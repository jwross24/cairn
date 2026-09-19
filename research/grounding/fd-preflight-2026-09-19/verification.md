# File-descriptor guard verification

Base source: `3801c15f6a350a41e460f73280405c790c98d711`.
The candidate is the commit carrying this record.

## Hook boundary and refusal

```bash
uv run pytest -q tests/hook_contract/test_fd_ceiling_contract.py tests/unit/test_fd_ceiling_gate.py
```

Exit 0: 28 passed in 8.69 seconds. The 260 warnings concern pytest temporary-directory
cleanup; no acceptance test skipped or xfailed. `focused.log.gz` preserves the output.

The historical-hook test reads the pinned base hook into a scratch repository.
With the external provider returning 321 / 400, that hook reaches the content-gate
recorder. The candidate refuses the same reading, leaves the recorder absent, and logs:

```text
FD-CEILING used=321 maximum=400 min_free=20%
```

The 320 / 400 boundary reaches the recorder and records `FD-CLEAR`. Other real-hook
tests cover provider failure, missing provider with named bypass guidance, missing uv,
an existing uv executable that exits 7, the explicit reason-bearing bypass, and the
inability of `CAIRN_CHECK_SKIP` to waive this preflight.

The Python tests cover malformed output, stderr, zero maximum, equal or excess usage,
timeout, invalid bypass reasons and an unavailable log. Both recovered historical
high-use readings fall below the policy reserve; the classifier directly exercises
162749 / 184320.

## Scanner review

Official UBS v5.4.2 scanned five Python files, exit 0, with zero critical findings,
three timeout warnings and 47 informational findings on the staged-path scan.
`ubs-staged.log.gz` preserves the report. The timeout warnings name two
existing local `git init` calls and the historical-hook `git show` test setup. They
remain under pytest's per-test and session deadlines; the production sysctl call
has its own five-second timeout. No live hang is established by those warnings.

Subprocess arguments are literal argv lists, not shell input. PATH lookup is the
explicit external-provider seam. Test assertions and return/raise control flow account
for the other reported patterns. `Substrate.open` opens a SQLite store, not a text
file requiring an encoding argument. No scanner suppression is added.

## Independent review

A separate Sol/high review exercised the candidate hook in scratch repositories.
A missing provider refuses with the named bypass instruction and leaves the content
recorder absent. A read-only `.check.log` also refuses before the recorder, with the
write failure visible on stderr. `missing-provider-stderr.txt` and
`unwritable-log-stderr.txt` preserve those outputs.

ASCII log encoding means a non-ASCII bypass reason refuses as a logging error.
That is a usability limitation, not a bypass of the capacity check.

## Full-suite attempt 1

`scripts/check.sh` exited 1: 3927 passed, one failed, three skipped and one xfailed
in 509.90 seconds. `full-gate-attempt-1.log.gz` preserves the failure. The failing
test is `test_a_launch_with_no_descendant_at_all_records_a_tree_figure`; its retained
attempt has `BUDGET_EXCEEDED` where the test expects `OK`. This result is not a pass
and does not authorize shipping.

The status writer in `runner.status_for` emits `BUDGET_EXCEEDED` only when measured
CPU exceeds the declared ceiling. The fixture's 40-bit toy-curve evaluation and
multiplier 4 produce a 0.6122-second ceiling. A joint probe of that source expression,
the ceiling calculation and the recorded failure exits 0. Exact failed CPU is unknown:
pytest cleaned the temporary database before the independent receipt query.

The fixture uses the existing `BURNER_BUDGET` with an explicit 120.077-second wall
cap. Production profiles and limits remain untouched, as do the status and scope
assertions. The source-coupling assertion refuses with exit 1. The six scope tests
and 28 FD tests pass together: 34 passed in 10.85 seconds, no skips or xfails.
`tree-and-fd-focused.log.gz` preserves that run.

`scripts/check.sh --fast` exits 0. The optional `scripts/check.sh --unit` also exits 0:
2441 passed and 10 deselected in 46.35 pytest seconds. The new classifier tests are
included by the default policy for nodes absent from the timing calibration. That
optional lane does not replace the full-suite requirement.

## Full-suite attempt 2

With the test-fixture correction, `scripts/check.sh` exits 0: 3929 passed, three
skipped and one xfailed in 493.02 seconds. `full-gate-attempt-2.log.gz` preserves the
complete run. All FD and tree-scope tests pass. The existing environment-dependent
skips and corpus xfail are not passes. No gate bypass is used.

## Limits

Controlled provider readings prove refusal and hook ordering, not live exhaustion.
No capacity is reserved, and no guarantee is made about later descriptor spikes.
Full-suite environment skips are not acceptance passes for this guard.
