# Handoff: cairn lane PATH, stopped 2026-10-13 07:45 EDT

Written by the lane's second orchestrator (agent-mail `CloudyBear`, tmux `cairn--path2`, claude-opus-5-5).
The lane is stopped and complete for the night. A new session resumes from the owner's decisions,
not from work in flight.

## Goal

The owner asked for the shortest honest path from the cairn harness (six weeks built, never used end
to end) to a first research result, and to walk it: use the harness for real, decide what to build,
turn that into beads, and implement with a swarm. In his words: "be brave and truly push the
boundaries of mathematical harnesses". He wanted one small, real, pre-registered campaign that ran
through the gates and came out as a rendered report, with a control that must be kept and a planted
fake that must be rejected.

Orders: `/Users/jwross/.local/share/cairn-agent-mail/orders/CAIRN-PATH-2026-10-13.md` (phases 0 to 5),
`CAIRN-PATH-HANDOFF-2026-10-13.md` (phase 5), `SWARM-2026-10-13.md` (common rules). `AGENTS.md` is law.

## Status

**Finished.** `main` and `origin/main` at `915a34d`. Six beads closed on green CI, each with a re-run
by a different model family than its implementer:

| Bead | What | Source | Closing commit |
|---|---|---|---|
| `cairn-jqo6` | report renderer, `python -m cairn.report` | `6c286f6` + test fix `9d030a2` | `99e6fd3` |
| `cairn-8cqh` | hunt campaign runner, `python -m cairn.campaign` | `798ea2f` | `99e6fd3` |
| `cairn-jmv9` | slope-model evaluators, `src/cairn/slopemodel/` | `9eafd35` | `99e6fd3` |
| `cairn-r15n` | `cairn doctor` names a refused deployed bundle | `0ec2e85` | `99e6fd3` |
| `cairn-x05f` | distinguished-point rho baseline for the counted VM | `eabc7e6` | `0e27b47` |
| `cairn-qt89` | versioned sign instruction, reported meters with additive checks, curve-blind generator contract (scope ratified in agent-mail 788 only) | `89dfb20`, `8be2daf`, `9b97f06` | `0e27b47` |

Results (all AuditOnly and lane-opened; nothing closes `cairn-m1-cqt.10`):

- Two pre-registered hunt campaigns on the exact average-case weight W of the two-grumpy-giants
  schedule. W <= (5/4) l^1.5 survived 64 of 64 gate-drawn primes twice on disjoint draws; both
  controls survived; both planted fakes were killed at trial 0.
- W <= (121/100) l^1.5 on [2^21, 4194301] was **refuted** at l = 2249227 (n = 845, W = 4082843265).
- Pre-registered search over 6,448 k-giant schedules (k = 2, 3, 4): null. Best ratio to the reference
  0.9982 (the reference's own shape); gate to a held-out hunt was 0.99, so none was opened.
- Counted baseline: 133 of 133 launches verified from 28 to 60 bits; 1.23 and 1.13 sqrt(n) at 40 and
  50 bits; 3 of 3 at 60 bits with every default as shipped. macOS and Linux counts identical on 60 of
  60 paired launches.
- Negation-map walk on `signed/1`: 1.73 sqrt(n) at 30 bits, 34 of 40 answered at 40 bits. With 1,024
  step choices it equals the plain program on 10 held-out seeds (difference -0.06, se 0.40). The
  0.886 figure is not supported.

**Half done.**

- `cairn-05c4` (CI lane split, source `218d730`): code on `main`, CI run 38373313542 green 21 of 21,
  orchestrator review comment and `check` gate result recorded. Status `in_progress`. Only the close
  remains; see Next steps.

**Not started, by decision.** `cairn-fxu0`, `cairn-421p`, `cairn-glaz`, stage S4 of `cairn-m1-cqt.1.4`.
`cairn-5ncx` is with lane LAND (agent-mail `RubyStream`).

Every tmux session this lane created is closed except `cairn--path2`. No agent-mail reservation held.

## Decisions

- **The first result goes through the hunt gate, not the ladder.** The ladder cannot reach a verdict
  until stage S4 lands; `hunt.run_hunt` works today.
- **Counted object: additive form only.** A first draft that demoted the CPU and RSS predicates to
  "backstops" was killed by an adversarial review and a cross-family audit as a RULE 2 weakening and
  withdrawn. `MagentaSparrow` ratified only stricter-only parts (mail 788). The L1 bead was filed from
  the withdrawn text and rewritten before dispatch.
- **Sign instruction stays behind `signed/1`.** No ladder plan admits it. It is admissible only with a
  baseline that also uses it.
- **`cairn-fxu0` not landed overnight.** Its repair rewrites `tests/planted/family_epistemics.py` and
  every hunt test asserting `refuted`; it must land with `cairn-421p` or campaigns stop (plant ends
  INCOMPLETE, exit 2). `MagentaSparrow` agreed (mail 918).
- **`cairn-05c4` not closed.** A close is a tracker-only commit that the post-commit hook pushes; the
  night rules forbid pushing bookkeeping alone or while a `main` run is in progress.
- **Gate `check` reported with provider `ci`** citing the green run on the pushed commit, as was done
  for `cairn-m1-cqt.3.8`. `br close` refuses without it (`.beads/policy.yaml`, `allow_bypass: false`).
- **Evaluator A is pure Python**; numpy was not added. The evaluators refuse l above 2^22.
- **Campaign runner:** length-framed source digest; a question that ends INCOMPLETE exits 2.
- **Bead polish stopped at the second round**, the allowed bound.
- Ruled out: lower ladder floors (weakens the refutation floor); a larger counted BSGS table; a
  time-memory tradeoff BSGS; re-running either campaign on its substrate (a second draw is a re-roll).

## Dead ends

- **Running a lane's test file alone as verification.** `tests/unit/test_report_render.py` passed
  alone and failed in CI (run 38354036700): `cairn.log.configure` installs a process-wide stderr
  handler once any test calls `cli.main`. Always run a lane's tests after
  `tests/unit/test_canon.py`.
- **`br close` without a gate result** fails with exit 4, "requires gate 'check' to pass".
- **ARTIFACTS block keys other than `source|test|commit|command`** (`vectors:`, `fixture:`, `docs:`)
  are refused by `.githooks/pre-commit`.
- **Shell redirects to a `$VAR` path** are blocked by `dcg`; use literal paths.
- **`sleep N; cmd` in the foreground** is blocked; use a background until-loop.
- **Codex panes stall on "Selected model is at capacity"**; a one-line "continue" resumes them. Do not
  switch the lane's model.
- **A count-only VM launch is not a heavy run**; holding `/tmp/cairn-heavy.lock` for it blocks other
  lanes for no reason.
- **Generator contract checks curve fields by name only.** `bounds={"max_steps": <field prime>}`
  launches. Not a claimant path (the gate supplies bounds), but S4 must take bounds from the plan.
- An agent labeled a scratch sample STRONG-EMPIRICAL. No worker or orchestrator sets a calibration
  tag (RULE 2); record scratch counts untagged.

## Files

- `/Users/jwross/Documents/fleet-infra/data/cairn-path-20261013/DECISIONS.md`: bottom line (what ran,
  held, was null, is the owner's) and nine owner decisions with evidence. Read first.
- `/Users/jwross/Documents/fleet-infra/data/cairn-path-20261013/REAL-USE.md`: findings F1 to F23 with
  commands and numbers.
- `/Users/jwross/Documents/fleet-infra/data/cairn-path-20261013/PLAN.md`: state at stop, bead table,
  what the M1 exit still needs.
- `/Users/jwross/Documents/fleet-infra/docs/operator-queue.md`, section `## cairn`: the owner's queue.
- `/Users/jwross/brennerbot_sessions/cairn-path-20261013/`: durable evidence (`campaign/`,
  `replication/`, `leap/`, `h001-rerun/`, `x05f-rerun/`, `top60/`, `vm-parity/`,
  `path-h2-negation-investigation-0e27b47/`, `path-h2-fxu0-readiness-0e27b47/`, `orchestrator-checks/`).
- `/tmp/cairn-path-20261013/`: scratch; does not survive a reboot.
- `src/cairn/report.py`, `src/cairn/campaign.py`, `src/cairn/slopemodel/`,
  `src/cairn/countedvm/{vm.c,__init__.py,programs.py,signed_programs.py,meters.py}`,
  `src/cairn/doctor/detectors.py`: what the lanes built.
- `/Users/jwross/.local/share/cairn-agent-mail/orders/`: `LANE-PATH-{R,H2,H3,L2}-2026-10-13.md` (lane
  orders to model new ones on), `measure-2026-10-13.jsonl` (lane `PATH` stop line appended),
  `BACKLOG-2026-10-13.md`.
- Agent-mail (MCP `cairn-mail`, project_key `/Users/jwross/Documents/cairn`): mails 788 (ruling),
  809 and 813 (replication), 786 and 793 (leap search), 860, 880, 912, 914, 930 (final).

## Verification

- `gh run view 38373313542 --json conclusion` : `success`, 21 of 21 jobs, on `0e27b47`.
- `gh run list --branch main --limit 1` : run 38391430373 on `915a34d` was `queued` at stop; its
  result is unread.
- `uv run pytest -q --no-header tests/unit/test_canon.py tests/unit/test_report_render.py` :
  `55 passed` (was `7 failed, 48 passed` before `9d030a2`).
- `uv run pytest -q --no-header tests/unit/test_campaign_spec.py tests/integration/test_campaign_toy_conjecture.py` : `40 passed`.
- Slope-model test files (four) : `178 passed`.
- Counted-VM files for `cairn-qt89` after `test_canon.py`, calibration file excluded : `421 passed`.
- `uv run cairn doctor --json` on this checkout : exit 1, finding `D-bundle-plans/invalid` (expected:
  `deploy/` is stale).
- `uv run python -m cairn.report --db /Users/jwross/brennerbot_sessions/cairn-path-20261013/replication/dep-readcopy/substrate.sqlite --kind campaign --statement c18d6e23446fe5dc4d20321c396b88bd14d349632147894b327eeb1806b59271`
  : exit 2, `refused: missing skeptic_record` (expected); `--kind run` exits 0.
- `git status --short --branch` at 08:35 : `main...origin/main` in sync; `.beads/issues.jsonl`
  modified, the `cairn-4sio` row at 07:44, which is lane LAND's.

## Next steps

1. Read run 38391430373: `gh run view 38391430373 --json status,conclusion,jobs`. If red, mail
   `MagentaSparrow`; lane LAND owns the harvest stack.
2. Close `cairn-05c4` when a `main` run is `completed` and a code commit is going up anyway:
   `br close cairn-05c4 --reason "CI lane split on 218d730; CI run 38373313542 green 21/21 on 0e27b47; reviewed by CloudyBear"`,
   `br sync --flush-only`, then commit `.beads/issues.jsonl` under
   `lockf -k /tmp/cairn-commit.lock`. Its gate result and ARTIFACTS block are already recorded.
3. Put the nine decisions at the end of `DECISIONS.md` in front of the owner; nothing below starts
   without them.
4. On the owner's go for `cairn-fxu0`: implement it together with `cairn-421p`, from comment 599 on the
   bead (check in `hunt.py` as admission before any KILLED record; eleven tests and fixtures listed).
5. Stage S4 of `cairn-m1-cqt.1.4` (unblocked by mail 918): wire the counted VM into the ladder, the
   generator contract with bounds taken from the plan and fixed before the curve is drawn, the
   additive meters as predicates that can only add INCONCLUSIVE or REJECT. Then the calibration, once,
   under a new committed pre-registration with long samples on a quiet host.
6. `cairn-glaz` after the owner's pin decision.

## Open questions

- Which baseline does the ladder pin: the plain distinguished-point program (recommended) or a
  negation walk?
- The two corpus plantings of `cairn-m1-cqt.3.2` that design v2 made unconstructible in native form.
- Control (j): no negation-map method measured shows an advantage on the count; what replaces it?
- Name the first subproblem (recommendation: the exact constant of two grumpy giants first; the
  schedule search's next family as its own pre-registration).
- Go, or amend, on `cairn-fxu0`; and is the missing entropy commitment on a default hunt a defect?
- Re-pin the default deployment on this machine (`deploy/` dates from 2026-09-13).
- Park the 37 beads of `DECISIONS.md` section 5; close `cairn-4nzu`, `cairn-3g6j`, `cairn-2clw` as
  won't-fix or keep them.

## Standing instructions from the owner

- `AGENTS.md` RULE 2 is absolute: never soften a gate, the ladder, the verifier, the calibration
  taxonomy or what counts as proven. A proposal that touches them goes to the operator queue with a
  cross-family audit and is not built until ruled on.
- Everything a lane produces is AuditOnly: no KEEP, no PROVEN, no promotion.
- A new pre-registration is mailed before any search or hunt draws entropy; a run is never repeated
  until it passes; no timing measurement on a loaded host.
- A lane's report is a claim: re-run its commands before a close. Lanes never close their own beads.
- All work lands on `main`; stage exact paths only; every stage, commit and push goes through
  `lockf -k /tmp/cairn-commit.lock`; push only when the newest `main` run is `completed`; never push
  bookkeeping alone.
- At most 4 panes for this lane. Never touch a tmux session this lane did not create.
- Zero explanatory comments, American English, `uv` only, no scripts that rewrite source files.
- Nobody is at the keyboard overnight: never wait for a human reply; questions go to the bead's notes
  and to `MagentaSparrow`.
