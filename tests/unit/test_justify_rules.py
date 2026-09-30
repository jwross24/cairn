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


def _statement(scope):
    return {"hash": "s" * 64, "scope": scope}


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
    ("population", "scope", "expected"),
    [
        (_scope(size=(40, 45)), _scope(), None),
        (_scope(size=(20, 60)), _scope(), "size_interval"),
        (_scope(size=(40, 45), param_ranges={"bits": [20, 45]}), _scope(), "param_ranges"),
        (_scope(size=(40, 45), param_ranges={}), _scope(), "param_ranges"),
        (_scope(family="other_curve", size=(40, 45)), _scope(), "target_family"),
        (_scope(size=(40, 45), assumptions=()), _scope(), "assumptions"),
        (_scope(size=(30, None)), _scope(), "size_interval"),
        (_scope(size=(40, 45), param_ranges={"bits": [40, None]}), _scope(), "param_ranges"),
        ("not-a-record", _scope(), "population"),
    ],
    ids=[
        "narrower",
        "outside_size",
        "outside_param",
        "missing_required_axis",
        "wrong_family",
        "missing_required_assumption",
        "invalid_interval",
        "invalid_range",
        "invalid_record",
    ],
)
def test_counterexample_coverage_requires_a_witness_inside_the_statement(population, scope, expected):
    assert justify.counterexample_coverage_violation(population, scope) == expected


def _hunt_evidence(population, verdict="KILLED", assumptions=()):
    return {
        "hash": "e" * 64,
        "kind": "counterexample_hunt_record",
        "verdict": verdict,
        "population": population,
        "assumptions": list(assumptions),
    }


def test_a_narrower_killed_hunt_record_is_a_refutation():
    evidence = _hunt_evidence(_scope(size=(40, 45), param_ranges={"bits": [40, 45]}))
    result = justify.justify(evidence, _statement(_scope()), justify.Context())
    assert isinstance(result, justify.Refutation)
    assert result.evidence_hash == evidence["hash"]


@pytest.mark.parametrize(
    ("population", "scope", "field"),
    [
        (_scope(size=(20, 40)), _scope(), "size_interval"),
        (_scope(size=(40, 45), param_ranges={"bits": [20, 40]}), _scope(), "param_ranges"),
        (_scope(size=(40, 45), param_ranges={}), _scope(), "param_ranges"),
        (_scope(family="other_curve", size=(40, 45)), _scope(), "target_family"),
        (_scope(size=(40, 45), assumptions=()), _scope(), "assumptions"),
    ],
    ids=["outside_size", "outside_param", "missing_required_axis", "wrong_family", "missing_assumption"],
)
def test_an_out_of_scope_killed_hunt_record_is_refused(population, scope, field):
    result = justify.justify(_hunt_evidence(population), _statement(scope), justify.Context())
    assert isinstance(result, justify.CoverageViolation) and result.field == field


@pytest.mark.parametrize("ctx", [justify.Context(disowned=True), justify.Context(inadmissible=True)])
def test_a_disowned_or_inadmissible_killed_hunt_record_stays_absent(ctx):
    evidence = _hunt_evidence(_scope(size=(40, 45), param_ranges={"bits": [40, 45]}))
    result = justify.justify(evidence, _statement(_scope()), ctx)
    assert isinstance(result, justify.Absent)


def test_a_narrower_survived_hunt_record_keeps_the_positive_coverage_rule():
    evidence = _hunt_evidence(
        _scope(size=(40, 45), param_ranges={"bits": [40, 45]}),
        verdict="SURVIVED",
    )
    result = justify.justify(evidence, _statement(_scope()), justify.Context())
    assert isinstance(result, justify.CoverageViolation) and result.field == "size_interval"


@pytest.mark.parametrize("kind", ["lean_artifact", "ladder_table", "repro_node", "statistical", "model_proof"])
def test_other_kinds_keep_the_positive_coverage_rule(kind):
    evidence = {
        **_hunt_evidence(_scope(size=(40, 45), param_ranges={"bits": [40, 45]})),
        "kind": kind,
        "verdict": None,
    }
    result = justify.justify(evidence, _statement(_scope()), justify.Context())
    assert isinstance(result, justify.CoverageViolation) and result.field == "size_interval"


@pytest.mark.parametrize(
    ("kind", "verdict", "repro", "grade", "cost_model", "expected"),
    [
        ("ladder_table", "KEEP", True, "Replayable", False, STRONG_EMPIRICAL),
        ("ladder_table", "KEEP", None, "Replayable", False, CONJECTURE),
        ("ladder_table", "KEEP", False, "Replayable", False, CONJECTURE),
        ("ladder_table", "KEEP", True, "AuditOnly", False, "Absent"),
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
        ("lean_artifact", None, None, "Replayable", False, "Absent"),
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


def test_an_approve_verdict_without_a_bound_gate_run_cannot_justify_proven():
    evidence = {
        "hash": "e" * 64,
        "kind": "lean_artifact",
        "verdict": None,
        "population": _scope(),
        "assumptions": [],
    }
    statement = {"hash": "s" * 64, "scope": _scope()}
    assert isinstance(justify.justify(evidence, statement, justify.Context()), justify.Absent)
    approved = justify.justify(evidence, statement, justify.Context(approved=True))
    assert isinstance(approved, justify.Absent) and approved.reason == "lean-gate-absent"
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


def test_axis_contributions_are_clipped_to_the_requested_interval():
    checks = [
        {"axis": "algorithm", "independent_range": {"bits": [0, 50]}},
        {"axis": "implementation", "independent_range": {"bits": [30, 60]}},
    ]
    coverage = justify.cross_check_covers(checks, {"bits": [10, 60]})
    assert coverage.covered is True
    assert coverage.dimensions == {"bits": True}
    assert coverage.contributions == {"bits": {"algorithm": [10, 50], "implementation": [30, 60]}}
    summary = factories.selftest_summary(AUTHOR_ORIGINS, False, checks)
    assert justify.producer_capped(summary, {"bits": [10, 60]}) is False


@pytest.mark.parametrize(("start", "covered"), [(20, True), (21, True), (22, False), (30, False)])
def test_integer_union_covers_adjacent_ranges_and_refuses_gaps(start, covered):
    checks = [
        {"axis": "algorithm", "independent_range": {"bits": [10, 20]}},
        {"axis": "implementation", "independent_range": {"bits": [start, 40]}},
    ]
    coverage = justify.cross_check_covers(checks, {"bits": [10, 40]})
    assert coverage.covered is covered
    assert coverage.dimensions == {"bits": covered}
    assert coverage.contributions == {"bits": {"algorithm": [10, 20], "implementation": [start, 40]}}


def test_axes_missing_requested_dimensions_contribute_nothing():
    checks = [
        {"axis": "algorithm", "independent_range": {"bits": [0, 50]}},
        {"axis": "implementation", "independent_range": {"seed": [1, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"bits": 40, "seed": 5, "missing": 1})
    assert coverage.covered is False
    assert coverage.dimensions == {"bits": False, "seed": False, "missing": False}
    assert coverage.contributions == {
        "bits": {},
        "seed": {},
        "missing": {},
    }


def test_a_point_cannot_borrow_dimensions_from_distinct_axis_boxes():
    checks = [
        {"axis": "algorithm", "independent_range": {"x": [0, 10], "y": [0, 0]}},
        {"axis": "implementation", "independent_range": {"x": [0, 0], "y": [0, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"x": 5, "y": 5})
    assert coverage.covered is False
    assert coverage.dimensions == {"x": False, "y": False}
    assert coverage.contributions == {"x": {}, "y": {}}


def test_l_shaped_axis_boxes_do_not_cover_their_bounding_square():
    checks = [
        {"axis": "algorithm", "independent_range": {"x": [0, 10], "y": [0, 0]}},
        {"axis": "implementation", "independent_range": {"x": [0, 0], "y": [0, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"x": [0, 10], "y": [0, 10]})
    assert coverage.covered is False
    assert coverage.dimensions == {"x": True, "y": True}
    assert coverage.contributions == {
        "x": {"algorithm": [0, 10], "implementation": [0, 0]},
        "y": {"algorithm": [0, 0], "implementation": [0, 10]},
    }
    assert justify.producer_capped(
        factories.selftest_summary(AUTHOR_ORIGINS, False, checks), {"x": [0, 10], "y": [0, 10]}
    )


@pytest.mark.parametrize("start", [4, 5, 6])
def test_axis_boxes_jointly_cover_a_rectangle_without_double_counting_overlap(start):
    checks = [
        {"axis": "algorithm", "independent_range": {"x": [0, 5], "y": [-5, 15]}},
        {"axis": "implementation", "independent_range": {"x": [start, 10], "y": [0, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"x": [0, 10], "y": [0, 10]})
    assert coverage.covered is True
    assert coverage.dimensions == {"x": True, "y": True}
    assert coverage.contributions == {
        "x": {"algorithm": [0, 5], "implementation": [start, 10]},
        "y": {"algorithm": [0, 10], "implementation": [0, 10]},
    }


def test_overlapping_boxes_are_not_counted_twice_to_fill_an_uncovered_region():
    checks = [
        {"axis": "algorithm", "independent_range": {"x": [0, 5], "y": [0, 10]}},
        {"axis": "implementation", "independent_range": {"x": [0, 5], "y": [0, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"x": [0, 11], "y": [0, 10]})
    assert coverage.covered is False
    assert coverage.dimensions == {"x": False, "y": True}


@pytest.mark.parametrize("algorithm_range", [{"x": [0, 10], "y": [0, 0]}, {"x": [0, 10]}])
def test_scalar_point_receives_credit_from_only_its_complete_covering_box(algorithm_range):
    checks = [
        {"axis": "algorithm", "independent_range": algorithm_range},
        {"axis": "implementation", "independent_range": {"x": [0, 10], "y": [0, 10]}},
    ]
    coverage = justify.cross_check_covers(checks, {"x": 5, "y": 5})
    assert coverage.covered is True
    assert coverage.dimensions == {"x": True, "y": True}
    assert coverage.contributions == {
        "x": {"implementation": [5, 5]},
        "y": {"implementation": [5, 5]},
    }


def test_extra_dimensions_in_a_singular_axis_less_record_do_not_expand_the_request():
    coverage = justify.cross_check_covers({"independent_range": {"bits": [0, 50], "seed": [10, 1]}}, INPUTS)
    assert coverage.record() == {"covered": True, "dimensions": {"bits": True}, "contributions": {"bits": {}}}


@pytest.mark.parametrize("inputs", [None, {}, [], {"bits": True}, {"bits": [50, 40]}, {"bits": "40"}])
def test_invalid_cross_check_inputs_are_uncovered(inputs):
    assert justify.cross_check_covers(COVERING_CROSS_CHECK, inputs).covered is False


@pytest.mark.parametrize(
    "checks",
    [
        [],
        [None],
        [{"axis": "algorithm"}],
        [{"axis": "vibes", "independent_range": {"bits": [0, 60]}}],
        [{"independent_range": {"bits": [0, 60]}}],
        [COVERING_CROSS_CHECK, COVERING_CROSS_CHECK],
        [COVERING_CROSS_CHECK, {"axis": "implementation", "independent_range": {}}],
        [COVERING_CROSS_CHECK, {"axis": "implementation", "independent_range": {"bits": [60, 0]}}],
        [COVERING_CROSS_CHECK, {"axis": "implementation", "independent_range": {"bits": [False, 60]}}],
        [COVERING_CROSS_CHECK, {"axis": "implementation", "independent_range": {"bits": ["0", 60]}}],
    ],
)
def test_malformed_plural_records_do_not_borrow_a_valid_records_coverage(checks):
    coverage = justify.cross_check_covers(checks, INPUTS)
    assert coverage.covered is False
    assert coverage.dimensions == {"bits": False}


def test_a_singular_axis_less_record_keeps_coverage_without_inventing_attribution():
    coverage = justify.cross_check_covers({"independent_range": {"bits": [0, 50]}}, INPUTS)
    assert coverage.covered is True
    assert coverage.dimensions == {"bits": True}
    assert coverage.contributions == {"bits": {}}


def test_coverage_requires_an_explicit_verdict_access():
    with pytest.raises(TypeError, match=r"use coverage\.covered"):
        bool(justify.cross_check_covers(COVERING_CROSS_CHECK, INPUTS))


def test_deferred_justification_keeps_axis_attribution():
    scope = _scope()
    evidence = {"hash": "e" * 64, "kind": "statistical", "population": scope, "assumptions": []}
    ctx = justify.Context(
        tier=2,
        producer_summary=factories.selftest_summary(AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK),
        attempt_inputs=INPUTS,
    )
    result = justify.justify(evidence, {"hash": "s" * 64, "scope": scope}, ctx)
    assert result.cls == CONJECTURE
    assert result.reason == justify.REASON_REPRO_DEFERRED
    assert result.cross_check_coverage.record() == {
        "covered": True,
        "dimensions": {"bits": True},
        "contributions": {"bits": {"algorithm": [40, 50]}},
    }


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
    assert isinstance(audit_only, justify.Absent) and audit_only.reason == justify.REASON_AUDIT_ONLY


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
