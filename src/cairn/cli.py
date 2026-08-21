import argparse
import importlib
import importlib.metadata
import json
import platform
import sys

from cairn import log

GLOBAL_DEFAULTS = {
    "db": "var/substrate.sqlite",
    "bundle": "deploy/gate-bundle.sqlite",
    "pin": "deploy/gate-bundle.pin",
    "attest": "deploy/attestations.log",
    "log": None,
}
COMMAND_MODULES = []
_SUBCOMMANDS = {}


def register(name, configure, run):
    _SUBCOMMANDS[name] = (configure, run)


def registered():
    _load_command_modules()
    return tuple(sorted(_SUBCOMMANDS))


def _load_command_modules():
    for module in COMMAND_MODULES:
        importlib.import_module(module)


def globals_parent(*, suppress):
    parent = argparse.ArgumentParser(add_help=False)
    default = (lambda key: argparse.SUPPRESS) if suppress else (lambda key: GLOBAL_DEFAULTS[key])
    parent.add_argument("--db", default=default("db"), metavar="PATH")
    parent.add_argument("--bundle", default=default("bundle"), metavar="PATH")
    parent.add_argument("--pin", default=default("pin"), metavar="PATH")
    parent.add_argument("--attest", default=default("attest"), metavar="PATH")
    parent.add_argument("--log", default=default("log"), metavar="LEVEL")
    return parent


def build_parser():
    _load_command_modules()
    parser = argparse.ArgumentParser(prog="cairn", parents=[globals_parent(suppress=False)])
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    for name, (configure, _run) in sorted(_SUBCOMMANDS.items()):
        sub = subparsers.add_parser(name, parents=[globals_parent(suppress=True)])
        configure(sub)
    return parser


def _env_configure(parser):
    parser.add_argument("--json", action="store_true")


def _env_run(ns):
    from cairn import pari

    info = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "blake3": importlib.metadata.version("blake3"),
        "gp_bin": pari.GP_BIN,
        **pari.pari_versions(),
    }
    if ns.json:
        print(json.dumps(info, sort_keys=True))
    else:
        for key in sorted(info):
            print(f"{key}: {info[key]}")
    return 0


register("env", _env_configure, _env_run)


def main(argv=None):
    parser = build_parser()
    ns = parser.parse_args(argv)
    log.configure(ns.log)
    lg = log.get("cli")
    if ns.version:
        version = importlib.metadata.version("cairn")
        lg.info("version", version=version)
        print(version)
        return 0
    if not ns.command:
        parser.print_usage(sys.stderr)
        return 2
    lg.info("command", command=ns.command, db=ns.db, bundle=ns.bundle, pin=ns.pin, attest=ns.attest)
    _configure, run = _SUBCOMMANDS[ns.command]
    return run(ns)


def entry():
    sys.exit(main())


if __name__ == "__main__":
    entry()
