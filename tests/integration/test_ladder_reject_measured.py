import dataclasses
import json
import sqlite3
from decimal import Decimal

import pytest
from _ladder_reject_helpers import _measured_floor_plan, run_measured_floor, run_model_miss
from _ladder_reject_helpers import replayed_run as replayed_run
from test_ladder_run import RUN_ID, _dispatch_run
from test_ladder_run import attest_path as attest_path
from test_ladder_run import hypothesis_object as hypothesis_object
from test_ladder_run import plan as plan
from test_ladder_run import shipped as shipped
from test_ladder_run import writer as writer

from cairn import ladder, ladderplan, laddertable, ledger, runner


@pytest.fixture
def measured_floor_run(replayed_run, shipped, plan, hypothesis_object):
    def get(ops_kind):
        return replayed_run(
            ("measured-floor", ops_kind),
            lambda sub, home, log: run_measured_floor(sub, shipped, home, plan, hypothesis_object, log, ops_kind),
        )

    return get


@pytest.mark.parametrize("ops_kind", [laddertable.OPS_EXACT, laddertable.OPS_LOWER_BOUND])
def test_refutation_floor_persists_gate_owned_measured_result(measured_floor_run, hypothesis_object, ops_kind):
    writer, _, (table, _) = measured_floor_run(ops_kind)
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


def test_measured_table_entry_refuses_forged_subject_points_result_and_predicate(measured_floor_run, hypothesis_object):
    writer, _, (table, _) = measured_floor_run(laddertable.OPS_EXACT)
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
    measured_floor_run, shipped, tmp_path, plan, hypothesis_object
):
    writer, _, (table, _) = measured_floor_run(laddertable.OPS_EXACT)
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
