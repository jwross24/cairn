import asyncio
import importlib.metadata
from pathlib import Path

import claude_agent_sdk
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, ResultMessage, SystemMessage

SDK_VERSION = "0.2.152"
CLI_VERSION = "2.1.259"
TOOLS: frozenset[str] = frozenset()


def _check_version():
    version = importlib.metadata.version("claude-agent-sdk")
    if version != SDK_VERSION:
        raise ValueError(f"SDK {version} requires dispatch re-grounding; expected {SDK_VERSION}")


def _options(prepared, cwd):
    return ClaudeAgentOptions(
        system_prompt=prepared.template,
        tools=list(prepared.tools),
        allowed_tools=list(prepared.tools),
        skills=[],
        setting_sources=[],
        strict_mcp_config=True,
        mcp_servers={},
        cwd=cwd,
        cli_path=str(Path(claude_agent_sdk.__file__).parent / "_bundled" / "claude"),
        model=prepared.model,
        max_turns=prepared.max_turns,
        permission_mode="dontAsk",
        extra_args={"bare": None, "disable-slash-commands": None, "no-session-persistence": None},
        thinking={"type": "disabled"},
    )


async def _execute(prepared, cwd):
    _check_version()
    initialized = None
    finished = None
    async with asyncio.timeout(prepared.timeout_s):
        async with ClaudeSDKClient(options=_options(prepared, cwd)) as client:
            await client.query(prepared.prompt)
            async for message in client.receive_response():
                if isinstance(message, SystemMessage) and message.subtype == "init":
                    initialized = message.data
                    _validate_init(prepared, cwd, initialized)
                elif isinstance(message, ResultMessage):
                    finished = message
    return _result_payload(initialized, finished)


def _validate_init(prepared, cwd, initialized):
    if (
        initialized.get("claude_code_version") != CLI_VERSION
        or not isinstance(initialized.get("tools"), list)
        or set(initialized["tools"]) != set(prepared.tools)
        or initialized.get("skills") != []
        or initialized.get("plugins") != []
        or initialized.get("mcp_servers") != []
        or initialized.get("slash_commands") != []
        or initialized.get("memory_paths")
        or initialized.get("cwd") != str(cwd.resolve())
    ):
        raise ValueError("SDK initialization differs from the grounded dispatch configuration")


def _result_payload(initialized, finished):
    if initialized is None or finished is None:
        raise ValueError("SDK stream has no initialization or terminal result")
    if finished.session_id != initialized.get("session_id"):
        raise ValueError("SDK terminal result belongs to another session")
    return {
        "status": "success" if finished.subtype == "success" and not finished.is_error else "error",
        "text": finished.result or "",
        "session_id": finished.session_id,
        "observed_tools": tuple(initialized["tools"]),
        "observed_skills": tuple(initialized["skills"]),
        "observed_plugins": tuple(initialized["plugins"]),
        "cost_usd": None if finished.total_cost_usd is None else str(finished.total_cost_usd),
    }
