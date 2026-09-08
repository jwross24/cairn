import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from cairn import allowlist

FRAMEWORK = os.environ.get("CAIRN_FRAMEWORK_PYTHON", "/opt/homebrew/bin/python3.14")
NETWORK = "import socket; socket.socket().connect(('1.1.1.1', 80)); print('METHOD_COMPLETED')"
HONEST = "print(2 + 2); print('METHOD_COMPLETED')"


def main():
    resolved = os.path.realpath(FRAMEWORK)
    derive = getattr(allowlist, "reexec_target", lambda path: None)
    target = derive(resolved)
    execs = tuple(sorted({resolved} | ({target} if target else set())))

    root = Path(tempfile.mkdtemp(prefix="cairn-framework-reexec-"))
    scratch = root / "scratch"
    scratch.mkdir()
    profile = root / "profile.sb"
    body = allowlist.profile_bytes(execs)
    profile.write_bytes(body)

    value = allowlist.AllowList(
        template_name="ladder_method",
        template_hash="0" * 64,
        bundle_hash="0" * 64,
        mechanism=allowlist.MECHANISM_SANDBOX_EXEC,
        counted_object=resolved,
        declared_backends=(),
        exec_paths=execs,
        network_egress=False,
        writable_root=os.path.realpath(scratch),
        profile_hash=hashlib.sha256(body).hexdigest(),
    )

    def run(source):
        argv = [
            allowlist.SANDBOX_EXEC,
            "-D",
            f"SCRATCH={value.writable_root}",
            "-f",
            str(profile),
            resolved,
            "-c",
            source,
        ]
        return subprocess.run(argv, capture_output=True)

    print("interpreter     :", FRAMEWORK)
    print("resolved        :", resolved)
    print("derived re-exec :", target)
    print("exec paths      :", len(execs))
    print()

    honest = run(HONEST)
    print("--- honest method ---")
    print("rc     :", honest.returncode)
    print("stdout :", honest.stdout)
    print("stderr :", honest.stderr)
    print()

    network = run(NETWORK)
    named = allowlist.detect_violation(network.returncode, network.stderr, value)
    print("--- network method ---")
    print("rc     :", network.returncode)
    print("stdout :", network.stdout)
    print("stderr :", network.stderr)
    print("detect_violation ->", named)
    print()

    unnamed_denial = network.returncode != 0 and named is None
    honest_confined = honest.returncode != 0 and b"METHOD_COMPLETED" not in honest.stdout
    print("DEFECT 1  a real denial is named None (fail-open)          :", unnamed_denial)
    print("DEFECT 2  the honest method never runs on this interpreter :", honest_confined)
    return 0 if (unnamed_denial and honest_confined) else 1


if __name__ == "__main__":
    sys.exit(main())
