# CI profile and authority map

This profile describes two successful GitHub Actions runs and the source each run pinned. The baseline is run [35704472553](https://github.com/jwross24/cairn/actions/runs/35704472553), commit `5882af8d500e325da3a854606a2b49cdc38c14cc`. The profile run is [36524637482](https://github.com/jwross24/cairn/actions/runs/36524637482), commit `7882d17aaaaeff9a652b35092808e32ec53b5ce4`. Retained source JSON and logs, their digests, and exact extracted lines are in [evidence.md](evidence.md). The measurements describe those run artifacts, not another revision or host.

Confidence is high for the exact values those digest-verified artifacts report. Confidence in causal timing explanations or results on other hosts is low; the runs use different commits and do not control runner conditions.

## Lane results

The JSON job duration spans the complete GitHub job. The pytest duration and result counts come from that lane's single pytest summary. The workflow runs three container lanes on `ubuntu-24.04-arm` and five other lanes on `macos-latest`; pytest is invoked with `--durations=25` for the selected lane ([workflow](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/.github/workflows/ci.yml#L19-L26), [macOS matrix](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/.github/workflows/ci.yml#L90-L99), [check command](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/scripts/check.sh#L181-L188)).

| Lane | Result counts | Baseline pytest / job (s) | Profile pytest / job (s) |
|---|---|---:|---:|
| `python` | 4053 passed, 2 skipped, 163 deselected, 1 xfailed | 708.90 / 737 | 739.07 / 775 |
| `lean` | 113 passed, 2 skipped, 4104 deselected | 709.96 / 836 | 618.37 / 695 |
| `solution` | 18 passed, 4201 deselected | 371.68 / 476 | 198.97 / 302 |
| `solution-plan-exact` | 1 passed, 4218 deselected | 743.88 / 863 | 447.85 / 525 |
| `solution-plan-refusals` | 2 passed, 4217 deselected | 333.21 / 417 | 197.92 / 282 |
| `container` | 21 passed, 6 deselected | 700.49 / 951 | 726.86 / 780 |
| `container-replay-exact` | 2 passed, 25 deselected | 561.17 / 643 | 634.40 / 687 |
| `container-replay-refusals` | 4 passed, 23 deselected | 704.93 / 901 | 723.99 / 779 |

These runs do not establish a CI speedup. They are from different commits and are not a controlled comparison. The container pytest duration increased by 26.37 seconds while its job duration decreased by 171 seconds. The workflow's Linux prerequisite-install step took 227, 67, and 178 seconds in the baseline container jobs, and 33, 35, and 32 seconds in the profile jobs. That setup variation confounds job-wall comparisons; these observations do not establish its cause or predict quiet-host timings.

## Lane authority map

At the profile commit, [the lane manifest](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_ci_lanes.py#L6-L46) declares eight CI lanes. It routes all tests outside the explicit Lean, solution, and container manifests to `python`; container lanes collect only `test_container_statement_hash.py` ([routing rules](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_ci_lanes.py#L69-L119)).

| Lane | Selected authority exercised by this run |
|---|---|
| `python` | General test collection outside the explicit Lean, solution, and container manifests. The two external-skill checks were skipped, as described below. |
| `lean` | Lean/toolchain and related integration tests, plus two real-prelude solution checks: weaker-statement comparison and forged theorem rejection. The two gold-container probes were skipped on this lane. |
| `solution` | Solution build/compile integration cases not routed to `lean` or the ordered-plan lanes. |
| `solution-plan-exact` | The ordered-plan `exact` case; the full plan reaches fresh replay and comparison. |
| `solution-plan-refusals` | The ordered-plan `sorry` and `timeout` cases; the plan stops after a refusal or timeout and blocks later checks. |
| `container` | Linux container candidate compilation and axiom checks, cache/image checks, and other container statement-hash tests outside the replay/comparison subsets. |
| `container-replay-exact` | Linux fresh replay of `rfl` and exact closure comparison. The candidate compiles, passes the axiom scan, and is accepted by fresh `leanchecker`. |
| `container-replay-refusals` | Linux fresh replay of `sorry` and forged candidates, replay timeout checks, and weaker-statement comparison. Refusal remains tied to the axiom scan or fresh kernel replay. |

The concrete replay tests assert that `sorryAx` is refused before replay, a forged theorem is rejected by `leanchecker --fresh`, `rfl` is replayed, and timeout records preserve their stage and recheck project inputs ([container replay](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_container_statement_hash.py#L211-L278), [timeout checks](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_container_statement_hash.py#L364-L415)). Ordered-plan cases also test that a fresh replay or axiom refusal blocks later comparisons ([solution ordered plan](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_solution_build_compile.py#L509-L574)). These execution and refusal stages are authority checks, not disposable timing overhead.

## Slowest pytest phases

The ten longest recorded pytest phases in the profile run are below. `setup` and `call` are separate pytest measurements; their values are not job-wall time.

| Seconds | Lane | Phase and node | Authority exercised |
|---:|---|---|---|
| 366.97 | `container-replay-exact` | call `test_linux_candidate_fresh_replay[rfl]` | Fresh checker accepts the valid candidate. |
| 352.09 | `solution-plan-exact` | call `test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks[exact]` | Ordered plan reaches fresh replay and later comparison. |
| 284.68 | `container-replay-refusals` | call `test_linux_candidate_fresh_replay[forged]` | Fresh checker rejects the forged declaration. |
| 269.43 | `lean` | call `test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay` | Axiom scan passes, fresh replay rejects, later comparison is blocked. |
| 218.82 | `container-replay-refusals` | setup `test_linux_candidate_fresh_replay[sorry]` | Shared Linux candidate fixture preparation. |
| 203.08 | `container-replay-exact` | setup `test_linux_candidate_fresh_replay[rfl]` | Shared Linux candidate fixture preparation. |
| 116.00 | `container` | call `test_linux_candidate_axioms[rfl]` | Axiom scan accepts the valid candidate. |
| 111.63 | `container-replay-refusals` | call `test_linux_replay_timeouts_keep_their_stage_and_check_inputs` | Axiom/replay timeout stages and refusal after dependency mutation. |
| 102.61 | `container` | call `test_linux_candidate_axioms[sorry]` | Axiom scan rejects `sorryAx`. |
| 86.91 | `container` | setup `test_linux_dependency_cache_restores_without_provisioning` | Dependency/image fixture setup for the restoration test. Its call phase is 80.98 seconds. |

The first replay setup and cache-restore test identify a prerequisite-only reuse seam. The module fixtures build or resolve a pinned Linux image, prepare or restore package dependencies, make a private project copy, and then create a fresh candidate project ([fixture chain](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_container_statement_hash.py#L67-L78), [image/dependency/project fixtures](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_container_statement_hash.py#L541-L589)). The dependency key binds the actual image ID and identity, Lean pins, project files, and required modules; validation checks the package inventory/configuration and rejects overrides, and restore verifies the private copy ([cache key and validation](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_linux_dependencies.py#L35-L105), [restore](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_linux_dependencies.py#L171-L180), [cached image](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_linux_dependencies.py#L188-L207)).

**Candidate seam, CONJECTURE:** prerequisite reuse may be evaluated for the identity-pinned image and validated dependency-package snapshot, followed by a private restore and fresh candidate preparation. This profile contains no controlled measurement showing a benefit. It supports no reuse of `PreparedChallenge`, candidate output, axiom results, replay results, refusals, or verdicts. Fresh compilation, axiom checks, replay, and refusal behavior remain required for each candidate.

## Skips and xfail

The two Python skips are for live compliance-skill drift checks. The test searches repository, user Claude, and user Codex locations for `skills/beads-compliance-and-completion-verification/scripts/gather-evidence.sh`; when absent, its module-level `skipif` skips both checks ([producer predicate](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_audit_missing_items_drift.py#L10-L24)). Separate unit tests exercise and pin the frozen excerpt and metadata ([excerpt tests](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/unit/test_audit_missing_items_gatherer.py#L39-L120)). CI therefore does not validate drift in an external live skill.

The two Lean skips cover the gold-image Landlock and `chattr` probes. Their helper skips when `daemon_info` raises `DaemonUnavailable`; that exception represents either a missing Docker client or an unreachable daemon ([skip helper](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_lean_container.py#L25-L31), [daemon predicate](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/src/cairn/container.py#L138-L149)). The log does not distinguish those causes. Separately, the Linux container lane filter selects only `test_container_statement_hash.py`, so it does not exercise the Landlock or `chattr` tests in `test_lean_container.py` ([filter](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/_ci_lanes.py#L69-L76), [probes](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/integration/test_lean_container.py#L96-L103)). A skipped test is not a pass.

The one Python xfail is the planted-corpus bar check. The corpus producer has `CORPUS_COMPLETE = False`, with bars of 30 plantings and 4 positive controls; the test is strict-xfail until that flag changes ([bars](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/planted/_corpus.py#L25-L30), [strict xfail](https://github.com/jwross24/cairn/blob/7882d17aaaaeff9a652b35092808e32ec53b5ce4/tests/planted/test_corpus_rollup.py#L88-L100)). The xfail summary does not report actual planting or control counts.

## Reproduction and limits

The retained gzip files preserve the exact run JSON and full job logs. [The extractor](profile_ci.py) checks decompressed SHA-256 digests, run URLs/SHAs and successful conclusions; it requires exactly the eight declared lanes and one valid pytest summary per lane. It derives job wall time from JSON timestamps and emits the source lines used for summaries and duration phases. `--self-test` plants a missing lane and a malformed summary and verifies both are refused. No missing lane, count, or timing is filled with zero.

```bash
uv run python research/grounding/test-architecture-2026-09-29/profile_ci.py \
  --baseline-json research/grounding/test-architecture-2026-09-29/baseline-ci.json.gz \
  --baseline-log research/grounding/test-architecture-2026-09-29/baseline-ci.log.gz \
  --latest-json research/grounding/test-architecture-2026-09-29/latest-ci.json.gz \
  --latest-log research/grounding/test-architecture-2026-09-29/latest-ci.log.gz \
  --self-test
```

The lane counts and timings are observations about the two retained runs. They establish neither quiet-host timings nor CI speedup, and they do not describe another working-tree state. There are no measurements here for `container-plan-exact` or `container-plan-refusals`. This artifact is one bounded profiling slice, not closure of the full Cairn audit or any bead. It records no new ADR or design decision.
