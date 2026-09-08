import asyncio
import json
import sys
import tempfile
from pathlib import Path

from claude_agent_sdk._internal.transport.subprocess_cli import SubprocessCLITransport

from cairn import dispatch, worker
from cairn.substrate import Substrate, blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.worker_dispatch import ECHO_TEXT, TEMPLATE, arena, make_bundle

__all__ = ["arena"]


def test_real_sdk_command_contains_only_the_constructed_context(arena, tmp_path):
    sub, gate_bundle, node = arena
    prepared = dispatch._prepare(sub, gate_bundle, role="echo", node_ids=(node,))
    options = worker._options(prepared, tmp_path)
    transport = SubprocessCLITransport(prompt=prepared.prompt, options=options)
    command = transport._build_command()
    assert command[command.index("--system-prompt") + 1] == TEMPLATE
    assert command[command.index("--tools") + 1] == ""
    assert "--setting-sources=" in command
    assert {"--bare", "--disable-slash-commands", "--no-session-persistence", "--strict-mcp-config"} <= set(command)
    assert not any(
        arg.startswith(("--resume", "--continue", "--fork-session", "--append-system-prompt")) for arg in command
    )
    assert options.cwd == tmp_path
    assert options.skills == [] and options.plugins == [] and options.mcp_servers == {}
    assert json.loads(prepared.prompt) == [
        {"hash": node, "kind": "worker_input", "encoding": "utf-8", "content": ECHO_TEXT}
    ]


def test_dispatch_record_fields_and_ledger_root(arena):
    sub, gate_bundle, node = arena
    prepared = dispatch._prepare(sub, gate_bundle, role="echo", node_ids=(node,))
    record = dispatch._record(sub, prepared)
    stored = dispatch.read(sub, record.dispatch_id)
    assert stored == record
    assert record.handed_node_hashes == (node,)
    assert record.role_template_hash == blob_hash(TEMPLATE.encode())
    assert record.tool_allow_list == ()
    assert record.prompt_bytes_hash == blob_hash(prepared.prompt.encode())
    assert record.request_bytes_hash is None
    assert record.request_bytes_unavailable == "sdk-query-does-not-expose-provider-bytes"
    assert record.bundle_hash == gate_bundle.hash
    assert record.role_config_hash == gate_bundle.digest_of("worker_roles")
    assert dispatch.result(sub, record.dispatch_id) is None
    assert sub.get_node(record.hash)["replay_grade"] == "AuditOnly"
    roots = sub.conn.execute("SELECT node_hash FROM roots WHERE root_kind = 'ledger_row'").fetchall()
    assert record.hash in {r[0] for r in roots}


async def live_check(directory):
    gate_bundle = make_bundle(directory)
    with Substrate.open(directory / "substrate.sqlite") as sub:
        node = sub.put_node("worker_input", ECHO_TEXT.encode())
        first = await dispatch.run(sub, gate_bundle, role="echo", node_ids=(node,))
        assert first.status == "success", first
        assert first.text == ECHO_TEXT, first
        assert first.observed_tools == ()
        assert first.observed_skills == ()
        assert first.observed_plugins == ()
        record = dispatch.read(sub, first.dispatch_id)
        assert record.handed_node_hashes == (node,)
        assert record.role_template_hash == blob_hash(TEMPLATE.encode())
        assert record.request_bytes_hash is None
        assert dispatch.result(sub, first.dispatch_id) == first
        print(json.dumps({"record": record.as_dict(), "result": first.as_dict()}, sort_keys=True))
        second = await dispatch.run(sub, gate_bundle, role="echo", node_ids=(node,))
        assert second.status == "success" and second.text == ECHO_TEXT, second
        assert second.session_id != first.session_id
        assert second.observed_tools == ()
        assert dispatch.read(sub, second.dispatch_id).tool_allow_list == ()
        print(json.dumps({"record": dispatch.read(sub, second.dispatch_id).as_dict(), "result": second.as_dict()}))
        task = asyncio.create_task(dispatch.run(sub, gate_bundle, role="echo", node_ids=(node,)))
        while sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] < 3:
            await asyncio.sleep(0)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise AssertionError("the canceled dispatch did not propagate cancellation")
        row = sub.conn.execute("SELECT dispatch_id FROM worker_dispatches ORDER BY rowid DESC LIMIT 1").fetchone()
        third_id = row[0]
        canceled = dispatch.result(sub, third_id)
        assert canceled.status == "error" and canceled.text == "CancelledError"
        assert canceled.cost_usd is None
        print(json.dumps({"record": dispatch.read(sub, third_id).as_dict(), "result": canceled.as_dict()}))


if __name__ == "__main__":
    directory = Path(tempfile.mkdtemp(prefix="cairn-live-dispatch-"))
    print(json.dumps({"artifact_directory": str(directory)}), flush=True)
    asyncio.run(live_check(directory))


def test_a_scoped_mcp_server_reaches_the_options_the_sdk_receives(arena, tmp_path):
    sub, gate_bundle, node = arena
    prepared = dispatch._prepare(sub, gate_bundle, role="echo", node_ids=(node,))
    servers = {"cairn_scope": {"type": "sdk", "name": "cairn_scope"}}
    assert worker._options(prepared, tmp_path, servers).mcp_servers == servers
    assert worker._options(prepared, tmp_path).mcp_servers == {}


def test_the_worker_envelope_pins_permission_mode_and_disables_thinking(arena, tmp_path):
    sub, gate_bundle, node = arena
    prepared = dispatch._prepare(sub, gate_bundle, role="echo", node_ids=(node,))
    options = worker._options(prepared, tmp_path)
    assert options.permission_mode == "dontAsk"
    assert options.thinking == {"type": "disabled"}
    assert options.setting_sources == []
    assert options.strict_mcp_config is True
