import dataclasses
import json
import sys
from pathlib import Path

import pytest

from cairn import attest, claims, foundations, justify, ladderplan, laddertable, runner
from cairn.justify import CONJECTURE, PROVEN, STRONG_EMPIRICAL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import ENV_MANIFEST_HASH, IDENTITY_A, TRANSCRIPT_HASH, open_writer

BITS = (30, 40, 50, 60)
FIT_BITS = BITS[:-1]
HOLD_OUT_BITS = BITS[-1]
COVERING_CROSS_CHECK = {"axis": "algorithm", "independent_range": {"bits": [0, 60]}}
AUTHOR_ORIGINS = {"F5": {"P": justify.AUTHOR_SUPPLIED, "p": justify.AUTHOR_SUPPLIED}}
GENERATED_ORIGINS = {"F5": {"P": "generated", "p": "generated"}}

TRIAL = laddertable.Trial(
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    recovered=True,
    completed=True,
    gate_ops=1000000,
    reported_ops=1000000,
    cpu_seconds="1",
    wall_seconds="1",
    peak_rss_bytes=1000,
    scratch_bytes=1000,
    reported_memory_bytes=1000,
    replay_grade="Replayable",
    measurement_scope=runner.SCOPE_TREE,
)
RUNG = laddertable.RungRow(
    bits=0,
    role=ladderplan.ROLE_FIT,
    trials=2,
    mean_ops="1000000",
    sd_ops="0",
    cpu_seconds="1",
    reference_rate="1000000",
    memory_bytes=100000,
    success_rate="1",
    radius="0.1216",
    claim_ci_low="1.5",
    claim_ci_high="1.8",
    model_prediction="1000000",
    model_band="0.05",
    shape_statistic="1",
    declared_shape="stable",
)
TABLE = laddertable.ResultTable(
    run_id="run-live",
    nonce="nonce-live",
    hypothesis_hash="aa" * 32,
    method_identity={"interface_version": "toy_curve/1", "params": {"r": "20"}},
    implementation_revision="aa" * 32,
    gate_bundle_hash="cc" * 32,
    plan_hash="dd" * 32,
    uncounted_backend=None,
    rungs=(),
    trials=(),
)


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "f" * 64)
    return path


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(
        json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    )


def real_table(hypothesis_hash, run_id="run-live"):
    return dataclasses.replace(
        TABLE,
        run_id=run_id,
        hypothesis_hash=hypothesis_hash,
        rungs=tuple(
            dataclasses.replace(
                RUNG, bits=b, role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT
            )
            for b in BITS
        ),
        trials=tuple(dataclasses.replace(TRIAL, bits=b, trial=t) for b in BITS for t in (0, 1)),
    )


def statement_with(writer, *, cost_model, seed=1, size=(30, 60)):
    stmt = factories.claim_statement(cost_model=cost_model, seed=seed, size=size)
    claims.write_claim_statement(writer, stmt)
    return stmt


def certify(writer, revision, summary):
    identity = writer.put_identity_bundle({**IDENTITY_A, "implementation_revision": revision})
    writer.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, summary)
    return identity


def live_ladder_node(writer, plan, statement, *, producer_identity, producer_tag="skill", run_id="run-live"):
    """A ladder_table node over a table the substrate actually holds, with a real repro record."""
    table = real_table(statement.hash, run_id=run_id)
    attempt_id = f"attempt-{run_id}"
    laddertable.write(writer, table, plan, attempt_id=attempt_id)
    verified = tuple((t.bits, t.trial) for t in table.trials)
    record, recomputation = laddertable.record(writer, table, plan, verified, attempt_id=attempt_id)
    node = laddertable.evidence_node(
        table,
        plan,
        target_statement_hash=statement.hash,
        population=statement.scope,
        assumptions=frozenset(statement.scope["assumption_set"]),
        producer_identity=producer_identity,
        producer_tag=producer_tag,
        attempt_id=attempt_id,
        repro_record_hash=record.hash,
    )
    claims.write_evidence_node(writer, node)
    return table, node, recomputation


def statistical_node(writer, statement, *, producer_identity, population=None):
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        population or statement.scope,
        frozenset(statement.scope["assumption_set"]),
        producer=(producer_identity, "skill"),
        seed=7,
    )
    claims.write_evidence_node(writer, node)
    return node


def judge(writer, node, statement, attest_path, **kw):
    row = dict(writer.conn.execute("SELECT * FROM evidence_nodes WHERE hash = ?", (node.hash,)).fetchone())
    ctx = justify.context_for(writer, row, {"hash": statement.hash, **dataclasses.asdict(statement)}, attest_path, **kw)
    return justify.justify(row, {"hash": statement.hash, "scope": statement.scope}, ctx)


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

    schema = (Path(substrate.__file__).with_name("schema.sql")).read_text()
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
