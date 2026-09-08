import sys
from pathlib import Path

import pytest

from cairn import canon, disagreement, keys
from cairn.disagreement import (
    CLASSIFICATIONS,
    HARNESS_BUG,
    INCONCLUSIVE,
    OUT_OF_SCOPE,
    OWNER_HUMAN,
    OWNER_PROVER,
    OWNERS,
    PROOF_GAP,
    ROUTING,
    STATEMENT_ERROR,
    DisagreementError,
    DisagreementRecord,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _substrate_helpers import open_writer

STATEMENT_HASH = "ab" * 32
LEFT = "11" * 32
RIGHT = "22" * 32
ITEM_ID = "33" * 32
AT = "2026-09-02T00:00:00+00:00"


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


def _record(**overrides):
    fields = {
        "statement_hash": STATEMENT_HASH,
        "left_hash": LEFT,
        "right_hash": RIGHT,
        "classification": STATEMENT_ERROR,
        "owner": OWNER_HUMAN,
        "frozen_tag": "CONJECTURE",
        "item_id": ITEM_ID,
        "raised_at": AT,
    }
    fields.update(overrides)
    return DisagreementRecord(**fields)


def test_routing_covers_classifications_exactly_and_every_owner_is_valid():
    assert tuple(sorted(ROUTING)) == tuple(sorted(CLASSIFICATIONS))
    assert all(owner in OWNERS for owner in ROUTING.values())


@pytest.mark.parametrize(
    "classification",
    [STATEMENT_ERROR, PROOF_GAP, HARNESS_BUG, OUT_OF_SCOPE, INCONCLUSIVE],
)
def test_a_record_carries_the_routed_owner(classification):
    owner = ROUTING[classification]
    record = _record(classification=classification, owner=owner)
    assert record.owner == owner


def test_an_unknown_classification_is_refused():
    with pytest.raises(DisagreementError, match="classification must be one of"):
        _record(classification="wrong_statement", owner=OWNER_HUMAN)


def test_an_owner_argued_to_disagree_with_routing_is_refused():
    with pytest.raises(DisagreementError, match="owner for statement_error must be"):
        _record(classification=STATEMENT_ERROR, owner=OWNER_PROVER)


def test_left_hash_equal_right_hash_is_refused():
    with pytest.raises(DisagreementError, match="two distinct artifacts"):
        _record(left_hash=LEFT, right_hash=LEFT)


def test_a_frozen_tag_outside_claims_tags_is_refused():
    with pytest.raises(DisagreementError, match="frozen_tag must be one of"):
        _record(frozen_tag="UNSOUND")


BASE_FIELDS = {
    "statement_hash": STATEMENT_HASH,
    "left_hash": LEFT,
    "right_hash": RIGHT,
    "classification": STATEMENT_ERROR,
    "owner": OWNER_HUMAN,
    "frozen_tag": "CONJECTURE",
    "item_id": ITEM_ID,
    "raised_at": AT,
}
FIELD_VARIANTS = {
    "statement_hash": "cd" * 32,
    "left_hash": "44" * 32,
    "right_hash": "55" * 32,
    "classification": PROOF_GAP,
    "owner": OWNER_PROVER,
    "frozen_tag": "PROVEN",
    "item_id": "66" * 32,
    "raised_at": "2026-09-02T00:01:00+00:00",
}


def _digest(fields):
    canonical = canon.encode(disagreement.DISAGREEMENT_RECORD, fields)
    return keys.node_hash(disagreement.KIND, canonical)


@pytest.mark.parametrize("field_name", list(BASE_FIELDS))
def test_the_record_hash_changes_when_any_single_field_changes(field_name):
    base = _digest(BASE_FIELDS)
    changed = dict(BASE_FIELDS)
    changed[field_name] = FIELD_VARIANTS[field_name]
    assert _digest(changed) != base


def test_record_on_an_unknown_statement_raises_and_writes_no_row(writer):
    with pytest.raises(disagreement.DisagreementError, match="no claim statement"):
        disagreement.record(
            writer,
            statement_hash=STATEMENT_HASH,
            left_hash=LEFT,
            right_hash=RIGHT,
            classification=STATEMENT_ERROR,
            at=AT,
        )
    count = writer.conn.execute("SELECT COUNT(*) FROM disagreements").fetchone()[0]
    assert count == 0


def test_the_module_public_api_is_closed():
    public = {
        name
        for name, obj in vars(disagreement).items()
        if not name.startswith("_") and callable(obj) and getattr(obj, "__module__", None) == "cairn.disagreement"
    }
    assert public == {
        "DisagreementError",
        "DisagreementRecord",
        "canonical",
        "check_artifacts",
        "record",
        "records_for",
        "standing",
        "freeze_for",
        "released",
    }
