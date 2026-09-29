# Linux prerequisite cache pilot observations

## Run identity and outcome

Baseline run `36536577420` completed successfully at source `bf8662704e1414e0d4f3a82200d660dacc231290`. Its profile classifies Linux prerequisite archive transport as `not-configured` for that pinned workflow.

Pilot run `36540366017` completed with overall conclusion `failure` at source `09a8a03852ca3473abaae0ce87c907b6aafdee82`. Its Python lane failed one unit test; each of the five Linux container lanes passed its own gate. The failed-run observation is retained at `pilot-runs/run-36540366017/failed-run-observation.json`. This is not a successful CI profile.

The Python summary reports 4,220 passed, 1 failed, 2 skipped, 181 deselected, and 1 xfailed in 943.60 seconds; 4,405 tests were collected and the job took 982 seconds. The failing node was `tests/unit/test_ci_lanes.py::test_every_direct_lean_import_has_one_explicit_lane_classification`. At `tests/unit/test_ci_lanes.py:432`, the import-set equality assertion found `tests/unit/test_linux_dependency_cache.py` in the observed direct Lean import set but absent from the expected classified set. The retained log has the node, assertion, extra path, traceback location, and summary source lines.

## Linux lane observations

The table reports the pytest summary's passed and deselected counts, pytest wall time, and job wall time. The baseline and pilot commits have different test source; these are per-run observations, not a speedup comparison. The pytest summaries reported only passed and deselected for these lanes; other counters remain separate in the JSON projection.

| Linux lane | Baseline passed / deselected | Baseline pytest / job seconds | Pilot passed / deselected | Pilot pytest / job seconds | Pilot prerequisite restore |
|---|---:|---:|---:|---:|---|
| `container` | 21 / 10 | 733.41 / 803 | 21 / 10 | 572.49 / 867 | miss |
| `container-replay-exact` | 2 / 29 | 634.15 / 679 | 2 / 29 | 451.34 / 661 | miss |
| `container-replay-refusals` | 4 / 27 | 697.27 / 778 | 4 / 27 | 562.42 / 764 | miss |
| `container-plan-exact` | 1 / 30 | 568.68 / 623 | 1 / 30 | 456.21 / 681 | miss |
| `container-plan-refusals` | 3 / 28 | 748.94 / 814 | 3 / 28 | 515.41 / 742 | miss |

All five Linux prerequisite restore steps logged `Cache not found for input keys` for the same key:

```text
cairn-linux-prerequisites-v1-Linux-ARM64-0fffe786376acbe9835c5694e81da4da419e88a7f45ed32e2ea0c54766943983-06b1b8e798d4c367a6ac2f86c947706001b499bbe38421acb9b8ca49104463e9
```

The import step was skipped in all five lanes after those misses. Preparation and gate step times were, in lane order from the table: `159 / 576`, `149 / 454`, `150 / 566`, `158 / 459`, and `158 / 519` seconds. Only the `container` lane ran archive export and save: export took 59 seconds and save took 17 seconds; the other four lanes skipped both steps.

The `container` log records `archive_published` for image `sha256:6d0f762647a8e2be1ff5c72927c8c3ff723592fde40ad7c5e3d52a610ba9bd18`. The save step then logged `Cache saved with key` for the same Linux prerequisite key shown above. The exact source lines are retained in the observation JSON and compressed run log. These findings concern the Linux prerequisite archive key; unrelated `setup-uv` cache hits also appear in the logs.

## Reproduction and refusal

From the repository root, the selected-field failed-run observation is regenerated with the read-only helpers in `pilot_profile.py`:

```bash
uv run python research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/extract_failed_observation.py > research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/failed-run-observation.json
```

The inputs are losslessly retained as `run.json.gz` and `run.log.gz`. Their compressed and decompressed SHA-256 values are in the observation JSON. The extractor pins both raw content digests, the run ID, source SHA, and helper SHA. Its output is an explicitly failed observation.

The normal successful-profile CLI refuses the same run:

```bash
uv run python research/grounding/test-architecture-2026-09-29/pilot_profile.py --run-json research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.json.gz --run-log research/grounding/test-architecture-2026-09-29/pilot-runs/run-36540366017/run.log.gz
```

It exits `2` with `{"status": "refused", "reason": "run failed: conclusion='failure'"}`. The failed run is not relabeled as green or passed to a successful profile.

## Warm-cache run

Run `36545011828` completed successfully at source `6452dbbeb7140cae1afc3318487f88d27ea46774`. The profiler accepted the terminal run, found the exact ten required lanes, and recorded every lane's reported passed, skipped, deselected, xfailed, xpassed, failed, error, warning, and collected counts. The full selected-field output and losslessly compressed inputs are retained under `pilot-runs/run-36545011828/`.

Each of the five Linux prerequisite restore steps reported a hit for the same key recorded by cold run `36540366017`:

```text
cairn-linux-prerequisites-v1-Linux-ARM64-0fffe786376acbe9835c5694e81da4da419e88a7f45ed32e2ea0c54766943983-06b1b8e798d4c367a6ac2f86c947706001b499bbe38421acb9b8ca49104463e9
```

All five import events reported image `sha256:6d0f762647a8e2be1ff5c72927c8c3ff723592fde40ad7c5e3d52a610ba9bd18`, the same image ID published by the cold `container` lane. Every import step succeeded; every prepare step was skipped. Warm export and save were skipped because this run consumed the restored archive.

The table compares one cold and one warm run. Prerequisite time is restore plus preparation for the cold run and restore plus import for the warm run. The deltas and percentages are `(warm - cold)` and `(warm - cold) / cold × 100`, rounded to one decimal. Linux counts were unchanged: each lane collected 31 tests, with zero skipped, failed, errored, xfailed, or xpassed; deselected tests are reported separately from passed tests.

| Linux lane | Passed / deselected | Prerequisite seconds, cold → warm | Job seconds, cold → warm | Gate seconds, cold → warm |
|---|---:|---:|---:|---:|
| `container` | 21 / 10 | 159 → 81 (−78, −49.1%) | 867 → 717 (−150, −17.3%) | 576 → 587 (+11, +1.9%) |
| `container-replay-exact` | 2 / 29 | 149 → 79 (−70, −47.0%) | 661 → 608 (−53, −8.0%) | 454 → 471 (+17, +3.7%) |
| `container-replay-refusals` | 4 / 27 | 150 → 89 (−61, −40.7%) | 764 → 788 (+24, +3.1%) | 566 → 636 (+70, +12.4%) |
| `container-plan-exact` | 1 / 30 | 158 → 76 (−82, −51.9%) | 681 → 585 (−96, −14.1%) | 459 → 464 (+5, +1.1%) |
| `container-plan-refusals` | 3 / 28 | 158 → 75 (−83, −52.5%) | 742 → 637 (−105, −14.2%) | 519 → 507 (−12, −2.3%) |

These are paired run observations, not causal estimates or an aggregate speedup. The raw counts and cache events are retained in the failed cold-run observation and successful warm profile. Between the cold and warm source SHAs, the Python-only `tests/unit/test_ci_lanes.py` classification gained the new dependency-cache unit-test path. The prerequisite helper, its unit test, `tests/integration/test_container_statement_hash.py`, `tests/_ci_lanes.py`, and `src/cairn/solutionchecks.py` have no source diff between those SHAs. The Linux gate test scope is therefore unchanged; the Python lane's test count is not used in this table.

`pilot-runs/run-36545011828/diagnostic-source.json.gz` retains the exact test JSONL text, content hashes, and upload artifact identities for the `rfl` and `forged` replay events. Both recorded argument vectors invoke `/usr/bin/docker run ... sha256:6d0f762647a8e2be1ff5c72927c8c3ff723592fde40ad7c5e3d52a610ba9bd18 lake +leanprover/lean4:v4.34.0-rc1 env leanchecker --fresh -v Solution.S_f4cd161738602628`; each contains exactly one `--fresh` invocation against the image published by the cold `container` lane.

For `rfl`, the fresh command returned `rc=0` and the event recorded `observed=replayed`, `reasons=[]`. For `forged`, it returned `rc=1`; the event recorded `observed=refused` and `kernel-rejected`, with the kernel reporting a declaration type mismatch. Their pytest call phases took 384.35 and 303.86 seconds; these are phase timings, not isolated checker costs. The profile's `--self-test` result also records refusal for a planted missing lane, malformed summary, nonterminal run, and failed run; those negatives use retained scratch copies.

From the repository root, the successful run profile and its self-test are reproduced with:

```bash
uv run python research/grounding/test-architecture-2026-09-29/pilot_profile.py --run-json research/grounding/test-architecture-2026-09-29/pilot-runs/run-36545011828/run.json.gz --run-log research/grounding/test-architecture-2026-09-29/pilot-runs/run-36545011828/run.log.gz --self-test
```

## Limits

The observations do not establish CI speedup, overall behavior beyond these recorded runs, full audit coverage, or skip-free non-Linux execution. The baseline has no Linux prerequisite archive transport. The cold pilot run remains an overall failed run because its Python lane failed the classification assertion described above; its five successful Linux lanes remain a separate failed-run observation, not a green profile. Warm-cache evidence consists of this single successful run and does not establish future cache behavior.

The local proof replay projection at `pilot-runs/local-fresh-proof.json` identifies its pilot commit separately from its initial runtime fingerprints and reviewed concurrent source diff. That local run does not claim that every runtime file at `09a8a03` was loaded during the proof.
