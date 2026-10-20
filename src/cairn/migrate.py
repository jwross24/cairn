import sys

from cairn import cli, exits, migrate_apply, migrate_catalog, migrate_plan, substrate
from cairn.errors import CliError

SUMMARY = "substrate maintenance: migrate plan | apply | undo (explicit, additive, backed up; never run on open)"


def configure(parser):
    subs = parser.add_subparsers(dest="substrate_command", metavar="GROUP")
    migrate = subs.add_parser("migrate", help="move an older store to the shipped schema", description=SUMMARY)
    verbs = migrate.add_subparsers(dest="migrate_command", metavar="VERB")
    shared = [cli.globals_parent(suppress=True), cli.json_parent()]
    verbs.add_parser("plan", parents=shared, help="print the steps, backup path and plan token; writes nothing")
    apply_parser = verbs.add_parser("apply", parents=shared, help="back up, migrate and verify under the plan token")
    apply_parser.add_argument("--plan-token", required=True, metavar="TOKEN", help="the token `plan` printed")
    undo_parser = verbs.add_parser(
        "undo", parents=shared, help="restore the verified backup; quarantine the current file"
    )
    undo_parser.add_argument("--run", required=True, metavar="RUN-ID", help="the run id `apply` printed")


def _emit(ns, payload, lines):
    if getattr(ns, "json", False):
        cli.emit_json("substrate", payload)
    else:
        sys.stdout.write("\n".join(lines) + "\n")


def _guard(call, db, next_command):
    try:
        return call()
    except FileNotFoundError as exc:
        raise CliError(exits.ENVIRONMENT, str(exc), where=str(db), next_command=next_command) from exc
    except migrate_plan.NothingToMigrate:
        raise
    except migrate_catalog.MigrationRefused as exc:
        raise CliError(exits.GATE_REFUSED, str(exc), where=str(db), next_command=next_command) from exc


def _plan(ns):
    command = f"cairn substrate migrate plan --db {ns.db}"
    try:
        plan = _guard(
            lambda: migrate_plan.plan_readonly(ns.db, substrate.shipped_objects(), migrate_catalog.load_catalog()),
            ns.db,
            command,
        )
    except migrate_plan.NothingToMigrate as exc:
        _emit(ns, {"mode": "plan", "status": "current", "message": str(exc)}, [str(exc)])
        return exits.OK
    document = plan.document(migrate_plan.utc_stamp())
    lines = [
        f"store: {document['path']}",
        f"from {plan.from_fp[:12]} to {plan.to_fp[:12]}",
        *[f"step {s['id']}: {s['file']} sha256 {s['sql_sha256'][:12]}" for s in document["steps"]],
        f"backup (timestamp is fixed at apply): {document['backup_path']}",
        f"integrity_check: {plan.integrity}",
        f"plan token: {plan.token}",
        f"run: cairn substrate migrate apply --db {document['path']} --plan-token {plan.token}",
    ]
    _emit(ns, {"mode": "plan", "status": "planned", **document}, lines)
    return exits.OK


def _apply(ns):
    result = _guard(
        lambda: migrate_apply.apply(ns.db, ns.plan_token, substrate.shipped_objects(), migrate_catalog.load_catalog()),
        ns.db,
        f"cairn substrate migrate plan --db {ns.db}",
    )
    lines = [
        f"migrated {result['path']}: {result['from_fingerprint'][:12]} to {result['to_fingerprint'][:12]}",
        f"steps: {', '.join(result['steps'])}",
        f"backup: {result['backup_path']}",
        f"undo: cairn substrate migrate undo --db {result['path']} --run {result['run_id']}",
    ]
    _emit(ns, {"mode": "apply", "status": "applied", **result}, lines)
    return exits.OK


def _undo(ns):
    result = _guard(
        lambda: migrate_apply.undo(ns.db, ns.run, substrate.shipped_objects()),
        ns.db,
        f"cairn substrate migrate undo --db {ns.db} --run {ns.run}",
    )
    lines = [
        f"restored {result['path']} from {result['restored_from']}",
        f"quarantined (kept, not deleted): {result['quarantined']}",
    ]
    _emit(ns, {"mode": "undo", "status": "restored", **result}, lines)
    return exits.OK


def run(ns):
    verbs = {"plan": _plan, "apply": _apply, "undo": _undo}
    verb = getattr(ns, "migrate_command", None)
    if getattr(ns, "substrate_command", None) != "migrate" or verb not in verbs:
        lines = [f"cairn substrate migrate {name} --db PATH" for name in verbs]
        _emit(ns, {"mode": "usage", "verbs": list(verbs)}, ["verbs (see cairn substrate migrate --help):", *lines])
        return exits.OK
    return verbs[verb](ns)


cli.register("substrate", configure, run, summary=SUMMARY, read_only=False, json=True)
