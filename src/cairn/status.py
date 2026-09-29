import argparse
import json
import sqlite3
from pathlib import Path

from cairn import bundle, canon, claims, cli, exits, human_queue, keys, substrate, yank

CALIBRATIONS = claims.TAGS
CLAIM_STATUSES = ("open", "refuted", "promoted", "withdrawn")


def _limit(value):
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from None
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return parsed


def configure(parser):
    parser.add_argument("--limit", "--last", dest="limit", type=_limit, default=10, metavar="N")


def _bundle_snapshot(bundle_path, pin_path):
    missing = [str(path) for path in (bundle_path, pin_path) if not Path(path).is_file()]
    if missing:
        return {
            "state": "absent",
            "bundle_hash": None,
            "pin_hash": None,
            "pin_match": None,
            "reason": "missing gate artifact: " + ", ".join(missing),
        }, {}
    try:
        rows = bundle.read_rows(bundle_path)
        digest = bundle.bundle_hash(rows)
        pin_hash = bundle.read_pin(pin_path)
    except (OSError, sqlite3.Error, bundle.BundleError) as exc:
        return {
            "state": "unavailable",
            "bundle_hash": None,
            "pin_hash": None,
            "pin_match": None,
            "reason": f"{type(exc).__name__}: {exc}",
        }, {}
    objects = {}
    try:
        for kind, canonical, _ in rows:
            if kind in ("gate_plan", "tiers"):
                objects[kind] = bundle._decode(canonical)
    except (ValueError, TypeError, IndexError) as exc:
        return {
            "state": "unavailable",
            "bundle_hash": digest,
            "pin_hash": pin_hash,
            "pin_match": digest == pin_hash,
            "reason": f"bundle object decode failed: {type(exc).__name__}: {exc}",
        }, {}
    return {
        "state": "present",
        "bundle_hash": digest,
        "pin_hash": pin_hash,
        "pin_match": digest == pin_hash,
    }, objects


def _unavailable(reason):
    return {"state": "unavailable", "reason": reason}


def _absent(reason):
    return {"state": "absent", "reason": reason}


def _claim_summary(sub):
    rows = sub.conn.execute(
        "SELECT statements.status, (SELECT history.to_tag FROM tag_history history "
        "WHERE history.statement_hash = statements.hash ORDER BY history.seq DESC LIMIT 1) AS calibration, "
        "COUNT(*) AS count FROM claim_statements statements "
        "GROUP BY statements.status, calibration ORDER BY statements.status, calibration"
    ).fetchall()
    groups = [
        {"status": row["status"], "calibration": row["calibration"] or "untagged", "count": row["count"]}
        for row in rows
    ]
    status_counts = dict.fromkeys(CLAIM_STATUSES, 0)
    calibration_counts = dict.fromkeys((*CALIBRATIONS, "untagged"), 0)
    for row in groups:
        claim_status = str(row["status"])
        calibration = str(row["calibration"])
        count = int(row["count"])
        status_counts[claim_status] = status_counts.get(claim_status, 0) + count
        calibration_counts[calibration] = calibration_counts.get(calibration, 0) + count
    return {
        "state": "present",
        "total": sum(status_counts.values()),
        "by_status": status_counts,
        "by_calibration": calibration_counts,
        "groups": groups,
    }


def _skill_revisions(sub, attest_path):
    rows = sub.conn.execute(
        "SELECT nodes.hash, nodes.canonical, certificates.cert_hash "
        "FROM nodes LEFT JOIN skill_certificates certificates "
        "ON certificates.identity_bundle_hash = nodes.hash "
        "WHERE nodes.kind = 'identity_bundle' ORDER BY nodes.hash"
    ).fetchall()
    revisions = []
    for row in rows:
        identity = row["hash"]
        data = canon.decode(keys.IDENTITY_BUNDLE, row["canonical"])
        yanks = yank.records_for(sub, identity, attest_path=attest_path)
        reach = [
            {
                "yank_id": yank["yank_id"],
                "predicate": json.loads(yank["reach_predicate"]),
                "kind": yank["kind"],
                "verdict_ref": yank["verdict_ref"],
                "ruling_ref": yank["ruling_ref"],
                "record_digest": yank["record_digest"],
                "file_offset": yank["file_offset"],
                "created_at": yank["created_at"],
            }
            for yank in yanks
        ]
        certified = sub.certified(identity)
        is_yanked = sub.yanked(identity, attest_path=attest_path)
        revisions.append(
            {
                "identity_bundle_hash": identity,
                "interface_version": data["interface_version"],
                "implementation_revision": data["implementation_revision"],
                "status": "yanked" if is_yanked else "certified" if certified else "uncertified",
                "certified": certified,
                "certificate_hash": row["cert_hash"] if certified else None,
                "yank_reach": reach,
            }
        )
    return {"state": "present", "revisions": revisions}


def _gate_plan(steps, sub, bundle_hash, pin_hash):
    if not isinstance(steps, list):
        return _unavailable("gate plan has no steps list")
    observed = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("step"), str):
            return _unavailable("gate plan contains a malformed step")
        row = sub.conn.execute(
            "SELECT run_id, result, reasons, at FROM gate_runs "
            "WHERE gate = ? AND plan_step = ? AND bundle_hash = ? AND pin_hash = ? "
            "ORDER BY rowid DESC LIMIT 1",
            ("gate_plan", step["step"], bundle_hash, pin_hash),
        ).fetchone()
        verdict = None
        if row is not None:
            verdict = {
                "result": row["result"],
                "reasons": json.loads(row["reasons"]),
                "run_id": row["run_id"],
                "at": row["at"],
            }
        observed.append(
            {
                "step": step["step"],
                "kind": step.get("kind"),
                "expected": step.get("expect"),
                "latest_verdict": verdict,
                "verdict_state": "recorded" if verdict is not None else "unrecorded",
            }
        )
    return {"state": "present", "steps": observed}


def _gate_runs(sub, limit):
    rows = sub.conn.execute(
        "SELECT run_id, gate, plan_step, bundle_hash, pin_hash, result, reasons, at "
        "FROM gate_runs ORDER BY rowid DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return {
        "state": "present",
        "limit": limit,
        "runs": [
            {
                "run_id": row["run_id"],
                "gate": row["gate"],
                "plan_step": row["plan_step"],
                "bundle_hash": row["bundle_hash"],
                "pin_hash": row["pin_hash"],
                "result": row["result"],
                "reasons": json.loads(row["reasons"]),
                "at": row["at"],
            }
            for row in rows
        ],
    }


def _database_snapshot(db_path, attest_path, limit, gate_steps, bundle_hash, pin_hash):
    if not Path(db_path).is_file():
        reason = f"substrate database is missing: {db_path}"
        return {
            "skills": _absent(reason),
            "claims": _absent(reason),
            "gate_runs": _absent(reason),
            "gate_plan": _absent(reason),
            "human_queue": _absent(reason),
        }
    try:
        with substrate.Substrate.open(db_path, role="reader") as sub:
            sub.conn.execute("BEGIN")
            try:
                skills = _skill_revisions(sub, attest_path)
                claim_summary = _claim_summary(sub)
                run_history = _gate_runs(sub, limit)
                plan = (
                    _gate_plan(gate_steps, sub, bundle_hash, pin_hash)
                    if bundle_hash is not None and pin_hash is not None
                    else _unavailable("bundle and pin hashes are required to scope plan verdicts")
                )
                try:
                    queue_depth = human_queue.depth(sub, attest_path)
                    queue = {"state": "present", "depth": queue_depth}
                except (OSError, human_queue.QueueError, human_queue.attest.AttestationError) as exc:
                    queue = _unavailable(f"{type(exc).__name__}: {exc}")
                sub.conn.execute("COMMIT")
            except BaseException:
                sub.conn.execute("ROLLBACK")
                raise
    except (OSError, sqlite3.Error, substrate.SubstrateError) as exc:
        reason = f"{type(exc).__name__}: {exc}"
        return {
            "skills": _unavailable(reason),
            "claims": _unavailable(reason),
            "gate_runs": _unavailable(reason),
            "gate_plan": _unavailable(reason),
            "human_queue": _unavailable(reason),
        }
    return {
        "skills": skills,
        "claims": claim_summary,
        "gate_runs": run_history,
        "gate_plan": plan,
        "human_queue": queue,
    }


def _tier_limits(bundle_state, objects):
    if bundle_state["state"] == "absent":
        return {
            "state": "absent",
            "reason": "tier limits are read from the gate bundle",
            "remaining_budget": {"state": "absent", "reason": "supplied per launch"},
        }
    if bundle_state["state"] != "present" or "tiers" not in objects:
        return {
            "state": "unavailable",
            "reason": bundle_state.get("reason", "gate bundle has no tiers object"),
            "remaining_budget": {"state": "absent", "reason": "supplied per launch"},
        }
    return {
        "state": "present",
        "limits": objects["tiers"],
        "remaining_budget": {"state": "absent", "reason": "supplied per launch"},
    }


def _affordances(bundle_state, bundle_path, pin_path, db_path, attest_path, limit):
    affordances = [
        {
            "argv": ["cairn", "capabilities", "--json"],
            "outcome": "available",
            "exit_code": exits.OK,
            "reasons": [],
        },
        {
            "argv": [
                "cairn",
                "status",
                "--db",
                str(db_path),
                "--bundle",
                str(bundle_path),
                "--pin",
                str(pin_path),
                "--attest",
                str(attest_path),
                "--limit",
                str(limit),
                "--json",
            ],
            "outcome": "available",
            "exit_code": exits.OK,
            "reasons": [],
        },
    ]
    requires_input = [
        {"command": "cairn justify", "arguments": ["--statement"], "reason": "a claim statement hash is required"}
    ]
    if bundle_state["state"] == "absent":
        code = exits.ENVIRONMENT
        outcome = "refused"
        reasons = [bundle_state["reason"]]
    elif bundle_state.get("bundle_hash") is not None and bundle_state.get("pin_hash") is not None:
        code = exits.OK if bundle_state["pin_match"] else exits.GATE_REFUSED
        outcome = "available" if bundle_state["pin_match"] else "refused"
        reasons = [] if bundle_state["pin_match"] else ["gate bundle hash differs from the pin"]
    else:
        code = None
        outcome = "unknown"
        reasons = [bundle_state["reason"]]
    if code is not None:
        affordances.append(
            {
                "argv": [
                    "cairn",
                    "bundle",
                    "show",
                    "--bundle",
                    str(bundle_path),
                    "--pin",
                    str(pin_path),
                    "--json",
                ],
                "outcome": outcome,
                "exit_code": code,
                "reasons": reasons,
            }
        )
    if bundle_state.get("bundle_hash") is not None and bundle_state.get("pin_match") is False:
        affordances.append(
            {
                "argv": [
                    "cairn",
                    "selftest",
                    "toy-curve",
                    "--db",
                    str(db_path),
                    "--bundle",
                    str(bundle_path),
                    "--pin",
                    str(pin_path),
                ],
                "precondition": "GateBundle.open",
                "outcome": "refused",
                "exit_code": exits.GATE_REFUSED,
                "reason": "the bundle pin mismatch is checked before the self-test writes substrate state",
            }
        )
    return affordances, requires_input


def document(*, db_path, bundle_path, pin_path, attest_path, limit=10):
    bundle_state, objects = _bundle_snapshot(bundle_path, pin_path)
    database = _database_snapshot(
        db_path,
        attest_path,
        limit,
        objects.get("gate_plan", {}).get("steps") if isinstance(objects.get("gate_plan"), dict) else None,
        bundle_state.get("bundle_hash"),
        bundle_state.get("pin_hash"),
    )
    if bundle_state["state"] == "absent":
        plan = _absent("gate plan is read from the gate bundle")
    elif bundle_state["state"] != "present":
        plan = _unavailable(bundle_state.get("reason", "gate bundle is unavailable"))
    elif "gate_plan" not in objects:
        plan = _unavailable("gate bundle has no gate_plan object")
    else:
        plan = database["gate_plan"]
    affordances, requires_input = _affordances(bundle_state, bundle_path, pin_path, db_path, attest_path, limit)
    return {
        "bundle": bundle_state,
        "gate_plan": plan,
        "skills": database["skills"],
        "tiers": _tier_limits(bundle_state, objects),
        "claims": database["claims"],
        "gate_runs": database["gate_runs"],
        "human_queue": database["human_queue"],
        "affordances": affordances,
        "requires_input": requires_input,
    }


def run(ns):
    payload = document(
        db_path=ns.db,
        bundle_path=ns.bundle,
        pin_path=ns.pin,
        attest_path=ns.attest,
        limit=ns.limit,
    )
    cli.emit_json("status", payload)
    return exits.OK


cli.register(
    "status",
    configure,
    run,
    summary="observe bundle, substrate and command preconditions in one read-only document",
    read_only=True,
    json=True,
)
