import dataclasses
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from test_counterexample_hunt import _setup
from test_ladder_table_repro import _clean_table

from cairn import claims, hunt, instances, ladderplan, laddertable, report, substrate

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
ROOT = Path(__file__).resolve().parents[2]


def _cli(path, statement_hash):
    return subprocess.run(
        [sys.executable, "-m", "cairn.report", "--db", str(path), "--kind", "run", "--statement", statement_hash],
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(("bounds", "verdict"), [((0, 3), "SURVIVED"), ((40, 40), "KILLED")])
def test_real_hunt_cli_and_three_read_only_renders(tmp_path, bounds, verdict):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=bounds, trials=2, certified=verdict == "KILLED")
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == verdict
        evidence_hash = result.evidence_hash
        receipts = sub.conn.execute("SELECT cpu_user_s, cpu_sys_s, wall_s FROM receipts ORDER BY rowid").fetchall()
        cpu_seconds = sum(
            (Decimal(str(row["cpu_user_s"])) + Decimal(str(row["cpu_sys_s"])) for row in receipts), Decimal(0)
        )
        wall_seconds = sum((Decimal(str(row["wall_s"])) for row in receipts), Decimal(0))
        history = claims.tag_history_for(sub, statement.hash)
    finally:
        sub.close()
    path = tmp_path / "substrate.sqlite"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    first = _cli(path, statement.hash)
    second = _cli(path, statement.hash)
    third = report.document(db_path=path, kind="run", statement_hash=statement.hash).encode()
    assert first.returncode == second.returncode == 0
    assert first.stderr == second.stderr == b""
    assert first.stdout == second.stdout == third
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    text = first.stdout.decode()
    assert re.findall(r"^## (.+)$", text, re.MULTILINE) == HEADINGS
    assert f"verdict: {verdict}" in text
    assert f"evidence={evidence_hash[:12]}" in text
    assert f"attempts: {len(receipts)}; CPU-seconds: {cpu_seconds}; wall-seconds: {wall_seconds}" in text
    latest = history[-1]["to_tag"] if history else "untagged"
    assert f"latest tag: {latest}" in text
    if verdict == "KILLED":
        assert "status: refuted" in text
        assert "## Ledger entry\n\nREFUTED:" in text
        assert "counterexample trial: 0; verifier status: OK" in text
    else:
        assert "CONJECTURE ceiling and is not a proof" in text
    print(json.dumps({"db": str(path), "statement": statement.hash, "stdout": text}))


def test_every_run_on_hypothesis_is_rendered_oldest_first(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(0, 3), trials=1)
    try:
        first = hunt.run_hunt(sub, plan, executor, verifier, run_id="z-first")
        second = hunt.run_hunt(sub, plan, executor, verifier, run_id="a-second")
        instances.draw_nonce(sub, plan.hypothesis_key, "unfinished-third")
    finally:
        sub.close()
    text = report.document(db_path=tmp_path / "substrate.sqlite", kind="run", statement_hash=statement.hash)
    records = text.split("## Hunt record\n\n")[1].split("\n\n## Skeptic record")[0]
    assert (
        records.index("run id: z-first") < records.index("run id: a-second") < records.index("run id: unfinished-third")
    )
    assert first.run_hash in records and second.run_hash in records
    assert "verdict: none recorded; unfinished run" in records
    assert "has a nonce but no hunt record; its outcome is unavailable" in text
    assert text.count("entropy commitment: none recorded") >= 3


def test_missing_evidence_blob_cli_refuses(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(0, 3), trials=1)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        digest = result.record.trials[0].execution_evidence
    finally:
        sub.close()
    copied = tmp_path / "missing-evidence.sqlite"
    with sqlite3.connect(tmp_path / "substrate.sqlite") as source, sqlite3.connect(copied) as destination:
        source.backup(destination)
    with sqlite3.connect(copied) as conn:
        conn.execute("DELETE FROM blobs WHERE hash = ?", (digest,))
    result = _cli(copied, statement.hash)
    assert (result.returncode, result.stdout, result.stderr) == (2, b"", b"refused: evidence missing\n")


def build_ladder(path, *, bound=True):
    plan = ladderplan.LadderPlan.load(json.loads((ROOT / "bundle" / "ladder_plan.json").read_text()))
    with substrate.Substrate.open(path) as sub:
        statement = claims.ClaimStatement(
            "ladder-report",
            1,
            "A finite measured cost",
            {
                "target_family": "toy_curve",
                "size_interval": [30, 60],
                "param_ranges": {"bits": [30, 60]},
                "assumption_set": [],
            },
            {"units": {}, "cost_model": None},
        )
        if bound:
            claims.write_claim_statement(sub, statement)
        hypothesis = claims.HypothesisObject(
            "toy_curve",
            {"cost": "fixture"},
            {"interface_version": "toy/1", "params": {}},
            {"bits": [30, 60]},
            claim_statement_hash=statement.hash if bound else None,
        )
        claims.write_hypothesis_object(sub, hypothesis)
        nonce = instances.draw_nonce(sub, hypothesis.hash, "real-nonce-ladder")
        table = dataclasses.replace(
            _clean_table(),
            run_id=nonce.run_id,
            nonce=nonce.nonce,
            hypothesis_hash=hypothesis.hash,
            uncounted_backend="gmp",
        )
        digest = laddertable.write(sub, table, plan)
    return digest, statement


@pytest.mark.parametrize("bound", [True, False])
def test_ladder_write_and_render_three_arms_predicate_and_read_only(tmp_path, bound):
    path = tmp_path / "ladder.sqlite"
    digest, statement = build_ladder(path, bound=bound)
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    text = report.document(db_path=path, kind="run", ladder_table_hash=digest)
    repeated = report.document(db_path=path, kind="run", ladder_table_hash=digest)
    assert text.encode() == repeated.encode()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert re.findall(r"^## (.+)$", text, re.MULTILINE) == [
        "Ladder table" if h == "Hunt record" else h for h in HEADINGS
    ]
    assert "verdict: INCONCLUSIVE; predicate: uncounted_backend" in text
    assert all(f"arm: {arm};" in text for arm in ladderplan.ARMS)
    assert "radius: 0.1216; band: 0.05" in text
    assert "The gate held no operation count." in text
    if bound:
        assert f"statement={statement.hash[:12]}" in text
        assert report.document(db_path=path, kind="run", statement_hash=statement.hash) == text
    else:
        assert "No claim statement is bound" in text
        assert "[statement=" not in text
