import pytest
from test_counterexample_hunt import _setup

from cairn import hunt, instances, justify, ledger


def _counts(sub, plan):
    return {
        "runs": sub.conn.execute("SELECT COUNT(*) FROM nodes WHERE kind = 'hunt_run'").fetchone()[0],
        "evidence": sub.conn.execute("SELECT COUNT(*) FROM evidence_nodes").fetchone()[0],
        "ledger": len(ledger.entries_for(sub, plan.hypothesis_key)),
        "unpublished": sum(r.published_at is None for r in instances.nonces_for(sub, plan.hypothesis_key)),
    }


def test_a_second_valid_kill_completes_with_its_own_ledger_entry_and_published_nonce(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, certified=True)
    try:
        first = hunt.run_hunt(sub, plan, executor, verifier)
        second = hunt.run_hunt(sub, plan, executor, verifier)
        assert (first.verdict, second.verdict) == ("KILLED", "KILLED")
        assert _counts(sub, plan) == {"runs": 2, "evidence": 2, "ledger": 2, "unpublished": 0}
        assert {e["evidence_node"] for e in ledger.entries_for(sub, plan.hypothesis_key)} == {
            first.evidence_hash,
            second.evidence_hash,
        }
        assert second.judgment.refuted_by == first.evidence_hash
        assert (
            sub.conn.execute("SELECT status FROM claim_statements WHERE hash = ?", (statement.hash,)).fetchone()[0]
            == "refuted"
        )
    finally:
        sub.close()


def test_a_second_kill_whose_own_evidence_is_not_a_refutation_borrows_nothing_from_the_first(tmp_path, monkeypatch):
    sub, plan, executor, verifier, _ = _setup(tmp_path, certified=True)
    try:
        hunt.run_hunt(sub, plan, executor, verifier)
        known = {r[0] for r in sub.conn.execute("SELECT attempt_id FROM attempts")}
        real = justify.derive_tag

        def derive_after_disowning_the_new_attempts(*args, **kwargs):
            for (attempt_id,) in sub.conn.execute("SELECT attempt_id FROM attempts").fetchall():
                if attempt_id not in known:
                    sub.disown(attempt_id)
            return real(*args, **kwargs)

        monkeypatch.setattr(hunt.justify, "derive_tag", derive_after_disowning_the_new_attempts)
        with pytest.raises(hunt.HuntError, match="own evidence"):
            hunt.run_hunt(sub, plan, executor, verifier)
        assert len(ledger.entries_for(sub, plan.hypothesis_key)) == 1
    finally:
        sub.close()
