# File-descriptor preflight evidence

## Historical occurrence

`historical-commits.jsonl` preserves the relevant lines of three raw tool results
from CASS session `19595eeb-80ba-4a80-af69-73384ec0ea53`. Each record identifies
its source line and timestamp. `historical-reading.jsonl` preserves the second
session's kernel counters. These are historical observations, not a live resource
exhaustion experiment.

At 2026-09-09T07:19:51.949Z a commit reports `COMMIT_EXIT=1` and multiple
`Too many open files in system` errors, followed by audit-score and scorecard
refusals. A 07:20:08.432Z reading is 162,749 / 184,320. Another commit reports
open-file pipe errors at 07:20:56.455Z. The separate 07:22:14.081Z reading is
165,638 / 184,320. The readings are nearby observations, not measurements taken
at the exact failure instants.

Source locations:

- `/Users/jwross/.claude/projects/-Users-jwross-Documents-cairn/19595eeb-80ba-4a80-af69-73384ec0ea53.jsonl`: lines 10776, 10793 and 10807.
- `/Users/jwross/.claude/projects/-Users-jwross-Documents-cairn/b8bb8011-e9ea-43ec-86bd-29b578b89628.jsonl`: line 2970.

The extraction retains only timestamp, source line and relevant tool-output lines;
it does not publish the conversations. The original bead's 174k peak is a secondary
landing-report observation, not one of these recovered raw readings.

## Missing preflight reproduction

Source revision: `3801c15f6a350a41e460f73280405c790c98d711`.
The following command exited 0 before implementation, matching the gate invocation
at `.githooks/pre-commit:71` while confirming the absence of the counter probe:

```bash
rg -q 'if ! scripts/check\.sh' .githooks/pre-commit && ! rg -q 'kern\.num_files|kern\.maxfiles|FD-CEILING' .githooks/pre-commit scripts/check.sh && rg -n 'if ! scripts/check\.sh' .githooks/pre-commit
```

The positive writer match establishes that the hook starts the content gate; the
historical commit results independently establish real resource-failure occurrence.

## Live provider

```bash
sysctl -n kern.num_files kern.maxfiles
```

The personal-MBP read returns 16,621 and 245,760, exit 0. This verifies the provider
format and healthy headroom for that observation. No kernel or process limit is
changed, and no descriptor-exhaustion experiment is performed.

## Policy limits

The twenty-percent reserve is policy, not a proven sufficient buffer. The predicate
passes 320 / 400, refuses 321 / 400, and refuses both recovered high-use readings.
It cannot reserve capacity or prevent pressure arising during a later audit.
The real-hook planted refusal and verification commands belong in the closing
record alongside this historical premise.
