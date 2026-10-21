import time
from dataclasses import dataclass

from cairn import container, lean, log, solutionbuild, solutionplan

lg = log.get("solutionchecks")

OFFENDING_AXIOM_PREFIX = "offending-axiom:"
KERNEL_REJECTED = "kernel-rejected"
REPLAY_FRESH = "replay_fresh"
REPLAY_TRUSTING_IMPORTS = "replay"
REPLAY_VARIANTS = (REPLAY_FRESH, REPLAY_TRUSTING_IMPORTS)
AXIOM_STEP_ERROR_PREFIX = "axiom-step-error:"
STDERR_HEAD_CHARS = 200
BUILD = "build"
REPLAY_CHECKER = "leanchecker"
IMAGE_REPLAY_CHECKER = "/home/cairn/lean/bin/leanchecker"
REPLAY_CHECKER_FOREIGN_PREFIX = "replay-checker-not-image:"
REPLAY_CHECKER_UNRESOLVED = "replay-checker-unresolved"
CHECKER_RESOLVE_TIMEOUT_S = 120.0
# The bundle is content-addressed under the operator pin, so an edited lean.json is refused at open;
# these forms keep a re-pinned bundle from swapping the kernel replay or the build for another command.
PINNED_CHECKER_COMMANDS = {
    BUILD: ("lake", "build", "{module}"),
    REPLAY_FRESH: ("lake", "env", REPLAY_CHECKER, "--fresh", "-v", "{module}"),
}
CHECKER_COMMAND_NOT_PINNED_PREFIX = "checker-command-not-pinned:"


@dataclass(frozen=True)
class ContainerCompilation:
    project: solutionbuild.Assembled
    image: container.Image
    result: lean.Run
    bundle_hash: str
    pin_hash: str


def check_container_axioms(gate, compilation, *, work_dir, timeout_s=container.RUN_TIMEOUT_S):
    for name, expected in (("bundle_hash", gate.hash), ("pin_hash", gate.pin_hash)):
        if getattr(compilation, name) != expected:
            raise solutionbuild.SolutionRefused(f"container-compilation-mismatch:{name}")
    lean.require_success(compilation.result)
    project = compilation.project
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    record = container.check_axioms(
        gate,
        compilation.image,
        project.solution_module,
        project.theorem_names,
        project_dir=project.root,
        work_dir=work_dir,
        timeout_s=timeout_s,
    )
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    return record


class CheckerCommandRefused(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


def _pinned_command(gate, key):
    command = gate.lean["checker"][key]
    if not isinstance(command, list) or tuple(command) != PINNED_CHECKER_COMMANDS[key]:
        lg.info("checker_command_refused", key=key, command=command)
        raise CheckerCommandRefused(f"{CHECKER_COMMAND_NOT_PINNED_PREFIX}{key}")
    tool, *arguments = command
    return tool, arguments


def _build_command(gate):
    return _pinned_command(gate, BUILD)


def _replay_command(gate):
    return _pinned_command(gate, REPLAY_FRESH)


def assert_checker_commands(gate):
    _build_command(gate)
    _replay_command(gate)


def _elapsed_ms(start):
    return int((time.monotonic() - start) * 1000)


def _head(text):
    for line in text.splitlines():
        if line.strip():
            return line.strip()[:STDERR_HEAD_CHARS]
    return ""


def _observe_axiom_step(gate, compilation, *, work_dir, timeout_s, start):
    try:
        axioms = check_container_axioms(gate, compilation, work_dir=work_dir, timeout_s=timeout_s)
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_AXIOMS, exc.timeout_s) from None
    except lean.LeanRejected as exc:
        return solutionplan.OBSERVED_REFUSED, (f"{AXIOM_STEP_ERROR_PREFIX}{exc}",), _elapsed_ms(start)
    if axioms["passed"]:
        return solutionplan.EXPECT_NO_OFFENDING_AXIOM, (), _elapsed_ms(start)
    reasons = tuple(f"{OFFENDING_AXIOM_PREFIX}{name}" for name in axioms["offending_axioms"])
    lg.info("container_replay_blocked", reasons=reasons, image_id=compilation.image.image_id)
    return solutionplan.OBSERVED_REFUSED, reasons, _elapsed_ms(start)


def _run_in_project(gate, compilation, argv, timeout_s):
    project, image = compilation.project, compilation.image
    try:
        return container.run(
            image.context,
            image.image_id,
            argv,
            user=container.host_user(),
            mounts=((project.root, "/project", "readonly=false"),),
            workdir="/project",
            env=(("HOME", "/project"),),
            timeout_s=timeout_s,
        )
    except lean.LeanTimeout:
        solutionbuild.assert_unchanged(project)
        solutionbuild.assert_dependencies(gate, project)
        raise


def _foreign_checker(gate, compilation, tool):
    argv = [tool, f"+{gate.lean['toolchain']}", "env", "/bin/sh", "-c", f"command -v {REPLAY_CHECKER}"]
    resolved = _run_in_project(gate, compilation, argv, CHECKER_RESOLVE_TIMEOUT_S)
    path = resolved.stdout.strip()
    if resolved.rc != 0 or not path:
        return REPLAY_CHECKER_UNRESOLVED
    if path != IMAGE_REPLAY_CHECKER:
        return f"{REPLAY_CHECKER_FOREIGN_PREFIX}{path}"
    return None


def _observe_fresh_replay(gate, compilation, command, *, timeout_s, start):
    tool, arguments = command
    project, image = compilation.project, compilation.image
    argv = [tool, f"+{gate.lean['toolchain']}", *(part.format(module=project.solution_module) for part in arguments)]
    try:
        foreign = _foreign_checker(gate, compilation, tool)
        if foreign is not None:
            solutionbuild.assert_unchanged(project)
            solutionbuild.assert_dependencies(gate, project)
            lg.info("container_kernel_replay_refused", module=project.solution_module, reason=foreign)
            return solutionplan.OBSERVED_REFUSED, (foreign,), _elapsed_ms(start)
        result = _run_in_project(gate, compilation, argv, timeout_s)
    except lean.LeanTimeout as exc:
        raise solutionplan.StepTimeout(solutionplan.KIND_KERNEL_REPLAY, exc.timeout_s) from None
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    wall_ms = _elapsed_ms(start)
    lg.info("container_kernel_replay", module=project.solution_module, image_id=image.image_id, result=result.__dict__)
    if result.rc == 0:
        return solutionplan.EXPECT_REPLAYED, (), wall_ms
    reasons = (KERNEL_REJECTED, f"rc:{result.rc}", _head(result.stderr) or _head(result.stdout))
    return solutionplan.OBSERVED_REFUSED, reasons, wall_ms


def observe_container_replay(
    gate, compilation, *, work_dir, timeout_s=lean.DEFAULT_TIMEOUT_S, axiom_timeout_s=container.RUN_TIMEOUT_S
):
    start = time.monotonic()
    command = _replay_command(gate)
    axioms = _observe_axiom_step(gate, compilation, work_dir=work_dir, timeout_s=axiom_timeout_s, start=start)
    if axioms[0] != solutionplan.EXPECT_NO_OFFENDING_AXIOM:
        return axioms
    return _observe_fresh_replay(gate, compilation, command, timeout_s=timeout_s, start=start)
