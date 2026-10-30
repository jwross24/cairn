# Lean v4.35.0: project checking, bundled external kernels, kernel fixes

Source: Lean v4.35.0 release notes, https://lean-lang.org/doc/reference/latest/releases/v4.35.0/ (released
2026-10-12; first 100k of 103k characters read 2026-10-30), with commit titles from
`gh api repos/leanprover/lean4/compare/v4.34.0...v4.35.0` and `.../v4.34.0...v4.34.1`.

## Commands
- `lake check` (#14990): builds default targets, exports, replays the export through the kernel, and "fails if
  anything uses an axiom other than the standard ones." `--paranoid` also runs the bundled external checkers and
  accepts only if every one accepts. `--from-export <file>` checks an export made elsewhere.
- `lake comparator` (#14885 as `lake challenge`, renamed in #15146): checks each named theorem in a solution proves
  the same statement as the challenge, uses only permitted axioms, and is kernel-accepted. Config `comparator.json`
  with `challenge_module`, `solution_module`, `theorem_names`, `permitted_axioms`. `--paranoid`,
  `--solution-from-export`, `--challenge-from-export`.
- Both "treat the project as untrusted": build and export run in a `bubblewrap` sandbox (#15005, replacing
  landrun) that hides the home directory and allows network only for dependency resolution; the kernel runs in a
  separate process (#15055). The sandbox "is currently only available on Linux". An expert flag disables it
  (#15156) and "should not be used in usual production environments".
- `leanchecker-paranoid` (#14884): leanchecker with a hardened allocator. `leanchecker --from-export file.ndjson`
  (#15050).

## Bundled external kernels
The toolchain bundles `lean4lean` (#15048), `nanoda` (#15099), `con-leche` (#15130) and `con-ron` (#15153); only
the `--paranoid` modes run them all (#15145). nanoda, con-leche and con-ron do not use the Lean runtime, so the
runtime bugs below did not affect them. This is the "four kernels as standard" New Scientist reported.

## Soundness fixes
- Kernel (also in v4.34.0 final, not in v4.34.0-rc1): #14806 order-independent `is_def_eq` caching, #14807
  `is_prop` requires a sort, #14808 type-check generated recursors, #14849 bound `Nat` numeral size.
- Runtime: #15241 frozen reference counts released in deletion cascades "could potentially be used to trigger
  use-after-free in the official kernel" on machines with 18GB free, which "could be extended into a proof of
  False"; #15289 maximal sharing over `INT_MAX` references on inputs "north of 100GB"; #15288 undefined behavior when
  shared between threads (the official kernel is single-threaded by default; con-leche may be affected). Three
  fixes of this kind were backported to v4.34.1 (2026-09-24), e.g. #15241 and #15307.
- #14953 removes `Lean.reduceBool`, `Lean.reduceNat`, `Lean.ofReduceBool`, `Lean.ofReduceNat` and the
  `Lean.trustCompiler` axiom, because `trustCompiler` "looked used in every environment that imported them", making
  whole-environment axiom checks "less meaningful". `native_decide` remains, via `Lean.Meta.nativeEqTrue`.

## For cairn
- cairn's pin `v4.34.0-rc1` predates the kernel fixes (v4.34.0) and the runtime fixes (v4.34.1). See cairn-p76j.
- `lake check --paranoid` / `lake comparator --paranoid` is the configuration that would have stopped a Kumar-style
  two-kernel exploit: acceptance needs five independent checkers, three not sharing the Lean runtime.
- cairn's own gold arm already does what the release does for isolation (no candidate code runs between export
  and replay, commit fb91dcc5); the release's bubblewrap sandbox is Linux-only, which matches cairn's container arm.
- Whether cairn's permitted-axiom list or any fixture uses `native_decide` decides how `nativeEqTrue` trust enters
  the axiom report; not checked.
