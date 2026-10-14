import asyncio
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
from mcp.client import Client
from test_counterexample_hunt import _setup
from test_ladder_table_repro import _clean_table

from cairn import (
    bundle,
    claims,
    dispatch,
    hunt,
    instances,
    ladderplan,
    laddertable,
    report,
    runner,
    skeptic_tools,
    substrate,
)
from cairn.profile import Evaluation

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


@pytest.mark.parametrize("blob_state", ["intact", "missing", "changed"])
def test_real_hunt_and_local_mcp_read_produce_typed_campaign_report(tmp_path, blob_state):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(40, 40), trials=1, certified=True)
    try:
        hunted = hunt.run_hunt(sub, plan, executor, verifier)
        assert hunted.verdict == "KILLED"
        read_hash = hunted.record.trials[0].verifier_evidence
        assert sub.get_node(read_hash) is None and sub.get_blob(read_hash) is not None
        source = tmp_path / "offline-skeptic-source"
        source.mkdir()
        config = {
            "template": dispatch.SKEPTIC_HUNT_TEMPLATE,
            "tools": [skeptic_tools.READ_NODE],
            "model": "claude-offline-fixture",
            "max_turns": 1,
            "timeout_s": 1,
        }
        (source / "worker_roles.json").write_text(json.dumps({"skeptic": config}))
        (source / "role_templates.json").write_text(
            json.dumps({dispatch.SKEPTIC_HUNT_TEMPLATE: "1. Offline fixture observation"})
        )
        (source / "skeptic_scope.json").write_text(json.dumps({"evidence_kinds": [hunt.KIND]}))
        bundle_path, pin = tmp_path / "offline-bundle.sqlite", tmp_path / "offline-bundle.pin"
        pin.write_text(bundle.build(source, bundle_path) + "\n")
        prepared = dispatch._prepare(
            sub, bundle.GateBundle.open(bundle_path, pin), role="skeptic", node_ids=(statement.hash,)
        )
        sent = dispatch._record(sub, prepared)
        scoped = skeptic_tools.ScopedTools(prepared.skeptic_handle, prepared.tools)

        async def read():
            async with Client(scoped.server["instance"]) as client:
                response = await client.call_tool("read_node", {"node_hash": read_hash})
                assert not response.is_error

        asyncio.run(read())
        response = {
            "statement_hash": statement.hash,
            "verdict": "gap",
            "items": [
                {
                    "id": 1,
                    "outcome": "gap",
                    "answer": "Offline fixture only; no model review",
                    "cited_node_hashes": [read_hash],
                }
            ],
        }
        finished = dispatch.DispatchResult(
            sent.dispatch_id,
            "success",
            json.dumps(response),
            "offline-fixture",
            prepared.tools,
            (),
            (),
            None,
            sent.at,
            read_node_hashes=tuple(scoped.read_node_hashes),
        )
        dispatch._write(sub, "worker_result", "worker_results", finished, (sent.hash,))
        if blob_state == "missing":
            sub.conn.execute("DELETE FROM blobs WHERE hash = ?", (read_hash,))
        elif blob_state == "changed":
            sub.conn.execute("UPDATE blobs SET bytes = ? WHERE hash = ?", (b"changed", read_hash))
        if blob_state != "intact":
            with pytest.raises(dispatch.DispatchRefused, match="observed read missing or changed"):
                dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)
            with pytest.raises(dispatch.DispatchRefused, match="observed read missing or changed"):
                report.render(sub, kind="campaign", statement_hash=statement.hash)
            return
        view = dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)
        assert view.read_node_hashes == (read_hash,)
        history = claims.tag_history_for(sub, statement.hash)
    finally:
        sub.close()
    path = tmp_path / "substrate.sqlite"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    args = [
        sys.executable,
        "-m",
        "cairn.report",
        "--db",
        str(path),
        "--kind",
        "campaign",
        "--statement",
        statement.hash,
    ]
    first = subprocess.run(args, capture_output=True, check=False)
    second = subprocess.run(args, capture_output=True, check=False)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout and first.stderr == second.stderr == b""
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
    assert b"audit observation:" in first.stdout and b'"verdict":"gap"' in first.stdout
    assert read_hash.encode() in first.stdout
    with substrate.Substrate.open(path, role="reader") as reader:
        assert claims.tag_history_for(reader, statement.hash) == history


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


@pytest.mark.parametrize("reference", ["execution_evidence", "stdout"])
def test_missing_evidence_blob_cli_refuses(tmp_path, reference):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(0, 3), trials=1)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        digest = result.record.trials[0].execution_evidence
        if reference == "stdout":
            digest = json.loads(sub.get_blob(digest))["stream_blobs"]["stdout"]
    finally:
        sub.close()
    copied = tmp_path / "missing-evidence.sqlite"
    with sqlite3.connect(tmp_path / "substrate.sqlite") as source, sqlite3.connect(copied) as destination:
        source.backup(destination)
    with sqlite3.connect(copied) as conn:
        conn.execute("DELETE FROM blobs WHERE hash = ?", (digest,))
    result = _cli(copied, statement.hash)
    assert (result.returncode, result.stdout, result.stderr) == (2, b"", b"refused: evidence missing\n")


def test_real_slope_executor_observations_match_stored_trials_and_render_read_only(tmp_path, monkeypatch):
    path = tmp_path / "slope.sqlite"
    with substrate.Substrate.open(path) as sub:
        bounds = {"t": (101, 107)}
        statement = claims.ClaimStatement(
            "slope-report",
            1,
            "A bounded slope executor observation",
            {
                "target_family": "slope",
                "size_interval": [101, 107],
                "param_ranges": {"t": [101, 107]},
                "assumption_set": [],
            },
            {"units": {}, "cost_model": None},
        )
        claims.write_claim_statement(sub, statement)
        distribution = hunt.Distribution(bounds)
        method = {"interface_version": "counterexample_hunt/1", "params": {}}
        hypothesis = claims.HypothesisObject(
            "slope", {"claim": "observations"}, method, {"t": [101, 107]}, distribution.hash, statement.hash
        )
        claims.write_hypothesis_object(sub, hypothesis)
        plan = hunt.HuntPlan(
            statement.hash,
            hypothesis.hash,
            distribution,
            2,
            bounds,
            target_family="slope",
            executor_identity="e" * 64,
            verifier_identity="f" * 64,
        )

        def executor(context):
            document = {
                "statement_hash": plan.statement_hash,
                "plan_hash": plan.hash,
                "run_id": context.run_id,
                "trial": context.trial,
                "point": dict(context.point),
                "seed": context.seed,
                "input_blob_hash": context.input_blob_hash,
                "predicate": {"kind": "weight_le", "num": 100, "den": 1},
            }
            return runner.launch(
                sub,
                "cairn.slopemodel.slope_hunt_executor",
                {
                    "skill_identity_hash": plan.executor_identity,
                    "inputs": {"hunt_input": (context.input_blob_hash, context.input_blob_size)},
                    "seed": context.seed,
                    "tool_versions": {},
                    "container_digest": "c" * 64,
                    "salt": f"hunt/{context.run_id}/{context.trial}/executor",
                },
                bundle_hash="b" * 64,
                evaluation=Evaluation(1, 1, 1),
                ceiling_multiplier=4,
                tool_digests={},
                scratch_root=tmp_path / "runs",
                skip_cache_lookup=True,
                do_not_cache=True,
                env_extra={"PYTHONPATH": str(ROOT / "src")},
                stdin_document=document,
            )

        def verifier(*args):
            pytest.fail("a surviving trial invoked the verifier")

        before_publication = []
        publish = instances.publish_nonce

        def inspect_before_publication(store, nonce, **kwargs):
            assert instances.withheld(store, nonce)
            rendered = report.render(store, kind="run", statement_hash=statement.hash)
            record = next(
                hunt.record_for(store, row["hash"])
                for row in store.conn.execute("SELECT hash FROM nodes WHERE kind = 'hunt_run'")
            )
            for trial in record.trials:
                assert str(trial.seed) not in rendered
            assert rendered.count("seed: withheld") == len(record.trials)
            assert (
                "n_rule" not in rendered and "last_index" not in rendered and "bl2012-two-grumpy-giants" not in rendered
            )
            before_publication.append(rendered)
            return publish(store, nonce, **kwargs)

        monkeypatch.setattr(instances, "publish_nonce", inspect_before_publication)
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "SURVIVED"
        assert len(before_publication) == 1
        observations = {}
        for trial in result.record.trials:
            evidence = json.loads(sub.get_blob(trial.execution_evidence))
            output = json.loads(sub.get_blob(evidence["stream_blobs"]["stdout"]))
            assert type(output["l"]) is type(output["weight"]) is int
            observations[trial.trial] = {name: output[name] for name in ("l", "weight")}
        before_rows = "\n".join(sub.conn.iterdump())
    before_bytes = path.read_bytes()
    first = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    second = report.document(db_path=path, kind="run", statement_hash=statement.hash)
    assert first == second
    assert path.read_bytes() == before_bytes
    with substrate.Substrate.open(path, role="reader") as sub:
        assert "\n".join(sub.conn.iterdump()) == before_rows
    for trial, values in observations.items():
        trial_line = next(line for line in first.splitlines() if line.startswith(f"trial: {trial};"))
        assert f"executor observations: prime: {values['l']}; weight: {values['weight']}" in trial_line
        assert f"statement={statement.hash[:12]}" in trial_line
        assert "tag=" in trial_line and "evidence=" in trial_line
    print(
        json.dumps(
            {"observations": observations, "report": first, "unpublished_report": before_publication[0]}, sort_keys=True
        )
    )


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
