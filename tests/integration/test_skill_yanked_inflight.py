import json
import multiprocessing
import os
import signal
import sqlite3
import time
from pathlib import Path

import _substrate_helpers as helpers
import pytest

from cairn import escrow, runner, yank
from cairn.profile import Evaluation
from cairn.substrate import Substrate

FIXTURES = str(Path(__file__).resolve().parents[1] / "fixtures")
REVISION = "aa" * 32


@pytest.fixture
def writer(tmp_path):
    with Substrate.open(tmp_path / "substrate.sqlite") as sub:
        sub.conn.create_function("test_settler", 0, lambda: "runner")
        sub.conn.executescript(
            "CREATE TABLE settlement_updates (attempt_id TEXT, settler TEXT);"
            "CREATE TRIGGER record_settlement AFTER UPDATE ON escrow "
            "BEGIN INSERT INTO settlement_updates VALUES (NEW.attempt_id, test_settler()); END;"
        )
        yield sub


def _record(sub, *, outside=False):
    return yank.record(
        sub,
        yank_id="test-yank",
        skill_identity_hash=REVISION,
        kind=yank.HUMAN_PATH,
        attest_path="unused-attestation",
        reach={"skill_identity_hash": REVISION, "seed": 2} if outside else None,
        ruling=yank.Ruling("test-ruling", "bb" * 32, 0),
    )


def _yank_after_ready(db_path, runs, outside, closed, pause_settlement):
    deadline = time.monotonic() + 15
    ready = None
    while ready is None:
        ready = next(Path(runs).glob("*/scratch/ready"), None)
        if time.monotonic() >= deadline:
            raise TimeoutError("child did not announce readiness")
        time.sleep(0.005)
    os.kill(int(ready.read_text()), 0)
    with Substrate.open(db_path) as sub:
        sub.conn.create_function("test_settler", 0, lambda: "yank-controller")
        pauses = []

        def pause(statement):
            if not pauses and statement.startswith("SELECT * FROM escrow"):
                pauses.append((sub.conn.in_transaction, closed.wait(10)))

        if pause_settlement:
            sub.conn.set_trace_callback(pause)
        rows = sub.conn.execute("SELECT * FROM attempts WHERE status='RUNNING'").fetchall()
        assert len(rows) == 1
        outcome = _record(sub, outside=outside)
        assert (rows[0]["attempt_id"] in outcome.disowned) is not outside
        if pause_settlement:
            assert pauses == [(False, True)]
    if outside:
        (ready.parent / "finish").write_text("finish")


def _launch(sub, tmp_path, **document):
    return runner.launch(
        sub,
        "skills.yank_target",
        helpers.recipe(),
        bundle_hash="cc" * 32,
        evaluation=Evaluation(1.0, 1.0, 0.5),
        ceiling_multiplier=5,
        tool_digests={"fixture": "dd" * 32},
        scratch_root=tmp_path / "runs",
        wall_cap_multiplier=1,
        wall_cap_floor_s=0,
        env_extra={"PYTHONPATH": FIXTURES},
        stdin_document=document,
    )


def _inflight(sub, tmp_path, *, outside=False, ignore_term=False, pause_settlement=False):
    context = multiprocessing.get_context("spawn")
    closed = context.Event()
    controller = context.Process(
        target=_yank_after_ready, args=(str(sub.path), str(tmp_path / "runs"), outside, closed, pause_settlement)
    )
    controller.start()
    try:
        try:
            return _launch(sub, tmp_path, ignore_term=ignore_term)
        finally:
            closed.set()
            controller.join(15)
            assert controller.exitcode == 0
    finally:
        closed.set()
        if controller.is_alive():
            controller.terminate()
            controller.join(5)
        if controller.is_alive():
            controller.kill()
            controller.join(5)
        controller.close()


@pytest.mark.parametrize("ignore_term", [False, True], ids=["term", "kill"])
def test_a_covering_yank_terminates_the_child_and_releases_escrow_once(writer, tmp_path, ignore_term):
    attempt = _inflight(writer, tmp_path, ignore_term=ignore_term)
    row = writer.get_attempt(attempt.attempt_id)
    receipt = dict(
        writer.conn.execute("SELECT * FROM receipts WHERE receipt_hash=?", (attempt.receipt_hash,)).fetchone()
    )
    reservation = escrow.reservation(writer, attempt.attempt_id)
    print(json.dumps({"attempt": row, "receipt": receipt, "escrow": reservation}, sort_keys=True))
    assert attempt.status == row["status"] == "SKILL_YANKED"
    assert attempt.launch.skill_yanked and not attempt.launch.timed_out
    assert row["receipt_hash"] == receipt["receipt_hash"]
    assert 0 < receipt["wall_s"] < 5 and receipt["peak_rss_bytes"] > 0
    assert row["disowned_at"] is not None
    assert reservation["released_by"] == "disowned" and reservation["spent_at"] is None
    assert writer.conn.execute("SELECT COUNT(*) FROM settlement_updates").fetchone()[0] == 1
    assert writer.conn.execute("SELECT settler FROM settlement_updates").fetchone()[0] == "yank-controller"
    assert escrow.settle_on_close(writer, attempt.attempt_id, "SKILL_YANKED") is None
    assert escrow.reservation(writer, attempt.attempt_id) == reservation
    assert writer.serve(attempt.recipe_key) is None
    with pytest.raises(yank.DisownedTicket, match="is no ticket"):
        yank.offer_as_ticket(writer, attempt.attempt_id)
    if ignore_term:
        assert attempt.launch.exit_status == -signal.SIGKILL
        assert attempt.output_manifest_hash is None
    else:
        assert attempt.launch.exit_status == 0 and attempt.parsed.status == "OK"
        assert (tmp_path / "runs" / attempt.attempt_id / "scratch" / "sigterm_seen").read_text() == "term"


def test_yank_propagation_owns_settlement_even_when_the_runner_closes_first(writer, tmp_path):
    attempt = _inflight(writer, tmp_path, pause_settlement=True)
    assert attempt.status == "SKILL_YANKED"
    updates = writer.conn.execute("SELECT attempt_id, settler FROM settlement_updates").fetchall()
    assert [tuple(row) for row in updates] == [(attempt.attempt_id, "yank-controller")]
    assert escrow.reservation(writer, attempt.attempt_id)["released_by"] == "disowned"


def test_a_receipt_write_failure_honors_the_yank_and_its_settlement_owner(writer, tmp_path):
    writer.conn.executescript(
        "CREATE TRIGGER reject_receipt BEFORE INSERT ON receipts BEGIN SELECT RAISE(ABORT, 'receipt rejected'); END;"
    )
    with pytest.raises(sqlite3.IntegrityError, match="receipt rejected"):
        _inflight(writer, tmp_path, pause_settlement=True)
    row = dict(writer.conn.execute("SELECT * FROM attempts").fetchone())
    assert row["status"] == "SKILL_YANKED" and row["ended_at"] is not None
    assert row["receipt_hash"] is None
    updates = writer.conn.execute("SELECT attempt_id, settler FROM settlement_updates").fetchall()
    assert [tuple(update) for update in updates] == [(row["attempt_id"], "yank-controller")]
    assert escrow.reservation(writer, row["attempt_id"])["released_by"] == "disowned"


def test_a_skill_yanked_status_alone_is_neither_cacheable_nor_a_ticket(writer):
    key = writer.put_recipe(helpers.recipe())
    attempt_id, _ = helpers.launch(writer, key, status="SKILL_YANKED", payloads={"out": b"result"})
    assert writer.get_attempt(attempt_id)["disowned_at"] is None
    assert writer.serve(key) is None
    with pytest.raises(yank.YankError, match="only an OK attempt is a ticket"):
        yank.offer_as_ticket(writer, attempt_id)


@pytest.mark.parametrize("candidate", ["OK", "FAIL", "BUDGET_EXCEEDED", "BLOCKED"])
def test_the_final_close_honors_a_yank_committed_after_the_wait_loop(writer, candidate):
    key = writer.put_recipe(helpers.recipe())
    attempt_id = writer.start_attempt(key)
    _record(writer)
    status = writer.close_attempt(attempt_id, candidate, honor_yank=True)
    assert status == writer.get_attempt(attempt_id)["status"] == "SKILL_YANKED"


def test_a_yank_outside_the_recipe_reach_leaves_the_running_attempt_ok(writer, tmp_path):
    attempt = _inflight(writer, tmp_path, outside=True)
    assert attempt.status == "OK"
    assert not attempt.launch.skill_yanked and not attempt.launch.timed_out
    assert writer.get_attempt(attempt.attempt_id)["disowned_at"] is None
    assert escrow.standing(writer, attempt.attempt_id)
    assert writer.serve(attempt.recipe_key).attempt_id == attempt.attempt_id
    assert yank.offer_as_ticket(writer, attempt.attempt_id)["status"] == "OK"


def test_a_yank_after_completion_disowns_without_rewriting_the_finished_status(writer, tmp_path):
    attempt = _launch(writer, tmp_path, finish=True)
    assert attempt.status == "OK"
    before = writer.get_attempt(attempt.attempt_id)
    assert writer.serve(attempt.recipe_key).attempt_id == attempt.attempt_id
    _record(writer)
    after = writer.get_attempt(attempt.attempt_id)
    assert after["disowned_at"] is not None
    assert {k: v for k, v in after.items() if k != "disowned_at"} == {
        k: v for k, v in before.items() if k != "disowned_at"
    }
    assert writer.serve(attempt.recipe_key) is None
    assert escrow.reservation(writer, attempt.attempt_id)["released_by"] == "disowned"
    assert writer.conn.execute("SELECT COUNT(*) FROM settlement_updates").fetchone()[0] == 1
