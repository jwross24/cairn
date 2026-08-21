# Grounding: statement-level linters and vacuity checks

Slug `lean-statement-linters-vacuity`. Sources: google-deepmind/formal-conjectures @ `e13dd7284e72012a1616806d09cb6b8025e387af` (2026-08-20); Shashi456/atp-checkers @ `3e7e99d027fece04d9cd96288cdd040c366458e5` (2026-04-28); leanprover/lean4 at tags v4.27.0 / v4.30.0-rc2 / v4.34.0-rc1; local probes (elan, lean v4.34.0-rc1) in scratch `grounding/lean-statement-linters-vacuity/` (`fcprobe/`, `atp-checkers/`, `atp-port.log`).

## 1. formal-conjectures linters

**Pins.** `lean-toolchain` = `v4.27.0`; `lakefile.toml:34-37` requires mathlib `v4.27.0`. Mathlib master (1f29011, 2026-08-21) is on `v4.34.0-rc1`; latest lean4 release v4.33.0 (2026-08-10); latest mathlib stable tag v4.33.0. Seven minor versions behind. [PROVEN-in-source]

**Wiring.** Core `Lean.Elab.Command.Linter {run, name}` (unchanged v4.27.0→v4.34.0-rc1, `src/Lean/Elab/Command.lean:64/72`) registered by `initialize … addLinter`, gated by `register_option linter.style.*`; `lakefile.toml` enables the default-false ones via `weak.linter.style.*` (L22-27, L55-60); `FormalConjecturesUtil.lean:21-32` imports all; CI runs `lake --wfail build/test` (`.github/workflows/build-and-docs.yml:149-155`). [PROVEN-in-source]

**What they check** (`FormalConjecturesUtil/Linters/`, 12 linters; two are statement-semantic):
- `ExistsImplicationLinter.lean` — `linter.style.existsImplication`, default **true** (L39-42). `checkExistsArrow` (L54-77) visits every elaborated term through an info-tree walk (`FormalConjecturesForMathlib/Tactic/Linter/Term.lean:71-96`; skipped when the command has errors, L75) and flags `Exists` applied to a lambda whose body is a `∀` with `Prop` domain and non-dependent codomain (L66-68), suggesting `∃ x, P ∧ … ∧ Q` (L46-49).
- `StubLinter.lean` — `linter.style.stubs`, default false (L30-33). Syntactic on the declaration node (L48-64): `opaque` and `axiom` → warn; `def`/`abbrev`/`instance`/`structure` whose syntax contains `sorry`/`admit`/`sorryAx` → warn; `mutual` unrolled (L68-73). `theorem … := by sorry` is deliberately silent (`FormalConjecturesTest/Util/Linters/StubLinter.lean:84-85`).
- `FormalProofLinter.lean` polices the `formal_proof`/`conditional` attribute (L49-111); the other nine (AMS, Category, CategoryDocstring, Answer, Copyright, Import, LatexDocstring, ModuleDocstring, Namespace) are repo metadata/style. [PROVEN-in-source]

**Running them elsewhere.** `require formal_conjectures` would pin mathlib v4.27.0, so vendor. Probe: 4 files (`InfoTree/Util.lean` 44 L, `Linter/Term.lean` 96 L, the two linters 92+78 L) in a mathlib-free lake project on **v4.34.0-rc1** built after two one-line import edits: `Term.lean` `+ public import Lean.Linter.Basic` (`withSetOptionIn` moved from `src/Lean/Elab/Command.lean:867` @v4.27.0 to `src/Lean/Linter/Basic.lean:39` @v4.34.0-rc1) and `StubLinter.lean` `Mathlib.Tactic.Linter.Header` → `public meta import Lean.Linter.Basic`. It reproduced the upstream test messages (`∃ n, n ≠ 0 → False`, the chained `→` form, `opaque`, `axiom`, `def … := sorry`) and stayed silent on `∃ n, n ≠ 0 ∨ False`, `∃ f : Nat → Nat, f 0 = 0`, `theorem … := by sorry`. Blind spots: `∃ n > 0, n ≠ 1 → False` (binder predicate elaborates to `∃ n, n > 0 ∧ (… → …)`) silent; `∃ n, (n ≠ 0 → False) ∧ True` silent; `(∃ n, n ≠ 0 → False) → True` warns (twice). [STRONG-EMPIRICAL, probe]

## 2. atp-checkers

**Pins.** `lean-toolchain` = `v4.30.0-rc2`; `lakefile.lean:6-10` mathlib and plausible @ `v4.30.0-rc2` (manifest rev `5450b53e`); `LIMITATIONS.md` §7 still says "v4.28.0". [PROVEN-in-source]

**`src/AtpLinter/VacuousCheck.lean`.** `analyzeDecl` (L163-189): Prop-typed declarations only. `checkVacuous` (L128-160): `forallTelescope` over the statement, then (a) per binder `checkDomainEmpty?` (L88-125): `whnf`; `Empty`/`PEmpty`; `Fin n` with `n` defeq 0 (L71-85); `Subtype` over `Nat`/`Int` whose predicate's negation `tryProve?` (omega+grind) closes; (b) `tryProveVacuity? False` (`GuardProver.lean:341-373`): `assumptionCore` → `falseOrByContra` + `omega` over `getVacuityOmegaFacts` (L140) → `Grind.main` with `grindConfigVacuity` (L77); state restored, exceptions → `none`. Certified-only (header L13-22: linear Nat/Int). Exposed as `#check_atp <decl>` / `#check_atp_all` (`src/AtpLinter.lean:463-560`, `ATP_LINT:{json}`); the Python runner wraps each problem with `import AtpLinter` … `#check_atp_all` and runs `lean` in the checkers workspace (`runner/executor.py:467-504`), i.e. against *its* mathlib. [PROVEN-in-source]

**`src/AtpLinter/AxiomChecker.lean`.** An `axiom` is reported unless named in `{propext, funext, Quot.sound, Classical.choice/em/propDecidable}` or imported under `Lean.*`/`Init.*` (L19-48); other decls get `Lean.collectAxioms` filtered to user `Prop` axioms (L51-65, L77-101). `sorryAx` passes the whitelist. [PROVEN-in-source]

**Porting cost.** Core entry points are signature-identical v4.30.0-rc2 → v4.34.0-rc1: `Omega.omega (facts) (g) (cfg := {})` (`Omega/Frontend.lean:672`), `Grind.mkParams`/`Grind.main` (`Grind/Main.lean` 59→70, 355→396), `falseOrByContra` (`FalseOrByContra.lean:38`), `collectAxioms` (`CollectAxioms.lean:149`). [PROVEN-in-source] Mathlib is required (`GuardProver` imports `Mathlib.Tactic.Positivity`, `Mathlib.Algebra.CharZero.Defs`; `GuardFacts` imports `Mathlib.Data.Real.Sqrt`, `Mathlib.Analysis.Complex.Norm`). Probe: toolchain → v4.34.0-rc1, mathlib → tag v4.34.0-rc1 (`de5ce8a9`, same toolchain as master), plausible `require` dropped, **no source edits**: `lake update` + cache 5.5 min (8691 files), `lake build AtpLinter` 33 s with one deprecation warning (`Mathlib.Data.Real.Sqrt` → `Mathlib.Analysis.Real.Sqrt`, `GuardFacts.lean:12`); `lake env lean vacprobe.lean` (4.3 s) flagged `(h : n < 0)` and `(a < b, b ≤ a)` as contradictory (omega), `∀ x : Fin 0` as empty domain, `axiom myAx : 1 = 2` and `theorem usesAx := myAx` as user-axiom, and left `a ≤ b → a ≤ b + 1` clean. [STRONG-EMPIRICAL, probe]

## 3. STATEMENTS.md checklist (`formal-conjectures/STATEMENTS.md` @ e13dd728)

1. Read the cited source incl. remarks and variants; the module docstring is not an independent source (L8-9).
2. Read every non-standard definition (Mathlib, `FormalConjecturesForMathlib/`, nearby files); confirm with `#check`; inspect what it returns on empty or smallest inputs (L11-13).
3. Never add an `axiom`, `opaque`, or `constant` (L17).
4. Compare (L21-29): order and scope of all quantifiers · strict vs non-strict bounds · all hypotheses and domain restrictions · equality vs asymptotic equivalence vs order relations · direction of implications · every variant and special case · the category and answer recorded by the source.
5. "Be careful with `∃ x, P x → Q`. The intended statement is usually `∃ x, P x ∧ Q`; the first form can be trivially true" (L31-32).
6. Yes/no problems: `answer(True)` positive, `answer(False)` negative; check scope and expected type of `answer(sorry)`; the rest must constrain the unknown answer, not make the theorem true for every answer (L34-37).
7. Boundary cases (L41-49): substitute the smallest permitted value of each parameter; empty types/sets, zero, missing witnesses. Table: empty indexed type/set → sum is `0`, function type can be a subsingleton; `ZMod 0` ≃ `ℤ`; `x / 0 = 0`; `sInf ∅` can be `0`.
8. A default value is a defect only if reachable and it changes the claim (L51-52).
9. For each hypothesis ask whether any object satisfies it; impossible hypothesis ⇒ vacuous implication; add a domain restriction when the source assumes one (L54-55).
[PROVEN-in-source]

## 4. Verdict

Mechanical today at low cost: `ExistsImplicationLinter` + `StubLinter` (four vendored files, two import lines, no Mathlib), and `VacuousCheck` + `AxiomChecker` via `AtpLinter`, which builds unchanged on the current toolchain after a lakefile bump (both probed); every core entry point they use is stable, so a ~100-line core-only re-implementation is also open, and an axiom gate alone is `Lean.collectAxioms` plus a whitelist. Needs work / stays human: STATEMENTS.md items 1-2, 4, 6-8 have no mechanical form; the ∃-linter misses `∃ x > 0, P x → Q` and `∃ x, (P → Q) ∧ R`; `StubLinter` sees only the declaration's own syntax; `VacuousCheck` certifies only linear Nat/Int contradictions and a few empty types. All are reject-on-certified filters, never a pass.

## OPEN
- OPEN: FC linters were probed mathlib-free; not built against Mathlib master itself (`Mathlib.Tactic.Linter.Header` import swapped, not tested). CONJECTURE it works: Header@master is itself `public meta import Lean.Linter.Basic` (L13).
- OPEN: the atp-checkers port built `AtpLinter` and 6 declarations only; its `#guard_msgs` test libraries and Python runner were not run, so message-format drift is unmeasured.
- OPEN: `∃ x ∈ S, P x → Q` (Mathlib binder) untested; same elaboration shape as the silent `∃ n > 0` case (CONJECTURE: silent).
- OPEN: VacuousCheck latency/recall beyond the probe is the authors' claim (`LIMITATIONS.md` §3, "~1-3 s"); not measured here.
