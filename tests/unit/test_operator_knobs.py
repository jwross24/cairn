import pytest

from cairn import human_authority

GATE_HASH = "a1" * 32
STATEMENT_HASH = "b2" * 32


def session_fields(**overrides):
    return {
        "session_id": "session-1",
        "issued_by": "operator-1",
        "opened_at": "2026-09-29T10:00:00Z",
        "expires_at": "2026-09-29T11:00:00+00:00",
        **overrides,
    }


def test_session_expiry_must_be_after_opening_and_at_most_one_hour():
    encoded = human_authority.canonical(
        human_authority.OPERATOR_SESSION,
        session_fields(expires_at="2026-09-29T11:00:00Z"),
        gate_bundle_hash=GATE_HASH,
    )
    assert human_authority._decode(human_authority.OPERATOR_SESSION, encoded)["session_id"] == "session-1"
    with pytest.raises(human_authority.HumanAuthorityError, match="within 3600 seconds"):
        human_authority.canonical(
            human_authority.OPERATOR_SESSION,
            session_fields(expires_at="2026-09-29T11:00:01Z"),
            gate_bundle_hash=GATE_HASH,
        )
    with pytest.raises(human_authority.HumanAuthorityError, match="within 3600 seconds"):
        human_authority.canonical(
            human_authority.OPERATOR_SESSION,
            session_fields(expires_at="2026-09-29T10:00:00Z"),
            gate_bundle_hash=GATE_HASH,
        )


@pytest.mark.parametrize(
    ("fields", "bundle_hash", "message"),
    [
        ({**session_fields(), "extra": "x"}, GATE_HASH, "unknown fields"),
        ({k: v for k, v in session_fields().items() if k != "session_id"}, GATE_HASH, "missing fields"),
        (session_fields(opened_at=True), GATE_HASH, "timezone-aware ISO timestamp"),
        (session_fields(opened_at="2026-09-29T10:00:00"), GATE_HASH, "timezone offset"),
        (
            session_fields(opened_at="0001-01-01T00:00:00+23:59", expires_at="0001-01-01T00:01:00+23:59"),
            GATE_HASH,
            "UTC timestamp range",
        ),
        (session_fields(), "not-a-hash", "gate_bundle_hash"),
    ],
    ids=["unknown-field", "missing-field", "bool-timestamp", "naive-timestamp", "utc-overflow", "malformed-hash"],
)
def test_malformed_session_records_are_rejected(fields, bundle_hash, message):
    with pytest.raises(human_authority.HumanAuthorityError, match=message):
        human_authority.canonical(human_authority.OPERATOR_SESSION, fields, gate_bundle_hash=bundle_hash)


def test_action_hashes_and_reach_json_are_validated():
    with pytest.raises(human_authority.HumanAuthorityError, match="statement_hash"):
        human_authority.canonical(
            human_authority.STATEMENT_RATIFICATION,
            {"statement_hash": "short", "issued_by": "operator-1", "at": "2026-09-29T10:00:00Z"},
            gate_bundle_hash=GATE_HASH,
        )
    base = {
        "ruling_ref": "ruling-1",
        "yank_id": "yank-1",
        "skill_identity_hash": "c3" * 32,
        "reach_predicate": '{"seed":[1,4],"skill_identity_hash":"' + "c3" * 32 + '"}',
        "issued_by": "operator-1",
        "at": "2026-09-29T10:00:00Z",
    }
    assert human_authority.canonical(human_authority.YANK_RULING, base, gate_bundle_hash=GATE_HASH)
    with pytest.raises(human_authority.HumanAuthorityError, match="sorted compact JSON"):
        human_authority.canonical(
            human_authority.YANK_RULING,
            {**base, "reach_predicate": '{ "skill_identity_hash": "' + "c3" * 32 + '", "seed": [1, 4] }'},
            gate_bundle_hash=GATE_HASH,
        )


def test_boolean_file_offsets_are_rejected_before_any_storage_access():
    with pytest.raises(human_authority.HumanAuthorityError, match="non-negative int"):
        human_authority.write(
            None,
            human_authority.STATEMENT_RATIFICATION,
            {"statement_hash": STATEMENT_HASH, "issued_by": "operator-1", "at": "2026-09-29T10:00:00Z"},
            gate_bundle_hash=GATE_HASH,
            file_offset=True,
        )
