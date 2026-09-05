import json
import sqlite3

import pytest
from _substrate_helpers import (
    ENV_MANIFEST_HASH,
    IDENTITY_A,
    IDENTITY_B,
    SELFTEST_SUMMARY,
    TRANSCRIPT_HASH,
    launch,
    open_writer,
    recipe,
)

from cairn import canon, keys, substrate
from cairn.substrate import (
    GradeError,
    HashCollision,
    HashMismatch,
    Substrate,
    UnknownAttempt,
    UnknownNode,
    WriterAlreadyOpen,
)

NON_OK_STATUSES = ("RUNNING", "FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED")


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


def certify(sub, bundle, transcript_hash=TRANSCRIPT_HASH):
    identity = sub.put_identity_bundle(bundle)
    cert = sub.put_certificate(identity, transcript_hash, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    return identity, cert


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


def test_yanked_true_after_yank_record(writer, db_snapshot):
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
    db_snapshot(writer.conn, "yanked")
    assert writer.yanked(identity) is True


def test_recipe_insert_writes_node_and_root(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    db_snapshot(writer.conn, "recipe")
    assert key == keys.recipe_key(recipe(1))
    assert writer.get_node(key)["kind"] == "recipe"
    assert writer.is_root("recipe", key)
    assert writer.put_recipe(recipe(1)) == key
    assert writer.conn.execute("SELECT count(*) FROM recipes").fetchone()[0] == 1


def test_serve_returns_ok_manifest_after_ok_then_fail(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    ok_attempt, manifest = launch(writer, key, "OK", {"out": b"result-1"})
    launch(writer, key, "FAIL")
    db_snapshot(writer.conn, "ok-then-fail")
    served = writer.serve(key)
    assert served is not None
    assert served.output_manifest_hash == manifest
    assert served.attempt_id == ok_attempt


def test_serve_picks_the_most_recent_eligible_attempt(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"out": b"first"})
    second, manifest = launch(writer, key, "OK", {"out": b"second"})
    launch(writer, key, "FAIL")
    db_snapshot(writer.conn, "three")
    assert writer.serve(key) == substrate.Served(second, manifest)


def test_disowning_the_ok_attempt_makes_serve_none(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, _ = launch(writer, key, "OK", {"out": b"x"})
    assert writer.serve(key) is not None
    writer.disown(attempt)
    db_snapshot(writer.conn, "disowned")
    assert writer.serve(key) is None
    assert writer.get_attempt(attempt)["disowned_at"] is not None


def test_disowned_at_is_settable_once(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, _ = launch(writer, key, "OK", {"out": b"x"})
    writer.disown(attempt, at="2026-08-21T00:00:00+00:00")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.disown(attempt, at="2026-08-22T00:00:00+00:00")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE attempts SET disowned_at = NULL WHERE attempt_id = ?", (attempt,))
    db_snapshot(writer.conn, "disowned-once")
    assert writer.get_attempt(attempt)["disowned_at"] == "2026-08-21T00:00:00+00:00"


def test_inadmissible_is_settable_once(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, _ = launch(writer, key, "OK", {"out": b"x"})
    writer.mark_inadmissible(attempt)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.mark_inadmissible(attempt)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE attempts SET inadmissible = 0 WHERE attempt_id = ?", (attempt,))
    db_snapshot(writer.conn, "inadmissible-once")
    assert writer.serve(key) is None


def test_do_not_cache_recipe_never_serves(writer, db_snapshot):
    key = writer.put_recipe(recipe(1), do_not_cache=True)
    launch(writer, key, "OK", {"out": b"x"})
    launch(writer, key, "OK", {"out": b"y"})
    db_snapshot(writer.conn, "do-not-cache")
    assert writer.serve(key) is None
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE recipes SET do_not_cache = 0 WHERE recipe_key = ?", (key,))


def test_skip_cache_lookup_records_a_new_attempt_on_a_hit(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    first, manifest = launch(writer, key, "OK", {"out": b"same"})
    assert writer.serve(key).attempt_id == first
    second, manifest_again = launch(writer, key, "OK", {"out": b"same"}, skip_cache_lookup=True)
    db_snapshot(writer.conn, "skip-cache-lookup")
    assert manifest_again == manifest
    assert [a["attempt_id"] for a in writer.attempts_for(key)] == [first, second]
    assert writer.get_attempt(second)["skip_cache_lookup"] == 1
    assert writer.serve(key) == substrate.Served(second, manifest)


def test_two_differing_ok_manifests_mark_non_reproducible(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    first, manifest_1 = launch(writer, key, "OK", {"out": b"one"})
    second, manifest_2 = launch(writer, key, "OK", {"out": b"two"})
    assert manifest_1 != manifest_2
    marked = writer.mark_non_reproducible(key)
    db_snapshot(writer.conn, "non-reproducible")
    assert sorted(marked) == sorted([first, second])
    assert [a["inadmissible"] for a in writer.attempts_for(key)] == [1, 1]
    assert writer.is_root("divergence", manifest_1) and writer.is_root("divergence", manifest_2)
    assert writer.get_node(manifest_1) is not None and writer.get_node(manifest_2) is not None
    assert writer.serve(key) is None


def test_mark_non_reproducible_without_divergence_raises(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    launch(writer, key, "OK", {"out": b"same"})
    launch(writer, key, "OK", {"out": b"same"})
    with pytest.raises(substrate.SubstrateError, match="divergence"):
        writer.mark_non_reproducible(key)
    db_snapshot(writer.conn, "agreeing")
    assert [a["inadmissible"] for a in writer.attempts_for(key)] == [0, 0]
    assert writer.serve(key) is not None


@pytest.mark.parametrize("status", NON_OK_STATUSES)
def test_non_ok_status_is_never_served(writer, db_snapshot, status):
    key = writer.put_recipe(recipe(1))
    artifacts = {"out": (writer.put_blob(b"payload"), 7)}
    manifest = writer.put_output_manifest(artifacts, recipe_key=key)
    attempt = writer.start_attempt(key)
    if status != "RUNNING":
        writer.close_attempt(attempt, status, output_manifest_hash=manifest)
    db_snapshot(writer.conn, status)
    assert writer.get_attempt(attempt)["status"] == status
    assert writer.serve(key) is None


def test_missing_blob_makes_serve_none(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, manifest = launch(writer, key, "OK", {"a": b"alpha", "b": b"beta"})
    assert writer.serve(key) == substrate.Served(attempt, manifest)
    beta = substrate.blob_hash(b"beta")
    writer.conn.execute("DELETE FROM blobs WHERE hash = ?", (beta,))
    db_snapshot(writer.conn, "blob-lost")
    assert writer.serve(key) is None
    writer.put_blob(b"beta")
    assert writer.serve(key) == substrate.Served(attempt, manifest)


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
    }
    digest = writer.put_receipt(receipt)
    assert writer.put_receipt(receipt) == digest
    db_snapshot(writer.conn, "receipt")
    stored = writer.get_receipt(digest)
    assert {k: stored[k] for k in receipt} == receipt
    assert writer.get_node(digest)["kind"] == "receipt"
    assert digest == substrate.receipt_hash(receipt)
    assert substrate.receipt_hash({**receipt, "exit_status": 1}) != digest


RECEIPT = {name: ("aa" * 32 if name.endswith(("hash", "digest")) else 1) for name in substrate.RECEIPT_FIELDS}


@pytest.fixture
def populated(writer):
    key = writer.put_recipe(recipe(1))
    receipt = writer.put_receipt(RECEIPT)
    attempt = writer.start_attempt(key)
    artifacts = {"out": (writer.put_blob(b"x"), 1)}
    manifest = writer.put_output_manifest(artifacts, recipe_key=key)
    writer.close_attempt(
        attempt,
        "OK",
        output_manifest_hash=manifest,
        receipt_hash=receipt,
        verifier_result_hash="55" * 32,
        certificate_hash="66" * 32,
    )
    running = writer.start_attempt(key)
    identity, cert = certify(writer, IDENTITY_A)
    writer.weaken_grade(manifest, "Verifiable")
    writer.add_yank_record(
        "yank-1", identity, "{}", kind="human_path", ruling_ref="r-1", record_digest="dd" * 32, file_offset=0
    )
    writer.add_salt("class-1", "salt-1", kind="human_path", record_digest="dd" * 32, file_offset=1)
    return writer, {
        "key": key,
        "attempt": attempt,
        "running": running,
        "manifest": manifest,
        "identity": identity,
        "cert": cert,
        "receipt": receipt,
    }


APPEND_ONLY_STATEMENTS = [
    ("nodes", "UPDATE nodes SET kind = 'other' WHERE hash = :manifest"),
    ("nodes", "DELETE FROM nodes WHERE hash = :manifest"),
    ("nodes", "UPDATE nodes SET replay_grade = 'AuditOnly' WHERE hash = :manifest"),
    ("recipes", "UPDATE recipes SET salt = 'x' WHERE recipe_key = :key"),
    ("recipes", "DELETE FROM recipes WHERE recipe_key = :key"),
    ("lineage", "UPDATE lineage SET edge_kind = 'x' WHERE child_hash = :manifest"),
    ("lineage", "DELETE FROM lineage WHERE child_hash = :manifest"),
    ("roots", "UPDATE roots SET root_kind = 'ledger_row' WHERE node_hash = :key"),
    ("roots", "DELETE FROM roots WHERE node_hash = :key"),
    ("skill_certificates", "UPDATE skill_certificates SET cert_hash = 'ff' WHERE identity_bundle_hash = :identity"),
    ("skill_certificates", "DELETE FROM skill_certificates WHERE identity_bundle_hash = :identity"),
    ("yank_records", "UPDATE yank_records SET reach_predicate = 'x' WHERE yank_id = 'yank-1'"),
    ("yank_records", "DELETE FROM yank_records WHERE yank_id = 'yank-1'"),
    ("salts", "UPDATE salts SET salt = 'x' WHERE class_key = 'class-1'"),
    ("salts", "DELETE FROM salts WHERE class_key = 'class-1'"),
    ("grade_history", "UPDATE grade_history SET to_grade = 'Replayable' WHERE node_hash = :manifest"),
    ("grade_history", "DELETE FROM grade_history WHERE node_hash = :manifest"),
    ("attempts", "UPDATE attempts SET status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET status = 'RUNNING', ended_at = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', inadmissible = 1 WHERE attempt_id = :attempt"),
    ("attempts", "DELETE FROM attempts WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', recipe_key = 'other' WHERE attempt_id = :running"),
    (
        "attempts",
        "UPDATE attempts SET status = 'OK', ended_at = 'x', replay_grade = 'AuditOnly' WHERE attempt_id = :running",
    ),
    (
        "attempts",
        "UPDATE attempts SET status = 'OK', ended_at = 'x', skip_cache_lookup = 1 WHERE attempt_id = :running",
    ),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', started_at = 'x' WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', disowned_at = 'x' WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = 'x', inadmissible = 1 WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET status = 'OK', ended_at = NULL WHERE attempt_id = :running"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', receipt_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', verifier_result_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', certificate_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', replay_grade = 'AuditOnly' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', ended_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET disowned_at = 'x', started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, receipt_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, verifier_result_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, certificate_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, output_manifest_hash = NULL WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, replay_grade = 'AuditOnly' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, ended_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, recipe_key = 'other' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, status = 'FAIL' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, skip_cache_lookup = 1 WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, started_at = 'x' WHERE attempt_id = :attempt"),
    ("attempts", "UPDATE attempts SET inadmissible = 1, disowned_at = 'x' WHERE attempt_id = :attempt"),
    ("receipts", "UPDATE receipts SET exit_status = 3 WHERE receipt_hash = :receipt"),
    ("receipts", "DELETE FROM receipts WHERE receipt_hash = :receipt"),
]


@pytest.mark.parametrize(
    ("table", "statement"),
    APPEND_ONLY_STATEMENTS,
    ids=[f"{t}:{s.split()[0]}:{i}" for i, (t, s) in enumerate(APPEND_ONLY_STATEMENTS)],
)
def test_append_only_triggers_refuse_update_and_delete(populated, db_snapshot, table, statement):
    sub, ids = populated
    before = db_snapshot(sub.conn, f"before:{table}")
    row_before = sub.get_attempt(ids["attempt"]), sub.get_attempt(ids["running"])
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        sub.conn.execute(statement, ids)
    assert db_snapshot(sub.conn, f"after:{table}") == before
    assert (sub.get_attempt(ids["attempt"]), sub.get_attempt(ids["running"])) == row_before


def test_running_to_terminal_close_is_the_single_permitted_update(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt = writer.start_attempt(key)
    writer.close_attempt(attempt, "INTERRUPTED")
    row = writer.get_attempt(attempt)
    assert row["status"] == "INTERRUPTED" and row["ended_at"] is not None
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.close_attempt(attempt, "OK")
    with pytest.raises(ValueError, match="status must be one of"):
        writer.close_attempt(attempt, "RUNNING")
    running = writer.start_attempt(key)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute("UPDATE attempts SET status = 'OK' WHERE attempt_id = ?", (running,))
    db_snapshot(writer.conn, "closes")
    assert writer.get_attempt(running)["status"] == "RUNNING"


def test_reader_sees_writes_and_cannot_write(tmp_path, writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    attempt, manifest = launch(writer, key, "OK", {"out": b"x"})
    reader = Substrate.open(tmp_path / "substrate.sqlite", role="reader")
    try:
        assert reader.serve(key) == substrate.Served(attempt, manifest)
        assert reader.effective_grade(manifest) == "Replayable"
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            reader.conn.execute("INSERT INTO blobs VALUES ('00', 0, x'', 'now')")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            reader.put_blob(b"nope")
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            reader.disown(attempt)
    finally:
        reader.close()
    db_snapshot(writer.conn, "reader")
    assert writer.get_attempt(attempt)["disowned_at"] is None


def test_reader_on_missing_file_fails_to_open(tmp_path):
    with pytest.raises(sqlite3.OperationalError, match="unable to open database file"):
        Substrate.open(tmp_path / "absent.sqlite", role="reader")


NON_REPRODUCIBLE_REFUSALS = ("disowned", "not_replayable", "one_manifest")


@pytest.mark.parametrize("setup", NON_REPRODUCIBLE_REFUSALS)
def test_mark_non_reproducible_ignores_disowned_and_non_replayable_attempts(writer, db_snapshot, setup):
    key = writer.put_recipe(recipe(1))
    grade = "Verifiable" if setup == "not_replayable" else "Replayable"
    first, _ = launch(writer, key, "OK", {"out": b"one"}, replay_grade=grade)
    second, _ = launch(writer, key, "OK", {"out": b"one" if setup == "one_manifest" else b"two"}, replay_grade=grade)
    if setup == "disowned":
        writer.disown(second)
    with pytest.raises(substrate.SubstrateError, match="divergence needs two"):
        writer.mark_non_reproducible(key)
    db_snapshot(writer.conn, f"refused:{setup}")
    assert [a["inadmissible"] for a in writer.attempts_for(key)] == [0, 0]
    assert writer.conn.execute("SELECT count(*) FROM roots WHERE root_kind = 'divergence'").fetchone()[0] == 0


def test_mark_non_reproducible_skips_an_already_inadmissible_attempt(writer, db_snapshot):
    key = writer.put_recipe(recipe(1))
    first, manifest_1 = launch(writer, key, "OK", {"out": b"one"})
    second, manifest_2 = launch(writer, key, "OK", {"out": b"two"})
    writer.mark_inadmissible(first)
    marked = writer.mark_non_reproducible(key)
    db_snapshot(writer.conn, "skip-already-inadmissible")
    assert marked == [second]
    assert [a["inadmissible"] for a in writer.attempts_for(key)] == [1, 1]
    assert writer.is_root("divergence", manifest_1) and writer.is_root("divergence", manifest_2)


@pytest.mark.parametrize("call", ["close_attempt", "disown", "mark_inadmissible"])
def test_unknown_attempt_id_raises_on_every_attempt_mutation(writer, db_snapshot, call):
    args = ("INTERRUPTED",) if call == "close_attempt" else ()
    with pytest.raises(UnknownAttempt, match="no attempt"):
        getattr(writer, call)("nosuch", *args)
    assert db_snapshot(writer.conn, f"unknown:{call}")["attempts"] == 0


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


WHY_NOT_SERVED = [
    ("unknown_recipe", "no_recipe"),
    ("no_attempts", "no_attempts"),
    ("status=FAIL", "fail"),
    ("disowned", "disowned"),
    ("inadmissible", "inadmissible"),
    ("missing_blob", "missing_blob"),
    ("do_not_cache", "do_not_cache"),
]


@pytest.mark.parametrize(("why_not", "setup"), WHY_NOT_SERVED, ids=[s for _, s in WHY_NOT_SERVED])
def test_every_refused_serve_logs_why_not(writer, json_test_log, db_snapshot, why_not, setup):
    key = keys.recipe_key(recipe(1))
    if setup != "no_recipe":
        key = writer.put_recipe(recipe(1), do_not_cache=setup == "do_not_cache")
    if setup not in ("no_recipe", "no_attempts"):
        attempt, _ = launch(
            writer, key, "FAIL" if setup == "fail" else "OK", None if setup == "fail" else {"out": b"payload"}
        )
        if setup == "disowned":
            writer.disown(attempt)
        if setup == "inadmissible":
            writer.mark_inadmissible(attempt)
        if setup == "missing_blob":
            writer.conn.execute("DELETE FROM blobs WHERE hash = ?", (substrate.blob_hash(b"payload"),))
    db_snapshot(writer.conn, setup)
    assert writer.serve(key) is None
    decisions = [
        json.loads(line) for line in json_test_log.read_text().splitlines() if json.loads(line).get("event") == "serve"
    ]
    assert decisions[-1] == {**decisions[-1], "served": False, "why_not": why_not, "recipe_key": key}
