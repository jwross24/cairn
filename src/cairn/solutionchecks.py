import time
from pathlib import Path

from cairn import lean, log, solutionbuild, solutionplan

lg = log.get("solutionchecks")

OFFENDING_AXIOM_PREFIX = "offending-axiom:"
KERNEL_REJECTED = "kernel-rejected"
REPLAY_FRESH = "replay_fresh"
REPLAY_TRUSTING_IMPORTS = "replay"
REPLAY_VARIANTS = (REPLAY_FRESH, REPLAY_TRUSTING_IMPORTS)
AXIOM_STEP_ERROR_PREFIX = "axiom-step-error:"
STDERR_HEAD_CHARS = 200
COMPARATOR_ABSENT_PREFIX = "comparator-binary-absent:"
CLOSURE_MISMATCH = "closure-mismatch"
COMPARATOR_RELATIVE_BINARY = Path(".lake") / "build" / "bin" / "comparator"


def _elapsed_ms(start):
    return int((time.monotonic() - start) * 1000)


def _head(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:STDERR_HEAD_CHARS]
    return ""


def observe_axioms(gate, module, theorem_names, *, project_dir, timeout_s, work_dir=None, tool=None):
    start = time.monotonic()
    try:
        record = lean.check_axioms(
            gate,
            module,
            theorem_names,
            project_dir=project_dir,
            work_dir=work_dir,
            tool=tool,
            timeout_s=timeout_s,
        )
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_AXIOMS, exc.timeout_s) from None
    except lean.LeanRejected as exc:
        return solutionplan.OBSERVED_REFUSED, (f"{AXIOM_STEP_ERROR_PREFIX}{exc}",), _elapsed_ms(start)
    if record["passed"]:
        return solutionplan.EXPECT_NO_OFFENDING_AXIOM, (), _elapsed_ms(start)
    reasons = tuple(f"{OFFENDING_AXIOM_PREFIX}{name}" for name in record["offending_axioms"])
    lg.info("axioms_refused", module=module, reasons=list(reasons))
    return solutionplan.OBSERVED_REFUSED, reasons, _elapsed_ms(start)


def observe_kernel_replay(pins, module, *, project_dir, timeout_s, variant=REPLAY_FRESH):
    if variant not in REPLAY_VARIANTS:
        raise ValueError(f"{variant!r} is not a kernel replay variant; choose from {REPLAY_VARIANTS}")
    start = time.monotonic()
    try:
        result = lean.run_argv(lean.command(pins, variant, module=module), cwd=project_dir, timeout_s=timeout_s)
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_KERNEL_REPLAY, exc.timeout_s) from None
    wall_ms = _elapsed_ms(start)
    if result.rc == 0:
        return solutionplan.EXPECT_REPLAYED, (), wall_ms
    reasons = (KERNEL_REJECTED, f"rc:{result.rc}", _head(result.stderr) or _head(result.stdout))
    lg.info("replay_refused", module=module, reasons=list(reasons))
    return solutionplan.OBSERVED_REFUSED, reasons, wall_ms


def comparator_binary(checkout):
    return Path(checkout) / COMPARATOR_RELATIVE_BINARY


def comparator_argv(pins, binary):
    return lean.argv(pins, "lake", "env", str(binary), solutionbuild.CONFIG_NAME)


def observe_closure_comparison(gate, assembled, *, comparator, timeout_s):
    start = time.monotonic()
    binary = Path(comparator)
    if not binary.is_file():
        lg.info("comparator_absent", binary=str(binary))
        return solutionplan.OBSERVED_REFUSED, (f"{COMPARATOR_ABSENT_PREFIX}{binary}",), _elapsed_ms(start)
    try:
        result = lean.run_argv(comparator_argv(gate.lean, binary), cwd=assembled.root, timeout_s=timeout_s)
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_CLOSURE_COMPARISON, exc.timeout_s) from None
    wall_ms = _elapsed_ms(start)
    try:
        solutionbuild.assert_unchanged(assembled)
    except solutionbuild.InputsChanged as exc:
        return solutionplan.OBSERVED_REFUSED, (exc.reason,), wall_ms
    if result.rc == 0:
        return solutionplan.EXPECT_CLOSURE_MATCHED, (), wall_ms
    reasons = (CLOSURE_MISMATCH, f"rc:{result.rc}", _head(result.stdout) or _head(result.stderr))
    lg.info("comparison_refused", module=assembled.solution_module, reasons=list(reasons))
    return solutionplan.OBSERVED_REFUSED, reasons, wall_ms
