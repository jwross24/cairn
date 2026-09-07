# Formal statement closure hashing

Calibration: STRONG-EMPIRICAL, measured 2026-09-07 on the dev-macos-fake-landrun arm.
The closure basis survives the listed probes. A hash names and binds; it makes no
statement-equality or Solution-acceptance decision. F6 owns comparator decisions,
fresh replay, and refusal when a matching hash accompanies a comparator mismatch.

## Reference and encoding

Comparator revision `575674928e239f5bc452aab72d1dd7b0f1326494` is nine commits past
the toolchain tag `v4.34.0-rc1` (`011e9d3`). Its lean4export dependency is
`b18d673bd29b476466a51a3be1012df2ed322b10`. The intervening subjects, from
`git log --format='%h %s' 011e9d3..5756749`, are:

```text
5756749 Merge pull request #75 from leanprover/hbv/multikernel
1aa34fe more docs
b63708a docs
d5b206c deny completely
6dc2594 feat: multi kernel support
777e7f5 Merge pull request #74 from leanprover/hbv/quot_trick
41a0907 fix: issue 71
2732944 Merge pull request #73 from leanprover/hbv/fix68
322d8ca chore: regression test for issue 68
```

`Comparator/Compare.lean:78-87` compares target ConstantVal fields:

```lean
    let (challengeConst, solutionConst) ←
      match challengeConst, solutionConst with
      | .thmInfo cc, .thmInfo sc
      | .axiomInfo cc, .axiomInfo sc => pure (cc.toConstantVal, sc.toConstantVal)
      | _, _ => throw s!"Challenge and solution constant kind don't match: '{target}'"

    if challengeConst != solutionConst then
      throw s!"Challenge and solution theorem statement do not match: '{target}'"

    worklist := worklist ++ challengeConst.type.getUsedConstants
```

This is structural ConstantVal equality through derived BEq, whose Expr field uses
alpha equivalence, not literal binder-name equality and not definitional equality.
`Compare.lean:50-56` compares full nontarget ConstantInfo; `Comparator/Util.lean:11-27`
walks types, values including opaque values, inductive families, constructors, and
recursor rules. The hasher mirrors these edges; omitting the current node's self-edge
does not alter reachability.

Deliberate scope and representation choices:

- Target values are excluded so a Challenge placeholder does not bind a Solution's
  proof. Referenced nontarget theorem values remain included.
- Only theorem targets are admitted. Comparator also supports axiom and definition
  targets; Cairn's statement API does not offer those modes.
- Primitive and permitted-axiom roots added by the comparator driver are absent unless
  reachable from the statement. Those are verifier obligations, not statement identity.
- Binder names and annotations are omitted to match Expr BEq. Export metadata and let
  `nonDep` are omitted to match lean4export's `Export.lean:130-151` normalization.
- Names and universe parameters remain structural. No alpha-renaming of declarations,
  definitional reduction, or mathematical-equivalence normalization is attempted.
- The hasher encodes unsafe ConstantInfo fields if encountered; the reference exporter
  filters unsafe declarations (`Export.lean:238`). Hash production grants no acceptance.
- Sorted roots and closure records replace traversal order. Each tag and field has a
  decimal UTF-8 byte-length frame; the outer node is `cairn.formal-statement.v1`.
  Python applies `canon.digest` with domain `cairn/formal-statement/v1` to those bytes.

Lean APIs are grounded in source at commit
`3447a668783dbce1a8fdb97101dd067687b2b418`, under `src/lean/Lean/`:
`Declaration.lean:95` (ConstantVal), `:430` (ConstantInfo), `:483` (value?);
`Util/FoldConsts.lean:55` (Expr.getUsedConstants);
`Environment.lean:839` (find?), `:2438` (importModules);
`Util/Path.lean:108` (initSearchPath), `:180` (findSysroot);
`Expr.lean:805` (alpha-equivalence BEq). The installed source and executable share
the pinned release; `lean.assert_pinned` checks its reported full commit before builds.

## Stability and differential probes

Command: `uv run pytest -q -s tests/integration/test_hasher_stability.py`.
The real compiled baseline is:

```lean
def bound : Nat := 3
theorem target (n : Nat) (h : n < bound) : n < bound := by sorry
```

Baseline, independent fresh build, comment prefix, and unused declaration each hash to
`c4454257a9a2e46d4b6d8a69089880243504118e8d08dba80f8bfb746d4a4397`.
The single hypothesis edit `<` to `≤` hashes to
`f95df265cb95e4ae6c7f543ea2ef920165aefc79236a4ef39ae58eb71ee326be`.
The single definition edit `3` to `4` hashes to
`7d22450090b37ef49b5e53f4d01b33494915f987d452b1a50af37e1fc743e8d8`.
The test prints every source, pair diff, and digest, and stores a computed rendered
Challenge hash through the real substrate's gate-run binding.

Command: `uv run python research/grounding/probe_formal_statement.py --comparator <scratch-clone>`.
The reference clone is built with `lake build lean4export comparator`; the probe sets
`COMPARATOR_LANDRUN` to that clone's `scripts/fake-landrun.sh`.
The reference-only permitted set includes `sorryAx` to isolate statement comparisons
between placeholder-containing fixtures. The production permitted set remains the
classical trio. This reference probe is not evidence of a valid Solution proof.

```text
fresh: rc=0, Your solution is okay!
comment: rc=0, Your solution is okay!
unused: rc=0, Your solution is okay!
definition: rc=1, Const does not match between challenge and target 'bound'
```

Raw exports of the same module `Raw` in fresh directories, differing only by the comment
prefix, both contain 577578 bytes but have distinct SHA-256 digests:

```text
fresh   8c6db0adcd126da4123dd169917162fdde21fa3d5c1a352ba4692a843fbdc641
comment 634004c39e7c7721f6317297452ca6afabec02d20c8308f0d468e1dcade0eb73
```

## Mathlib cost

In `lean/`, using the pinned toolchain and mathlib
`1f29011071772620f612bf5a06433775f06067b8`:

```text
/usr/bin/time -p lake +leanprover/lean4:v4.34.0-rc1 build Challenge.FormalHasherCost
Build completed successfully (1994 jobs).
real 36.73
user 2.57
sys 7.29

/usr/bin/time -p lake +leanprover/lean4:v4.34.0-rc1 exe statement_hash Challenge.FormalHasherCost formalHasherCost
real 36.58
user 1.24
sys 4.84

/usr/bin/time -p lake +leanprover/lean4:v4.34.0-rc1 env leanchecker --fresh -v Challenge.FormalHasherCost
replaying Challenge.FormalHasherCost with --fresh
real 465.52
user 287.06
sys 32.72
```

All three exited 0. Fresh replay's process wall was 465794.034 ms with a 600 s bound.
The fixture imports the affine-point mathlib module and uses a placeholder proof;
replay success does not remove `sorryAx` or establish a mathematical result.

## Solution compilation precondition for F6 P-6d

The comparator compiles Solution source and permits `import Lean` on this arm.
A fresh scratch project with Challenge `theorem target : True := by sorry` and the
following Solution, under the production classical permitted set, produced:

```lean
import Lean
run_elab Lean.logInfo "CAIRN_ELABORATOR_EXECUTED"
theorem target : True := True.intro
```

```text
Building Solution
info: Solution.lean:2:0: CAIRN_ELABORATOR_EXECUTED
Build completed successfully (3 jobs).
Running Lean default kernel on solution.
Lean default kernel accepts the solution
Your solution is okay!
rc=0, wall_ms=30908.466
```

Thus the protocol admits a source-level elaborator planting, including the environment
manipulation contemplated by F6 P-6d. This observation does not establish containment
on Linux or the forged-environment refusal; F6 owns those checks.
