import json
from pathlib import Path

import pytest
from _skeptic_fixture import add_skeptic
from test_small_numbers_floor_hunt import _setup

from cairn import attest, claims, cli, exits, human_authority, hunt, report, substrate, withdrawal

GATE_HASH = "a1" * 32
AT = "2026-10-19T20:00:00Z"


def _survived(tmp_path, *, mode="normal"):
    (tmp_path / "campaign").mkdir()
    sub, plan, _, adapter, statement = _setup(tmp_path / "campaign", mode=mode)
    try:
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier)
    finally:
        sub.close()
    return tmp_path / "campaign" / "substrate.sqlite", statement, result


def _attestations(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "d4" * 32)
    return path


def _fields(statement, result, sent, *, reason="survived every declared trial; not promoted"):
    return {
        "statement_hash": statement.hash,
        "hunt_run_hash": result.run_hash,
        "skeptic_dispatch_id": sent.dispatch_id,
        "reason": reason,
        "issued_by": "operator-1",
        "at": AT,
    }


def _tags(sub, statement_hash):
    return sub.conn.execute(
        "SELECT * FROM tag_history WHERE statement_hash = ? ORDER BY rowid", (statement_hash,)
    ).fetchall()


def test_a_survived_campaign_with_a_skeptic_record_is_withdrawn_without_moving_a_tag(tmp_path, clear_flags):
    database, statement, result = _survived(tmp_path)
    assert result.record.verdict == "SURVIVED"
    sent = add_skeptic(database, statement.hash)
    attestations = _attestations(tmp_path, clear_flags)
    with substrate.Substrate.open(database) as sub:
        before = [tuple(row) for row in _tags(sub, statement.hash)]
        row = withdrawal.withdraw(sub, attestations, _fields(statement, result, sent), gate_bundle_hash=GATE_HASH)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "withdrawn"
        assert [tuple(row) for row in _tags(sub, statement.hash)] == before
        visible = human_authority.visible_records(sub, human_authority.STATEMENT_WITHDRAWAL, attestations)
        assert [record["record_digest"] for record in visible] == [row["record_digest"]]
    text = report.document(db_path=database, kind="campaign", statement_hash=statement.hash)
    assert "status: withdrawn" in text
    assert "withdrawal reason: survived every declared trial; not promoted" in text


def _append(database, bundle_path, pin_path, attestations, record_path):
    return cli.main(
        [
            "--db",
            str(database),
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
            "--attest",
            str(attestations),
            "attest",
            "append",
            "--kind",
            human_authority.STATEMENT_WITHDRAWAL,
            "--record",
            str(record_path),
            "--json",
        ]
    )


def test_attest_append_withdraws_through_the_cli_and_refuses_a_bad_record(pinned_bundle, tmp_path, clear_flags, capsys):
    bundle_path, pin_path = pinned_bundle()
    database, statement, result = _survived(tmp_path)
    sent = add_skeptic(database, statement.hash)
    attestations = _attestations(tmp_path, clear_flags)
    record_path = tmp_path / "withdrawal.json"
    record_path.write_text(json.dumps(_fields(statement, result, sent) | {"hunt_run_hash": "e5" * 32}))
    assert _append(database, bundle_path, pin_path, attestations, record_path) == exits.GATE_REFUSED
    assert "withdrawal must conclude a SURVIVED hunt of this statement" in capsys.readouterr().err
    with substrate.Substrate.open(database, role="reader") as sub:
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "open"
    record_path.write_text(json.dumps(_fields(statement, result, sent)))
    assert _append(database, bundle_path, pin_path, attestations, record_path) == 0
    assert json.loads(capsys.readouterr().out)["kind"] == human_authority.STATEMENT_WITHDRAWAL
    with substrate.Substrate.open(database, role="reader") as sub:
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "withdrawn"


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("blank_reason", "reason must not be blank"),
        ("no_skeptic", "missing skeptic_record"),
        ("incomplete_hunt", "withdrawal must conclude a SURVIVED hunt of this statement"),
        ("foreign_hunt", "withdrawal must conclude a SURVIVED hunt of this statement"),
        ("not_open", "statement is not open"),
    ],
)
def test_a_withdrawal_that_fails_a_precondition_refuses_and_writes_nothing(tmp_path, clear_flags, case, message):
    mode = "fail" if case == "incomplete_hunt" else "normal"
    database, statement, result = _survived(tmp_path, mode=mode)
    sent = add_skeptic(database, statement.hash, role="skeptic" if case != "no_skeptic" else "prover")
    attestations = _attestations(tmp_path, clear_flags)
    fields = _fields(statement, result, sent, reason="   " if case == "blank_reason" else "fixture")
    if case == "foreign_hunt":
        fields["hunt_run_hash"] = "e5" * 32
    log_before = Path(attestations).read_bytes()
    with substrate.Substrate.open(database) as sub:
        if case == "not_open":
            claims.transition_status(sub, statement.hash, "refuted")
        with pytest.raises(withdrawal.WithdrawalRefused, match=message):
            withdrawal.withdraw(sub, attestations, fields, gate_bundle_hash=GATE_HASH)
        expected = "refuted" if case == "not_open" else "open"
        assert claims.get_claim_statement(sub, statement.hash)["status"] == expected
        assert human_authority.visible_records(sub, human_authority.STATEMENT_WITHDRAWAL, attestations) == []
    assert Path(attestations).read_bytes() == log_before


def test_a_malformed_skeptic_reply_on_the_statement_refuses_withdrawal(tmp_path, clear_flags):
    database, statement, result = _survived(tmp_path)
    add_skeptic(database, statement.hash, text="not JSON", name="malformed")
    sent = add_skeptic(database, statement.hash, name="valid")
    attestations = _attestations(tmp_path, clear_flags)
    with substrate.Substrate.open(database) as sub:
        with pytest.raises(withdrawal.WithdrawalRefused, match="malformed skeptic_record"):
            withdrawal.withdraw(sub, attestations, _fields(statement, result, sent), gate_bundle_hash=GATE_HASH)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "open"


def test_the_report_names_only_withdrawals_its_attestation_file_holds(tmp_path, clear_flags):
    database, statement, result = _survived(tmp_path)
    sent = add_skeptic(database, statement.hash)
    attestations = _attestations(tmp_path, clear_flags)
    fields = _fields(statement, result, sent)
    with substrate.Substrate.open(database) as sub:
        withdrawal.withdraw(sub, attestations, fields, gate_bundle_hash=GATE_HASH)
        unattested = fields | {"reason": "unattested mirror row", "issued_by": "unattested-writer"}
        human_authority.write(
            sub, human_authority.STATEMENT_WITHDRAWAL, unattested, gate_bundle_hash=GATE_HASH, file_offset=0
        )
    text = report.document(db_path=database, kind="campaign", statement_hash=statement.hash, attest_path=attestations)
    assert "withdrawal reason: survived every declared trial; not promoted" in text
    assert "unattested mirror row" not in text


def test_a_retry_after_a_failed_status_change_reuses_the_attested_withdrawal(tmp_path, clear_flags, monkeypatch):
    database, statement, result = _survived(tmp_path)
    sent = add_skeptic(database, statement.hash)
    attestations = _attestations(tmp_path, clear_flags)
    fields = _fields(statement, result, sent)
    real = claims.transition_status

    def fail_once(*args):
        monkeypatch.setattr(claims, "transition_status", real)
        raise RuntimeError("status change interrupted")

    monkeypatch.setattr(claims, "transition_status", fail_once)
    with substrate.Substrate.open(database) as sub:
        with pytest.raises(RuntimeError, match="status change interrupted"):
            withdrawal.withdraw(sub, attestations, fields, gate_bundle_hash=GATE_HASH)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "open"
        log_after_failure = Path(attestations).read_bytes()
        withdrawal.withdraw(sub, attestations, fields, gate_bundle_hash=GATE_HASH)
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "withdrawn"
        visible = human_authority.visible_records(sub, human_authority.STATEMENT_WITHDRAWAL, attestations)
        assert len(visible) == 1
    assert Path(attestations).read_bytes() == log_after_failure
