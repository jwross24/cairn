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
IMAGE_REPLAY_CHECKER = container.PINNED_IMAGE_COMMANDS[REPLAY_FRESH][0]
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
        packages=solutionbuild.dependency_names(gate, project),
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
    for key in container.PINNED_IMAGE_COMMANDS:
        try:
            container.assert_image_command(gate, key)
        except container.ContainerError:
            raise CheckerCommandRefused(f"{CHECKER_COMMAND_NOT_PINNED_PREFIX}image_checker.{key}") from None


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


def _observe_fresh_replay(gate, compilation, *, timeout_s, start):
    project, image = compilation.project, compilation.image
    argv = container.image_command(gate, REPLAY_FRESH, module=project.solution_module)
    try:
        result = container.run(
            image.context,
            image.image_id,
            argv,
            user=container.host_user(),
            mounts=((project.root, container.PROJECT_GUEST, "readonly=true"),),
            workdir=container.PROJECT_GUEST,
            env=container.image_search_env(solutionbuild.dependency_names(gate, project)),
            timeout_s=timeout_s,
        )
    except lean.LeanTimeout as exc:
        solutionbuild.assert_unchanged(project)
        solutionbuild.assert_dependencies(gate, project)
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
    assert_checker_commands(gate)
    axioms = _observe_axiom_step(gate, compilation, work_dir=work_dir, timeout_s=axiom_timeout_s, start=start)
    if axioms[0] != solutionplan.EXPECT_NO_OFFENDING_AXIOM:
        return axioms
    return _observe_fresh_replay(gate, compilation, timeout_s=timeout_s, start=start)
