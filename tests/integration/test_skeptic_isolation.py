import asyncio
import base64
import json
import os
import shutil
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
from _substrate_helpers import ENV_MANIFEST_HASH, IDENTITY_A, SELFTEST_SUMMARY, TRANSCRIPT_HASH, recipe


def _seed(writer, gate, *, statement_seed=31, include_lean=True):
    statement = factories.claim_statement(seed=statement_seed)
    claims.write_claim_statement(writer, statement)
    identity_hash = writer.put_identity_bundle(IDENTITY_A)
    certificate_hash = writer.put_certificate(identity_hash, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    solution_blob = writer.put_blob(b"solution secret")
    recipe_key = writer.put_recipe(
        recipe(seed=statement_seed, skill_identity_hash=identity_hash, inputs={"solution": (solution_blob, 15)})
    )
    attempt_id = writer.start_attempt(recipe_key, skip_cache_lookup=True)
    writer.close_attempt(attempt_id, "OK")
    repro = factories.repro_record(attempt_id)
    claims.write_repro_record(writer, repro)
    evidence = {}
    for offset, kind in enumerate(("ladder_table", "repro_node", "counterexample_hunt_record"), 1):
        node = factories.evidence_node(
            kind,
            statement.hash,
            statement.scope,
            statement.scope["assumption_set"],
            verdict="KEEP",
            repro=repro,
            producer=(identity_hash, "skill"),
            seed=statement_seed + offset,
            attempt_id=attempt_id,
        )
        claims.write_evidence_node(writer, node)
        evidence[kind] = node
    lean = None
    gate_run = None
    lean_recipe = None
    if include_lean:
        lean_recipe = writer.put_recipe(recipe(seed=statement_seed + 500, inputs={"solution": (solution_blob, 15)}))
        lean_attempt = writer.start_attempt(lean_recipe, skip_cache_lookup=True)
        writer.close_attempt(lean_attempt, "OK")
        gate_run = factories.gate_run(
            gate="challenge_render",
            result="pass",
            seed=statement_seed + 20,
            bundle_hash=gate.hash,
            pin_hash=gate.pin_hash,
            statement_hash=statement.hash,
            formal_statement_hash="f" * 64,
            renderer_hash="a" * 64,
            prelude_hash="b" * 64,
            arm="dev-macos-fake-landrun",
        )
        claims.write_gate_run(writer, gate_run)
        lean = factories.evidence_node(
            "lean_artifact",
            statement.hash,
            statement.scope,
            statement.scope["assumption_set"],
            verdict="KEEP",
            producer=(identity_hash, "gate"),
            seed=statement_seed + 21,
            attempt_id=lean_attempt,
            repro=None,
        )
        claims.write_evidence_node(writer, lean)
        writer.add_lineage(lean.hash, gate_run.hash, substrate.EDGE_INPUT)
        evidence["lean_artifact"] = lean
    other_statement = factories.claim_statement(seed=statement_seed + 100)
    claims.write_claim_statement(writer, other_statement)
    other_evidence = factories.evidence_node(
        "ladder_table",
        other_statement.hash,
        other_statement.scope,
        other_statement.scope["assumption_set"],
        verdict="KEEP",
        producer=(identity_hash, "skill"),
        seed=statement_seed + 101,
        attempt_id=attempt_id,
    )
    claims.write_evidence_node(writer, other_evidence)
    transcript_node = writer.put_node("prover_transcript", b"prover proof text")
    return {
        "statement": statement,
        "identity_hash": identity_hash,
        "certificate_hash": certificate_hash,
        "recipe_key": recipe_key,
        "attempt_id": attempt_id,
        "repro": repro,
        "evidence": evidence,
        "other_statement": other_statement,
        "other_evidence": other_evidence,
        "solution_blob": solution_blob,
        "transcript_node": transcript_node,
        "gate_run": gate_run,
        "lean_recipe": lean_recipe,
    }


def _make_skeptic_bundle(tmp_path, clear_flags, name, kinds, *, tools=None):
    source = tmp_path / f"{name}-source"
    shutil.copytree(bundle.REPO_ROOT / "bundle", source)
    (source / "skeptic_scope.json").write_text(json.dumps({"evidence_kinds": kinds}))
    if tools is not None:
        (source / "worker_roles.json").write_text(
            json.dumps(
                {
                    "skeptic": {
                        "template": "scoped_read_probe",
                        "tools": tools,
                        "model": "claude-haiku-4-5-20251001",
                        "max_turns": 4,
                        "timeout_s": 120,
                    }
                }
            )
        )
        templates = json.loads((source / "role_templates.json").read_text())
        templates["scoped_read_probe"] = (
            "Call read_node with the first handed node's hash. "
            "Return exactly the informal field from that tool result, without surrounding text."
        )
        (source / "role_templates.json").write_text(json.dumps(templates))
    bundle_path = tmp_path / f"{name}.sqlite"
    pin_path = tmp_path / f"{name}.pin"
    bundle.build(source, bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    clear_flags(pin_path)
    return bundle_path, pin_path


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
        hunt = factories.evidence_node(
            "counterexample_hunt_record",
            seeded["statement"].hash,
            seeded["statement"].scope,
            seeded["statement"].scope["assumption_set"],
            producer=(seeded["identity_hash"], "skill"),
            seed=999,
            attempt_id=None,
        )
        claims.write_evidence_node(writer, hunt)
        db_snapshot(writer.conn, "skeptic-rerun-refusals")
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        with pytest.raises(skeptic.ScopedReadRefused):
            handle.request_rerun(hunt.hash)
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


@pytest.mark.parametrize("kinds", [None, "all", ["prover_transcript"], ["ladder_table", "ladder_table"], [7]])
def test_invalid_pinned_scope_is_refused(tmp_path, clear_flags, kinds):
    gate = bundle.GateBundle.open(*_make_skeptic_bundle(tmp_path, clear_flags, "invalid", kinds))
    with substrate.Substrate.open(tmp_path / "invalid-substrate.sqlite") as writer:
        seeded = _seed(writer, gate, include_lean=False)
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(writer, gate, seeded["statement"].hash)


def test_missing_pinned_scope_does_not_grant_the_maximum(tmp_path, pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    with substrate.Substrate.open(tmp_path / "missing.sqlite") as writer:
        seeded = _seed(writer, gate, include_lean=False)
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(writer, gate, seeded["statement"].hash)


def test_in_memory_scope_mutation_cannot_widen_access(tmp_path, clear_flags):
    gate = bundle.GateBundle.open(*_make_skeptic_bundle(tmp_path, clear_flags, "narrow", ["lean_artifact"]))
    with substrate.Substrate.open(tmp_path / "narrow-memory.sqlite") as writer:
        seeded = _seed(writer, gate)
        gate.object("skeptic_scope")["evidence_kinds"].append("ladder_table")
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        assert handle.read(seeded["evidence"]["lean_artifact"].hash)["verdict"] == "pass"
        with pytest.raises(skeptic.ScopedReadRefused):
            handle.read(seeded["evidence"]["ladder_table"].hash)


def test_dispatch_prepares_a_scoped_handle_and_records_rerun_artifacts(tmp_path, clear_flags):
    tools = [skeptic_tools.READ_NODE, skeptic_tools.REQUEST_RERUN]
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(tmp_path, clear_flags, "dispatch", sorted(skeptic.MAX_EVIDENCE_KINDS), tools=tools)
    )
    with substrate.Substrate.open(tmp_path / "dispatch-substrate.sqlite") as sub:
        seeded = _seed(sub, gate)
        prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(seeded["statement"].hash,))
        assert isinstance(prepared.skeptic_handle, skeptic.Handle)
        assert prepared.skeptic_handle.read(seeded["statement"].hash)["claim_id"] == seeded["statement"].claim_id
        with pytest.raises(skeptic.ScopedReadRefused):
            prepared.skeptic_handle.read(seeded["transcript_node"])
        record = dispatch._record(sub, prepared)
        assert dispatch.read(sub, record.dispatch_id).tool_allow_list == tuple(tools)
        request = asdict(prepared.skeptic_handle.request_rerun(seeded["evidence"]["ladder_table"].hash))
        finished = dispatch.DispatchResult(
            dispatch_id=record.dispatch_id,
            status="success",
            text="",
            session_id="record-fixture",
            observed_tools=tuple(tools),
            observed_skills=(),
            observed_plugins=(),
            cost_usd=None,
            at=record.at,
            rerun_requests=(request,),
        )
        dispatch._write(sub, "worker_result", "worker_results", finished, (record.hash,))
        assert dispatch.result(sub, record.dispatch_id) == finished
        stored = sub.conn.execute(
            "SELECT record_json FROM worker_results WHERE dispatch_id = ?", (record.dispatch_id,)
        ).fetchone()
        assert json.loads(stored["record_json"])["rerun_requests"] == [request]


@pytest.mark.parametrize("handed", ["empty", "transcript", "statement_and_transcript", "two_statements"])
def test_scoped_dispatch_refuses_unfiltered_handed_nodes(tmp_path, clear_flags, handed):
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(
            tmp_path, clear_flags, "handed", sorted(skeptic.MAX_EVIDENCE_KINDS), tools=[skeptic_tools.READ_NODE]
        )
    )
    with substrate.Substrate.open(tmp_path / "handed-substrate.sqlite") as sub:
        seeded = _seed(sub, gate)
        choices = {
            "empty": (),
            "transcript": (seeded["transcript_node"],),
            "statement_and_transcript": (seeded["statement"].hash, seeded["transcript_node"]),
            "two_statements": (seeded["statement"].hash, seeded["other_statement"].hash),
        }
        with pytest.raises(dispatch.DispatchRefused, match="exactly one handed claim statement"):
            dispatch._prepare(sub, gate, role="skeptic", node_ids=choices[handed])
        assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_dispatch_distinguishes_a_supported_tool_from_its_duplicate(tmp_path, clear_flags):
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(tmp_path, clear_flags, "valid-tool", ["ladder_table"], tools=[skeptic_tools.READ_NODE])
    )
    duplicate = bundle.GateBundle.open(
        *_make_skeptic_bundle(
            tmp_path,
            clear_flags,
            "duplicate-tool",
            ["ladder_table"],
            tools=[skeptic_tools.READ_NODE, skeptic_tools.READ_NODE],
        )
    )
    with substrate.Substrate.open(tmp_path / "duplicate-substrate.sqlite") as sub:
        seeded = _seed(sub, gate, include_lean=False)
        prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(seeded["statement"].hash,))
        assert prepared.tools == (skeptic_tools.READ_NODE,)
        with pytest.raises(dispatch.DispatchRefused, match="duplicate worker tool"):
            dispatch._prepare(sub, duplicate, role="skeptic", node_ids=(seeded["statement"].hash,))


def test_empty_rerun_artifacts_preserve_record_bytes():
    fields = {
        "dispatch_id": "record-fixture",
        "status": "success",
        "text": "",
        "session_id": "session-fixture",
        "observed_tools": (),
        "observed_skills": (),
        "observed_plugins": (),
        "cost_usd": None,
        "at": "2026-09-08T00:00:00+00:00",
    }
    result = dispatch.DispatchResult(
        "record-fixture", "success", "", "session-fixture", (), (), (), None, "2026-09-08T00:00:00+00:00"
    )
    assert result.rerun_requests == ()
    assert result.as_dict() == fields
    assert result.hash == substrate.node_hash_for("worker_result", bundle.canonical_bytes("worker_result", fields))


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


def test_a_handed_bundle_that_is_not_the_pinned_bundle_is_refused(tmp_path, clear_flags):
    bundle_path, pin_path = _make_skeptic_bundle(tmp_path, clear_flags, "pinned-narrow", ["lean_artifact"])
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    widened = json.dumps({"evidence_kinds": sorted(skeptic.MAX_EVIDENCE_KINDS)}).encode()
    forged_rows = [
        bundle._row(kind, bundle.canonical_bytes(kind, json.loads(widened)))
        if kind == "skeptic_scope"
        else (kind, canonical, digest)
        for kind, canonical, digest in gate.rows
    ]
    forged_hash = bundle.bundle_hash(forged_rows)
    forged = bundle.GateBundle(bundle_path, pin_path, forged_rows, forged_hash, forged_hash)
    assert forged.object("skeptic_scope")["evidence_kinds"] == sorted(skeptic.MAX_EVIDENCE_KINDS)
    with substrate.Substrate.open(tmp_path / "forged.sqlite") as writer:
        seeded = _seed(writer, gate)
        assert (
            skeptic.snapshot(writer, gate, seeded["statement"].hash).read(seeded["evidence"]["lean_artifact"].hash)[
                "verdict"
            ]
            == "pass"
        )
        with pytest.raises(skeptic.ScopedReadRefused, match="supplied gate bundle is not the pinned bundle"):
            skeptic.snapshot(writer, forged, seeded["statement"].hash)
