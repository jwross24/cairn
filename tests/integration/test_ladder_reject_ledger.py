import dataclasses
import json
import sqlite3
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import attest, claims, human_authority, ladder, ladderplan, laddertable, ledger, runner

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import factories
from test_ladder_run import (
    MAKER_CEILING,
    RUN_ID,
    _dispatch_run,
)
from test_ladder_run import attest_path as attest_path
from test_ladder_run import hypothesis_object as hypothesis_object
from test_ladder_run import plan as plan
from test_ladder_run import shipped as shipped
from test_ladder_run import writer as writer

from tests.fixtures.skills import ladder_model_miss, ladder_wrong_answer


def run_wrong_answer(writer, shipped, tmp_path, plan, hypothesis_object, attest_path):
    nonce = _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID, claimant=ladder_wrong_answer)
    scratch = tmp_path / "runs"
    scratch.mkdir()
    return ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )


def run_measured_floor(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, ops_kind):
    measured_plan = _measured_floor_plan(plan)
    nonce = _dispatch_run(writer, shipped, tmp_path, measured_plan, hypothesis_object, RUN_ID)
    scratch = tmp_path / "measured-runs"
    scratch.mkdir()

    def observe(trial):
        assert trial.reported_ops is not None
        return laddertable.OpsObservation(ops_kind, trial.reported_ops)

    return ladder.run(
        writer,
        shipped,
        plan=measured_plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        ops_counter=observe,
        attest_path=attest_path,
    )


def run_model_miss(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, bits):
    nonce = _dispatch_run(
        writer,
        shipped,
        tmp_path,
        plan,
        hypothesis_object,
        RUN_ID,
        claimant=ladder_model_miss,
    )
    scratch = tmp_path / f"model-miss-{bits}"
    scratch.mkdir()

    def observe(trial):
        if trial.arm == ladder.CLAIMANT and trial.bits == bits:
            assert trial.reported_ops is not None
            return laddertable.OpsObservation(laddertable.OPS_EXACT, trial.reported_ops)
        return laddertable.OpsObservation(laddertable.OPS_UNKNOWN, None)

    return ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        ops_counter=observe,
        attest_path=attest_path,
    )


def _measured_floor_plan(plan):
    floor = dataclasses.replace(plan.rungs[0].refutation_floor, group_ops=1)
    floor_rung = dataclasses.replace(
        plan.rungs[0], floor_binds=True, memory_cap_bytes=floor.memory_bytes, refutation_floor=floor
    )
    return dataclasses.replace(plan, rungs=(floor_rung, *plan.rungs[1:]))


def test_wrong_answer_yanks_the_dispatched_bundle_without_measured_refutation(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    table, trials = run_wrong_answer(writer, shipped, tmp_path, plan, hypothesis_object, attest_path)
    verdict = laddertable.verdict(table, plan)
    assert (verdict.kind, verdict.predicate) == (laddertable.REJECT, laddertable.RECOVERY)
    dispatched = ladder.dispatches_for(writer, RUN_ID)
    claimant = dispatched[ladder.CLAIMANT]
    assert claimant.identity_bundle_hash != claimant.implementation_revision
    entries = ledger.entries_for(writer, hypothesis_object.hash)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["refutation_kind"] == ledger.IMPLEMENTATION
    assert entry["faulting_revision"] == claimant.identity_bundle_hash
    assert entry["evidence_node"] == table.hash
    assert json.loads(entry["retry_predicate"]) == {
        "kind": ledger.RETRY_NEW_CERTIFIED_REVISION,
        "target": claimant.identity_bundle_hash,
    }
    assert writer.yanked(claimant.identity_bundle_hash)
    assert not writer.yanked(dispatched[ladder.BASELINE].identity_bundle_hash)
    assert not [entry for entry in entries if entry["refutation_kind"] == ledger.MEASURED]
    for trial in trials:
        assert bool(writer.get_attempt(trial.attempt_id)["disowned_at"]) == (trial.arm == ladder.CLAIMANT)
    print(json.dumps(entry, sort_keys=True))


@pytest.mark.parametrize(
    ("field", "message"),
    [
        ("hypothesis_key", "disagrees with its ladder table"),
        ("method", "disagrees with its ladder table"),
        ("faulting_revision", "another dispatched identity"),
        ("caught_by", "must read <writer>:<predicate>"),
        ("retry_predicate", "never supplied by its caller"),
    ],
)
def test_an_implementation_entry_refuses_a_foreign_subject_or_caller_retry(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path, field, message
):
    table, _ = run_wrong_answer(writer, shipped, tmp_path, plan, hypothesis_object, attest_path)
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    fields = {
        "hypothesis_key": hypothesis_object.hash,
        "decision": ledger.REFUTED,
        "refutation_kind": ledger.IMPLEMENTATION,
        "evidence_node": table.hash,
        "method": table.method_identity,
        "faulting_revision": claimant.identity_bundle_hash,
        "caught_by": "ladder:recovery",
        "at": table.created_at,
    }
    fields[field] = {"interface_version": "foreign/1", "params": {}} if field == "method" else "foreign"
    with pytest.raises(ledger.LedgerError, match=message):
        ledger.write(writer, **fields)
    assert len(ledger.entries_for(writer, hypothesis_object.hash)) == 1


def test_a_yank_failure_rolls_back_the_table_and_ledger_but_preserves_trial_receipts(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    writer.conn.execute(
        "CREATE TEMP TRIGGER refuse_yank BEFORE INSERT ON yank_records "
        "BEGIN SELECT RAISE(ABORT, 'planted yank failure'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="planted yank failure"):
        run_wrong_answer(writer, shipped, tmp_path, plan, hypothesis_object, attest_path)
    assert writer.conn.execute("SELECT count(*) FROM ladder_tables").fetchone()[0] == 0
    assert ledger.entries_for(writer, hypothesis_object.hash) == []
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    assert not writer.yanked(claimant.identity_bundle_hash)
    attempts = writer.conn.execute("SELECT disowned_at, receipt_hash FROM attempts").fetchall()
    assert attempts and all(row["receipt_hash"] and row["disowned_at"] is None for row in attempts)


def test_wrong_answer_disowns_bound_evidence_without_refuting_the_statement(
    writer, shipped, tmp_path, plan, hypothesis_object
):
    statement = factories.claim_statement(family="dlp", seed=91)
    claims.write_claim_statement(writer, statement)
    bound = dataclasses.replace(hypothesis_object, claim_statement_hash=statement.hash)
    bound_attest_path = tmp_path / "bound-attestations.log"
    attest.init(str(bound_attest_path), shipped.waiver_target())
    human_authority.append(
        writer,
        str(bound_attest_path),
        human_authority.STATEMENT_RATIFICATION,
        {"statement_hash": statement.hash, "issued_by": "test-operator", "at": datetime.now(UTC).isoformat()},
        gate_bundle_hash=shipped.hash,
    )
    table, trials = run_wrong_answer(writer, shipped, tmp_path, plan, bound, bound_attest_path)
    evidence = claims.evidence_for(writer, statement.hash)
    claimant_ids = {trial.attempt_id for trial in trials if trial.arm == ladder.CLAIMANT}
    assert {node["attempt_id"] for node in evidence} == claimant_ids
    assert claims.get_claim_statement(writer, statement.hash)["status"] == "open"
    assert ledger.entries_for(writer, bound.hash)[0]["evidence_node"] == table.hash


def test_missing_attestation_log_refuses_before_trial_launch(
    writer, shipped, tmp_path, plan, hypothesis_object, popen_spy
):
    nonce = _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID)
    with pytest.raises(FileNotFoundError, match=r"absent\.log"):
        ladder.run(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=nonce,
            scratch_root=tmp_path,
            budget_remaining=10_000.0,
            attest_path=tmp_path / "absent.log",
        )
    assert popen_spy == []


def test_unsettled_measured_rejection_refuses_without_minting_a_ledger_entry(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    capped = dataclasses.replace(plan, rungs=(dataclasses.replace(plan.rungs[0], memory_cap_bytes=1), *plan.rungs[1:]))
    nonce = _dispatch_run(writer, shipped, tmp_path, capped, hypothesis_object, RUN_ID)
    with pytest.raises(ladder.RunRefused, match="measured-settlement-unavailable"):
        ladder.run(
            writer,
            shipped,
            plan=capped,
            plan_hash=ladderplan.plan_digest(shipped),
            run_id=RUN_ID,
            hypothesis_hash=hypothesis_object.hash,
            nonce=nonce,
            scratch_root=tmp_path,
            budget_remaining=10_000.0,
            ceiling_multiplier=MAKER_CEILING,
            attest_path=attest_path,
        )
    assert ledger.entries_for(writer, hypothesis_object.hash) == []
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    assert not writer.yanked(claimant.identity_bundle_hash)


@pytest.mark.parametrize("ops_kind", [laddertable.OPS_EXACT, laddertable.OPS_LOWER_BOUND])
def test_refutation_floor_persists_gate_owned_measured_result(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path, ops_kind
):
    table, _ = run_measured_floor(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, ops_kind)
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert (recorded.kind, recorded.predicate, recorded.refutation_kind) == (
        laddertable.REJECT,
        laddertable.REFUTATION_FLOOR,
        ledger.MEASURED,
    )
    stored = laddertable.read(writer, table.hash)
    row = next(rung for rung in stored.rungs if rung.bits == recorded.rung_bits)
    measured = laddertable._measured_entry_fields(stored, recorded)
    entries = ledger.entries_for(writer, hypothesis_object.hash)
    assert len(entries) == 1
    entry = entries[0]
    result = json.loads(entry["result"])
    assert entry["evidence_node"] == table.hash
    assert (entry["decision"], entry["refutation_kind"], entry["faulting_revision"]) == (
        ledger.REFUTED,
        ledger.MEASURED,
        None,
    )
    assert entry["caught_by"] == f"ladder:{laddertable.REFUTATION_FLOOR}"
    assert json.loads(entry["measured_points"]) == list(measured["measured_points"])
    assert result == measured["result"]
    assert result["kind"] == (ledger.EXACT if ops_kind == laddertable.OPS_EXACT else ledger.LOWER_BOUND)
    assert result["quantity"] == "mean_group_operations"
    assert result["value"] == row.mean_ops
    assert result["ci"] is result["ci_method"] is result["coverage"] is None
    if ops_kind == laddertable.OPS_LOWER_BOUND:
        assert "lower bound" in result["summary"]
    assert json.loads(entry["retry_predicate"]) == {
        "kind": ledger.RETRY_GATE_OWNED_REMEASUREMENT,
        "target": hypothesis_object.hash,
    }
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    assert not writer.yanked(claimant.identity_bundle_hash)
    print(json.dumps({"entry": entry, "table": table.hash}, sort_keys=True))


@pytest.mark.parametrize(
    ("bits", "role", "predicate"),
    [
        (28, ladderplan.ROLE_FIT, laddertable.IN_SAMPLE_MISS),
        (30, ladderplan.ROLE_HOLD_OUT, laddertable.OUT_OF_SAMPLE_MISS),
    ],
)
def test_model_miss_persists_gate_owned_finite_sample_result(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path, bits, role, predicate
):
    table, _ = run_model_miss(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, bits)
    stored = laddertable.read(writer, table.hash)
    recorded = laddertable.recorded_verdict(writer, table.hash)
    assert (recorded.kind, recorded.predicate, recorded.refutation_kind, recorded.rung_bits) == (
        laddertable.REJECT,
        predicate,
        ledger.MEASURED,
        bits,
    )
    row = next(rung for rung in stored.rungs if rung.bits == bits)
    assert row.role == role
    assert row.model_prediction == "1.000000"
    assert row.model_band == str(plan.design_radius)
    assert Decimal(row.mean_ops) > Decimal(row.model_prediction) * (1 + Decimal(row.model_band))
    target_trials = [trial for trial in stored.trials if trial.arm == ladder.CLAIMANT and trial.bits == bits]
    assert len(target_trials) == row.trials
    assert all(
        trial.gate_ops.kind == laddertable.OPS_EXACT
        and trial.gate_ops.value == trial.reported_ops
        and trial.status == runner.STATUS_OK
        and trial.output_complete
        and trial.recovered
        for trial in target_trials
    )
    expected_mean = format(
        (sum(Decimal(trial.gate_ops.value) for trial in target_trials) / Decimal(len(target_trials))).quantize(
            Decimal("0.000001")
        ),
        "f",
    )
    assert row.mean_ops == expected_mean

    entries = ledger.entries_for(writer, hypothesis_object.hash)
    assert len(entries) == 1
    entry = entries[0]
    assert entry["evidence_node"] == stored.hash
    assert (entry["decision"], entry["refutation_kind"], entry["faulting_revision"]) == (
        ledger.REFUTED,
        ledger.MEASURED,
        None,
    )
    assert entry["caught_by"] == f"ladder:{predicate}"
    assert json.loads(entry["measured_points"]) == [
        {
            "numeric": {"bits": bits},
            "categorical": {
                "predicate": predicate,
                "mean_ops": expected_mean,
                "model_prediction": row.model_prediction,
                "model_band": row.model_band,
            },
        }
    ]
    assert json.loads(entry["result"]) == {
        "kind": ledger.EXACT,
        "quantity": "mean_group_operations",
        "summary": f"finite-sample mean of gate operation counts at {bits} bits",
        "value": expected_mean,
        "ci": None,
        "ci_method": None,
        "coverage": None,
    }
    assert json.loads(entry["retry_predicate"]) == {
        "kind": ledger.RETRY_GATE_OWNED_REMEASUREMENT,
        "target": hypothesis_object.hash,
    }
    claimant = ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT]
    assert not writer.yanked(claimant.identity_bundle_hash)


def test_measured_table_entry_refuses_forged_subject_points_result_and_predicate(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    table, _ = run_measured_floor(
        writer, shipped, tmp_path, plan, hypothesis_object, attest_path, laddertable.OPS_EXACT
    )
    recorded = laddertable.recorded_verdict(writer, table.hash)
    measured = laddertable._measured_entry_fields(table, recorded)
    fields = {
        "hypothesis_key": table.hypothesis_hash,
        "decision": ledger.REFUTED,
        "refutation_kind": ledger.MEASURED,
        "evidence_node": table.hash,
        "method": table.method_identity,
        "measured_points": measured["measured_points"],
        "result": measured["result"],
        "caught_by": f"ladder:{recorded.predicate}",
        "at": table.created_at,
    }
    altered_points = ({"numeric": {"bits": recorded.rung_bits}, "categorical": {"predicate": "forged"}},)
    altered_result = dict(measured["result"], value="0")
    for name, value in (
        ("hypothesis_key", "ff" * 32),
        ("method", {"interface_version": "foreign/1", "params": {}}),
        ("caught_by", "ladder:in_sample_model_miss"),
        ("measured_points", altered_points),
        ("result", altered_result),
    ):
        with pytest.raises(ledger.LedgerError):
            ledger.write(writer, **{**fields, name: value})
    with pytest.raises(ledger.RetryPredicateNotYours):
        ledger.write(
            writer,
            **fields,
            retry_predicate={"kind": ledger.RETRY_GATE_OWNED_REMEASUREMENT, "target": table.hypothesis_hash},
        )
    assert len(ledger.entries_for(writer, hypothesis_object.hash)) == 1


def test_measured_entry_refuses_a_table_not_bound_to_its_claimant_dispatch(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    table, _ = run_measured_floor(
        writer, shipped, tmp_path, plan, hypothesis_object, attest_path, laddertable.OPS_EXACT
    )
    members = laddertable.membership_for_table(writer, table.hash)
    measured_plan = _measured_floor_plan(plan)
    forged_run_id = "run-forged-measured-source"
    nonce = _dispatch_run(writer, shipped, tmp_path, measured_plan, hypothesis_object, forged_run_id)
    forged = dataclasses.replace(
        table,
        run_id=forged_run_id,
        nonce=nonce,
        method_identity={"interface_version": "foreign/1", "params": {}},
    )
    laddertable.write(writer, forged, measured_plan)
    laddertable._store_membership(writer, forged, members)

    with pytest.raises(ledger.LedgerError, match=r"claimant dispatch .* disagrees with the table identity"):
        ledger.write_ladder_measured_refutation(writer, forged.hash)
    assert len(ledger.entries_for(writer, hypothesis_object.hash)) == 1


def test_measured_entry_failure_rolls_back_table_and_entry_but_preserves_trial_receipts(
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    writer.conn.execute(
        "CREATE TEMP TRIGGER refuse_measured_entry BEFORE INSERT ON ledger_entries "
        "WHEN NEW.refutation_kind = 'measured' BEGIN SELECT RAISE(ABORT, 'planted measured entry failure'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="planted measured entry failure"):
        run_measured_floor(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, laddertable.OPS_EXACT)
    assert writer.conn.execute("SELECT count(*) FROM ladder_tables").fetchone()[0] == 0
    assert ledger.entries_for(writer, hypothesis_object.hash) == []
    attempts = writer.conn.execute("SELECT receipt_hash FROM attempts").fetchall()
    assert attempts and all(row["receipt_hash"] for row in attempts)
