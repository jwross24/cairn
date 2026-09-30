# The gate-owned counted object is C, pinned by source and by built-binary digest

This record states a decision that rests on executed measurements and on file reads, and it
takes no new timing. Every claim below names the file or the probe run it comes from. The
cost of the counted, process-kind object is measured per arm in
`research/grounding/paired-rate-ratio.md` under `cairn-mns5`, and the "Arms" and "What
`cairn-m1-cqt.1.4` item 1 implements" sections below carry those figures and what they
settle.

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
therefore describes the arithmetic floor under Apple clang 17, not the object that fills
the slot. `research/grounding/counted_process.c` is that object as a research prototype:
the same chain, a volatile counter incremented once per group-operation wrapper call, and a
closed JSON protocol the parent validates against a scalar oracle
(`research/grounding/counted-process-cost.md`). Its measured cost per arm is in "Arms".

### The measured cost against the incumbent figure

On the build machine under Apple clang 21, in the paired run of 2026-09-30, the counted
object's chain costs a median of 152.7 ns per group operation of child CPU, and the same
reference C text compiled by the same compiler costs 153.5 ns in the same window; the
per-pair `cpu` ratio's median is 0.990 with a spread of 0.252 inside its pre-registered
0.30 bound, and a reference-versus-reference null control sits at 1.001. Against the
bundle's 217.1 ns the counted object reads as 0.70 of the incumbent figure, but that
comparison crosses a compiler (Apple clang 17 to 21) and a host state, so the like-for-like
number is the paired ratio, and the bundle figure's own re-pin is a bundle change. The
spawned object at 10000 operations per call costs 2.376 times the reference child CPU on
the host (`deployed` kind), with a spread that exceeded its bound; it is recorded, not
qualified.

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

One build cannot serve both arms. On the host the object is a Mach-O binary from
`/usr/bin/clang`, Apple clang 21; in a Linux container it is an ELF binary from whichever
clang the image carries. The Linux arm runs in a container reached through a docker daemon
(`src/cairn/container.py` lines 20 and 132-145, where `DOCKER` resolves through
`shutil.which("docker")` and the daemon probe raises `DaemonUnavailable`). The gold gate
image, `cairn-gate:b7a0f1bcf5e5d33c`, carries no distro compiler at all: `which clang gcc
cc` finds nothing, and the only C compiler in it is Lean's bundled
`/home/cairn/lean/bin/clang`, `clang version 22.1.4` (`docker run … --version`,
2026-09-30). A counted object built on the gold arm is therefore built by that compiler,
which the Lean toolchain pin already fixes, or by a distro clang the Containerfile gains
under its apt snapshot; the research measurement below used a disposable
`debian:bookworm-slim` image with Debian clang 14.0.6, because the gate image has no Python
to drive the probe.

The source is one text with one hash on every arm; the binary digest is per arm; the ratio
is per arm; the plan carries a value per arm. Measured in `paired-rate-ratio.md`, 31
interleaved pairs at 10000 operations per call, same compiler on both sides of every pair:

| Arm | Compiler | `cpu` ratio median (spread, verdict) | `deployed` median at 10000 ops per call (spread, verdict) | Counted child CPU |
|---|---|---|---|---|
| `macos-host` | Apple clang 21 | 0.990 (0.252, within bound) | 2.376 (0.891, exceeded) | 152.7 ns/group op |
| `linux-container` | Debian clang 14.0.6 | 1.016 (0.212, within bound) | 3.445 (0.829, exceeded) | 178.1 ns/group op |

The `cpu` ratio is the counted chain over the reference chain on `CLOCK_PROCESS_CPUTIME_ID`
inside the child; the `deployed` ratio is the spawned object's parent wall over the
reference child CPU, and moves with the batch size through spawn amortization.

## What `cairn-m1-cqt.1.4` item 1 implements

Item 1 of `cairn-m1-cqt.1.4` builds the gate-owned counted object and records its ratio to
the fastest implementation. From this record and `paired-rate-ratio.md` it is stateable as
implementation work:

1. The object is C, `-O2 -std=c11 -Wall`, built at gate time by the arm's platform clang
   from one source text; `research/grounding/counted_process.c` is the prototype of the
   chain, the counter and the closed protocol, and `probe_counted_process.validate_payload`
   is the prototype of the parent-side validation. The gold arm's compiler is a decision
   inside `.1.4`: Lean's bundled clang 22.1.4 already in the image, or a distro clang added
   to `bundle/Containerfile` under its snapshot.
2. The source text joins `IDENTITY_SOURCES` of the skill that spawns it, so
   `tests/unit/test_identity_sources.py` obliges `AGENTS.md` to name it; the built binary's
   SHA-256 joins that skill's `tool_digests`, per arm, the way `env.gp_binary_sha256` does,
   with the digest assertion written for that skill.
3. `clock.rate_ratio` becomes a value per arm. The measured candidate is the `cpu` kind
   (0.990 host, 1.016 container), which the seeded `1.0` matches within the method's noise
   for the arithmetic-plus-counting meaning. If `ladderplan.ClockBound` means the spawned
   object, the value is the `deployed` kind at a named batch size, which exceeded its
   pre-registered spread on both arms at 10000 operations per call and needs a run whose
   spread holds, or a batch size at which the spawn term is amortized. Which meaning the
   bound carries is the one design decision `.1.4` makes; the numbers for either are in
   the record.
4. `bundle/ladder_plan.json` and `clock.reference_cost` are identity-bearing, so the
   commit that moves them regenerates the goldens in the same attributed commit; the
   reference figure's own provenance (Apple clang 17, 2026-09-08) is re-pinned there or
   left, and either choice is stated.

## What this record settles, and what it leaves

Settled: the language and compiler flags, with their rejected alternatives and the
constraint that decides between them; both halves of the identity-bundle pinning, named
against the code that already implements them; which object the `0.000000217100` figure
describes; the per-arm answer, with the gold image's compiler named; and the measured
per-operation cost of the counted process-kind object on both arms, with the separation of
arithmetic plus counting (`cpu`) from spawn (`deployed`).

Left to `cairn-m1-cqt.1.4`: the meaning `ClockBound` gives `rate_ratio`, the gold arm's
compiler, and the pin itself with its goldens.
