import re
from dataclasses import dataclass

from cairn import container, log
from cairn.gateplan import BLOCKED_PREFIX, MISMATCH_REASON, RESULT_BLOCKED, RESULT_FAIL, RESULT_PASS

lg = log.get("solutionplan")

GATE = "solution_plan"

KIND_IMPORT_ALLOWLIST = "import_allowlist"
KIND_BUILD = "build"
KIND_AXIOMS = "axiom_computation"
KIND_KERNEL_REPLAY = "kernel_replay"
STEP_KINDS = (KIND_IMPORT_ALLOWLIST, KIND_BUILD, KIND_AXIOMS, KIND_KERNEL_REPLAY)

# An axiom carries no proof for the kernel to replay and a forged unchecked theorem is invisible to
# the axiom computation, so neither step sees the other's forgery and a plan carrying one is open to
# the forgery the other catches (research/grounding/solution-forgery-2026-09-08/probe.log).
CHECKER_KINDS = (KIND_AXIOMS, KIND_KERNEL_REPLAY)
MANDATORY_KINDS = (KIND_IMPORT_ALLOWLIST, KIND_BUILD, *CHECKER_KINDS)

RESULT_TIMEOUT = "timeout"
RESULTS = (RESULT_PASS, RESULT_FAIL, RESULT_TIMEOUT, RESULT_BLOCKED)

EXPECT_ADMITTED = "admitted"
EXPECT_BUILT = "built"
EXPECT_NO_OFFENDING_AXIOM = "no-offending-axiom"
EXPECT_REPLAYED = "replayed"
EXPECTATIONS = (EXPECT_ADMITTED, EXPECT_BUILT, EXPECT_NO_OFFENDING_AXIOM, EXPECT_REPLAYED)

KIND_EXPECTATION = {
    KIND_IMPORT_ALLOWLIST: EXPECT_ADMITTED,
    KIND_BUILD: EXPECT_BUILT,
    KIND_AXIOMS: EXPECT_NO_OFFENDING_AXIOM,
    KIND_KERNEL_REPLAY: EXPECT_REPLAYED,
}

TIMEOUT_REASON = "step-timeout"
STEP_FIELDS = ("step", "kind", "expect", "blocking", "timeout_s")


class PlanInvalid(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Step:
    step: str
    kind: str
    expect: str
    blocking: bool
    timeout_s: float


@dataclass(frozen=True)
class StepResult:
    step: str
    kind: str
    expected: str
    observed: str
    result: str
    reasons: tuple
    wall_ms: int


@dataclass(frozen=True)
class PlanResult:
    steps: tuple
    arm: str

    @property
    def ok(self):
        return all(step.result == RESULT_PASS for step in self.steps)

    @property
    def first_failure(self):
        for step in self.steps:
            if step.result in (RESULT_FAIL, RESULT_TIMEOUT):
                return step
        return None


class SolutionPlan:
    def __init__(self, steps, arm):
        self.steps = tuple(steps)
        self.arm = arm

    @classmethod
    def load(cls, plan_rows, *, arm):
        container.assert_arm(arm)
        if not isinstance(plan_rows, list):
            raise PlanInvalid(f"plan-not-a-list:{type(plan_rows).__name__}")
        if not plan_rows:
            raise PlanInvalid("plan-empty")
        steps = [_step_at(index, row) for index, row in enumerate(plan_rows)]
        names = set()
        for index, step in enumerate(steps):
            if step.step in names:
                raise PlanInvalid(f"duplicate-step-name:{index}.{step.step}")
            names.add(step.step)
        _assert_every_mandatory_kind(steps)
        _assert_canonical_order(steps)
        return cls(steps, arm)

    def run(self, observe):
        results = []
        for step, observed, result, reasons, wall_ms in plan_outcomes(self.steps, observe):
            lg.info(
                "step",
                step=step.step,
                kind=step.kind,
                expected=step.expect,
                observed=observed,
                result=result,
                reasons=list(reasons),
                wall_ms=wall_ms,
                arm=self.arm,
            )
            results.append(StepResult(step.step, step.kind, step.expect, observed, result, reasons, wall_ms))
        return PlanResult(tuple(results), self.arm)


class ImportsUnparsable(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class StepTimeout(RuntimeError):
    def __init__(self, step, timeout_s):
        super().__init__(f"step {step} exceeded {timeout_s}s")
        self.step = step
        self.timeout_s = timeout_s


def plan_outcomes(steps, observe):
    blocker = None
    for step in steps:
        if blocker is not None:
            yield step, RESULT_BLOCKED, RESULT_BLOCKED, (f"{BLOCKED_PREFIX}{blocker}",), 0
            continue
        try:
            observed, extra, wall_ms = observe(step)
        except StepTimeout as exc:
            yield step, RESULT_TIMEOUT, RESULT_TIMEOUT, (TIMEOUT_REASON, f"timeout_s:{exc.timeout_s}"), 0
            if step.blocking:
                blocker = step.step
            continue
        if observed == step.expect:
            yield step, observed, RESULT_PASS, tuple(extra), wall_ms
            continue
        yield step, observed, RESULT_FAIL, (MISMATCH_REASON, f"observed:{observed}", *tuple(extra)), wall_ms
        if step.blocking:
            blocker = step.step


def _step_at(index, row):
    if not isinstance(row, dict):
        raise PlanInvalid(f"step-not-a-mapping:{index}.{type(row).__name__}")
    for field in STEP_FIELDS:
        if field not in row:
            raise PlanInvalid(f"step-missing-field:{index}.{field}")
    for key in sorted(row):
        if key not in STEP_FIELDS:
            raise PlanInvalid(f"unknown-step-field:{index}.{key!r}")
    if not isinstance(row["step"], str) or row["step"] == "":
        raise PlanInvalid(f"step-name-not-a-string:{index}")
    if row["kind"] not in STEP_KINDS:
        raise PlanInvalid(f"unknown-step-kind:{index}.{row['kind']!r}")
    if row["expect"] not in EXPECTATIONS:
        raise PlanInvalid(f"expect-outside-vocabulary:{index}.{row['expect']!r}")
    if row["expect"] != KIND_EXPECTATION[row["kind"]]:
        raise PlanInvalid(f"expect-not-this-kind:{index}.{row['kind']}.{row['expect']}")
    if not isinstance(row["blocking"], bool):
        raise PlanInvalid(f"step-field-wrong-type:{index}.blocking")
    if not isinstance(row["timeout_s"], (int, float)) or isinstance(row["timeout_s"], bool) or row["timeout_s"] <= 0:
        raise PlanInvalid(f"step-field-wrong-type:{index}.timeout_s")
    return Step(
        step=row["step"],
        kind=row["kind"],
        expect=row["expect"],
        blocking=row["blocking"],
        timeout_s=float(row["timeout_s"]),
    )


def _assert_every_mandatory_kind(steps):
    present = set()
    for step in steps:
        if step.kind in present:
            raise PlanInvalid(f"duplicate-step-kind:{step.kind}")
        present.add(step.kind)
    missing_checkers = [kind for kind in CHECKER_KINDS if kind not in present]
    if len(missing_checkers) == 1:
        raise PlanInvalid(f"checker-steps-are-a-pair:missing:{missing_checkers[0]}")
    for kind in MANDATORY_KINDS:
        if kind not in present:
            raise PlanInvalid(f"missing-mandatory-step:{kind}")
    for step in steps:
        if step.kind in MANDATORY_KINDS and not step.blocking:
            raise PlanInvalid(f"mandatory-step-not-blocking:{step.step}")


def _assert_canonical_order(steps):
    positions = {step.kind: index for index, step in enumerate(steps)}
    if positions[KIND_IMPORT_ALLOWLIST] > positions[KIND_BUILD]:
        raise PlanInvalid("import-allowlist-after-build")
    for kind in CHECKER_KINDS:
        if positions[kind] < positions[KIND_BUILD]:
            raise PlanInvalid(f"checker-before-build:{kind}")


ADMITTED_ROOTS = ("Mathlib", "Challenge")
IMPORT_REFUSED_PREFIX = "import-refused:"
UNDECODABLE_SOURCE = "solution-source-not-utf8"
UNPARSABLE_IMPORT_PREFIX = "unparsable-import:"
UNTERMINATED_COMMENT = "unterminated-block-comment"
OBSERVED_REFUSED = "refused"

MODULE_COMPONENT = re.compile(r"\A[A-Za-z_][A-Za-z0-9_'!?]*\Z")


def module_admitted(name):
    root, _, _ = name.partition(".")
    return root in ADMITTED_ROOTS


def imported_modules(text):
    names = []
    depth = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        line, depth = _strip_comments(raw, depth)
        stripped = line.strip()
        if not stripped.startswith("import"):
            continue
        rest = stripped[len("import") :]
        if rest[:1] not in (" ", "\t"):
            continue
        name = rest.strip()
        parts = name.split(".")
        if not name or any(not MODULE_COMPONENT.fullmatch(part) for part in parts):
            raise ImportsUnparsable(f"{UNPARSABLE_IMPORT_PREFIX}{number}")
        names.append(name)
    if depth != 0:
        raise ImportsUnparsable(UNTERMINATED_COMMENT)
    return tuple(names)


def _strip_comments(raw, depth):
    out = []
    index = 0
    while index < len(raw):
        pair = raw[index : index + 2]
        if depth == 0 and pair == "--":
            break
        if pair == "/-":
            depth += 1
            index += 2
            continue
        if pair == "-/" and depth > 0:
            depth -= 1
            index += 2
            continue
        if depth == 0:
            out.append(raw[index])
        index += 1
    return "".join(out), depth


def check_imports(source):
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return OBSERVED_REFUSED, (UNDECODABLE_SOURCE,)
    try:
        names = imported_modules(text)
    except ImportsUnparsable as exc:
        return OBSERVED_REFUSED, (exc.reason,)
    refused = tuple(f"{IMPORT_REFUSED_PREFIX}{name}" for name in names if not module_admitted(name))
    if refused:
        lg.info("imports_refused", refused=list(refused), imported=list(names))
        return OBSERVED_REFUSED, refused
    return EXPECT_ADMITTED, ()
