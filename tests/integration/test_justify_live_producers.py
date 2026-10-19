import factories
import pytest
from _justify_live_helpers import (
    AUTHOR_ORIGINS,
    COVERING_CROSS_CHECK,
    GENERATED_ORIGINS,
    certify,
    judge,
    live_ladder_node,
    statement_with,
    statistical_node,
)
from integration.test_justify import _bind_counterexample

from cairn import claims, foundations, justify, laddertable
from cairn.justify import CONJECTURE, PROVEN, STRONG_EMPIRICAL


def test_a_real_ladder_table_with_its_recomputed_repro_record_justifies_strong_empirical(writer, plan, attest_path):
    statement = statement_with(writer, cost_model=True)
    identity = certify(writer, "11" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    table, node, recomputation = live_ladder_node(writer, plan, statement, producer_identity=identity)
    assert recomputation.agrees, recomputation.divergences
    assert laddertable.read(writer, table.hash) is not None
    result = judge(writer, node, statement, attest_path)
    assert isinstance(result, justify.Justification), result
    assert result.cls == STRONG_EMPIRICAL
    assert result.reason == "ladder-keep-repro"


def test_a_real_statistical_node_offered_for_the_same_cost_model_statement_takes_the_conjecture_ceiling(
    writer, plan, attest_path
):
    statement = statement_with(writer, cost_model=True, seed=2)
    identity = certify(writer, "22" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    node = statistical_node(writer, statement, producer_identity=identity)
    result = judge(writer, node, statement, attest_path)
    assert result.cls == CONJECTURE
    assert result.reason == "cost-model-statement"


def test_the_same_real_statistical_node_reaches_strong_empirical_for_a_statement_with_no_cost_model(
    writer, plan, attest_path
):
    statement = statement_with(writer, cost_model=None, seed=3)
    identity = certify(writer, "33" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    node = statistical_node(writer, statement, producer_identity=identity)
    result = judge(writer, node, statement, attest_path)
    assert result.cls == STRONG_EMPIRICAL
    assert result.reason == "statistical-population"


def test_a_real_statistical_node_offered_for_proven_is_a_lattice_violation(writer, plan, attest_path):
    statement = statement_with(writer, cost_model=None, seed=4)
    identity = certify(writer, "44" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    node = statistical_node(writer, statement, producer_identity=identity)
    result = judge(writer, node, statement, attest_path, offered_class=PROVEN)
    assert isinstance(result, justify.LatticeViolation)
    assert result.reason == "statistical-cannot-justify-PROVEN"


def test_a_producer_whose_real_certificate_is_author_supplied_only_caps_a_live_node_at_conjecture(
    writer, plan, attest_path
):
    statement = statement_with(writer, cost_model=None, seed=5)
    identity = certify(writer, "55" * 32, factories.selftest_summary(AUTHOR_ORIGINS, False, None))
    node = statistical_node(writer, statement, producer_identity=identity)
    result = judge(writer, node, statement, attest_path)
    assert result.cls == CONJECTURE


@pytest.mark.parametrize(
    ("case", "summary_kw", "expected"),
    [
        ("generated-origin", (GENERATED_ORIGINS, False, None), STRONG_EMPIRICAL),
        ("randomized-arm", (AUTHOR_ORIGINS, True, None), STRONG_EMPIRICAL),
        ("covering-cross-check", (AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK), STRONG_EMPIRICAL),
        (
            "cross-check-misses-inputs",
            (AUTHOR_ORIGINS, False, {"axis": "algorithm", "independent_range": {"bits": [55, 60]}}),
            CONJECTURE,
        ),
    ],
)
def test_producer_standing_reads_the_certificate_row_the_substrate_holds(
    writer, plan, attest_path, case, summary_kw, expected
):
    statement = statement_with(writer, cost_model=None, seed=6)
    identity = certify(writer, f"{len(case):02x}" * 32, factories.selftest_summary(*summary_kw))
    node = statistical_node(writer, statement, producer_identity=identity)
    assert judge(writer, node, statement, attest_path).cls == expected


def test_a_node_declaring_a_wide_population_over_a_narrow_run_is_judged_on_the_run(writer, plan, attest_path):
    statement = statement_with(writer, cost_model=None, seed=8, size=(20, 80))
    identity = certify(
        writer,
        "7a" * 32,
        factories.selftest_summary(
            AUTHOR_ORIGINS, False, {"axis": "algorithm", "independent_range": {"bits": [30, 60]}}
        ),
    )
    _, node, _ = live_ladder_node(writer, plan, statement, producer_identity=identity, run_id="run-wide")
    assert laddertable.inputs_for_attempt(writer, "attempt-run-wide") == {"bits": [30, 60]}
    assert judge(writer, node, statement, attest_path).cls == STRONG_EMPIRICAL


def test_a_node_carrying_no_attempt_is_judged_on_its_declared_population(writer, plan, attest_path):
    statement = statement_with(writer, cost_model=None, seed=9, size=(20, 80))
    identity = certify(
        writer,
        "8b" * 32,
        factories.selftest_summary(
            AUTHOR_ORIGINS, False, {"axis": "algorithm", "independent_range": {"bits": [0, 90]}}
        ),
    )
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        statement.scope,
        frozenset(statement.scope["assumption_set"]),
        producer=(identity, "skill"),
        seed=11,
        attempt_id=None,
    )
    claims.write_evidence_node(writer, node)
    assert judge(writer, node, statement, attest_path).cls == STRONG_EMPIRICAL


def test_a_store_built_before_the_column_fails_loud_rather_than_falling_back(tmp_path):
    import sqlite3

    from cairn import substrate

    schema = substrate.schema_text()
    old = schema.replace(
        "    attempt_id TEXT,\n    verdict TEXT NOT NULL CHECK (verdict IN ('KEEP'",
        "    verdict TEXT NOT NULL CHECK (verdict IN ('KEEP'",
    )
    assert old != schema
    conn = sqlite3.connect(tmp_path / "old.sqlite")
    conn.row_factory = sqlite3.Row
    conn.executescript(old)
    stale = type("Stale", (), {"conn": conn})()
    with pytest.raises(sqlite3.OperationalError, match="attempt_id"):
        laddertable.inputs_for_attempt(stale, "attempt-anything")
    conn.close()


def refuting_hunt(writer, statement, seed):
    node = factories.evidence_node(
        "counterexample_hunt_record",
        statement.hash,
        {**statement.scope, "size_interval": [40, 40], "param_ranges": {"bits": [40, 40]}},
        frozenset(statement.scope["assumption_set"]),
        verdict="KILLED",
        seed=seed,
    )
    claims.write_evidence_node(writer, node)
    _bind_counterexample(writer, node, seed)
    return node


def test_a_refutation_reaches_a_dependent_through_rederive(writer, plan, attest_path):
    premise = statement_with(writer, cost_model=None, seed=12, size=(30, 60))
    dependent = statement_with(writer, cost_model=None, seed=13, size=(30, 60))
    identity = certify(writer, "9c" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    live_ladder_node(writer, plan, premise, producer_identity=identity, run_id="run-premise")
    live_ladder_node(writer, plan, dependent, producer_identity=identity, run_id="run-dependent")
    foundations.add_premise(writer, dependent.hash, premise.hash)
    assert justify.derive_tag(writer, premise.hash, attest_path).tag == STRONG_EMPIRICAL
    assert justify.derive_tag(writer, dependent.hash, attest_path).tag == STRONG_EMPIRICAL

    hunt = refuting_hunt(writer, premise, 12)
    assert justify.derive_tag(writer, premise.hash, attest_path).refuted_by == hunt.hash

    derivations = foundations.rederive(writer, premise.hash, attest_path)

    assert [d.statement_hash for d in derivations] == [dependent.hash]
    assert derivations[0].tag == justify.SPECULATION
    assert foundations.current_tag(writer, dependent.hash) == justify.SPECULATION


def test_a_refutation_reaches_a_dependent_through_rederive_for_attempts(writer, plan, attest_path):
    premise = statement_with(writer, cost_model=None, seed=14, size=(30, 60))
    dependent = statement_with(writer, cost_model=None, seed=15, size=(30, 60))
    identity = certify(writer, "ad" * 32, factories.selftest_summary(GENERATED_ORIGINS, True, None))
    live_ladder_node(writer, plan, premise, producer_identity=identity, run_id="run-p2")
    live_ladder_node(writer, plan, dependent, producer_identity=identity, run_id="run-d2")
    foundations.add_premise(writer, dependent.hash, premise.hash)
    justify.derive_tag(writer, dependent.hash, attest_path)
    refuting_hunt(writer, premise, 14)

    rederived = foundations.rederive_for_attempts(writer, ["attempt-run-p2"], attest_path)

    assert premise.hash in rederived and dependent.hash in rederived
    assert foundations.current_tag(writer, premise.hash) == justify.SPECULATION
    assert foundations.current_tag(writer, dependent.hash) == justify.SPECULATION


def test_a_node_whose_attempt_resolves_to_no_table_falls_back_to_its_declared_population(writer, plan, attest_path):
    statement = statement_with(writer, cost_model=None, seed=10, size=(20, 80))
    identity = certify(
        writer,
        "9c" * 32,
        factories.selftest_summary(
            AUTHOR_ORIGINS, False, {"axis": "algorithm", "independent_range": {"bits": [0, 90]}}
        ),
    )
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        statement.scope,
        frozenset(statement.scope["assumption_set"]),
        producer=(identity, "skill"),
        seed=12,
        attempt_id="attempt-absent",
    )
    claims.write_evidence_node(writer, node)
    assert laddertable.inputs_for_attempt(writer, "attempt-absent") is None
    assert judge(writer, node, statement, attest_path).cls == STRONG_EMPIRICAL
