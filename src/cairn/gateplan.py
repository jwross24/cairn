import dataclasses
import time
from dataclasses import dataclass
from pathlib import Path

from cairn import attest, bundle, claims, cli, exits, kat, keys, log, tiergate, verifier
from cairn.errors import CliError
from cairn.profile import CostProfile, Production, SizeCost, Verification
from cairn.substrate import blob_hash

lg = log.get("gateplan")

GATE = "gate_plan"

KIND_CANON_KAT = "canon_kat"
KIND_VERIFIER = "verifier"
KIND_WAIVER = "waiver_cannot_advance"
KIND_TIER_GATE = "tier_gate"
STEP_KINDS = (KIND_CANON_KAT, KIND_VERIFIER, KIND_WAIVER, KIND_TIER_GATE)

REQUIRED_STEPS = (
    "canon_kat",
    "verifier_selftest_pass",
    "verifier_selftest_fail_xP_ne_Q",
    "verifier_selftest_crash",
    "verifier_selftest_crash_control",
)

EXPECT_PASS = "pass"
EXPECT_OK = "OK"
EXPECT_FAIL_XP_NE_Q = "FAIL xP-ne-Q"
EXPECT_FAIL_BACKEND_CRASH = "FAIL backend-crash"
EXPECT_NO_TICKET = "no-ticket"
EXPECT_TIER_TWO_ABOVE = "TierRefused(tier-two-above)"
EXPECTATIONS = (
    EXPECT_PASS,
    EXPECT_OK,
    EXPECT_FAIL_XP_NE_Q,
    EXPECT_FAIL_BACKEND_CRASH,
    EXPECT_NO_TICKET,
    EXPECT_TIER_TWO_ABOVE,
)

ENTRY_VERIFY = "verify"
ENTRY_CRASH_SELFTEST = "crash_selftest"
ENTRIES = (ENTRY_VERIFY, ENTRY_CRASH_SELFTEST)

RESULT_PASS = "pass"
RESULT_FAIL = "fail"
RESULT_BLOCKED = "blocked"

MISMATCH_REASON = "expect-mismatch"
BLOCKED_PREFIX = "blocked-by:"

BASE_STEP_FIELDS = ("step", "kind", "expect")
VERIFIER_STEP_FIELDS = (*BASE_STEP_FIELDS, "fixture", "entry", "x", "stack")

CORPUS_FIELDS = ("p", "a", "b", "n", "Px", "Py", "Qx", "Qy")
CRASH_FIELDS = ("p", "a", "b")
PROFILE_FIELDS = (
    "tier",
    "model",
    "bits",
    "mean_tries",
    "sd_tries",
    "per_try_s",
    "mean_wall_s",
    "grade",
    "cost_model",
    "source",
)


class PlanInvalid(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class FixtureInvalid(PlanInvalid):
    pass


@dataclass(frozen=True)
class Step:
    step: str
    kind: str
    expect: str
    fixture: str | None = None
    entry: str | None = None
    x: str | None = None
    stack: str | None = None


@dataclass(frozen=True)
class StepResult:
    step: str
    kind: str
    expected: str
    observed: str
    result: str
    reasons: tuple
    run_id: str
    wall_ms: int
    stdout_digest: str | None = None
    stderr_digest: str | None = None


@dataclass(frozen=True)
class PlanResult:
    steps: tuple
    bundle_hash: str
    pin_hash: str

    @property
    def ok(self):
        return all(step.result == RESULT_PASS for step in self.steps)

    @property
    def first_failure(self):
        for step in self.steps:
            if step.result == RESULT_FAIL:
                return step
        return None


def _is_str(value):
    return isinstance(value, str) and value != ""


def _decimal(value):
    return _is_str(value) and value.lstrip("-").isdigit()


def _number(raw, path):
    if not _is_str(raw):
        raise FixtureInvalid(f"fixture-field-wrong-type:{path}")
    try:
        return float(raw)
    except ValueError:
        raise FixtureInvalid(f"fixture-field-wrong-type:{path}") from None


class GatePlan:
    def __init__(self, steps):
        self.steps = tuple(steps)

    @classmethod
    def load(cls, plan_rows):
        if not isinstance(plan_rows, list):
            raise PlanInvalid(f"plan-not-a-list:{type(plan_rows).__name__}")
        if not plan_rows:
            raise PlanInvalid("plan-empty")
        steps = [_step_at(index, row) for index, row in enumerate(plan_rows)]
        seen = set()
        for index, step in enumerate(steps):
            if step.step in seen:
                raise PlanInvalid(f"duplicate-step-name:{index}.{step.step}")
            seen.add(step.step)
        for name in REQUIRED_STEPS:
            if name not in seen:
                raise PlanInvalid(f"missing-required-selftest:{name}")
        return cls(steps)

    @classmethod
    def from_bundle(cls, gate_bundle):
        plan = gate_bundle.gate_plan
        if not isinstance(plan, dict) or "steps" not in plan:
            raise PlanInvalid("plan-object-has-no-steps")
        return cls.load(plan["steps"])

    def run(self, gate_bundle, sub, attest_path):
        fixtures = _fixtures(gate_bundle)
        elapsed = {}

        def observe(step):
            start = time.monotonic()
            try:
                return _execute(step, gate_bundle, sub, attest_path, fixtures)
            finally:
                elapsed[step.step] = int((time.monotonic() - start) * 1000)

        results = []
        for step, observed, result, reasons, digests in plan_outcomes(self.steps, observe):
            wall_ms = elapsed.get(step.step, 0)
            run = claims.GateRun(
                gate=GATE,
                bundle_hash=gate_bundle.hash,
                pin_hash=gate_bundle.pin_hash,
                plan_step=step.step,
                result=result,
                reasons=reasons,
                at=cli.now_iso(),
            )
            claims.write_gate_run(sub, run)
            lg.info(
                "step",
                step=step.step,
                kind=step.kind,
                expected=step.expect,
                observed=observed,
                result=result,
                reasons=list(reasons),
                run_id=run.hash,
                wall_ms=wall_ms,
            )
            lg.debug("step_digests", step=step.step, stdout_digest=digests[0], stderr_digest=digests[1])
            results.append(
                StepResult(
                    step.step,
                    step.kind,
                    step.expect,
                    observed,
                    result,
                    reasons,
                    run.hash,
                    wall_ms,
                    digests[0],
                    digests[1],
                )
            )
        return PlanResult(tuple(results), gate_bundle.hash, gate_bundle.pin_hash)


def plan_outcomes(steps, observe):
    blocker = None
    for step in steps:
        if blocker is not None:
            yield step, RESULT_BLOCKED, RESULT_BLOCKED, (f"{BLOCKED_PREFIX}{blocker}",), (None, None)
            continue
        observed, extra, digests = observe(step)
        if observed == step.expect:
            yield step, observed, RESULT_PASS, tuple(extra), digests
        else:
            yield step, observed, RESULT_FAIL, (MISMATCH_REASON, f"observed:{observed}", *tuple(extra)), digests
            blocker = step.step


def _step_at(index, row):
    if not isinstance(row, dict):
        raise PlanInvalid(f"step-not-a-mapping:{index}.{type(row).__name__}")
    for field in ("step", "kind", "expect"):
        if field not in row:
            raise PlanInvalid(f"step-missing-field:{index}.{field}")
    if not _is_str(row["step"]):
        raise PlanInvalid(f"step-name-not-a-string:{index}")
    if row["kind"] not in STEP_KINDS:
        raise PlanInvalid(f"unknown-step-kind:{index}.{row['kind']!r}")
    if row["expect"] not in EXPECTATIONS:
        raise PlanInvalid(f"expect-outside-vocabulary:{index}.{row['expect']!r}")
    if row["kind"] == KIND_VERIFIER:
        _reject_unknown_fields(index, row, VERIFIER_STEP_FIELDS)
        return _verifier_step_at(index, row)
    _reject_unknown_fields(index, row, BASE_STEP_FIELDS)
    return Step(step=row["step"], kind=row["kind"], expect=row["expect"])


def _reject_unknown_fields(index, row, allowed):
    for key in sorted(row):
        if key not in allowed:
            raise PlanInvalid(f"unknown-step-field:{index}.{key!r}")


def _verifier_step_at(index, row):
    for field in ("fixture", "entry"):
        if field not in row:
            raise PlanInvalid(f"step-missing-field:{index}.{field}")
        if not _is_str(row[field]):
            raise PlanInvalid(f"step-field-wrong-type:{index}.{field}")
    if row["entry"] not in ENTRIES:
        raise PlanInvalid(f"unknown-verifier-entry:{index}.{row['entry']!r}")
    if row["entry"] == ENTRY_VERIFY:
        if "x" not in row:
            raise PlanInvalid(f"step-missing-field:{index}.x")
        if not _decimal(row["x"]):
            raise PlanInvalid(f"step-field-wrong-type:{index}.x")
    stack = row.get("stack")
    if stack is not None and not _is_str(stack):
        raise PlanInvalid(f"step-field-wrong-type:{index}.stack")
    return Step(
        step=row["step"],
        kind=row["kind"],
        expect=row["expect"],
        fixture=row["fixture"],
        entry=row["entry"],
        x=row.get("x"),
        stack=stack,
    )


def _fixtures(gate_bundle):
    plan = gate_bundle.gate_plan
    if not isinstance(plan, dict) or not isinstance(plan.get("fixtures"), dict):
        raise FixtureInvalid("fixtures-absent")
    return plan["fixtures"]


def _fixture(fixtures, name, fields):
    value = fixtures.get(name)
    if not isinstance(value, dict):
        raise FixtureInvalid(f"fixture-absent:{name}")
    for field in fields:
        if not _decimal(value.get(field)):
            raise FixtureInvalid(f"fixture-field-wrong-type:{name}.{field}")
    return value


def _cost_profile(fixtures):
    raw = fixtures.get("cost_profile")
    if not isinstance(raw, dict) or any(field not in raw for field in PROFILE_FIELDS):
        raise FixtureInvalid("fixture-absent:cost_profile")
    bits = raw["bits"]
    if isinstance(bits, bool) or not isinstance(bits, int):
        raise FixtureInvalid("fixture-field-wrong-type:cost_profile.bits")
    size = SizeCost(
        mean_tries=_number(raw["mean_tries"], "cost_profile.mean_tries"),
        sd_tries=_number(raw["sd_tries"], "cost_profile.sd_tries"),
        per_try_s=_number(raw["per_try_s"], "cost_profile.per_try_s"),
        mean_wall_s=_number(raw["mean_wall_s"], "cost_profile.mean_wall_s"),
    )
    profile = CostProfile(
        tier=raw["tier"],
        production=Production(model=raw["model"], per_size={bits: size}),
        verification=Verification(grade=raw["grade"], cost_model=raw["cost_model"]),
        source=raw["source"],
    )
    return profile, bits


def _launch(fixtures, hypothesis, *, declared_tier):
    profile, bits = _cost_profile(fixtures)
    identity = fixtures.get("skill_identity_hash")
    if not _is_str(identity):
        raise FixtureInvalid("fixture-field-wrong-type:skill_identity_hash")
    budget = fixtures.get("budget_remaining")
    if isinstance(budget, bool) or not isinstance(budget, (int, float)):
        raise FixtureInvalid("fixture-field-wrong-type:budget_remaining")
    return tiergate.Launch(
        cost_profile=profile,
        inputs=bits,
        budget_remaining=float(budget),
        hypothesis_key=keys.hypothesis_key(hypothesis),
        method_identity=hypothesis["method_identity"],
        skill_identity_hash=identity,
        declared_tier=declared_tier,
    )


def _hypothesis(fixtures, name):
    value = fixtures.get(name)
    if not isinstance(value, dict) or not isinstance(value.get("method_identity"), dict):
        raise FixtureInvalid(f"fixture-absent:{name}")
    return value


def _execute(step, gate_bundle, sub, attest_path, fixtures):
    if step.kind == KIND_CANON_KAT:
        return _run_canon_kat()
    if step.kind == KIND_VERIFIER:
        return _run_verifier(step, gate_bundle, fixtures)
    if step.kind == KIND_WAIVER:
        return _run_waiver(gate_bundle, sub, attest_path, fixtures)
    return _run_tier_gate(gate_bundle, sub, fixtures)


def _run_canon_kat():
    failures = kat.run()
    if failures:
        return "fail", tuple(f"kat:{f}" for f in failures[:4]), (None, None)
    return EXPECT_PASS, (), (None, None)


def _run_verifier(step, gate_bundle, fixtures):
    config = gate_bundle.verifier_config()
    if step.stack is not None:
        config = dataclasses.replace(config, stack_ceiling=step.stack)
    engine = verifier.Verifier(config)
    if step.entry == ENTRY_CRASH_SELFTEST:
        raw = _fixture(fixtures, step.fixture, CRASH_FIELDS)
        instance = verifier.Instance(p=int(raw["p"]), a=int(raw["a"]), b=int(raw["b"]), n=None, P=None, Q=None)
        result = engine.crash_selftest(instance)
    else:
        raw = _fixture(fixtures, step.fixture, CORPUS_FIELDS)
        instance = verifier.Instance(
            p=int(raw["p"]),
            a=int(raw["a"]),
            b=int(raw["b"]),
            n=int(raw["n"]),
            P=(int(raw["Px"]), int(raw["Py"])),
            Q=(int(raw["Qx"]), int(raw["Qy"])),
        )
        result = engine.run(instance, int(step.x))
    observed = EXPECT_OK if result.accepted else f"FAIL {result.reason}"
    return observed, tuple(result.reasons), (result.stdout_digest, result.stderr_digest)


def _run_waiver(gate_bundle, sub, attest_path, fixtures):
    hypothesis = _hypothesis(fixtures, "waiver_hypothesis")
    target = keys.hypothesis_key(hypothesis)
    waiver = attest.fixture_waiver(target)
    digest = blob_hash(attest.waiver_canonical(waiver))
    if not attest.attestation_record_matches(attest_path, 0, digest):
        return "waiver-record-absent", (f"attest:{attest_path}",), (digest, None)
    if gate_bundle.waivable_checks != []:
        return "waivable-checks-nonempty", ("waivable-checks",), (digest, None)
    decision = tiergate.TierGate(sub, gate_bundle).admit(_launch(fixtures, hypothesis, declared_tier=1))
    if not isinstance(decision, tiergate.TierRefused) or tiergate.TICKET_ABSENT not in decision.reasons:
        return "admitted", tuple(getattr(decision, "reasons", ())), (digest, None)
    if _tickets_for(sub, target):
        return "ticket-present", tuple(decision.reasons), (digest, None)
    return EXPECT_NO_TICKET, tuple(decision.reasons), (digest, None)


def _run_tier_gate(gate_bundle, sub, fixtures):
    hypothesis = _hypothesis(fixtures, "admitted_hypothesis")
    target = keys.hypothesis_key(hypothesis)
    if claims.get_hypothesis_object(sub, target) is None:
        claims.write_hypothesis_object(sub, claims.HypothesisObject(**hypothesis))
    decision = tiergate.TierGate(sub, gate_bundle).admit(_launch(fixtures, hypothesis, declared_tier=2))
    if not isinstance(decision, tiergate.TierRefused):
        return "admitted", (), (None, None)
    if tiergate.TIER_TWO_ABOVE not in decision.reasons:
        return f"TierRefused({','.join(decision.reasons)})", tuple(decision.reasons), (None, None)
    if not claims.tier_refusals_for(sub, target):
        return "refusal-unrecorded", tuple(decision.reasons), (None, None)
    return EXPECT_TIER_TWO_ABOVE, tuple(decision.reasons), (None, None)


def _tickets_for(sub, hypothesis_key):
    return (
        sub.conn.execute("SELECT 1 FROM tickets WHERE hypothesis_key = ? LIMIT 1", (hypothesis_key,)).fetchone()
        is not None
    )


def _configure(parser):
    subs = parser.add_subparsers(dest="sub", metavar="SUBCOMMAND", required=True)
    subs.add_parser(
        "selftest",
        parents=[cli.globals_parent(suppress=True), cli.json_parent()],
        help="run the gate bundle's plan of planted-failure self-tests, blocking every step after the first failure",
    )


def _run(ns):
    return {"selftest": _run_selftest}[ns.sub](ns)


def _run_selftest(ns):
    from cairn import substrate

    if not Path(ns.attest).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist; the waiver step reads its record 0",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest} --bundle {ns.bundle} --pin {ns.pin}",
        )
    gate_bundle = bundle.open_or_refuse(ns, command="cairn gate selftest")
    try:
        plan = GatePlan.from_bundle(gate_bundle)
    except PlanInvalid as invalid:
        raise CliError(
            exits.GATE_REFUSED,
            f"the gate plan in bundle {gate_bundle.hash} is invalid ({invalid.reason}); no step ran",
            where=str(ns.bundle),
            next_command=bundle.repin_sequence(ns.bundle, ns.pin),
        ) from None
    try:
        with substrate.Substrate.open(ns.db) as sub:
            result = plan.run(gate_bundle, sub, ns.attest)
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn gate selftest --db {ns.db}",
        ) from None
    except FixtureInvalid as invalid:
        raise CliError(
            exits.GATE_REFUSED,
            f"the gate plan in bundle {gate_bundle.hash} carries no usable fixture ({invalid.reason})",
            where=str(ns.bundle),
            next_command=bundle.repin_sequence(ns.bundle, ns.pin),
        ) from None
    steps = [
        {
            "step": s.step,
            "kind": s.kind,
            "expected": s.expected,
            "observed": s.observed,
            "result": s.result,
            "reasons": list(s.reasons),
            "run_id": s.run_id,
            "wall_ms": s.wall_ms,
        }
        for s in result.steps
    ]
    if getattr(ns, "json", False):
        cli.emit_json(
            "gate",
            {
                "sub": "selftest",
                "ok": result.ok,
                "bundle_hash": result.bundle_hash,
                "pin_hash": result.pin_hash,
                "steps": steps,
            },
        )
    else:
        for s in result.steps:
            print(f"{s.result} {s.step} expected={s.expected} observed={s.observed} run={s.run_id}")
    if result.ok:
        return exits.OK
    failed = result.first_failure
    raise CliError(
        exits.GATE_REFUSED,
        f"gate plan step {failed.step} expected {failed.expected} and observed {failed.observed}; every later step is blocked",
        where=str(ns.bundle),
        next_command=f"cairn gate selftest --json --log DEBUG --bundle {ns.bundle} --pin {ns.pin}",
    )


cli.register(
    "gate",
    _configure,
    _run,
    summary="run the gate bundle's declarative plan of planted-failure self-tests before any gate is trusted",
    read_only=False,
    json=True,
)
