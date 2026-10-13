import json
import logging
import re
import sqlite3

import pytest

from cairn import attest, bundle, claims, dispatch, hunt, instances, ladder, report, substrate

HEADINGS = [
    "Claim",
    "Hypothesis key",
    "Pre-registration",
    "Hunt record",
    "Skeptic record",
    "Calibration tag",
    "Ledger entry",
    "Tier spend",
    "Limitations",
]


@pytest.fixture(autouse=True)
def isolated_log_handlers(monkeypatch):
    monkeypatch.setattr(logging.getLogger("cairn"), "handlers", [])


def build_records(path, *, status="open", entropy_first=False, tagged=False):
    with substrate.Substrate.open(path) as sub:
        statement = claims.ClaimStatement(
            "report-claim",
            1,
            "Claim text\n## forged heading",
            {"target_family": "fixture", "size_interval": [1, 2], "param_ranges": {"n": [1, 2]}, "assumption_set": []},
            {"units": {}, "cost_model": None},
        )
        claims.write_claim_statement(sub, statement)
        if status != "open":
            claims.transition_status(sub, statement.hash, status)
        distribution = hunt.Distribution({"n": (1, 2)})
        method = {"interface_version": "counterexample_hunt/1", "params": {}}
        hypothesis = claims.HypothesisObject(
            "fixture", {"claim": "fixture"}, method, {"n": [1, 2]}, distribution.hash, statement.hash
        )
        if entropy_first:
            _, nonce = ladder.commit_entropy(sub, hypothesis_hash=hypothesis.hash, run_id="fixture-run")
        claims.write_hypothesis_object(sub, hypothesis)
        plan = hunt.HuntPlan(
            statement.hash,
            hypothesis.hash,
            distribution,
            1,
            {"n": (1, 2)},
            target_family="fixture",
            executor_identity="e" * 64,
            verifier_identity="f" * 64,
        )
        hunt._store_plan(sub, plan)
        if not entropy_first:
            nonce = instances.draw_nonce(sub, hypothesis.hash, "fixture-run")
        record = hunt.HuntRecord(
            plan.hash,
            distribution.hash,
            statement.hash,
            hypothesis.hash,
            nonce.nonce,
            1,
            0,
            "PARTIAL",
            "INCOMPLETE",
            None,
            False,
            (),
        )
        sub.put_node("hunt_run", hunt.run_canonical(record))
        evidence = claims.EvidenceNode(
            "counterexample_hunt_record",
            statement.hash,
            dict(statement.scope),
            frozenset(),
            "gate:hunt",
            "gate",
            verdict="INCOMPLETE",
        )
        claims.write_evidence_node(sub, evidence)
        sub.add_lineage(evidence.hash, record.hash, "input")
        if tagged:
            claims.append_tag_history(
                sub, statement.hash, None, "SPECULATION", evidence.hash, "recorded initial tag", "fixture"
            )
            claims.append_tag_history(
                sub, statement.hash, "SPECULATION", "CONJECTURE", evidence.hash, "recorded second tag", "fixture"
            )
    return statement, hypothesis, evidence


def add_skeptic(path, statement_hash, *, role="skeptic", result_present=True, status="success", text=None):
    source = path.parent / "skeptic-fixture"
    source.mkdir()
    config = {
        "template": dispatch.SKEPTIC_HUNT_TEMPLATE,
        "tools": [],
        "model": "claude-offline-fixture",
        "max_turns": 1,
        "timeout_s": 1,
    }
    (source / "worker_roles.json").write_text(json.dumps({role: config}))
    (source / "role_templates.json").write_text(json.dumps({dispatch.SKEPTIC_HUNT_TEMPLATE: "1. Offline fixture"}))
    bundle_path, pin = path.parent / "skeptic-bundle.sqlite", path.parent / "skeptic-bundle.pin"
    pin.write_text(bundle.build(source, bundle_path) + "\n")
    gate = bundle.GateBundle.open(bundle_path, pin)
    with substrate.Substrate.open(path) as sub:
        sent = dispatch._record(sub, dispatch._prepare(sub, gate, role=role, node_ids=(statement_hash,)))
        if result_present:
            response = {
                "statement_hash": statement_hash,
                "verdict": "gap",
                "items": [
                    {"id": 1, "outcome": "gap", "answer": "Recorded review\n## forged heading", "cited_node_hashes": []}
                ],
            }
            result = dispatch.DispatchResult(
                sent.dispatch_id,
                status,
                json.dumps(response) if text is None else text,
                "fixture-session",
                (),
                (),
                (),
                None,
                "2026-10-13T00:00:01Z",
            )
            dispatch._write(sub, "worker_result", "worker_results", result, (sent.hash,))
    return sent


def test_section_order_untagged_absent_and_byte_equal(tmp_path):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path)
    first = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    second = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    assert first.encode() == second.encode()
    assert re.findall(r"^## (.+)$", first, re.MULTILINE) == HEADINGS
    assert "latest tag: untagged" in first
    assert "## Skeptic record\n\nabsent\n" in first
    assert first.count("entropy commitment: none recorded") == 2
    assert "uncertified producer" in first
    assert "AuditOnly" in first
    assert "covered population:" in first


def test_every_assertion_line_has_statement_tag_and_evidence(tmp_path):
    path = tmp_path / "report.sqlite"
    statement, _, evidence = build_records(path, tagged=True)
    text = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    assertions = [line for line in text.splitlines() if line and not line.startswith("## ") and line != "absent"]
    brackets = re.findall(r"\[statement=[0-9a-f]{12} tag=\S+ evidence=[0-9a-f]{12}\]$", text, re.MULTILINE)
    assert len(brackets) == len(assertions)
    assert all(f"statement={statement.hash[:12]}" in line for line in assertions)
    calibration = text.split("## Calibration tag\n\n")[1].split("\n\n## Ledger entry")[0]
    assert "latest tag: CONJECTURE" in calibration
    assert "history seq: 1; from: None; to: SPECULATION" in calibration
    assert "history seq: 2; from: SPECULATION; to: CONJECTURE" in calibration
    assert f"evidence pointer: {evidence.hash}" in calibration
    assert "Claim text ## forged heading" in text


def test_statement_free_formatter_emits_prose():
    assert report.assertion_line("A prose sentence", None, "PROVEN", "e" * 64) == "A prose sentence"


@pytest.mark.parametrize("status", ["refuted", "withdrawn"])
def test_terminal_status_and_campaign_skeptic(tmp_path, status):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path, status=status)
    sent = add_skeptic(path, statement.hash)
    text = report.document(db_path=path, kind="campaign", statement_hash=statement.hash)
    assert text.startswith(f"## Claim\n\nstatus: {status};")
    assert sent.dispatch_id in text
    assert "Recorded review\\n## forged heading" in text
    assert re.findall(r"^## (.+)$", text, re.MULTILINE) == HEADINGS


@pytest.mark.parametrize("result_present", [True, False])
def test_failed_or_pending_skeptic_stays_visible_but_cannot_complete_campaign(tmp_path, result_present):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path, status="withdrawn")
    sent = add_skeptic(path, statement.hash, status="error", text="TimeoutError", result_present=result_present)
    text = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    assert sent.dispatch_id in text
    assert "TimeoutError" in text if result_present else "result: absent" in text
    assert "Completed typed Skeptic review absent" in text
    with pytest.raises(report.ReportRefused, match="missing skeptic_record"):
        report.document(db_path=path, kind="campaign", statement_hash=statement.hash)


def test_malformed_success_skeptic_refuses_campaign(tmp_path, capsys):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path, status="withdrawn")
    add_skeptic(path, statement.hash, text="not JSON")
    code = report.main(["--db", str(path), "--kind", "campaign", "--statement", statement.hash])
    captured = capsys.readouterr()
    assert code == 2 and captured.out == ""
    assert "malformed skeptic_record" in captured.err


@pytest.mark.parametrize("skeptic_case", ["absent", "dispatch_only", "wrong_role"])
def test_campaign_missing_skeptic_cli_refuses(tmp_path, capsys, skeptic_case):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path, status="withdrawn")
    if skeptic_case == "dispatch_only":
        add_skeptic(path, statement.hash, result_present=False)
    elif skeptic_case == "wrong_role":
        add_skeptic(path, statement.hash, role="prover")
    code = report.main(["--db", str(path), "--kind", "campaign", "--statement", statement.hash])
    captured = capsys.readouterr()
    assert (code, captured.out, captured.err) == (2, "", "refused: missing skeptic_record\n")


def test_campaign_open_statement_refuses(tmp_path, capsys):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path)
    add_skeptic(path, statement.hash)
    code = report.main(["--db", str(path), "--kind", "campaign", "--statement", statement.hash])
    captured = capsys.readouterr()
    assert (code, captured.out, captured.err) == (2, "", "refused: statement not terminal\n")


def test_unknown_statement_cli_refuses(tmp_path, capsys):
    path = tmp_path / "report.sqlite"
    build_records(path)
    code = report.main(["--db", str(path), "--kind", "run", "--statement", "0" * 64])
    captured = capsys.readouterr()
    assert (code, captured.out, captured.err) == (2, "", "refused: unknown statement\n")


def test_missing_statement_row_with_existing_records_cli_refuses(tmp_path, capsys):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path)
    copied = tmp_path / "missing-statement.sqlite"
    with sqlite3.connect(path) as source, sqlite3.connect(copied) as destination:
        source.backup(destination)
    with sqlite3.connect(copied) as conn:
        conn.execute("DROP TRIGGER claim_statements_no_delete")
        conn.execute("DELETE FROM claim_statements WHERE hash = ?", (statement.hash,))
        conn.executescript(substrate.SCHEMA_PATH.read_text())
    code = report.main(["--db", str(copied), "--kind", "run", "--statement", statement.hash])
    captured = capsys.readouterr()
    assert (code, captured.out, captured.err) == (2, "", "refused: unknown statement\n")


def test_hypothesis_after_entropy_refuses(tmp_path, capsys):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path, entropy_first=True)
    code = report.main(["--db", str(path), "--kind", "run", "--statement", statement.hash])
    captured = capsys.readouterr()
    assert (code, captured.out, captured.err) == (2, "", "refused: hypothesis after entropy\n")


@pytest.mark.parametrize("selectors", [[], ["--statement", "a", "--ladder-table", "b"]])
def test_selector_refusal_has_empty_stdout(tmp_path, capsys, selectors):
    code = report.main(["--db", str(tmp_path / "absent.sqlite"), "--kind", "run", *selectors])
    captured = capsys.readouterr()
    assert code == 2
    assert captured.out == ""
    assert captured.err.startswith("refused: ")
    assert not (tmp_path / "absent.sqlite").exists()


def test_attestation_verification_only_changes_report_observation(tmp_path):
    path = tmp_path / "report.sqlite"
    statement, _, _ = build_records(path)
    attestation = tmp_path / "attest.log"
    review = claims.ReviewVerdict(
        statement.hash, "reviewer", "approve", "a" * 64, "b" * 64, "2026-10-13T00:00:00Z", file_offset=0
    )
    attest.append_record(attestation, claims.review_verdict_canonical(review))
    with substrate.Substrate.open(path) as sub:
        claims.write_review_verdict(sub, review)
    unverified = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    verified = report.document(db_path=path, kind="run", statement_hash=statement.hash, attest_path=attestation)
    assert "verifies: false" in unverified
    assert "verifies: true" in verified
    assert "latest tag: untagged" in verified
