# Proof automation & the formalization gate (Lean/mathlib, checkers, provers, statement review)

Target components: **formalization gate** (PLAN §7), **lemma library** (§11), **Formalizer/Prover workers**, HANDOFF open decision "confirm mathlib coverage". All claims below were read this session at the pinned commits shown.

## Top line

The PROVEN verdict should be produced by a *challenge/solution* check, not by "Lean compiled without errors": the statement lives in a trusted Challenge file owned by the gate, the Formalizer submits a Solution, and the gate runs (a) kernel replay, (b) axiom allow-list = {propext, Quot.sound, Classical.choice}, (c) statement identity over the statement's transitive constant closure. This is exactly what `leanprover/comparator` (and the lighter `SafeVerify`) implement, and what the Lean reference manual names the gold standard. It mechanizes half of "statement-level review" (the statement cannot drift) and leaves the other half (does the Challenge say what we mean) to the human/Skeptic, which is where it belongs.

## Mathlib coverage table (mathlib4 @ `1f29011071772620f612bf5a06433775f06067b8`, 2026-08-21, `lean-toolchain` = v4.34.0-rc1)

| Topic | Status | Where |
|---|---|---|
| Weierstrass curves, Δ, j, `IsElliptic` | present | `Mathlib/AlgebraicGeometry/EllipticCurve/Weierstrass.lean` |
| Group law on nonsingular points, proved | **present** (affine via class-group injection, ITP 2023) | `…/Affine/Point.lean:780` `instance : AddCommGroup W.Point`; Jacobian `…/Jacobian/Point.lean:588`; Projective `…/Projective/Point.lean:572` |
| Division polynomials | present | `…/DivisionPolynomial/Basic.lean`, `Degree.lean`; `Mathlib/NumberTheory/EllipticDivisibilitySequence.lean` |
| Reduction over DVR/local fields, good/multiplicative reduction | present (2025, definitions + existence of minimal models) | `…/EllipticCurve/Reduction.lean` |
| L-function of a Weierstrass curve (local Euler factors use `Nat.card (W.reduction R).toAffine.Point`) | present as definition (2026) | `…/EllipticCurve/LFunction.lean:42-58` |
| `Finite`/`Fintype` instance for points over a finite field | **absent** (no `[Finite F]` anywhere in the EC tree) | grep of `Mathlib/AlgebraicGeometry/EllipticCurve/` |
| Hasse bound / Hasse–Weil | **absent** (no match for "hasse", "weil bound" in sparse tree incl. NumberTheory) | — |
| Discrete-log definition / DLP | **absent**; state ad hoc as `∃ k, k • P = Q`; `orderOf`, `Nat.card_zpowers`, cyclic groups present | `Mathlib/GroupTheory/OrderOfElement.lean:1143-1150` |
| Finite fields (GaloisField, card, Frobenius, polynomial facts) | present | `Mathlib/FieldTheory/Finite/{Basic,GaloisField,Polynomial,Trace,Extension,Valuation}.lean` |
| Gröbner bases as library objects | **absent**: only the multivariate division algorithm `MonomialOrder.div` (no Buchberger/S-polys/ideal-membership theory) | `Mathlib/RingTheory/MvPolynomial/Groebner.lean:128,232,243`; monomial orders in `…/MonomialOrder.lean`, `DegLex.lean` |
| Gröbner-style *tactic* | present in core: `grind` ring solver (Gröbner-inspired, `ringSteps` cap) and `grobner` wrapper; Mathlib `polyrith` is defunct (Sage server gone) | Lean reference §16.8; `Mathlib/Tactic/Polyrith.lean` header |
| Semaev summation polynomials | **absent** | grep |

Decision input: adequate for *statements* about curve groups and generic-group/DLP lemmas; Hasse, point counting, summation-polynomial material must be built in the lemma library. `Finite W.Point` over a finite field is a first item.

## Sources

### 1. Lean reference manual, "Validating a Lean Proof" (lean-lang.org/doc/reference/latest/ValidatingProofs/)
- Mechanism: escalating checks — (i) `lake build` with no errors/warnings; (ii) `#print axioms thm` must print only `propext`, `Classical.choice`, `Quot.sound`; `sorryAx` ⇒ incomplete; `Lean.trustCompiler` ⇒ native evaluation; since Lean 4.29.0 `decide +native`/`bv_decide` each add a *dedicated* axiom per computation, so the three-axiom rule catches them automatically; (iii) `lean4checker --fresh` replay; (iv) gold standard: `comparator` with external checker (nanoda). It states that `#print axioms` is meaningful only if you trust the statement and imported libs, and that external checkers cannot check native-evaluation proofs.
- Home: formalization gate (the exact ordered checklist). Cost: none beyond toolchain. Evidence: PROVEN-in-source (normative doc). Epistemics: none; it strengthens the gate. Borrow the axiom rule verbatim and reject any non-three-axiom set, which subsumes `native_decide`.

### 2. `leanprover/comparator` @ `575674928e239f5bc452aab72d1dd7b0f1326494` (2026-08-19, toolchain v4.34.0-rc1)
- Mechanism (read `Main.lean`, `Comparator/Compare.lean`, `Comparator/Axioms.lean`): config `{challenge_module, solution_module, theorem_names, permitted_axioms, external_kernels}`; `safeLakeBuild` (Main.lean:114) builds in a `landrun` sandbox; `safeExport` (:134) runs `lean4export`; `runBuiltinKernel` (:211) replays into the kernel; `runExternalKernel` (:152). `compareAt` (Compare.lean:67-87) requires challenge/solution targets to both be theorems with identical `ConstantVal` (throws "theorem statement do not match"), then `loop` (:37-58) walks `getUsedConstants` of the statement transitively and throws "Const does not match" if any referenced constant differs — closing redefinition attacks; `Axioms.lean:45` "Illegal axiom detected". `tests/projects/` is a 20-case attack catalog (`proj_trick`: same-named structure made uninhabited; `char_ofnat_issue`: prelude-level `Char` redefinition; `quot_mismatch`, `olean_issue`, `opaque_value`).
- Home: formalization gate — the PROVEN verdict function. Cost: Linux `landrun` (dev fallback `scripts/fake-landrun.sh`), `lean4export` pinned to the same Lean version, optional Rust build of nanoda; the Challenge project's imports/lakefile must be gate-owned. Evidence: PROVEN-in-source (tests exercise each attack). Epistemics: strengthens; also gives the Skeptic a mechanical "the thing proved is the thing stated" certificate.

### 3. `GasStationManager/SafeVerify` @ `b291b588a53999a7e837dda61c7dbfe8c550c814` (2026-04-22, toolchain v4.27.0)
- Mechanism (read `Main.lean`): target/submission `.olean` pair; `Environment.replay` (:160); rejects `unsafe`/`partial` (:155-158); `allowedAxioms := #[propext, Quot.sound, Classical.choice]` (:382); theorem type equality (:48-50, :298); definition bodies must match unless the target's def depends on `sorryAx` (:57-58); import-superset check to block type redefinition (:225-254); `Nat` literal corruption check (:286); `--disproofs` mode accepts a proof of the *negation* (:48-55).
- Home: formalization gate (lighter alternative to comparator, no sandbox); the `--disproofs` mode maps directly onto the dead-end ledger: a REFUTED entry can carry a mechanically matched disproof of the Challenge. Cost: olean-level only — does not see `implemented_by`/`extern` (README says scan source separately); Lean version lags (v4.27.0). Evidence: STRONG-EMPIRICAL (used by PutnamBench leaderboard; branches re-check DeepSeek-Prover-V2, Kimina, Seed-Prover outputs). Epistemics: strengthens.

### 4. `leanprover/lean4checker` @ `91a7f0e8e9dffe927089f5a6edcfeeb8a0e07709` (2026-03-25)
- Mechanism: README states it is deprecated and shipped inside the toolchain as `leanchecker` from v4.28.0: `lake env leanchecker --fresh Module`. `Main.lean` replays constants via `env.replay'`; README: "not an external verifier", detects environment hacking; `--fresh` single-module only.
- Home: gate step (iii). Cost: minutes per module; `.olean` must be built locally (bignum-library mismatch rejects cached oleans). Evidence: PROVEN-in-source. Epistemics: strengthens.

### 5. DeepSeek-Prover-V2 (arXiv 2504.21801v2, §3 note) + kimina-lean-server issue #75
- Mechanism (negative evidence): v2 of the report retracts 13 "7B-only" PutnamBench solves traced to a Lean 4.9.0 `apply?` UI bug that failed to emit `sorry` declarations (exploited via `Cardinal.toNat`); kimina issue #75: `by admit` is absent from the REPL `sorries` list so the client's `has_sorry` returned valid while messages carried "declaration uses 'sorry'".
- Home: formalization gate / Formalizer skill — forbids "no error messages" or "`sorries` list empty" as a PROVEN criterion. Cost: none. Evidence: STRONG-EMPIRICAL (published erratum; reproduced issue). Epistemics: protects the gate.

### 6. AlphaProof, Hubert et al., Nature 2025 (doi 10.1038/s41586-025-09833-y), Methods "Evaluation and Benchmarking", "Problem Formalization", "Verification and Judging"
- Mechanism: autoformalization candidates pass "majority voting, syntax checking, cycle consistency, and rapid disproof/proof attempts" before a ~3-person Lean-expert panel judges correctness; IMO statements were hand-formalized by experts; proofs were kernel-verified then judged by Gowers and Myers.
- Home: statement review — two borrowable mechanical pre-filters: round-trip (informalize the Lean statement blind and diff against the source claim) and a bounded "can a weak prover prove or disprove this in seconds" triviality/vacuity screen; final verdict stays human. Cost: extra LLM calls and a short prover budget per statement. Evidence: STRONG-EMPIRICAL that the pipeline was used; CONJECTURE that it transfers to research statements. Epistemics: fine if used only to *flag*, never to *pass*.

### 7. Harmonic Aristotle (arXiv 2510.01346 §2.1.6, §3.1, verification paragraph)
- Mechanism: solved ⇔ complete Lean/Mathlib proof with no `sorryAx`; statement autoformalization = formalize → judge with Lean REPL signals → correct; lemma proofs filtered by an LLM faithfulness judge vs the informal proof; IMO statements formalized by hand (the only human step); each found proof is re-rendered as a self-contained file, run through Lean, axioms listed, and the necessary lemmas recorded.
- Home: Prover/Formalizer workers (self-contained re-render + axiom listing as the handoff artifact to the gate). Cost: low. Evidence: STRONG-EMPIRICAL. Epistemics: the LLM faithfulness judge must stay a router, not a gate.

### 8. `google-deepmind/formal-conjectures` @ `e13dd728` (2026-08-20, toolchain v4.27.0): `STATEMENTS.md`, `FormalConjecturesUtil/Linters/*`
- Mechanism: a concrete review checklist (quantifier order/scope, strict vs non-strict bounds, hypotheses/domain, implication direction, `∃ x, P x → Q` trap, `answer(sorry)` must constrain the theorem, boundary cases `ZMod 0`, `x/0`, `sInf ∅`, impossible hypotheses) plus linters: `ExistsImplicationLinter` (flags the `∃ x, P x → Q` pattern), `StubLinter` (no `opaque`/`def := sorry`/new `axiom`), `AnswerLinter`, `CategoryLinter`.
- Home: statement-level review (checklist becomes the Skeptic's statement rubric; linters run in the gate as a pre-check). Cost: port linters to the gate's toolchain. Evidence: PROVEN-in-source that the linters exist; effect on error rate is CONJECTURE. Epistemics: strengthens.

### 9. `Shashi456/atp-checkers` @ `3e7e99d027fece04d9cd96288cdd040c366458e5` (2026-04-28, toolchain v4.30.0-rc2) + "Faults in Our Formal Benchmarking" (Ammanamanchi, Bhat, Biderman)
- Mechanism: 13 Lean metaprogram checkers with semantic guard proving (`assumption → omega → grind`); `VacuousCheck.lean` tries to prove `False` from the hypothesis telescope and detects empty binder types; Counterexample via `decide`/Plausible; `AxiomChecker.lean` flags user Prop axioms; paper reports 4,833 findings / 398 machine-certified across five benchmarks and recommends `proof_wanted` instead of `sorry` for open statements (Batteries command, imported globally by `Mathlib/Init.lean:34`), `autoImplicit false`, no axioms, version pinning.
- Home: formalization gate pre-check + lemma-library intake lint. Cost: toolchain coupling (v4.30.0-rc2 vs mathlib v4.34.0-rc1); "maybe" findings need triage. Evidence: STRONG-EMPIRICAL. Epistemics: strengthens (certified vacuity ⇒ automatic reject).

### 10. BEq / BEq+ symbolic equivalence (Poiroux et al., EMNLP 2025, aclanthology 2025.emnlp-main.907; Liu et al., ICLR 2025)
- Mechanism: prove candidate ⇔ reference with restricted `exact?`/tactic recipes; ICLR BEq 82.5→90.5% accuracy on 200 expert-labeled pairs; EMNLP paper reports high false-negative rate, type-check filtering critical.
- Home: lemma library (dedup of near-identical lemmas) and an optional *positive* signal in statement review. Cost: cheap CPU. Evidence: STRONG-EMPIRICAL, low recall. Epistemics: success is evidence, failure is not; never a gate.

### 11. Tooling maturity (GitHub API, this session)
`repl` @ `d84f94d` (2026-08-11, v4.34.0-rc1; JSON cmd/tactic modes, `sorries`, env pickling) — Formalizer interaction layer; `kimina-lean-server` wraps it with LRU import caching (1.5–2× faster per its paper). `leanprover/Pantograph` @ `d704b851` (2026-08-14, v4.31.0; goal-level tactic API). `LeanHammer` @ `f6d189d1` (2026-08-19; tags v4.20–v4.33; Zipperposition+Duper+Aesop+grind+premise server), `duper` v4.33.0 — one minor behind mathlib; `aesop`, `lean4export` at v4.34.0-rc1; `nanoda_lib` (2026-08-18), `loogle` (2026-07-09) active. `LeanDojo` README: deprecated in favor of LeanDojo-v2. Pinning: `lean-toolchain` + `lake-manifest.json` `rev` fields — record both in the PROVEN artifact.

### 12. Local skill `~/.claude/skills/lean-formal-feedback-loop/SKILL.md`
Encodes: `#print axioms` must show only the three axioms (PROOF-ARTIFACTS.md:61-65, :98), sha256 of the theorem source block, `lake build`, "no artifact, no closure". Missing: kernel replay (`leanchecker`/comparator), toolchain + manifest hash pinning, challenge/solution statement identity, awareness of `admit`/`apply?`-style sorry leaks, the native-evaluation axiom rule, sandboxing, any statement-review checklist or vacuity/counterexample lint. It is hard-wired to asupersync (Rust conformance, `cass`), so it is a pattern donor, not a reusable Formalizer skill.

## Rejected
- GTED tree-edit similarity (Kappa ≈0.4): a similarity score cannot gate PROVEN and would blur calibration.
- LLM faithfulness judges (Aristotle §2.1.6, Kimina post-RL judge, robustness-paper StmtSC) as a gate: routers only.
- Goedel-Prover-V2: verifier-guided self-correction is prover strategy (mutable), no statement-review mechanism found.
- LeanDojo (original): deprecated.
- `polyrith`: defunct external dependency.
- `decide +native` / `Lean.ofReduceBool`: extra axiom, uncheckable by external kernels — reject in gate.
- "No errors" / empty `sorries` list as verification: refuted by §5.
- Assuming mathlib has Hasse/point counts/DLP/summation polynomials: absent.

## Recommend /research-software next on
comparator on macOS vs Linux (`fake-landrun` fidelity); LeanDojo-v2; porting atp-checkers and formal-conjectures linters to v4.34; lean4export/nanoda version matrix; kimina-lean-server vs raw REPL throughput for Cairn's tiers; `leanchecker` CLI surface in v4.34.

## Sources (read this session)
lean-lang.org/doc/reference/latest/ValidatingProofs/ · github.com/leanprover/comparator @5756749 · github.com/GasStationManager/SafeVerify @b291b58 · github.com/leanprover/lean4checker @91a7f0e · arxiv.org/abs/2504.21801v2 · github.com/project-numina/kimina-lean-server/issues/75 · arxiv 2504.21230v3 · doi.org/10.1038/s41586-025-09833-y · arxiv.org/pdf/2510.01346 · github.com/google-deepmind/formal-conjectures @e13dd728 (STATEMENTS.md, Linters) · github.com/Shashi456/atp-checkers @3e7e99d · aclanthology.org/2025.emnlp-main.907 · ICLR 2025 BEq abstract · github.com/leanprover-community/mathlib4 @1f29011 · repl @d84f94d · leanprover/Pantograph @d704b851 · JOSHCLUNE/LeanHammer @f6d189d1 · lean-lang.org/doc/reference/latest/The--grind--tactic/ §16.8 · lean-dojo/LeanDojo README · alphaxiv 2504.11354 (Kimina-Prover Preview).
