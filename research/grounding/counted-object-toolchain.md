# The gate-owned counted object is C, pinned by source and by built-binary digest

This record states a decision that rests on an already-executed measurement and on file
reads, and it takes no new timing. Every claim below names the file or the probe run it
comes from. The one thing it does not establish is what a counted, process-kind object
costs: no such object has been measured, and `cairn-mns5` holds that gap with its
conditions.

## The slot being filled

`bundle/allow_lists.json` pins the counted-object slot under
`templates.ladder_method.backend_catalog`:

    "counted_object": {"counted": true,  "kind": "process"}
    "gmpy2":          {"counted": false, "kind": "in_process"}
    "gp":             {"counted": false, "kind": "process"}

So the object is a separate binary the gate spawns, and `gmpy2` is an admitted uncounted
in-process backend a method may carry.

## The toolchain: C, compiled with the platform clang at `-O2 -std=c11`

`bundle/ladder_plan.json` names `clock.reference_cost.arm` as `c_reference` and carries
`cost_s_per_group_op` of `0.000000217100`. That figure comes from
`research/grounding/probe_clock_reference_cost.py`, run 2026-09-08 on the build machine at
its defaults of 10000 group operations per arm per rep over 7 reps, and recorded in
`research/grounding/clock-reference-cost.md`. Its C arm is compiled with `/usr/bin/clang`
(Apple clang 17.0.0) at `-O2 -std=c11 -Wall` into a directory outside the checkout, and
timed on `CLOCK_PROCESS_CPUTIME_ID`.

Per-operation medians from that run, all four arms agreeing on the same final point:

| arm | median s/op |
|---|---|
| `c_reference` | 0.000000217100 |
| `gmpy2` | 0.000000676500 |
| `cypari2` | 0.000000767900 |
| `python_int` | 0.000002767600 |

### Why not a Python-level counter

`ladderplan.ClockBound` holds while `clock_tolerance * rate_ratio < 2 * design_radius`,
and `rate_ratio` is the counted object's per-operation cost over the reference. The bound
is meaningful only while no arithmetic a method can carry is faster per operation than the
gate's object. `gmpy2` is admitted and uncounted at `0.000000676500` s/op, about 3.1 times
the C arm's `0.000000217100`, so an in-process Python counter sits on the wrong side of
that constraint by construction.

### Why not a second systems language

Rust or Zig would add a toolchain to both CI arms to replace one that ships with the
platform, is already installed on the build machine, and already carries a measurement in
the bundle. The rejection is dependency cost, not speed: no measurement here says anything
about their relative per-operation cost, and none is needed to prefer the incumbent.

### What the incumbent figure does not cover

The `c_reference` arm is a bare chain inside one process. A counted process-kind object
additionally pays process spawn and the counting itself. The `0.000000217100` figure
therefore describes the arithmetic floor, not the object that fills the slot, and
`bundle/ladder_plan.json` keeps `clock.rate_ratio` at `1.0` with its seeded provenance
until a counted process-kind object carries a measured one. `cairn-mns5` is that
measurement.

## Pinning a compiled object into the identity bundle

The mechanism a compiled object needs exists, in two halves, and `src/cairn/skills/toy_curve.py`
carries both.

**Source half.** `implementation_revision` (lines 326-332) blake3-hashes each path in
`IDENTITY_SOURCES` (line 21) as `length_prefix(path) + length_prefix(bytes)`, reading a
missing file as empty. An edit to any listed source moves the revision. The counted
object's C source belongs in this list.

**Binary half.** `identity_bundle` (lines 335-347) carries `tool_digests`, and
`env.gp_binary_sha256` (`src/cairn/env.py` lines 10-14) puts an external binary's sha256
in it, raising `GpMissing` rather than returning a digest for a file that is not there.
The counted object's built binary belongs here, so a rebuild under a different compiler
moves the identity even when no source changed.

### The source half is checked generically, the binary half per skill

`tests/unit/test_identity_sources.py` parses every module under `src/cairn/skills/` with
`ast`, collects each `IDENTITY_SOURCES` assignment, and asserts `AGENTS.md` names every
collected path inside backticks. It carries its own planted negative:
`test_a_scratch_agents_md_missing_one_path_goes_red` removes one path from a scratch copy
of `AGENTS.md` and asserts the check goes red. Because the walk globs the skills directory,
a module that declares `IDENTITY_SOURCES` there is covered without anyone extending the
test, and adding the C source to that list obliges `AGENTS.md` to name it. The reach is the
declaration rather than the directory: the walk collects only from modules carrying the
assignment, so a file that declares none contributes nothing to the collected set.

Four modules under `src/cairn/skills/` declare `IDENTITY_SOURCES` — `bsgs.py`,
`instance_maker.py`, `rho_dp.py` and `toy_curve.py` — and they are the four Cairn skills.
The directory holds two further files: `__init__.py`, and `order_bsgs_gmpy2.py`, a
gmpy2-only arithmetic module with no module entry point and no identity bundle, so it
declares none by design rather than by omission.

`tool_digests` is held per skill instead. `tests/integration/test_toy_curve.py` line 304
asserts `set(bundle["tool_digests"]) == {"gp_binary_sha256", "cypari2", "libpari"}` and
lines 305-306 assert two of the values, so for `toy_curve` a dropped or added digest goes
red. That assertion names one skill of the four, so the coverage a new counted object
inherits is the generic source walk and not the digest assertion, which has to be written
for it.

## Arms

The measurement behind this record was taken on one host: Apple M4, arm64, macOS 26.6
(`research/grounding/clock-reference-cost.md`). The Linux arm runs in a container reached
through a docker daemon (`src/cairn/container.py` lines 20 and 132-145, where `DOCKER`
resolves through `shutil.which("docker")` and the daemon probe raises `DaemonUnavailable`).
Nothing here measures that arm, so the per-arm question stays open on `cairn-mns5`: the
shape is that the plan carries a value per arm, and the Linux value is unmeasured.

## What this record settles, and what it leaves

Settled: the language and compiler flags, with their rejected alternatives and the
constraint that decides between them; both halves of the identity-bundle pinning, named
against the code that already implements them; and which object the `0.000000217100`
figure describes.

Left open, on `cairn-mns5`: the cost of a counted process-kind object, the separation of
arithmetic from counting from spawn, the Linux arm, and the provenance of
`clock.rate_ratio`.
