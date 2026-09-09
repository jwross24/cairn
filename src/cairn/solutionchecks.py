import time

from cairn import lean, log, solutionplan

lg = log.get("solutionchecks")

OFFENDING_AXIOM_PREFIX = "offending-axiom:"
KERNEL_REJECTED = "kernel-rejected"
REPLAY_FRESH = "replay_fresh"
REPLAY_TRUSTING_IMPORTS = "replay"
REPLAY_VARIANTS = (REPLAY_FRESH, REPLAY_TRUSTING_IMPORTS)
AXIOM_STEP_ERROR_PREFIX = "axiom-step-error:"
STDERR_HEAD_CHARS = 200


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
