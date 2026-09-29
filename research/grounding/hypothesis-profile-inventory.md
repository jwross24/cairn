# Hypothesis profile inventory

Recorded 2026-09-29. Source revision inspected: `1d1fd3b3049a83c6db5976eb8bad983bff3577ae`. Owner decision via MagentaSparrow: retain `ci=500` and `dev=50`. This inventory does not change profiles, tests, or CI.

## Profiles and budget semantics

`tests/conftest.py:45-47` registers `ci` with `max_examples=500`, `deadline=None`, and `print_blob=True`; `dev` has `max_examples=50` and `deadline=None`. It loads `HYPOTHESIS_PROFILE`, defaulting to `ci`. `scripts/check.sh:180,187` and `.github/workflows/ci.yml` do not select another profile, so their pytest commands inherit `ci` unless the environment supplies an override.

The installed package is Hypothesis **6.165.10**. Its `_settings.py:586-598` specifies that omitted settings inherit from the active profile; `_settings.py:754-773` defines `max_examples` as a target of satisfying cases, with fewer cases on early failure or exhausted space and more draws when cases are rejected. `core.py:204-208` states explicit `@example` cases do not count toward that target. `_settings.py:959-967` defines `stateful_step_count` as a maximum per state-machine case. The installed source and metadata were inspected directly; Context7 lookup returned its monthly-quota error.

The read-only AST inventory covers `tests/**/test_*.py`. It finds 74 `@given` function definitions plus two test callables assigned from `given(...)` in `tests/unit/test_verifier_fuzz.py:106,150`, for 76 test callables. Literal parameter expansion estimates 86 pytest items; this is not a `pytest --collect-only` result. Of those, 19 definitions / 24 estimated items specify `max_examples`, while 57 callables / 62 estimated items inherit the active profile. These are test and item counts, not generated-example counts.

| Explicit target | Source | Items | Target sum |
|---|---|---:|---:|
| 30 | `tests/integration/test_toy_curve_properties.py:47` | 2 | 60 |
| 40 | `tests/integration/test_verifier_properties.py:73,94,109,143` | 8 | 320 |
| 80, 60 | `tests/unit/test_bsgs.py:69,90` | 2 | 140 |
| 60 | `tests/unit/test_order_bsgs_gmpy2.py:175`; `tests/unit/test_rho_witness_verifier.py:131` | 2 | 120 |
| 500 | `tests/unit/test_gateplan_fuzz.py:80,87,185`; `tests/unit/test_gateplan_validation.py:75` | 4 | 2,000 |
| 150 | `tests/unit/test_justified_by_query.py:56,64` | 2 | 300 |
| 50 | `tests/unit/test_ladder_engine_fuzz.py:23,159` (three decorated tests) | 3 | 150 |
| 200 | `tests/unit/test_ladder_plan.py:230` | 1 | 200 |
| **Total** | **19 definitions** | **24** | **3,290** |

The 62 inherited items have a nominal target sum of 31,000 under `ci` or 3,100 under `dev`. Adding explicit targets gives nominal totals of 34,290 and 6,390. These sums are arithmetic over settings, not counts of examples actually executed or runtime estimates.

The planted negative is visible under an active `dev` profile: an installed `settings(max_examples=500)` object retains 500, and `settings(max_examples=200, stateful_step_count=50, database=None)` retains 200 and 50 while the profile default is 50. The four 500-target gate-plan properties, the four 40-target verifier items per curve, and the state machine therefore are not capped by the `dev` value.

## Fixed examples, replay data, and stateful coverage

There are 11 literal `@example` decorators, no `@seed` decorators, and no `@reproduce_failure` decorators. `tests/fuzz_corpus/` contains 72 JSON cases: attest 7, canon 8, gateplan 8, runner 15, selftest corpus 8, and verifier 26. Sixty-four are direct parameterized replay items. The eight selftest-corpus inputs are attached as explicit examples; verifier and runner corpus inputs are also attached to property tests. Such fixed inputs remain regardless of profile, and can run in addition to generated cases. The default failure database lives under `.hypothesis/examples`; the workflow does not cache it.

`tests/integration/test_substrate_stateful.py:16,22,52-136,173-183` defines one machine with seven rules and one invariant. Its settings are `max_examples=200`, `stateful_step_count=50`, `deadline=None`, and `database=None`. The ordinary property and three substrate-mutant cases each invoke it with those settings. Fifty is a per-case maximum number of rule calls, not a fixed operation count.

## Reproduction and timing limits

The inventory checker is a read-only AST/runtime-metadata probe; it does not import test modules or run property cases:

```bash
uv run python /tmp/cairn-x54.tPhtW8/inventory_check.py
```

Its complete JSON output is retained at `/tmp/cairn-x54.tPhtW8/inventory-check.json`. The positive profile and planted-negative fields are:

```json
{
  "profiles_max_examples": {"ci": 500, "dev": 50},
  "explicit_budget_functions": 19,
  "explicit_budget_items": 24,
  "generated_test_functions": 74,
  "generated_test_assignments": 2,
  "parameter_expanded_items_ast": 86,
  "planted_negative_under_dev": {
    "profile_default_max_examples": 50,
    "explicit_settings_max_examples_500": 500,
    "explicit_stateful_max_examples": 200,
    "explicit_stateful_step_count": 50
  }
}
```

`research/grounding/ci-runtime-2026-09-08.md:349-360` records an instrumented unit run with 2,092 passed, 2 failed, and 2 deselected in 750.37 seconds; setup was 152.457 seconds, call 475.099 seconds, and teardown 97.420 seconds. Concurrent source edits caused the two failures, so it is timing attribution, not a passing baseline. The recorded call ranking assigns 212.280 seconds to `test_justify_properties.py` and 37.440 seconds to `test_runner_fuzz.py`.

`research/grounding/test-architecture-2026-09-29/evidence.md` preserves successful eight-lane runs 35704472553 at `5882af8d500e325da3a854606a2b49cdc38c14cc` and 36524637482 at `7882d17aaaaeff9a652b35092808e32ec53b5ce4`. Their Python lanes report 4,053 passed, 2 skipped, 163 deselected, and 1 xfailed in 708.90 and 739.07 seconds. The revisions and runner conditions differ; this is not a controlled profile comparison. Recorded slow phases are primarily Lean, solution, and container replay. Skips and xfail remain exclusions, not passes.

## No-claim

The settings sums are not execution counts or runtime gains. The archived measurements establish no causal speedup, 60-second unit tier, or nightly equivalence to CI. No sample reduction or mathematical result is claimed.
