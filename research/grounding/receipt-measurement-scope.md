# Receipt measurement scope: what os.wait4 reports for a skill's descendants

PLAN §3 specifies the receipt's CPU seconds and peak RSS as measurements over the process
tree, and the §6 ladder reads exactly those fields. `runner.spawn_and_wait`
(`src/cairn/runner.py:215`, `:233`, `:246`) measures with `os.wait4`, which reports the
direct child's own usage plus the usage of descendants that child itself reaped. The
probes below establish the size of the gap, its determinism, and what a macOS host can
measure instead.

Probe source: `research/grounding/probe_receipt_scope.py`. Host: darwin 25.6.0, arm64,
CPython 3.14, `nbthreads` irrelevant (no PARI in this path).

## Probe 1 — the reap gap

Three arms, each a child that spawns a grandchild which burns CPU (40M-iteration integer
loop) or grows RSS (48 MB bytearray, touched one byte per page). The child either waits
for the grandchild, exits without waiting, or sleeps past a 3 s wall cap and is killed.

| burns | arm | cpu_user_s | peak_rss MB | exit |
|---|---|---|---|---|
| cpu | reap | 2.800 | 18.4 | 0 |
| cpu | orphan | 0.021 | 18.6 | 0 |
| cpu | killed | 2.124 | 18.5 | -15 |
| rss | reap | 0.034 | 64.0 | 0 |
| rss | orphan | 0.020 | 18.5 | 0 |
| rss | killed | 0.028 | 64.0 | -15 |

The reaping arm carries the grandchild's figure; the orphaning arm undercounts CPU by a
factor of 133 (2.800 s against 0.021 s) and RSS by 45.5 MB (64.0 MB against 18.5 MB).
No receipt field distinguishes the two rows.

## Probe 2 — the ceiling-killed arm is not deterministic

Four repetitions of the killed arm at a 3 s cap, split by whether the grandchild's burn
outlasts the cap:

| case | cpu_user_s across four runs |
|---|---|
| grandchild still running at kill | 0.020, 0.016, 0.021, 0.020 |
| grandchild finished before kill | 2.030, 0.019, 2.143, 1.666 |

A grandchild alive at the kill is a clean undercount. A grandchild that exits before the
kill lands anywhere between the undercount and near-full attribution for identical work,
so the figure a ceiling-killed receipt carries is unreproducible.

This is the sharpest of the three findings, because `laddertable._clock`
(`src/cairn/laddertable.py:430`) compares `cpu_seconds` against
`gate_ops / reference_rate` and `laddertable._wall` (`:450`) compares `wall_seconds`
against `cpu_seconds`. Both predicates read a quantity that varies run to run for the
same work, and both directions are unsound:

- An undercount inflates the wall-to-CPU ratio, so `_wall` returns INCONCLUSIVE for a
  method that forks and orphans rather than one that blocks.
- An undercount never reaches `_clock`'s ceiling, so CPU burned in a non-reaped
  grandchild is invisible to the clock check. A method that offloads its work into an
  unreaped descendant is measured as fast.

## Probe 3 — what a macOS host can measure

`proc_listpgrppids` in `/usr/lib/libproc.dylib` lists exact process-group membership.
Reached through `ctypes` with signature `(uint32 pgid, void *buf, int bufsize) -> int`,
it returns the **count** of pids written, not a byte count.

`spawn_and_wait` already calls `subprocess.Popen(..., start_new_session=True)` and holds
`pgid = proc.pid` (`src/cairn/runner.py:206`), so the group contains the skill's
descendants and nothing else.

Measured (`research/grounding/probe_receipt_scope.py`, probe 3 arm):

- With a grandchild alive, the call returns both pids: leader 89266, grandchild 89274.
- After a group kill, it returns the empty list.
- Cost is 17.2 us per call over 2000 calls with a 1024-pid buffer.

The poll loop in `spawn_and_wait` already ticks at `TICK_S = 0.005`
(`src/cairn/runner.py:30`), so one membership sample per tick costs 0.34 % of the tick.

Blind window: a descendant born and reaped inside one tick is never observed, so the
sampled membership is a lower bound on the descendants that existed. Sampling therefore
supports the negative claim (membership beyond the leader was observed, so the wait4
figure is not a tree figure) and does not support the positive claim (no membership was
observed, therefore none existed) more strongly than the 5 ms window allows.

## Bearing on the two admissible shapes

The bead names a real subtree measurement and a `measurement_scope` field as alternatives.
The probes place them in sequence rather than in competition: macOS supplies no true
subtree accounting comparable to a cgroup, so the sampled membership is not a substitute
for the figure, but it is a sound witness for the figure's scope. A scope derived from
observed membership is a measurement, where a scope declared by the launching party is
an assertion.

## Probe 4 — classification through the real runner

`spawn_and_wait` samples process-group membership once per tick and classifies the figure
from the sampled membership plus the exit shape. Four arms, each through the real runner:

| arm | measurement_scope | cpu_user_s |
|---|---|---|
| child reaps its CPU-burning grandchild | `reaped_descendants` | 1.697 |
| child orphans it | `truncated` | 0.019 |
| child killed at a 3 s wall cap | `truncated` | 1.634 |
| child with no descendant at all | `tree` | 0.015 |

## Probe 5 — the blind window, measured

The window is one tick, so a descendant born and reaped inside 5 ms is unobservable in
principle. Measured against the fastest fork-and-reap a skill can perform, a bare CPython
spawn whose grandchild exits immediately:

| case | runs | scopes observed |
|---|---|---|
| grandchild exits immediately | 30 | `reaped_descendants` 30 |
| grandchild lives 200 ms | 15 | `reaped_descendants` 15 |

Zero misses in 45 runs, because interpreter startup for the grandchild is roughly 20 ms
against a 5 ms tick. The window is not closed by this measurement, and a descendant
spawned by something cheaper than a Python interpreter remains unobservable; the claim the
measurement supports is that the realistic fork-and-reap shape is caught, not that no shape
escapes.
