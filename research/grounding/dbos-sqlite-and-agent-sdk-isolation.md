# Grounding brief: DBOS-on-SQLite and Agent SDK subagent isolation

Sources: `dbos` 2.30.0 (PyPI 2026-08-18; tag 2.30.0 = `e0b742c2`; file:line at that tag); docs.dbos.dev and code.claude.com/docs (platform.claude.com 307-redirects there), fetched 2026-08-21; probes `scratchpad/grounding/dbos-sqlite-and-agent-sdk-isolation/probe*.py` (uv, Python 3.12).

## A. DBOS Transact (Python) on SQLite

**Step/workflow semantics.** PROVEN-in-source. Before a step runs, `check_operation_execution` selects `operation_outputs` by `(workflow_uuid, function_id)`; a row with matching `function_name` is returned without executing; a name mismatch raises `DBOSUnexpectedStepError` (`dbos/_sys_db.py:2914-2985`). After a step, one row is inserted: `workflow_uuid, function_id, function_name, started_at_epoch_ms, completed_at_epoch_ms, output|error, serialization, application_name`; a conflicting insert raises `DBOSWorkflowConflictIDError` (`_sys_db.py:2744-2782`). Step *inputs* are not recorded; workflow inputs are (`workflow_status.inputs`). Default serialization is base64(pickle) (`_serialization.py:112-113`). Docs: "Steps are tried _at least once_ but are never re-executed after they complete" (docs.dbos.dev/python/tutorials/workflow-tutorial).

**Tables (SQLite DDL).** PROVEN-in-source, `dbos/_migration.py:1208-1285` + `:1290-1360`: `workflow_status(workflow_uuid TEXT PK, status, name, inputs, output, error, executor_id, application_version, recovery_attempts, queue_name, timeout/deadline, deduplication_id, priority, created_at, updated_at, forked_from, parent_workflow_id, serialization, …)`; `operation_outputs(workflow_uuid, function_id, function_name, output, error, child_workflow_id, started/completed_at_epoch_ms, serialization; PK(workflow_uuid,function_id); FK→workflow_status ON DELETE CASCADE)`; plus notifications/events/streams/schedules/application_versions tables. Status values: `PENDING, SUCCESS, ERROR, MAX_RECOVERY_ATTEMPTS_EXCEEDED, ENQUEUED, DELAYED, CANCELLED` (docs.dbos.dev/explanations/system-tables).

**Idempotency-key rule.** Docs: "An assigned workflow ID acts as an idempotency key: if a workflow is called multiple times with the same ID, it executes only once." Source: `INSERT … ON CONFLICT(workflow_uuid) DO UPDATE` touching only `updated_at`/`executor_id`; stored `name`/`class_name`/`config_name` must match or `DBOSConflictingWorkflowError`; a different `queue_name` only warns; new inputs are ignored (`_sys_db.py:856-975`; probe confirmed).

**Resume when code changed.** PROVEN-in-source + STRONG-EMPIRICAL (probe2.py). Startup recovery selects `status=PENDING AND executor_id=… AND application_version == current` (`_sys_db.py:2216-2235`, `_dbos.py:663-676`). `application_version` = md5 over sorted `inspect.getsource` of *workflow* functions + dbos version + app name, unless `DBOS__APPVERSION`/config overrides (`_dbos.py:296-322`). After a mid-workflow `os._exit`:
- step *body* changed, names same → hash unchanged, workflow recovered, recorded output replayed (stale value, step not re-run);
- *workflow* body changed → new hash, "No workflows to recover", row stays `PENDING` (docs: "it only recovers workflows whose version matches"; fix via `DBOS.patch()`/fork/pinned version — docs.dbos.dev/python/tutorials/upgrading-workflows);
- recorded step renamed → `DBOSUnexpectedStepError: function s1 was recorded when s1_renamed was expected`, workflow `ERROR`.
Docs: "A breaking change to a workflow is any change in what steps run or the order in which steps run."

**SQLite status.** PROVEN. Default when no URL is given: `sqlite:///{app_name}.sqlite` (`_dbos_config.py:486-489`). Docs: "By default, DBOS uses SQLite." "SQLite is excellent for prototyping and testing because it requires no configuration or server." "it can't be used in a distributed setting"; "for production, we recommend using Postgres" (docs.dbos.dev/python/tutorials/database-connection). Engine: `isolation_level="IMMEDIATE"`, `busy_timeout=30000`, `foreign_keys=ON`, no WAL pragma (`_sys_db_sqlite.py:40-47`).

**Size/deps.** PROVEN (PyPI JSON, local install): wheel 268,218 B; hard deps `pyyaml, python-dateutil, psycopg[binary]>=3.1, websockets, click, sqlalchemy[asyncio]` (`pyproject.toml:8-15`) — psycopg required even on SQLite; fresh venv = 32 MB (psycopg_binary 17 MB, sqlalchemy 9.1 MB, dbos 1.3 MB). Extras: `otel`, `validation`, `aiosqlite`.

**Does a hand-rolled "tick table + idempotent steps" lose anything material?** CONJECTURE (judgment on the facts above). For a single-process orchestrator, no. DBOS's durable core is two tables plus (i) ordered `function_id` replay with a step-name check, (ii) workflow-ID upsert, (iii) version-gated recovery — each well under 50 lines. Forgone: queues/dedup/priority, durable sleep/events/streams, fork, patch tooling, admin server. Avoided: 32 MB incl. a Postgres driver, pickle default, versioning that ignores step bodies (stale outputs replay silently), mismatched rows stranded `PENDING` without alarm. Recommend: hand-roll (i)-(iii), copy the `operation_outputs` shape incl. the `function_name` check, hash step source into the tick record (Cairn's self-modifying workers need that either way).

## B. Claude Agent SDK subagents (code.claude.com/docs/en/agent-sdk/subagents; page cites Claude Code ≥ v2.1.235)

PROVEN-in-docs, verbatim:
- "each subagent runs in its own conversation, which starts fresh unless the subagent is a fork. Either way, intermediate tool calls and results stay inside the subagent; only its final message returns to the parent."
- "Unless the subagent is a fork, its context window starts fresh, with no parent conversation, but isn't empty. The only content you pass from parent to subagent is the Agent tool's prompt string".
- Receives: "Its own system prompt (`AgentDefinition.prompt`) and the Agent tool's prompt"; "Project CLAUDE.md (loaded via settingSources)"; "Tool definitions (inherited from parent or the subset in `tools`, filtered for background runs)". Does not receive: "The parent's conversation history or tool results"; "Preloaded skill content, unless listed in `AgentDefinition.skills`"; "The parent's system prompt".
- `tools`: "Array of allowed tool names. If omitted, inherits every tool available to subagents". `disallowedTools`: "Array of tool names to remove from the agent's tool set. MCP server-level patterns are also accepted". `maxTurns`: "Maximum number of agentic turns before the agent stops". "A tool you leave out isn't in the subagent's session at all" (Python dataclass: …/agent-sdk/python#agentdefinition).
- "The parent receives the subagent's final message as the Agent tool result, but may summarize it in its own response." "In v2.1.210 and later, Claude Code scans the final message for instruction-shaped patterns before the parent reads it… it never removes or rewords the subagent's text." (sub-agents page: "The scan doesn't judge whether content is malicious".)
- sub-agents page: "It doesn't see your conversation history, the skills you've already invoked, or the files Claude has already read." Startup context also includes every CLAUDE.md level and a git-status snapshot; from v2.1.198 subagents "run in the background by default" with a reduced built-in tool set.

**What "by construction" buys** (CONJECTURE for the advice): (1) context isolation holds — only `prompt` + the Agent-tool string (+ CLAUDE.md/skills/memory if enabled) reach the Skeptic. (2) As a *subagent*, the parent LLM composes that string, so statement-only is the parent's discipline; to make it structural, the Python orchestrator should call the Skeptic as its own top-level `query()` with the statement as `prompt`, `setting_sources=[]`, custom `system_prompt`. (3) Context isolation is not filesystem isolation: `Read`/`Bash` can open prover artifacts — whitelist `tools` (e.g., counterexample MCP only) and sandbox the cwd. (4) The scan neutralizes control-tag/turn-marker imitation only; not a content filter.

## C. Top-level dispatch probe, 2026-09-07

**STRONG-EMPIRICAL**, Python 3.14, `claude-agent-sdk==0.2.152`, bundled Claude Code
`2.1.259`, model `claude-haiku-4-5-20251001`. The project environment initially held
no agent SDK. The installed distribution supplies the CLI; no system CLI is selected.

The live probe uses `query()` with a fresh temporary working directory, a custom
`system_prompt`, `tools=[]`, `allowed_tools=[]`, `skills=[]`, `setting_sources=[]`,
`strict_mcp_config=True`, `mcp_servers={}`, `permission_mode="dontAsk"`, and one turn.
CLI arguments `--bare --disable-slash-commands --no-session-persistence` suppress
auto-memory, skill discovery, and persisted conversation state. Resume, continuation,
forking, plugins, additional directories, and parent-agent dispatch are absent.

The comparison without those three CLI flags reported 16 bundled skills and an
auto-memory path despite `skills=[]`. With the flags, initialization reports
`tools=[]`, `skills=[]`, `slash_commands=[]`, `plugins=[]`, `mcp_servers=[]`, and no
`memory_paths` field. The result is `success`, `num_turns=1`, with the exact echo
`CAIRN_DISPATCH_ECHO_738194`. Usage is 124 input tokens and 15 output tokens; the SDK
reports `$0.000199`. The session ID is `f36134b5-8a53-4063-8bd3-bd57efced9d9`.

Raw output, exit 0: `/private/tmp/cairn-session-b.b1cxUK/probe_bare.log`. The probe's template
is `Return exactly the user message, with no surrounding text.` and its prompt is
the echo token above. Authentication uses the process's existing API-key source;
bare mode does not load OAuth or keychain credentials.

**Verified source**, installed `claude_agent_sdk/_internal/transport/subprocess_cli.py`:
`_build_command()` serializes SDK configuration and `_apply_skills_defaults()`
preserves an explicit empty `setting_sources` list. `connect()` inherits process
environment variables except `CLAUDECODE`. The public `query()` stream exposes
initialization, assistant messages, and results, not provider HTTP request bytes.
Dispatch therefore records a prompt-bytes digest separately and leaves the provider
request-bytes digest absent with the reason `sdk-query-does-not-expose-provider-bytes`.
An SDK input digest is not a provider request digest.

The executable close check is:

```bash
uv run python tests/integration/test_worker_dispatch.py
```

**STRONG-EMPIRICAL**, the dispatch implementation creates one fresh `ClaudeSDKClient`
per invocation, calls its top-level `query()` once, consumes `receive_response()`, and
closes the client in its async context manager. No client is shared or resumed. Two
successive dispatches on 2026-09-07 returned the exact handed-node echo with distinct
session IDs `70cbd9ef-df00-4575-9fd2-7d5a62d51970` and
`26906e86-9f6b-4b4b-96ef-c0afdf00c628`; each reported `$0.00026`. A third dispatch
received cancellation and persisted `error`, `CancelledError`, and an unknown cost.
Raw output is `/private/tmp/cairn-session-b.b1cxUK/live_client.log`; the real substrate
is `/private/var/folders/8r/mztncc5x11x42rtx33pmqbww0000gp/T/cairn-live-dispatch-fyduap1r/substrate.sqlite`.

The supported tool registry is empty. A live `WebSearch` request in bare mode reported
an empty tool list, so a nonempty role allow-list is refused. `.6.3` owns the scoped
tool connection and its live grounding; none is claimed here. Initialization checks
also reject unexpected skills, plugins, MCP servers, memory paths, working directory,
or CLI version. These checks validate observed metadata, not an unseen provider request.

**Verified source**, `ClaudeSDKClient.__aenter__`, `connect`, `__aexit__`, and `disconnect`
own subprocess cleanup, including connection failures. The module-level `query()`
wrapper yields from an inner generator without forwarding early closure; a live
initialization refusal on that path produced an asynchronous-generator cleanup error.
The explicit client lifecycle is the dispatch path. A standalone raw-token client
probe returned a successful SDK result but did not echo the token; the close check
requires both SDK success and exact echo and does not treat that probe as a pass.

CI runs offline construction, real-substrate, and validation tests. The authenticated
live command above is a mandatory manual close gate with raw output and source SHA;
it is not a credential-dependent pytest skip. This execution split follows the
operator's delegated CI-key decision on 2026-09-07. `.6.4` owns the repeated leakage
canary and its execution policy on toolchain changes.

**CONJECTURE**, scope limit: these switches constrain Cairn's construction and the
reported SDK configuration. They do not establish the absence of every SDK-injected
instruction. The `.6.4` canary owns ambient-context leakage and re-grounding on an SDK
or CLI change. No research result or mathematical calibration follows from this probe.

## D. In-flight yank settlement ownership

**VERIFIED-PROBE**, 2026-09-08, Python 3.14 / SQLite 3.50.4: a real reserved
RUNNING attempt was passed through `yank.record`, closed as `SKILL_YANKED`, and
passed to `escrow.settle_on_close`. A temporary AFTER UPDATE trigger counted one
escrow update. The release owner was `disowned`; the close callback returned None
and preserved the reservation byte-for-byte. A forced second update raised
`escrow settles once: spent or released, never both, never twice`.
Artifact: `/private/var/folders/8r/mztncc5x11x42rtx33pmqbww0000gp/T/cairn-yank-grounding-u2147lp2/substrate.sqlite`.
The existing ordered callbacks do not reproduce a double settlement.

**DECISION**, `.4.3`: yank propagation owns release for a covering yank. A runner
closing `SKILL_YANKED` does not invoke a competing settlement path. Ordinary closes
retain `settle_on_close`; direct escrow writes retain the strict settle-once trigger.
The wait loop observes covering yank records and uses its process-group termination
path. The final close rechecks coverage inside its SQLite write transaction, so a
yank committed during receipt construction cannot produce an OK close. A yank
committed after that transaction disowns history without rewriting terminal status.
The integration test pins release ownership and exactly one update on the real database.

SQLite connections are thread-affine and the substrate admits one writer per process.
The in-flight integration uses a separate harness control process with its own
connection; the skill receives only its scratch path and test control flags. The
runner retains its original writer connection. `.4.3` does not make the multi-step
`yank.record` propagation atomic; crash recovery for that sequence belongs to `cairn-yp7`.

## OPEN
- Docs say `function_id` "starts from 0"; probe rows start at 1 for a top-level `start_workflow` — minor, not chased.
- TypeScript `AgentDefinition` page truncated in fetch; fields taken from the subagents table + Python reference.
- Whether `setting_sources=[]` suppresses `~/.claude/CLAUDE.md` for subagents was not probed.
