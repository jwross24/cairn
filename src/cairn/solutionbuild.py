import json
import time
from dataclasses import dataclass
from pathlib import Path

from cairn import canon, challenge, lean, log, solutionplan
from cairn.substrate import blob_hash

lg = log.get("solutionbuild")

MODULE_PREFIX = "Solution.S_"
HASH_CHARS = 16
SOLUTION_DIR = "Solution"
CHALLENGE_DIR = "Challenge"
TOOLCHAIN_NAME = "lean-toolchain"
LAKEFILE_NAME = "lakefile.toml"
CONFIG_NAME = "config.json"
LAKEFILE = (
    'name = "cairn_solution"\n\n'
    '[[lean_lib]]\nname = "Challenge"\nglobs = ["Challenge.+"]\n\n'
    '[[lean_lib]]\nname = "Solution"\nglobs = ["Solution.+"]\n'
)
FINGERPRINT_DOMAIN = "cairn/solution-inputs/v1"
STATEMENT_HASH_MISMATCH = "statement-hash-mismatch"
BUILD_FAILED = "build-failed"
STDOUT_HEAD_CHARS = 200
EMPTY_SOLUTION = "solution-module-empty"
EMPTY_THEOREM_NAMES = "empty-theorem-names"


class SolutionRefused(RuntimeError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class InputsChanged(SolutionRefused):
    def __init__(self, paths):
        super().__init__("solution-inputs-changed:" + ",".join(paths))
        self.paths = tuple(paths)


@dataclass(frozen=True)
class Assembled:
    root: str
    challenge_module: str
    solution_module: str
    formal_statement_hash: str
    theorem_names: tuple
    inputs: tuple
    input_hashes: tuple
    fingerprint: str


def module_name(formal_statement_hash):
    return f"{MODULE_PREFIX}{formal_statement_hash[:HASH_CHARS]}"


def module_path(formal_statement_hash, root):
    return Path(root) / SOLUTION_DIR / f"S_{formal_statement_hash[:HASH_CHARS]}.lean"


def assert_binding(submission, formal_statement_hash):
    if submission.formal_statement_hash != formal_statement_hash:
        lg.info(
            "statement_hash_mismatch",
            submitted=submission.formal_statement_hash,
            challenge=formal_statement_hash,
        )
        raise SolutionRefused(f"{STATEMENT_HASH_MISMATCH}:{submission.formal_statement_hash}")


def observe_binding(submission, formal_statement_hash):
    start = time.perf_counter()
    try:
        assert_binding(submission, formal_statement_hash)
    except SolutionRefused as exc:
        return solutionplan.OBSERVED_REFUSED, (exc.reason,), round((time.perf_counter() - start) * 1000)
    return solutionplan.EXPECT_BOUND, (), round((time.perf_counter() - start) * 1000)


def fingerprint(root, inputs):
    root = Path(root)
    rows = []
    for relative in inputs:
        path = root / relative
        if not path.is_file():
            raise InputsChanged([relative])
        rows.append(canon.length_prefix(relative.encode()) + canon.length_prefix(blob_hash(path.read_bytes()).encode()))
    return canon.digest(FINGERPRINT_DOMAIN, canon.length_prefix(b"".join(rows)))


def assert_unchanged(assembled):
    root = Path(assembled.root)
    changed = []
    for relative, digest in zip(assembled.inputs, assembled.input_hashes, strict=True):
        path = root / relative
        if not path.is_file() or blob_hash(path.read_bytes()) != digest:
            changed.append(relative)
    if changed:
        lg.info("inputs_changed", root=assembled.root, paths=changed)
        raise InputsChanged(sorted(changed))


def config(challenge_module, solution_module, theorem_names, pins):
    return {
        "challenge_module": challenge_module,
        "solution_module": solution_module,
        "theorem_names": list(theorem_names),
        "permitted_axioms": list(pins["permitted_axioms"]),
        "enable_nanoda": False,
    }


def assemble(gate, statement, submission, theorem_names, *, root, formal_statement_hash):
    pins = gate.lean
    lean.assert_pinned(pins)
    assert_binding(submission, formal_statement_hash)
    if not submission.solution_module:
        raise SolutionRefused(EMPTY_SOLUTION)
    if not theorem_names:
        raise SolutionRefused(EMPTY_THEOREM_NAMES)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=False)
    (root / CHALLENGE_DIR).mkdir()
    (root / SOLUTION_DIR).mkdir()
    (root / TOOLCHAIN_NAME).write_text(pins["toolchain"] + "\n")
    (root / LAKEFILE_NAME).write_text(LAKEFILE)
    challenge_source = challenge.render(statement, gate.raw(challenge.PRELUDE_KIND))
    challenge_path = challenge.module_path(statement, root / CHALLENGE_DIR)
    challenge_path.write_bytes(challenge_source)
    solution_path = module_path(formal_statement_hash, root)
    solution_path.write_bytes(submission.solution_module)
    challenge_module = challenge.module_name(statement)
    solution_module = module_name(formal_statement_hash)
    config_path = root / CONFIG_NAME
    config_path.write_text(
        json.dumps(config(challenge_module, solution_module, theorem_names, pins), sort_keys=True, indent=2) + "\n"
    )
    inputs = tuple(
        str(path.relative_to(root))
        for path in (root / TOOLCHAIN_NAME, root / LAKEFILE_NAME, config_path, challenge_path, solution_path)
    )
    assembled = Assembled(
        root=str(root),
        challenge_module=challenge_module,
        solution_module=solution_module,
        formal_statement_hash=formal_statement_hash,
        theorem_names=tuple(theorem_names),
        inputs=inputs,
        input_hashes=tuple(blob_hash((root / relative).read_bytes()) for relative in inputs),
        fingerprint=fingerprint(root, inputs),
    )
    lg.info(
        "assembled",
        root=assembled.root,
        challenge_module=assembled.challenge_module,
        solution_module=assembled.solution_module,
        fingerprint=assembled.fingerprint,
    )
    return assembled


def observe_build(gate, assembled, *, timeout_s=lean.DEFAULT_TIMEOUT_S):
    try:
        result = build(gate, assembled, timeout_s=timeout_s)
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_BUILD, exc.timeout_s) from None
    try:
        assert_unchanged(assembled)
    except InputsChanged as exc:
        return solutionplan.OBSERVED_REFUSED, (exc.reason,), result.wall_ms
    if result.rc != 0:
        return BUILD_FAILED, (f"rc:{result.rc}", _head(result.stdout)), result.wall_ms
    return solutionplan.EXPECT_BUILT, (), result.wall_ms


def _head(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:STDOUT_HEAD_CHARS]
    return ""


def build(gate, assembled, *, timeout_s=lean.DEFAULT_TIMEOUT_S):
    pins = gate.lean
    result = lean.run_argv(
        lean.command(pins, "build", module=assembled.solution_module),
        cwd=assembled.root,
        timeout_s=timeout_s,
    )
    lg.info(
        "build",
        module=assembled.solution_module,
        rc=result.rc,
        wall_ms=result.wall_ms,
        stderr=result.stderr[-400:],
    )
    return result
