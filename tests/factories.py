import json
import random
import re
from pathlib import Path

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
