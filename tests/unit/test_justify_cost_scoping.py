import sys
from pathlib import Path

import pytest

from cairn import justify
from cairn.justify import CONJECTURE, PROVEN, STRONG_EMPIRICAL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

A1 = factories.assumption_id("A1")
INPUTS = {"bits": [30, 50]}


def scope():
    return {
        "target_family": "toy_curve",
        "size_interval": [30, 50],
        "param_ranges": {"bits": [30, 50]},
        "assumption_set": [A1],
    }


def statement():
    return {"hash": "s" * 64, "scope": scope()}


def evidence(kind, **kw):
    node = {
        "hash": "e" * 64,
        "kind": kind,
        "population": scope(),
        "assumptions": [A1],
        "verdict": None,
        "in_sample_sizes": [30, 50],
    }
    node.update(kw)
    return node


def summary(*, origins, randomized_arm=False, cross_check=None):
    return {"corpus_origins": origins, "randomized_arm": randomized_arm, "cross_check": cross_check}


@pytest.mark.parametrize("kind", ["repro_node", "statistical"])
def test_a_cost_model_statement_takes_the_conjecture_ceiling_from_a_non_ladder_kind(kind):
    result = justify.justify(evidence(kind), statement(), justify.Context(has_cost_model=True))
    assert isinstance(result, justify.Justification)
    assert result.cls == CONJECTURE
    assert result.reason == "cost-model-statement"


@pytest.mark.parametrize("kind", ["repro_node", "statistical"])
def test_the_same_kind_reaches_strong_empirical_when_the_statement_carries_no_cost_model(kind):
    result = justify.justify(evidence(kind), statement(), justify.Context())
    assert result.cls == STRONG_EMPIRICAL
    assert result.reason == f"{kind}-population"


def test_a_ladder_table_is_the_one_kind_a_cost_model_statement_takes_strong_empirical_from():
    node = evidence("ladder_table", verdict="KEEP")
    result = justify.justify(node, statement(), justify.Context(has_cost_model=True, repro_passed=True))
    assert result.cls == STRONG_EMPIRICAL
    assert result.reason == "ladder-keep-repro"


def test_a_ladder_keep_without_a_passing_repro_node_is_capped():
    node = evidence("ladder_table", verdict="KEEP")
    result = justify.justify(node, statement(), justify.Context(repro_passed=False))
    assert result.cls == CONJECTURE
    assert result.reason == "ladder-keep-no-repro"


def test_statistical_evidence_offered_for_proven_is_a_lattice_violation():
    result = justify.justify(evidence("statistical"), statement(), justify.Context(offered_class=PROVEN))
    assert isinstance(result, justify.LatticeViolation)
    assert result.reason == "statistical-cannot-justify-PROVEN"


def test_an_author_supplied_only_producer_caps_the_node_at_conjecture():
    ctx = justify.Context(
        producer_summary=summary(origins={"toy_curve": {"c30": justify.AUTHOR_SUPPLIED}}),
        attempt_inputs=INPUTS,
    )
    assert justify.justify(evidence("statistical"), statement(), ctx).cls == CONJECTURE


@pytest.mark.parametrize(
    "kw",
    [
        {"origins": {"toy_curve": {"c30": "generated"}}},
        {"origins": {"toy_curve": {"c30": justify.AUTHOR_SUPPLIED}}, "randomized_arm": True},
        {
            "origins": {"toy_curve": {"c30": justify.AUTHOR_SUPPLIED}},
            "cross_check": {"independent_range": {"bits": [20, 60]}},
        },
    ],
)
def test_standing_survives_a_generated_origin_a_randomized_arm_or_a_covering_cross_check(kw):
    ctx = justify.Context(producer_summary=summary(**kw), attempt_inputs=INPUTS)
    assert justify.justify(evidence("statistical"), statement(), ctx).cls == STRONG_EMPIRICAL


def test_a_cross_check_whose_range_misses_the_attempt_s_inputs_does_not_restore_standing():
    ctx = justify.Context(
        producer_summary=summary(
            origins={"toy_curve": {"c30": justify.AUTHOR_SUPPLIED}},
            cross_check={"independent_range": {"bits": [40, 60]}},
        ),
        attempt_inputs=INPUTS,
    )
    assert justify.justify(evidence("statistical"), statement(), ctx).cls == CONJECTURE


def test_the_standing_cap_and_the_cost_model_ceiling_compose_to_the_weaker_of_the_two():
    ctx = justify.Context(
        has_cost_model=True,
        producer_summary=summary(origins={"toy_curve": {"c30": justify.AUTHOR_SUPPLIED}}),
        attempt_inputs=INPUTS,
    )
    assert justify.justify(evidence("statistical"), statement(), ctx).cls == CONJECTURE
