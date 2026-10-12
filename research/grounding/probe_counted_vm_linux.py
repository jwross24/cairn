import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHILD = ROOT / "tests" / "fixtures" / "countedvm_child.py"
DENIED = (
    "file",
    "fork",
    "exec",
    "socket",
    "read_extra",
    "write_extra",
    "write_stdin",
    "read_stdout",
    "read_high_fd",
    "clock",
    "stat",
    "mmap_exec",
    "mmap_file",
    "mmap_anon_fd",
    "mmap_extra_flags",
)
ALLOWED = ("read_stdin", "write_stdio", "mmap_anon")


def _child(request):
    completed = subprocess.run(
        [sys.executable, str(CHILD)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def run(scratch):
    checks = {}
    for kind in (*DENIED, *ALLOWED):
        results = _child({"op": "probe", "scratch": str(scratch / kind), "kind": kind})
        assert results["uncontained"]["rc"] == 0, (kind, results)
        assert results["contained"]["rc"] == (1 if kind in DENIED else 0), (kind, results)
        checks[kind] = results
    mutant = _child(
        {
            "op": "mutant",
            "scratch": str(scratch / "bad-arch"),
            "old": "BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, arch, 1, 0)",
            "new": "BPF_JUMP(BPF_JMP | BPF_JEQ | BPF_K, 0, 1, 0)",
        }
    )
    refused = _child(
        {
            "op": "launch",
            "binary": mutant["binary"],
            "digest": mutant["digest"],
            "instance": [23, 1, 1, 28, [3, 10], [3, 10]],
            "program": "halt",
            "budget": 10_000,
            "attempt_id": "linux-wrong-architecture",
            "scratch": str(scratch / "bad-arch-run"),
        }
    )
    assert refused == {"refused": "vm_exit"}, refused
    checks["architecture"] = refused
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path)
    args = parser.parse_args()
    if sys.platform != "linux":
        parser.exit(64, "REFUSED: this probe requires a real Linux kernel\n")
    scratch = args.scratch or Path(tempfile.mkdtemp(prefix="cairn-seccomp-probe-"))
    scratch.mkdir(parents=True, exist_ok=True)
    results = run(scratch)
    print(json.dumps({"status": "PASS", "checks": results, "scratch": str(scratch)}, sort_keys=True))


if __name__ == "__main__":
    main()
