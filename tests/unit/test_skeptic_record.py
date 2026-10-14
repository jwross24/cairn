import asyncio
import dataclasses
import json

import pytest
from claude_agent_sdk import ResultMessage, SystemMessage
from mcp.client import Client

from cairn import bundle, claims, dispatch, skeptic_tools, substrate, worker
from cairn.substrate import HashMismatch


@pytest.fixture
def arena(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    role = {
        "template": dispatch.SKEPTIC_HUNT_TEMPLATE,
        "tools": [skeptic_tools.READ_NODE],
        "model": "claude-offline-fixture",
        "max_turns": 1,
        "timeout_s": 1,
    }
    (source / "worker_roles.json").write_text(json.dumps({"skeptic": role, "prover": role}))
    (source / "role_templates.json").write_text(
        json.dumps({dispatch.SKEPTIC_HUNT_TEMPLATE: "1. Offline fixture item\n2. Offline fixture item"})
    )
    (source / "skeptic_scope.json").write_text(json.dumps({"evidence_kinds": []}))
    path, pin = tmp_path / "bundle.sqlite", tmp_path / "bundle.pin"
    pin.write_text(bundle.build(source, path) + "\n")
    gate = bundle.GateBundle.open(path, pin)
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        statement = claims.ClaimStatement(
            "offline-fixture",
            1,
            "Offline fixture statement",
            {"target_family": "fixture", "size_interval": [1, 2], "param_ranges": {}, "assumption_set": []},
            {"units": {}, "cost_model": None},
        )
        claims.write_claim_statement(sub, statement)
        yield sub, gate, statement


def record(
    arena,
    *,
    role="skeptic",
    status="success",
    change=None,
    text=None,
    reads=True,
    session_id="offline-fixture",
    template=None,
):
    sub, gate, statement = arena
    prepared = dispatch._prepare(sub, gate, role=role, node_ids=(statement.hash,))
    if template is not None:
        prepared = dataclasses.replace(prepared, template=template)
    sent = dispatch._record(sub, prepared)
    scoped = skeptic_tools.ScopedTools(prepared.skeptic_handle, prepared.tools)

    async def read():
        async with Client(scoped.server["instance"]) as client:
            response = await client.call_tool("read_node", {"node_hash": statement.hash})
            assert not response.is_error

    if reads:
        asyncio.run(read())
    value = {
        "statement_hash": statement.hash,
        "verdict": "gap",
        "items": [
            {"id": i, "outcome": "gap", "answer": "Offline fixture only", "cited_node_hashes": [statement.hash]}
            for i in (1, 2)
        ],
    }
    if change is not None:
        change(value)
    finished = dispatch.DispatchResult(
        sent.dispatch_id,
        status,
        json.dumps(value) if text is None else text,
        session_id,
        prepared.tools,
        (),
        (),
        None,
        sent.at,
        read_node_hashes=tuple(scoped.read_node_hashes),
    )
    dispatch._write(sub, "worker_result", "worker_results", finished, (sent.hash,))
    return sent, finished


def test_real_record_and_local_mcp_reads_form_typed_view(arena):
    sub, _, statement = arena
    sent, finished = record(arena)
    view = dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)
    assert isinstance(view, dispatch.SkepticRecord)
    assert view.dispatch_hash == sent.hash and view.result_hash == finished.hash
    assert view.role_template_hash == sent.role_template_hash
    assert view.read_node_hashes == (statement.hash,)
    assert tuple(item.id for item in view.items) == (1, 2)
    assert view.verdict == "gap"
    assert dispatch.result(sub, sent.dispatch_id) == finished
    assert sub.conn.execute("SELECT COUNT(*) FROM tag_history").fetchone()[0] == 0


def test_worker_execute_persists_only_successful_local_mcp_reads(arena, tmp_path, monkeypatch):
    sub, gate, statement = arena
    prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(statement.hash,))
    sent = dispatch._record(sub, prepared)
    value = {
        "statement_hash": statement.hash,
        "verdict": "gap",
        "items": [
            {"id": i, "outcome": "gap", "answer": "Offline transport fixture", "cited_node_hashes": [statement.hash]}
            for i in (1, 2)
        ],
    }

    class ScriptedClient:
        def __init__(self, *, options):
            self.options = options

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc_value, _traceback):
            return False

        async def query(self, prompt):
            assert prompt == prepared.prompt

        async def receive_response(self):
            yield SystemMessage(
                subtype="init",
                data={
                    "claude_code_version": worker.CLI_VERSION,
                    "cwd": str(tmp_path.resolve()),
                    "tools": list(prepared.tools),
                    "skills": [],
                    "plugins": [],
                    "mcp_servers": [{"name": skeptic_tools.SERVER_NAME, "source": "sdk", "status": "connected"}],
                    "slash_commands": [],
                    "session_id": "offline-transport",
                },
            )
            server = self.options.mcp_servers[skeptic_tools.SERVER_NAME]
            async with Client(server["instance"]) as client:
                accepted = await client.call_tool("read_node", {"node_hash": statement.hash})
                assert not accepted.is_error
                denied = await client.call_tool("read_node", {"node_hash": "0" * 64})
                assert denied.is_error
            yield ResultMessage(
                subtype="success",
                duration_ms=0,
                duration_api_ms=0,
                is_error=False,
                num_turns=1,
                session_id="offline-transport",
                result=json.dumps(value),
            )

    monkeypatch.setattr(worker, "ClaudeSDKClient", ScriptedClient)
    outcome = asyncio.run(worker._execute(prepared, tmp_path))
    assert outcome.get("read_node_hashes") == (statement.hash,), "missing successful scoped-read observations"
    finished = dispatch.DispatchResult(dispatch_id=sent.dispatch_id, at=sent.at, **outcome)
    dispatch._write(sub, "worker_result", "worker_results", finished, (sent.hash,))
    persisted = dispatch.result(sub, sent.dispatch_id)
    assert persisted.read_node_hashes == (statement.hash,)
    row = sub.conn.execute(
        "SELECT record_json FROM worker_results WHERE dispatch_id = ?", (sent.dispatch_id,)
    ).fetchone()
    assert json.loads(row["record_json"])["read_node_hashes"] == [statement.hash]
    view = dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)
    assert view.read_node_hashes == (statement.hash,)
    assert view.result_hash == finished.hash


def test_wrong_role_has_no_typed_record(arena):
    sub, _, statement = arena
    sent, _ = record(arena, role="prover")
    assert dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash) is None


def test_wrong_requested_statement_has_no_typed_record(arena):
    sub, _, _ = arena
    sent, _ = record(arena)
    assert dispatch.skeptic_record(sub, sent.dispatch_id, "0" * 64) is None


def test_error_result_has_no_typed_record(arena):
    sub, _, statement = arena
    sent, _ = record(arena, status="error")
    assert dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash) is None


def test_success_without_session_refuses(arena):
    sub, _, statement = arena
    sent, _ = record(arena, session_id="")
    with pytest.raises(dispatch.DispatchRefused, match="successful session missing"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


@pytest.mark.parametrize("outcome", ["clear", "gap", "issue"])
def test_audit_verdict_matches_most_severe_item(arena, outcome):
    sub, _, statement = arena

    def change(value):
        value["items"][0]["outcome"] = "clear"
        value["items"][1]["outcome"] = outcome
        value["verdict"] = outcome

    sent, _ = record(arena, change=change)
    assert dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash).verdict == outcome


@pytest.mark.parametrize("text", ["not JSON", "```json\n{}\n```", '{"items":[],"items":[]}', "NaN"])
def test_malformed_success_text_refuses(arena, text):
    sub, _, statement = arena
    sent, _ = record(arena, text=text)
    with pytest.raises(dispatch.DispatchRefused, match="malformed skeptic_record"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update(statement_hash="0" * 64),
        lambda value: value.update(verdict="PROVEN"),
        lambda value: value.update(extra="unknown"),
        lambda value: value["items"].pop(),
        lambda value: value["items"].reverse(),
        lambda value: value["items"][0].update(id=True),
        lambda value: value["items"][0].update(outcome="PASS"),
        lambda value: value["items"][0].update(answer=" "),
        lambda value: value["items"][0].update(cited_node_hashes=["0" * 64]),
        lambda value: value["items"][0].update(extra="unknown"),
    ],
)
def test_closed_schema_and_checklist_binding_refuse(arena, change):
    sub, _, statement = arena
    sent, _ = record(arena, change=change)
    with pytest.raises(dispatch.DispatchRefused, match="malformed skeptic_record"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


def test_model_citation_cannot_replace_actual_read(arena):
    sub, _, statement = arena
    sent, _ = record(arena, reads=False)
    with pytest.raises(dispatch.DispatchRefused, match="citation was not observed read"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


def test_exact_one_statement_dispatch_is_required(arena):
    sub, gate, statement = arena
    prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(statement.hash,))
    sent = dispatch._record(sub, dataclasses.replace(prepared, node_ids=(statement.hash, statement.hash)))
    assert dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash) is None


def test_missing_template_blob_refuses(arena):
    sub, _, statement = arena
    sent, _ = record(arena)
    sub.conn.execute("DELETE FROM blobs WHERE hash = ?", (sent.role_template_hash,))
    with pytest.raises(dispatch.DispatchRefused, match="evidence missing"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


def test_changed_template_blob_refuses(arena):
    sub, _, statement = arena
    sent, _ = record(arena)
    sub.conn.execute("UPDATE blobs SET bytes = ? WHERE hash = ?", (b"1. Changed", sent.role_template_hash))
    with pytest.raises(HashMismatch, match="blob does not match"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)


@pytest.mark.parametrize("template", ["Offline fixture", "2. Offline fixture", "1. First\n1. Duplicate"])
def test_recorded_template_must_have_exact_numbered_ids(arena, template):
    sub, _, statement = arena
    sent, _ = record(arena, template=template)
    with pytest.raises(dispatch.DispatchRefused, match="numbered template items"):
        dispatch.skeptic_record(sub, sent.dispatch_id, statement.hash)
