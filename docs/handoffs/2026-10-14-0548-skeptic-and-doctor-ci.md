# Handoff: lane SKEPTIC, cairn-glaz Skeptic branch and the doctor/CI branch

## Goal

Lane SKEPTIC (agent-mail name `SapphireBadger`, orchestrator `MagentaSparrow`) finishes `cairn-glaz`, the hunt Skeptic the M1 milestone `cairn-m1-cqt.10` needs. The work runs on draft branches; nothing reaches `main` from this lane. A second order (`/Users/jwross/.local/share/cairn-agent-mail/orders/CAIRN-SKEPTIC-NEXT-0320.md`) adds two items on branch `fix-doctor-ci-20261014`: fix `cairn-p8lb`, and diagnose the `test_counted_vm` CI timeout.

Standing instructions:
- Read `AGENTS.md` first; it is law.
- Nobody is at the keyboard; never wait on a human. Mail `MagentaSparrow` (MCP server `cairn-mail`, project_key `/Users/jwross/Documents/cairn`) at pickup, at results, and at stop.
- Never read or print a provider key. Paid calls are done for this lane; the key stays with the orchestrator.
- Stage exact paths only. No reset, clean, stash or force. Never weaken a test or gate, and never change timeouts or CI budgets (those are the owner's, under `cairn-1qx8`).
- Reproduce before fixing, show a planted negative, and have each change read by a fresh subagent that did not write it.
- Run one CI run at a time on the macOS pool.
- At 05:00 EDT the orchestrator ordered a full stop for the weekly usage cap until the 06:00 reset. Start nothing new until it says otherwise.

## Status

Finished and pushed:
- **`draft/hunt-skeptic-20261013`**, worktree `/private/tmp/cairn-skeptic-20261013`, tip `b5ce449dedb647e9fe28022f5cd829602055292a`.
  - Codex audit verdict: LAND AFTER FIXES. `b5ce449` is the required repair (finding 1).
  - Branch CI run 38530112506 on `b5ce449`: 21/21 success.
  - Mailed `MagentaSparrow` for the same auditor's re-audit (mail 1340).
  - Paid pilot already passed on `cf8d696` ($1.04; the Skeptic flagged the planted defect `issue`).
- **`fix-doctor-ci-20261014`**, worktree `/private/tmp/cairn-fix-doctor-20261014`, from `main` `3d3b891`, pushed:
  - `3fb527d` fixes `cairn-p8lb` (doctor read git HEAD as `nogit` in a linked worktree).
  - `6e3208f` moves `from cairn import runner` into `countedvm.launch()`. The `--input` path no longer loads the runner stack, and `test_every_pair_of_points_adds_like_pari` drops from 60.71 s to 31.10 s locally. No assertion or timeout changed.
  - Both changes had a fresh-subagent review. The first reviewer found a raise on damaged `.git` files, which `3fb527d` covers. The second found no defect.
- **Bead comments:**
  - On `cairn-glaz`: three comments with state.
  - On `cairn-p8lb`: the fix note.
  - On `cairn-1qx8`: timeout evidence plus the diagnosis ("slow, not waiting": 784 interpreter spawns, 61 ms of each in imports).

Half done:
- **CI run 38535810922** on `fix-doctor-ci-20261014` `6e3208f` was 8/21 green, 0 failed, at the 05:00 stop. Its result is unread.

Not started or not mine:
- Owner decisions listed under Open questions.

Uncommitted in the main tree `/Users/jwross/Documents/cairn`:
- `.beads/issues.jsonl` (the bead comments, flushed with `br sync --flush-only`) is for the next lane's push. Do not commit it from this lane alone.
- `docs/handoffs/` and `lean/Grounding/*.lean` belong to other lanes.

## Decisions

- **SDK pin `claude-agent-sdk==0.2.158`** (bundled CLI 2.1.280, read from each verified sdist): the provider refused CLI 2.1.259 for `claude-opus-5-5`. 0.2.157 bundles 2.1.277, which is below the provider's 2.1.280 minimum.
- **Built-in plugins off:** `worker.BUILTIN_PLUGINS_OFF` passes `--settings {"enabledPlugins":{"agents-md@builtin":false,"telemetry@builtin":false}}`.
  - Why: CLI 2.1.280 loads those built-ins even under `--bare`, so the worker init check (which requires no plugins) refused every scoped dispatch.
  - The init check itself is unchanged. It expects the exact MCP entry `{"name":"cairn_skeptic","source":"sdk","status":"connected"}`.
  - The canary re-grounded on this envelope.
- **Orchestrator rulings on the owner's delegation:**
  - `max_turns` 64 (`4ae7df2`; bundle hash `1cb811a5c66168a10608956a95f3fbe03e4c9661a41dde943d9386bf45f611a5`).
  - `timeout_s` 600.
  - Effort unpinned (the CLI sends `medium`).
- **Audit finding 2 deliberately left unchanged:** one malformed successful Skeptic reply blocks every report for that statement, permanently. That is the owner's call.
- **The counted-VM timeout itself and the 784-spawn test shape stay with `cairn-1qx8`.** Changing either is an owner budget decision.

## Dead ends

- **`br` in a linked worktree resolves to the main tree's database**, so `br sync --import-only` there does nothing useful. The pre-commit gate then refuses with `[doctor-gate] no bead database to inspect`. Build the worktree's own database instead: `br --db <worktree>/.beads/beads.db sync --import-only`.
- **Tests cannot spawn `git` directly** (conftest allow-list: `IsolationViolation: subprocess outside the allow-list: /usr/bin/git`). Use the python-child `GIT_RUNNER` pattern, as `tests/integration/test_closing_commit_cli.py` does.
- **zsh does not word-split `$E="env -i ..."`;** write the `env -i ...` prefix out literally.
- **dcg blocks `>` redirects to variable paths;** use literal paths or `>>`.

## Files

- `/Users/jwross/Documents/fleet-infra/data/cairn-skeptic-20261013/HANDOFF.md`: full lane handoff (pilot table, rulings, owner commands, CI history).
- `/Users/jwross/Documents/fleet-infra/data/cairn-skeptic-20261013/AUDIT-REQUEST.md`: what the auditor attacks first (SDK move, plugin switch-off, 64 turns).
- `/Users/jwross/Documents/fleet-infra/data/cairn-skeptic-20261013/AUDIT-codex.md`: the Codex audit report.
- `/Users/jwross/Documents/fleet-infra/data/cairn-skeptic-20261013/run_skeptic_pilot.py`: the one-command pilot. Its default `--dep` is `/private/tmp/cairn-skeptic-rehearsal-turns64-20261014/dep`.
- `/Users/jwross/Documents/fleet-infra/data/cairn-skeptic-20261013/sdk-0158-regrounding/`: canary, plugin and AGENTS.md probe evidence.
- `/private/tmp/cairn-skeptic-20261013/src/cairn/dispatch.py`: dispatch, typed record, `python -m cairn.dispatch`, and the `b5ce449` repair.
- `/private/tmp/cairn-skeptic-20261013/src/cairn/worker.py`: SDK pin constants and the built-in plugin setting.
- `/private/tmp/cairn-fix-doctor-20261014/src/cairn/doctor/artifacts.py`: the `git_head` fix.
- `/private/tmp/cairn-fix-doctor-20261014/src/cairn/countedvm/__init__.py`: the lazy runner import.
- `/private/tmp/cairn-skeptic-lane.g4uWeW/`: raw test, mutant, CI and commit-message outputs.

## Verification

- **Doctor branch CI, unread:** `gh run view 38535810922 --json status,conclusion,jobs --jq '{status,conclusion,failed:[.jobs[]|select(.conclusion=="failure")|.name]}'`. Last seen 8/21 success, 0 failed.
- **Pair-test CI duration** (the measurement for `cairn-1qx8`): `gh run view 38535810922 --log` on the `check (python-integration)` job, grep `test_every_pair_of_points_adds_like_pari`. Earlier passing CI durations were 103.07 s and 138.19 s.
- **Skeptic branch CI:** `gh run view 38530112506`. Result: success 21/21 on `b5ce449`.
- **Local doctor tests:** `cd /private/tmp/cairn-fix-doctor-20261014 && uv run pytest -q --no-header -p no:cacheprovider tests/integration/test_doctor.py`. Result: 135 passed.

## Next steps

1. After the 06:00 reset, and only if `MagentaSparrow` says to resume, read CI run 38535810922 with the command above. If `python-integration` passed, note the pair test's CI duration. If it failed, read the failing test before anything else.
2. Mail `MagentaSparrow` the stop summary:
   - branch `fix-doctor-ci-20261014`, commits `3fb527d` and `6e3208f`, the run id, its result and the pair-test duration;
   - add the duration to `cairn-1qx8` with `br comments add cairn-1qx8 "$(cat <file>)"`, written through a file.
3. Wait for the Codex re-audit verdict on `b5ce449` and act only on what it requires. Leave `draft/hunt-skeptic-20261013` otherwise untouched.

## Open questions

- **A survived statement never reaches a terminal status.** Its campaign report always refuses `statement not terminal`. Does the owner want a terminal path (`withdrawn`/`promoted`) for survived hunts?
- **Malformed-reply report poisoning** (audit finding 2): keep it permanent, or let a later valid audit restore reports?
- **Effort pin for the Skeptic role:** the CLI sends `medium`.
- **The `test_counted_vm` 180 s timeout and its 784-spawn shape** (`cairn-1qx8`).
- **When the bundle pin and deployment move to the audited branch:** that is the owner's step, using the commands in the lane HANDOFF.md.
