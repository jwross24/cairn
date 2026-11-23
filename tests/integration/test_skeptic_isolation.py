import asyncio
import base64
import json
import os
import sys
import tempfile
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeSDKClient, ResultMessage, SystemMessage
from mcp.client import Client
from mcp.types import TextContent

from cairn import bundle, claims, dispatch, runner, skeptic, skeptic_tools, substrate, worker
from cairn.profile import Evaluation

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _skeptic_isolation_seed import _make_skeptic_bundle, _seed
from _substrate_helpers import IDENTITY_A, recipe


@pytest.fixture
def skeptic_bundle(tmp_path, clear_flags):
    return _make_skeptic_bundle(tmp_path, clear_flags, "all", sorted(skeptic.MAX_EVIDENCE_KINDS))


def _payload(result):
    assert len(result.content) == 1
    content = result.content[0]
    assert isinstance(content, TextContent)
    return json.loads(content.text)


def test_snapshot_reads_filtered_records_and_refuses_forbidden_data(tmp_path, skeptic_bundle, db_snapshot):
    bundle_path, pin_path = skeptic_bundle
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    writer = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    try:
        seeded = _seed(writer, gate)
        db_snapshot(writer.conn, "skeptic-seeded")
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)

        ladder_hash = seeded["evidence"]["ladder_table"].hash
        assert handle.read(seeded["statement"].hash)["claim_id"] == seeded["statement"].claim_id
        assert handle.read(ladder_hash) == {
            "kind": "ladder_table",
            "recipe_hash": seeded["recipe_key"],
            "certificate_hash": seeded["certificate_hash"],
            "repro_record_hash": seeded["repro"].hash,
            "attempt_id": seeded["attempt_id"],
        }
        recipe_projection = handle.read(seeded["recipe_key"])
        assert recipe_projection["canonical"]["encoding"] == "base64"
        assert (
            base64.b64decode(recipe_projection["canonical"]["content"])
            == writer.get_node(seeded["recipe_key"])["canonical"]
        )
        cert_projection = handle.read(seeded["certificate_hash"])
        assert (
            base64.b64decode(cert_projection["canonical"]["content"])
            == writer.get_node(seeded["certificate_hash"])["canonical"]
        )
        repro_projection = handle.read(seeded["repro"].hash)
        assert (
            base64.b64decode(repro_projection["canonical"]["content"])
            == writer.get_node(seeded["repro"].hash)["canonical"]
        )
        assert handle.request_rerun(ladder_hash) == skeptic.RerunRequest(
            statement_hash=seeded["statement"].hash,
            evidence_hash=ladder_hash,
            attempt_id=seeded["attempt_id"],
            recipe_key=seeded["recipe_key"],
        )

        result = handle.read(ladder_hash)
        result["kind"] = "lean_artifact"
        assert handle.read(ladder_hash)["kind"] == "ladder_table"
        assert not hasattr(handle, "conn")
        assert not hasattr(handle, "put_blob")
        for forbidden in (
            seeded["solution_blob"],
            seeded["transcript_node"],
            seeded["other_statement"].hash,
            seeded["other_evidence"].hash,
            seeded["gate_run"].hash,
            seeded["lean_recipe"],
        ):
            with pytest.raises(skeptic.ScopedReadRefused):
                handle.read(forbidden)
    finally:
        writer.close()


def test_snapshot_scope_filters_each_evidence_kind(tmp_path, clear_flags, db_snapshot):
    for kind in ("repro_node", "ladder_table", "counterexample_hunt_record", "lean_artifact"):
        writer = substrate.Substrate.open(tmp_path / f"substrate-{kind}.sqlite")
        try:
            bundle_path, pin_path = _make_skeptic_bundle(tmp_path, clear_flags, kind, [kind])
            gate = bundle.GateBundle.open(bundle_path, pin_path)
            seeded = _seed(writer, gate, statement_seed=31 + len(kind))
            handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
            assert handle.read(seeded["evidence"][kind].hash) is not None
            for other_kind, other_node in seeded["evidence"].items():
                if other_kind != kind:
                    with pytest.raises(skeptic.ScopedReadRefused):
                        handle.read(other_node.hash)
            db_snapshot(writer.conn, f"skeptic-scope-{kind}")
        finally:
            writer.close()


def test_lean_binding_is_statement_and_bundle_scoped(tmp_path, skeptic_bundle, db_snapshot):
    bundle_path, pin_path = skeptic_bundle
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    writer = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    try:
        seeded = _seed(writer, gate)
        db_snapshot(writer.conn, "skeptic-lean-seeded")
        lean_hash = seeded["evidence"]["lean_artifact"].hash
        assert skeptic.snapshot(writer, gate, seeded["statement"].hash).read(lean_hash) == {
            "formal_statement_hash": "f" * 64,
            "verdict": "pass",
        }
    finally:
        writer.close()


@pytest.mark.parametrize("mismatch", ["bundle", "statement"])
def test_lean_binding_mismatch_is_refused(tmp_path, skeptic_bundle, db_snapshot, mismatch):
    bundle_path, pin_path = skeptic_bundle
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    writer = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    try:
        seeded = _seed(writer, gate, include_lean=False)
        bad_run = factories.gate_run(
            gate="challenge_render",
            result="pass",
            seed=901,
            bundle_hash="0" * 64 if mismatch == "bundle" else gate.hash,
            pin_hash=gate.pin_hash,
            statement_hash=seeded["other_statement"].hash if mismatch == "statement" else seeded["statement"].hash,
            formal_statement_hash="e" * 64,
            renderer_hash="a" * 64,
            prelude_hash="b" * 64,
            arm="dev-macos-fake-landrun",
        )
        claims.write_gate_run(writer, bad_run)
        lean = factories.evidence_node(
            "lean_artifact",
            seeded["statement"].hash,
            seeded["statement"].scope,
            seeded["statement"].scope["assumption_set"],
            producer=(seeded["identity_hash"], "gate"),
            seed=902,
            attempt_id=None,
            repro=None,
        )
        claims.write_evidence_node(writer, lean)
        writer.add_lineage(lean.hash, bad_run.hash, substrate.EDGE_INPUT)
        db_snapshot(writer.conn, "skeptic-lean-bad-binding")
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(writer, gate, seeded["statement"].hash)
    finally:
        writer.close()


def test_rerun_refuses_lean_and_missing_attempt(tmp_path, skeptic_bundle, db_snapshot):
    bundle_path, pin_path = skeptic_bundle
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    writer = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    try:
        seeded = _seed(writer, gate)
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        with pytest.raises(skeptic.ScopedReadRefused):
            handle.request_rerun(seeded["evidence"]["lean_artifact"].hash)
        missing_attempt = factories.evidence_node(
            "repro_node",
            seeded["statement"].hash,
            seeded["statement"].scope,
            seeded["statement"].scope["assumption_set"],
            producer=(seeded["identity_hash"], "skill"),
            seed=999,
            attempt_id=None,
        )
        claims.write_evidence_node(writer, missing_attempt)
        db_snapshot(writer.conn, "skeptic-rerun-refusals")
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        with pytest.raises(skeptic.ScopedReadRefused):
            handle.request_rerun(missing_attempt.hash)
    finally:
        writer.close()


def test_real_mcp_server_exposes_only_scoped_reads_and_rerun_requests(tmp_path, skeptic_bundle):
    gate = bundle.GateBundle.open(*skeptic_bundle)
    with substrate.Substrate.open(tmp_path / "mcp.sqlite") as writer:
        seeded = _seed(writer, gate)
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        scoped = skeptic_tools.ScopedTools(handle, tuple(sorted(skeptic_tools.TOOLS)))
        before = writer.conn.total_changes

        async def exercise():
            async with Client(scoped.server["instance"]) as client:
                offered = await client.list_tools()
                assert {item.name for item in offered.tools} == {"list_nodes", "read_node", "request_rerun"}
                listed = await client.call_tool("list_nodes", {})
                assert not listed.is_error
                assert set(_payload(listed)["node_hashes"]) == set(handle.node_hashes)
                for digest in handle.node_hashes:
                    read = await client.call_tool("read_node", {"node_hash": digest})
                    assert not read.is_error
                    assert _payload(read) == handle.read(digest)
                for digest in (
                    seeded["solution_blob"],
                    seeded["lean_recipe"],
                    seeded["transcript_node"],
                    seeded["other_statement"].hash,
                    seeded["other_evidence"].hash,
                ):
                    denied = await client.call_tool("read_node", {"node_hash": digest})
                    assert denied.is_error
                for name in ("Bash", "Read", "put_blob", "execute_sql"):
                    denied = await client.call_tool(name, {})
                    assert denied.is_error
                extra = await client.call_tool("read_node", {"node_hash": handle.statement_hash, "sql": "SELECT 1"})
                assert extra.is_error
                request = await client.call_tool(
                    "request_rerun", {"evidence_hash": seeded["evidence"]["ladder_table"].hash}
                )
                assert not request.is_error
                assert _payload(request)["rerun_request"] == scoped.requests[0]
                forbidden = await client.call_tool(
                    "request_rerun", {"evidence_hash": seeded["evidence"]["lean_artifact"].hash}
                )
                assert forbidden.is_error

        asyncio.run(exercise())
        assert len(scoped.requests) == 1
        assert writer.conn.total_changes == before


def test_a_narrow_tool_list_removes_the_rerun_tool(tmp_path, skeptic_bundle):
    gate = bundle.GateBundle.open(*skeptic_bundle)
    with substrate.Substrate.open(tmp_path / "narrow.sqlite") as writer:
        seeded = _seed(writer, gate)
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        scoped = skeptic_tools.ScopedTools(handle, (skeptic_tools.READ_NODE,))

        async def exercise():
            async with Client(scoped.server["instance"]) as client:
                assert [item.name for item in (await client.list_tools()).tools] == ["read_node"]
                denied = await client.call_tool(
                    "request_rerun", {"evidence_hash": seeded["evidence"]["ladder_table"].hash}
                )
                assert denied.is_error

        asyncio.run(exercise())
        assert scoped.requests == []
        with pytest.raises(ValueError, match="allow-list"):
            skeptic_tools.ScopedTools(handle, (skeptic_tools.READ_NODE, skeptic_tools.READ_NODE))


def test_writer_executes_mcp_rerun_request_as_a_fresh_measured_attempt(tmp_path, skeptic_bundle, db_snapshot):
    gate = bundle.GateBundle.open(*skeptic_bundle)
    with substrate.Substrate.open(tmp_path / "rerun.sqlite") as writer:
        seeded = _seed(writer, gate, include_lean=False)
        launch_options = {
            "bundle_hash": gate.hash,
            "evaluation": Evaluation(1.0, 1.0, 0.1),
            "ceiling_multiplier": 4,
            "tool_digests": IDENTITY_A["tool_digests"],
            "scratch_root": tmp_path / "runs",
            "env_extra": {"PYTHONPATH": str(Path(__file__).resolve().parent.parent / "fixtures")},
        }
        inputs = recipe(seed=61, skill_identity_hash=seeded["identity_hash"])
        first = runner.launch(writer, "skills.scratch_1mb", inputs, **launch_options)
        assert first.status == "OK" and first.launch is not None
        assert writer.serve(first.recipe_key).attempt_id == first.attempt_id
        evidence = factories.evidence_node(
            "repro_node",
            seeded["statement"].hash,
            seeded["statement"].scope,
            seeded["statement"].scope["assumption_set"],
            producer=(seeded["identity_hash"], "skill"),
            attempt_id=first.attempt_id,
            seed=61,
        )
        claims.write_evidence_node(writer, evidence)
        scoped = skeptic_tools.ScopedTools(
            skeptic.snapshot(writer, gate, seeded["statement"].hash), (skeptic_tools.REQUEST_RERUN,)
        )

        async def request():
            async with Client(scoped.server["instance"]) as client:
                result = await client.call_tool("request_rerun", {"evidence_hash": evidence.hash})
                assert not result.is_error

        asyncio.run(request())
        requested = scoped.requests[0]
        second = runner.launch(
            writer, "skills.scratch_1mb", **skeptic_tools.rerun_options(writer, gate, requested), **launch_options
        )
        assert second.status == "OK" and second.launch is not None
        assert not second.served_from_cache
        assert second.attempt_id != first.attempt_id
        assert second.output_manifest_hash == first.output_manifest_hash
        assert writer.get_attempt(second.attempt_id)["skip_cache_lookup"] == 1
        assert writer.get_attempt(second.attempt_id)["receipt_hash"] is not None
        db_snapshot(writer.conn, "skeptic-fresh-rerun")
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic_tools.rerun_options(writer, gate, {**requested, "prompt": "unhanded prose"})
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic_tools.rerun_options(writer, gate, {**requested, "recipe_key": seeded["recipe_key"]})
        writer.disown(first.attempt_id)
        with pytest.raises(skeptic.ScopedReadRefused, match="standing"):
            skeptic_tools.rerun_options(writer, gate, requested)


async def live_check(directory):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("the named live close gate requires an existing ANTHROPIC_API_KEY")
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(
            directory, lambda _: None, "live", sorted(skeptic.MAX_EVIDENCE_KINDS), tools=sorted(skeptic_tools.TOOLS)
        )
    )
    with substrate.Substrate.open(directory / "live-substrate.sqlite") as sub:
        statement = replace(factories.claim_statement(seed=810), informal="CAIRN_SCOPED_READ_810")
        claims.write_claim_statement(sub, statement)
        prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(statement.hash,))
        record = dispatch._record(sub, prepared)
        scoped = skeptic_tools.ScopedTools(skeptic.snapshot(sub, gate, statement.hash), prepared.tools)
        cwd = directory / "cwd"
        cwd.mkdir()
        options = replace(
            worker._options(prepared, cwd, {skeptic_tools.SERVER_NAME: scoped.server}), max_budget_usd=0.01
        )
        initialized = None
        finished = None
        async with asyncio.timeout(prepared.timeout_s):
            async with ClaudeSDKClient(options=options) as client:
                await client.query(prepared.prompt)
                async for message in client.receive_response():
                    if isinstance(message, SystemMessage) and message.subtype == "init":
                        initialized = message.data
                        print(json.dumps({"initialization": initialized}, sort_keys=True), flush=True)
                        worker._validate_init(prepared, cwd, initialized)
                    elif isinstance(message, ResultMessage):
                        finished = message
        result = worker._result_payload(initialized, finished)
        assert isinstance(finished, ResultMessage)
        print(json.dumps({"terminal": asdict(finished)}, sort_keys=True), flush=True)
        print(
            json.dumps(
                {"record": record.as_dict(), "result": result, "successful_tool_reads": scoped.read_node_hashes},
                sort_keys=True,
            ),
            flush=True,
        )
        assert result["status"] == "success"
        assert result["text"] == statement.informal
        assert set(result["observed_tools"]) == skeptic_tools.TOOLS
        assert result["observed_skills"] == () and result["observed_plugins"] == ()
        assert statement.hash in scoped.read_node_hashes


if __name__ == "__main__":
    directory = Path(tempfile.mkdtemp(prefix="cairn-live-skeptic-"))
    print(json.dumps({"artifact_directory": str(directory)}), flush=True)
    asyncio.run(live_check(directory))
