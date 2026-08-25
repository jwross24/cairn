# Grounding brief: Lean checker protocol (PROVEN gate tooling on this machine)

Probe date 2026-08-21, macOS 26.6 / Darwin 25.6.0 arm64. Sources: `leanprover/comparator` @5756749 (2026-08-19), `GasStationManager/SafeVerify` @b291b58, `leanprover/lean4checker` @91a7f0e (deprecated), Lean v4.34.0-rc1 (commit 3447a66), `lean4export` @b18d673, mathlib master @1f29011. Scratch (clones, builds, `*.log`): `/private/tmp/claude-502/-Users-jr843u-Documents-cairn/9cf1d827-93dc-467a-8101-c39c1c16857b/scratchpad/grounding/lean-checker-protocol/`.

## 1. Toolchain on this machine

- STRONG-EMPIRICAL: `command -v elan lean lake leanchecker landrun` → all NOT FOUND; no `~/.elan`. Homebrew bottle `elan-init 4.2.3` exists.
- Install (ran into an isolated `ELAN_HOME`, exit 0, gives elan 4.2.3 b6cec7e10):
  ```
  curl -sSf https://elan.lean-lang.org/elan-init.sh -o elan-init.sh
  sh elan-init.sh -y --default-toolchain leanprover/lean4:v4.34.0-rc1      # or: brew install elan-init
  elan toolchain install leanprover/lean4:v4.34.0-rc1                     # lazy download otherwise; first `lean` call took >2 min
  ```
  Result: `Lean (version 4.34.0-rc1, arm64-apple-darwin24.6.0, commit 3447a668783dbce1a8fdb97101dd067687b2b418, Release)`, `Lake version 5.0.0-src+3447a66`; toolchain `bin/` ships `leanchecker`.
- Pin to record: `lean-toolchain = leanprover/lean4:v4.34.0-rc1` — identical in comparator (`lean-toolchain`) and mathlib master @1f29011 (raw `lean-toolchain`, fetched 2026-08-21) (PROVEN-in-source). SafeVerify pins v4.27.0: a second toolchain if used.

## 2. comparator on macOS; SafeVerify

- PROVEN-in-source (README; `Main.lean:325-326`): needs `landrun` (Linux Landlock ≥5.13 only — landrun README, WebFetch 2026-08-21) and `lean4export` in PATH, optional nanoda; overrides `COMPARATOR_LANDRUN|LEAN4EXPORT|NANODA`.
- `scripts/fake-landrun.sh` fidelity (lines 2-4, 43-62): drops every landrun flag, prints a stderr WARNING, `exec "$@"` unsandboxed. Skipped: all of `--best-effort --ro / --rw /dev -ldd -add-exec`, `--env` allow-list, `--rwx .lake`, `--rox <lean prefix>,<git>` (`Main.lean:80-86,124-132,142-150`). So README assumptions 3-4 are void on macOS: Solution's `lake build` runs with full user privilege. Closure compare (`Compare.lean:67-87`), axiom check (`Axioms.lean:45`) and kernel replay (`Main.lean:211-238`) are unaffected; README allows a pre-built `.lake` in lieu of the sandbox.
- Config (`Main.lean:311-319`, argv[0] = config path, cwd = project with both libs): `{challenge_module, solution_module, theorem_names[], definition_names?[], permitted_axioms[], enable_nanoda?, external_kernels?: {name: [cmd, args...]}}`.
- STRONG-EMPIRICAL, commands run:
  ```
  cd comparator && lake build lean4export comparator        # 29.4 s wall
  cd tests/projects/simple_match   # lakefile.toml with lean_lib Solution + Challenge, per README
  COMPARATOR_LANDRUN=$(realpath ../../../scripts/fake-landrun.sh) \
  COMPARATOR_LEAN4EXPORT=$(realpath ../../../.lake/packages/lean4export/.lake/build/bin/lean4export) \
  lake env ../../../.lake/build/bin/comparator config.json
  ```
  simple_match: `Your solution is okay!` rc=0, 6.6 s wall (first run, manifest created); simple_mismatch: `Challenge and solution constant kind don't match: 'comm'` rc=1, 2.3 s; simple_axiom_issue: `Illegal axiom detected: 'helper'` rc=1, 2.3 s. `lean --run runtests.lean`: 17/20 pass in 73 s; the 3 failures are nanoda cases (`nanoda exited with 127`, no `nanoda_bin`).
- SafeVerify (olean-level). Invocation (`--help` verified; `Main.lean:459-471`):
  ```
  lake env lean -o target.olean target.lean        # Lean 4.27 requires sources inside the package root
  lake exe safe_verify [--disallow-partial] [-v] [-s out.json] [-d|--disproofs] target.olean submission.olean
  ```
  Checks (`Main.lean:145-174,42-66,403-405`; `Util.lean:10-16,128-137`): import-superset; `Environment.replay` of each file's own constants; rejects `unsafe` (`partial` with flag); re-runs `Kernel.check`+`isDefEq` on rebuilt proof terms; name/kind/type/levelParams structural equality; def bodies equal unless target depends on sorryAx; axioms ⊆ {propext, Quot.sound, Classical.choice} hard-coded (`Main.lean:382`); `--disproofs` accepts `foo.disproof` whose type is kernel-defeq to the negated target. Misses (README + source): imports trusted, no `--fresh` analog, no compile sandbox, no external kernel, no `implemented_by`/`extern` scan, same kernel. Runs (v4.27.0; scratch copy with the unused `require mathlib` removed from `lakefile.lean` — the exe imports only Lean+Cli): match 4.0 s rc=0; wrong statement → `theorem type mismatch` rc=1; `axiom cheat` → `uses disallowed axioms #[cheat]`; `sorry` → `#[sorryAx]`; disproof pair rc=1 without `-d` (`declaration not found`), rc=0 with `--disproofs`.

## 3. leanchecker (toolchain v4.34.0-rc1)

- PROVEN-in-source (`src/LeanChecker.lean` @v4.34.0-rc1:70-114): flags are only `-v|--verbose` and `--fresh`; any other `-x` is ignored (no `--help`; in a dir without `lake-manifest.json` it checks every olean on the search path — `leanchecker --help` hung >2 min here). Default: per module, imports loaded as-is, only the module's own constants replayed (`replayFromImports`, 12-34), parallel, prefix match. `--fresh MOD` (single module): `withImportModules` then `(mkEmptyEnvironment).toKernelEnv.replay env.constants.map₁` (36-38) — every constant in the transitive closure re-checked by the kernel from empty. Guarantees: no environment hacking in imports; not an external verifier; does NOT reject `sorryAx` or extra axioms.
- STRONG-EMPIRICAL (tinyproj, no mathlib): `lake build` exits 0 with `sorry` (warning only); `lake env leanchecker --fresh -v Solution` 32.3 s rc=0; `leanchecker -v Solution` 1.3 s; `leanchecker --fresh Challenge` (body `sorry`) rc=0. `#print axioms`: `grind` proof → `[propext, Classical.choice, Quot.sound]`; `sorry` → `[sorryAx]`; `decide +native` → `[t._native.decide.ax_1_1]`. Reference manual (ValidatingProofs, 4.34.0-rc1) names `lean4checker --fresh`; the shipped binary is `leanchecker` (lean4checker README: built in from v4.28.0).

## 4. Minimal PROVEN artifact fields

- `lean_toolchain` string + `lean --version` commit; lean4export header already embeds `{"lean":{"githash","version"}, "exporter":{"version":"3.1.0"}}` (observed).
- `lake_manifest`: full `lake-manifest.json` (mathlib `rev` + every inherited dep) and lakefile hash — README assumption 1: Challenge's import closure and lakefile are part of the statement.
- comparator config verbatim: `challenge_module`, `theorem_names`, `definition_names`, `permitted_axioms`.
- `axioms`: `#print axioms` set per theorem (must ⊆ permitted).
- `checker`: `{comparator, rev 5756749, lean4export b18d673, landrun real|fake, external_kernels}` | `{leanchecker --fresh, toolchain}` | `{safe_verify b291b58, v4.27.0, flags}`.
- `statement_hash` (CONJECTURE on construction): hashing raw `lean4export Challenge -- thm` is NOT stable — two semantically identical Challenge files hashed differently (sha256 9b15b8af… vs a1b5cd7a…) because the export carries the sorry'd value (hygienic name with module+position). Hash what `compareAt` compares: the target's ConstantVal (name, levelParams, type) plus full ConstantInfo of every constant in the transitive `getUsedConstants` closure of the type (`Compare.lean:37-59,67-87`), excluding the target's value.
- `source_hash`: sha256 of Challenge.lean, Solution.lean, Solution olean.

OPEN: wall time for mathlib-importing Challenge (comparator `lake build`+export, `leanchecker --fresh`).
OPEN: nanoda / external kernels untested (no `nanoda_bin`; Rust build not attempted).
OPEN: statement-hash tool does not exist; needs a small Lean script over the export (the proxy above is inferred from `compareAt`, not run).
OPEN: real landrun is impossible on macOS; PROVEN-gold must run on Linux (or a Linux container) — dev-only fidelity here.
