import pytest
from test_counterexample_hunt import _setup

from cairn import hunt, instances, ladder

CASES = {
    "SURVIVED": {"bounds": (0, 39), "trials": 3},
    "KILLED": {"certified": True},
    "INCOMPLETE": {"verifier_valid": False},
}


def _watched(sub, plan, executor, seen):
    def wrapped(context):
        if not seen:
            records = instances.nonces_for(sub, plan.hypothesis_key)
            seen.append((len(records), records[0].published_at))
            ladder.check_order(sub, hypothesis_hash=plan.hypothesis_key, nonce=records[0].nonce)
        return executor(context)

    return wrapped


@pytest.mark.parametrize("verdict", sorted(CASES))
def test_a_default_hunt_binds_one_typed_commitment_to_its_run_before_dispatch(tmp_path, verdict):
    sub, plan, executor, verifier, _ = _setup(tmp_path, **CASES[verdict])
    seen = []
    try:
        result = hunt.run_hunt(sub, plan, _watched(sub, plan, executor, seen), verifier)
        assert result.verdict == verdict
        assert seen == [(1, None)]
        commitments = sub.conn.execute("SELECT hash FROM nodes WHERE kind = ?", (ladder.COMMITMENT_KIND,)).fetchall()
        assert len(commitments) == 1
        _, commitment = ladder.commitment_for(sub, result.record.nonce)
        assert commitment.hash == commitments[0]["hash"]
        parents = {row["parent_hash"] for row in sub.lineage_of(result.run_hash)}
        assert commitment.hash in parents
        assert len(instances.nonces_for(sub, plan.hypothesis_key)) == 1
    finally:
        sub.close()


def test_a_hunt_whose_order_check_refuses_never_dispatches(tmp_path, monkeypatch):
    sub, plan, executor, verifier, _ = _setup(tmp_path)
    calls = []
    try:

        def refuse(*args, **kwargs):
            raise ladder.RunRefused(ladder.COMMITMENT_ABSENT, "planted")

        monkeypatch.setattr(ladder, "check_order", refuse)
        with pytest.raises(ladder.RunRefused):
            hunt.run_hunt(sub, plan, lambda context: calls.append(context) or executor(context), verifier)
        assert calls == []
    finally:
        sub.close()
