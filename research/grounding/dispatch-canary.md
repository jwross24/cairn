# Dispatch canary: serialized worker context

Probe: `research/grounding/probe_dispatch_canary.py`. Mechanism: `src/cairn/canary.py`.
The probe checks four settings sources against the installed SDK and CLI. A pass covers their
absence from the captured dispatch requests; it does not establish that a provider adds no context.

## Decision form

The **request_bytes** form captures actual CLI HTTP request bodies at an ephemeral localhost
endpoint selected through `ClaudeAgentOptions.env`. It uses a dummy API key and returns a fixed
synthetic `LOCAL_CAPTURE_ONLY` response so the SDK can finish its turn. The response is not model
output and supplies none of the evidence. The endpoint retains bodies, not authorization headers.

The SDK's public message stream does not expose HTTP request bytes. Its supported
`ANTHROPIC_BASE_URL` routing permits this separate observation at the serialization boundary.
Initialization metadata is retained separately and never counted as a request-body token.
The substrate records the observations and their content hashes under **request_bytes**.

## Source attribution

HOME and the project directory are distinct siblings in a fresh scratch directory.
`CLAUDE_CONFIG_DIR` points to HOME's `.claude`. Making HOME equal to the project would let the
user planting double as a project instruction file and could not establish which source loaded it.

| Source | Planted location | Deciding channel |
|---|---|---|
| project_instructions | `<project>/CLAUDE.md` | request `messages` |
| user_instructions | `<home>/.claude/CLAUDE.md` | request `messages` |
| skill_file | `<project>/.claude/skills/canary-<token>/SKILL.md` | request `messages` |
| working_tree_status | `<project>/uncommitted-<token>.md`, in a fresh Git repository | request `messages` |

The dispatch arm uses `worker._options` with a local endpoint, dummy credential and loopback proxy
exclusions supplied for capture. The control enables `user`, `project` and `local` settings, restores skills and the Skill
tool, drops `--bare` and `--disable-slash-commands`, and uses the `claude_code` system-prompt preset
with the canary template appended. The handed-node token must appear in dispatch request bytes.

## Verified controls, 2026-09-29

**VERIFIED-PROBE**, SDK 0.2.152 / CLI 2.1.259. CLI SHA-256:
`884baa38fe1a624be25c4a91568bf5a08b5cf4e7d7acf29b7760e3525d964898`.

Two distinct seeds produced these request-body observations, with two requests per arm:

| Arm | Source tokens present |
|---|---|
| Dispatch envelope | none; handed-node token present |
| Project/local settings, custom system prompt | project_instructions |
| User/project/local settings, custom system prompt | project_instructions, user_instructions |
| User/project/local settings, preset and Skill tool | all four |

All four sources are **reachable**. No planting is retired. The isolated project/local control
excludes the user token, settling the home/project attribution. The full control also exposes the
skill token in initialization metadata; the request-byte finding stands independently of it.

Exploration artifacts reside under `/private/var/folders/wp/7c8dr9tn5t3fdj8wy07zrn4w0000gn/T/`:

- `cairn-canary-capture-fme_v280`, record hash
  `5a4e17deb9f131369aa875c83ea7aecf016aa9086a92f2e09bf8c1f9dff84cb3`.
- `cairn-canary-capture-0rxbhwn3`, record hash
  `0eca4b762af5e8374875aff3a93c70ea27447143cef5bb0ef758b8d0cc60a5cf`.

Each directory holds exact request bodies and hashes, separate init/result JSON, a script snapshot,
a summary and `substrate.sqlite`. Both stored records have `form: request_bytes`, `verdict: pass`,
all four sources reachable, no leaked tokens and a detected handed-node control.

The reusable probe's independent acceptance runs use seeds `lane4-parent-final-a` and
`lane4-parent-final-b`, exit 0. Their artifact directories under the same base are
`cairn-canary-_vjwlivj` and `cairn-canary-8bil44n4`. The source-file SHA-256 in both summaries is
`20876abcbeaf12fdae706734dd864313fe40e92a145678bf8b1c3f4b53129f6e`.

A planted dispatch with settings enabled writes a **failed** record with all four leaked tokens
and exits 2. Its artifact directory is `cairn-canary-2u_wnkxp`; `require_grounded` refuses it with:
`the newest dispatch canary failed; dispatches refuse until a fresh canary passes`.
Incomplete capture, an SDK error or partial control reachability retains diagnostics but writes
no grounding record. The probe's local HTTP and real-substrate tests exercise these refusals.

## Installed source explanation

**VERIFIED-SOURCE**, the hashed CLI above: `ZDt` at binary offset `0xaba4981` substitutes an empty
dynamic system context when `customSystemPrompt` is defined. It still loads enabled instruction
context through `FC`. The preset leaves the custom prompt undefined and reaches dynamic context
construction. `Rno` at `0x9bb523b` supplies Git status, subject to the nonremote and Git-instruction
settings checks; `Rle` is at `0x9bb4f79`. These branches explain the custom/preset control difference.

## Limits and re-grounding

This is evidence about the pinned CLI's serialized requests to the local endpoint. It does not
exercise a provider or prove that every possible ambient-context channel is absent. A model echo
that omits a token cannot establish its absence from a request.

The historical echo probe's 2026-09-08 result decided only `skill_file`. The 2026-09-29 live echo
attempt returned `Not logged in · Please run /login` in both arms and failed its handed-node
control. That result is an authentication hold, not evidence of isolation.

`canary.require_grounded` refuses absent, failed or stale records. Its SDK and CLI version checks
compare against `worker.SDK_VERSION` and `worker.CLI_VERSION`; changing either pin requires a fresh
passing record. The probe additionally requires control reachability for all four plantings.
