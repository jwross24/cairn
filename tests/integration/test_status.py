import json
import shutil
import sqlite3
import sys
import time
from pathlib import Path

import pytest

from cairn import attest, bundle, claims, cli, exits, human_queue, substrate, yank
from cairn.human_queue import Item

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import ENV_MANIFEST_HASH, IDENTITY_A, TRANSCRIPT_HASH

AT = "2026-09-28T12:00:00Z"


def _status(argv, capsys):
    started = time.perf_counter()
    code = cli.main(argv)
    elapsed = time.perf_counter() - started
    out, err = capsys.readouterr()
    return code, out, err, elapsed


def _fixture(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    db_path = tmp_path / "substrate.sqlite"
    attest_path = tmp_path / "attestations.log"
    attest.init(attest_path, gate.waiver_target())
    statement = factories.claim_statement(seed=11)
    second_statement = factories.claim_statement(seed=12)
    current_run = factories.gate_run(
        gate="gate_plan",
        plan_step="canon_kat",
        bundle_hash=gate.hash,
        pin_hash=gate.hash,
        result="pass",
        reasons=(),
        at="2026-09-28T11:00:00Z",
        seed=21,
    )
    unrelated_run = factories.gate_run(
        gate="gate_plan",
        plan_step="canon_kat",
        bundle_hash="0" * 64,
        pin_hash="1" * 64,
        result="fail",
        reasons=("other-bundle",),
        at="2026-09-28T13:00:00Z",
        seed=22,
    )
    with substrate.Substrate.open(db_path) as sub:
        identity_certified = sub.put_identity_bundle(IDENTITY_A)
        sub.put_certificate(identity_certified, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, {"pass": 1})
        identity_uncertified = sub.put_identity_bundle(
            {**IDENTITY_A, "interface_version": "rho_dp/1", "implementation_revision": "bb" * 32}
        )
        identity_yanked = sub.put_identity_bundle({**IDENTITY_A, "implementation_revision": "cc" * 32})
        sub.put_certificate(identity_yanked, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, {"pass": 1})
        claims.write_claim_statement(sub, statement)
        claims.append_tag_history(
            sub,
            statement.hash,
            None,
            "CONJECTURE",
            None,
            "tagged fixture claim",
            "test",
            at=AT,
        )
        claims.write_claim_statement(sub, second_statement)
        claims.write_gate_run(sub, current_run)
        claims.write_gate_run(sub, unrelated_run)
        for index, step in enumerate(gate.gate_plan["steps"]):
            if step["step"] == "canon_kat":
                continue
            claims.write_gate_run(
                sub,
                factories.gate_run(
                    gate="gate_plan",
                    plan_step=step["step"],
                    bundle_hash=gate.hash,
                    pin_hash=gate.hash,
                    result="pass",
                    reasons=(),
                    at=f"2026-09-28T10:{index:02d}:00Z",
                    seed=30 + index,
                ),
            )
        latest_plan_run = factories.gate_run(
            gate="gate_plan",
            plan_step="canon_kat",
            bundle_hash=gate.hash,
            pin_hash=gate.hash,
            result="refused",
            reasons=("append-order",),
            at="2026-09-28T09:00:00Z",
            seed=80,
        )
        claims.write_gate_run(sub, latest_plan_run)
        sub.add_yank_record(
            "yank-cc",
            identity_yanked,
            yank.reach_json(yank.default_reach(identity_yanked)),
            kind="gate_verdict",
            verdict_ref=current_run.hash,
            created_at=AT,
        )
        human_queue.enqueue(
            sub,
            Item("leaked", "statement", statement.hash, AT),
        )
    return {
        "bundle_path": bundle_path,
        "pin_path": pin_path,
        "db_path": db_path,
        "attest_path": attest_path,
        "gate": gate,
        "statement": statement,
        "identity_certified": identity_certified,
        "identity_uncertified": identity_uncertified,
        "identity_yanked": identity_yanked,
        "unrelated_run": unrelated_run,
        "latest_plan_run": latest_plan_run,
    }


def _argv(data, *tail):
    return [
        "--db",
        str(data["db_path"]),
        "--bundle",
        str(data["bundle_path"]),
        "--pin",
        str(data["pin_path"]),
        "--attest",
        str(data["attest_path"]),
        "status",
        *tail,
    ]


def _store_snapshot(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = sorted(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        rows = []
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            contents = sorted((tuple(row) for row in conn.execute(f"SELECT * FROM {quoted}")), key=repr)
            rows.append((table, tuple(contents)))
    finally:
        conn.close()
    return Path(path).read_bytes(), tuple(rows)


def _assert_store_unchanged(path, before):
    assert Path(path).read_bytes() == before[0], "main database file bytes changed"
    assert _store_snapshot(path)[1] == before[1], "logical database rows changed"


def test_status_golden_is_fast_and_leaves_main_store_and_rows_unchanged(
    tmp_path, pinned_bundle, capsys, scrub, assert_golden
):
    data = _fixture(tmp_path, pinned_bundle)
    before_store = _store_snapshot(data["db_path"])

    code, out, err, elapsed = _status(_argv(data, "--json", "--limit", "10"), capsys)

    assert code == exits.OK, err
    assert elapsed < 2
    _assert_store_unchanged(data["db_path"], before_store)
    document = json.loads(out)
    assert document["command"] == "status"
    assert document["bundle"]["pin_match"] is True
    assert {revision["status"] for revision in document["skills"]["revisions"]} == {
        "certified",
        "uncertified",
        "yanked",
    }
    plan_steps = document["gate_plan"]["steps"]
    assert len(plan_steps) == len(data["gate"].gate_plan["steps"])
    latest = next(step for step in plan_steps if step["step"] == "canon_kat")["latest_verdict"]
    assert latest["run_id"] == data["latest_plan_run"].hash
    assert latest["result"] == "refused"
    assert latest["reasons"] == ["append-order"]
    assert document["gate_runs"]["runs"][0]["run_id"] == data["latest_plan_run"].hash
    assert any(run["run_id"] == data["unrelated_run"].hash for run in document["gate_runs"]["runs"])
    assert document["claims"]["total"] == 2
    assert document["claims"]["by_calibration"]["CONJECTURE"] == 1
    assert document["claims"]["by_calibration"]["untagged"] == 1
    assert document["human_queue"]["depth"] == 1
    assert document["tiers"]["remaining_budget"] == {"state": "absent", "reason": "supplied per launch"}
    assert document["claims"]["by_calibration"].get("SPECULATION", 0) == 0
    assert document["requires_input"] == [
        {"command": "cairn justify", "arguments": ["--statement"], "reason": "a claim statement hash is required"}
    ]
    assert {tuple(row["argv"][:2]) for row in document["affordances"]} >= {
        ("cairn", "capabilities"),
        ("cairn", "status"),
        ("cairn", "bundle"),
    }
    assert_golden("status", scrub(out, bundle_hash=data["gate"].hash, pin_hash=data["gate"].hash))


def test_status_reads_committed_rows_from_a_live_wal(tmp_path, pinned_bundle, capsys):
    data = _fixture(tmp_path, pinned_bundle)
    with substrate.Substrate.open(data["db_path"]) as writer:
        wal_run = factories.gate_run(
            gate="tier_gate",
            result="refused",
            reasons=("wal-visible",),
            at="2026-09-28T08:00:00Z",
            seed=91,
        )
        claims.write_gate_run(writer, wal_run)
        before_store = _store_snapshot(data["db_path"])

        code, out, err, elapsed = _status(_argv(data, "--json"), capsys)

        _assert_store_unchanged(data["db_path"], before_store)
    assert code == exits.OK, err
    assert elapsed < 2
    document = json.loads(out)
    assert document["gate_runs"]["runs"][0]["run_id"] == wal_run.hash


@pytest.mark.parametrize("mutation", ["logical-row", "main-file"])
def test_store_preservation_check_detects_injected_mutations(tmp_path, mutation):
    db_path = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db_path):
        pass
    before_store = _store_snapshot(db_path)
    if mutation == "logical-row":
        with substrate.Substrate.open(db_path) as sub:
            run = factories.gate_run(
                gate="tier_gate",
                result="fail",
                reasons=("injected-write",),
                at=AT,
                seed=101,
            )
            claims.write_gate_run(sub, run)
            expected_reason = "logical database rows changed"
            with pytest.raises(AssertionError, match=expected_reason):
                _assert_store_unchanged(db_path, before_store)
    else:
        main_bytes = db_path.read_bytes()
        db_path.write_bytes(main_bytes + b"mutation")
        expected_reason = "main database file bytes changed"
        with pytest.raises(AssertionError, match=expected_reason):
            _assert_store_unchanged(db_path, before_store)


def test_tampered_bundle_reports_pin_mismatch_and_real_open_refusal(tmp_path, pinned_bundle, capsys, clear_flags):
    data = _fixture(tmp_path, pinned_bundle)
    tampered = tmp_path / "tampered.sqlite"
    shutil.copy(data["bundle_path"], tampered)
    clear_flags(tampered)
    tampered.chmod(0o644)
    with sqlite3.connect(tampered) as conn:
        conn.execute("UPDATE objects SET canonical = ? WHERE kind = 'tiers'", (b"tampered",))
    data["bundle_path"] = tampered

    code, out, err, _ = _status(_argv(data, "--json"), capsys)

    assert code == exits.OK, err
    document = json.loads(out)
    assert document["bundle"]["pin_match"] is False
    show = next(row for row in document["affordances"] if row["argv"][1:3] == ["bundle", "show"])
    assert show["outcome"] == "refused"
    show_code = cli.main(["--db", str(data["db_path"]), *show["argv"][1:]])
    show_out, show_err = capsys.readouterr()
    assert show["exit_code"] == exits.GATE_REFUSED
    assert show_code == show["exit_code"]
    assert json.loads(show_out)["pin_match"] is False
    assert "fails closed" in show_err
    refusal = next(row for row in document["affordances"] if row.get("precondition"))
    assert refusal["argv"][:3] == ["cairn", "selftest", "toy-curve"]
    assert refusal["precondition"] == "GateBundle.open"
    assert refusal["exit_code"] == exits.GATE_REFUSED
    before_store = _store_snapshot(data["db_path"])
    actual_code = cli.main(refusal["argv"][1:])
    actual_err = capsys.readouterr().err
    assert actual_code == refusal["exit_code"]
    _assert_store_unchanged(data["db_path"], before_store)
    assert "fails closed" in actual_err
    assert refusal["argv"][1:3] != ["bundle", "open"]
