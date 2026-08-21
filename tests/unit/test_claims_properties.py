import dataclasses
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories  # noqa: E402
from mutants import claims_mutants  # noqa: E402

hexdigest = st.binary(min_size=32, max_size=32).map(bytes.hex)
families = st.sampled_from(["toy_curve", "planted_curve", "interval_dlp"])
assumption_names = st.frozensets(st.sampled_from(["A1", "A2", "A3", "A4", "A5", "A6"]), min_size=1)
sizes = st.tuples(st.integers(20, 60), st.integers(0, 20)).map(lambda t: (t[0], t[0] + t[1]))
cost_models = st.none() | st.fixed_dictionaries(
    {"exponent": st.sampled_from(["1/2", "1/3", "2/3"]), "constant": st.sampled_from(["0.886", "1.0", "2.5"]), "crossover": st.integers(30, 70)}
)


@st.composite
def statements(draw):
    return factories.claim_statement(
        family=draw(families),
        size=draw(sizes),
        assumptions=draw(assumption_names),
        cost_model=draw(cost_models),
        seed=draw(st.integers(0, 2**32)),
    )


def mutate_one_field(stmt, field, data):
    if field == "claim_id":
        return dataclasses.replace(stmt, claim_id=stmt.claim_id + "x")
    if field == "version":
        return dataclasses.replace(stmt, version=stmt.version + data.draw(st.integers(1, 100)))
    if field == "informal":
        return dataclasses.replace(stmt, informal=stmt.informal + "x")
    if field == "formal_source":
        return dataclasses.replace(stmt, formal_source=(stmt.formal_source or "") + "theorem x")
    if field == "source_claim_hash":
        return dataclasses.replace(stmt, source_claim_hash=data.draw(hexdigest))
    if field == "supersedes":
        return dataclasses.replace(stmt, supersedes=data.draw(hexdigest))
    if field == "scope.size_interval":
        lo, hi = stmt.scope["size_interval"]
        return dataclasses.replace(stmt, scope={**stmt.scope, "size_interval": [lo, hi + data.draw(st.integers(1, 30))]})
    if field == "scope.target_family":
        return dataclasses.replace(stmt, scope={**stmt.scope, "target_family": stmt.scope["target_family"] + "x"})
    if field == "scope.param_ranges":
        return dataclasses.replace(stmt, scope={**stmt.scope, "param_ranges": {**stmt.scope["param_ranges"], "r": [1, data.draw(st.integers(2, 40))]}})
    if field == "scope.assumption_set":
        extra = factories.assumption_id(data.draw(st.text(min_size=1, max_size=8)))
        grown = frozenset(stmt.scope["assumption_set"]) | {extra}
        if grown == stmt.scope["assumption_set"]:
            grown = frozenset(stmt.scope["assumption_set"]) | {factories.assumption_id("A7")}
        return dataclasses.replace(stmt, scope={**stmt.scope, "assumption_set": grown})
    if field == "quantities.units":
        return dataclasses.replace(stmt, quantities={**stmt.quantities, "units": {**stmt.quantities["units"], "memory": "bytes"}})
    model = stmt.quantities["cost_model"]
    changed = {"exponent": "3/5", "constant": "9.9", "crossover": 99} if model is None else None
    if model is not None and field == "quantities.cost_model":
        changed = {**model, "crossover": model["crossover"] + data.draw(st.integers(1, 50))}
    return dataclasses.replace(stmt, quantities={**stmt.quantities, "cost_model": changed})


FIELDS = [
    "claim_id",
    "version",
    "informal",
    "formal_source",
    "source_claim_hash",
    "supersedes",
    "scope.size_interval",
    "scope.target_family",
    "scope.param_ranges",
    "scope.assumption_set",
    "quantities.units",
    "quantities.cost_model",
]


def check_one_field_sensitivity(stmt, changed):
    assert changed != stmt
    assert changed.hash != stmt.hash


@given(statements(), st.sampled_from(FIELDS), st.data())
def test_two_statements_differing_in_exactly_one_typed_field_hash_differently(stmt, field, data):
    check_one_field_sensitivity(stmt, mutate_one_field(stmt, field, data))


@given(statements())
def test_a_supersedes_successor_is_a_new_hash(v1):
    v2 = factories.superseding_statement(v1)
    assert v2.supersedes == v1.hash
    assert v2.hash != v1.hash
    assert dataclasses.replace(v1, supersedes=v1.hash).hash != v1.hash


def test_mutant_statement_hash_skips_scope_is_killed():
    a = factories.claim_statement(size=(30, 50), seed=7)
    b = dataclasses.replace(a, scope={**a.scope, "size_interval": [30, 60]})
    check_one_field_sensitivity(a, b)
    with claims_mutants.statement_hash_skips_scope(), pytest.raises(AssertionError):
        check_one_field_sensitivity(dataclasses.replace(a), dataclasses.replace(b))
