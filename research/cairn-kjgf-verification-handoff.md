# cairn-kjgf verification handoff

Status: implementation reviewed and frozen; full local gate passed, pushed CI pending. Base revision: `d722b72575be49372a8acc3b26d44c332670b6f6`.

## Behavior

Trusted operation observations are exact, lower-bound, or unknown. Unknown is absent, never zero. Child reports remain diagnostic. Complete post-exit-overage output is retained without successful status. Counting precedes shared rung aggregation and replay. Lower-bound means round downward; exact statistics retain their rounding.

Fit rungs persist three arms; hold-out rungs persist the claimant alone. Immutable membership covers the expected topology, while evidence and recomputation authors remain claimant-only. Paired speedup intervals require the entire successful, exact, matching pair set, not a selected subset.

Bounds can support explicit floors and sound one-sided count divergence. They cannot establish model miss from the existing design-radius field: fitted, sampling-error-widened bands belong to `cairn-m1-cqt.1.8` and `cairn-m1-cqt.1.9`. Independent verifier-supported recovery failures can reject even with unknown operations. No failed claimant can promote.

Old ladder schemas are refused without automatic mutation. No databases are migrated or deleted. Production counted-object work remains `cairn-p3vy` and `cairn-m1-cqt.1.4`; true CPU enforcement remains `cairn-0zrz`. Test counter injection establishes accounting behavior, not production instrumentation.

## Evidence

- The real captured overage reported 1,654,804 operations but persisted the synthetic 1,171,736. Original reachable proof: `/tmp/cairn-kjgf.eyS2rk/production-bound.log`, `production/`, and `verify_reproduction.py`.
- Conversion replay through `ladder.run_arm`, reconstructed receipt/output, and the real pinned verifier exits 0: status remains `BUDGET_EXCEEDED`, output is complete/recovered, reported count is 1,654,804, and gate count is unknown/None. Command: `uv run python /tmp/cairn-kjgf-post-exit.3T4Kel/replay_post_exit.py`. The same script with `old-defect` exits 1 on the obsolete synthetic-count assertion. This is captured-artifact conversion replay, not a fresh production run or observed gate count.
- Focused unit modules: 67 passed, exit 0. `/tmp/cairn-kjgf-implementation.OCl7a1/unit-focused-post-rounding-final.log` supersedes the earlier red fixture run.
- Focused integration/substrate selection: 241 passed. Related factory selection: 72 passed. Membership/evidence final selection: two passed. Logs are in `/tmp/cairn-kjgf-implementation.OCl7a1/`.
- Scoped fast gate: all five gates pass, exit 0; test execution is explicitly excluded by fast mode. Log: `/tmp/cairn-kjgf-implementation.OCl7a1/scoped-fast-post-rounding-final.log`.
- Independent review: 17 focused checks passed; five post-repair checks passed. Independent probes exit 0. Evidence index: `/tmp/cairn-kjgf-independent.5WJEon/evidence-index.md`, SHA-256 `d425285c10a581435055dbe8dc0d17d587a8c9a768a1b544c7fa3a5650c57363`.
- Old-schema fixture uses exact `d722b72` schema bytes. Current open raises `SchemaMismatch`; database SHA-256 and sqlite_master digest are identical before/after, with no WAL/SHM sidecars. Exact hashes are in the independent evidence index.

## Planted refusals

The original upward-rounding defect predicate exits 0 before repair and 1 afterward: lower observations `[0,1,1]` produce `0.666666`, not the overstated `0.666667`.

Scratch-only mutations cause their intended assertions to fail: synthetic counts for failed attempts; post-hoc counters leaving stale statistics; report-derived CI with unknown baseline; canonical unknown coerced to zero; controls omitted from recomputation; failed baseline admitted to paired CI; lower bounds admitted to model-miss rejection; and failed-trial protection bypassed. Artifacts: `/tmp/cairn-kjgf-post-exit.3T4Kel/` and `/tmp/cairn-kjgf-independent.5WJEon/`. No source mutation remains in the checkout.

## Scanner and limits

Official UBS v5.4.2 scan exits 1: 11 Python files, 14 critical, 47 warning, 270 informational findings. Independent triage classifies 48 false positives and 13 parameter-count style observations, with no actionable defect or unresolved finding. This is a completed, triaged scan, not an exit-0 scan. No suppression or cosmetic refactor was applied. Log: `/tmp/cairn-accounting-acceptance.E0f5PT/ubs.log`.

A constructed public-aggregation input can contain duplicate trial slots. The production runner generates the exact grid; no producer of duplicate rows was found. The reviewer reports this as a LOW boundary-only observation, not a demonstrated production defect. No hardening fix is claimed.

Full gate: exit 0, 3,901 passed, three skipped, one expected failure, 99 temporary-directory cleanup warnings in 467.01 seconds. Log: `/tmp/cairn-accounting-acceptance.E0f5PT/full-gate.log`. Skipped and expected-failure lanes are not established. No bead close is authorized by this checkpoint.
