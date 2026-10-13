import annotationlib
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from cairn import runner
from cairn.substrate import blob_hash

SOURCE = Path(__file__).resolve().with_name("vm.c")
REPO_ROOT = Path(__file__).resolve().parents[3]
CC = Path("/usr/bin/clang")
CFLAGS = ("-O2", "-std=c11", "-Wall", "-Wextra")
RUN_TIMEOUT_S = 120
STATUS_OK = "OK"
STATUS_REFUSED = "REFUSED"
EXIT_INPUT_REFUSED = 2
EXIT_PROGRAM_REFUSED = 3
INSTRUCTION_SETS = {"plain/1", "signed/1"}
OUTPUT_KEYS = {
    "status",
    "sandbox",
    "instruction_set",
    "count",
    "executed",
    "result",
    "p0",
    "i0",
    "table_rows",
    "table_bytes",
    "program_bytes",
    "program_lines",
}
SANDBOX_PURE_COMPUTATION = "pure-computation"
SANDBOX_SECCOMP = "seccomp-stdio-anonymous-memory"
SANDBOX_NONE = "none"
SANDBOX_REQUIRED = {"darwin": SANDBOX_PURE_COMPUTATION, "linux": SANDBOX_SECCOMP}
REFUSAL_KEYS = ({"status", "reason"}, {"status", "reason", "count", "executed"})
GENERATOR_CONTRACT_REFUSAL = "generator_contract_violation"
GENERATOR_INPUT_KEYS = {"n", "seed", "bounds"}
CURVE_INPUT_KEYS = {"p", "a", "b", "P", "Q"}
COUNTING_CONVENTION = {
    "addp": "one group op, whatever the operands; an add that reaches the doubling formula is still one op",
    "dblp": "one group op, whatever the operand",
    "negp": "not a group op",
    "canonicalp": "signed/1 only; smaller-y representative and flip bit; not a group op",
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
    sandbox: str | None = None
    instruction_set: str | None = None
    table_rows: int | None = None
    table_bytes: int | None = None
    program_bytes: int | None = None
    program_lines: int | None = None


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


def document(instance, program, budget, *, instruction_set="plain/1"):
    lines = [
        f"p {instance.p}",
        f"a {instance.a}",
        f"b {instance.b}",
        f"n {instance.n}",
        _point_line("P", instance.P),
        _point_line("Q", instance.Q),
        f"budget {budget}",
        f"instruction_set {instruction_set}",
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
        if type(payload["instruction_set"]) is not str or payload["instruction_set"] not in INSTRUCTION_SETS:
            raise CountedVmError("vm instruction_set must name a supported version")
        for key in ("count", "executed", "table_rows", "table_bytes", "program_bytes", "program_lines"):
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
            payload["sandbox"],
            payload["instruction_set"],
            payload["table_rows"],
            payload["table_bytes"],
            payload["program_bytes"],
            payload["program_lines"],
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


def run(binary, instance, program, budget, *, instruction_set="plain/1"):
    completed = subprocess.run(
        [str(binary)],
        input=document(instance, program, budget, instruction_set=instruction_set),
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


class LaunchRefused(CountedVmError):
    def __init__(self, reason, detail=""):
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason


@dataclass(frozen=True)
class VmLaunch:
    attempt_id: str
    outcome: Outcome
    program_digest: str
    instance_hash: str
    binary_digest: str
    stdout_digest: str
    argv: tuple
    cpu_user_s: float
    cpu_sys_s: float
    wall_s: float
    peak_rss_bytes: int
    measurement_scope: str
    binding: str


def file_digest(path):
    return blob_hash(Path(path).read_bytes())


def instance_hash(instance):
    lines = [
        f"p {instance.p}",
        f"a {instance.a}",
        f"b {instance.b}",
        f"n {instance.n}",
        _point_line("P", instance.P),
        _point_line("Q", instance.Q),
    ]
    return blob_hash("\n".join(lines).encode("ascii"))


def _binding(fields):
    return blob_hash(json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8"))


def launch(
    binary,
    expected_binary_digest,
    instance,
    program,
    budget,
    *,
    attempt_id,
    scratch_dir,
    wall_cap_s=None,
    instruction_set="plain/1",
):
    binary = Path(binary)
    binary_digest = file_digest(binary)
    if binary_digest != expected_binary_digest:
        raise LaunchRefused("binary_digest_mismatch", f"{binary_digest} != {expected_binary_digest}")
    scratch_dir = Path(scratch_dir)
    scratch_dir.mkdir(parents=True, exist_ok=True)
    out_path, err_path = scratch_dir / "stdout", scratch_dir / "stderr"
    stdin_bytes = document(instance, program, budget, instruction_set=instruction_set).encode("ascii")
    ran = runner.spawn_and_wait(
        [str(binary)],
        out_path,
        err_path,
        wall_cap_s=RUN_TIMEOUT_S if wall_cap_s is None else wall_cap_s,
        env=runner.child_env(),
        stdin_bytes=stdin_bytes,
    )
    stdout_bytes, stderr_bytes = out_path.read_bytes(), err_path.read_bytes()
    if ran.timed_out:
        raise LaunchRefused("wall_cap_exceeded")
    if ran.argv != (str(binary),):
        raise LaunchRefused("argv_not_direct", repr(ran.argv))
    if stderr_bytes:
        raise LaunchRefused("vm_stderr", stderr_bytes.decode("utf-8", "replace").strip())
    if ran.exit_status not in (0, EXIT_INPUT_REFUSED, EXIT_PROGRAM_REFUSED):
        raise LaunchRefused("vm_exit", str(ran.exit_status))
    try:
        outcome = decode(stdout_bytes.decode("utf-8"), ran.exit_status)
    except (CountedVmError, UnicodeDecodeError) as exc:
        raise LaunchRefused("output_not_protocol", str(exc)) from exc
    required = SANDBOX_REQUIRED.get(sys.platform)
    if outcome.status == STATUS_OK and outcome.instruction_set != instruction_set:
        raise LaunchRefused("instruction_set_mismatch", f"{outcome.instruction_set!r} != {instruction_set!r}")
    if outcome.status == STATUS_OK and required is not None and outcome.sandbox != required:
        raise LaunchRefused("containment_missing", f"{outcome.sandbox!r} != {required!r}")
    program_digest = blob_hash(program.encode("utf-8"))
    inst_hash = instance_hash(instance)
    stdout_digest = blob_hash(stdout_bytes)
    binding = _binding(
        {
            "attempt_id": attempt_id,
            "binary_digest": binary_digest,
            "instance_hash": inst_hash,
            "program_digest": program_digest,
            "budget": budget,
            "stdout_digest": stdout_digest,
            "count": outcome.count,
            "result": outcome.result,
        }
    )
    return VmLaunch(
        attempt_id,
        outcome,
        program_digest,
        inst_hash,
        binary_digest,
        stdout_digest,
        ran.argv,
        ran.cpu_user_s,
        ran.cpu_sys_s,
        ran.wall_s,
        ran.peak_rss_bytes,
        ran.measurement_scope,
        binding,
    )


def _check_generator_contract(generator, call_arguments, extra):
    if extra or set(call_arguments) != GENERATOR_INPUT_KEYS:
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, "generator receives only n, seed, bounds")
    bounds = call_arguments["bounds"]
    if not isinstance(bounds, Mapping):
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, "bounds must be a mapping")
    bounds = dict(bounds)
    if any(type(key) is not str or key in CURVE_INPUT_KEYS or type(value) is not int for key, value in bounds.items()):
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, "bounds must contain named integer bounds without curve fields")
    call_arguments["bounds"] = bounds
    if type(call_arguments["seed"]) is not int:
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, "seed must be an integer")
    try:
        signature = inspect.signature(generator, annotation_format=annotationlib.Format.STRING)
        signature.bind(**call_arguments)
    except (TypeError, ValueError) as exc:
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, str(exc)) from exc


def generate_and_launch(
    binary,
    expected_binary_digest,
    instance,
    generator,
    budget,
    *,
    seed,
    bounds,
    attempt_id,
    scratch_dir,
    wall_cap_s=None,
    instruction_set="plain/1",
    **extra,
):
    call_arguments = {"n": instance.n, "seed": seed, "bounds": bounds, **extra}
    _check_generator_contract(generator, call_arguments, extra)
    program = generator(**call_arguments)
    if type(program) is not str:
        raise LaunchRefused(GENERATOR_CONTRACT_REFUSAL, "generator must return program text")
    return launch(
        binary,
        expected_binary_digest,
        instance,
        program,
        budget,
        attempt_id=attempt_id,
        scratch_dir=scratch_dir,
        wall_cap_s=wall_cap_s,
        instruction_set=instruction_set,
    )


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
