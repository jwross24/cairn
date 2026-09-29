# Root fixture ownership evidence

## Scope and source revisions

`db_snapshot` accepts a filesystem path or a caller-supplied `sqlite3.Connection`. The ownership implementation closes only a connection opened from a path, in `finally` across table queries and diagnostic logging. Borrowed connections remain open, with transaction state unchanged. The source pattern is [`read_rows`](../../../src/cairn/bundle.py#L142), which closes its owned connection in `finally`.

The warning reproducer uses the fixture body from source `133f23aa647f42eb00e9aa1063b798ad3ac606b3`. The ownership overlay has `tests/conftest.py` SHA-256 `6b0e07e29f1297fee3451a0524c80e054b042f344e95e94a2df82986bdb70058` and `tests/unit/test_db_snapshot.py` SHA-256 `76fecef3c3dc3d88ad17852eb2368a0db96281c8634b3b21af35226d20f68ece`. The tests use real SQLite connections and databases.

A read-only source inventory at `c31d0a0b7ff8a3d8bcd21a256c0a356d7dc751f1` counted 160 `db_snapshot` call sites: 159 pass an existing connection, and one passes a path at [`test_m0_slice.py:165`](../../../tests/e2e/test_m0_slice.py#L165). This is a source inventory, not a runtime count.

## Ownership evidence

The exact source reproducer is archived as [`db_snapshot_repro.py`](root-fixture-ownership/db_snapshot_repro.py). It creates a real SQLite file, calls the path branch, and collects warnings. The fixture body from source `133f23aa647f42eb00e9aa1063b798ad3ac606b3` produces this exit-0 observation:

```text
unclosed ['unclosed database in <sqlite3.Connection object at 0x109666890>']
REPRODUCED: path snapshot abandons one unclosed SQLite connection.
```

The actual M0 caller at `test_m0_slice.py:165` passes while emitting a `ResourceWarning`; its allocation trace points from that call to the path connection at `tests/conftest.py:181`. The archived caller log is [`db-snapshot-caller.log.gz`](root-fixture-ownership/db-snapshot-caller.log.gz). The ownership overlay inverts the reproducer: it reports `unclosed []`, and the reproducer exits 1 because its assertion expects the leak. The raw inversion is [`db-parent-repro-inverted.log.gz`](root-fixture-ownership/db-parent-repro-inverted.log.gz).

| Run scope | Result | Raw evidence |
|---|---|---|
| Ownership contracts, `clear_flags`, substrate, GC, and actual M0 caller in the isolated overlay | 155 passed in 9.65 seconds | [`db-parent-positive.log.gz`](root-fixture-ownership/db-parent-positive.log.gz) |
| M0 caller with `PYTHONTRACEMALLOC=5` and `-W always::ResourceWarning` | 1 passed in 3.79 seconds; no warning | [`db-parent-caller-warning-check.log.gz`](root-fixture-ownership/db-parent-caller-warning-check.log.gz) |
| Root fixture harness contracts: collection warm, isolation snapshot, golden harness, `clear_flags`, test logging, and `db_snapshot` | 47 passed in 4.08 seconds | [`root-harness-contracts.log.gz`](root-fixture-ownership/root-harness-contracts.log.gz) |
| Scoped fast gates for the two ownership files | All gates passed | [`db-parent-fast.log.gz`](root-fixture-ownership/db-parent-fast.log.gz) |
| UBS scan of the two ownership files | Exit 0; 0 critical, 1 warning, 29 info | [`db-parent-ubs.log.gz`](root-fixture-ownership/db-parent-ubs.log.gz) |

The 155-test and 47-test outputs are separate scopes with overlap; their counts are not additive. The five ownership contracts exercise seeded counts and diagnostic fields, borrowed-connection transaction state on success and query error, and owned-connection closure on success, corrupt-database query error, and logging error.

The runs used the parent's isolated `db-fixed` snapshot and private `PYTEST_DEBUG_TEMPROOT` directories. The 155-test scope covered `tests/unit/test_db_snapshot.py`, `tests/unit/test_clear_flags.py`, `tests/integration/test_substrate.py`, `tests/integration/test_gc.py`, and `tests/e2e/test_m0_slice.py::test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal`. The 47-test scope covered `tests/unit/test_check_unit_tier.py`, `tests/unit/test_isolation_snapshot.py`, `tests/unit/test_golden_harness.py`, `tests/unit/test_clear_flags.py`, `tests/unit/test_test_logging.py`, and `tests/unit/test_db_snapshot.py`. The warning run exercised the same M0 test with `PYTHONTRACEMALLOC=5` and `-W always::ResourceWarning`. Raw outputs retain terminal results; the parent-run logs do not record shell invocations or private temporary directory names.

The recorded 155-test invocation was:

```bash
cd /tmp/cairn-day-lane3.uMzz8z/db-fixed
PYTEST_DEBUG_TEMPROOT=/tmp/cairn-day-lane3.uMzz8z/db-test-tmp PYTHONPATH=/tmp/cairn-day-lane3.uMzz8z/db-fixed/src:/tmp/cairn-day-lane3.uMzz8z/db-fixed/tests uv run --no-project /Users/jwross/Documents/cairn/.venv/bin/python -m pytest -q tests/unit/test_db_snapshot.py tests/unit/test_clear_flags.py tests/integration/test_substrate.py tests/integration/test_gc.py tests/e2e/test_m0_slice.py::test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal
```

The 47-test invocation used the same working tree and environment with arguments `tests/unit/test_check_unit_tier.py tests/unit/test_isolation_snapshot.py tests/unit/test_golden_harness.py tests/unit/test_clear_flags.py tests/unit/test_test_logging.py tests/unit/test_db_snapshot.py`. The caller warning invocation used the repository as its working directory, the same `PYTHONPATH` and interpreter, `PYTHONTRACEMALLOC=5`, and arguments `-m pytest -q /tmp/cairn-day-lane3.uMzz8z/db-fixed/tests/e2e/test_m0_slice.py::test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal -W always::ResourceWarning`.

The UBS warning is B608 at the table-name interpolation in `tests/conftest.py`. The table names come from SQLite `sqlite_master`; no injection or reachable malicious premise was reproduced, and the scan does not authorize a SQL behavior change.

The unmodified fixture mutant fails the three owned-connection closure assertions and passes the two borrowed-connection cases. The close-every-connection mutant fails both borrowed transaction cases because the connection is closed, and passes the other three cases. Raw outputs are [`db-parent-mutant-original.log.gz`](root-fixture-ownership/db-parent-mutant-original.log.gz) and [`db-parent-mutant-borrowed.log.gz`](root-fixture-ownership/db-parent-mutant-borrowed.log.gz).

Python 3.14 documents `ResourceWarning` for an unclosed connection and states that a connection context manager does not close the connection ([connection objects](https://docs.python.org/3.14/library/sqlite3.html#connection-objects), [connection context manager](https://docs.python.org/3.14/library/sqlite3.html#how-to-use-the-connection-context-manager)). The explicit ownership branch and `finally` preserve the read-only URI and borrowed transaction semantics.

## Source-only root fixture map

This map reflects source inspection of `tests/conftest.py` blob `7b12db79205c08f60294637cf6508e9804bc7b79` at `c31d0a0b7ff8a3d8bcd21a256c0a356d7dc751f1`. Mapping itself did not execute these tests; the separate 47-test run above covers its named harness-contract modules.

| Fixture or behavior | Mapped contract |
|---|---|
| Collection warm | [`test_check_unit_tier.py`](../../../tests/unit/test_check_unit_tier.py): unrelated selection and `--collect-only` leave the cache cold; consumer selection warms it; warm failure returns `USAGE_ERROR`. |
| Isolation snapshot | [`test_isolation_snapshot.py`](../../../tests/unit/test_isolation_snapshot.py): records file size and mtime; skips nested directory symlinks and FIFOs, excludes missing and inaccessible paths, and follows guarded-root links and aliases. |
| Isolation guard, `Popen`, and goldens | [`test_golden_harness.py`](../../../tests/unit/test_golden_harness.py): deploy/leak and outside-echo refuse; read-only Git is admitted and mutation Git is refused; mismatched goldens report diff and actual output; `UPDATE_GOLDENS` rewrites. |
| `clear_flags` | [`test_clear_flags.py`](../../../tests/unit/test_clear_flags.py): missing `chflags` API, missing paths, mode restoration, and platform `UF_APPEND`. |
| `pinned_bundle` | [`test_gate_bundle.py`](../../../tests/integration/test_gate_bundle.py): deterministic pin; [`test_ladder_allowlist.py`](../../../tests/unit/test_ladder_allowlist.py): custom source changes the bundle hash. |
| Output scrub | [`test_m0_slice.py`](../../../tests/e2e/test_m0_slice.py): transcript `[HASH]` and seven `[MS]` replacements; [`test_status.py`](../../../tests/integration/test_status.py): `[BUNDLE]` and `[PATH]` replacements. |
| `load_vector` | [`test_smoke.py`](../../../tests/integration/test_smoke.py): asserts a `tries` value of 46. |
| `db_snapshot` callers | [`test_substrate.py`](../../../tests/integration/test_substrate.py#L553) passes a borrowed connection and later calls `writer.get_attempt` at line 572; [`test_gc.py`](../../../tests/integration/test_gc.py#L206) passes a borrowed connection and later calls `writer.has_blob` at line 212. `test_m0_slice.py:165` is the single path caller in the inventory. |

Unverified seams are collection behavior without a terminal reporter or with import failure; snapshot stat races and `entry.is_dir` errors; isolation restoration for modified or deleted existing paths and `CAIRN_DB` removal/restoration; `Popen` remote/status exceptions, string arguments, and dynamic allow entries; `clear_flags` symlinks; distinct helper names for bundle pinning; missing or stale actual goldens; and output scrub `[ID]` and separate pin-hash behavior. These are unprobed seams, not demonstrated defects.

## CI boundary and claims

The fixture repair is committed at `2de797830071146bc4433983e8ff8e5d3f90bebe`. Its two owned source files have the byte lengths and SHA-256 values recorded above. [Run 36596493998](https://github.com/jwross24/cairn/actions/runs/36596493998) is terminal success on that exact pushed commit, with all ten jobs successful. The Python log names each of the five `test_db_snapshot.py` contracts and the actual M0 path caller as `PASSED`.

| Lane | Collected | Passed | Deselected | Skipped / xfailed | Pytest seconds |
|---|---:|---:|---:|---:|---:|
| Python | 4460 | 4269 | 188 | 2 / 1 | 877.79 |
| Lean | 4460 | 122 | 4338 | 0 / 0 | 722.25 |
| Solution | 4460 | 18 | 4442 | 0 / 0 | 449.31 |
| Solution plan exact | 4460 | 1 | 4459 | 0 / 0 | 837.14 |
| Solution plan refusals | 4460 | 2 | 4458 | 0 / 0 | 568.59 |
| Container | 45 | 35 | 10 | 0 / 0 | 663.23 |
| Container replay exact | 45 | 2 | 43 | 0 / 0 | 458.35 |
| Container replay refusals | 45 | 4 | 41 | 0 / 0 | 548.40 |
| Container plan exact | 45 | 1 | 44 | 0 / 0 | 433.26 |
| Container plan refusals | 45 | 3 | 42 | 0 / 0 | 543.84 |

Every lane reports zero failures, errors, and warnings. The two Python skips are the external compliance-skill drift checks; the xfail is corpus completeness. None exercises `db_snapshot`, and none is counted as passed. Their broader audit holds are documented in [compliance-drift.md](compliance-drift.md) and the checklist.

The exact metadata, full log, and parsed counts are retained as [`2de-ci-run.json.gz`](root-fixture-ownership/2de-ci-run.json.gz), [`2de-ci-run.log.gz`](root-fixture-ownership/2de-ci-run.log.gz), and [`2de-ci-profile.json.gz`](root-fixture-ownership/2de-ci-profile.json.gz). The profiler's planted missing-lane, malformed-summary, nonterminal, failed-run, and incorrect step-category inputs refuse. The invocation was:

```bash
uv run python research/grounding/test-architecture-2026-09-29/pilot_profile.py --run-json /tmp/cairn-day-lane3.uMzz8z/2de-ci-run.json --run-log /tmp/cairn-day-lane3.uMzz8z/2de-ci-run.log --self-test
```

**No-Claim:** These fixture results do not establish a speedup, global leak freedom, or a production database defect. The source-only fixture map does not label the entire fixture audit as passing.

Raw logs and the exact reproducer source are retained under [`root-fixture-ownership/`](root-fixture-ownership/). [`manifest.json`](root-fixture-ownership/manifest.json) records each source path, artifact name, uncompressed byte length, and uncompressed SHA-256.
