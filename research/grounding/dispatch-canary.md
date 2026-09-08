# Dispatch canary: what the worker's context holds

Grounds the stack fact PLAN §4 rests on — a dispatched worker's context holds nothing but the
nodes it is handed — against the installed toolchain, and states the limit of that grounding.

Probe: `research/grounding/probe_dispatch_canary.py`. Mechanism: `src/cairn/canary.py`.
Gate wiring: `src/cairn/dispatch.py` refuses a dispatch whose newest canary record is absent,
grounded on another SDK or CLI, or failed.

## Decision form

**VERIFIED-SOURCE**, installed `claude_agent_sdk` 0.2.152: the public stream exposes
initialization, assistant messages and results, not provider HTTP request bytes
(`research/grounding/dbos-sqlite-and-agent-sdk-isolation.md`). The request-bytes form is
therefore unavailable and every record on this toolchain names the **echo** form.

## The plantings and how each is decided

One distinct token per settings source, written into a scratch tree that the canary also makes
the process HOME and `CLAUDE_CONFIG_DIR` for the duration of the run:

| source | file | how its presence shows |
|---|---|---|
| project_instructions | `CLAUDE.md` | the worker follows the planted instruction and appends the token |
| user_instructions | `.claude/CLAUDE.md` | same |
| skill_file | `.claude/skills/canary-<token>/SKILL.md` | the token is the skill name, so it appears in the initialization message's `skills` and `slash_commands` |
| working_tree_status | `uncommitted-<token>.md` in a fresh `git init` tree | the worker echoes it if the working tree reaches context |

The run is decided on the initialization message plus the worker's reply, concatenated. A control
run repeats the dispatch with `setting_sources=["project", "local"]`, skills restored and the
`--bare` and `--disable-slash-commands` arguments dropped, so a source that shows in the control
and not in the dispatch is a suppressed source rather than an unreadable one.

## Result, 2026-09-08, SDK 0.2.152 / CLI 2.1.259

**VERIFIED-PROBE**, exit 0, `verdict: pass`:

```
verdict pass  reachable ['skill_file']  leaked []  handed_control_detected True
dispatch init:  skills [] · slash_commands [] · plugins [] · mcp_servers [] · tools [] · memory_paths None
dispatch reply: CAIRN-CANARY-CONTROL-e23384bd1b8c9b142125bb9b26ed7fe2
control init:   skills ['canary-CAIRN-CANARY-5b670b4fd656967e483638b7370a6ced', ...]
control memory_paths: {'auto': '.../cairn-canary-lb0se7m6/tree/.claude/projects/.../memory/'}
```

Artifacts: `/var/folders/8r/mztncc5x11x42rtx33pmqbww0000gp/T/cairn-canary-lb0se7m6` (`observed.txt`, `control.txt`, `substrate.sqlite`).

Three facts hold together. The handed control token comes back, so the detector sees what reaches
the worker. The skill planting reaches the control run's context and is absent from the dispatch
run's, on a field the CLI fills mechanically rather than one the model chooses. `memory_paths` is
populated in the control and `None` in the dispatch, so the settings layer the control enables is
the layer the dispatch envelope suppresses.

## The limit

**CONJECTURE**, the other three sources: no control run has shown the project instruction file, the
user instruction file or the working tree reaching a worker's context on this toolchain, so their
absence under the dispatch envelope is not evidence that the envelope suppressed them. The record
carries `reachable`, and a reader takes absence as meaningful only for the sources listed there.
The project instruction token was observed once under an earlier control that also loaded the
operator's user layer, and not since; a token that depends on the model choosing to obey a planted
instruction is a weaker channel than an initialization field, which is why the skill planting
carries the decision.

A pass says the dispatch path emitted no planted token on the decided channels at that toolchain.
It does not establish that the provider adds no context of its own, and an echo that omits a token
is a regression signal, not a proof.

**VERIFIED-PROBE**, refused form: a role template instructing the worker to return its context
verbatim is declined as an extraction attempt, and the reply carries no planted token for a reason
unrelated to isolation. A canary decided on that template reads as a pass while measuring nothing,
so the plantings are written as ordinary instructions and the skill name carries the token.

## Re-grounding

`canary.require_grounded` compares the newest record's `sdk_version` and `cli_version` against
`worker.SDK_VERSION` and `worker.CLI_VERSION`. A bump on either pin leaves the record stale and
every dispatch refuses until the probe runs again and records a pass, as a failed self-test yanks
a skill revision (PLAN §2).
