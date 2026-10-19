import dataclasses
import json

import factories
import pytest
from _justify_live_helpers import (
    assert_evidence_refused,
    assert_membership_refused,
    bound_production_run,
    replay_attempt,
)

from cairn import bundle, claims, instances, justify, ladder, laddertable, substrate
from cairn.substrate import HashCollision


def test_a_bound_production_ladder_run_emits_evidence_for_every_claimant_attempt(writer, pinned_bundle, tmp_path):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    _, statement, table, arm_trials, rows = bound_production_run(writer, shipped, tmp_path, "run-bound-production")
    claimant_attempts = {
        (trial.arm, trial.bits, trial.trial): trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT
    }
    membership = {(trial.arm, trial.bits, trial.trial): trial.attempt_id for trial in arm_trials}
    assert laddertable.membership_for_table(writer, table.hash) == tuple(
        (arm, bits, trial, attempt_id) for (arm, bits, trial), attempt_id in sorted(membership.items())
    )
    assert {row["attempt_id"] for row in rows} == set(claimant_attempts.values())
    assert all(justify._attempt_inputs(writer, row) == {"bits": [28, 30]} for row in rows)
    declared_population = claims.to_json(statement.scope)
    assert json.loads(declared_population)["param_ranges"]["bits"] == [7, 77]
    assert all(
        justify._attempt_inputs(writer, {**row, "population": declared_population}) == {"bits": [28, 30]}
        for row in rows
    )
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
    assert all(laddertable.inputs_for_attempt(writer, trial.attempt_id) == {"bits": [28, 30]} for trial in arm_trials)
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
    mapping = {(trial.arm, trial.bits, trial.trial): trial.attempt_id for trial in arm_trials}
    first_slot, first_attempt = next(
        (slot, attempt_id) for slot, attempt_id in sorted(mapping.items()) if slot[0] == ladder.CLAIMANT
    )
    replay = replay_attempt(writer, first_attempt)
    _, _, foreign_table, foreign_trials, _ = bound_production_run(writer, shipped, tmp_path, "run-membership-foreign")
    baseline = next(trial.attempt_id for trial in arm_trials if trial.arm == ladder.BASELINE)
    maker = instances.trials_for(writer, table.nonce)[0]["attempt_id"]
    foreign = next(trial.attempt_id for trial in foreign_trials if trial.arm == ladder.CLAIMANT)

    assert laddertable.inputs_for_attempt(writer, baseline) == {"bits": [28, 30]}
    assert laddertable.inputs_for_attempt(writer, maker) is None
    assert laddertable.inputs_for_attempt(writer, "attempt-unknown") is None
    assert laddertable.inputs_for_attempt(writer, replay) is None
    assert laddertable.mapped_table_for_attempt(writer, foreign) == foreign_table.hash
    assert laddertable.mapped_table_for_attempt(writer, foreign) != table.hash

    before = db_snapshot(writer.conn, "before-wrong-origin-memberships")
    assert_membership_refused(writer, table, plan, mapping, first_slot, baseline, "attempt", before, db_snapshot)
    assert_membership_refused(writer, table, plan, mapping, first_slot, maker, "attempt", before, db_snapshot)
    assert_membership_refused(
        writer, table, plan, mapping, first_slot, "attempt-unknown", "names no attempt", before, db_snapshot
    )
    assert_membership_refused(writer, table, plan, mapping, first_slot, foreign, "attempt", before, db_snapshot)


def test_membership_repeats_idempotently_and_refuses_incomplete_extra_or_conflicting_maps(
    writer, pinned_bundle, tmp_path, db_snapshot
):
    shipped = bundle.GateBundle.open(*pinned_bundle())
    plan, _, table, arm_trials, _ = bound_production_run(writer, shipped, tmp_path, "run-map-atomicity")
    mapping = {(trial.arm, trial.bits, trial.trial): trial.attempt_id for trial in arm_trials}
    before = db_snapshot(writer.conn, "before-idempotent-membership")

    laddertable.write(writer, table, plan, trial_attempts=mapping)
    assert db_snapshot(writer.conn, "after-idempotent-membership") == before

    first_slot, first_attempt = next(iter(sorted(mapping.items())))
    incomplete = {slot: attempt_id for slot, attempt_id in mapping.items() if slot != first_slot}
    extra = {**mapping, (ladder.CLAIMANT, 31, 0): "attempt-extra"}
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
        (arm, bits, trial, attempt_id) for (arm, bits, trial), attempt_id in sorted(mapping.items())
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

    one_trial = {(table.trials[0].arm, table.trials[0].bits, table.trials[0].trial)}
    with pytest.raises(laddertable.LadderTableError, match="must verify every trial"):
        laddertable.record(writer, table, plan, one_trial, attempt_id=attempt_id)

    complete, recomputation = laddertable.record(
        writer,
        table,
        plan,
        {(trial.arm, trial.bits, trial.trial) for trial in table.trials},
        attempt_id=attempt_id,
    )
    assert recomputation.agrees is True
    assert justify._repro_passed(writer, rows[0]) is True
    assert justify._repro_passed(writer, {**rows[0], "repro_record_hash": complete.hash}) is True
    sibling = next(row for row in rows if row["attempt_id"] != attempt_id)
    assert justify._repro_passed(writer, {**sibling, "repro_record_hash": complete.hash}) is None
