import json

import pytest
from test_counterexample_hunt import _setup

from cairn import claims, hunt, ledger, repro


@pytest.mark.parametrize(
    ("case", "reason"),
    [
        ("uncertified", "verifier-uncertified"),
        ("same_identity", "verifier-ships-in-producer-revision"),
        ("no_must_fail", "verifier-selftest-carries-no-must-fail-witness"),
    ],
)
def test_audit_only_verifiers_cannot_refute_or_write_a_refuted_ledger(tmp_path, case, reason):
    sub, plan, executor, verifier, statement = _setup(
        tmp_path,
        certified=case != "uncertified",
        same_identity=case == "same_identity",
        must_fail=0 if case == "no_must_fail" else 1,
    )
    try:
        assert repro.owner_grade(
            sub, plan.executor_identity, repro.Verifier(repro.SKILL_VERIFIER, plan.verifier_identity)
        ) == (repro.AUDIT_ONLY, reason)
        result = hunt.run_hunt(sub, plan, executor, verifier)
        refuted = sub.conn.execute("SELECT count(*) FROM claim_statements WHERE status = 'refuted'").fetchone()[0]
        entries = ledger.entries_for(sub, plan.hypothesis_key)
        certificates = sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0]
        print(
            json.dumps(
                {"case": case, "refuted_count": refuted, "certificate_count": certificates, "verdict": result.verdict}
            )
        )
        assert (refuted, sum(entry["decision"] == ledger.REFUTED for entry in entries)) == (0, 0)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "open"
        assert result.verdict == "INCOMPLETE"
        assert result.standing is False
        assert result.ledger_hash is None
        assert result.judgment is None
        assert len(result.record.trials) == 1
        trial = result.record.trials[0]
        assert trial.outcome == "VERIFIER_UNVERIFIED"
        assert trial.verifier_status == reason
        assert sub.get_attempt(trial.verifier_attempt_id)["status"] == "OK"
        assert hunt.record_for(sub, result.run_hash) == result.record
        assert result.record.counterexample_trial is None
        if case == "uncertified":
            assert certificates == 0
    finally:
        sub.close()


def test_certified_distinct_verifier_with_a_must_fail_witness_can_refute(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, certified=True)
    try:
        assert plan.executor_identity != plan.verifier_identity
        assert repro.owner_grade(
            sub, plan.executor_identity, repro.Verifier(repro.SKILL_VERIFIER, plan.verifier_identity)
        ) == (repro.VERIFIABLE, "certified-independent-verifier-with-must-fail-witness")
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "KILLED"
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "refuted"
        entry = ledger.get_entry(sub, result.ledger_hash)
        assert entry["decision"] == ledger.REFUTED
        assert entry["evidence_node"] == result.evidence_hash
        assert result.record.trials[0].outcome == "COUNTEREXAMPLE"
    finally:
        sub.close()


def test_uncertified_survival_keeps_standing_without_running_a_verifier(tmp_path):
    sub, plan, executor, _, statement = _setup(tmp_path, bounds=(0, 2), trials=3)

    def unexpected_verifier(*args):
        pytest.fail("a surviving trial invoked its verifier")

    try:
        assert repro.owner_grade(
            sub, plan.executor_identity, repro.Verifier(repro.SKILL_VERIFIER, plan.verifier_identity)
        ) == (repro.AUDIT_ONLY, "verifier-uncertified")
        result = hunt.run_hunt(sub, plan, executor, unexpected_verifier)
        assert result.verdict == "SURVIVED"
        assert result.standing is True
        assert len(result.record.trials) == 3
        assert all(trial.verifier_attempt_id is None for trial in result.record.trials)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "open"
        assert ledger.entries_for(sub, plan.hypothesis_key) == []
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0
    finally:
        sub.close()
