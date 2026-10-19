import json
import sqlite3

import pytest
from _substrate_helpers import (
    ENV_MANIFEST_HASH,
    IDENTITY_A,
    IDENTITY_B,
    SELFTEST_SUMMARY,
    TRANSCRIPT_HASH,
    certify,
    open_writer,
    recipe,
)

from cairn import canon, keys, substrate
from cairn.substrate import (
    GradeError,
    HashCollision,
    HashMismatch,
    Substrate,
    UnknownNode,
    WriterAlreadyOpen,
)


def test_writer_opens_in_wal_with_pragmas_and_schema(writer, json_test_log, db_snapshot):
    assert writer.journal_mode() == "wal"
    assert writer.conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    assert writer.conn.execute("PRAGMA synchronous").fetchone()[0] == 1
    assert writer.conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    tables = {r[0] for r in writer.conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {
        "blobs",
        "nodes",
        "lineage",
        "roots",
        "recipes",
        "attempts",
        "receipts",
        "skill_certificates",
        "yank_records",
        "salts",
        "escrow",
        "grade_history",
    } <= tables
    db_snapshot(writer.conn, "fresh")
    records = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    assert any(r.get("event") == "open" and r.get("journal_mode") == "wal" for r in records)


def test_second_writer_in_process_is_refused_until_close(writer, tmp_path, db_snapshot):
    with pytest.raises(WriterAlreadyOpen, match="already open"):
        Substrate.open(tmp_path / "other.sqlite", role="writer")
    assert not (tmp_path / "other.sqlite").exists()
    writer.close()
    other = Substrate.open(tmp_path / "other.sqlite", role="writer")
    db_snapshot(other.conn, "second-writer-after-close")
    other.close()


def test_weaken_grade_down_the_order_and_effective_grade_follows(writer, db_snapshot):
    node = writer.put_node("evidence", b"payload", replay_grade="Replayable")
    writer.weaken_grade(node, "Verifiable", reason="producer verifier only")
    assert writer.effective_grade(node) == "Verifiable"
    writer.weaken_grade(node, "AuditOnly")
    db_snapshot(writer.conn, "weakened")
    assert writer.effective_grade(node) == "AuditOnly"
    assert writer.get_node(node)["replay_grade"] == "Replayable"
    assert [(h["from_grade"], h["to_grade"]) for h in writer.grade_history(node)] == [
        ("Replayable", "Verifiable"),
        ("Verifiable", "AuditOnly"),
    ]


@pytest.mark.parametrize(
    ("start", "to", "match"),
    [
        ("AuditOnly", "Verifiable", "strengthen"),
        ("Verifiable", "Verifiable", "same grade"),
        ("Verifiable", "Replayable", "strengthen"),
        ("Replayable", "Replayable", "same grade"),
    ],
)
def test_weaken_grade_refuses_strengthening_and_same_grade(writer, db_snapshot, start, to, match):
    node = writer.put_node("evidence", f"{start}->{to}".encode(), replay_grade=start)
    with pytest.raises(GradeError, match=match):
        writer.weaken_grade(node, to)
    db_snapshot(writer.conn, "refused")
    assert writer.grade_history(node) == []
    assert writer.effective_grade(node) == start


def test_effective_grade_of_unknown_node_raises(writer, db_snapshot):
    with pytest.raises(UnknownNode, match="no node"):
        writer.effective_grade("00" * 32)
    assert db_snapshot(writer.conn, "unknown-node")["nodes"] == 0


def test_certified_true_for_well_formed_row_false_for_unknown_and_tampered(writer, db_snapshot):
    identity, cert = certify(writer, IDENTITY_A)
    assert writer.certified(identity) is True
    assert writer.certified(keys.identity_bundle_hash(IDENTITY_B)) is False
    assert cert == substrate.certificate_hash(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH)
    assert writer.get_node(cert)["kind"] == "skill_certificate"
    assert writer.is_root("certificate", cert)
    assert writer.lineage_of(cert) == [{"child_hash": cert, "parent_hash": identity, "edge_kind": "certifies"}]
    stored = writer.get_certificate(identity)["selftest_summary"]
    assert stored == json.dumps(SELFTEST_SUMMARY, sort_keys=True, separators=(",", ":"))
    assert json.loads(stored) == SELFTEST_SUMMARY
    tampered_identity = writer.put_identity_bundle(IDENTITY_B)
    writer.conn.execute(
        "INSERT INTO skill_certificates VALUES (?, ?, ?, ?, ?, ?)",
        (tampered_identity, "ff" * 32, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, "{}", "now"),
    )
    db_snapshot(writer.conn, "certified+tampered")
    assert writer.certified(tampered_identity) is False


def test_transplanted_certificate_row_is_uncertified(tmp_path, db_snapshot):
    source = open_writer(tmp_path, "source.sqlite")
    identity_a, cert_a = certify(source, IDENTITY_A)
    identity_b = source.put_identity_bundle(IDENTITY_B)
    row = source.get_certificate(identity_a)
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        source.conn.execute(
            "INSERT INTO skill_certificates VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity_b,
                row["cert_hash"],
                row["transcript_hash"],
                row["env_manifest_hash"],
                row["selftest_summary"],
                row["at"],
            ),
        )
    source.close()
    target = open_writer(tmp_path, "target.sqlite")
    try:
        target.put_identity_bundle(IDENTITY_B)
        target.conn.execute(
            "INSERT INTO skill_certificates VALUES (?, ?, ?, ?, ?, ?)",
            (
                identity_b,
                row["cert_hash"],
                row["transcript_hash"],
                row["env_manifest_hash"],
                row["selftest_summary"],
                row["at"],
            ),
        )
        db_snapshot(target.conn, "transplanted")
        assert target.get_certificate(identity_b)["cert_hash"] == cert_a
        assert target.certified(identity_b) is False
        assert target.certified(identity_a) is False
    finally:
        target.close()


def test_certificate_for_identity_without_node_is_refused(writer, db_snapshot):
    unknown = keys.identity_bundle_hash(IDENTITY_B)
    with pytest.raises(UnknownNode, match="has no nodes row"):
        writer.put_certificate(unknown, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
        writer.conn.execute(
            "INSERT INTO skill_certificates VALUES (?, ?, ?, ?, ?, ?)",
            (unknown, "11" * 32, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, "{}", "now"),
        )
    db_snapshot(writer.conn, "refused")
    assert writer.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0
    assert writer.conn.execute("SELECT count(*) FROM nodes WHERE kind = 'skill_certificate'").fetchone()[0] == 0


def test_unattested_human_yank_record_is_not_visible(writer, db_snapshot):
    identity = writer.put_identity_bundle(IDENTITY_A)
    assert writer.yanked(identity) is False
    writer.add_yank_record(
        "yank-1",
        identity,
        '{"bits":[0,50]}',
        kind="human_path",
        ruling_ref="r-1",
        record_digest="dd" * 32,
        file_offset=0,
    )
    db_snapshot(writer.conn, "unattested-yank")
    assert writer.yanked(identity) is False


def test_identical_node_reinsert_is_noop_and_differing_bytes_collide(writer, db_snapshot):
    digest = writer.put_node("evidence", b"bytes-1")
    assert writer.put_node("evidence", b"bytes-1") == digest
    assert writer.conn.execute("SELECT count(*) FROM nodes").fetchone()[0] == 1
    planted = substrate.node_hash_for("evidence", b"other")
    writer.conn.execute("INSERT INTO nodes VALUES (?, 'evidence', ?, 'Replayable', NULL, 'now')", (planted, b"planted"))
    with pytest.raises(HashCollision, match="different bytes or kind"):
        writer.put_node("evidence", b"other")
    with pytest.raises(HashMismatch, match="!= recomputed"):
        writer.put_node("evidence", b"bytes-1", hash="00" * 32)
    db_snapshot(writer.conn, "nodes")
    assert writer.get_node(digest)["canonical"] == b"bytes-1"


def test_identical_blob_reput_is_noop_and_differing_bytes_collide(writer, db_snapshot):
    digest = writer.put_blob(b"blob")
    assert writer.put_blob(b"blob") == digest
    writer.conn.execute("INSERT INTO blobs VALUES (?, 3, ?, 'now')", ("ab" * 32, b"xyz"))
    writer.conn.execute("UPDATE blobs SET hash = ? WHERE hash = ?", (substrate.blob_hash(b"abc"), "ab" * 32))
    with pytest.raises(HashCollision, match="different bytes"):
        writer.put_blob(b"abc")
    db_snapshot(writer.conn, "blobs")
    assert writer.get_blob(digest) == b"blob"


def test_recipe_reinsert_with_other_cache_bit_raises(writer, db_snapshot):
    writer.put_recipe(recipe(1))
    with pytest.raises(substrate.SubstrateError, match="do_not_cache"):
        writer.put_recipe(recipe(1), do_not_cache=True)
    assert db_snapshot(writer.conn, "recipe-cache-bit")["recipes"] == 1


def test_node_hash_recompute_covers_identity_and_recipe_kinds(writer, db_snapshot):
    identity = writer.put_identity_bundle(IDENTITY_A)
    assert identity == keys.identity_bundle_hash(IDENTITY_A)
    canonical = canon.encode(keys.IDENTITY_BUNDLE, IDENTITY_A)
    assert writer.put_node("identity_bundle", canonical, hash=identity) == identity
    with pytest.raises(HashMismatch, match="!= recomputed"):
        writer.put_node("identity_bundle", canonical, hash=keys.node_hash("identity_bundle", canonical))
    assert db_snapshot(writer.conn, "identity-node")["nodes"] == 1


def test_output_manifest_links_recipe_inputs_and_members(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    inp = writer.put_blob(b"input")
    out = writer.put_blob(b"output")
    manifest = writer.put_output_manifest({"out": (out, 6)}, recipe_key=key, input_blobs=[inp])
    db_snapshot(writer.conn, "manifest")
    assert manifest == substrate.output_manifest_hash({"out": (out, 6)})
    assert sorted(writer.lineage_of(manifest), key=lambda e: e["edge_kind"]) == [
        {"child_hash": manifest, "parent_hash": inp, "edge_kind": "input"},
        {"child_hash": manifest, "parent_hash": key, "edge_kind": "output_of"},
    ]
    assert writer.lineage_of(out) == [{"child_hash": out, "parent_hash": manifest, "edge_kind": "member"}]


def test_receipt_round_trips_and_is_a_node(writer, db_snapshot):
    receipt = {
        "gate_bundle_hash": "bb" * 32,
        "start_mono": 1.25,
        "end_mono": 2.5,
        "cpu_user_s": 0.75,
        "cpu_sys_s": 0.125,
        "wall_s": 1.25,
        "peak_rss_bytes": 12345678,
        "scratch_bytes_written": 4096,
        "exit_status": 0,
        "stdout_digest": "11" * 32,
        "stderr_digest": "22" * 32,
        "tool_digests_hash": "33" * 32,
        "measurement_scope": "tree",
    }
    digest = writer.put_receipt(receipt)
    assert writer.put_receipt(receipt) == digest
    db_snapshot(writer.conn, "receipt")
    stored = writer.get_receipt(digest)
    assert {k: stored[k] for k in receipt} == receipt
    assert writer.get_node(digest)["kind"] == "receipt"
    assert digest == substrate.receipt_hash(receipt)
    assert substrate.receipt_hash({**receipt, "exit_status": 1}) != digest


def test_recertifying_an_identity_raises_and_leaves_no_orphan_certificate(writer, db_snapshot):
    identity, cert = certify(writer, IDENTITY_A)
    before = db_snapshot(writer.conn, "certified-once")
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        writer.put_certificate(identity, "99" * 32, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    other_cert = substrate.certificate_hash(identity, "99" * 32, ENV_MANIFEST_HASH)
    assert db_snapshot(writer.conn, "recertify-refused") == before
    assert writer.get_node(other_cert) is None
    assert writer.lineage_of(other_cert) == []
    assert not writer.is_root("certificate", other_cert)
    assert writer.get_certificate(identity)["cert_hash"] == cert
    assert writer.certified(identity) is True


GUARDS = [
    ("role", "role must be 'writer' or 'reader'"),
    ("replay_grade", "replay_grade must be one of"),
    ("root_kind", "root_kind must be one of"),
    ("grade", "grade must be one of"),
]


@pytest.mark.parametrize(("guard", "match"), GUARDS, ids=[g for g, _ in GUARDS])
def test_vocabulary_guards_refuse_a_value_outside_the_check_list(writer, tmp_path, db_snapshot, guard, match):
    calls = {
        "role": lambda: Substrate.open(tmp_path / "bad.sqlite", role="auditor"),
        "replay_grade": lambda: writer.put_node("evidence", b"x", replay_grade="Bit-identical"),
        "root_kind": lambda: writer.add_root("branch", "aa" * 32),
        "grade": lambda: writer.weaken_grade("aa" * 32, "Bit-identical"),
    }
    with pytest.raises(ValueError, match=match):
        calls[guard]()
    assert set(db_snapshot(writer.conn, f"guard:{guard}").values()) == {0}


def test_same_hash_planted_under_another_kind_is_a_collision(writer, db_snapshot):
    digest = substrate.node_hash_for("evidence", b"shared")
    writer.conn.execute(
        "INSERT INTO nodes VALUES (?, 'output_manifest', ?, 'Replayable', NULL, 'now')", (digest, b"shared")
    )
    with pytest.raises(HashCollision, match="different bytes or kind"):
        writer.put_node("evidence", b"shared")
    db_snapshot(writer.conn, "kind-collision")
    assert writer.get_node(digest)["kind"] == "output_manifest"


def test_blob_reference_hash_accepts_bytes_and_hex_alike(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    blob = writer.put_blob(b"artifact")
    from_hex = writer.put_output_manifest({"out": (blob, 8)}, recipe_key=key)
    from_bytes = writer.put_output_manifest({"out": (bytes.fromhex(blob), 8)}, recipe_key=key)
    db_snapshot(writer.conn, "blobref-forms")
    assert from_bytes == from_hex
    assert writer.lineage_of(blob) == [{"child_hash": blob, "parent_hash": from_hex, "edge_kind": "member"}]
