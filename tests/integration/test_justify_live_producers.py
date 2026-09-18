import dataclasses
import json
import sys
from pathlib import Path

import pytest

from cairn import (
    attest,
    bundle,
    claims,
    foundations,
    instances,
    justify,
    ladder,
    ladderplan,
    laddertable,
    runner,
    substrate,
)
from cairn.justify import CONJECTURE, PROVEN, STRONG_EMPIRICAL
from cairn.skills import bsgs, rho_dp
from cairn.substrate import HashCollision

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


def production_plan():
    obj = json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    obj["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    full = ladderplan.LadderPlan.load(obj)
    fit = dataclasses.replace(full.rung(30), bits=28, trials=2)
    hold_out = dataclasses.replace(full.rung(40), bits=30, role=ladderplan.ROLE_HOLD_OUT, trials=2)
    return dataclasses.replace(full, rungs=(fit, hold_out), hold_out_m=2, patience_multiplier=60)


def bound_production_run(writer, shipped, tmp_path, run_id, declared_size=(7, 77)):
    from test_ladder_run import _dispatch_run

    plan = production_plan()
    statement = factories.claim_statement(
        family="dlp",
        size=declared_size,
        param_ranges={"bits": list(declared_size)},
        seed=91,
    )
    claims.write_claim_statement(writer, statement)
    hypothesis = claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": list(declared_size)},
        claim_statement_hash=statement.hash,
    )
    nonce = _dispatch_run(writer, shipped, tmp_path, plan, hypothesis, run_id)
    scratch = tmp_path / f"bound-{run_id}"
    scratch.mkdir()
    table, arm_trials = ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id=run_id,
        hypothesis_hash=hypothesis.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=60,
    )
    claimant_ids = {trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT}
    evidence = [
        dict(row)
        for row in writer.conn.execute(
            "SELECT * FROM evidence_nodes WHERE kind = ? AND target_statement_hash = ? ORDER BY attempt_id",
            (laddertable.NODE_KIND, statement.hash),
        ).fetchall()
        if row["attempt_id"] in claimant_ids
    ]
    return plan, statement, table, arm_trials, evidence


def replay_attempt(writer, attempt_id):
    original = writer.get_attempt(attempt_id)
    replay = writer.start_attempt(
        original["recipe_key"],
        replay_grade=original["replay_grade"],
        skip_cache_lookup=True,
    )
    writer.close_attempt(
        replay,
        original["status"],
        output_manifest_hash=original["output_manifest_hash"],
        receipt_hash=original["receipt_hash"],
        verifier_result_hash=original["verifier_result_hash"],
        certificate_hash=original["certificate_hash"],
    )
    return replay


def assert_membership_refused(writer, table, plan, mapping, slot, replacement, match, before, db_snapshot):
    with pytest.raises(laddertable.LadderTableError, match=match):
        laddertable.write(writer, table, plan, trial_attempts={**mapping, slot: replacement})
    assert db_snapshot(writer.conn, f"after-{replacement}") == before


def assert_evidence_refused(writer, table, node, match, before, db_snapshot):
    with pytest.raises(laddertable.LadderTableError, match=match):
        laddertable.write_evidence_node(writer, table, node)
    assert claims.get_evidence_node(writer, node.hash) is None
    assert db_snapshot(writer.conn, f"after-{node.hash}") == before


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


def test_a_bound_production_ladder_run_emits_evidence_for_every_claimant_attempt(writer, pinned_bundle, tmp_path):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    _, statement, table, arm_trials, rows = bound_production_run(writer, shipped, tmp_path, "run-bound-production")
    claimant_attempts = {
        (trial.bits, trial.trial): trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT
    }
    assert laddertable.membership_for_table(writer, table.hash) == tuple(
        (bits, trial, attempt_id) for (bits, trial), attempt_id in sorted(claimant_attempts.items())
    )
    assert {row["attempt_id"] for row in rows} == set(claimant_attempts.values())
    assert all(justify._attempt_inputs(writer, row) == {"bits": [28, 30]} for row in rows)
    assert all(
        laddertable.inputs_for_attempt(writer, attempt_id) == {"bits": [28, 30]}
        for attempt_id in claimant_attempts.values()
    )
    expected_population = {
        "target_family": "dlp",
        "size_interval": [28, 30],
        "param_ranges": {"bits": [28, 30]},
        "assumption_set": sorted(statement.scope["assumption_set"]),
    }
    claimant_identity = ladder.dispatches_for(writer, table.run_id)[ladder.CLAIMANT].identity_bundle_hash
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert all(json.loads(row["population"]) == expected_population for row in rows)
    assert all(json.loads(row["assumptions"]) == sorted(statement.scope["assumption_set"]) for row in rows)
    assert all(json.loads(row["in_sample_sizes"]) == [28] for row in rows)
    assert all(row["producer_identity"] == claimant_identity and row["producer_tag"] == "skill" for row in rows)
    assert all(row["verdict"] == recorded.kind and row["repro_record_hash"] is None for row in rows)
    assert all(
        laddertable.inputs_for_attempt(writer, trial.attempt_id) is None
        for trial in arm_trials
        if trial.arm != ladder.CLAIMANT
    )
    assert all(
        laddertable.inputs_for_attempt(writer, row["attempt_id"]) is None
        for row in instances.trials_for(writer, table.nonce)
    )
    assert bytes(writer.get_node(table.hash)["canonical"]) == laddertable._table_canonical(table)
    assert all(
        laddertable._trial_canonical(stored) == laddertable._trial_canonical(actual)
        for stored, actual in zip(laddertable.read(writer, table.hash).trials, table.trials, strict=True)
    )


def test_only_exact_claimant_attempts_resolve_to_their_production_table(writer, pinned_bundle, tmp_path, db_snapshot):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    plan, _, table, arm_trials, _ = bound_production_run(writer, shipped, tmp_path, "run-membership")
    mapping = {(trial.bits, trial.trial): trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT}
    first_slot, first_attempt = next(iter(sorted(mapping.items())))
    replay = replay_attempt(writer, first_attempt)
    _, _, foreign_table, foreign_trials, _ = bound_production_run(writer, shipped, tmp_path, "run-membership-foreign")
    baseline = next(trial.attempt_id for trial in arm_trials if trial.arm == ladder.BASELINE)
    maker = instances.trials_for(writer, table.nonce)[0]["attempt_id"]
    foreign = next(trial.attempt_id for trial in foreign_trials if trial.arm == ladder.CLAIMANT)

    assert laddertable.inputs_for_attempt(writer, baseline) is None
    assert laddertable.inputs_for_attempt(writer, maker) is None
    assert laddertable.inputs_for_attempt(writer, "attempt-unknown") is None
    assert laddertable.inputs_for_attempt(writer, replay) is None
    assert laddertable.mapped_table_for_attempt(writer, foreign) == foreign_table.hash
    assert laddertable.mapped_table_for_attempt(writer, foreign) != table.hash

    before = db_snapshot(writer.conn, "before-wrong-origin-memberships")
    assert_membership_refused(
        writer, table, plan, mapping, first_slot, baseline, "is not the claimant trial", before, db_snapshot
    )
    assert_membership_refused(
        writer, table, plan, mapping, first_slot, maker, "is not the claimant trial", before, db_snapshot
    )
    assert_membership_refused(
        writer, table, plan, mapping, first_slot, "attempt-unknown", "names no attempt", before, db_snapshot
    )
    assert_membership_refused(
        writer, table, plan, mapping, first_slot, foreign, "is not the claimant trial", before, db_snapshot
    )


def test_membership_repeats_idempotently_and_refuses_incomplete_extra_or_conflicting_maps(
    writer, pinned_bundle, tmp_path, db_snapshot
):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    plan, _, table, arm_trials, _ = bound_production_run(writer, shipped, tmp_path, "run-map-atomicity")
    mapping = {(trial.bits, trial.trial): trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT}
    before = db_snapshot(writer.conn, "before-idempotent-membership")

    laddertable.write(writer, table, plan, trial_attempts=mapping)
    assert db_snapshot(writer.conn, "after-idempotent-membership") == before

    first_slot, first_attempt = next(iter(sorted(mapping.items())))
    incomplete = {slot: attempt_id for slot, attempt_id in mapping.items() if slot != first_slot}
    extra = {**mapping, (31, 0): "attempt-extra"}
    incomplete_table = dataclasses.replace(table, uncounted_backend="/incomplete")
    with pytest.raises(laddertable.LadderTableError, match="every and only table trial"):
        laddertable.write(writer, incomplete_table, plan, trial_attempts=incomplete)
    assert writer.get_node(incomplete_table.hash) is None
    assert laddertable.read(writer, incomplete_table.hash) is None
    assert db_snapshot(writer.conn, "after-incomplete-membership") == before

    extra_table = dataclasses.replace(table, uncounted_backend="/extra")
    with pytest.raises(laddertable.LadderTableError, match="every and only table trial"):
        laddertable.write(writer, extra_table, plan, trial_attempts=extra)
    assert writer.get_node(extra_table.hash) is None
    assert laddertable.read(writer, extra_table.hash) is None
    assert db_snapshot(writer.conn, "after-extra-membership") == before

    replay = replay_attempt(writer, first_attempt)
    before_conflict = db_snapshot(writer.conn, "before-conflicting-membership")
    with pytest.raises(HashCollision, match="different trial_attempts"):
        laddertable.write(writer, table, plan, trial_attempts={**mapping, first_slot: replay})
    assert db_snapshot(writer.conn, "after-conflicting-membership") == before_conflict
    assert laddertable.membership_for_table(writer, table.hash) == tuple(
        (bits, trial, attempt_id) for (bits, trial), attempt_id in sorted(mapping.items())
    )
    assert laddertable.inputs_for_attempt(writer, replay) is None


def test_bound_evidence_refuses_wrong_attempt_target_producer_and_table_binding(
    writer, pinned_bundle, tmp_path, db_snapshot
):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    plan, statement, table, arm_trials, rows = bound_production_run(writer, shipped, tmp_path, "run-evidence-refusals")
    valid = laddertable.evidence_node(
        table,
        plan,
        target_statement_hash=statement.hash,
        population=json.loads(rows[0]["population"]),
        assumptions=frozenset(json.loads(rows[0]["assumptions"])),
        producer_identity=rows[0]["producer_identity"],
        producer_tag=rows[0]["producer_tag"],
        attempt_id=rows[0]["attempt_id"],
    )
    baseline = next(trial.attempt_id for trial in arm_trials if trial.arm == ladder.BASELINE)
    other_statement = factories.claim_statement(seed=92)
    claims.write_claim_statement(writer, other_statement)
    baseline_identity = ladder.dispatches_for(writer, table.run_id)[ladder.BASELINE].identity_bundle_hash
    refused = (
        (dataclasses.replace(valid, attempt_id=baseline), "is not a claimant member"),
        (dataclasses.replace(valid, target_statement_hash=other_statement.hash), "is not table"),
        (dataclasses.replace(valid, producer_identity=baseline_identity), "producer is not"),
    )
    before = db_snapshot(writer.conn, "before-evidence-refusals")
    assert_evidence_refused(writer, table, refused[0][0], refused[0][1], before, db_snapshot)
    assert_evidence_refused(writer, table, refused[1][0], refused[1][1], before, db_snapshot)
    assert_evidence_refused(writer, table, refused[2][0], refused[2][1], before, db_snapshot)

    _, _, other_table, _, _ = bound_production_run(writer, shipped, tmp_path, "run-evidence-other")
    writer.add_lineage(valid.hash, other_table.hash, substrate.EDGE_INPUT)
    with pytest.raises(HashCollision, match="already bound to another ladder table"):
        laddertable.write_evidence_node(writer, table, valid)
    assert laddertable._binding_table_hashes(writer, valid.hash) == {table.hash, other_table.hash}


@pytest.mark.parametrize("mutation", ["disown", "mark_inadmissible"], ids=["disowned", "inadmissible"])
def test_every_table_evidence_node_reads_the_standing_of_every_claimant_member(
    writer, pinned_bundle, tmp_path, attest_path, mutation
):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    _, statement, _, _, rows = bound_production_run(
        writer,
        shipped,
        tmp_path,
        f"run-standing-{mutation}",
        declared_size=(28, 30),
    )
    statement_row = claims.get_claim_statement(writer, statement.hash)
    named_attempt = rows[0]["attempt_id"]
    affected_attempt = next(row["attempt_id"] for row in rows if row["attempt_id"] != named_attempt)
    statistical = factories.evidence_node(
        "statistical",
        statement.hash,
        statement.scope,
        frozenset(statement.scope["assumption_set"]),
        producer=(rows[0]["producer_identity"], "skill"),
        seed=93,
        attempt_id=named_attempt,
    )
    claims.write_evidence_node(writer, statistical)
    statistical_row = claims.get_evidence_node(writer, statistical.hash)

    getattr(writer, mutation)(affected_attempt)

    table_contexts = [justify.context_for(writer, row, statement_row, attest_path) for row in rows]
    field = "disowned" if mutation == "disown" else "inadmissible"
    reason = "disowned" if mutation == "disown" else justify.REASON_INADMISSIBLE
    assert all(getattr(context, field) for context in table_contexts)
    results = [justify.justify(row, statement_row, context) for row, context in zip(rows, table_contexts, strict=True)]
    assert all(isinstance(result, justify.Absent) and result.reason == reason for result in results)
    unrelated = justify.context_for(writer, statistical_row, statement_row, attest_path)
    assert unrelated.disowned is False
    assert unrelated.inadmissible is False


def test_table_reproduction_requires_a_complete_linked_recomputation(writer, pinned_bundle, tmp_path):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    plan, _, table, _, rows = bound_production_run(writer, shipped, tmp_path, "run-table-repro")
    attempt_id = rows[0]["attempt_id"]
    ordinary = claims.ReproRecord(
        attempt_id=attempt_id,
        kind=claims.REPRO_KINDS[0],
        passed=True,
        at="2026-09-18T10:00:00Z",
    )
    claims.write_repro_record(writer, ordinary)
    assert justify._repro_passed(writer, rows[0]) is None
    assert justify._repro_passed(writer, {**rows[0], "repro_record_hash": ordinary.hash}) is None

    one_trial = {(table.trials[0].bits, table.trials[0].trial)}
    with pytest.raises(laddertable.LadderTableError, match="must verify every trial"):
        laddertable.record(writer, table, plan, one_trial, attempt_id=attempt_id)

    complete, recomputation = laddertable.record(
        writer,
        table,
        plan,
        {(trial.bits, trial.trial) for trial in table.trials},
        attempt_id=attempt_id,
    )
    assert recomputation.agrees is True
    assert justify._repro_passed(writer, rows[0]) is True
    assert justify._repro_passed(writer, {**rows[0], "repro_record_hash": complete.hash}) is True
    sibling = next(row for row in rows if row["attempt_id"] != attempt_id)
    assert justify._repro_passed(writer, {**sibling, "repro_record_hash": complete.hash}) is None


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
