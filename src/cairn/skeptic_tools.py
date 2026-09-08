import json
from dataclasses import asdict

from claude_agent_sdk import create_sdk_mcp_server, tool

from cairn import repro, skeptic, yank

SERVER_NAME = "cairn_skeptic"
READ_NODE = f"mcp__{SERVER_NAME}__read_node"
LIST_NODES = f"mcp__{SERVER_NAME}__list_nodes"
REQUEST_RERUN = f"mcp__{SERVER_NAME}__request_rerun"
TOOLS = frozenset({LIST_NODES, READ_NODE, REQUEST_RERUN})


def _response(value, *, failed=False):
    return {
        "content": [{"type": "text", "text": json.dumps(value, sort_keys=True, separators=(",", ":"))}],
        "is_error": failed,
    }


class ScopedTools:
    def __init__(self, handle, allow_list):
        if len(set(allow_list)) != len(allow_list) or not set(allow_list) <= TOOLS:
            raise ValueError("invalid scoped tool allow-list")
        self.requests = []
        self.read_node_hashes = []

        @tool("list_nodes", "List the hashes readable in the scoped statement evidence.", {})
        async def list_nodes(arguments):
            if arguments:
                return _response({"refused": "list_nodes takes no arguments"}, failed=True)
            return _response({"node_hashes": handle.node_hashes})

        @tool("read_node", "Read one node from the scoped statement evidence.", {"node_hash": str})
        async def read_node(arguments):
            try:
                if set(arguments) != {"node_hash"}:
                    raise skeptic.ScopedReadRefused("read_node requires only node_hash")
                value = handle.read(arguments["node_hash"])
                self.read_node_hashes.append(arguments["node_hash"])
                return _response(value)
            except (skeptic.ScopedReadRefused, TypeError) as exc:
                return _response({"refused": str(exc)}, failed=True)

        @tool("request_rerun", "Request a fresh writer-owned rerun of scoped evidence.", {"evidence_hash": str})
        async def request_rerun(arguments):
            try:
                if set(arguments) != {"evidence_hash"}:
                    raise skeptic.ScopedReadRefused("request_rerun requires only evidence_hash")
                request = asdict(handle.request_rerun(arguments["evidence_hash"]))
                self.requests.append(request)
                return _response({"rerun_request": request})
            except (skeptic.ScopedReadRefused, TypeError) as exc:
                return _response({"refused": str(exc)}, failed=True)

        registry = {LIST_NODES: list_nodes, READ_NODE: read_node, REQUEST_RERUN: request_rerun}
        self.server = create_sdk_mcp_server(
            name=SERVER_NAME,
            version="1.0.0",
            tools=[registry[name] for name in allow_list],
        )


def rerun_options(sub, gate_bundle, request):
    if not isinstance(request, dict) or set(request) != {
        "statement_hash",
        "evidence_hash",
        "attempt_id",
        "recipe_key",
    }:
        raise skeptic.ScopedReadRefused("invalid rerun request fields")
    handle = skeptic.snapshot(sub, gate_bundle, request["statement_hash"])
    expected = handle.request_rerun(request["evidence_hash"])
    if asdict(expected) != request:
        raise skeptic.ScopedReadRefused("rerun request differs from scoped evidence")
    attempt = sub.get_attempt(expected.attempt_id)
    if attempt is None or attempt["disowned_at"] is not None or attempt["inadmissible"]:
        raise skeptic.ScopedReadRefused("rerun source attempt is not standing")
    if yank.covers_recipe(sub, expected.recipe_key):
        raise skeptic.ScopedReadRefused("rerun recipe is yanked")
    return {"recipe": yank.recipe_fields(sub, expected.recipe_key), **repro.rerun_launch_kwargs()}
