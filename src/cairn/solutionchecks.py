import time
from dataclasses import dataclass
from pathlib import Path

from cairn import challenge, cli, container, lean, log, solutionbuild, solutionplan

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
CONTAINER_COMPARATOR_BINARY = "/home/cairn/comparator/.lake/build/bin/comparator"
BUILD = "build"
# The bundle is content-addressed under the operator pin, so an edited lean.json is refused at open;
# these forms keep a re-pinned bundle from swapping the kernel replay or the build for another command.
PINNED_CHECKER_COMMANDS = {
    BUILD: ("lake", "build", "{module}"),
    REPLAY_FRESH: ("lake", "env", "leanchecker", "--fresh", "-v", "{module}"),
}
CHECKER_COMMAND_NOT_PINNED_PREFIX = "checker-command-not-pinned:"


@dataclass(frozen=True)
class PreparedChallenge:
    project: solutionbuild.ChallengeProject
    statement_hash: str
    bundle_hash: str
    pin_hash: str
    renderer_hash: str
    prelude_hash: str
    formal_statement_hash: str
    image: container.Image | None


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


def _observe_fresh_replay(gate, compilation, command, *, timeout_s, start):
    tool, arguments = command
    project, image = compilation.project, compilation.image
    argv = [tool, f"+{gate.lean['toolchain']}", *(part.format(module=project.solution_module) for part in arguments)]
    try:
        result = container.run(
            image.context,
            image.image_id,
            argv,
            user=container.host_user(),
            mounts=((project.root, "/project", "readonly=false"),),
            workdir="/project",
            env=(("HOME", "/project"),),
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
    command = _replay_command(gate)
    axioms = _observe_axiom_step(gate, compilation, work_dir=work_dir, timeout_s=axiom_timeout_s, start=start)
    if axioms[0] != solutionplan.EXPECT_NO_OFFENDING_AXIOM:
        return axioms
    return _observe_fresh_replay(gate, compilation, command, timeout_s=timeout_s, start=start)


def observe_container_comparison(gate, compilation, *, timeout_s=lean.DEFAULT_TIMEOUT_S):
    start = time.monotonic()
    for name, expected in (("bundle_hash", gate.hash), ("pin_hash", gate.pin_hash)):
        if getattr(compilation, name) != expected:
            raise solutionbuild.SolutionRefused(f"container-compilation-mismatch:{name}")
    lean.require_success(compilation.result)
    project, image = compilation.project, compilation.image
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    try:
        container.assert_pinned(gate, image, timeout_s=timeout_s)
        result = container.run(
            image.context,
            image.image_id,
            ["lake", f"+{gate.lean['toolchain']}", "env", CONTAINER_COMPARATOR_BINARY, solutionbuild.CONFIG_NAME],
            user=container.host_user(),
            mounts=((project.root, "/project", "readonly=false"),),
            workdir="/project",
            env=(("HOME", "/project"),),
            timeout_s=timeout_s,
        )
    except lean.LeanTimeout as exc:
        solutionbuild.assert_unchanged(project)
        solutionbuild.assert_dependencies(gate, project)
        raise solutionplan.StepTimeout(solutionplan.KIND_CLOSURE_COMPARISON, exc.timeout_s) from None
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    wall_ms = _elapsed_ms(start)
    lg.info("container_comparison", image_id=image.image_id, result=result.__dict__)
    if result.rc == 0:
        return solutionplan.EXPECT_CLOSURE_MATCHED, (), wall_ms
    reasons = (CLOSURE_MISMATCH, f"rc:{result.rc}", _head(result.stderr) or _head(result.stdout))
    return solutionplan.OBSERVED_REFUSED, reasons, wall_ms


def compile_container(
    gate, image, statement, submission, theorem_names, *, root, prepared, timeout_s=container.RUN_TIMEOUT_S
):
    assert_prepared(gate, statement, theorem_names, prepared, image=image)
    solutionbuild.assert_binding(submission, prepared.formal_statement_hash)
    admission, reasons = solutionplan.check_imports(submission.solution_module)
    if admission != solutionplan.EXPECT_ADMITTED:
        raise solutionbuild.SolutionRefused(",".join(reasons))
    solutionbuild.assert_dependencies(gate, prepared.project)
    project = solutionbuild.assemble_container(
        gate,
        image,
        statement,
        submission,
        theorem_names,
        root=root,
        formal_statement_hash=prepared.formal_statement_hash,
        dependency_project=(prepared.project.root if solutionbuild.MANIFEST_NAME in prepared.project.inputs else None),
        timeout_s=timeout_s,
    )
    tool, arguments = _build_command(gate)
    argv = [tool, f"+{gate.lean['toolchain']}", *(part.format(module=project.solution_module) for part in arguments)]
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    result = container.run(
        image.context,
        image.image_id,
        [*argv, project.challenge_module],
        user=container.host_user(),
        mounts=((project.root, "/project", "readonly=false"),),
        workdir="/project",
        env=(("HOME", "/project"),),
        timeout_s=timeout_s,
    )
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    lg.info(
        "container_compilation",
        module=project.solution_module,
        image_id=image.image_id,
        rc=result.rc,
        wall_ms=result.wall_ms,
    )
    return ContainerCompilation(project, image, result, gate.hash, gate.pin_hash)


def prepare_dev(gate, statement, theorem_names, *, root, dependency_project=None, timeout_s=lean.DEFAULT_TIMEOUT_S):
    if gate.challenge_renderer != challenge.renderer_bytes():
        raise solutionbuild.SolutionRefused("challenge-renderer-mismatch")
    lean.assert_pinned(gate.lean)
    project = solutionbuild.prepare_challenge(
        gate, statement, theorem_names, root=root, dependency_project=dependency_project
    )
    formal_hash = lean.formal_statement_hash(
        gate,
        project.challenge_module,
        list(project.theorem_names),
        project_dir=project.root,
        work_dir=Path(project.root) / "statement-tool",
        timeout_s=timeout_s,
    )
    return _prepared(gate, statement, project, formal_hash, None)


def prepare_container(
    gate, image, statement, theorem_names, *, root, dependency_project=None, timeout_s=container.RUN_TIMEOUT_S
):
    if gate.challenge_renderer != challenge.renderer_bytes():
        raise solutionbuild.SolutionRefused("challenge-renderer-mismatch")
    if image.identity != gate.container_identity or not container.IMAGE_ID_RE.fullmatch(image.image_id):
        raise container.ContainerError("statement-hasher-image-mismatch")
    project = solutionbuild.prepare_challenge(
        gate, statement, theorem_names, root=root, dependency_project=dependency_project
    )
    formal_hash = container.formal_statement_hash(
        gate,
        image,
        project.challenge_module,
        list(project.theorem_names),
        project_dir=project.root,
        work_dir=Path(project.root) / "statement-tool",
        timeout_s=timeout_s,
    )
    return _prepared(gate, statement, project, formal_hash, image)


def _prepared(gate, statement, project, formal_hash, image):
    solutionbuild.assert_unchanged(project)
    solutionbuild.assert_dependencies(gate, project)
    return PreparedChallenge(
        project=project,
        statement_hash=statement.hash,
        bundle_hash=gate.hash,
        pin_hash=gate.pin_hash,
        renderer_hash=gate.digest_of(challenge.RENDERER_KIND),
        prelude_hash=gate.digest_of(challenge.PRELUDE_KIND),
        formal_statement_hash=formal_hash,
        image=image,
    )


def assert_prepared(gate, statement, theorem_names, prepared, *, image=None):
    expected = {
        "statement_hash": statement.hash,
        "bundle_hash": gate.hash,
        "pin_hash": gate.pin_hash,
        "renderer_hash": gate.digest_of(challenge.RENDERER_KIND),
        "prelude_hash": gate.digest_of(challenge.PRELUDE_KIND),
        "image": image,
    }
    for name, value in expected.items():
        if getattr(prepared, name) != value:
            raise solutionbuild.SolutionRefused(f"prepared-challenge-mismatch:{name}")
    if prepared.project.theorem_names != tuple(theorem_names):
        raise solutionbuild.SolutionRefused("prepared-challenge-mismatch:theorem_names")
    if gate.challenge_renderer != challenge.renderer_bytes():
        raise solutionbuild.SolutionRefused("challenge-renderer-mismatch")
    solutionbuild.assert_unchanged(prepared.project)


def run_dev(
    gate,
    statement,
    submission,
    theorem_names,
    plan_rows,
    *,
    sub,
    root,
    prepared,
    comparator,
):
    plan = solutionplan.SolutionPlan.load(plan_rows, arm=container.DEV_ARM)
    if tuple(step.kind for step in plan.steps) != solutionplan.STEP_KINDS:
        raise solutionplan.PlanInvalid("dev-plan-requires-axioms-before-replay")
    assert_checker_commands(gate)
    assembled = None

    def observe(step):
        nonlocal assembled
        start = time.monotonic()
        if step.kind == solutionplan.KIND_STATEMENT_BINDING:
            try:
                assert_prepared(gate, statement, theorem_names, prepared)
            except solutionbuild.SolutionRefused as exc:
                return solutionplan.OBSERVED_REFUSED, (exc.reason,), _elapsed_ms(start)
            return solutionbuild.observe_binding(submission, prepared.formal_statement_hash)
        if step.kind == solutionplan.KIND_IMPORT_ALLOWLIST:
            return (*solutionplan.check_imports(submission.solution_module), _elapsed_ms(start))
        try:
            if step.kind == solutionplan.KIND_BUILD:
                assembled = solutionbuild.assemble(
                    gate,
                    statement,
                    submission,
                    theorem_names,
                    root=root,
                    formal_statement_hash=prepared.formal_statement_hash,
                    dependency_project=(
                        prepared.project.root if solutionbuild.MANIFEST_NAME in prepared.project.inputs else None
                    ),
                )
                return solutionbuild.observe_build(gate, assembled, timeout_s=step.timeout_s)
            assert assembled is not None
            if step.kind == solutionplan.KIND_AXIOMS:
                result = observe_axioms(
                    gate,
                    assembled.solution_module,
                    list(assembled.theorem_names),
                    project_dir=assembled.root,
                    work_dir=Path(assembled.root) / "axiom-tool",
                    timeout_s=step.timeout_s,
                )
            elif step.kind == solutionplan.KIND_KERNEL_REPLAY:
                result = observe_kernel_replay(
                    gate.lean,
                    assembled.solution_module,
                    project_dir=assembled.root,
                    timeout_s=step.timeout_s,
                    variant=REPLAY_FRESH,
                )
            else:
                result = observe_closure_comparison(gate, assembled, comparator=comparator, timeout_s=step.timeout_s)
            solutionbuild.assert_unchanged(assembled)
            return result
        except solutionbuild.SolutionRefused as exc:
            return solutionplan.OBSERVED_REFUSED, (exc.reason,), _elapsed_ms(start)

    return plan.run(
        observe,
        sub,
        bundle_hash=gate.hash,
        pin_hash=gate.pin_hash,
        statement_hash=statement.hash,
        formal_statement_hash=prepared.formal_statement_hash,
        renderer_hash=gate.digest_of(challenge.RENDERER_KIND),
        prelude_hash=gate.digest_of(challenge.PRELUDE_KIND),
        at=cli.now_iso(),
    )


def run_container(gate, image, statement, submission, theorem_names, plan_rows, *, sub, root, work_dir, prepared):
    plan = solutionplan.SolutionPlan.load(plan_rows, arm=container.GOLD_ARM)
    if tuple(step.kind for step in plan.steps) != solutionplan.STEP_KINDS:
        raise solutionplan.PlanInvalid("gold-plan-requires-axioms-before-replay")
    resolved_root, resolved_work = Path(root).resolve(), Path(work_dir).resolve()
    if resolved_work == resolved_root or resolved_work.is_relative_to(resolved_root):
        raise ValueError("work-dir-inside-project-root")
    assert_checker_commands(gate)
    compilation = None

    def observe(step):
        nonlocal compilation
        start = time.monotonic()
        if step.kind == solutionplan.KIND_STATEMENT_BINDING:
            try:
                assert_prepared(gate, statement, theorem_names, prepared, image=image)
            except solutionbuild.SolutionRefused as exc:
                return solutionplan.OBSERVED_REFUSED, (exc.reason,), _elapsed_ms(start)
            return solutionbuild.observe_binding(submission, prepared.formal_statement_hash)
        if step.kind == solutionplan.KIND_IMPORT_ALLOWLIST:
            return (*solutionplan.check_imports(submission.solution_module), _elapsed_ms(start))
        try:
            if step.kind == solutionplan.KIND_BUILD:
                try:
                    compilation = compile_container(
                        gate,
                        image,
                        statement,
                        submission,
                        theorem_names,
                        root=root,
                        prepared=prepared,
                        timeout_s=step.timeout_s,
                    )
                except lean.LeanTimeout as exc:
                    raise solutionplan.StepTimeout(solutionplan.KIND_BUILD, exc.timeout_s) from None
                rc = compilation.result.rc
                if rc != 0:
                    return (
                        solutionbuild.BUILD_FAILED,
                        (f"rc:{rc}", _head(compilation.result.stdout)),
                        _elapsed_ms(start),
                    )
                return solutionplan.EXPECT_BUILT, (), _elapsed_ms(start)
            assert compilation is not None
            if step.kind == solutionplan.KIND_AXIOMS:
                return _observe_axiom_step(gate, compilation, work_dir=work_dir, timeout_s=step.timeout_s, start=start)
            if step.kind == solutionplan.KIND_KERNEL_REPLAY:
                return _observe_fresh_replay(
                    gate, compilation, _replay_command(gate), timeout_s=step.timeout_s, start=start
                )
            return observe_container_comparison(gate, compilation, timeout_s=step.timeout_s)
        except solutionbuild.SolutionRefused as exc:
            return solutionplan.OBSERVED_REFUSED, (exc.reason,), _elapsed_ms(start)

    return plan.run(
        observe,
        sub,
        bundle_hash=gate.hash,
        pin_hash=gate.pin_hash,
        statement_hash=statement.hash,
        formal_statement_hash=prepared.formal_statement_hash,
        renderer_hash=gate.digest_of(challenge.RENDERER_KIND),
        prelude_hash=gate.digest_of(challenge.PRELUDE_KIND),
        at=cli.now_iso(),
    )


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
