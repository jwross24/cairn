import json
import sys
from pathlib import Path

import pytest

from cairn import attest, bundle, claims, cli, exits, human_queue, substrate
from cairn.human_queue import ClosingRuleViolation, Item

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

T0 = "2026-09-02T00:00:00+00:00"
T1 = "2026-09-02T00:01:00+00:00"
AT = "2026-09-02T00:05:00Z"
BRANCH = "branch-3"
RUNG = "rung-50-2"


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def deploy(tmp_path, pinned_bundle, clear_flags):
    bundle_path, pin_path = pinned_bundle()
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "attestations.log"
    clear_flags(attest_path)
    attest.init(attest_path, gate_bundle.waiver_target())
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        statement = factories.claim_statement(seed=4)
        claims.write_claim_statement(sub, statement)
        items = {
            "review": human_queue.enqueue(
                sub, Item("statement_review", "statement", statement.hash, T0, blocker="statement_review")
            ),
            "near_dup": human_queue.enqueue(
                sub, Item("near_dup_review", "branch", BRANCH, T0, blocker="near_dup_review")
            ),
            "leaked": human_queue.enqueue(sub, Item("leaked", "statement", statement.hash, T1)),
            "clock": human_queue.enqueue_clock_inconclusive(sub, RUNG, at=T1),
            "drift": human_queue.enqueue_cost_drift(sub, BRANCH, at=T1),
        }
    return {
        "db": db,
        "attest": attest_path,
        "paths": ["--bundle", str(bundle_path), "--pin", str(pin_path), "--attest", str(attest_path), "--db", str(db)],
        "statement": statement,
        "items": items,
        "bundle_hash": gate_bundle.hash,
    }


def _rows(db, attest_path):
    with substrate.Substrate.open(db, role="reader") as sub:
        open_ids = [row["item_id"] for row in human_queue.open_items(sub, attest_path)]
        closures = [dict(r) for r in sub.conn.execute("SELECT * FROM human_queue_closures ORDER BY seq")]
        acks = [dict(r) for r in sub.conn.execute("SELECT * FROM acknowledgments ORDER BY row_id")]
    return open_ids, closures, acks


def _ack_record(tmp_path, item_id, **overrides):
    record = tmp_path / "ack.json"
    record.write_text(json.dumps({"item_id": item_id, "issued_by": "operator", "at": AT, "note": "seen", **overrides}))
    return record


def test_a_statement_review_closes_by_the_review_verdict_the_file_holds(deploy, tmp_path, capsys, db_snapshot):
    record = tmp_path / "verdict.json"
    record.write_text(
        json.dumps(
            {
                "statement_hash": deploy["statement"].hash,
                "reviewer": "operator",
                "verdict": "approve",
                "checklist_template_hash": "b" * 64,
                "at": AT,
            }
        )
    )
    code, out, _ = _run(
        ["attest", "append", "--kind", "review_verdict", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.OK
    appended = json.loads(out)
    before = _rows(deploy["db"], deploy["attest"])
    with substrate.Substrate.open(deploy["db"]) as sub:
        db_snapshot(sub.conn, "before-attestation-close")
        human_queue.close_by_attestation(
            sub,
            deploy["items"]["review"],
            attest_path=deploy["attest"],
            file_offset=appended["offset"],
            record_digest=appended["record_digest"],
            at=AT,
        )
        db_snapshot(sub.conn, "after-attestation-close")
    after = _rows(deploy["db"], deploy["attest"])
    assert deploy["items"]["review"] in before[0] and deploy["items"]["review"] not in after[0]
    assert len(after[0]) == len(before[0]) - 1
    assert [(c["path"], c["record_digest"], c["file_offset"]) for c in after[1]] == [
        ("attestation", appended["record_digest"], appended["offset"])
    ]
    print(before[1], after[1])


def test_a_blocker_clearing_closes_the_item_that_held_it(deploy):
    before = _rows(deploy["db"], deploy["attest"])
    with substrate.Substrate.open(deploy["db"]) as sub:
        canonical = attest.waiver_canonical(attest.fixture_waiver("near-dup-difference"))
        offset = attest.append_record(deploy["attest"], canonical)
        with pytest.raises(human_queue.ClosingRuleViolation, match="carries an attestation record"):
            human_queue.close_by_blocker_clear(
                sub,
                deploy["items"]["near_dup"],
                attest_path=deploy["attest"],
                cleared_by="librarian:difference-stated",
                at=AT,
            )
        human_queue.close_by_blocker_clear(
            sub,
            deploy["items"]["near_dup"],
            attest_path=deploy["attest"],
            cleared_by="librarian:difference-stated",
            record_digest=attest.blob_hash(canonical),
            file_offset=offset,
            at=AT,
        )
    after = _rows(deploy["db"], deploy["attest"])
    assert set(before[0]) - set(after[0]) == {deploy["items"]["near_dup"]}
    assert [(c["item_id"], c["path"], c["ref"]) for c in after[1]] == [
        (deploy["items"]["near_dup"], "blocker_cleared", "librarian:difference-stated")
    ]
    print(before[1], after[1])


def test_a_terminal_status_closes_a_blocker_free_item_on_the_statement_it_names(deploy):
    with substrate.Substrate.open(deploy["db"]) as sub:
        with pytest.raises(ClosingRuleViolation, match="not a terminal status"):
            human_queue.close_by_terminal_status(
                sub, deploy["items"]["leaked"], attest_path=deploy["attest"], status="x", ref="justify"
            )
        claims.transition_status(sub, deploy["statement"].hash, "withdrawn")
        human_queue.close_by_terminal_status(
            sub, deploy["items"]["leaked"], attest_path=deploy["attest"], status="x", ref="justify", at=AT
        )
    open_ids, closures, _ = _rows(deploy["db"], deploy["attest"])
    assert deploy["items"]["leaked"] not in open_ids
    assert [(c["path"], c["ref"]) for c in closures] == [("terminal_status", "withdrawn:justify")]
    print(closures)


def test_an_acknowledgment_through_the_attestation_file_closes_only_the_item_it_names(
    deploy, tmp_path, capsys, db_snapshot
):
    before = _rows(deploy["db"], deploy["attest"])
    size_before = deploy["attest"].stat().st_size
    record = _ack_record(tmp_path, deploy["items"]["clock"])
    code, out, _ = _run(
        ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.OK, out
    payload = json.loads(out)
    assert payload["kind"] == "acknowledgment" and payload["offset"] == size_before and payload["row_id"] == 1
    after = _rows(deploy["db"], deploy["attest"])
    assert set(before[0]) - set(after[0]) == {deploy["items"]["clock"]}
    assert deploy["items"]["drift"] in after[0] and deploy["items"]["leaked"] in after[0]
    assert [(a["item_id"], a["issued_by"], a["note"], a["record_digest"], a["file_offset"]) for a in after[2]] == [
        (deploy["items"]["clock"], "operator", "seen", payload["record_digest"], payload["offset"])
    ]
    assert [(c["item_id"], c["path"], c["record_digest"], c["file_offset"]) for c in after[1]] == [
        (deploy["items"]["clock"], "acknowledgment", payload["record_digest"], payload["offset"])
    ]
    assert attest.attestation_record_matches(deploy["attest"], payload["offset"], payload["record_digest"])
    with substrate.Substrate.open(deploy["db"], role="reader") as sub:
        db_snapshot(sub.conn, "acknowledged")
        assert [
            a["row_id"] for a in human_queue.visible_acknowledgments(sub, deploy["items"]["clock"], deploy["attest"])
        ] == [1]
        assert (
            sub.get_node(sub.conn.execute("SELECT hash FROM nodes WHERE kind = 'acknowledgment'").fetchone()["hash"])[
                "producer_identity"
            ]
            == "operator"
        )
    print(after)


def test_an_acknowledgment_on_a_blocker_item_is_refused_before_the_file_grows(deploy, tmp_path, capsys):
    size_before = deploy["attest"].stat().st_size
    record = _ack_record(tmp_path, deploy["items"]["near_dup"])
    code, out, err = _run(
        ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.GATE_REFUSED
    assert "holds blocker near_dup_review" in out + err
    assert deploy["attest"].stat().st_size == size_before
    open_ids, closures, acks = _rows(deploy["db"], deploy["attest"])
    assert deploy["items"]["near_dup"] in open_ids and closures == [] and acks == []


def test_an_acknowledgment_naming_no_item_or_a_closed_one_is_refused(deploy, tmp_path, capsys):
    record = _ack_record(tmp_path, "ghost")
    code, out, err = _run(
        ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.GATE_REFUSED and "no human queue item ghost" in out + err
    record = _ack_record(tmp_path, deploy["items"]["drift"])
    assert (
        _run(
            ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"],
            capsys,
        )[0]
        == exits.OK
    )
    code, out, err = _run(
        ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.GATE_REFUSED and "closed by acknowledgment" in out + err


def test_a_malformed_acknowledgment_record_is_user_input(deploy, tmp_path, capsys):
    record = tmp_path / "ack.json"
    record.write_text(json.dumps({"item_id": deploy["items"]["clock"], "issued_by": "operator"}))
    code, out, err = _run(
        ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"], capsys
    )
    assert code == exits.USER_INPUT and "missing at, note" in out + err


def test_an_acknowledgment_whose_digest_matches_no_record_leaves_the_item_open(deploy):
    ack = human_queue.acknowledgment_from(
        {"item_id": deploy["items"]["clock"], "issued_by": "operator", "at": AT, "note": "unfiled"}
    )
    with substrate.Substrate.open(deploy["db"]) as sub:
        with pytest.raises(ClosingRuleViolation, match="holds no acknowledgment at offset 0"):
            human_queue.write_acknowledgment(sub, ack, attest_path=deploy["attest"], file_offset=0)
        digest = human_queue.acknowledgment_digest(ack)
        sub.conn.execute(
            "INSERT INTO acknowledgments (item_id, issued_by, at, note, record_digest, file_offset) VALUES (?, 'operator', ?, 'unfiled', ?, 4096)",
            (deploy["items"]["clock"], AT, digest),
        )
        sub.conn.execute(
            "INSERT INTO human_queue_closures (item_id, path, ref, record_digest, file_offset, closed_at) VALUES (?, 'acknowledgment', ?, ?, 4096, ?)",
            (deploy["items"]["clock"], digest, digest, AT),
        )
        assert human_queue.visible_acknowledgments(sub, deploy["items"]["clock"], deploy["attest"]) == []
        assert human_queue.visible_closure(sub, deploy["items"]["clock"], deploy["attest"]) is None
    open_ids, _, _ = _rows(deploy["db"], deploy["attest"])
    assert deploy["items"]["clock"] in open_ids


@pytest.mark.parametrize(
    ("mutate", "still_closed"),
    [
        (lambda data: data + b"\x00", True),
        (lambda data: data[:-1], False),
        (lambda data: data[:-1] + bytes([data[-1] ^ 1]), False),
    ],
)
def test_a_human_path_closure_is_visible_only_while_the_file_holds_its_bytes(
    deploy, tmp_path, capsys, clear_flags, mutate, still_closed
):
    record = _ack_record(tmp_path, deploy["items"]["clock"])
    assert (
        _run(
            ["attest", "append", "--kind", "acknowledgment", "--record", str(record), *deploy["paths"], "--json"],
            capsys,
        )[0]
        == exits.OK
    )
    assert deploy["items"]["clock"] not in _rows(deploy["db"], deploy["attest"])[0]
    data = deploy["attest"].read_bytes()
    clear_flags(deploy["attest"])
    import os

    os.chflags(deploy["attest"], 0)
    deploy["attest"].write_bytes(mutate(data))
    assert (deploy["items"]["clock"] not in _rows(deploy["db"], deploy["attest"])[0]) is still_closed
