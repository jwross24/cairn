# Handoff: lane NOTES, campaign 5 operator snags (2026-10-14 02:46 EDT)

## Goal

This is lane NOTES of the overnight swarm. Orders:
`/Users/jwross/.local/share/cairn-agent-mail/orders/CAIRN-NOTES-2026-10-14.md`, with the shared rules in
`CAIRN-DAY-2026-10-13.md` and `SWARM-2026-10-13.md` beside it. AGENTS.md is law.

The task is to fix the operator snags campaign 5 recorded in
`/Users/jwross/brennerbot_sessions/cairn-giants-20261013/campaign5/PRODUCT-NOTES.md`, on branch
`product-notes-20261014`, with nothing reaching `main`.

Scope: notes 4, 5, 6, 7, 9, 10, 11, 12, 13, 14 and 15. Notes 1, 2 and 3 are the owner's, and note 8
belongs to lane SKEPTIC: do not touch branch `draft/hunt-skeptic-20261013`.

Standing rules:

- Nobody is at the keyboard; never wait for a human reply.
- **Stop at 05:50 EDT, and start nothing new after 05:30.**
- No proof, no fix: a reproduction that exits 0 before any change, a failing test first, a planted
  negative, one commit per note.
- A change that makes a gate stricter is marked for the other model family's audit. A change that
  loosens or reinterprets a refusal is written up for the owner instead.
- A fresh subagent that did not write a change reviews it.
- At most one CI run on the macOS pool at a time.
- Register with agent-mail as ChartreuseGlen (MCP `cairn-mail`, project_key
  `/Users/jwross/Documents/cairn`, registration token in this session) and mail `MagentaSparrow` at
  pickup (sent, mail 1312) and at stop (**not yet sent**).

## Status

**Done and pushed** to `origin/product-notes-20261014`, base `3d3b891`:

- `f16a2f0`, note 12: `report --statement` given a claim id refuses and names the statement hash, and gains help text.
- `974a15c`, note 6: the `cairn --version` log record is DEBUG.
- `09da63e`, note 4: a skill-backed campaign refuses before any draw unless the verifier's
  `owner_grade` is Verifiable. **This is a STRICTER GATE and needs a different-family audit before it lands.**
- `e8c73cc`, note 15: docs on ranges touched by earlier runs.
- `a235cff` and `473dc0f`, note 5: a test pinning that a relative `"module_dir": "src"` is accepted from the checkout root, plus docs.

Every commit was reviewed by a fresh subagent. All came back CLEAN, except that the 5/15 review found
an overbroad docs sentence, which `473dc0f` fixed; its re-review was CLEAN.

**Verified already fixed on `main` by `f346b78`:** 7, 10 and 14 (rendering). Checked on a copy of the
campaign 5 substrate at `/private/tmp/cairn-notes-fMmzOy/c5/`.

**Owner's, written up:** 9 and 11. **Nothing to fix:** 13.

**Half done:**

- **Branch CI not yet run.** A background watch waits for `gh run list --limit 1` to read
  `completed` (SKEPTIC run 38517458602 was in progress at 01:55); it had not fired by 02:46. No
  `workflow_dispatch` has been sent for the branch.
- The `CI_PENDING` placeholder in the deliverable handoff is not yet filled.
- The stop mail to MagentaSparrow is not sent.

## Decisions

- **The work is in a fresh clone, not a worktree.** `/private/tmp/cairn-notes-fMmzOy/wt` was cloned
  from `git@github.com:jwross24/cairn.git`. In the main checkout, `git fetch`, `git worktree add` and
  `git worktree list` hang on iCloud-evicted files: `.git/worktrees/with/commondir` carries
  `hidden,compressed,dataless`, and `timeout 5 cat` on it exits 124. Reported in mail 1314. Do not
  prune; that is the owner's job.
- **The branch is based on pushed `3d3b891`, not local `main`.** Local `main` is 1 ahead with
  tracker-only `1aae09e`, which belongs to lane EXIT.
- **Note 12 keeps `--statement` hash-only.** The refusal points at the hash; no claim-id selection was added.
- **Note 4 is a preflight in `campaign.run_campaign`**, using the same `owner_grade` call the hunt
  uses. Programs without `skill`, and `--plan-only`, are unchanged.
- **Note 11 is not implemented.** Committing entropy on every hunt would loosen
  `small_numbers_floor.validate_protocol`. Executed both ways: `repro/note11_floor.py` shows the
  refusal today, and `repro/note11_counterfactual.py` shows the floor hunt accepted after the change.
- **Note 9 is the owner's.** The behavior is specified by PLAN §7, and changing it changes the semantics and hashes of hunt records.

## Dead ends

- `git worktree add` from `/Users/jwross/Documents/cairn` hangs because of the dataless files. Use the clone.
- The `dcg` guard blocks a shell redirect to a variable path (`> "$WT/x"`). Write literal paths.
- The fresh clone's pre-commit hook refuses without a bead DB until `br sync --import-only` runs in the clone. Done.

## Files

- `/Users/jwross/Documents/fleet-infra/data/cairn-notes-20261014/HANDOFF.md`: the lane deliverable,
  bottom line first, with per-note verdicts and the owner write-ups. Fill in `CI_PENDING`.
- `/Users/jwross/Documents/fleet-infra/data/cairn-notes-20261014/repro/`: reproduction scripts. Run each from the clone root.
- `/Users/jwross/Documents/fleet-infra/docs/operator-queue.md`: entry "2026-10-14 NOTES" under `## cairn`, uncommitted.
- In the clone:
  - `src/cairn/campaign.py`: `check_verifier_standing`.
  - `src/cairn/report.py`: `_statement`.
  - `src/cairn/cli.py`: `--version`.
  - `docs/development.md`: "Fresh campaign deployment" paragraphs.
  - Tests: `tests/integration/test_slope_weight_selftest.py`, `tests/unit/test_report_render.py`, `tests/unit/test_cli_contract.py`.
- `/Users/jwross/.local/share/cairn-agent-mail/orders/measure-2026-10-13.jsonl`: lane NOTES measurement lines.
- `/Users/jwross/Documents/cairn/.git/refs/heads/product-notes-20261014`: a stray local ref at
  `3d3b891`, left by the aborted worktree add. Harmless; not deleted (RULE 1).

## Verification

- `cd /private/tmp/cairn-notes-fMmzOy/wt && uv run pytest -q --no-header -p no:cacheprovider tests/integration/test_slope_weight_selftest.py tests/unit/test_campaign_spec.py tests/integration/test_giants_examples.py`
  Last result: 68 passed, before the note 5 test was added. The reviewers ran 52 passed and 3 passed on later subsets.
- `uv run pytest -q --no-header tests/unit/test_report_render.py`: 34 passed.
- `tests/unit/test_cli_contract.py`: 68 passed.
- `scripts/check.sh --fast --paths <changed paths>`: all gates pass for every commit.
- `ubs`: 0 critical.

## Next steps

1. Check that the pool is free:
   `cd /private/tmp/cairn-notes-fMmzOy/wt && timeout 60 gh run list --limit 1 --json status,databaseId,headBranch`.
   When it reads `completed`, dispatch once with `gh workflow run ci.yml --ref product-notes-20261014`.
   Watch with `gh run list --branch product-notes-20261014 --limit 1`. A red job caused by this branch is the next task.
2. Replace `CI_PENDING` in the fleet-infra HANDOFF.md with the run id, SHA `473dc0f` and the job results.
3. Before 05:50, mail `MagentaSparrow` a stop summary: per-note verdicts, branch tip `473dc0f`, the
   audit needed on `09da63e`, the owner items 9 and 11, the iCloud blocker, and the uncommitted
   operator-queue entry. Append a `stop` line for lane NOTES with SHA `473dc0f` to the measure file.
   Release reservations (none are held).

## Open questions

- **Owner:** run the different-family audit of `09da63e`, then land the branch. Accept the refusal of
  a skill spec with no plant?
- **Owner, note 11:** authorize "every hunt commits entropy; floor validation refuses any prior non-floor draw"?
- **Owner, note 9:** should survived trials be re-checked by the verifier? That would be a PLAN §7 change.
- **Owner:** fix the iCloud eviction under `cairn/.git` (keep Documents downloaded or move the repo), then `git worktree prune`.
