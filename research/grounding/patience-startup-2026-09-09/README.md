# The startup floor is a harness constant, and it is not what busts the patience ceiling

`uv run python research/grounding/patience-startup-2026-09-09/probe_startup_floor.py`
(2026-09-09, build machine, load average 11.9 on 10 cores).

The probe spawns `sys.executable -c "import <skill module>"`, the same interpreter and
argv shape `runner.skill_argv` builds, and reads `ru_utime + ru_stime` from `os.wait4`
the way `runner.spawn_and_wait` does. It measures the CPU a skill subprocess spends
before any declared work begins.

## The floor is one number, not three

15 spawns per module, minimum reported: the minimum is the least load-contaminated
estimator, and under this load average every sample is an upper bound on the quiet
floor.

    module                                min   median      max  max/min
    cairn.skills.instance_maker        0.0627   0.0752   0.1286     2.05
    cairn.skills.bsgs                  0.0613   0.0676   0.0808     1.32
    cairn.skills.rho_dp                0.0603   0.0697   0.0899     1.49

The three minima span 0.0024 s, 4 percent. The cost is the interpreter start plus the
`cypari2` and libpari import, which every skill pays identically; it is a property of the
harness's spawn rather than of any skill's algorithm. A decomposition of the import
itself, 5 spawns each, median:

    sys                        0.0194
    cypari2                    0.0302
    cairn.pari                 0.0512
    cairn.skills.toy_curve     0.0596
    cairn.skills.bsgs          0.0782
    cairn.skills.instance_maker 0.0899

## The floor sits under the ceiling, in every declared case measured

    skill            startup(min)   declared_wall_s   ceiling@4   startup/ceiling
    instance_maker        0.0627            0.0491      0.1964              32%
    bsgs                  0.0613            0.0292      0.1168              52%
    rho_dp                0.0603            0.0331      0.1324              46%

`ladder-patience-ceiling.md` states that "at every declared size below 40 bits the
ceiling sits under the startup cost alone". On these measurements it does not: the
ceiling is above the startup floor by a factor of two or more in all three cases, and a
lower quiet-machine floor widens the margin. That record's arithmetic on the declared
walls and ceilings is reproduced here unchanged; the reading placed on it is what differs.

## The ceiling is busted, and by which term

`uv run python research/grounding/patience-startup-2026-09-09/probe_ceiling_margin.py`
spawns the shipped child, `sys.executable -m cairn.skills.instance_maker` with the stdin
document, exactly as `runner.spawn_and_wait` does, and reads `wait4` rusage. 7 reps per
declared size, `ceiling_multiplier` 4 read from `bundle/tiers.json`, load average 18.9
falling to 18.7.

     bits  declared   ceiling      min   median      max  max/ceil
       28    0.0491    0.1964   0.1450   0.1795   0.2144      1.09
       30    0.0336    0.1344   0.1271   0.1359   0.1691      1.26
       40    0.0507    0.2028   0.1330   0.1587   0.1812      0.89

The tightest declared rung is 30 bits, whose declared wall is the smallest while the fixed
cost is unchanged. The bust is a tail event: the median fits at every size and the maximum
does not, so a run that passes and a run that does not differ by scheduler noise on a fixed
cost rather than by anything the skill did.

The probe takes the startup term as its one argument, so the same command reproduces the
defect and its inversion. With the term at zero, under load average 55.7 rising to 67.4:

     bits  declared   ceiling      min   median      max  max/ceil
       28    0.0491    0.1964   0.2229   0.2317   0.2622      1.33
       30    0.0336    0.1344   0.2049   0.2188   0.2286      1.70
       40    0.0507    0.2028   0.1645   0.2061   0.2246      1.11

With the shipped term, at the same moment on the same machine:

     bits  declared   ceiling      min   median      max  max/ceil
       28    0.0491    0.2734   0.1803   0.1951   0.2205      0.81
       30    0.0336    0.2114   0.1443   0.1698   0.1811      0.86
       40    0.0507    0.2798   0.1571   0.1992   0.2369      0.85

## What the gap is instead

`instance_maker` at 28 bits was observed at `cpu_s=0.2002` against a `0.1964` ceiling
(`ladder-patience-ceiling.md`, not re-executed here). The startup floor accounts for
about 0.063 of that. The declared 0.0491 covers the solve alone, because `measure._dlp_one`
times the solve in-process. Roughly 0.09 s is therefore per-run work inside the child that
no cost profile declares: the stdin parse, `validate`, curve construction,
`check_postcondition`, and `second_opinion`, which imports `bsgs` lazily and runs a second
algorithm as a cross-check.

`probe_trial_decomposition.py` splits the child, 5 reps, `process_time` medians. It
reconstructs `instance_maker.run` by calling the same functions in the same order rather
than running the shipped `main`; its `_process_total` of 0.1244 against the shipped child's
`wait4` total of 0.1265 at the same moment is what establishes the reconstruction is
faithful.

      import (in-process)      0.0451
      validate                 0.0000
      toy_curve.run            0.0441
      draw_x + ec.mul          0.0000
      check_postcondition      0.0001
      second_opinion (bsgs)    0.0170
      to_json                  0.0000

The undeclared work is two terms, and neither is the claimant's algorithm. About 0.075 is
interpreter plus `cypari2` startup, measured by `wait4` in the same conditions (min 0.0673,
median 0.0769); the 0.03 above the in-process import figure is exec and interpreter boot,
which `process_time` cannot see and the ceiling can. About 0.017 is `second_opinion`, which
imports `bsgs` at `instance_maker.py:264` and solves the instance a second time as the
cross-check, at every size at or below `CROSS_CHECK_MAX_BITS`. The declared 0.0491 covers
`toy_curve.run` alone, and measurement agrees: 0.0441.

The ceiling multiplies the declared part while the undeclared part is fixed. Below about 40
bits the fixed part is the majority of the trial, so the multiplier funds the smaller half.
A ceiling term covering startup alone leaves the `second_opinion` 0.017 undeclared, which is
skill work and belongs in the cost profile rather than in a gate constant.

## The term the gate carries

`bundle/tiers.json` carries `subprocess_startup_ms`, and `runner.ceiling_for` reads it as
`subprocess_startup_ms / 1000 + ceiling_multiplier * declared`. The term is added once and
never multiplied: the multiplier funds the skill's own work, which is what a cost profile
declares, and the interpreter start every spawn pays is the same whatever the size. It is an
integer count of milliseconds because the gate bundle's canonical encoding admits no float
(`cairn.canon.reject_floats`). `ladder._ceiling_ops` passes zero, because it converts a
ceiling into a count of group operations at the declared per-try rate, and startup is not
group operations. `ladder.dispatch` and `m0` read the term from the gate bundle;
`instances.launch_trial` takes `runner.launch`'s default instead, which is the same number,
because `src/cairn/instances.py` sits in `instance_maker.IDENTITY_SOURCES` and reading the
term there would give that skill a new revision for a change that says nothing about how it
computes anything. `tests/unit/test_runner_status.py` asserts the gate value and the module
default are equal, so they cannot drift apart without a red test.

The value 77 is **provisional, measured at load average 18.7 to 18.9**. It is the `wait4`
median of the import floor, and every measurement behind it is an upper bound rather than a
floor. A quiet-box re-measure, one-minute load under 10 with five cold spawns per skill, is
what settles it.

Two alternatives were measured and rejected. Raising `ceiling_multiplier` scales the declared
part, which is not where the gap sits: covering the fixed cost at 30 bits needs roughly 6.5x,
and that same factor over-funds 50 and 60 bits, where the ceiling is the only thing catching a
runaway. Declaring the fixed cost in each skill's `COST_PROFILE` writes one harness constant
into three identity bundles and moves three skill revisions to fix one harness fact.
`second_opinion` is the opposite case: it is genuinely the skill's own work and belongs in
that skill's profile.

## Calibration

No constant in this record is fit to pin as a shipped value: every number was taken under
load average 11.9 to 18.9 on 10 cores, so each is an upper bound on a quiet floor and none
is a floor. A `subprocess_startup_s` that ships needs a re-measure on a quiet machine.

Measured here and load-independent in the sense that matters: that the three skills' startup
floors agree within 4 percent, that the declared wall covers `toy_curve.run` alone, and that
the trial's undeclared work is startup plus the cross-check. `bsgs` and `rho_dp` were
measured only for their import floors, not end to end.
