import sys
from pathlib import Path

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from cairn import justify
from cairn.justify import CONJECTURE, PROVEN, STRONG_EMPIRICAL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories  # noqa: E402
from mutants import justify_mutants  # noqa: E402

STATEMENT = "s" * 64


def _statement(scope, status="open"):
    return {"hash": STATEMENT, "scope": scope, "status": status}


def _evidence(kind, verdict, population, *, digest="e" * 64, in_sample=None):
    return {
        "hash": digest,
        "kind": kind,
        "verdict": verdict,
        "population": population,
        "assumptions": [],
        "in_sample_sizes": list(in_sample) if in_sample is not None else None,
    }


@st.composite
def covering_case(draw):
    scope = draw(factories.scopes())
    population = draw(factories.covering_populations(scope))
    kind, verdict = draw(st.sampled_from(factories.JUSTIFYING))
    in_sample = population["size_interval"] if verdict == "KEEP_IN_SAMPLE" else None
    ctx = justify.Context(
        grade=draw(st.sampled_from(("Replayable", "Verifiable", "AuditOnly"))),
        repro_passed=draw(st.sampled_from((None, True, False))),
        has_cost_model=draw(st.booleans()),
        approved=True,
    )
    return (
        scope,
        population,
        _evidence(kind, verdict, population, in_sample=in_sample),
        ctx,
    )


@given(covering_case())
def test_mr_w_a_covering_population_always_justifies(case):
    scope, _, evidence, ctx = case
    assert isinstance(
        justify.justify(evidence, _statement(scope), ctx), justify.Justification
    )


@given(covering_case(), st.data())
def test_mr_w_widening_further_keeps_the_same_class(case, data):
    scope, population, evidence, ctx = case
    baseline = justify.justify(evidence, _statement(scope), ctx)
    wider = data.draw(factories.covering_populations(population))
    widened = {
        **evidence,
        "population": {**wider, "assumption_set": population["assumption_set"]},
    }
    result = justify.justify(widened, _statement(scope), ctx)
    assert isinstance(result, justify.Justification) and result.cls == baseline.cls


@given(covering_case(), st.data())
def test_mr_w_moving_an_endpoint_inside_the_scope_is_a_coverage_violation(case, data):
    scope, _, evidence, ctx = case
    narrowed, field = data.draw(factories.narrowed_populations(scope))
    result = justify.justify(
        {**evidence, "population": narrowed}, _statement(scope), ctx
    )
    assert isinstance(result, justify.CoverageViolation) and result.field == field


@given(covering_case(), st.data())
def test_mr_a_an_assumption_outside_the_scope_is_always_a_coverage_violation(
    case, data
):
    scope, population, evidence, ctx = case
    outside = data.draw(
        st.sampled_from(factories.ASSUMPTION_NAMES).filter(
            lambda n: factories.assumption_id(n) not in scope["assumption_set"]
        )
    )
    extra = {
        **population,
        "assumption_set": frozenset(population["assumption_set"])
        | {factories.assumption_id(outside)},
    }
    result = justify.justify({**evidence, "population": extra}, _statement(scope), ctx)
    assert (
        isinstance(result, justify.CoverageViolation) and result.field == "assumptions"
    )


@given(covering_case(), st.data())
def test_mr_w_then_mr_a_still_names_the_assumption(case, data):
    scope, population, evidence, ctx = case
    outside = data.draw(
        st.sampled_from(factories.ASSUMPTION_NAMES).filter(
            lambda n: factories.assumption_id(n) not in scope["assumption_set"]
        )
    )
    wider = data.draw(factories.covering_populations(population))
    both = {
        **wider,
        "assumption_set": frozenset(population["assumption_set"])
        | {factories.assumption_id(outside)},
    }
    result = justify.justify({**evidence, "population": both}, _statement(scope), ctx)
    assert (
        isinstance(result, justify.CoverageViolation) and result.field == "assumptions"
    )


@st.composite
def node_sequence(draw):
    scope = draw(factories.scopes())
    population = draw(factories.covering_populations(scope))
    kinds = draw(
        st.lists(st.sampled_from(factories.JUSTIFYING), min_size=1, max_size=5)
    )
    ctx = justify.Context(
        repro_passed=draw(st.sampled_from((None, True))), approved=True
    )
    nodes = [
        _evidence(
            kind,
            verdict,
            population,
            digest=f"{index:064x}",
            in_sample=population["size_interval"]
            if verdict == "KEEP_IN_SAMPLE"
            else None,
        )
        for index, (kind, verdict) in enumerate(kinds)
    ]
    return scope, nodes, ctx


def _derived(scope, nodes, ctx):
    statement = _statement(scope)
    pairs = [(node, justify.justify(node, statement, ctx)) for node in nodes]
    best = justify.strongest(pairs)
    return justify.SPECULATION if best is None else best[1].cls


@given(node_sequence())
def test_mr_m_the_derived_class_never_falls_as_nodes_are_appended(case):
    scope, nodes, ctx = case
    classes = [
        justify.rank(_derived(scope, nodes[: n + 1], ctx)) for n in range(len(nodes))
    ]
    assert classes == sorted(classes)


EXPECTED_CEILING = {
    "lean_artifact": PROVEN,
    "ladder_table": STRONG_EMPIRICAL,
    "repro_node": STRONG_EMPIRICAL,
    "statistical": STRONG_EMPIRICAL,
    "counterexample_hunt_record": CONJECTURE,
    "model_proof": CONJECTURE,
}


def test_the_shipped_kind_table_is_the_one_the_relations_assume():
    assert justify.KIND_MAX_CLASS == EXPECTED_CEILING


@given(node_sequence())
def test_mr_m_the_derived_class_never_exceeds_the_strongest_kind_ceiling(case):
    scope, nodes, ctx = case
    ceiling = max(justify.rank(EXPECTED_CEILING[node["kind"]]) for node in nodes)
    assert justify.rank(_derived(scope, nodes, ctx)) <= ceiling


@given(covering_case(), st.data())
def test_mr_l_a_class_above_the_kind_ceiling_is_refused_and_one_below_is_not(
    case, data
):
    scope, _, evidence, ctx = case
    ceiling = EXPECTED_CEILING[evidence["kind"]]
    offered = data.draw(st.sampled_from(justify.CLASSES))
    result = justify.justify(
        evidence,
        _statement(scope),
        justify.Context(**{**ctx.__dict__, "offered_class": offered}),
    )
    above = justify.rank(offered) > justify.rank(ceiling)
    assert isinstance(result, justify.LatticeViolation) is above


def _covers(ranges, inputs):
    for axis, (lo, hi) in inputs.items():
        bounds = ranges.get(axis)
        if bounds is None or bounds[0] > lo or bounds[1] < hi:
            return False
    return bool(inputs)


def _expected_cap(summary, inputs):
    origins = [
        value
        for entry in summary["corpus_origins"].values()
        for value in entry.values()
    ]
    if not all(origin == "author_supplied" for origin in origins):
        return False
    if summary["randomized_arm"]:
        return False
    cross_check = summary["cross_check"]
    if not cross_check:
        return True
    return not _covers(cross_check["independent_range"], inputs)


@given(covering_case(), factories.producer_summaries())
def test_mr_c_no_result_ever_exceeds_the_kind_ceiling(case, summary):
    scope, population, evidence, ctx = case
    with_producer = justify.Context(
        **{
            **ctx.__dict__,
            "producer_summary": summary,
            "attempt_inputs": population["param_ranges"],
        }
    )
    result = justify.justify(evidence, _statement(scope), with_producer)
    assume(isinstance(result, justify.Justification))
    assert justify.rank(result.cls) <= justify.rank(EXPECTED_CEILING[evidence["kind"]])


@given(covering_case(), factories.producer_summaries())
def test_mr_c_a_producer_with_no_covering_basis_caps_at_conjecture(case, summary):
    scope, population, evidence, ctx = case
    inputs = population["param_ranges"]
    assume(inputs and _expected_cap(summary, inputs))
    with_producer = justify.Context(
        **{**ctx.__dict__, "producer_summary": summary, "attempt_inputs": inputs}
    )
    result = justify.justify(evidence, _statement(scope), with_producer)
    assume(isinstance(result, justify.Justification))
    assert justify.rank(result.cls) <= justify.rank(CONJECTURE)


@given(factories.arbitrary_records(), factories.scopes())
def test_the_comparator_never_raises_on_an_arbitrary_record(population, scope):
    field = justify.coverage_violation(population, scope)
    assert field is None or field in (
        "population",
        "target_family",
        "size_interval",
        "param_ranges",
        "assumptions",
    )


@given(factories.arbitrary_records(), factories.scopes())
def test_justify_never_raises_on_an_arbitrary_population(population, scope):
    evidence = _evidence("ladder_table", "KEEP", population, in_sample=[0, 100])
    result = justify.justify(
        evidence, _statement(scope), justify.Context(repro_passed=True)
    )
    assert isinstance(result, (justify.Justification, justify.CoverageViolation))


KILLED_BY = {
    "comparator_strict_containment": test_mr_w_a_covering_population_always_justifies,
    "comparator_checks_lo_only": test_mr_w_moving_an_endpoint_inside_the_scope_is_a_coverage_violation,
    "comparator_assumptions_superset": test_mr_a_an_assumption_outside_the_scope_is_always_a_coverage_violation,
    "derive_takes_last_node": test_mr_m_the_derived_class_never_falls_as_nodes_are_appended,
    "kind_table_off_by_one": test_mr_l_a_class_above_the_kind_ceiling_is_refused_and_one_below_is_not,
    "producer_rule_ignores_range": test_mr_c_a_producer_with_no_covering_basis_caps_at_conjecture,
}


@pytest.mark.parametrize("name", sorted(justify_mutants.ALL))
def test_every_named_mutant_is_killed_by_its_relation(name):
    relation = KILLED_BY[name]
    relation()
    with justify_mutants.ALL[name](), pytest.raises(AssertionError):
        relation()


def test_the_mutant_catalog_and_the_relation_map_agree():
    assert sorted(justify_mutants.ALL) == sorted(KILLED_BY)
