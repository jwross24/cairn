import json
import sqlite3

import pytest
from _substrate_helpers import launch, recipe

from cairn import keys, substrate
from cairn.substrate import Substrate, UnknownAttempt

NON_OK_STATUSES = ("RUNNING", "FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED")


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


def test_a_nested_transaction_joins_the_open_one_and_commits_once(writer):
    with writer.transaction():
        writer.put_blob(b"one")
        with writer.transaction():
            writer.put_blob(b"two")
        assert writer.conn.in_transaction is True
    assert writer.conn.in_transaction is False
    assert writer.has_blob(substrate.blob_hash(b"one")) is True
    assert writer.has_blob(substrate.blob_hash(b"two")) is True


def test_a_failure_inside_a_nested_transaction_discards_the_whole_block(writer):
    def block():
        with writer.transaction():
            writer.put_blob(b"outer")
            with writer.transaction():
                writer.put_blob(b"inner")
                raise RuntimeError("inner")

    with pytest.raises(RuntimeError, match="inner"):
        block()
    assert writer.has_blob(substrate.blob_hash(b"outer")) is False
    assert writer.has_blob(substrate.blob_hash(b"inner")) is False


def test_a_caught_inner_failure_still_refuses_to_commit_the_block(writer):
    def block():
        with writer.transaction():
            writer.put_blob(b"before")
            try:
                with writer.transaction():
                    writer.put_blob(b"during")
                    raise RuntimeError("swallowed")
            except RuntimeError:
                pass
            writer.put_blob(b"after")

    with pytest.raises(substrate.SubstrateError, match="rolled back"):
        block()
    for payload in (b"before", b"during", b"after"):
        assert writer.has_blob(substrate.blob_hash(payload)) is False


def test_a_block_that_failed_does_not_poison_the_next_one(writer):
    def block():
        with writer.transaction():
            writer.put_blob(b"discarded")
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        block()
    with writer.transaction():
        writer.put_blob(b"kept")
    assert writer.has_blob(substrate.blob_hash(b"discarded")) is False
    assert writer.has_blob(substrate.blob_hash(b"kept")) is True
