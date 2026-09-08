import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

SANDBOX_EXEC = "/usr/bin/sandbox-exec"
CHILD = """
import os, socket, subprocess, sys
scratch, action, outside, backend = sys.argv[1:5]
try:
    if action == "arith":
        sys.stdout.write(str(pow(3, 41, 2**61 - 1)))
    elif action == "scratch_write":
        (open(os.path.join(scratch, "ok.txt"), "w")).write("x")
    elif action == "outside_write":
        (open(outside, "w")).write("x")
    elif action == "network":
        s = socket.socket(); s.settimeout(5); s.connect(("1.1.1.1", 80)); s.close()
    elif action == "undeclared_exec":
        subprocess.run(["/bin/echo", "spawned"], check=True)
    elif action == "declared_exec":
        subprocess.run([backend, "-c", "pass"], check=True)
except BaseException as exc:
    sys.stderr.write("CHILD_ERR %s: %s\\n" % (type(exc).__name__, exc))
    raise SystemExit(9)
sys.stdout.write("CHILD_OK")
"""
PROFILE = """(version 1)
(deny default)
(allow process-fork)
(allow process-exec {execs})
(allow sysctl-read)
(allow mach-lookup)
(allow file-read* (subpath "/"))
(allow file-write* (subpath (param "SCRATCH")))
"""
ACTIONS = ("arith", "scratch_write", "declared_exec", "outside_write", "network", "undeclared_exec")
CONFINED = ("outside_write", "network", "undeclared_exec")


def _real(path):
    return os.path.realpath(str(path))


def run(action, *, root, profile, backend, resolve_scratch):
    scratch = root / "scratch"
    outside = root / "outside" / f"{action}.txt"
    argv = [
        SANDBOX_EXEC,
        "-D",
        f"SCRATCH={_real(scratch) if resolve_scratch else str(scratch)}",
        "-f",
        str(profile),
        backend,
        "-c",
        CHILD,
        str(scratch),
        action,
        str(outside),
        backend,
    ]
    done = subprocess.run(argv, capture_output=True, text=True)
    return {
        "action": action,
        "rc": done.returncode,
        "stdout": done.stdout.strip()[-120:],
        "stderr": done.stderr.strip()[-160:],
        "side_effect_present": outside.exists() if action == "outside_write" else None,
    }


def main():
    parser = argparse.ArgumentParser(description="probe the macOS method allow-list enforcement arm")
    parser.add_argument("--backend", default=_real(sys.executable))
    parser.add_argument("--unresolved-scratch", action="store_true")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="cairn-allowlist-probe-"))
    (root / "scratch").mkdir()
    (root / "outside").mkdir()
    profile = root / "method.sb"
    profile.write_text(PROFILE.format(execs=f'(literal "{args.backend}")'))
    rows = [
        run(a, root=root, profile=profile, backend=args.backend, resolve_scratch=not args.unresolved_scratch)
        for a in ACTIONS
    ]
    report = {
        "platform": sys.platform,
        "uname": " ".join(os.uname()),
        "sandbox_exec": SANDBOX_EXEC,
        "backend": args.backend,
        "root": str(root),
        "scratch_resolved": not args.unresolved_scratch,
        "rows": rows,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    by_action = {r["action"]: r for r in rows}
    if args.unresolved_scratch:
        assert by_action["scratch_write"]["rc"] == 9, "an unresolved scratch path is expected to deny the honest write"
        return
    for action in ("arith", "scratch_write", "declared_exec"):
        assert by_action[action]["rc"] == 0, f"{action} must be admitted"
    for action in CONFINED:
        assert by_action[action]["rc"] == 9, f"{action} must be confined"
    assert by_action["outside_write"]["side_effect_present"] is False
    with socket.socket() as probe:
        probe.settimeout(5)
        probe.connect(("1.1.1.1", 80))


if __name__ == "__main__":
    main()
