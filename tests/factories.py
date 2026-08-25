import json
import random
import re
from pathlib import Path

from hypothesis import strategies as st

from cairn.claims import ClaimStatement, EvidenceNode, GateRun, HypothesisObject, ReproRecord, ReviewVerdict, Ticket
from cairn.substrate import blob_hash

VECTORS = Path(__file__).resolve().parent / "vectors"
CREATED_AT = "2026-08-21T00:00:00.000000+00:00"
DEFAULT_COST_MODEL = {"exponent": "1/2", "constant": "0.886", "crossover": 48}
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _rng(seed):
    return random.Random(f"cairn-factories:{seed}")


def _digest(rng):
    return rng.randbytes(32).hex()


def assumption_id(name):
    return name if _HEX64.match(name) else blob_hash(f"assumption:{name}".encode())


def assumption_ids(names):
    return frozenset(assumption_id(n) for n in names)


def scope(family="toy_curve", size=(30, 50), assumptions=frozenset({"A1"}), param_ranges=None):
    return {
        "target_family": family,
        "size_interval": list(size),
        "param_ranges": dict(param_ranges) if param_ranges is not None else {"bits": list(size)},
        "assumption_set": assumption_ids(assumptions),
    }


def _cost_model(cost_model, rng):
    if cost_model is None:
        return None
    if cost_model is True:
        return {**DEFAULT_COST_MODEL, "crossover": rng.randrange(40, 61)}
    return dict(cost_model)


def claim_statement(family="toy_curve", size=(30, 50), assumptions=frozenset({"A1"}), cost_model=None, seed=0, **kw):
    rng = _rng(seed)
    fields = {
        "claim_id": f"claim-{rng.randrange(16**8):08x}",
        "version": 1,
        "informal": f"rho on {family} costs c*sqrt(n) over {size[0]}-{size[1]} bits (case {rng.randrange(1000)})",
        "scope": scope(family, size, assumptions, kw.pop("param_ranges", None)),
        "quantities": {"units": {"cost": "core_s", "size": "bits"}, "cost_model": _cost_model(cost_model, rng)},
        "created_at": CREATED_AT,
    }
    fields.update(kw)
    return ClaimStatement(**fields)


def superseding_statement(statement, **kw):
    changes = {"supersedes": statement.hash, "version": statement.version + 1, **kw}
    fields = {
        name: getattr(statement, name)
        for name in ("claim_id", "informal", "scope", "quantities", "formal_source", "source_claim_hash", "status", "created_at")
    }
    return ClaimStatement(**{**fields, **changes})


def hypothesis_object(family="toy_curve", cost_model=None, claim_statement_hash=None, supersedes=None, seed=0, **kw):
    rng = _rng(seed)
    model = _cost_model(cost_model, rng) or DEFAULT_COST_MODEL
    fields = {
        "target_family": family,
        "claimed": {"kind": "cost_model", "exponent": model["exponent"], "constant": model["constant"], "crossover": str(model["crossover"])},
        "method_identity": {"interface_version": f"{family}/1", "params": {"r": "20", "theta": "2^-10"}},
        "declared_parameter_ranges": {"bits": [30, 50]},
        "sampling_distribution": None,
        "claim_statement_hash": claim_statement_hash,
        "supersedes": supersedes,
        "created_at": CREATED_AT,
    }
    fields.update(kw)
    return HypothesisObject(**fields)


def _producer(producer, rng):
    if producer is None:
        return _digest(rng), "skill"
    if isinstance(producer, tuple):
        return producer
    return producer, "skill"


def evidence_node(kind, target_statement_hash, population, assumptions, verdict=None, repro=None, producer=None, seed=0, **kw):
    rng = _rng(seed)
    identity, tag = _producer(producer, rng)
    fields = {
        "kind": kind,
        "target_statement_hash": target_statement_hash,
        "population": population,
        "assumptions": assumption_ids(assumptions),
        "producer_identity": identity,
        "producer_tag": tag,
        "verdict": verdict,
        "repro_record_hash": repro if repro is None or isinstance(repro, str) else repro.hash,
        "attempt_id": kw.pop("attempt_id", f"attempt-{rng.randrange(16**8):08x}"),
        "created_at": CREATED_AT,
    }
    fields.update(kw)
    return EvidenceNode(**fields)


def repro_record(attempt_id, passed=True, kind="second_attempt_agree", at=CREATED_AT):
    return ReproRecord(attempt_id=attempt_id, kind=kind, passed=passed, at=at)


def ladder_table_keep(statement, population, repro_passed=True, seed=0, **kw):
    rng = _rng(seed)
    attempt_id = f"attempt-{rng.randrange(16**8):08x}"
    repro = repro_record(attempt_id, passed=repro_passed)
    node = evidence_node(
        "ladder_table",
        statement.hash,
        population,
        kw.pop("assumptions", frozenset(population["assumption_set"])),
        verdict="KEEP",
        repro=repro,
        seed=seed,
        attempt_id=attempt_id,
        in_sample_sizes=kw.pop("in_sample_sizes", tuple(population["size_interval"])),
        **kw,
    )
    return node, repro


def review_verdict(statement_hash, verdict="approve", seed=0, **kw):
    rng = _rng(seed)
    fields = {
        "statement_hash": statement_hash,
        "reviewer": f"reviewer-{rng.randrange(16**4):04x}",
        "verdict": verdict,
        "checklist_template_hash": _digest(rng),
        "gate_bundle_hash": _digest(rng),
        "at": CREATED_AT,
        "file_offset": 0,
    }
    fields.update(kw)
    return ReviewVerdict(**fields)


def gate_run(gate="tier_gate", result="admitted", reasons=(), seed=0, **kw):
    rng = _rng(seed)
    fields = {
        "gate": gate,
        "bundle_hash": _digest(rng),
        "pin_hash": _digest(rng),
        "result": result,
        "reasons": tuple(reasons),
        "at": CREATED_AT,
    }
    fields.update(kw)
    return GateRun(**fields)


def ticket(hypothesis_key=None, tier=0, kind="hypothesis_object", seed=0, **kw):
    rng = _rng(seed)
    fields = {
        "hypothesis_key": hypothesis_key or _digest(rng),
        "method_identity": {"interface_version": "toy_curve/1", "params": {"r": "20", "theta": "2^-10"}},
        "tier": tier,
        "kind": kind,
        "node_hash": _digest(rng),
        "bundle_hash": _digest(rng),
    }
    fields.update(kw)
    return Ticket(**fields)


def selftest_summary(origins, randomized_arm, cross_check):
    return {"corpus_origins": origins, "randomized_arm": randomized_arm, "cross_check": cross_check, "pass": 4, "floor": 4}


def instance_from_vector(name="curve60_seed1"):
    data = json.loads((VECTORS / f"{name}.json").read_text())
    point = [int(c) for c in data["P"]]
    return {"p": int(data["p"]), "a": int(data["a"]), "b": int(data["b"]), "n": int(data["n"]), "P": point, "Q": list(point)}


FAMILIES = ("toy_curve", "model_curve", "prime_field")
ASSUMPTION_NAMES = ("A1", "A2", "A3", "A4", "A5", "A6")
PARAM_AXES = ("bits", "cores", "trials")
ORIGIN_VALUES = ("author_supplied", "upstream_vendored", "randomized")
JUSTIFYING = (
    ("ladder_table", "KEEP"),
    ("ladder_table", "KEEP_IN_SAMPLE"),
    ("repro_node", None),
    ("statistical", None),
    ("model_proof", None),
    ("counterexample_hunt_record", "SURVIVED"),
    ("lean_artifact", None),
)


@st.composite
def size_intervals(draw, low=20, high=80):
    lo = draw(st.integers(low, high))
    return [lo, draw(st.integers(lo, high))]


@st.composite
def scopes(draw):
    axes = draw(st.lists(st.sampled_from(PARAM_AXES), max_size=3, unique=True))
    return {
        "target_family": draw(st.sampled_from(FAMILIES)),
        "size_interval": draw(size_intervals()),
        "param_ranges": {axis: draw(size_intervals()) for axis in axes},
        "assumption_set": assumption_ids(
            draw(st.frozensets(st.sampled_from(ASSUMPTION_NAMES)))
        ),
    }


_SLACK = st.one_of(st.just(0), st.integers(0, 10))


@st.composite
def covering_populations(draw, scope):
    def widen(interval):
        return [interval[0] - draw(_SLACK), interval[1] + draw(_SLACK)]

    held = sorted(scope["assumption_set"])
    return {
        "target_family": scope["target_family"],
        "size_interval": widen(scope["size_interval"]),
        "param_ranges": {
            axis: widen(interval) for axis, interval in scope["param_ranges"].items()
        },
        "assumption_set": frozenset(draw(st.sets(st.sampled_from(held))))
        if held
        else frozenset(),
    }


@st.composite
def narrowed_populations(draw, scope):
    population = draw(covering_populations(scope))
    axis = draw(st.sampled_from(["size_interval", *sorted(scope["param_ranges"])]))
    target = (
        scope["size_interval"]
        if axis == "size_interval"
        else scope["param_ranges"][axis]
    )
    wide = (
        population["size_interval"]
        if axis == "size_interval"
        else population["param_ranges"][axis]
    )
    moved = (
        [target[0] + 1, wide[1]] if draw(st.booleans()) else [wide[0], target[1] - 1]
    )
    if axis == "size_interval":
        return {**population, "size_interval": moved}, "size_interval"
    return {
        **population,
        "param_ranges": {**population["param_ranges"], axis: moved},
    }, "param_ranges"


@st.composite
def producer_summaries(draw):
    origins = draw(
        st.dictionaries(
            st.sampled_from(("F5", "GF101", "bits150")),
            st.dictionaries(
                st.sampled_from(("P", "p", "n")),
                st.sampled_from(ORIGIN_VALUES),
                max_size=3,
            ),
            max_size=3,
        )
    )
    cross_check = draw(
        st.one_of(
            st.none(),
            st.fixed_dictionaries(
                {
                    "axis": st.just("algorithm"),
                    "independent_range": st.dictionaries(
                        st.sampled_from(PARAM_AXES), size_intervals(0, 100), max_size=2
                    ),
                }
            ),
        )
    )
    return selftest_summary(origins, draw(st.booleans()), cross_check)


_ENDPOINT = st.one_of(
    st.integers(-1000, 1000),
    st.none(),
    st.booleans(),
    st.text(max_size=3),
    st.integers(10**30, 10**40),
)
_INTERVALISH = st.one_of(
    st.lists(_ENDPOINT, max_size=3),
    _ENDPOINT,
    st.dictionaries(st.text(max_size=2), _ENDPOINT, max_size=2),
)


@st.composite
def arbitrary_records(draw):
    record = {
        "target_family": draw(
            st.one_of(st.sampled_from(FAMILIES), st.none(), st.integers())
        ),
        "size_interval": draw(_INTERVALISH),
        "param_ranges": draw(
            st.one_of(
                st.none(),
                st.integers(),
                st.dictionaries(
                    st.sampled_from((*PARAM_AXES, "extra")), _INTERVALISH, max_size=3
                ),
            )
        ),
        "assumption_set": draw(
            st.one_of(
                st.none(),
                st.integers(),
                st.text(max_size=4),
                st.lists(st.text(max_size=4), max_size=3),
            )
        ),
    }
    for key in draw(st.sets(st.sampled_from(sorted(record)), max_size=2)):
        del record[key]
    return record
