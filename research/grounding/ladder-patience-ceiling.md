# The patience ceiling counts interpreter startup

`uv run python research/grounding/probe_ladder_run.py` (2026-09-08, build machine,
`bundle/tiers.json` `ceiling_multiplier` 4).

`runner.status_for` compares the whole child process's CPU against
`ceiling_multiplier * declared_expectation_s`, and the declared expectation comes from a
cost profile measured in-process by `cairn measure dlp`. The gap between the two is the
interpreter start plus the `cypari2` and libpari import, which every skill pays and no
profile declares.

    ceiling_multiplier=4 declared_wall_s=0.0491 ceiling_s=0.1964
    instance_maker cpu_s=0.2002 status=BUDGET_EXCEEDED

The same arithmetic covers `bsgs` at 28 bits (declared 0.0292 s, ceiling 0.1168 s) and
`rho_dp` at 30 bits (declared 0.0263 s, ceiling 0.1052 s): at every declared size below
40 bits the ceiling sits under the startup cost alone, so a correct trial is recorded as
a patience failure and its rung is at most INCONCLUSIVE. At 40 bits and above the solve
dominates and the ceiling holds.

`tests/integration/test_instance_maker_substrate.py` widens the multiplier to 60 for this
reason, and `tests/integration/test_ladder_run.py` and the probe's first section do the
same. `cairn.ladder.run` takes the instance stream's multiplier as an argument and reads
the arms' from the plan's `patience_ceiling`, so no widening is compiled in.

The fix is `cairn-w6k`: either the profiles declare a per-process startup constant the
ceiling adds, or the runner measures the skill's own CPU rather than the process's.
