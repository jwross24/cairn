import json
import sqlite3
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from cairn import attest, bundle, canon, cli, human_authority, substrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _substrate_helpers import open_writer

GATE_HASH = "a1" * 32
STATEMENT_HASH = "b2" * 32
SKILL_HASH = "c3" * 32
AT = "2026-09-29T10:00:00Z"


@pytest.fixture
def authority_store(tmp_path, clear_flags):
    database = tmp_path / "substrate.sqlite"
    attest_path = tmp_path / "attestations.log"
    clear_flags(attest_path)
    attest.init(attest_path, "d4" * 32)
    sub = open_writer(tmp_path)
    yield sub, attest_path, database
    sub.close()


def _fields(kind):
    if kind == human_authority.OPERATOR_SESSION:
        return {
            "session_id": "session-1",
            "issued_by": "operator-1",
            "opened_at": "2026-09-29T09:00:00Z",
            "expires_at": "2026-09-29T09:30:00Z",
        }
    if kind == human_authority.STATEMENT_RATIFICATION:
        return {"statement_hash": STATEMENT_HASH, "issued_by": "operator-1", "at": AT}
    if kind == human_authority.YANK_RULING:
        return {
            "ruling_ref": "ruling-1",
            "yank_id": "yank-1",
            "skill_identity_hash": SKILL_HASH,
            "reach_predicate": json.dumps({"skill_identity_hash": SKILL_HASH}, sort_keys=True, separators=(",", ":")),
            "issued_by": "operator-1",
            "at": AT,
        }
    return {"class_key": "class-1", "salt": "salt-2", "issued_by": "operator-1", "at": AT}


def test_exact_attested_records_bind_each_authorized_action(authority_store):
    sub, attest_path, _ = authority_store
    records = {
        kind: human_authority.append(sub, attest_path, kind, _fields(kind), gate_bundle_hash=GATE_HASH)
        for kind in human_authority.KINDS
    }
    gate = SimpleNamespace(
        hash=GATE_HASH,
        tiers={"operator_session": {"required": True, "max_duration_s": 3600}},
    )
    assert human_authority.operator_session_open(sub, gate, attest_path, at="2026-09-29T09:15:00Z")
    assert not human_authority.operator_session_open(sub, gate, attest_path, at="2026-09-29T09:30:00Z")
    assert not human_authority.operator_session_open(sub, gate, attest_path, at="2026-09-29T08:59:59Z")
    assert not human_authority.operator_session_open(
        sub,
        SimpleNamespace(hash="e5" * 32, tiers=gate.tiers),
        attest_path,
        at="2026-09-29T09:15:00Z",
    )
    assert not human_authority.operator_session_open(
        sub,
        SimpleNamespace(hash=GATE_HASH, tiers={"operator_session": {"required": True}}),
        attest_path,
        at="2026-09-29T09:15:00Z",
    )
    assert not human_authority.operator_session_open(
        sub,
        SimpleNamespace(
            hash=GATE_HASH, tiers={"operator_session": {**gate.tiers["operator_session"], "unexpected": 1}}
        ),
        attest_path,
        at="2026-09-29T09:15:00Z",
    )
    assert human_authority.statement_ratified(sub, STATEMENT_HASH, GATE_HASH, attest_path)
    assert not human_authority.statement_ratified(sub, "e5" * 32, GATE_HASH, attest_path)
    assert not human_authority.statement_ratified(sub, STATEMENT_HASH, "e5" * 32, attest_path)
    future_statement = "e5" * 32
    human_authority.append(
        sub,
        attest_path,
        human_authority.STATEMENT_RATIFICATION,
        {"statement_hash": future_statement, "issued_by": "operator-1", "at": "9999-01-01T00:00:00Z"},
        gate_bundle_hash=GATE_HASH,
    )
    assert not human_authority.statement_ratified(sub, future_statement, GATE_HASH, attest_path)
    yank = records[human_authority.YANK_RULING]
    reach = {"skill_identity_hash": SKILL_HASH}
    assert human_authority.yank_ruling_matches(
        sub,
        yank_id="yank-1",
        skill_identity_hash=SKILL_HASH,
        reach=reach,
        ruling_ref="ruling-1",
        record_digest=yank["record_digest"],
        file_offset=yank["file_offset"],
        attest_path=attest_path,
    )
    assert not human_authority.yank_ruling_matches(
        sub,
        yank_id="yank-1",
        skill_identity_hash=SKILL_HASH,
        reach={"skill_identity_hash": SKILL_HASH, "seed": [1, 4]},
        ruling_ref="ruling-1",
        record_digest=yank["record_digest"],
        file_offset=yank["file_offset"],
        attest_path=attest_path,
    )
    assert not human_authority.yank_ruling_matches(
        sub,
        yank_id="yank-1",
        skill_identity_hash=SKILL_HASH,
        reach=reach,
        ruling_ref="ruling-1",
        record_digest="e5" * 32,
        file_offset=yank["file_offset"],
        attest_path=attest_path,
    )
    assert not human_authority.yank_ruling_matches(
        sub,
        yank_id="yank-1",
        skill_identity_hash=SKILL_HASH,
        reach=reach,
        ruling_ref="ruling-1",
        record_digest=yank["record_digest"],
        file_offset=yank["file_offset"] + 1,
        attest_path=attest_path,
    )
    salt = records[human_authority.SALT_ISSUANCE]
    assert human_authority.salt_issuance_matches(
        sub,
        class_key="class-1",
        salt="salt-2",
        record_digest=salt["record_digest"],
        file_offset=salt["file_offset"],
        attest_path=attest_path,
    )
    assert not human_authority.salt_issuance_matches(
        sub,
        class_key="class-1",
        salt="salt-3",
        record_digest=salt["record_digest"],
        file_offset=salt["file_offset"],
        attest_path=attest_path,
    )
    assert not human_authority.salt_issuance_matches(
        sub,
        class_key="class-1",
        salt="salt-2",
        record_digest="e5" * 32,
        file_offset=salt["file_offset"],
        attest_path=attest_path,
    )
    expected_counts = dict.fromkeys(human_authority.KINDS, 1)
    expected_counts[human_authority.STATEMENT_RATIFICATION] = 2
    for kind in human_authority.KINDS:
        visible = human_authority.visible_records(sub, kind, attest_path)
        assert len(visible) == expected_counts[kind]
        assert any(row["record_digest"] == records[kind]["record_digest"] for row in visible)
        assert any(row["file_offset"] == records[kind]["file_offset"] for row in visible)
    session = records[human_authority.OPERATOR_SESSION]
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute(
            f"UPDATE {human_authority.TABLE} SET producer_identity = 'forged' WHERE record_digest = ?",
            (session["record_digest"],),
        )
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute(
            f"DELETE FROM {human_authority.TABLE} WHERE record_digest = ?",
            (session["record_digest"],),
        )


def test_operator_session_renewal_requires_a_fresh_attested_record(authority_store):
    sub, attest_path, _ = authority_store
    gate = SimpleNamespace(
        hash=GATE_HASH,
        tiers={"operator_session": {"required": True, "max_duration_s": 3600}},
    )
    session_id = "renewal-session"
    issued_by = "operator-1"
    original_opened = datetime(2026, 9, 29, 9, 0, tzinfo=UTC)
    original_expires = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
    renewal_opened = datetime(2026, 9, 29, 10, 30, tzinfo=UTC)
    renewal_expires = renewal_opened + timedelta(seconds=3600)
    original_fields = {
        "session_id": session_id,
        "issued_by": issued_by,
        "opened_at": original_opened.isoformat(),
        "expires_at": original_expires.isoformat(),
    }
    original = human_authority.append(
        sub,
        attest_path,
        human_authority.OPERATOR_SESSION,
        original_fields,
        gate_bundle_hash=GATE_HASH,
    )
    original_mirror = dict(
        sub.conn.execute(
            f"SELECT kind, canonical, record_digest, file_offset, producer_identity FROM {human_authority.TABLE} WHERE record_digest = ?",
            (original["record_digest"],),
        ).fetchone()
    )

    assert human_authority.operator_session_open(
        sub, gate, attest_path, at=datetime(2026, 9, 29, 9, 30, tzinfo=UTC).isoformat()
    )
    assert not human_authority.operator_session_open(sub, gate, attest_path, at=renewal_opened.isoformat())
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute(
            f"UPDATE {human_authority.TABLE} SET producer_identity = 'forged' WHERE record_digest = ?",
            (original["record_digest"],),
        )

    renewal_fields = {
        "session_id": session_id,
        "issued_by": issued_by,
        "opened_at": renewal_opened.isoformat(),
        "expires_at": renewal_expires.isoformat(),
    }
    unattested = human_authority.write(
        sub,
        human_authority.OPERATOR_SESSION,
        renewal_fields,
        gate_bundle_hash=GATE_HASH,
        file_offset=1_000_000,
    )
    assert human_authority.visible_records(sub, human_authority.OPERATOR_SESSION, attest_path) == [original]
    assert not human_authority.operator_session_open(sub, gate, attest_path, at=renewal_opened.isoformat())

    renewed = human_authority.append(
        sub,
        attest_path,
        human_authority.OPERATOR_SESSION,
        renewal_fields,
        gate_bundle_hash=GATE_HASH,
    )
    visible = human_authority.visible_records(sub, human_authority.OPERATOR_SESSION, attest_path)
    assert visible == [original, renewed]
    assert renewed["session_id"] == original["session_id"]
    assert (renewed["record_digest"], renewed["file_offset"]) != (
        original["record_digest"],
        original["file_offset"],
    )
    assert (unattested["record_digest"], unattested["file_offset"]) == (
        renewed["record_digest"],
        1_000_000,
    )
    assert datetime.fromisoformat(renewed["expires_at"]) - datetime.fromisoformat(renewed["opened_at"]) == timedelta(
        seconds=3600
    )
    assert human_authority.operator_session_open(sub, gate, attest_path, at=renewal_opened.isoformat())
    assert not human_authority.operator_session_open(sub, gate, attest_path, at=renewed["expires_at"])
    assert visible[0] == original
    assert (
        dict(
            sub.conn.execute(
                f"SELECT kind, canonical, record_digest, file_offset, producer_identity FROM {human_authority.TABLE} WHERE record_digest = ? AND file_offset = ?",
                (original["record_digest"], original["file_offset"]),
            ).fetchone()
        )
        == original_mirror
    )


def test_mirror_rows_without_the_exact_attestation_are_absent(authority_store, tmp_path):
    sub, attest_path, _ = authority_store
    fields = _fields(human_authority.STATEMENT_RATIFICATION)
    forged = human_authority.write(
        sub, human_authority.STATEMENT_RATIFICATION, fields, gate_bundle_hash=GATE_HASH, file_offset=0
    )
    assert human_authority.visible_records(sub, human_authority.STATEMENT_RATIFICATION, attest_path) == []
    assert (
        human_authority.visible_records(
            sub,
            human_authority.STATEMENT_RATIFICATION,
            tmp_path / "missing-attestations.log",
        )
        == []
    )
    assert not human_authority.statement_ratified(sub, STATEMENT_HASH, GATE_HASH, attest_path)
    assert forged["file_offset"] == 0


def test_forged_mirror_digest_is_absent_even_at_the_real_attested_offset(authority_store):
    sub, attest_path, _ = authority_store
    kind = human_authority.STATEMENT_RATIFICATION
    fields = _fields(kind)
    raw = human_authority.canonical(kind, fields, gate_bundle_hash=GATE_HASH)
    offset = attest.append_record(attest_path, raw)
    sub.put_node(kind, raw, producer_identity=fields["issued_by"])
    sub.conn.execute(
        f"INSERT INTO {human_authority.TABLE} (kind, canonical, record_digest, file_offset, producer_identity) VALUES (?, ?, ?, ?, ?)",
        (kind, raw, "f" * 64, offset, fields["issued_by"]),
    )
    assert human_authority.visible_records(sub, kind, attest_path) == []
    assert not human_authority.statement_ratified(sub, STATEMENT_HASH, GATE_HASH, attest_path)


def test_timestamp_overflow_in_a_mirrored_attestation_is_absent(authority_store):
    sub, attest_path, _ = authority_store
    payload = {
        "kind": human_authority.OPERATOR_SESSION,
        "gate_bundle_hash": GATE_HASH,
        "session_id": "session-overflow",
        "issued_by": "operator-1",
        "opened_at": "0001-01-01T00:00:00+23:59",
        "expires_at": "0001-01-01T00:01:00+23:59",
    }
    raw = canon.encode(human_authority.RECORDS[human_authority.OPERATOR_SESSION], payload)
    offset = attest.append_record(attest_path, raw)
    digest = substrate.blob_hash(raw)
    sub.put_node(human_authority.OPERATOR_SESSION, raw, producer_identity="operator-1")
    sub.conn.execute(
        f"INSERT INTO {human_authority.TABLE} (kind, canonical, record_digest, file_offset, producer_identity) VALUES (?, ?, ?, ?, ?)",
        (human_authority.OPERATOR_SESSION, raw, digest, offset, "operator-1"),
    )
    assert human_authority.visible_records(sub, human_authority.OPERATOR_SESSION, attest_path) == []


def test_cli_append_routes_authority_kinds_through_the_mirror(pinned_bundle, tmp_path, clear_flags, capsys):
    bundle_path, pin_path = pinned_bundle()
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "attestations.log"
    clear_flags(attest_path)
    attest.init(attest_path, "d4" * 32)
    database = tmp_path / "substrate.sqlite"
    record_path = tmp_path / "session.json"
    fields = _fields(human_authority.OPERATOR_SESSION)
    record_path.write_text(json.dumps(fields))
    code = cli.main(
        [
            "--db",
            str(database),
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
            "--attest",
            str(attest_path),
            "attest",
            "append",
            "--kind",
            human_authority.OPERATOR_SESSION,
            "--record",
            str(record_path),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    document = json.loads(out)
    assert document["kind"] == human_authority.OPERATOR_SESSION
    assert document["bundle_hash"] == gate.hash
    with substrate.Substrate.open(database, role="reader") as sub:
        visible = human_authority.visible_records(sub, human_authority.OPERATOR_SESSION, attest_path)
    assert len(visible) == 1
    assert visible[0]["session_id"] == "session-1"
