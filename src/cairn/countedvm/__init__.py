import hashlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

SOURCE = Path(__file__).resolve().with_name("vm.c")
REPO_ROOT = Path(__file__).resolve().parents[3]
CC = Path("/usr/bin/clang")
CFLAGS = ("-O2", "-std=c11", "-Wall", "-Wextra")
RUN_TIMEOUT_S = 120
STATUS_OK = "OK"
STATUS_REFUSED = "REFUSED"
EXIT_INPUT_REFUSED = 2
EXIT_PROGRAM_REFUSED = 3
OUTPUT_KEYS = {"status", "count", "executed", "result", "p0", "i0"}
REFUSAL_KEYS = ({"status", "reason"}, {"status", "reason", "count", "executed"})
COUNTING_CONVENTION = {
    "addp": "one group op, whatever the operands; an add that reaches the doubling formula is still one op",
    "dblp": "one group op, whatever the operand",
    "negp": "not a group op",
    "mulp": "one group op per double and per add the ladder executes, from the scalar's top set bit down, "
    "identity operands included; a zero scalar executes nothing",
    "solve": "finalization, not a group op",
    "tables and index arithmetic": "not group ops; a tfind scan charges its scanned entries to the instruction budget",
}


class CountedVmError(RuntimeError):
    pass


@dataclass(frozen=True)
class Instance:
    p: int
    a: int
    b: int
    n: int
    P: tuple | None
    Q: tuple | None


@dataclass(frozen=True)
class Outcome:
    status: str
    reason: str | None
    count: int | None
    executed: int | None
    result: int | None
    p0: tuple | None
    i0: int | None
    exit_code: int


def source_sha256():
    return hashlib.sha256(SOURCE.read_bytes()).hexdigest()


def build(compiler=CC, scratch=None):
    compiler = Path(compiler)
    if not compiler.is_file() or not os.access(compiler, os.X_OK):
        raise CountedVmError(f"compiler is missing or not executable: {compiler}")
    scratch = Path(tempfile.mkdtemp(prefix="cairn-countedvm-")) if scratch is None else Path(scratch)
    binary = scratch / "vm"
    completed = subprocess.run(
        [str(compiler), *CFLAGS, "-o", str(binary), str(SOURCE)],
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_S,
        check=False,
    )
    if completed.returncode != 0 or not binary.is_file():
        raise CountedVmError(f"vm build failed: {completed.stderr.strip()}")
    return binary


def _point_line(name, point):
    if point is None:
        return f"{name} inf"
    return f"{name} {point[0]} {point[1]}"


def document(instance, program, budget):
    lines = [
        f"p {instance.p}",
        f"a {instance.a}",
        f"b {instance.b}",
        f"n {instance.n}",
        _point_line("P", instance.P),
        _point_line("Q", instance.Q),
        f"budget {budget}",
        "program",
        *program.strip("\n").splitlines(),
        "end",
    ]
    return "\n".join(lines) + "\n"


def _reject_duplicates(pairs):
    seen = {}
    for key, value in pairs:
        if key in seen:
            raise CountedVmError(f"duplicate output key: {key}")
        seen[key] = value
    return seen


def decode(stdout, exit_code):
    try:
        payload = json.loads(stdout, object_pairs_hook=_reject_duplicates)
    except (json.JSONDecodeError, TypeError) as exc:
        raise CountedVmError("vm output is not one JSON object") from exc
    if type(payload) is not dict:
        raise CountedVmError("vm output is not one JSON object")
    if payload.get("status") == STATUS_OK:
        if set(payload) != OUTPUT_KEYS or exit_code != 0:
            raise CountedVmError("vm success output does not match the closed protocol")
        p0 = payload["p0"]
        if p0 is not None and (type(p0) is not list or len(p0) != 2 or any(type(c) is not int for c in p0)):
            raise CountedVmError("vm p0 must be null or a pair of integers")
        for key in ("count", "executed"):
            if type(payload[key]) is not int or payload[key] < 0:
                raise CountedVmError(f"vm {key} must be a nonnegative integer")
        if payload["result"] is not None and (type(payload["result"]) is not int or payload["result"] < 0):
            raise CountedVmError("vm result must be null or a nonnegative integer")
        if type(payload["i0"]) is not int or payload["i0"] < 0:
            raise CountedVmError("vm i0 must be a nonnegative integer")
        return Outcome(
            STATUS_OK,
            None,
            payload["count"],
            payload["executed"],
            payload["result"],
            None if p0 is None else tuple(p0),
            payload["i0"],
            exit_code,
        )
    if payload.get("status") == STATUS_REFUSED:
        expected_keys = {EXIT_INPUT_REFUSED: REFUSAL_KEYS[0], EXIT_PROGRAM_REFUSED: REFUSAL_KEYS[1]}.get(exit_code)
        if expected_keys is None or set(payload) != expected_keys:
            raise CountedVmError("vm refusal output does not match the closed protocol")
        if type(payload["reason"]) is not str or not payload["reason"]:
            raise CountedVmError("vm refusal must name a reason")
        for key in ("count", "executed"):
            if key in payload and (type(payload[key]) is not int or payload[key] < 0):
                raise CountedVmError(f"vm refusal {key} must be a nonnegative integer")
        return Outcome(
            STATUS_REFUSED,
            payload["reason"],
            payload.get("count"),
            payload.get("executed"),
            None,
            None,
            None,
            exit_code,
        )
    raise CountedVmError("vm output status is unknown")


def run(binary, instance, program, budget):
    completed = subprocess.run(
        [str(binary)],
        input=document(instance, program, budget),
        capture_output=True,
        text=True,
        timeout=RUN_TIMEOUT_S,
        check=False,
    )
    if completed.stderr:
        raise CountedVmError(f"vm wrote to stderr: {completed.stderr.strip()}")
    if completed.returncode not in (0, EXIT_INPUT_REFUSED, EXIT_PROGRAM_REFUSED):
        raise CountedVmError(f"vm exited {completed.returncode}")
    return decode(completed.stdout, completed.returncode)


def expected_mul_ops(k):
    if k == 0:
        return 0
    bits = f"{k:b}"
    return (len(bits) - 1) + (bits.count("1") - 1)


def cached_binary(compiler=CC):
    scratch = Path(tempfile.gettempdir()) / f"cairn-countedvm-{source_sha256()[:16]}"
    binary = scratch / "vm"
    if binary.is_file() and os.access(binary, os.X_OK):
        return binary
    scratch.mkdir(parents=True, exist_ok=True)
    return build(compiler, scratch)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "--input":
        print("usage: python -m cairn.countedvm --input FILE", file=sys.stderr)
        return 2
    text = Path(argv[1]).read_text()
    binary = cached_binary()
    completed = subprocess.run(
        [str(binary)], input=text, capture_output=True, text=True, timeout=RUN_TIMEOUT_S, check=False
    )
    sys.stdout.write(completed.stdout)
    sys.stderr.write(completed.stderr)
    return completed.returncode
