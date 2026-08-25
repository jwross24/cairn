import argparse
import difflib
import importlib
import importlib.metadata
import json
import os
import platform
import sys
import time
import traceback
from dataclasses import dataclass, field

from cairn import exits, log
from cairn.errors import CliError

SCHEMA_VERSION = 1
CONTRACT_VERSION = "1"
GLOBAL_DEFAULTS = {
    "db": "var/substrate.sqlite",
    "bundle": "deploy/gate-bundle.sqlite",
    "pin": "deploy/gate-bundle.pin",
    "attest": "deploy/attestations.log",
    "log": None,
}
ENV_VARS = {
    "CAIRN_LOG": "log level when --log is absent (default INFO); records are JSON lines on stderr",
    "HYPOTHESIS_PROFILE": "test-only: ci (500 examples) or dev (50)",
    "UPDATE_GOLDENS": "test-only: 1 rewrites golden files instead of diffing them",
    "SOURCE_DATE_EPOCH": "any emitted timestamp uses this epoch instead of the wall clock",
    "NO_COLOR": "honored trivially: cairn never emits ANSI sequences",
}
DISCOVERY_HINT = "Structured output: add --json to any read-side command. Contract: cairn capabilities --json. Agent handbook: cairn robot-docs."
COMMAND_MODULES = ["cairn.kat", "cairn.measure", "cairn.bundle", "cairn.attest", "cairn.selftest", "cairn.runner", "cairn.gateplan", "cairn.justify", "cairn.m0"]
_SUBCOMMANDS = {}


@dataclass(frozen=True)
class Command:
    name: str
    configure: object
    run: object
    summary: str
    read_only: bool
    json: bool
    dangerous: bool = False
    gating: str | None = None
    aliases: tuple = field(default_factory=tuple)
    dry_run_default: bool = False


def register(name, configure, run, *, summary, read_only, json, dangerous=False, gating=None, aliases=(), dry_run_default=False):
    if dangerous and not gating:
        raise ValueError(f"{name}: a dangerous command must name its gating flag")
    _SUBCOMMANDS[name] = Command(name, configure, run, summary, read_only, json, dangerous, gating, tuple(aliases), dry_run_default)


def unregister(name):
    _SUBCOMMANDS.pop(name, None)


def commands():
    _load_command_modules()
    return tuple(_SUBCOMMANDS[n] for n in sorted(_SUBCOMMANDS))


def registered():
    return tuple(c.name for c in commands())


def _load_command_modules():
    for module in COMMAND_MODULES:
        importlib.import_module(module)


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        hint = ""
        if message.startswith("unrecognized arguments:"):
            bad = [tok for tok in message.split(":", 1)[1].split() if tok.startswith("-")]
            known = sorted(_all_option_strings(self))
            for tok in bad:
                close = difflib.get_close_matches(tok, known, n=1, cutoff=0.6)
                if close:
                    hint = f"did you mean {close[0]}?"
                    break
        what = f"{self.prog}: {message}" + (f" ({hint})" if hint else "")
        raise CliError(exits.USER_INPUT, what, next_command=f"{self.prog} --help")


def _all_option_strings(parser):
    found = set(parser._option_string_actions)
    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for sub in action.choices.values():
                found |= set(sub._option_string_actions)
    return found


def globals_parent(*, suppress):
    parent = argparse.ArgumentParser(add_help=False)
    default = (lambda key: argparse.SUPPRESS) if suppress else (lambda key: GLOBAL_DEFAULTS[key])
    parent.add_argument("--db", default=default("db"), metavar="PATH", help="substrate SQLite file")
    parent.add_argument("--bundle", default=default("bundle"), metavar="PATH", help="gate bundle SQLite file")
    parent.add_argument("--pin", default=default("pin"), metavar="PATH", help="gate-bundle pin file")
    parent.add_argument("--attest", default=default("attest"), metavar="PATH", help="attestation file")
    parent.add_argument("--log", default=default("log"), metavar="LEVEL", help="log level for the JSON records on stderr")
    return parent


def json_parent():
    parent = argparse.ArgumentParser(add_help=False)
    parent.add_argument("--json", "--robot", dest="json", action="store_true", default=argparse.SUPPRESS, help="emit exactly one JSON document on stdout")
    return parent


def build_parser():
    _load_command_modules()
    parser = _Parser(prog="cairn", parents=[globals_parent(suppress=False)], epilog=DISCOVERY_HINT, suggest_on_error=True)
    parser.add_argument("--version", action="store_true", help="print the version and exit")
    parser.add_argument("--robot-help", action="store_true", help="print the agent handbook (same as: cairn robot-docs)")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    for cmd in commands():
        sub = subparsers.add_parser(cmd.name, aliases=cmd.aliases, parents=[globals_parent(suppress=True)], help=cmd.summary, description=cmd.summary, epilog=DISCOVERY_HINT, suggest_on_error=True)
        sub.__class__ = _Parser
        if cmd.json:
            sub.add_argument("--json", "--robot", dest="json", action="store_true", help="emit exactly one JSON document on stdout")
        if cmd.dangerous:
            sub.add_argument(cmd.gating, dest=_gating_dest(cmd.gating), action="store_true", help="required for the irreversible part of this command")
        cmd.configure(sub)
    return parser


def _gating_dest(flag):
    return flag.lstrip("-").replace("-", "_")


def _refuse_ungated(cmd, ns):
    if cmd.dangerous and not cmd.dry_run_default and not getattr(ns, _gating_dest(cmd.gating), False):
        raise CliError(exits.GATE_REFUSED, f"{cmd.name} is irreversible and was invoked without {cmd.gating}; nothing was changed", next_command=f"cairn {cmd.name} {cmd.gating}")


def resolve_command(name):
    for cmd in commands():
        if name == cmd.name or name in cmd.aliases:
            return cmd
    raise KeyError(name)


def emit_json(command, payload):
    document = {"schema_version": SCHEMA_VERSION, "command": command, **payload}
    sys.stdout.write(json.dumps(document, sort_keys=True) + "\n")


def now_iso():
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    seconds = int(epoch) if epoch else time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(seconds))


def refuse_overwrite(path, *, flag, command, force):
    if os.path.exists(path) and not force:
        raise CliError(exits.GATE_REFUSED, f"{path} exists and would be overwritten; nothing was changed", where=str(path), next_command=f"{command} {flag}")


def require_yes(yes, *, plan, command):
    if not yes:
        raise CliError(exits.GATE_REFUSED, f"refusing the irreversible step without --yes; nothing was changed; plan: {plan}", next_command=f"{command} --yes")


def capabilities_document():
    from cairn import pari

    return {
        "tool": "cairn",
        "version": importlib.metadata.version("cairn"),
        "contract_version": CONTRACT_VERSION,
        "python": platform.python_version(),
        "commands": [
            {"name": c.name, "summary": c.summary, "read_only": c.read_only, "json": c.json, "dangerous": c.dangerous, "gating": c.gating, "dry_run_default": c.dry_run_default, "aliases": list(c.aliases)}
            for c in commands()
        ],
        "exit_codes": {"cli": {str(k): v for k, v in exits.CLI.items()}, "doctor": {str(k): v for k, v in exits.DOCTOR.items()}},
        "env_vars": ENV_VARS,
        "global_options": {"--db": GLOBAL_DEFAULTS["db"], "--bundle": GLOBAL_DEFAULTS["bundle"], "--pin": GLOBAL_DEFAULTS["pin"], "--attest": GLOBAL_DEFAULTS["attest"], "--log": "INFO"},
        "default_paths": {"db": GLOBAL_DEFAULTS["db"], "bundle": GLOBAL_DEFAULTS["bundle"], "pin": GLOBAL_DEFAULTS["pin"], "attest": GLOBAL_DEFAULTS["attest"], "gp_bin": pari.GP_BIN},
        "stdout_is_data": True,
        "stderr_is_diagnostics": True,
        "emits_ansi": False,
        "interactive": False,
    }


def _capabilities_run(ns):
    doc = capabilities_document()
    if ns.json:
        emit_json("capabilities", doc)
        return exits.OK
    print(f"cairn {doc['version']} (contract {doc['contract_version']})")
    for c in doc["commands"]:
        flags = ", ".join(f for f, on in (("read-only", c["read_only"]), ("--json", c["json"]), ("dangerous", c["dangerous"])) if on)
        print(f"  {c['name']:<14} {c['summary']}  [{flags}]")
    print("exit codes (cli): " + "; ".join(f"{k}={v.split(':')[0]}" for k, v in doc["exit_codes"]["cli"].items()))
    print("full contract: cairn capabilities --json; handbook: cairn robot-docs")
    return exits.OK


def robot_docs_text():
    doc = capabilities_document()
    lines = [
        "# cairn — agent handbook",
        "",
        "cairn is a research harness whose gates are immutable. You drive it non-interactively; stdout is data, stderr is JSON log records.",
        "",
        "## Canonical operator sequence (deploy once, then run)",
        "1. cairn bundle build --bundle deploy/gate-bundle.sqlite      (compile the gate bundle from bundle/)",
        "2. cairn bundle pin --bundle deploy/gate-bundle.sqlite --pin deploy/gate-bundle.pin   (pin its hash; pin becomes 0444+uappnd)",
        "3. cairn attest init --attest deploy/attestations.log --bundle ... --pin ...           (create the append-only attestation file)",
        "4. cairn selftest toy-curve --db var/substrate.sqlite --bundle ... --pin ...            (certify the exemplar skill)",
        "5. cairn gate selftest --db ... --bundle ... --pin ... --attest ...                   (planted-failure self-tests must pass first)",
        "6. cairn m0-run --bits 40 --seed 1 --db ... --bundle ... --pin ... --attest ...       (the M0 slice)",
        "When any command refuses: cairn doctor (read-only), then cairn doctor --fix for the two repairs it owns.",
        "",
        "## Commands (name: summary [read-only|writes] [--json] [dangerous: gating])",
    ]
    for c in doc["commands"]:
        tags = ["read-only" if c["read_only"] else "writes"]
        if c["json"]:
            tags.append("--json")
        if c["dangerous"]:
            tags.append(f"dangerous: {c['gating']}")
        alias = f" (aliases: {', '.join(c['aliases'])})" if c["aliases"] else ""
        lines.append(f"- {c['name']}: {c['summary']} [{'; '.join(tags)}]{alias}")
    lines += ["", "## Exit codes (cli)"]
    lines += [f"- {k}: {v}" for k, v in doc["exit_codes"]["cli"].items()]
    lines += ["", "## Exit codes (doctor)"]
    lines += [f"- {k}: {v}" for k, v in doc["exit_codes"]["doctor"].items()]
    lines += [
        "",
        "## Global options (before or after the subcommand)",
        "--db PATH, --bundle PATH, --pin PATH, --attest PATH, --log LEVEL; defaults: " + ", ".join(f"{k}={v}" for k, v in doc["global_options"].items()),
        "",
        "## Where artifacts land",
        "deploy/ (bundle, pin, attestation file; operator-owned, never hand-edited), var/ (substrate DB, locks), .doctor/ (doctor run artifacts, gitignored), tests/vectors + tests/goldens (committed known answers).",
        "",
        "## Never",
        "- never hand-edit or chmod files under deploy/; use cairn bundle/attest/doctor",
        "- never run gp through a shell; every gp spawn goes through cairn.pari.run_gp with an explicit stack",
        "- never bypass the pin: a bundle whose hash differs from the pin fails closed by design",
        "- never read exit 0 as proof: read the JSON document; a gate result is OK only when it says so",
        "",
        "## Env vars",
    ]
    lines += [f"- {k}: {v}" for k, v in doc["env_vars"].items()]
    return "\n".join(lines) + "\n"


def _robot_docs_run(ns):  # noqa: ARG001
    sys.stdout.write(robot_docs_text())
    return exits.OK


def _env_run(ns):
    from cairn import pari

    uname = os.uname()
    info = {
        "python": platform.python_version(),
        "os": f"{uname.sysname} {uname.release}",
        "machine": uname.machine,
        "blake3": importlib.metadata.version("blake3"),
        "gp_bin": pari.GP_BIN,
        **pari.pari_versions(),
    }
    if ns.json:
        emit_json("env", info)
    else:
        for key in sorted(info):
            print(f"{key}: {info[key]}")
    return exits.OK


register("env", lambda p: None, _env_run, summary="report the toolchain (python, cypari2/libpari, blake3, gp path)", read_only=True, json=True)
register("capabilities", lambda p: None, _capabilities_run, summary="describe the CLI contract: commands, exit codes, env vars, paths", read_only=True, json=True)
register("robot-docs", lambda p: None, _robot_docs_run, summary="print the paste-ready agent handbook", read_only=True, json=False)


def _render_error(err, lg):
    lg.info("error", **err.record())
    sys.stderr.write(err.human() + "\n")
    return err.code


def main(argv=None):
    lg = log.get("cli")
    try:
        parser = build_parser()
        ns = parser.parse_args(argv)
    except CliError as err:
        log.configure(None)
        return _render_error(err, lg)
    log.configure(ns.log)
    if ns.version:
        version = importlib.metadata.version("cairn")
        lg.info("version", version=version)
        print(version)
        return exits.OK
    if ns.robot_help:
        sys.stdout.write(robot_docs_text())
        return exits.OK
    if not ns.command:
        parser.print_usage(sys.stderr)
        sys.stderr.write(DISCOVERY_HINT + "\n")
        return exits.USER_INPUT
    cmd = resolve_command(ns.command)
    lg.info("command", command=cmd.name, db=ns.db, bundle=ns.bundle, pin=ns.pin, attest=ns.attest)
    try:
        _refuse_ungated(cmd, ns)
        return cmd.run(ns)
    except CliError as err:
        return _render_error(err, lg)
    except AssertionError:
        raise
    except Exception as exc:
        import sqlite3

        from cairn import pari

        if isinstance(exc, pari.GpMissing):
            code = exits.ENVIRONMENT
        elif isinstance(exc, sqlite3.OperationalError) and "locked" in str(exc):
            code = exits.CONFLICT
        else:
            code = exits.BACKEND
        err = CliError(code, f"{type(exc).__name__}: {exc}", next_command="cairn doctor")
        lg.debug("traceback", text=traceback.format_exc())
        return _render_error(err, lg)


def entry():
    sys.exit(main())


if __name__ == "__main__":
    from cairn.cli import entry as _entry

    _entry()
