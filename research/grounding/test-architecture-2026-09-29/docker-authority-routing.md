# Docker authority lane evidence

Bead `cairn-76p8`. The authority module belongs to the Linux `container` lane. A missing Docker daemon is an error. The two authority nodes retain their real image builds, Landrun/comparator calls, and append-only probes.

Implementation revision: `5b36e29ca6c4bf9b354d2a1ec83cb0b307b6a03f`. The local verification snapshot contains exactly the five implementation files from this commit, byte-compared with `git show`; its remaining files come from `7b6a199`. The relevant authority inputs have an empty diff between that base and the implementation revision. Peer edits are outside the snapshot.

## Local observations

The retained [raw files and hashes](docker-authority-routing/manifest.json) distinguish authority execution from routing contracts. All `.gz` files are lossless compressed command output or JSONL diagnostics.

| Scope | Result | Raw artifact |
|---|---|---|
| Real `tests/integration/test_lean_container.py` | 14 passed in 11.53 seconds, exit 0 | `authority-fixed-positive.log.gz`, `gold-positive.jsonl.gz`, `chattr-positive.jsonl.gz` |
| Routing, lane dispatch, Linux setup contracts | 223 passed in 59.03 seconds, exit 0 | `parent-routing.log.gz` |
| Final exact-node and missing-daemon contracts | 2 passed in 3.20 seconds, exit 0 | `final-contracts.log.gz` |
| Scoped fast checks | exit 0 | `fast-final.log.gz` |

The real authority run uses the shared heavy-run lock, descendant memory watchdog capped at 6 GiB, and a Docker argument adapter applying `--memory=6g --memory-swap=6g`. The host watchdog reports a 0.08 GiB peak; that number excludes memory inside the Docker VM. A separate container receipt reads `memory.max=6442450944` and `memory.swap.max=0`.

The build receipts contain two actual image builds with the same input identity, `b7a0f1bcf5e5d33c106266ed09534ccac29baa0732294b6e054b1ffed002e375`. Their OCI image IDs differ. Identity equality does not establish bit-identical images. The JSONL retains the successful comparator case and its refusal cases, plus the append-only capability observations.

## Planted refusals

The exact-node contract names both authority node IDs literally and collects them across all ten lanes. The `container` lane owns each once; every other lane deselects both. Restoring the original Lean routing makes the contract fail because Lean collects both nodes. Raw: `wrong-lane-refusal.log.gz`, exit 1.

The missing-daemon contract invokes the two real nodes with a nonexistent Docker context. Both fail with `DaemonUnavailable`, without skips. Restoring the skip-converting helper makes the inner run report two skipped tests and exit 0; the outer contract refuses that outcome. Raw: `missing-daemon-after.log.gz` and `skip-mutation-refusal.log.gz`, both exit 1 for their respective refusal commands.

UBS exits 0 on four Python files, with no critical findings and three warnings. Two warnings concern JSON parsing of controlled command receipts, where malformed data must fail the test. The remaining warning treats `GateBundle.open` as a file handle; the reviewed underlying `read_rows` closes its SQLite connection in `finally`. This is not a zero-warning result.

## Linux CI boundary

[Run 36584903760](https://github.com/jwross24/cairn/actions/runs/36584903760) tests implementation revision `5b36e29ca6c4bf9b354d2a1ec83cb0b307b6a03f`. Nine jobs pass. The Linux `container` job reports `35 passed, 10 deselected, 3 errors in 760.47s`.

All three errors are fixture teardown errors: `clear_flags` calls `os.chflags`, which Linux does not provide. The affected nodes are the image-identity case and both authority cases. Their call phases pass, but the job is red and cannot support a bead close. `container-ci-failed.log.gz` retains the complete job log. An exit-0 diagnostic asserts the exact three node names, the `AttributeError`, and the summary counts.

## Fixture portability contract

`clear_flags` clears BSD flags only when that API exists and restores mode `0644` on every existing registered path. The contract runs the actual fixture in a subprocess without `os.chflags`, then checks the file mode outside that subprocess. A second subprocess exercises platform protection: real `UF_APPEND` on macOS and read-only mode on both platforms. Missing paths are harmless; actual flag or mode errors propagate.

The isolated verification tree contains committed revision `fe80638e6847937232d1c1e32c079c3dfec5ad5d` plus the two fixture files. Their SHA-256 digests are `ad80c155f1b71fc2081b8235301b2e7382c9f2f2ac9c1c485df670f31a956a7b` (`tests/conftest.py`) and `d76d859f288bb89816c84751a9b06df5b8249dfa025fda5c346ea198e183e13a` (`tests/unit/test_clear_flags.py`). Parent verification of the fixture contracts, scratch-retention contracts, and bundle integration module reports 46 passed in 2.15 seconds, no skips. Scope:

```bash
uv run python -m pytest -q tests/unit/test_clear_flags.py tests/unit/test_test_logging.py tests/integration/test_gate_bundle.py
scripts/check.sh --fast --paths tests/conftest.py tests/unit/test_clear_flags.py research/grounding/test-architecture-2026-09-29/docker-authority-routing.md
```

Each isolated run sets `PYTHONPATH` to its own `src` and `tests`, uses the repository environment through `uv run --no-project`, and places pytest scratch under its own `PYTEST_DEBUG_TEMPROOT`. The initial run without a private temp root passed 46 tests but emitted warnings while pytest attempted cleanup of unrelated retained temp directories; that output is not the clean-scratch result above.

Restoring only the unguarded committed fixture in a separate snapshot makes the missing-API contract fail: the child reports one passed call and one teardown error, `AttributeError: module 'os' has no attribute 'chflags'`; the outer contract exits 1. Raw: `fixture-parent-mutant-isolated.log.gz`. The fixed run is `fixture-parent-isolated.log.gz`; the scoped fast check is `fixture-fast.log.gz`. Linux CI for the fixture repair remains required.

**No-Claim:** local routing contracts do not prove Linux execution; passing test calls do not cancel teardown errors; this report does not claim terminal green CI, bead completion, a speedup, or a mathematical result.
