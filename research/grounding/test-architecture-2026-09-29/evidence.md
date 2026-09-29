# Retained CI run evidence

The compressed inputs preserve the exact GitHub Actions run JSON and job logs used by the profile. The extractor hashes their decompressed bytes before parsing them.

| Run | Source | Commit | JSON SHA-256 | Log SHA-256 | Compressed JSON | Compressed log |
|---|---|---|---|---|---:|---:|
| Baseline, run 35704472553 | [GitHub Actions run](https://github.com/jwross24/cairn/actions/runs/35704472553) | `5882af8d500e325da3a854606a2b49cdc38c14cc` | `a0475687fa620bb89a21a3172f6745da77240b1d711f5abc0d5a5765b1c806c1` | `fb424b9170121e6e337fa129f04d65e7b472f9d948c183c4cc4e5ee1a7264fca` | 2.5 KB | 249 KB |
| Profile, run 36524637482 | [GitHub Actions run](https://github.com/jwross24/cairn/actions/runs/36524637482) | `7882d17aaaaeff9a652b35092808e32ec53b5ce4` | `55886954457d365873c24a521f91fffdb2645be727ff4fd941355c84c638bafb` | `4ad3251cb00b9465f0f66da3d16b9b9cba1139cae8292b7deaf684e33421c7c3` | 2.4 KB | 255 KB |

The digests above cover the original uncompressed bytes. The retained gzip files also have these archive digests:

| File | Compressed SHA-256 |
|---|---|
| `baseline-ci.json.gz` | `62995a558f054281a461735139e3c11df19fdc17aa5bcc28cb4c93eb7246c9eb` |
| `baseline-ci.log.gz` | `bdf1eceb7c89c3f9653aea547bba1ace196a5d31195dd4491ad118c37a4cd753` |
| `latest-ci.json.gz` | `bfb5de984ae01a60002b507b35e2591c0a414cc0d9fa15db92a322edaf341596` |
| `latest-ci.log.gz` | `b82cfe968dcdd12617a92b2c19cb4762d1c8438c24466a7f44bb9ca75ba447a5` |

The extractor ran against the retained gzip files with exit code `0`:

```bash
uv run python research/grounding/test-architecture-2026-09-29/profile_ci.py --baseline-json research/grounding/test-architecture-2026-09-29/baseline-ci.json.gz --baseline-log research/grounding/test-architecture-2026-09-29/baseline-ci.log.gz --latest-json research/grounding/test-architecture-2026-09-29/latest-ci.json.gz --latest-log research/grounding/test-architecture-2026-09-29/latest-ci.log.gz --self-test
```

The positive output contains one exact pytest summary source line for every lane and the ten duration source lines that follow. The planted refusals returned:

```json
{
  "missing_lane_refused": "lane set mismatch; missing=['container'], extra=[]",
  "malformed_summary_refused": "expected one pytest summary for lane container; found 0"
}
```

## Pytest summary lines

These lines are copied from the retained job logs. The baseline log reports `UNKNOWN STEP`; the profile log records the gate step name.

```text
check (python)	UNKNOWN STEP	2026-09-22T08:35:02.7101720Z ==== 4053 passed, 2 skipped, 163 deselected, 1 xfailed in 708.90s (0:11:48) ====
check (lean)	UNKNOWN STEP	2026-09-22T08:36:41.8375780Z ========= 113 passed, 2 skipped, 4104 deselected in 709.96s (0:11:49) ==========
check (solution)	UNKNOWN STEP	2026-09-22T08:30:37.8416380Z =============== 18 passed, 4201 deselected in 371.68s (0:06:11) ================
check (solution-plan-exact)	UNKNOWN STEP	2026-09-22T08:37:01.4845640Z ================ 1 passed, 4218 deselected in 743.88s (0:12:23) ================
check (solution-plan-refusals)	UNKNOWN STEP	2026-09-22T08:29:41.0374080Z ================ 2 passed, 4217 deselected in 333.21s (0:05:33) ================
check (container)	UNKNOWN STEP	2026-09-22T08:38:37.8757665Z ================= 21 passed, 6 deselected in 700.49s (0:11:40) =================
check (container-replay-exact)	UNKNOWN STEP	2026-09-22T08:33:33.2320482Z ================= 2 passed, 25 deselected in 561.17s (0:09:21) =================
check (container-replay-refusals)	UNKNOWN STEP	2026-09-22T08:37:49.5106294Z ================= 4 passed, 23 deselected in 704.93s (0:11:44) =================
check (python)	Gates	2026-09-29T05:19:38.5210040Z ==== 4053 passed, 2 skipped, 163 deselected, 1 xfailed in 739.07s (0:12:19) ====
check (lean)	Gates	2026-09-29T05:18:19.1066670Z ========= 113 passed, 2 skipped, 4104 deselected in 618.37s (0:10:18) ==========
check (solution)	Gates	2026-09-29T05:11:43.6050460Z =============== 18 passed, 4201 deselected in 198.97s (0:03:18) ================
check (solution-plan-exact)	Gates	2026-09-29T05:15:29.9496880Z ================ 1 passed, 4218 deselected in 447.85s (0:07:27) ================
check (solution-plan-refusals)	Gates	2026-09-29T05:11:11.0293570Z ================ 2 passed, 4217 deselected in 197.92s (0:03:17) ================
check (container)	Linux container gates	2026-09-29T05:19:48.3688804Z ================= 21 passed, 6 deselected in 726.86s (0:12:06) =================
check (container-replay-exact)	Linux container gates	2026-09-29T05:18:13.3225299Z ================= 2 passed, 25 deselected in 634.40s (0:10:34) =================
check (container-replay-refusals)	Linux container gates	2026-09-29T05:19:45.3201404Z ================= 4 passed, 23 deselected in 723.99s (0:12:03) =================
```

## Ten slowest pytest phases in run 36524637482

```text
check (container-replay-exact)	Linux container gates	2026-09-29T05:18:13.3221121Z 366.97s call     tests/integration/test_container_statement_hash.py::test_linux_candidate_fresh_replay[rfl]
check (solution-plan-exact)	Gates	2026-09-29T05:15:29.9327860Z 352.09s call     tests/integration/test_solution_build_compile.py::test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks[exact]
check (container-replay-refusals)	Linux container gates	2026-09-29T05:19:45.3193506Z 284.68s call     tests/integration/test_container_statement_hash.py::test_linux_candidate_fresh_replay[forged]
check (lean)	Gates	2026-09-29T05:18:19.0983200Z 269.43s call     tests/integration/test_solution_build_compile.py::test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay
check (container-replay-refusals)	Linux container gates	2026-09-29T05:19:45.3194228Z 218.82s setup    tests/integration/test_container_statement_hash.py::test_linux_candidate_fresh_replay[sorry]
check (container-replay-exact)	Linux container gates	2026-09-29T05:18:13.3221796Z 203.08s setup    tests/integration/test_container_statement_hash.py::test_linux_candidate_fresh_replay[rfl]
check (container)	Linux container gates	2026-09-29T05:19:48.3665498Z 116.00s call     tests/integration/test_container_statement_hash.py::test_linux_candidate_axioms[rfl]
check (container-replay-refusals)	Linux container gates	2026-09-29T05:19:45.3195009Z 111.63s call     tests/integration/test_container_statement_hash.py::test_linux_replay_timeouts_keep_their_stage_and_check_inputs
check (container)	Linux container gates	2026-09-29T05:19:48.3666139Z 102.61s call     tests/integration/test_container_statement_hash.py::test_linux_candidate_axioms[sorry]
check (container)	Linux container gates	2026-09-29T05:19:48.3666858Z 86.91s setup    tests/integration/test_container_statement_hash.py::test_linux_dependency_cache_restores_without_provisioning
```

## Skip and xfail producer observations

```text
check (python)	Gates	2026-09-29T05:10:29.9446390Z tests/integration/test_audit_missing_items_drift.py::test_the_live_gatherer_still_matches_the_frozen_excerpt SKIPPED [  5%]
check (python)	Gates	2026-09-29T05:10:29.9454680Z tests/integration/test_audit_missing_items_drift.py::test_the_live_renderer_still_emits_the_frozen_heading_line SKIPPED [  5%]
check (lean)	Gates	2026-09-29T05:09:39.7704700Z tests/integration/test_lean_container.py::test_the_gold_image_builds_and_the_checker_runs_under_landrun_inside_it SKIPPED [ 32%]
check (lean)	Gates	2026-09-29T05:09:39.8114250Z tests/integration/test_lean_container.py::test_the_chattr_probe_inside_the_container_is_recorded SKIPPED [ 33%]
check (python)	Gates	2026-09-29T05:17:10.3739070Z tests/planted/test_corpus_rollup.py::test_the_corpus_bars_are_met XFAIL  [ 35%]
```
