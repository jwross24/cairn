import dataclasses
import json
import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import claims, ladder, ladderplan, laddertable, ledger

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

from tests.fixtures.skills import ladder_wrong_answer


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
    writer, shipped, tmp_path, plan, hypothesis_object, attest_path
):
    statement = factories.claim_statement(family="dlp", seed=91)
    claims.write_claim_statement(writer, statement)
    bound = dataclasses.replace(hypothesis_object, claim_statement_hash=statement.hash)
    table, trials = run_wrong_answer(writer, shipped, tmp_path, plan, bound, attest_path)
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
