# Personal-MBP unit-tier verification

Source revision: `935933cd7d399daba21e1136a751c9a70dd9cb10`.
Measured on 2026-09-19 UTC in `/Users/jwross/Documents/cairn`.
Calibration data changes; Python, shell, test bodies and Hypothesis settings do not.
Both full samples and the timed unit command use this same checkout revision;
`git diff -- src tests scripts pyproject.toml uv.lock` is empty. The unit command
uses the calibration committed alongside this report.

## Complete population

Both samples execute all 2,432 unit tests, including slow-marked tests. Each node
has one setup, call and teardown observation in each report. No node is unmeasured.

```bash
uv run pytest tests/unit -q --durations=0 --durations-min=0
uv run pytest tests/unit -q --durations=0 --durations-min=0 --basetemp=/tmp/cairn-unit-next.gLEfDO/pytest-run-2
```

The first command reports 2,432 passed, 170 warnings in 67.81 seconds; command
wall time is 68.58 seconds. The second reports 2,432 passed in 71.22 seconds;
command wall time is 71.966681 seconds. Neither report contains a skipped test.
The first uses pytest's shared temporary root; its cleanup warnings are not passes
or failures. The second uses an isolated root and emits no warnings.

Raw pytest output is compressed in `mbp-20260919-run-1.log.gz` and
`mbp-20260919-run-2.log.gz`; `calibration.json` pins both compressed-byte digests.
The first report excludes exactly the trailing `real`, `user` and `sys` lines
from `/usr/bin/time -p`; the preserved scratch wrapper log is
`/tmp/cairn-unit-next.gLEfDO/full-unit.log`. The second captures timing separately.

One-minute load before/after is 5.17/4.44 for sample one and 4.514160/5.568848
for sample two. Process snapshots at both endpoints contain no competing pytest
process. They are retained locally under `/tmp/cairn-unit-next.gLEfDO`, not published
because unrelated process command lines are outside this project's evidence scope.

## Selection and whole-command result

The 45-second phase budget yields the largest observed fitting threshold,
1.075 seconds. Ten nodes are slow-marked; 2,422 nodes remain included. The retained
median sum is 43.880 seconds. All tests remain in the full check and CI.

The two complete reports have phase sums 59.35 and 62.46 seconds, leaving command
overheads of 9.23 and 9.506681 seconds. The unchanged unit command has 2.42 seconds
of non-pytest overhead. Reserving 15 seconds accounts for their combined maximum
plus approximately three seconds of variation; these measurements are not a runtime
guarantee.

```bash
scripts/check.sh --unit
```

PASS: 47.707804 seconds for the actual command, exit 0. Pytest reports
`2422 passed, 10 deselected, 170 warnings in 46.25s`. Every fast gate passes.
Raw output is `mbp-unit-command.log.gz`. Load before/after is 3.674316/3.491699,
with no competing pytest process at either endpoint. The ten deselections belong
only to this optional feedback tier, not to full-check evidence.

The unchanged calibration's command reports 2,167 passed and 265 deselected in
21.86 seconds. The measured selection includes 255 additional tests. This comparison
describes coverage, not a causal speedup of any test or the full suite.

## Planted refusal

```bash
uv run python -c 'import sys; sys.path.insert(0,"tests"); from _unit_tier import CALIBRATION,CALIBRATION_ROOT,SLOW_UNIT_TESTS,unmarked_slow_tests; reports=[CALIBRATION_ROOT / item["path"] for item in CALIBRATION["reports"]]; assert unmarked_slow_tests(reports,SLOW_UNIT_TESTS)=={}; planted=next(iter(sorted(SLOW_UNIT_TESTS))); defects=unmarked_slow_tests(reports,SLOW_UNIT_TESTS-{planted}); print("PLANTED_MISSING_MARKER",planted,defects,flush=True); assert defects=={}'
```

REFUSED, exit 1: removing the marker for
`tests/unit/test_cli_contract.py::test_json_commands_emit_exactly_one_document_on_stdout[m0-run]`
produces a detected 2.41-second median and an `AssertionError`. The unchanged marker
set passes the assertion in the same process. Raw refusal is
`mbp-planted-refusal.log.gz`. Its raw command includes `from pathlib import Path`,
an unused import with no effect on the predicate.

```bash
uv run pytest -q tests/unit/test_check_unit_tier.py
```

PASS: 20 passed, 180 temporary-directory cleanup warnings in 2.30 seconds, exit 0.

## Limits

The unit tier is not a closing gate. Full-check and pushed-commit CI evidence belong
in the bead's closing record. No claim of timing portability, full-suite speedup,
reduced Hypothesis coverage or mathematical progress is made.
