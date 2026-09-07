# Gate-owned axiom computation

Calibration: STRONG-EMPIRICAL, 2026-09-07, dev-macos-fake-landrun.
Lean pin: `leanprover/lean4:v4.34.0-rc1`, commit
`3447a668783dbce1a8fdb97101dd067687b2b418`; mathlib pin
`1f29011071772620f612bf5a06433775f06067b8`.

The gate materializes `lean/Cairn/Axioms.lean` from a raw bundle object into a fresh
tool project, builds the trusted executable, compiles the Solution module, and runs
the executable against that module. Only the executable's canonical JSON is consumed.
Solution build output is diagnostic data. `bundle/lean.json` owns permitted axioms,
checker commands, and the ordinary path's empty external-kernel list. Supplied checker
configuration must equal those bundle fields before compilation. The toolchain's full
commit is checked before any Lake build.

## Executed matrix and decisions

Command: `uv run pytest -q -s tests/integration/test_axiom_computation.py`.
Every source is in that file's `SOURCES`; the expected complete records are in
`tests/goldens/axiom_computation.golden` with generator provenance alongside it.

| Fixture | Observed target axioms | Subset decision |
|---|---|---|
| Clean | `[]` | pass |
| Sorry | `[sorryAx]` | refuse `sorryAx` |
| NativeDecide | `[target._native.decide.ax_1_1]` | refuse generated axiom |
| BvDecide | `[Classical.choice, Quot.sound, propext, target._native.bv_decide.ax_1_5]` | refuse generated axiom |
| BvSimplified | `[Classical.choice, Quot.sound, propext]` | pass |
| CustomAxiom | `[planted]` | refuse `planted` |
| UnusedSorry | `[]`; flag `unusedAdmission` | pass with named flag |

There are no uncovered classes in F5-a. NativeDecide reports no `Lean.trustCompiler`,
refuting the REPORTED expectation in the bead's design comment 111. The gate uses the
observed generated axiom names. These names are toolchain-dependent, not universal
names for native evaluation.

The multiplication BvDecide fixture requires the native LRAT-checking path. The
addition-by-zero BvSimplified fixture discharges during simplification and introduces
no native axiom. Thus source syntax alone does not establish an axiom dependency.
Lean's pipeline is described in its implementation at
`src/lean/Lean/Elab/Tactic/BVDecide.lean:47-67` on the pinned commit.

**P-5a decision:** an empty Challenge theorem list refuses with
`empty-theorem-names`. A vacuous subset check would establish no obligation about any
submitted theorem. Missing declarations and nontheorem targets also refuse.

**P-5b decision:** a clean target closure passes even when the Solution contains an
unreachable admission. Rejecting it would change the predicate from target-closure
containment to whole-module cleanliness. The record exposes `unused_admissions` so
the admission is visible; it does not silently certify the whole module. The scanner
names declarations in the submitted module whose collected dependencies include
`sorryAx` but which are outside the target dependency walk. The fixture pins this record:

```json
{"offending_axioms":[],"passed":true,"theorems":{"target":[]},"unused_admissions":["unusedAdmission"]}
```

## Authority and refusal

`Lean.collectAxioms` is the actual collector. Python checks the exact JSON schema,
target names, sorted unique name lists, and the subset relation. It does not parse
`#print axioms` text or infer axioms from source strings. A planted human-readable
line refuses as `non-canonical-json`. Configuration mutation fixtures cover each of
the three bundle configuration fields and report `checker-config-mismatch` with
`spawned: []`. The wrong-commit fixture observes only elan-list and Lean-version
spawns, a `pin_mismatch` log entry, and no Lake spawn or tool directory.

The collector sorts serialized strings explicitly: Lean Name ordering and Python
string ordering differ on the multi-axiom bit-vector result. The canonical reader
refuses unsorted or duplicate names.

The ordinary-path result depends on the imported environment. Pinned Lean caches
imported axiom dependencies in a persistent environment extension; this executable
does not independently authenticate arbitrary manipulated extension state. F6 owns
fresh kernel replay and the forged-environment planting. The Solution compilation
precondition is settled in `formal-statement-hasher.md`: `import Lean` is admissible,
and a source-level elaborator command executes under the comparator on this dev arm.

## Source authority

All paths below are in Lean commit `3447a668783dbce1a8fdb97101dd067687b2b418`:

- `src/lean/Lean/Util/CollectAxioms.lean:149`: public collector;
  `:37-73`: recursive collection, imported cache, and missing-name no-op;
  `:118-146`: exported extension construction.
- `src/lean/Lean/Environment.lean:839`: declaration lookup;
  `:1195`: module ownership lookup; `:2438`: module import.
- `src/lean/Lean/CoreM.lean:440-452`: execution in a supplied environment.
- `src/lean/Lean/Data/SMap.lean:103-114`: complete constant-map fold and list conversion.
- `src/lean/Lean/Util/FoldConsts.lean:55`: expression constant traversal;
  `src/lean/Lean/Declaration.lean:483`: access to definition, theorem, and opaque values.
- `src/lean/Lean/Util/Path.lean:108,180`: search-path and sysroot initialization.

The proprietary skill informs author code review only: dependency and execution-path
inspection, separation of implementation checking from independent review, and exact
reproduction of suspected defects. Source references:
`lean-proof-mastery-with-epistemic-humility/references/REVIEW-PROMPTS.md:5,25-39`.
No skill prose or proof-authoring template is part of the gate bundle.

## Mathlib cost

Fixture `lean/Challenge/AxiomCost.lean` imports the affine-point module and proves
`W.Δ = W.Δ` by reflexivity. From `lean/`:

```text
/usr/bin/time -p lake +leanprover/lean4:v4.34.0-rc1 exe axioms Challenge.AxiomCost axiomCost
{"theorems":{"axiomCost":["propext"]},"unused_admissions":[]}
real 163.71
user 18.87
sys 9.72
```

The command exited 0. Timing includes Lake startup; the executable was prebuilt.
Host load averages during this run were 39.43, 23.54, and 17.77. An earlier run
measured 54.53 s, so this is a load-dependent measurement, not an idle cost estimate.
Axiom containment alone establishes neither statement match nor intended meaning.
F6 owns the former; the statement-level review owns the latter.
