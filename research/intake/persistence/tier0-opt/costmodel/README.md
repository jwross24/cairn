# Tier A cost model

Plan and model only; nothing here runs or touches the sweep.

- `costmodel.py`: unit costs (measured, P-core, host load ~10), per-q rate fits (`rates.json`, fitted on the sweep's recorded per-equation level counts), Lemma C / sandwich fits (`post_fit.json`).
- `scenarios.py`, `runscen.py`: scenario matrix, pool (4 P + 6 E at 0.6 + GPU lane) list-scheduling simulation. Output: `data/scenario_results.json`, `data/scen_out.txt`.
- `schedule.py`: LPT order of the remaining Tier A vertices from the current `trees_mac.jsonl` and engine speeds (`--t12-ns --gpu --lvlN-x --post-x --open`). Needs only the standard library.
- `data/per_vertex_model.csv`: per-vertex predicted counts and P-core hours per stage.
- `killrate/`: instrumented lvl12 (`lvl12_kr.c`), kill-rate histograms, ordering analysis, and the staged early-abort kernel benchmark.
- `data/stage_runs*.jsonl`, `ab_result.json`, `abN_result.json`, `validate.json`: raw measurements.
- Reference timings use the frozen engines in `../reference/` (lvl12 sha256 a28dc065...).
