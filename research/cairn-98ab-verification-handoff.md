# cairn-98ab verification handoff

Status: implementation present, acceptance blocked, bead in progress. No Cairn commit or push from this session.

## Acceptance checkpoint, 2026-09-18

The complete local `scripts/check.sh` exits 0: 3,891 passed, three skipped, one expected failure, 23 warnings in 487.38 seconds. Log: `/tmp/cairn-98ab-work.acX1Nv/full-gate-repaired.log`. This does not establish the skipped lanes or pushed CI. Targeted probes confirm two skips because the Docker socket is absent and one because no framework-build interpreter is available. The expected failure is the existing incomplete-corpus check. No bead is closed at this checkpoint.

Independent review of `cairn-mlkn` finds no actionable defects. Its narrow tests pass, and missing mathlib raises the planted prerequisite assertion. The exact external GitHub predicate `cancelled()` has a spelling exemption; a real codespell invocation refuses the prose spelling without parentheses. A cold-cache GitHub run remains required evidence.

The operator approved exact/lower-bound/unknown accounting for `cairn-kjgf`, with trustworthy gate-owned counts distinct from child diagnostics and attempt success. Synthetic operation counts derived from elapsed time are excluded. Process-tree CPU enforcement is separate investigation `cairn-0zrz`. Accounting implementation follows the binding commit.

The final staged UBS scan covers ten Python files, exits 1, and reports eight critical and 32 warning items. Independent added-only review finds no actionable defect in the four additional criticals or seven additional warnings: fixed test nonces, literal SQL table names, checked-in JSON fixtures, in-memory bundle factories, and subprocesses bounded by pytest's mandatory timeout and session watchdog. The earlier 29 findings retain their separate triage below. Log: `/tmp/cairn-98ab-work.acX1Nv/ubs-staged.log`. No scanner suppression is used.

## Continuation, 2026-09-18

- Global UBS was repaired with official release v5.4.2. The installed runner's SHA-256 is `a8fc9672e4dcc479b295fbfd30d61797c6f1aaa35e2f352300f9aa5ef1bc8154`, verified against the release's SHA256SUMS. `ubs doctor --fix` exits 0 with all modules/helpers verified. A clean scanner probe exits 0; a planted unsafe-deserialization probe exits 1; both reports contain no failed modules. The altered runner is preserved at `/Users/jwross/.local/state/ubs/backups/20260918-cairn/ubs.previous`. Logs and the previous module cache are under `/tmp/cairn-ubs-official.5fyzDj`.
- The official Cairn scan completes with exit 1, four critical and 25 warning items. Independent Sol review finds 22 false positives and seven accurate parameter-count observations without a demonstrated defect. The criticals are deterministic test nonces and SQL identifiers derived only from literal dictionaries/module constants, with all data parameterized. No suppressions or cosmetic fixes were applied, and this is not described as a clean scanner pass.
- The complete unit lane passes: 2,418 passed, 16 temporary-directory cleanup warnings, exit 0. Log: `/tmp/cairn-98ab-work.acX1Nv/unit-blockers.log`.
- The Lean cache repair fetched 1,978 pinned artifacts. The exact real-mathlib test passes unchanged in purpose in 3.09 seconds. `cairn-mlkn` tracks CI prerequisite provisioning and missing-dependency refusal; `cairn-6odl` remains the separate blocked job-splitting task.
- `cairn-uz4g` owns the flaky universal timing assertion. Five real probes failed at load 4.43. Its test repair passes seven real integration tests and 19 ladder-engine unit tests. Two planted faults are refused, each exit 1: changing the strict CPU boundary and counting an over-budget trial as successful. Logs: `/tmp/cairn-98ab-work.acX1Nv/uz4g-*.log`.
- `cairn-kjgf` remains a separate accounting/design issue. A real post-exit CPU overage discarded a parsed count of 1,654,804 and stored 1,171,736. The operator approved exact/lower-bound/unknown observations. Evidence: `/tmp/cairn-kjgf.eyS2rk/diagnosis-and-design.md`. The test repair does not repair that defect or establish real-time CPU enforcement.

The sections below preserve the preceding handoff and its original blocker observations.

## Scope and behavior

Base revision: `1535f02e633fe5d92042e64e6d933aafc2c2bea0`.

Production ladder tables have immutable membership nodes mapping every claimant trial to its actual attempt. Justification reads the table's measured population for every member, including holdouts. Baseline, maker, replay and foreign attempts are excluded. Evidence binding validates the statement and producer, and mapped-table standing considers every member. SQL schema and table/trial canonical bytes are unchanged. Epistemic gates are unchanged.

Owned paths:

- `src/cairn/ladder.py`
- `src/cairn/laddertable.py`
- `src/cairn/justify.py`
- `tests/integration/test_justify_live_producers.py`
- `tests/unit/test_ladder_table.py`
- `research/decisions/adr-001-ladder-attempt-membership.md`
- This handoff
- Only the `cairn-98ab` row in `.beads/issues.jsonl`

Preexisting changes, preserved: the `cairn-xr2e` tracker row and untracked `.cass/`.

## Verification

- Original real-run reproduction exited 0 with four missing claimant bindings and justification selecting declared bits `[7,77]`. Script and database: `/tmp/cairn-98ab-repro.EmadIs/reproduce.py`, `/tmp/cairn-98ab-repro.EmadIs/run4`.
- The same defect assertion against the implementation exited 1: claimant lookups resolve, and justification selects measured bits `[28,30]`. Log: `/tmp/cairn-98ab-work.acX1Nv/reproduction-after.log`.
- The planted negative removes membership arguments from the production writer in an isolated process. The real integration assertion refuses the missing membership, exit 1. Log: `/tmp/cairn-98ab-work.acX1Nv/planted-missing-binding.log`.
- Full live-producer integration module: 22 passed, exit 0, reported by Sol/high test worker.
- Final `uv run pytest tests/unit/test_ladder_table.py -q`: 36 passed, 16 temporary-directory cleanup warnings, exit 0. Log: `/tmp/cairn-98ab-work.acX1Nv/laddertable-final.log`.
- `scripts/check.sh --fast`: all five gates passed, exit 0. Log: `/tmp/cairn-98ab-work.acX1Nv/fast-final.log`.
- Independent Sol/high review: no actionable source findings, HIGH confidence. Reviewer exercised seven focused cases, 18 legacy cases and the planted negative. These scoped runs are not whole-suite acceptance.
- `scripts/check.sh`: exit 1. Pytest's 180-second timeout terminated `test_the_real_prelude_compiles_in_the_gate_project_when_mathlib_is_present` while waiting for the real Lean build. The remaining suite was not run. Log: `/tmp/cairn-98ab-work.acX1Nv/full-gate.log`.
- A separate ladder sweep also reproduced the patience-ceiling test failure. A control loading the prechange ladder and ladder-table modules reproduced it, exit 1; this is not a whole-checkout baseline replay. Log: `/tmp/cairn-98ab-work.acX1Nv/baseline-patience.log`. Existing bead: `cairn-kjgf`. No timing constants were fitted.
- Required UBS scan: exit 2, Python module checksum mismatch. `ubs doctor --fix`: exit 2, 23 blocking issues, including unmatched release and main-fallback checksums. No checksum bypass. Logs: `/tmp/cairn-98ab-work.acX1Nv/ubs.log`, `/tmp/cairn-98ab-work.acX1Nv/ubs-doctor.log`.

## Local setup

Origin is `https://github.com/jwross24/cairn.git`, verified and fetched after user confirmation. Local main includes one restored commit beyond origin/main; no force operation is needed.

The virtual environment uses an editable installation plus a direct `site-packages/cairn` symlink to source because Python ignores hidden `.pth` files on macOS. Editable metadata and RECORD were verified: no package payload entries point through the symlink. The installed copy is preserved beside it. The process setting hidden flags remains unidentified. Ordinary `uv run` imports source and resolves Lean resources.

Approved persistent Codex configuration grants workspace-write access to five tool-data directories and command networking. Fresh sandbox probes passed CASS, CM, uv and HTTPS; Codex doctor had zero failed checks. A new session is required to inherit saved permissions. Protected settings and unrelated directories still require approval.

## Acceptance holds and next work

1. Repair UBS from a trustworthy, internally consistent distribution; do not accept mismatched downloads by replacing checksums.
2. Diagnose the real Lean build timeout and the existing `cairn-kjgf` patience failure without weakening gates. Temporary-directory cleanup warnings also remain observable.
3. Run the unchanged full gate to completion. Do not close on scoped or filtered evidence.
4. Stage only owned changes, excluding `cairn-xr2e`. Commit, attach exact artifact/source-SHA evidence, close only after acceptance, push and verify CI on the pushed SHA.

Terra/high implemented the main change; Sol/high completed negative coverage and a separate Sol/high independently reviewed it. Astra owns acceptance and leaves it blocked.
