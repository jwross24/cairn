"""The ladder plan: one versioned gate-bundle object every ladder bead reads.

Every tolerance, count and cap the ladder applies comes from this object, so a verdict
names the plan that produced it through the plan hash the load step records in its
gate-run row, and a later bundle never recomputes an earlier verdict. Loading fails
closed: a field absent, mistyped or unknown, a rung set with no hold-out, a memory cap
where the floor does not bind, or a clock tolerance the KEEP band cannot cover each
refuse with a typed reason before any rung exists.

Several literals are placeholders an owning bead replaces with a measurement. The
provenance section names the owner while a value is still seeded, and seeded_fields()
lists those paths so a run engine can refuse to score a verdict against a literal.

The clock bound. The clock check bounds uncounted arithmetic to the clock tolerance
times the counted work at the reference rate, which is a bound only while no arithmetic
a method can carry is faster per operation than the gate's counted object; the plan
therefore requires clock_tolerance * rate_ratio < 2 * design_radius, the most a method
could hide inside the KEEP band and still be caught by it.
"""

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from cairn import bundle, claims, cli, exits, log
from cairn.errors import CliError

lg = log.get("ladderplan")

KIND = "ladder_plan"
GATE = "ladder_plan"
STEP_LOAD = "load"
RESULT_PASS = "pass"
RESULT_REFUSED = "refused"
PLAN_HASH_PREFIX = "ladder_plan:"
PLAN_ABSENT = "plan-object-absent"
VERSION = 1
COMPARISON_VERSION = 1
TRIAL_FLOOR = 100

ROLE_FIT = "fit"
ROLE_HOLD_OUT = "hold_out"
ROLES = (ROLE_FIT, ROLE_HOLD_OUT)
STATISTIC = "speedup_factor"
NUMERATOR = "baseline_group_ops"
DENOMINATOR = "claim_group_ops"
ESTIMATOR_FORMS = ("mean_ci", "median_ci")
INSTANCE_STREAM = "shared"
METHOD_SEEDS = "gate_drawn_per_arm"
ARMS = ["claimant", "baseline", "baseline_aa"]
CI_METHODS = ("normal", "bootstrap_percentile")
PATIENCE_BASIS = "declared_profile_mean_per_trial"
SEEDED = "seeded"
PROVENANCE_PREFIXES = (SEEDED, "measured", "written", "policy")

TOP_FIELDS = (
    "version",
    "rungs",
    "hold_out_m",
    "design_radius",
    "comparison",
    "keep_band_floor",
    "tolerances",
    "clock",
    "baseline",
    "patience_ceiling",
    "shape_departure_tolerance",
    "provenance",
)
RUNG_FIELDS = ("bits", "role", "trials", "floor_binds", "memory_cap_bytes", "refutation_floor")
FLOOR_FIELDS = ("group_ops", "table_entries", "memory_bytes")
COMPARISON_FIELDS = ("version", "estimator", "pairing", "ci", "every_rung_must_pass")
ESTIMATOR_FIELDS = ("statistic", "numerator", "denominator", "form")
PAIRING_FIELDS = ("instance_stream", "method_seeds", "arms")
CI_FIELDS = ("method", "coverage")
TOLERANCE_FIELDS = ("count_divergence", "clock", "wall")
CLOCK_FIELDS = ("rate_ratio",)
BASELINE_FIELDS = ("skill", "method_identity", "identity_bundle_hash", "implementation_revision")
METHOD_IDENTITY_FIELDS = ("interface_version", "params")
PATIENCE_FIELDS = ("multiplier", "basis")
PROVENANCE_KEYS = (
    "rungs.bits",
    "rungs.trials",
    "design_radius",
    "rungs.refutation_floor",
    "rungs.memory_cap_bytes",
    "baseline",
    "clock.rate_ratio",
    "tolerances",
    "comparison",
    "keep_band_floor",
    "hold_out_m",
    "patience_ceiling",
    "shape_departure_tolerance",
)

DECIMAL = re.compile(r"-?[0-9]+(\.[0-9]+)?")
HEX64 = re.compile(r"[0-9a-f]{64}")


class LadderPlanInvalid(ValueError):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class RefutationFloor:
    group_ops: int
    table_entries: int
    memory_bytes: int

    def node(self):
        return {"group_ops": self.group_ops, "table_entries": self.table_entries, "memory_bytes": self.memory_bytes}


@dataclass(frozen=True)
class Rung:
    bits: int
    role: str
    trials: int
    floor_binds: bool
    memory_cap_bytes: int | None
    refutation_floor: RefutationFloor

    def node(self):
        return {
            "bits": self.bits,
            "role": self.role,
            "trials": self.trials,
            "floor_binds": self.floor_binds,
            "memory_cap_bytes": self.memory_cap_bytes,
            "refutation_floor": self.refutation_floor.node(),
        }


@dataclass(frozen=True)
class Tolerances:
    count_divergence: Decimal
    clock: Decimal
    wall: Decimal

    def node(self):
        return {"count_divergence": _text(self.count_divergence), "clock": _text(self.clock), "wall": _text(self.wall)}


@dataclass(frozen=True)
class Comparison:
    version: int
    estimator_form: str
    ci_method: str
    ci_coverage: Decimal
    every_rung_must_pass: bool

    def node(self):
        return {
            "version": self.version,
            "estimator_form": self.estimator_form,
            "ci_method": self.ci_method,
            "ci_coverage": _text(self.ci_coverage),
            "every_rung_must_pass": self.every_rung_must_pass,
        }


@dataclass(frozen=True)
class Baseline:
    skill: str
    method_identity: dict
    identity_bundle_hash: str
    implementation_revision: str

    def node(self):
        return {
            "skill": self.skill,
            "method_identity": self.method_identity,
            "identity_bundle_hash": self.identity_bundle_hash,
            "implementation_revision": self.implementation_revision,
        }


@dataclass(frozen=True)
class ClockBound:
    clock_tolerance: Decimal
    rate_ratio: Decimal
    design_radius: Decimal

    @property
    def product(self):
        return self.clock_tolerance * self.rate_ratio

    @property
    def keep_band_excess(self):
        return 2 * self.design_radius

    @property
    def holds(self):
        return self.product < self.keep_band_excess

    def describe(self):
        relation = "<" if self.holds else ">="
        return (
            f"{_text(self.clock_tolerance)}*{_text(self.rate_ratio)}={_text(self.product)}"
            f"{relation}{_text(self.keep_band_excess)}"
        )

    def node(self):
        return {
            "clock_tolerance": _text(self.clock_tolerance),
            "rate_ratio": _text(self.rate_ratio),
            "product": _text(self.product),
            "keep_band_excess": _text(self.keep_band_excess),
            "holds": self.holds,
        }


@dataclass(frozen=True)
class LadderPlan:
    version: int
    rungs: tuple
    hold_out_m: int
    design_radius: Decimal
    comparison: Comparison
    keep_band_floor: Decimal
    tolerances: Tolerances
    rate_ratio: Decimal
    baseline: Baseline
    patience_multiplier: int
    shape_departure_tolerance: Decimal
    provenance: dict
    hash: str | None = None
    bundle_hash: str | None = None

    @classmethod
    def load(cls, obj, *, tiers_ceiling=None, plan_hash=None, bundle_hash=None):
        if not isinstance(obj, dict):
            raise LadderPlanInvalid(f"plan-not-a-mapping:{type(obj).__name__}")
        _mapping(obj, "", TOP_FIELDS)
        version = _int(obj["version"], "version")
        if version != VERSION:
            raise LadderPlanInvalid(f"plan-version-unsupported:{version}")
        hold_out_m = _int(obj["hold_out_m"], "hold_out_m")
        if hold_out_m < 1:
            raise LadderPlanInvalid(f"hold-out-m-not-positive:{hold_out_m}")
        rungs = _rungs(obj["rungs"], hold_out_m)
        design_radius = _decimal(obj["design_radius"], "design_radius")
        if not 0 < design_radius < Decimal("0.5"):
            raise LadderPlanInvalid(f"design-radius-out-of-range:{_text(design_radius)}")
        comparison = _comparison(obj["comparison"])
        keep_band_floor = _decimal(obj["keep_band_floor"], "keep_band_floor")
        if keep_band_floor <= 1:
            raise LadderPlanInvalid(f"keep-band-floor-not-above-one:{_text(keep_band_floor)}")
        tolerances = _tolerances(obj["tolerances"])
        clock = _mapping(obj["clock"], "clock", CLOCK_FIELDS)
        rate_ratio = _decimal(clock["rate_ratio"], "clock.rate_ratio")
        if rate_ratio < 1:
            raise LadderPlanInvalid(f"rate-ratio-below-one:{_text(rate_ratio)}")
        baseline = _baseline(obj["baseline"])
        multiplier = _patience(obj["patience_ceiling"], tiers_ceiling)
        shape = _decimal(obj["shape_departure_tolerance"], "shape_departure_tolerance")
        if shape <= 0:
            raise LadderPlanInvalid(f"shape-tolerance-not-positive:{_text(shape)}")
        provenance = _provenance(obj["provenance"])
        bound = ClockBound(tolerances.clock, rate_ratio, design_radius)
        if not bound.holds:
            raise LadderPlanInvalid(f"clock-bound-violated:{bound.describe()}")
        return cls(
            version=version,
            rungs=rungs,
            hold_out_m=hold_out_m,
            design_radius=design_radius,
            comparison=comparison,
            keep_band_floor=keep_band_floor,
            tolerances=tolerances,
            rate_ratio=rate_ratio,
            baseline=baseline,
            patience_multiplier=multiplier,
            shape_departure_tolerance=shape,
            provenance=provenance,
            hash=plan_hash,
            bundle_hash=bundle_hash,
        )

    @classmethod
    def from_bundle(cls, gate_bundle):
        try:
            obj = gate_bundle.ladder_plan
            plan_hash = gate_bundle.digest_of(KIND)
        except bundle.BundleError:
            raise LadderPlanInvalid(PLAN_ABSENT) from None
        tiers = gate_bundle.tiers
        ceiling = tiers.get("ceiling_multiplier") if isinstance(tiers, dict) else None
        return cls.load(obj, tiers_ceiling=ceiling, plan_hash=plan_hash, bundle_hash=gate_bundle.hash)

    @property
    def fit_rungs(self):
        return tuple(rung for rung in self.rungs if rung.role == ROLE_FIT)

    @property
    def hold_out_rung(self):
        return self.rungs[-1]

    def rung(self, bits):
        for rung in self.rungs:
            if rung.bits == bits:
                return rung
        raise KeyError(f"the ladder plan has no {bits}-bit rung")

    def seeded_fields(self):
        return [key for key in PROVENANCE_KEYS if self.provenance[key].startswith(SEEDED + ":")]

    def clock_bound(self):
        return ClockBound(self.tolerances.clock, self.rate_ratio, self.design_radius)

    def node(self):
        return {
            "version": self.version,
            "hash": self.hash,
            "bundle_hash": self.bundle_hash,
            "rungs": [rung.node() for rung in self.rungs],
            "hold_out_m": self.hold_out_m,
            "design_radius": _text(self.design_radius),
            "comparison": self.comparison.node(),
            "keep_band_floor": _text(self.keep_band_floor),
            "tolerances": self.tolerances.node(),
            "rate_ratio": _text(self.rate_ratio),
            "baseline": self.baseline.node(),
            "patience_multiplier": self.patience_multiplier,
            "shape_departure_tolerance": _text(self.shape_departure_tolerance),
            "provenance": dict(self.provenance),
            "seeded": self.seeded_fields(),
            "clock_bound": self.clock_bound().node(),
        }


def _text(value):
    return f"{value.normalize():f}"


def _at(path, name):
    return f"{path}.{name}" if path else name


def _wrong(path):
    return LadderPlanInvalid(f"plan-field-wrong-type:{path}")


def _mapping(value, path, fields):
    if not isinstance(value, dict):
        raise _wrong(path)
    for name in fields:
        if name not in value:
            raise LadderPlanInvalid(f"plan-missing-field:{_at(path, name)}")
    for name in sorted(value):
        if name not in fields:
            raise LadderPlanInvalid(f"plan-unknown-field:{_at(path, name)}")
    return value


def _int(value, path):
    if isinstance(value, bool) or not isinstance(value, int):
        raise _wrong(path)
    return value


def _bool(value, path):
    if not isinstance(value, bool):
        raise _wrong(path)
    return value


def _str(value, path):
    if not isinstance(value, str) or value == "":
        raise _wrong(path)
    return value


def _decimal(value, path):
    if not isinstance(value, str) or not DECIMAL.fullmatch(value):
        raise _wrong(path)
    return Decimal(value)


def _rungs(raw, hold_out_m):
    if not isinstance(raw, list):
        raise _wrong("rungs")
    if not raw:
        raise LadderPlanInvalid("rungs-empty")
    rungs = [_rung(index, row) for index, row in enumerate(raw)]
    for index in range(1, len(rungs)):
        if rungs[index].bits <= rungs[index - 1].bits:
            raise LadderPlanInvalid(f"rungs-not-ascending:{index}")
    hold_out = [rung for rung in rungs if rung.role == ROLE_HOLD_OUT]
    if len(hold_out) != 1:
        raise LadderPlanInvalid(f"hold-out-rung-count:{len(hold_out)}")
    if hold_out[0] is not rungs[-1]:
        raise LadderPlanInvalid(f"hold-out-rung-not-largest:{hold_out[0].bits}")
    if len(rungs) == 1:
        raise LadderPlanInvalid("fit-rung-count:0")
    for rung in rungs:
        if rung.role == ROLE_FIT and rung.trials < TRIAL_FLOOR:
            raise LadderPlanInvalid(f"trials-below-floor:{rung.bits}.{rung.trials}")
        if rung.role == ROLE_HOLD_OUT and rung.trials != hold_out_m:
            raise LadderPlanInvalid(f"hold-out-trials-ne-m:{rung.bits}.{rung.trials}!={hold_out_m}")
        if rung.floor_binds and rung.memory_cap_bytes is None:
            raise LadderPlanInvalid(f"floor-without-memory-cap:{rung.bits}")
        if not rung.floor_binds and rung.memory_cap_bytes is not None:
            raise LadderPlanInvalid(f"memory-cap-without-floor:{rung.bits}")
        table = rung.refutation_floor.memory_bytes
        if rung.memory_cap_bytes is not None and rung.memory_cap_bytes != table:
            raise LadderPlanInvalid(f"memory-cap-ne-floor-table:{rung.bits}.{rung.memory_cap_bytes}!={table}")
    return tuple(rungs)


def _rung(index, row):
    path = f"rungs.{index}"
    _mapping(row, path, RUNG_FIELDS)
    bits = _int(row["bits"], f"{path}.bits")
    role = _str(row["role"], f"{path}.role")
    if role not in ROLES:
        raise LadderPlanInvalid(f"rung-role-unknown:{index}.{role}")
    cap = row["memory_cap_bytes"]
    return Rung(
        bits=bits,
        role=role,
        trials=_int(row["trials"], f"{path}.trials"),
        floor_binds=_bool(row["floor_binds"], f"{path}.floor_binds"),
        memory_cap_bytes=None if cap is None else _int(cap, f"{path}.memory_cap_bytes"),
        refutation_floor=_floor(row["refutation_floor"], f"{path}.refutation_floor", bits),
    )


def _floor(raw, path, bits):
    _mapping(raw, path, FLOOR_FIELDS)
    values = {name: _int(raw[name], f"{path}.{name}") for name in FLOOR_FIELDS}
    for name, value in values.items():
        if value < 1:
            raise LadderPlanInvalid(f"floor-not-positive:{bits}.{name}")
    return RefutationFloor(**values)


def _comparison(raw):
    _mapping(raw, "comparison", COMPARISON_FIELDS)
    version = _int(raw["version"], "comparison.version")
    if version != COMPARISON_VERSION:
        raise LadderPlanInvalid(f"comparison-version-unsupported:{version}")
    estimator = _mapping(raw["estimator"], "comparison.estimator", ESTIMATOR_FIELDS)
    for name, expected in (("statistic", STATISTIC), ("numerator", NUMERATOR), ("denominator", DENOMINATOR)):
        if _str(estimator[name], f"comparison.estimator.{name}") != expected:
            raise LadderPlanInvalid(f"estimator-{name}-unknown:{estimator[name]}")
    form = _str(estimator["form"], "comparison.estimator.form")
    if form not in ESTIMATOR_FORMS:
        raise LadderPlanInvalid(f"estimator-form-unknown:{form}")
    pairing = _mapping(raw["pairing"], "comparison.pairing", PAIRING_FIELDS)
    if _str(pairing["instance_stream"], "comparison.pairing.instance_stream") != INSTANCE_STREAM:
        raise LadderPlanInvalid(f"pairing-instance-stream-unknown:{pairing['instance_stream']}")
    if _str(pairing["method_seeds"], "comparison.pairing.method_seeds") != METHOD_SEEDS:
        raise LadderPlanInvalid(f"pairing-method-seeds-unknown:{pairing['method_seeds']}")
    if pairing["arms"] != ARMS:
        raise LadderPlanInvalid(f"pairing-arms-unknown:{pairing['arms']!r}")
    ci = _mapping(raw["ci"], "comparison.ci", CI_FIELDS)
    method = _str(ci["method"], "comparison.ci.method")
    if method not in CI_METHODS:
        raise LadderPlanInvalid(f"ci-method-unknown:{method}")
    coverage = _decimal(ci["coverage"], "comparison.ci.coverage")
    if not 0 < coverage < 1:
        raise LadderPlanInvalid(f"ci-coverage-out-of-range:{_text(coverage)}")
    if not _bool(raw["every_rung_must_pass"], "comparison.every_rung_must_pass"):
        raise LadderPlanInvalid("every-rung-must-pass-false")
    return Comparison(version, form, method, coverage, True)


def _tolerances(raw):
    _mapping(raw, "tolerances", TOLERANCE_FIELDS)
    values = {}
    for name in TOLERANCE_FIELDS:
        value = _decimal(raw[name], f"tolerances.{name}")
        if not 0 < value < 1:
            raise LadderPlanInvalid(f"tolerance-out-of-range:{name}.{_text(value)}")
        values[name] = value
    return Tolerances(**values)


def _baseline(raw):
    _mapping(raw, "baseline", BASELINE_FIELDS)
    skill = _str(raw["skill"], "baseline.skill")
    identity = _mapping(raw["method_identity"], "baseline.method_identity", METHOD_IDENTITY_FIELDS)
    interface_version = _str(identity["interface_version"], "baseline.method_identity.interface_version")
    params = identity["params"]
    if not isinstance(params, dict) or any(not isinstance(v, str) for v in params.values()):
        raise _wrong("baseline.method_identity.params")
    for name in ("identity_bundle_hash", "implementation_revision"):
        if not isinstance(raw[name], str) or not HEX64.fullmatch(raw[name]):
            raise LadderPlanInvalid(f"baseline-hash-malformed:{name}")
    return Baseline(
        skill=skill,
        method_identity={"interface_version": interface_version, "params": dict(params)},
        identity_bundle_hash=raw["identity_bundle_hash"],
        implementation_revision=raw["implementation_revision"],
    )


def _patience(raw, tiers_ceiling):
    _mapping(raw, "patience_ceiling", PATIENCE_FIELDS)
    multiplier = _int(raw["multiplier"], "patience_ceiling.multiplier")
    if multiplier < 1:
        raise LadderPlanInvalid(f"patience-multiplier-below-one:{multiplier}")
    basis = _str(raw["basis"], "patience_ceiling.basis")
    if basis != PATIENCE_BASIS:
        raise LadderPlanInvalid(f"patience-basis-unknown:{basis}")
    if tiers_ceiling is not None and multiplier != tiers_ceiling:
        raise LadderPlanInvalid(f"patience-ceiling-ne-tiers:{multiplier}!={tiers_ceiling}")
    return multiplier


def _provenance(raw):
    if not isinstance(raw, dict):
        raise _wrong("provenance")
    for key in PROVENANCE_KEYS:
        if key not in raw:
            raise LadderPlanInvalid(f"provenance-missing:{key}")
    for key in sorted(raw):
        if key not in PROVENANCE_KEYS:
            raise LadderPlanInvalid(f"provenance-unknown:{key}")
    out = {}
    for key in PROVENANCE_KEYS:
        value = raw[key]
        prefix, _, rest = value.partition(":") if isinstance(value, str) else ("", "", "")
        if prefix not in PROVENANCE_PREFIXES or rest == "":
            raise LadderPlanInvalid(f"provenance-malformed:{key}")
        out[key] = value
    return out


def plan_digest(gate_bundle):
    try:
        return gate_bundle.digest_of(KIND)
    except bundle.BundleError:
        return None


@dataclass(frozen=True)
class Load:
    plan: LadderPlan | None
    reason: str | None
    plan_hash: str | None
    run_id: str

    @property
    def ok(self):
        return self.plan is not None


def load_for_gate(sub, gate_bundle):
    plan_hash = plan_digest(gate_bundle)
    hash_reason = () if plan_hash is None else (PLAN_HASH_PREFIX + plan_hash,)
    try:
        plan = LadderPlan.from_bundle(gate_bundle)
    except LadderPlanInvalid as invalid:
        run_id = _record(sub, gate_bundle, RESULT_REFUSED, (invalid.reason, *hash_reason))
        lg.info("load_refused", bundle_hash=gate_bundle.hash, plan_hash=plan_hash, reason=invalid.reason, run_id=run_id)
        return Load(None, invalid.reason, plan_hash, run_id)
    run_id = _record(sub, gate_bundle, RESULT_PASS, hash_reason)
    lg.info("load", bundle_hash=gate_bundle.hash, plan_hash=plan_hash, run_id=run_id, seeded=plan.seeded_fields())
    return Load(plan, None, plan_hash, run_id)


def _record(sub, gate_bundle, result, reasons):
    run = claims.GateRun(
        gate=GATE,
        bundle_hash=gate_bundle.hash,
        pin_hash=gate_bundle.pin_hash,
        plan_step=STEP_LOAD,
        result=result,
        reasons=tuple(reasons),
        at=cli.now_iso(),
    )
    claims.write_gate_run(sub, run)
    return run.hash


def _configure(parser):
    subs = parser.add_subparsers(dest="sub", metavar="SUBCOMMAND", required=True)
    subs.add_parser(
        "plan",
        parents=[cli.globals_parent(suppress=True), cli.json_parent()],
        help="load and validate the ladder plan from the gate bundle, writing the load as a gate run",
    )


def _run(ns):
    return {"plan": _run_plan}[ns.sub](ns)


def _open(sub, ns):
    try:
        return bundle.open_for_gate(sub, ns.bundle, ns.pin)
    except bundle.BundlePinMismatch as mismatch:
        raise CliError(
            exits.GATE_REFUSED,
            f"gate bundle hash {mismatch.bundle_hash} differs from the pin {mismatch.pin_hash}; cairn ladder plan fails closed",
            where=mismatch.pin_path,
            next_command=bundle.repin_sequence(ns.bundle, ns.pin),
        ) from None


def _run_plan(ns):
    from cairn import substrate

    for path, what in ((ns.bundle, "gate bundle"), (ns.pin, "gate-bundle pin")):
        if not Path(path).exists():
            raise CliError(
                exits.ENVIRONMENT,
                f"the {what} {path} does not exist",
                where=str(path),
                next_command=bundle.repin_sequence(ns.bundle, ns.pin),
            )
    try:
        with substrate.Substrate.open(ns.db) as sub:
            gate_bundle = _open(sub, ns)
            load = load_for_gate(sub, gate_bundle)
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn ladder plan --db {ns.db}",
        ) from None
    if not load.ok:
        raise CliError(
            exits.GATE_REFUSED,
            f"the ladder plan in bundle {gate_bundle.hash} is invalid ({load.reason}); the refusal is gate run {load.run_id}",
            where=str(ns.bundle),
            next_command=bundle.repin_sequence(ns.bundle, ns.pin),
        )
    plan = load.plan
    if getattr(ns, "json", False):
        cli.emit_json(
            "ladder",
            {
                "sub": "plan",
                "ok": True,
                "bundle_hash": gate_bundle.hash,
                "pin_hash": gate_bundle.pin_hash,
                "plan_hash": load.plan_hash,
                "run_id": load.run_id,
                "plan": plan.node(),
            },
        )
    else:
        print(f"plan_hash {load.plan_hash}")
        print(f"bundle_hash {gate_bundle.hash}")
        print(f"run_id {load.run_id}")
        for rung in plan.rungs:
            cap = "none" if rung.memory_cap_bytes is None else str(rung.memory_cap_bytes)
            floor = rung.refutation_floor
            print(
                f"rung {rung.bits} {rung.role} trials={rung.trials} floor_ops={floor.group_ops} "
                f"floor_bytes={floor.memory_bytes} cap={cap}"
            )
        print(f"clock_bound {plan.clock_bound().describe()}")
        print(f"seeded {','.join(plan.seeded_fields()) or 'none'}")
    return exits.OK


cli.register(
    "ladder",
    _configure,
    _run,
    summary="load and validate the ladder plan from the gate bundle, recording the load as a gate run",
    read_only=False,
    json=True,
)
