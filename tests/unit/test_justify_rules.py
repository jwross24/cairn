import sys
from pathlib import Path

import pytest

from cairn import justify
from cairn.justify import CONJECTURE, PROVEN, SPECULATION, STRONG_EMPIRICAL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

A1 = factories.assumption_id("A1")
A2 = factories.assumption_id("A2")


def _scope(family="toy_curve", size=(30, 50), assumptions=(A1,), param_ranges=None):
    return {
        "target_family": family,
        "size_interval": list(size),
        "param_ranges": {"bits": list(size)} if param_ranges is None else param_ranges,
        "assumption_set": list(assumptions),
    }


def test_the_class_order_is_total_and_ascending():
    assert justify.CLASSES == (
        "SPECULATION",
        "CONJECTURE",
        "STRONG-EMPIRICAL",
        "PROVEN",
    )
    assert (SPECULATION, CONJECTURE, STRONG_EMPIRICAL, PROVEN) == justify.CLASSES
    assert [justify.rank(c) for c in ("SPECULATION", "CONJECTURE", "STRONG-EMPIRICAL", "PROVEN")] == [0, 1, 2, 3]
    assert justify.weakest(PROVEN, CONJECTURE) == CONJECTURE
    assert justify.weakest(CONJECTURE, PROVEN) == CONJECTURE
    assert justify.weakest(PROVEN, PROVEN) == PROVEN


@pytest.mark.parametrize(
    ("outer", "inner", "expected"),
    [
        ([30, 50], [30, 50], True),
        ([30, 50], [40, 45], True),
        ([30, 50], [29, 50], False),
        ([30, 50], [30, 51], False),
        ([30, 50], 40, True),
        (40, [40, 40], True),
        ([50, 30], [40, 45], False),
        ([30, 50], [45, 40], False),
        ([30, None], [30, 50], False),
        (None, [30, 50], False),
        ([30, 50], None, False),
        (["30", "50"], [30, 50], False),
        ([True, 50], [30, 50], False),
        ([0, 10**40], [10**30, 10**31], True),
    ],
    ids=[
        "equal_endpoints",
        "strictly_inside",
        "lo_below",
        "hi_above",
        "scalar_inner",
        "scalar_outer",
        "inverted_outer",
        "inverted_inner",
        "none_endpoint",
        "outer_missing",
        "inner_missing",
        "string_endpoints",
        "bool_endpoint",
        "huge_ints",
    ],
)
def test_interval_containment(outer, inner, expected):
    assert justify.contains(outer, inner) is expected


@pytest.mark.parametrize(
    ("inner", "outer", "expected"),
    [
        ((), (), True),
        ((), (A1,), True),
        ((A1,), (A1,), True),
        ((A1,), (A1, A2), True),
        ((A1, A2), (A1,), False),
        (None, (A1,), True),
        (A1, (A1,), False),
        ((A1,), A1, False),
    ],
    ids=[
        "both_empty",
        "empty_inner",
        "equal",
        "proper_subset",
        "superset",
        "none_inner",
        "bare_string_inner",
        "bare_string_outer",
    ],
)
def test_assumption_subset(inner, outer, expected):
    assert justify.subset(inner, outer) is expected


@pytest.mark.parametrize(
    ("population", "expected"),
    [
        (_scope(), None),
        (_scope(size=(20, 60), param_ranges={"bits": [20, 60]}), None),
        (_scope(assumptions=()), None),
        (_scope(family="other_curve"), "target_family"),
        (_scope(size=(40, 50), param_ranges={"bits": [30, 50]}), "size_interval"),
        (_scope(param_ranges={"bits": [35, 50]}), "param_ranges"),
        (_scope(param_ranges={}), "param_ranges"),
        (_scope(assumptions=(A1, A2)), "assumptions"),
        ("not-a-record", "population"),
        (_scope(param_ranges={"bits": [30, 50], "cores": [1, 8]}), None),
    ],
    ids=[
        "identical",
        "wider",
        "fewer_assumptions",
        "family_mismatch",
        "size_gap",
        "param_gap",
        "param_axis_absent",
        "extra_assumption",
        "not_a_record",
        "extra_axis",
    ],
)
def test_coverage_comparator(population, expected):
    assert justify.coverage_violation(population, _scope()) == expected


@pytest.mark.parametrize(
    ("kind", "verdict", "repro", "grade", "cost_model", "expected"),
    [
        ("ladder_table", "KEEP", True, "Replayable", False, STRONG_EMPIRICAL),
        ("ladder_table", "KEEP", None, "Replayable", False, CONJECTURE),
        ("ladder_table", "KEEP", False, "Replayable", False, CONJECTURE),
        ("ladder_table", "KEEP", True, "AuditOnly", False, CONJECTURE),
        ("ladder_table", "KEEP_IN_SAMPLE", True, "Replayable", False, STRONG_EMPIRICAL),
        ("ladder_table", "REJECT", True, "Replayable", False, "Absent"),
        ("ladder_table", "INCONCLUSIVE", True, "Replayable", False, "Absent"),
        ("repro_node", None, True, "Replayable", False, STRONG_EMPIRICAL),
        ("repro_node", None, True, "Replayable", True, CONJECTURE),
        ("statistical", None, None, "Replayable", False, STRONG_EMPIRICAL),
        ("statistical", None, None, "Replayable", True, CONJECTURE),
        ("model_proof", None, None, "Replayable", False, CONJECTURE),
        (
            "counterexample_hunt_record",
            "SURVIVED",
            None,
            "Replayable",
            False,
            CONJECTURE,
        ),
        (
            "counterexample_hunt_record",
            "KILLED",
            None,
            "Replayable",
            False,
            "Refutation",
        ),
        (
            "counterexample_hunt_record",
            "INCOMPLETE",
            None,
            "Replayable",
            False,
            "Absent",
        ),
        ("lean_artifact", None, None, "Replayable", False, "Pending"),
        ("not_a_kind", None, True, "Replayable", False, "Absent"),
    ],
    ids=[
        "ladder_keep_repro",
        "ladder_keep_no_repro",
        "ladder_keep_failed_repro",
        "ladder_keep_audit_only",
        "ladder_keep_in_sample",
        "ladder_reject",
        "ladder_inconclusive",
        "repro_node",
        "repro_node_cost_model",
        "statistical",
        "statistical_cost_model",
        "model_proof",
        "hunt_survived",
        "hunt_killed",
        "hunt_incomplete",
        "lean_artifact_unreviewed",
        "unknown_kind",
    ],
)
def test_kind_to_max_class(kind, verdict, repro, grade, cost_model, expected):
    evidence = {
        "hash": "e" * 64,
        "kind": kind,
        "verdict": verdict,
        "population": _scope(),
        "assumptions": [],
        "in_sample_sizes": [30, 50],
    }
    ctx = justify.Context(grade=grade, repro_passed=repro, has_cost_model=cost_model)
    result = justify.justify(evidence, {"hash": "s" * 64, "scope": _scope()}, ctx)
    if expected in justify.CLASSES:
        assert isinstance(result, justify.Justification) and result.cls == expected
    else:
        assert type(result).__name__ == expected


def test_lean_artifact_with_an_approve_verdict_is_the_only_route_to_proven():
    evidence = {
        "hash": "e" * 64,
        "kind": "lean_artifact",
        "verdict": None,
        "population": _scope(),
        "assumptions": [],
    }
    statement = {"hash": "s" * 64, "scope": _scope()}
    assert isinstance(justify.justify(evidence, statement, justify.Context()), justify.Pending)
    approved = justify.justify(evidence, statement, justify.Context(approved=True))
    assert isinstance(approved, justify.Justification) and approved.cls == PROVEN
    assert {kind for kind, cls in justify.KIND_MAX_CLASS.items() if cls == PROVEN} == {"lean_artifact"}


def test_a_class_above_the_kind_maximum_is_a_lattice_violation():
    evidence = {
        "hash": "e" * 64,
        "kind": "statistical",
        "population": _scope(),
        "assumptions": [],
        "verdict": None,
    }
    result = justify.justify(
        evidence,
        {"hash": "s" * 64, "scope": _scope()},
        justify.Context(offered_class=PROVEN),
    )
    assert isinstance(result, justify.LatticeViolation)
    assert result.reason == "statistical-cannot-justify-PROVEN"


def test_a_class_at_or_below_the_kind_maximum_is_not_a_lattice_violation():
    evidence = {
        "hash": "e" * 64,
        "kind": "statistical",
        "population": _scope(),
        "assumptions": [],
        "verdict": None,
    }
    result = justify.justify(
        evidence,
        {"hash": "s" * 64, "scope": _scope()},
        justify.Context(offered_class=STRONG_EMPIRICAL),
    )
    assert isinstance(result, justify.Justification) and result.cls == STRONG_EMPIRICAL


COVERING_CROSS_CHECK = {"axis": "algorithm", "independent_range": {"bits": [0, 50]}}
NARROW_CROSS_CHECK = {"axis": "algorithm", "independent_range": {"bits": [0, 35]}}
AUTHOR_ORIGINS = {"F5": {"P": "author_supplied", "p": "author_supplied"}}
MIXED_ORIGINS = {"F5": {"P": "author_supplied", "p": "upstream_vendored"}}
INPUTS = {"bits": [40, 50]}


@pytest.mark.parametrize(
    ("origins", "randomized_arm", "cross_check", "inputs", "expected"),
    [
        (AUTHOR_ORIGINS, False, None, INPUTS, True),
        (AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK, INPUTS, False),
        (AUTHOR_ORIGINS, False, NARROW_CROSS_CHECK, INPUTS, True),
        (AUTHOR_ORIGINS, True, None, INPUTS, False),
        (MIXED_ORIGINS, False, None, INPUTS, False),
        (AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK, None, True),
        ([], False, None, INPUTS, True),
        (AUTHOR_ORIGINS, False, {"axis": "algorithm"}, INPUTS, True),
    ],
    ids=[
        "all_author_supplied",
        "cross_check_covers_the_inputs",
        "cross_check_range_misses_the_inputs",
        "randomized_arm",
        "one_upstream_origin",
        "no_inputs_to_cover",
        "empty_corpus",
        "cross_check_without_a_range",
    ],
)
def test_producer_standing(origins, randomized_arm, cross_check, inputs, expected):
    summary = factories.selftest_summary(origins, randomized_arm, cross_check)
    assert justify.producer_capped(summary, inputs) is expected


def test_a_capped_producer_pulls_a_strong_empirical_node_to_conjecture():
    evidence = {
        "hash": "e" * 64,
        "kind": "ladder_table",
        "verdict": "KEEP",
        "population": _scope(),
        "assumptions": [],
        "in_sample_sizes": [30, 50],
    }
    statement = {"hash": "s" * 64, "scope": _scope()}
    capped = justify.Context(
        repro_passed=True,
        producer_summary=factories.selftest_summary(AUTHOR_ORIGINS, False, None),
        attempt_inputs=INPUTS,
    )
    covered = justify.Context(
        repro_passed=True,
        producer_summary=factories.selftest_summary(AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK),
        attempt_inputs=INPUTS,
    )
    assert justify.justify(evidence, statement, capped).cls == CONJECTURE
    assert justify.justify(evidence, statement, covered).cls == STRONG_EMPIRICAL


def test_a_refuted_statement_admits_no_positive_class():
    evidence = {
        "hash": "e" * 64,
        "kind": "ladder_table",
        "verdict": "KEEP",
        "population": _scope(),
        "assumptions": [],
        "in_sample_sizes": [30, 50],
    }
    result = justify.justify(
        evidence,
        {"hash": "s" * 64, "scope": _scope()},
        justify.Context(repro_passed=True, statement_status="refuted"),
    )
    assert isinstance(result, justify.LatticeViolation) and result.reason == "refuted-statement"


def test_a_disowned_attempt_is_absent_while_an_audit_only_grade_is_not():
    evidence = {
        "hash": "e" * 64,
        "kind": "ladder_table",
        "verdict": "KEEP",
        "population": _scope(),
        "assumptions": [],
        "in_sample_sizes": [30, 50],
    }
    statement = {"hash": "s" * 64, "scope": _scope()}
    disowned = justify.justify(evidence, statement, justify.Context(repro_passed=True, disowned=True))
    audit_only = justify.justify(
        evidence,
        statement,
        justify.Context(repro_passed=True, grade=justify.AUDIT_ONLY),
    )
    assert isinstance(disowned, justify.Absent) and disowned.reason == "disowned"
    assert isinstance(audit_only, justify.Justification) and audit_only.cls == CONJECTURE


def test_the_node_s_own_assumptions_join_the_population_s_for_coverage():
    evidence = {
        "hash": "e" * 64,
        "kind": "repro_node",
        "verdict": None,
        "population": _scope(assumptions=(A1,)),
        "assumptions": [A2],
    }
    result = justify.justify(evidence, {"hash": "s" * 64, "scope": _scope()}, justify.Context())
    assert isinstance(result, justify.CoverageViolation) and result.field == "assumptions"


def test_keep_in_sample_needs_the_scope_inside_the_in_sample_sizes():
    def node(in_sample):
        return {
            "hash": "e" * 64,
            "kind": "ladder_table",
            "verdict": "KEEP_IN_SAMPLE",
            "population": _scope(size=(20, 60), param_ranges={"bits": [20, 60]}),
            "assumptions": [],
            "in_sample_sizes": in_sample,
        }

    statement = {"hash": "s" * 64, "scope": _scope()}
    ctx = justify.Context(repro_passed=True)
    inside = justify.justify(node([30, 50]), statement, ctx)
    outside = justify.justify(node([30, 45]), statement, ctx)
    assert isinstance(inside, justify.Justification) and inside.cls == STRONG_EMPIRICAL
    assert isinstance(outside, justify.Absent)


@pytest.mark.parametrize(
    ("population", "expected"),
    [
        (
            '{"target_family": "toy_curve", "size_interval": [30, 50], "param_ranges": {"bits": [30, 50]}, "assumption_set": []}',
            None,
        ),
        ("{not json at all", "population"),
        ("[]", "population"),
        ({**_scope(), "assumption_set": [["unhashable"]]}, "assumptions"),
    ],
    ids=[
        "json_string",
        "unparsable_json",
        "json_but_not_a_record",
        "unhashable_assumption",
    ],
)
def test_a_population_that_is_not_a_plain_record(population, expected):
    evidence = {
        "hash": "e" * 64,
        "kind": "repro_node",
        "verdict": None,
        "population": population,
        "assumptions": [],
    }
    result = justify.justify(evidence, {"hash": "s" * 64, "scope": _scope()}, justify.Context())
    if expected is None:
        assert isinstance(result, justify.Justification)
    else:
        assert isinstance(result, justify.CoverageViolation) and result.field == expected


def test_a_scope_naming_no_parameter_ranges_constrains_only_its_size():
    scope = {
        "target_family": "toy_curve",
        "size_interval": [30, 50],
        "assumption_set": [A1],
    }
    evidence = {
        "hash": "e" * 64,
        "kind": "repro_node",
        "verdict": None,
        "population": _scope(param_ranges={}),
        "assumptions": [],
    }
    result = justify.justify(evidence, {"hash": "s" * 64, "scope": scope}, justify.Context())
    assert isinstance(result, justify.Justification)


@pytest.mark.parametrize("origins", ["author_supplied", 7, None], ids=["a_bare_string", "a_number", "absent"])
def test_a_selftest_summary_whose_origins_are_not_a_collection_caps(origins):
    summary = factories.selftest_summary(origins, False, None)
    assert justify.producer_capped(summary, INPUTS) is True
