import hashlib
import re
import sqlite3
from contextlib import closing

import pytest
from test_counterexample_hunt import _setup

from cairn import claims, hunt, report, repro


def _store_snapshot(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        tables = sorted(row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'"))
        rows = {table: sorted(conn.execute(f'SELECT * FROM "{table}"').fetchall(), key=repr) for table in tables}
    finally:
        conn.close()
    return hashlib.sha256(path.read_bytes()).hexdigest(), rows


def _read_only_report(path, statement_hash, evidence_hash):
    before = _store_snapshot(path)
    text = report.document(db_path=path, kind="run", statement_hash=statement_hash)
    assert report.document(db_path=path, kind="run", statement_hash=statement_hash) == text
    assert _store_snapshot(path) == before
    assertions = [line for line in text.splitlines() if line and not line.startswith("## ") and line != "absent"]
    assert all(re.search(r"\[statement=[0-9a-f]{12} tag=\S+ evidence=[0-9a-f]{12}\]$", line) for line in assertions)
    assert f"evidence={evidence_hash[:12]}" in text
    return text


@pytest.mark.parametrize("mutation", [None, "disown", "mark_inadmissible"])
def test_killed_report_separates_owner_rule_recorded_verification_and_live_admissibility(tmp_path, mutation):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(40, 40), trials=2, certified=True)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "KILLED"
        assert repro.owner_grade(
            sub, plan.executor_identity, repro.Verifier(repro.SKILL_VERIFIER, plan.verifier_identity)
        ) == (
            repro.VERIFIABLE,
            "certified-independent-verifier-with-must-fail-witness",
        )
        assert sub.get_node(result.evidence_hash)["replay_grade"] == repro.REPLAYABLE
        history = claims.tag_history_for(sub, statement.hash)
        if mutation is not None:
            getattr(sub, mutation)(result.record.trials[result.record.counterexample_trial].verifier_attempt_id)
        assert claims.tag_history_for(sub, statement.hash) == history
        assert claims.get_claim_statement(sub, statement.hash)["status"] == "refuted"
    finally:
        sub.close()
    text = _read_only_report(tmp_path / "substrate.sqlite", statement.hash, result.evidence_hash)
    assert "stored evidence replay grade: Replayable" in text
    assert "recorded statement survival standing: false" in text
    assert (
        "computed verifier owner rule: Verifiable; reason: certified-independent-verifier-with-must-fail-witness"
        in text
    )
    assert "counterexample trial: 0; verifier status: OK" in text
    assert f"live required hunt attempts admissible: {str(mutation is None).lower()}" in text
    assert "status: refuted" in text and "## Ledger entry\n\nREFUTED:" in text


@pytest.mark.parametrize(
    ("bounds", "certified", "verdict", "standing", "verifier_status", "mutation"),
    [
        ((0, 3), True, "SURVIVED", "true", "NOT_REQUIRED", None),
        ((0, 3), True, "SURVIVED", "true", "NOT_REQUIRED", "disown"),
        ((40, 40), False, "INCOMPLETE", "false", "verifier-uncertified", None),
    ],
)
def test_report_without_killed_witness_does_not_turn_certification_into_verification(
    tmp_path, bounds, certified, verdict, standing, verifier_status, mutation
):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=bounds, trials=2, certified=certified)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == verdict
        assert sub.certified(plan.verifier_identity) is certified
        if mutation is not None:
            getattr(sub, mutation)(result.record.trials[0].attempt_id)
    finally:
        sub.close()
    text = _read_only_report(tmp_path / "substrate.sqlite", statement.hash, result.evidence_hash)
    assert f"recorded statement survival standing: {standing}" in text
    assert "computed verifier owner rule: not evaluated; no KILLED witness" in text
    assert "computed verifier owner rule: Verifiable" not in text
    assert f"verifier status: {verifier_status}" in text
    if verdict == "SURVIVED":
        assert f"live required hunt attempts admissible: {str(mutation is None).lower()}" in text
        assert "CONJECTURE ceiling and is not a proof" in text
    else:
        assert "live required hunt attempts admissible: false" in text
        assert "outcome: VERIFIER_UNVERIFIED" in text


def test_legacy_killed_report_with_missing_must_fail_count_marks_owner_rule_unavailable(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(40, 40), trials=2, certified=True)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "KILLED"
    finally:
        sub.close()
    path = tmp_path / "substrate.sqlite"
    with closing(sqlite3.connect(f"file:{path}?mode=ro", uri=True)) as conn:
        statements = list(conn.iterdump())
    certificate = next(
        sql
        for sql in statements
        if sql.startswith('INSERT INTO "skill_certificates"') and plan.verifier_identity in sql
    )
    assert certificate.count('"must_fail_witnesses":1,') == 1
    statements[statements.index(certificate)] = certificate.replace('"must_fail_witnesses":1,', "", 1)
    legacy_path = tmp_path / "legacy.sqlite"
    with closing(sqlite3.connect(legacy_path)) as conn:
        conn.executescript("\n".join(statements))
    text = _read_only_report(legacy_path, statement.hash, result.evidence_hash)
    assert "computed verifier owner rule: unavailable; reason:" in text
    assert "carries no must_fail_witnesses count; re-certify the verifier before grading a witness" in text
    assert "computed verifier owner rule: Verifiable" not in text
    assert "computed verifier owner rule: AuditOnly" not in text
    assert "certificate: recorded" in text
    assert "stored evidence replay grade: Replayable" in text
    assert "recorded statement survival standing: false" in text
    assert "counterexample trial: 0; verifier status: OK" in text
