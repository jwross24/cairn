import pytest
from test_small_numbers_floor_hunt import _setup

from cairn import hunt, ladder
from cairn import small_numbers_floor as floor


def test_a_plain_hunt_commits_its_entropy_after_the_hypothesis_and_before_its_draw(tmp_path):
    sub, plan, _, adapter, _ = _setup(tmp_path)
    try:
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier)
        position, commitment = ladder.commitment_for(sub, result.record.nonce)
        assert commitment is not None
        assert (commitment.nonce, commitment.hypothesis_hash) == (result.record.nonce, plan.hypothesis_key)
        assert ladder.sequence_position(sub, plan.hypothesis_key) < position
    finally:
        sub.close()


def test_a_plain_draw_after_the_protocol_refuses_the_later_floor_run(tmp_path):
    sub, plan, protocol, adapter, _ = _setup(tmp_path)
    try:
        hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier)
        with pytest.raises(floor.FloorRefused, match="a non-floor entropy draw precedes this floor run"):
            hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
    finally:
        sub.close()


def test_a_floor_run_after_an_earlier_floor_run_is_admitted(tmp_path):
    sub, plan, protocol, adapter, _ = _setup(tmp_path)
    try:
        first = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        second = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        assert first.record.nonce != second.record.nonce
        for result in (first, second):
            floor.registration_for(sub, result)
    finally:
        sub.close()
