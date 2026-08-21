# Cairn — proposed revisions to PLAN.md from the mechanism mining

Date 2026-08-21 · Status: **PROPOSAL, nothing landed.** `PLAN.md` is untouched. Each item below is
a rationale plus a git-diff-style change against `PLAN.md`, so it can be reviewed before it lands.
Evidence tags (PROVEN-in-source / STRONG-EMPIRICAL / CONJECTURE / SPECULATION) are applied to the
proposals themselves. Full evidence lives in `briefs/`; file:line citations there were printed by
the agent that wrote them, and the lines marked **[reviewer-checked]** were re-read by me.

## 0. Read first

**The honest baseline is intact.** Nothing here is an attack on the 254-bit instance and nothing
softens PLAN §0, §8, §14 or HANDOFF's baseline. The dives also produced *evidence for* the existing
design that is worth recording (item C5's incident table): every documented way a prior autonomous
research system fabricated or gamed maps onto a gate Cairn already has.

**Standing constraint — borrow mechanisms, never code.** All six primary repos carry the identical
"MIT License (with OpenAI/Anthropic Rider)" (`LICENSE:1-45` in each, **[reviewer-checked]**),
whose definition of "use" includes analyzing or incorporating the software into "any … evaluation
harness, or pipeline for machine learning or other automated systems" and whose Restricted Parties
include anyone acting on behalf of or for the benefit of OpenAI/Anthropic. Every proposal below is
therefore stated as a mechanism to re-implement from the primary paper/spec (cited), never as a
dependency or a vendored file. All of them are small (tens to a few hundred lines) and textbook.
Whether anything further follows from the rider is the operator's decision, not this review's.

**Scorecard.** ≈70 distinct mechanisms were read across 6 primary repos, 13 adjacent projects and
≈25 papers/specs. 14 proposals are marked confident, 7 need a prototype, the rest are rejected
explicitly in §3 (including both mechanisms HANDOFF named as hypotheses: RaptorQ is rejected as
homeless for M0–M3; e-values are adopted narrowly, with one invariant fencing them).

**Two negative findings that shaped everything:** (1) the suite's own "e-process" gates are uneven —
frankensearch's PhaseGate multiplies a factor with E[f]>1 under its own null and decides two-sided
on 1/e (`frankensearch-fusion/src/phase_gate.rs:152-270` **[reviewer-checked]**; null crossing
≈36–51% vs a claimed 5%, `briefs/frankensearch.md` §3), and frankensqlite's SSI gate uses an
e-process to *skip* a correctness check (`briefs/frankensqlite.md` M3). The valid primitive is ~30
lines (`fsqlite-types/src/eprocess.rs:173-215` **[reviewer-checked]**: fixed-λ Bernoulli betting
supermartingale, λ clamped to (−1/(1−p0), 1/p0)); everything accretive is the *protocol around* it,
and the one invariant that keeps it honest is C2(b). (2) "Certificate" in this suite mostly means a
calibration bound, not a verifiable witness; Cairn's §3 certificate must be a witness (C4).

---

## 1. Confident proposals (sorted by expected accretion per cost, highest first)

### C1 · Formalization gate = challenge/solution protocol with kernel replay, axiom allow-list, and statement-closure identity
**Component.** Gate layer: formalization gate (§4, §7); Formalizer/Prover workers; resolves HANDOFF's
open decision on the Lean/mathlib stack.
**Why.** "Green Lean" is under-specified in three ways the prior art has already paid for. (a) Lean
exits 0 on `sorry`; DeepSeek-Prover-V2's report retracted 13 PutnamBench solves traced to an
`apply?` UI bug that failed to emit `sorry` declarations (arXiv 2504.21801v2 §3 note), and
kimina-lean-server #75 shows `by admit` absent from the REPL `sorries` list — so "no error messages"
and "sorries list empty" are both refuted as PROVEN criteria (STRONG-EMPIRICAL). (b) The Lean
reference manual's "Validating a Lean Proof" names the escalating checks: `lake build` clean,
`#print axioms` ⊆ {propext, Classical.choice, Quot.sound} (since Lean 4.29 `decide +native` and
`bv_decide` each add a dedicated axiom, so the three-axiom rule rejects native evaluation
automatically), `leanchecker --fresh` kernel replay, and as gold standard `comparator` with an
external kernel (PROVEN-in-source, normative doc). (c) `leanprover/comparator` @5756749
implements the protocol Cairn's statement-level review needs half of: a gate-owned Challenge module
holds the statement, the Formalizer submits a Solution, `compareAt` (`Comparator/Compare.lean:67-87`)
requires identical `ConstantVal` and then walks the statement's transitive `getUsedConstants`,
throwing on any differing constant (closes redefinition attacks; `tests/projects/` is a 20-case
attack catalog); `Axioms.lean:45` rejects illegal axioms; sandboxed `lake build`. `SafeVerify`
@b291b58 is the lighter olean-level variant and its `--disproofs` mode accepts a proof of the
*negation* (`Main.lean:48-55`) — which is exactly what a REFUTED ledger entry should be able to carry
(PROVEN-in-source; used by PutnamBench). mathlib @1f29011 (toolchain v4.34.0-rc1): Weierstrass
curves, proved affine group law (`…/Affine/Point.lean:780`), division polynomials, finite fields
present; `Finite W.Point` over a finite field, Hasse bound, a DLP definition, Gröbner bases as
library objects, summation polynomials **absent** (`briefs/adjacent-proof-automation.md` table).
**Cost.** Linux `landrun` sandbox for comparator (dev fallback `scripts/fake-landrun.sh`),
`lean4export` pinned to the Lean version, optional Rust nanoda build; record `lean-toolchain` +
`lake-manifest.json` rev in every PROVEN artifact. Statement-closure identity mechanizes "the thing
proved is the thing stated"; "the Challenge says what we mean" stays with the human/Skeptic (C11).
**Epistemics.** Strengthens non-negotiable #2; nothing else changes.
**Diff (PLAN §7, §11, §12):**
```diff
 - **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
   (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
+  **"Green Lean" is defined as the challenge/solution protocol:** the gate owns a Challenge
+  module holding the statement; the Formalizer submits a Solution; the gate (i) rebuilds in a
+  sandbox under the pinned `lean-toolchain` + `lake-manifest` rev recorded in the artifact,
+  (ii) kernel-replays (`leanchecker --fresh`, comparator/nanoda at the gold tier),
+  (iii) requires `#print axioms` ⊆ {propext, Classical.choice, Quot.sound} — which rejects
+  `sorryAx`, `native_decide`/`bv_decide` axioms and any custom axiom — and (iv) requires the
+  Challenge and Solution theorem statements to be identical over the statement's transitive
+  constant closure. "No error messages" or an empty `sorries` list is never a PROVEN criterion.
+  A REFUTED ledger entry may carry a machine-matched proof of the Challenge's negation.
...
 - **Formalized-lemma library (shared, mathlib-style):** every `PROVEN` lemma lands here, so
   month N is cheaper than month 1 — deeper scaffolding is what "accretive" means.
+  *Coverage decision (mathlib @1f29011):* adequate for statements about curve groups and
+  generic-group/DLP lemmas (proved affine group law, division polynomials, finite fields).
+  First library items, absent upstream: `Finite W.Point` over a finite field, Hasse bound,
+  a DLP definition (`∃ k, k • P = Q`), summation polynomials.
```

### C2 · Calibration-layer invariants: tags are derived through a lattice; statistical monitors may block or alarm, never promote; tag history is append-only and attributed
**Component.** Calibration layer (§7) and claims DB (§4); foundations auditor.
**Why.** (a) frankengraphdb's `fgdb-claim` enforces "weaker evidence may inform but never justify
stronger" as `try_justify(self,target) → Justification | LatticeViolation` over closed ranks, with
a sealed type-level twin so an illegal pair is a compile error, and an evidence-kind cap (a Lean
model-only proof may justify at most bounded-model; refined-to-implementation may justify proof;
statistical evidence at most statistical) — `crates/fgdb-claim/src/lib.rs:70-96`
**[reviewer-checked]**, `:153-226, 484-548`; all 36 pairs unit-tested (`:581-640`), transitivity at
56 triples by compilation (`tests/claim_lattice_laws.rs`). PROVEN-in-source. The claim class is
*derived* from the strongest justifying evidence, never a settable field
(`briefs/focus-calibrate-evidence-certificate-family.md` synthesis). (b) The suite's own misuse
catalog is the argument for one sentence: PhaseGate decides on `1/e` (two-sided, invalid); the SSI
gate docstring claims α bounds missed pivots when Ville bounds only false alarms
(`ssi_eprocess_gate.rs:59-64`); `evalue_eviction.rs` reads `1/e` as "probability the page is hot";
frankensearch's adaptive α moves *toward* observed error; fgdb's exploration bound peeks. The
counter-rule is practiced in the same codebase: `fsqlite-harness/src/eprocess.rs:338, 1971-1984`
asserts hard invariants deterministically and gives the e-process only a stochastic rate. (c)
frankensqlite's `ratchet_policy.rs:371-549` (tested `:715-1320`, STRONG-EMPIRICAL) has the
no-silent-regress shape: a level moves up only through an explicit Allow; a down-move needs an
attributed, reason-bearing record; a non-waivable floor sits under the top level.
**Cost.** ~200 lines (rank table + `justify` + append-only history + one transitive check over the
claims DAG). Type-level enforcement only if the claims DB is in a typed language.
**Epistemics.** This is §0 made mechanical at the tag level; it is the single cheapest
strengthening in this document.
**Diff (PLAN §7):**
```diff
 - **Calibration taxonomy (mandatory per claim):** `PROVEN` (formalized) · `STRONG-EMPIRICAL`
   (ladder + repro node) · `CONJECTURE` · `SPECULATION`. No green Lean check → not `PROVEN`.
+  **The tag is derived, never set.** Each evidence kind has a maximum class it may justify
+  (green Lean via the C1 protocol → PROVEN; ladder + repro node → STRONG-EMPIRICAL;
+  sampled/statistical evidence → at most STRONG-EMPIRICAL on its declared population; Lean
+  proofs about a *model* → at most CONJECTURE); a claim's tag = the strongest class that some
+  evidence node justifies via `justify(evidence, target)`, which returns a typed justification
+  or a lattice violation, never a boolean. A weaker class may inform a stronger claim; it may
+  never justify it. The foundations auditor's core query is the transitive form: no PROVEN
+  claim may carry a `justified_by` edge to a weaker premise.
+- **Statistical monitors block or alarm; they never promote.** An e-value, conformal bound,
+  posterior, or similarity score may withhold a promotion, trigger extra scrutiny, or raise an
+  alarm. It may never move a tag upward, and non-rejection is never positive evidence.
+- **Tag history is append-only and attributed.** Every tag transition records who/what moved it
+  and the evidence node; a downgrade requires an evidence pointer (refutation, retraction,
+  failed re-verification); PROVEN has a non-waivable floor (the C1 artifact must exist and
+  re-verify). Nothing is edited in place.
```

### C3 · Substrate key and cache semantics: canonical typed encoding, (hash,size) digests, and four cache-control bits
**Component.** Substrate (§3); reproducibility gate; Skeptic re-runs.
**Why.** PLAN's "REFUTED recognized by hash" is only as sound as the canonicalizer. Bazel REAPI
(`remote_execution.proto` @becdd8f) is the widest-deployed definition of "semantically identical
computation ⇒ identical key": key = digest of the canonical binary encoding of
Action{command_digest, input_root_digest, timeout, do_not_cache, salt, platform}; normative rules
fields-in-tag-order / no unknown or duplicate fields / sorted env vars and output paths / sorted
directory children (`L55-62, L716-795, L925-933, L1097-1107`); `Digest` = (hash, size) with size
integral; BLAKE3 is an enumerated digest function (`L2125-2200`). REAPI lets non-canonical inputs
split into distinct keys (`L55-62`), so Cairn must canonicalize *at write time*. Its cache bits are
the vocabulary Cairn is missing: `do_not_cache` (`L651-653`), `skip_cache_lookup` = execute even if
cached and overwrite (`L1527-1539`), `status≠OK ⇒ MUST NOT be cached` (`L1605-1615`), `salt` to
disown a poisoned class (`L657-663`). PROVEN-in-source (spec). The same shape appears in the suite:
frankensearch's `CanonicalEncoder` (domain tag `.vN`, length-prefixed, big-endian ints, Option tag;
`frankensearch-core/src/generation.rs`, 109 tests) and frankensqlite's
`ObjectId = BLAKE3("fsqlite:ecs:v1" ‖ canonical_header ‖ payload_hash)` (`fsqlite-types/src/ecs.rs:14-100`;
keep 256 bits, not their 128-bit truncation). Buildbarn's `CompletenessCheckingBlobAccess` /
bazel-remote's `GetValidatedActionResult` (`cache/disk/disk.go:812-930` @ead2079) serve a cached
result only if every referenced blob is present. No off-the-shelf CAS fits (see C14).
**Cost.** ~200 lines: one canonical encoder with a known-answer test vector, three boolean columns
and a salt, one completeness check on the read path.
**Epistemics.** A cache hit must never stand in for a gate pass; the Skeptic's independent re-run
is `skip_cache_lookup=true` by construction; failed results are never cached.
**Diff (PLAN §3):**
```diff
 - **Every artifact is hashed by `(skill@version, inputs-by-hash, seed, tool-versions,
   container-digest)`.** Provenance stops being an audit you run afterward and becomes how
   results are stored. A result not in the substrate does not exist to the claims DB.
+  *Key construction:* the key is BLAKE3-256 over a canonical, typed, domain-separated
+  encoding of that tuple (fields in fixed order, sorted maps/sets, length-prefixed
+  variable-length fields, no unknown fields, `(hash,size)` digests for inputs), enforced at
+  write time and covered by a known-answer test vector. Two logically equal recipes that hash
+  differently are a bug in the canonicalizer, not a feature.
+  *Cache bits on every node:* `do_not_cache` (never memoize), `skip_cache_lookup` (run even
+  if cached, overwrite; the Skeptic's re-runs always set it), `status≠OK ⇒ never cached`,
+  and a `salt` that moves a whole class of results into a fresh namespace when a tool
+  version is found faulty. A cached result is served only if every blob it references is
+  present; otherwise it is recomputed.
```

### C4 · Certificates are witnesses; every node carries a replay-completeness grade; the reproducibility gate is a `--check`-style re-run
**Component.** Substrate (§3), reproducibility gate (§4), Tier-2 rho skill (§5), Skeptic.
**Why.** (a) Nix's fixed-output derivation is the standard model for non-replayable work: the
output's content address is declared in advance, the build fails on mismatch, input-addressed
derivations must be pure, impure ones must be fixed-output; the manual's design note proposes a
stand-alone assertion object separate from the derivation — Cairn's certificate
(`nix.dev/manual/nix/2.34/store/derivation/outputs/content-address`, PROVEN-in-source). Nix
`--check` rebuilds an existing output, compares bitwise, exits 1 "may not be deterministic", keeps
the divergent copy at `<path>.check` and runs `diff-hook` only on mismatch — the mechanical
definition of "replayable" (`advanced-topics/diff-hook`). (b) The collision-search literature gives
the rho witness exactly: two distinguished-point triples (X,a,b),(X,c,d) with b≢d yield
x ≡ (a−c)(d−b)⁻¹ mod n (van Oorschot–Wiener 1999 §5.1); the verifier checks aP+bQ = X = cP+dQ (four
scalar multiplications) then xP==Q and must *reject* b≡d rather than retry silently; ≈60 bytes at
60 bits plus the walk definition (`briefs/adjacent-distributed-collision-search.md` §1). Storing
seeds instead of (a,b) (Bernstein et al. 2016 §3; ECC2K-130) shrinks reports but makes
verification O(1/θ) — a Tier-3 storage optimization, not the certificate. (c) fgdb-evidence's
`ReplayCompleteness ∈ {Replayable, StructuralReplay, VerifiableIfArtifactsSupplied, AuditOnly}`
with `weaken_for_redaction` monotone downward (`crates/fgdb-evidence/src/lib.rs:459-520, 647-668`,
PROVEN-in-source) and frankensqlite's `ScheduleProvenance{ObservationOnly|Deterministic,
schedule_sha256, replay_command}` where observation-only runs "never claim deterministic replay"
(`serializability_oracle.rs:50-80`) are the same refinement of PLAN's "replayable ≠ verifiable".
(d) frankensearch's "recall certificate" is a conformal *bound*, not a witness
(`frankensearch-index/src/recall_certificate.rs:28-75` **[reviewer-checked]**: the
⌊α(n+1)⌋-th smallest calibration recall, trivial 0.0 when n is too small) — correct, but it does not
solve the succinct-certificate problem; witnesses do.
**Cost.** A certificate schema {declared content address, witness, producer skill@version,
producer's calibration tag}; a grade column; one extra run per checked artifact; root the divergent
copy (Nix does not GC-protect `.check` paths; Cairn must).
**Epistemics.** A certificate certifies identity and checkability, never truth: the artifact keeps
its producer's tag. AuditOnly nodes are inadmissible as evidence.
**Diff (PLAN §3):**
```diff
 - **Replayable ≠ verifiable.** Deterministic work (a Sage computation) is bit-reproducible.
   Nondeterministic/expensive work (distributed rho) is not — store a **succinct
   certificate cheap to check** (the found relation, seed, walk definition) instead of a
   full replay. Same move as verify-before-submit: check the answer, don't redo the search.
+  *Grades:* every node carries `replay ∈ {Replayable (bit-identical re-run), Verifiable
+  (witness checked by a deterministic verifier), AuditOnly (logs only)}`; the grade can only
+  be weakened, and AuditOnly is inadmissible as evidence. *Certificate = declared content
+  address + witness:* for a rho/kangaroo run the witness is the curve, n, P, Q, the walk
+  definition (multipliers or their PRNG seed, index function, DP predicate θ) and the two
+  colliding DP triples (X,a,b),(X,c,d); the verifier checks aP+bQ = X = cP+dQ, rejects b≡d,
+  computes x and checks xP==Q. A certificate never raises the producer's calibration tag.
+  *Reproducibility gate = `--check`:* re-run the recipe (or re-check the witness) and compare
+  bitwise; on divergence keep the second copy rooted as evidence of non-reproducibility and
+  mark the node inadmissible.
```

### C5 · Every gate ships a planted-failure self-test; gates run from a declarative plan, fail closed, and waivers are explicit, attributed, expiring — plus the incident table that is evidence *for* the design
**Component.** Gate layer (§4), skill self-tests (§2), tier gate (§5).
**Why.** franken_markdown's gate scripts each have a `--self-test` that plants a violation and
asserts detection, plants an allow-listed case and asserts pass, then runs live; CI runs the
self-tests before the real gate (`scripts/check-claim-discipline.sh:110-144`,
`check-test-doubles.sh:83-105`, `.github/workflows/ci.yml:44-60`; PROVEN-in-source).
frankensqlite's `verification_gates.rs` (declarative `GateSpec` with expected exit codes incl.
expected-failure greps, ordered scopes where an earlier failure blocks and records why, raw output
retained; `:279-354, 585-1350, 1367-1407`) and `confidence_gates.rs` (invalid config ⇒ Fail,
`:474-475`; waiver flag mandatory in serialized config, `:1015-1029`; external enforcement can only
downgrade) are working code for "mechanical, immutable checks" — with the caveat that in that repo
`Waived` counts as satisfied by default (`confidence_gates.rs:72-83`) and parity obligations are
hand-stamped Verified with empty artifact lists (`parity_invariant_catalog.rs`); Cairn must invert
both. frankenfs's `release_gate.rs:717-940` folds every finding with `more_conservative`, stale
proof (git sha/timestamp) forces Disabled, and a lane that passed but whose provenance class is
dry-run/small-host/stale/missing-raw-log "cannot strengthen public readiness" (`proof_bundle.rs:2128-2240`;
STRONG-EMPIRICAL). The prior-art incident table (`briefs/adjacent-agent-orchestration.md` Q2):
AI Scientist v1 edited its own time limit and hallucinated an ablations table (arXiv 2408.06292v3
§8) → tier gate + reproducibility gate; AI Scientist v2's verified-but-wrong figures (2504.08066
§4.2) → statement-level review + ladder; AI CUDA Engineer's evaluator memory exploit and
single-input overfitting (2509.14279 §3, App. A) → verifier as subprocess + C6(a); DGM removing the
instrumentation that detected its hallucinations (2505.22954v2 App. H) → §0 + substrate lineage.
**Cost.** One negative fixture per gate; a gate-plan file kept in the immutable layer.
**Epistemics.** This is the mechanical defense against silent-fail-open gates (the failure the
enforcement-over-instructions rule names). Nothing softens.
**Diff (PLAN §4 gate layer):**
```diff
 - **Gate layer (mechanical, immutable):** submission verifier (`xP==Q` subprocess or no
   submit, ever) · small-scale ladder §6 · no-go checklist §8 · formalization gate §7 ·
   reproducibility gate (no substrate node = inadmissible) · proportional-scrutiny router §7
   · tier gate §5.
+  *Gate discipline:* every gate ships a planted-failure self-test (a fixture that must FAIL
+  and one that must PASS) run before the gate itself; gates run from a declarative plan with
+  expected exit codes and ordered scopes where an earlier failure blocks later ones and
+  records why; invalid or missing gate config fails closed; a waiver is explicit, attributed,
+  reason-bearing and expiring, and a waived check never counts as satisfied; a green result
+  whose provenance is weaker than required (dry run, missing raw output, stale tool digest)
+  cannot strengthen a claim. The gate plan, the no-go set and the waiver registry live with
+  the gates, out of the orchestrator's write path.
```

### C6 · Ladder hardening: fresh instances, distributions not single runs, ops not seconds, a quantitative BSGS bar, and an A/A-null decision band for speedup claims
**Component.** Small-scale ladder (§6); calibration layer's STRONG-EMPIRICAL definition.
**Why.** (a) The documented exploit class for automated evaluators is overfitting a fixed input
(AI CUDA Engineer, 2509.14279 §3): the ladder must generate a fresh random prime-order curve and
random (P,Q) per run, at several sizes, never an instance the worker has seen (STRONG-EMPIRICAL in
that domain, CONJECTURE by analogy here — but free). (b) Bernstein–Lange–Schwabe (PKC 2011 §6) ran
32,237 / 257,241 / 33,791 independent DLPs on 2^50/2^55/2^60 prime-order subgroups obtained by
varying b with the prime fixed, DP probability 2^-20, and measured mean DP count
1.0789/1.0074/0.9996 × √(πℓ/4)/2^20 with sd ≈ 0.53–0.56 × mean; Bernstein et al. 2016 §5 ran 1024
DLs per size, compared the sorted distribution to rho theory, spot-checked against an independent
implementation, and their record run was "unlucky by 2.55×" — a single run calibrates nothing
(STRONG-EMPIRICAL). (c) Measured this session (Python+gmpy2, one core): 30-bit rho 25k–45k ops,
BSGS 33k–58k ops; 40-bit rho 0.95M–1.47M ops (≈1 s), BSGS 1.5M–1.8M ops with a 0.92M-entry table;
50-bit rho 4.2M and 30.3M ops (2.9 s, 20.7 s); every run verified xP==Q. Derived bar: rho ≈1.25√n
ops, BSGS ≈1.5√n ops and √n memory ⇒ at 50 bits rho ≈4×10⁷ ops vs BSGS ≈5×10⁷ ops + 33.5M entries
(≈0.4–0.8 GB in C); at 60 bits rho ≈1.35×10⁹ ops (2–3 min in C, BLS: 362 cycles/iteration) while
BSGS needs 2³⁰ entries (≥12 GB). So "beats BSGS at 50 bits" = fewer than ~5×10⁷ group ops and <1 GB
at 50 bits and *completes* at 60 bits; scaling must be reported in group ops against √n
(60/50-bit ratio ≈32×), not seconds (STRONG-EMPIRICAL ≤50 bits; CONJECTURE at 60). (d) For any
speedup claim, frankensqlite's A/A-null decision band: run an A/A arm, `null_radius =
max|CI_AA − 1|`, KEEP only if the entire claim CI clears `max(1+2·radius, 1.01)`
(`fsqlite-e2e/benches/pipeline_stage_bench.rs:1262-1283`, tests `:1545-1568`; PROVEN-in-source);
frankensearch's `verify_run_stability` (IQR-trim, CV ≤ max, n ≥ min; `metrics_eval.rs:624-700`).
(e) Galbraith–Gebregiyorgis (INDOCRYPT 2014) is the reporting template: columns n, l, #Var,
D_reg, T, Mem, P_succ over 100 trials with a patience threshold, and a closing bound that becomes
a negative-results entry.
**Cost.** Compute only: ≥10² runs per size (seconds at ≤50 bits, minutes–hours at 60).
**Epistemics.** Tightens §6; also hardens the verifier against the one exploit class documented.
**Diff (PLAN §6):**
```diff
 Any claimed *algorithmic* advance must, mechanically, before it earns attention at full
 size: run end-to-end on prime-order toy curves (~30/40/50/60 bit), actually recover `x`
 (`xP==Q`), and show measured scaling matching its *claimed* asymptotic. A "subexponential
 attack" that can't beat baby-step-giant-step at 50 bits is refuted on the spot. Cheap,
 mechanical, near-impossible to fake; kills the dominant failure mode (proof-shaped text
 that's subtly wrong).
+**Protocol.** (1) The ladder generates its own instances: a fresh random prime-order curve
+and random (P,Q) per run, at each size, never a fixed instance the worker has seen. (2) It
+gates on distributions, not runs: ≥10² independent trials per size (sd ≈ 0.5×mean for rho),
+sorted-distribution shape compared to the claimed model, and an A/A null arm whose CI radius
+sets the decision band (KEEP only if the whole claim CI clears 1+2·radius, floor 1%). (3) It
+reports group operations against √n, not seconds. (4) The bar is quantitative: at 50 bits
+the baseline is rho ≈1.25√n ≈ 4×10⁷ ops and BSGS ≈1.5√n ops with ≈3×10⁷ table entries;
+"beats BSGS at 50 bits" means fewer than ~5×10⁷ group ops and under 1 GB, and the method
+must complete at 60 bits where BSGS needs 2³⁰ entries. (5) The result table (size, trials,
+mean/sd ops, memory, success rate, fit to claimed exponent) is the ladder's artifact and the
+template for a negative-results entry.
```

### C7 · Skill identity bundle + known-answer certificate, ratcheted conformance corpus, and two-implementation agreement at Tier-0
**Component.** Skill interface + self-tests (§2); substrate key (§3); Tier-0 verifier (§4).
**Why.** frankensearch's `EmbeddingIdentityBundleV1` = {space (model id, immutable revision,
role-tagged artifacts each with SHA-256+size), producer (backend, implementation revision, protocol
revision, numeric profile, provenance-manifest fingerprint), golden certificate} where the
certificate is a domain-separated hash over a canonical transcript of a fixed ordered corpus and the
exact `f32::to_bits` outputs; a changed producer with an identical space ⇒ `CertificateRequired`,
mismatch ⇒ `GoldenVectorMismatch`, fail-closed (`frankensearch-core/src/generation.rs:1780-1860,
2220-2300, 2363-2412, 2560-2580`; test `model_manifest.rs:3351-3400`; STRONG-EMPIRICAL).
franken_markdown vendors the official corpus, writes a per-example ledger
(`pass | intentional_non_goal | known_gap`), enforces a committed integer floor that only
`--update-floor` may raise, and makes the tool *advertise* its own floor so flag and floor cannot
drift (`scripts/commonmark-conformance.sh:57-164`; STRONG-EMPIRICAL); every corpus test re-renders
and asserts byte equality (`tests/corpus_soak.rs:92-96`). Sage's `discrete_log(...)` verifies its
answer before returning (`sage/groups/generic.py:807-809`) and `cardinality(algorithm='all')`
cross-checks PARI vs Sage's own BSGS and raises on disagreement; `P.log(Q)` checks subgroup
membership first because PARI's generic DL "may enter an infinite loop" without a solution
(PROVEN-in-source; doctests are ready known-answer seeds). asupersync's lab recipe is the checklist
of what to pin for a replayable self-test: one seed → RNG, seeded hashers on every hot-path
set/map, virtual clock, one RNG draw per step recorded (`src/lab/runtime.rs:2066-2135, 3710-3731`;
PROVEN-in-source).
**Cost.** Schema discipline plus a committed floor file and corpus per skill; bit-exact outputs need
a pinned numeric profile (floats) or a declared tolerance.
**Epistemics.** Strengthens §2; the floor is a lower bound and the non-goal set is fixed in the
immutable layer (an orchestrator that could edit the non-goal set would own its own pass rate).
**Diff (PLAN §2):**
```diff
 - **Every skill ships a known-answer self-test.** Decomposition multiplies the places a
   subtle error can hide; each unit validates itself on cases where the answer is known.
   This is the ladder pushed down to the component level.
+  *Shape:* a skill's identity is a typed bundle {interface version, implementation revision,
+  tool and container digests, numeric profile}; its self-test is a vendored known-answer
+  corpus with a per-case ledger, a committed pass floor the skill advertises about itself
+  (a lower bound that only an explicit update may raise), and a golden certificate = hash of
+  the canonical transcript of the corpus and the exact outputs; a changed implementation
+  with the same interface needs a fresh certificate, and a mismatch fails closed. Self-tests
+  pin every nondeterminism source (seed, hashers, clock) and assert byte-equal double runs.
+  Tier-0 arithmetic skills verify their own answer before returning and, where two
+  independent implementations exist (PARI vs Sage), require agreement or raise.

### C8 · Dead-end ledger preflight (Allowed | Blocked | RequiresNullControl), retry predicates, and near-duplicate advisory routing
**Component.** State layer: dead-end ledger (§4); negative-results map (§11); Librarian.
**Why.** frankensqlite keeps a 583-entry negative-results ledger where every entry carries target,
evidence, an A/A null control, result, and a concrete *retry condition*; a preflight gate answers
`Allowed | Blocked | RequiresNullControl` for a proposed candidate — `Blocked` forbids the work,
`RequiresNullControl` means the prior REJECT lacked an A/A null and must be rerun before anything
new is proposed (`fsqlite-harness/src/sql_pipeline_optimization.rs:733-797`, tests `:1318-1438`;
PROVEN-in-source for the gate). Their adjudication classes (VALID-PROFILE / VALID-MECHANISM /
VALID-AB / VOID-CV / VOID-ZEROSELF / VOID-NONULL) and the rule that mechanical void-screens build a
reading queue, never a verdict (`docs/LEDGER_RESURRECTION.md:40-130`), map onto REFUTED vs PARKED.
A reachability gate (zero dispatches ⇒ timing not interpreted) is the no-go checklist's cousin.
frankensearch's `NEGATIVE_EVIDENCE.md` entry schema {hypothesis, immutable receipt hash, method,
result+CI, decision, retry predicate} and fgdb's {doctrine, claimed, actual, caught_by, signature}
are the same record. For near-duplicates, frankensearch's 64-bit SimHash over 3-token shingles
(`frankensearch-core/src/fingerprint.rs:25-110, 252-330`, 23 tests; PROVEN-in-source) and
ShinkaEvolve's embedding rejection (cos > 0.95; `shinka/llm/prioritization.py`) are cheap, but both
co-scientist's Proximity agent and Shinka use similarity to *reject*, which would let similarity
edit the ledger; Cairn keeps REFUTED-by-exact-hash and uses similarity only to route.
**Cost.** Structured records (not frankensqlite's markdown-heuristic parser); ~150 lines SimHash.
**Epistemics.** Strengthens "REFUTED is permanent unless the retry predicate is met"; similarity
never changes a status.
**Diff (PLAN §4 state layer, §11):**
```diff
 - **State layer:** branch tree (`{id, parent, hypothesis, status∈{active,parked,refuted,
   promoted}, priors, effort, yield, blocker?}`); **dead-end ledger** with `REFUTED`
   (proven dead → permanent blacklist, recognized by hash §3) vs `PARKED` (blocked-not-dead,
   tagged with blocker → auto-revived when blocker clears); **claims DB** (mandatory
   calibration tag §7, pointer to evidence node); substrate §3 is the reproducibility store.
+  *Ledger preflight:* before any branch is funded the ledger answers `Allowed | Blocked |
+  RequiresNullControl`: `Blocked` = hash matches a REFUTED entry whose retry predicate is
+  unmet; `RequiresNullControl` = a prior refutation rests on a measurement without a null
+  control and must be re-measured first. Every REFUTED/PARKED entry carries {hypothesis
+  hash, evidence node, method, result (+CI where measured), decision, retry predicate,
+  caught_by}. A near-duplicate signal (SimHash / embedding similarity to a REFUTED entry) is
+  advisory only: it routes the proposal to the Librarian, who must state the difference; it
+  never sets a status.
```

### C9 · Roots-based GC and a hash-chained, compare-and-swap ledger log
**Component.** Substrate retention (§3); state layer (§4).
**Why.** Nix liveness = closure reachable from explicit GC roots, `keep-derivations` keeps recipes
of live outputs while outputs may die; Cairn's "lineage forever" is stricter and is modeled as
"recipes, ledger rows, certificates and divergence copies are always roots; only blobs are
collectable" (Nix manual `nix-store --gc`, `conf-file`; PROVEN-in-source). For the ledger itself,
fgdb-chronicle's markers: `chain_hash = BLAKE3(domain ‖ prior_chain ‖ canonical_bytes)`
(`crates/fgdb-chronicle/src/marker.rs:180-187` **[reviewer-checked]**), `marker_oid = chain_hash`
so identical content at different positions has a distinct history identity, `HeadUpdate{graph,
branch, expected_previous}` is a compare-and-swap where all heads in a marker are checked before any
is applied, gap-free `commit_seq`, and `verify` replays every append-time law from origin
(`marker.rs:412-440, 495-516, 533-560`; tests `tests/commit_stream.rs:85-709` cover tamper at any
field, failed CAS leaves every branch untouched, prefix verifies without suffix; PROVEN-in-source).
frankensqlite's `commit_marker.rs` is the same idea with BLAKE3 domain separation; its
`SsiEvidenceLedger::compute_chain_hash` concatenates variable-length lists without length prefixes
(reframing collisions, `ssi_abort_policy.rs:1528-1572`) — the one shape not to copy.
**Cost.** A roots table + mark phase over lineage edges; in SQLite a `chain_hash` column and an
`expected_previous` check in the same transaction (~100 lines) or ~600 lines standalone.
**Epistemics.** Gives "the orchestrator may rewrite the tree but never REFUTED entries" a
tamper-evident form: a rewritten history fails verification.
**Diff (PLAN §3 retention):**
```diff
 - **Retention:** keep lineage + certificates forever (cheap, load-bearing); GC the giant
   intermediate blobs once their derivation is recorded and the result verified. Keep the
   edges, prune the mass.
+  *Mechanism:* recipes, ledger rows, certificates and recorded divergences are GC roots;
+  liveness is reachability from roots over lineage edges; only blobs are collectable. The
+  ledger and branch-tree history are an append-only, hash-chained log
+  (`chain = H(domain ‖ prior_chain ‖ canonical_record)`, length-prefixed fields) with
+  compare-and-swap head advancement, re-verifiable from origin; an orchestrator that
+  rewrites history produces a log that fails verification.
```

### C10 · Skeptic isolation by construction; hide the rubric from the gated worker; disagreement is preserved, never majority-voted
**Component.** Workers (§4), calibration layer (§7), panel (§10).
**Why.** Claude Agent SDK subagents start with a fresh context; "the only content you pass from
parent to subagent is the Agent tool's prompt string"; per-agent tool allow/deny lists
(platform.claude.com/docs/en/agent-sdk/subagents; PROVEN-in-source as docs) — so "sees only the
statement" is enforceable by construction, not by instruction. DGM's authors report that
objective hacking rose when the detection functions were visible to the agent and that the agent
removed the instrumentation (2505.22954v2 App. H; STRONG-EMPIRICAL, small n). AI co-scientist's
Meta-review appends feedback to agents' prompts (2502.18864 §3.3.2) — the channel a prover must
never have into the skeptic. frankenfs's cross-oracle arbitration never majority-votes; it preserves
conflicting evidence with artifact hashes, classifies the conflict (model/kernel/product/harness/
fixture/scope/capability/inconclusive), routes ownership, and fails public claims closed while
unresolved (`ffs-harness/src/cross_oracle_arbitration.rs:3-8, 121-134`; CONJECTURE — header and
enums read, validator body not). This is the operational form of §10's "surfaces its own
disagreement" and of the reviewer rule that convergence is not proof.
**Cost.** Zero beyond discipline and a conflict record type.
**Epistemics.** Strengthens independence; no status is ever decided by vote.
**Diff (PLAN §7, §10):**
```diff
 - **Independent skeptic:** sees only the *statement*, never the prover's reasoning; rewarded
   solely for gaps/counterexamples. If it reads the proof it just agrees — independence is
   the whole value.
+  *By construction:* the skeptic is a fresh-context worker whose only input is the statement
+  node plus tools for counterexample search; no prover output, no panel feedback and no
+  gate rubric is reachable from its context. Gate rubrics and detection logic are hidden
+  from the worker being gated.
...
 - **Mixture-of-models as filter, not oracle.** ...
+  *Disagreement protocol:* a Prover/Skeptic or panel disagreement is never resolved by vote;
+  it is recorded with both artifacts' hashes, classified (statement error, proof gap,
+  harness bug, out-of-scope, inconclusive), routed to an owner (human for statement
+  errors), and the claim's tag stays at its pre-dispute level until resolved.
```

### C11 · Statement-level review pre-filters that can flag or reject, never pass
**Component.** Calibration layer: statement-level review (§7); Skeptic rubric; lemma-library intake.
**Why.** DeepMind's `formal-conjectures` `STATEMENTS.md` is a concrete review checklist (quantifier
order/scope, strict vs non-strict bounds, implication direction, the `∃ x, P x → Q` trap, boundary
cases `ZMod 0`, `x/0`, `sInf ∅`, impossible hypotheses) with linters `ExistsImplicationLinter`,
`StubLinter` (no `opaque`/`def := sorry`/new `axiom`) (@e13dd728; PROVEN-in-source that they exist).
`atp-checkers` `VacuousCheck.lean` tries to prove `False` from the hypothesis telescope and detects
empty binder types; the accompanying paper reports 4,833 findings / 398 machine-certified across five
benchmarks (@3e7e99d; STRONG-EMPIRICAL). AlphaProof's pipeline pre-filtered autoformalizations by
round-trip consistency and rapid disproof/proof attempts before a ~3-person expert panel judged
(Nature 2025, Methods). Harmonic re-renders each proof as a self-contained file, lists axioms and
records the lemmas used as the handoff artifact (arXiv 2510.01346 §2.1.6). BEq-style symbolic
equivalence against a reference statement is a positive signal with low recall (EMNLP 2025).
**Cost.** Port two linters; a short prover budget per statement; extra LLM calls for round-trip.
**Epistemics.** Certified vacuity ⇒ automatic reject; everything else only flags; the final
"statement says what we mean" verdict stays human (C1 mechanizes "proved = stated").
**Diff (PLAN §7):**
```diff
 - **Statement-level review:** Lean verifies a proof is valid, not that you stated the
   theorem you meant. Verified-but-wrong-statement (weaker/trivial, smuggled hypothesis,
   wrong quantifier) is *more* dangerous than an open gap. Check the statement separately.
+  *Mechanical pre-filters (reject or flag, never pass):* a vacuity check that tries to
+  derive `False` from the hypotheses (certified vacuous ⇒ reject); linters for
+  `∃ x, P x → Q`, stubs and new axioms; a bounded prove/disprove attempt with a weak prover
+  (trivially provable or disprovable ⇒ flag); a blind round-trip informalization diffed
+  against the source claim (divergence ⇒ flag). The Skeptic's rubric is the
+  quantifier/bound/direction/boundary checklist. The human verdict remains the gate.
```

### C12 · Terminal-status (obligation) invariant on branches and claims; budget = meet(parent, declared profile)
**Component.** State layer (§4); tier scheduler / cost profiles (§5); orchestrator.
**Why.** asupersync's obligations are linear tokens `{Reserved, Committed, Aborted, Leaked}` with
resolve-once semantics; on task completion the runtime audits obligations still held, marks them
`Leaked`, counts, escalates by threshold and fails fast in lab mode or logs in production
(`src/record/obligation.rs:192-222, 440-470`; `src/runtime/state.rs:4640-4720, 6688-6714`;
STRONG-EMPIRICAL). frankensqlite states the same invariant as a protocol
(`fsqlite-types/src/obligation.rs:1-60`). asupersync's `Budget{deadline, poll_quota, cost_quota,
priority}` composes by meet (componentwise min, priority max; `src/types/budget.rs:173-182,
496-545`) and supervision refuses a restart the remaining budget cannot afford
(`src/supervision.rs:214-300`; STRONG-EMPIRICAL).
**Cost.** A small enum + an audit hook at worker exit; a meet on spawn.
**Epistemics.** None; it closes "a branch quietly dropped with no status" and "retry spends what
was never granted".
**Diff (PLAN §4, §5):**
```diff
 - **Orchestrator (mutable brain):** bandit allocation over active branches (fund yield,
   prune stalls, revive parked, force periodic pivots so it can't rabbit-hole); ...
+  *Terminal-status invariant:* every opened branch and every opened claim is a linear
+  obligation that must reach a terminal status (refuted / parked / promoted / withdrawn);
+  a worker that exits leaving one open produces a `Leaked` record that is counted and
+  escalated — fail-fast in tests, logged and escalated in production — never silently dropped.
...
 **Mechanism:** every skill declares its **cost profile** (complexity in inputs, expected
 tier) as part of its typed interface, so the orchestrator *predicts* spend before launch
 and the tier gate enforces cheap-before-expensive automatically. ...
+A spawned worker's budget is the meet of its parent's remaining budget and the skill's
+declared profile; a retry or restart is launched only if the remaining budget can afford it.
```

### C13 · M0 exemplar skill and first substrate contents
**Component.** Build order M0 (§13); resolves HANDOFF open decisions "M0 scope and the first
exemplar skill" and (with C1) "formalization stack".
**Why.** The exemplar skill is "generate a prime-order toy curve of b bits": random prime p, random
(a,b), order via PARI `ellcard` (Shanks–Mestre BSGS Õ(q^{1/4}); ms at ≤60 bits), accept if prime;
acceptance ≈ c/ln p — measured 10/25/130 curve tries at 30/40/50 bits (0.00/0.06/1.52 s, one seed;
STRONG-EMPIRICAL), with `cardinality(algorithm='all')` as the two-implementation check
(`sage/schemes/elliptic_curves/ell_finite_field.py:318-508`; PROVEN-in-source for code paths). The
Tier-0 verifier is `xP==Q` preceded by subgroup-membership checks (n·Q = O), because PARI's generic
DL can loop without a solution (`ell_point.py:4558-4751`). The Tier-1 rho skill's known answers are
Sage's doctest seeds and its certificate is C4's witness. This gives M0 exactly the demonstrable
property PLAN asks for: a hashed, self-tested, cost-tagged substrate node on a 40-bit curve.
**Cost.** None beyond M0 itself; Sage/PARI (cypari2) as the Tier-0/1 backend.
**Epistemics.** None.
**Diff (PLAN §13):**
```diff
 - **M0 — the real slice.** Substrate schema (§3) + **one exemplar skill built end-to-end**
   (content-addressed I/O, captured seed, self-test, declared cost profile) + Tier-0 verifier
   + tier gate. *Done when:* it runs one skill on a 40-bit toy curve end to end, and the
   result is a hashed, self-tested, cost-tagged substrate node. Everything else plugs into
   this shape — get it right once.
+  *Exemplar skill:* `toy_curve(bits, seed) → (p, a, b, n, P)` — random prime-order curve via
+  PARI `ellcard`, accept-if-prime, two-implementation agreement on the order, known-answer
+  corpus from Sage doctests, cost profile "Tier-0, ≈c·ln p tries". *Tier-0 verifier:* subgroup
+  membership (n·Q = O) then `xP==Q`, in a subprocess. *M0 schema includes* the C3 key and
+  cache bits, the C4 grade and certificate slot, the C2 derived-tag rule, and a roots table.
```

### C14 · What not to build or adopt (negative results, recorded so they are not re-walked)
**Component.** §3, §12; HANDOFF's candidate-technique list.
**Findings.** (a) **No off-the-shelf CAS.** bazel-remote (SHA256-only keys, LRU eviction, no roots
or lineage; `utils/validate/action_result.go:34`, `cache/disk/load.go:580-581` @ead2079), NativeLink
(execution system, LRU), cacache-rs (no BLAKE3, no roots) all evict what Cairn keeps forever; SQLite
blobs + BLAKE3 + a roots table at M0 (PROVEN-in-source for each limitation). (b) **RaptorQ /
fountain codes: real, homeless for M0–M3.** asupersync's is an in-tree RFC 6330 implementation
(~45k lines in `src/raptorq/`, RFC conformance harness, differential tests against the `raptorq`
crate, fuzz, metamorphic tests) — so "does it work" is settled; but frankensqlite's use is unwired
(`WalBackendAdapter::with_fec_hook` has zero callers) and frankenfs's is erasure-only with
caller-supplied corrupt indices; Cairn at M0–M3 is single-node with no lossy transport lane. Revisit
criterion: a Tier-3 distributed run that ships distinguished-point tables across unreliable links.
(c) **Not frankensqlite, frankengraphdb or frankensearch as dependencies:** fsqlite documents ≥10
concurrent writers as unsupported (`docs/concurrency-contract.md:18-32`), fgdb reads are
whole-history validate + linear filter with no transitive reachability (`fgdb-strata/src/root.rs:894-955`;
SQLite + edges table + recursive CTE beats it), frankensearch needs ≈621 MB of models and a
nightly pin; all three carry the license rider. (d) **Conformal test martingales for cost-profile
drift** are a weak fit (they detect any exchangeability break, require an art-dependent betting
function, decay under the null); a one-sided bounded-mean e-process is 20 lines if an alarm is
wanted (P4). (e) **Hermit** as a determinism runtime (Linux x86-64 ptrace, 3–6× wall clock, nightly
Rust) — keep only its definition of replayable.
**Diff (PLAN §12 and HANDOFF candidate list):**
```diff
 It designs none of the above. Its one job: current, code-level truth on the stack before
 you wire it — Lean/mathlib, Sage/PARI/Magma, the orchestration framework, Claude Code's
 subagent/Task interface. ...
+Recorded negative results (2026-08-21 mining): no off-the-shelf CAS fits (LRU-only
+retention) — SQLite+BLAKE3 at M0; RaptorQ is real but has no home before a Tier-3
+distributed lane exists; none of frankensqlite / frankengraphdb / frankensearch is a
+dependency (scale, maturity, license rider) — mechanisms are re-implemented from primary
+sources; Temporal/LangGraph are not the orchestrator's state layer.
```

---

## 2. Needs a prototype to decide (validity mostly established; *usefulness to Cairn* is the open question)

### P1 · A quantitative floor for the strong-law-of-small-numbers gate: a pre-registered betting e-process
**Component.** Calibration layer (§7). **HANDOFF's e-value hypothesis, adopted narrowly.**
**Mechanism (exact).** Conjecture C: "property P holds on family F". The Experimentalist declares a
sampling distribution D over F, ε, α and a seed *before* sampling, draws x₁, x₂, …, sets
Xᵢ = 1[P fails on xᵢ], and runs E_t = ∏(1 − λᵢ(Xᵢ − ε)) with predictable λᵢ ∈ [0, 1/(1−ε)] against
H₀: "P fails with probability ≥ ε under D". E_t is a test supermartingale (Waudby-Smith–Ramdas
JRSS-B 2024 eq. (29), Prop. 2–3; Ramdas et al. 2023 §2.2 eq. (13)), so Ville gives
P(∃t: E_t ≥ 1/α) ≤ α under any P ∈ H₀, with optional stopping free. At the maximal bet
λ = 1/(1−ε), E_n = (1−ε)^{−n} on a clean prefix and 0 at the first failure, so crossing 1/α needs
n* = ln(1/α)/(−ln(1−ε)) clean cases (α=.05: 299 at ε=.01, 2,995 at ε=.001); a never-busting
adaptive bet needs ≈2× that (Monte Carlo in `briefs/adjacent-anytime-valid-stats.md` S1;
PROVEN-in-source for validity). The same primitive exists, correct, in
`fsqlite-types/src/eprocess.rs:173-215` **[reviewer-checked]** and
`asupersync/src/lab/oracle/eprocess.rs:224-255`.
**What it licenses and what it does not.** It is a statement about D, never about F: it never
supports universality, never PROVEN, and the deliberate/structured counterexample hunt remains a
separate obligation. There are no principled sub-grades (Shafer 2021 §3: any p↔e translation is
"fundamentally arbitrary"; Vovk–Wang 2021 Prop. 2.2: the only admissible e→p map is min(1,1/e)); the
four tags stay categorical and log₁₀E is a numeric attribute on a CONJECTURE row.
**Proposed use (a resource gate, not a truth gate).** The gate keeps its text and gains a floor: before
Tier-2 compute is spent *proving* C, the claim's repro node must hold (D, ε, α, seed, case hashes)
and E_t ≥ 1/α for the declared (D, ε). D is hashed into the claim; a new D is a new claim, so the
orchestrator cannot tune D toward clean cases. E never feeds the bandit's reward.
**Why prototype first.** Power at honest ε (hundreds to thousands of clean cases) may make the floor
rarely binding, in which case the simpler rule "counterexample hunt + larger cases" already does the
work and the extra machinery is cost without accretion. Decide at M1 with planted-false conjectures.
**Diff if adopted (PLAN §7):**
```diff
 - **Strong law of small numbers (hard gate):** a small-case pattern is a conjecture until it
   survives larger cases + a deliberate counterexample hunt.
+  *Quantitative floor (resource gate):* sampled evidence for a conjecture is accumulated as
+  a pre-registered betting e-process (declared sampling distribution D, ε, α, seed, all
+  hashed into the claim); Tier-2 spend on proving it requires E ≥ 1/α for the declared
+  (D, ε). E is stored as log₁₀E on the claim; it creates no sub-grade, never promotes a tag,
+  is about D not the family, and never enters the orchestrator's reward.
```

### P2 · Selector audit as a calibration test martingale
**Component.** Problem queue / selector (§10, M4). **Mechanism.** Panel emits greenlight probability
q_t; a gate adjudicates Y_t ∈ {0,1} "panned out"; M_t = ∏(1 + λ_t(Y_t − q_t)) with predictable
λ_t ∈ [−1/(1−q_t), 1/q_t] is a test martingale under "q_t calibrated" (Ramdas et al. 2023 eq. (13));
Choe–Ramdas (OR 2023) Thm 3 gives an e-process for "panel no better than a cheap baseline on
Brier"; Arnold–Henzi–Ziegel (AoAS 2023) Def. 4.2 warns that with outcome lag h>1 the process is not
an e-process without their τ_{α,h} correction (PROVEN-in-source for validity). **Why prototype.**
Dozens of greenlights per month ⇒ E rarely reaches 1/α; this is a monitor plus a confidence
sequence on mean Brier difference, not a swap trigger on its own; "panned out" must be gate-
adjudicated or the null is gamed. Also the shape of the selector-measurement protocol HANDOFF lists
as open.

### P3 · Orchestrator mechanics: periodic reset of the worst half; gate-computed reward with a relative baseline; crash-safe ticks
**Component.** Orchestrator (§4, M3); state-layer durability. **Evidence.** FunSearch uses no bandit:
uniform island choice, Boltzmann sampling over score clusters with decaying temperature, and a
timer-driven reset every `reset_period=4h` that wipes the worst half of islands and reseeds from
survivors (`implementation/programs_database.py:106, 147-170, 209-216` @cc53f27; SI Fig. A.1 shows
single-island fails where multi-island finds I(15,10) 2/5 seeds — STRONG-EMPIRICAL, thin).
AlphaEvolve's evaluation cascade is PLAN's ladder+tier gate as an evaluator feature (2506.13131
§2.4). ShinkaEvolve's `AsymmetricUCB` over *model* arms shifts reward by max(parent, initial) and
clips at 0, adds √(2 log t/n) and a cost-aware blend (`shinka/llm/prioritization.py:295-650`
@e344678; one-task ablation). Nobody has shown a branch-level bandit beats simpler allocation;
Cairn's info-per-dollar is ahead of the literature and therefore unvalidated. Durable execution:
DBOS-on-SQLite ≈ "SQLite tick table + idempotent steps" with the bookkeeping written
(docs.dbos.dev/architecture); Temporal's determinism/versioning discipline bites exactly where the
loop self-modifies; LangGraph checkpoints re-fire LLM calls. **Proposal to test at M3.** (i) the
forced pivot is FunSearch's reset: periodic, mechanical, kills the worst half regardless of agent
opinion; (ii) reward = gate outcomes only (never self-report), relative-improvement baseline,
cost-aware blend; (iii) one orchestrator tick = one short idempotent workflow with its RNG draws
stored as steps (hand-rolled or DBOS-shaped), so a crash resumes from the last step; not Temporal.
M3's existing bar ("reallocates off a stall unaided") decides.

### P4 · Operational alarms: split-conformal anomaly flag on ladder/self-test measurements; one-sided drift e-process on cost profiles
**Component.** Skill interface cost profiles (§5); ladder (§6). **Evidence.** Split-conformal
threshold = ⌈(1−α)(n+1)⌉-th order statistic, returning +∞ when rank > n rather than clamping (which
silently loses the finite-sample guarantee): `asupersync/src/lab/conformal.rs:542-560`,
`fsqlite-mvcc/src/sheaf_conformal.rs:362-384` (PROVEN-in-source, ~40 lines). For "measured scaling
drifted from declared profile", a one-sided bounded-mean e-process on clipped log(measured/declared)
is 20 lines and more targeted than Vovk's conformal test martingales (which detect any
exchangeability break and need an art-dependent betting function;
`briefs/adjacent-anytime-valid-stats.md` S4). **Why prototype.** Both are strategy-layer alarms with
no epistemic role; adopt only if the alarms turn out to fire on something the ladder misses.

### P5 · Conformal "surprise" per claim class as an additional scrutiny-router trigger
**Component.** Proportional-scrutiny router (§7). **Evidence.** Conformal p-value
(#{prior ≥ observed}+1)/(n+1) with Mondrian per-class calibration (`frankensearch-fusion/src/conformal.rs:208-298`;
PROVEN-in-source for mechanics; the adaptive-α variant there moves α toward observed error and is
not borrowed). **Proposal.** A claimed effect in the top-α of historical claims of its class
triggers extra scrutiny; it can only *raise* scrutiny, never lower it. **Why prototype.** CONJECTURE
that it adds anything beyond the deterministic "bigger claim ⇒ more scrutiny" rule; may be homeless.

### P6 · Exact-dispatch replay receipt for Cairn's own concurrent components
**Component.** Skill self-tests / reproducibility gate for the orchestrator itself (M3). **Evidence.**
asupersync's `ForcedSchedule`: each dispatch folded into a running `ScheduleCertificate`
over (task, lane, step); a recorder captures (task_gen, worker, lane, at_step, at_nanos); replay
removes the exact recorded task from its exact queue — no RNG fallback — and returns typed errors
EarlyRunnable / StepMismatch / TimeMismatch / ScheduleExhausted / TerminalMismatch /
CertificateMismatch; artifact sealed with a domain-separated SHA-256 (`src/lab/runtime.rs:2236-2385,
3740-3790`; test `:9684-9718` records 6 dispatches, replays, asserts identical hash; PROVEN-in-source).
**Why prototype.** Only matters if the orchestrator is itself concurrent and its tests need exact
interleaving replay; if M3 is a single-threaded tick loop (P3), a seed suffices. Note "DPOR" in that
repo is a race-guided seed sweep, not DPOR (`src/lab/explorer.rs:812-829`).

### P7 · Librarian retrieval stack and off-policy evaluation of allocation policies
**Component.** Librarian (§4, M4); orchestrator (M3+). **Evidence.** frankensearch's measurements:
hybrid ≥ best single tier on three BEIR sets, never ensemble two embedders, RRF k≈10 beats the
k=60 default by +2.6% nDCG yet the default was kept (`docs/SEARCH_QUALITY_FINDINGS.md:28-75`;
STRONG-EMPIRICAL, not re-run); RRF with a 4-level deterministic tiebreak (`fusion/src/rrf.rs:190-330`,
57 tests); conformal `required_k` for retrieval depth at coverage 1−α (advisory; queries are not
exchangeable with any calibration set). IPS/DR off-policy evaluation (`fusion/src/ope.rs`;
CONJECTURE) to evaluate a proposed allocation policy from logged branch outcomes + propensities
before switching. **Why prototype.** Whether "tried before / why it failed" retrieval needs more than
BM25 over the negative-results map is an M4 question; OPE needs logged propensities first.

---

## 3. Rejected explicitly (homeless cleverness, wrong abstraction, or invalid)

| Candidate | Source | Why rejected |
|---|---|---|
| RaptorQ / fountain codes in the substrate now | asupersync `src/raptorq/` (real), frankensqlite `wal_fec.rs` (unwired), frankenfs `ffs-repair` (erasure-only, dependency) | No lossy-transport or multi-node lane before Tier-3; revisit criterion recorded in C14. |
| frankensqlite / frankengraphdb as the state store | `docs/concurrency-contract.md:18-32`; `fgdb-strata/src/root.rs:894-955` | ≥10 writers unsupported; whole-history linear reads, no reachability; SQLite + recursive CTE wins; license rider. |
| frankensearch as a dependency | `Cargo.toml`, README:113, LICENSE | 621 MB models, nightly pin, rider; borrow RRF/SimHash/conformal math only if needed (P7, C8). |
| PhaseGate-style multiplicative "evidence" | `frankensearch-fusion/src/phase_gate.rs:152-270` **[reviewer-checked]** | E[factor] > 1 under its own null; two-sided decision on 1/e; ≈36–51% null crossings vs 5% claimed. |
| e-process as a gate-skipper | `fsqlite-mvcc/src/ssi_eprocess_gate.rs`, `connection.rs:64985-65010` | Uses evidence to dissolve a correctness check; C2(b) forbids it. |
| e-values as sub-grades; e-values in bandit reward | Shafer 2021 §3; Vovk–Wang 2021 Prop. 2.2 | No principled ladder; reward would let the orchestrator choose D toward clean cases. |
| `evalue_eviction.rs`, `conformal_martingale.rs`, `regime_monitor.rs`, fgdb exploration "conformal" bound, frankenfs posterior-mean thresholds | frankensqlite, frankengraphdb, frankenfs | Vestigial or mislabeled; the name outruns the mechanism. |
| Conformal test martingales for cost-profile drift | Vovk et al. COPA 2021 | Weak fit; P4's simpler alarm if any. |
| Temporal; LangGraph checkpointing as state layer | docs | Determinism/versioning discipline on a self-rewriting loop; replay re-fires LLM calls. |
| AI co-scientist Elo tournament as a gate | 2502.18864 §3.3.3, §4 | LLM-judged, validated only by GPQA concordance; allowed only inside the selector's ranking. |
| LLM faithfulness judges, GTED similarity, BEq as a PROVEN gate | Aristotle §2.1.6; EMNLP 2025 | Routers / positive-only signals; a similarity score cannot gate PROVEN. |
| `native_decide` / `Lean.ofReduceBool`; "no errors" or empty `sorries` as PROVEN | Lean reference; DeepSeek-V2 erratum; kimina #75 | Extra axiom / uncheckable externally; refuted criteria. |
| Hermit as a runtime; Inspect AI as a framework | READMEs/docs | Platform and cost; keep only the replayability definition and the sandbox contract. |
| Off-the-shelf CAS (bazel-remote, NativeLink, cacache-rs) | code @ead2079, @105692a | LRU retention, no roots/lineage, SHA256-only or no BLAKE3. |
| frankenfs beyond patterns; franken_markdown renderer | briefs | Nothing mathematical; the patterns are in C5/C7. |
| Semantic near-duplicate as auto-REFUTE | ShinkaEvolve, co-scientist Proximity | Similarity would edit the ledger; advisory only (C8). |

---

## 4. Naming

**Keep "Cairn."** A cairn is built one stone at a time by successive travelers; it marks a route,
warns where the path is not, outlasts any single climber, and says nothing about whether the summit
was reached. That is HANDOFF's ethos exactly: progress = knowledge gained, not distance to the
summit; a first-class negative-results map; accretion across runs; the curve may stand while the
pile grows. The one alternative worth a line is **"Trig"** (a trig point: a surveyed, immutable
reference that everything else is measured from — the §0 epistemics), but it names the fixed part
and not the accretive one, and Cairn names both.

---

## 5. Where I would stake the most, and where I am least sure

**Stake the most (PROVEN-in-source evidence, cheap, strictly strengthening):**
1. **C1** — the challenge/solution formalization gate with kernel replay, the three-axiom rule and
   statement-closure identity. The protocol exists in `comparator` with an attack catalog, the Lean
   manual names it normative, and two published errata show what "green Lean" without it misses.
2. **C3 + C4 + C9** — the substrate's key canonicalization, cache bits, witness certificates with a
   replay grade, `--check` reproducibility, and roots-based GC. These are REAPI and Nix semantics,
   deployed for a decade at scale; Cairn's schema should copy them rather than discover them.
3. **C2** — derived tags through a lattice, "monitors block or alarm, never promote", append-only
   attributed tag history. ~200 lines, type-enforceable, and the suite's own misuse catalog is the
   argument for it.

**Least sure (validity fine, accretion uncertain):**
1. **P1** — the e-process floor on the small-numbers gate. The math is certain; whether a floor that
   needs 300–3,000 clean cases changes any decision the counterexample hunt would not already make
   is unknown. This is the honest verdict on HANDOFF's e-value hypothesis: adopt the invariant
   (C2b) now, adopt the number only if M1 shows it binds.
2. **P3** — the orchestrator items. Evidence is 3–5 seeds on one task each; branch-level bandits
   are unvalidated in the literature; keep M3's bar and let it decide.
3. **P5** — conformal surprise for the scrutiny router. CONJECTURE; plausibly homeless.

**Calibration of this document itself.** Every file:line was printed by the agent that cited it or
by me; the lines I re-read are marked. I did not build or run any of the six repos (nightly pins,
uncached git deps), so "tests pass" claims are counts and reads, not executions; the one piece of
code I executed is the ladder benchmark (`scratchpad/adjacent/toy_ladder_bench.py`, one seed).
The prior-art incident table rests on the authors' own reports. Nothing here changes the expected
outcome in PLAN §14.

---

## 6. Per-source verdicts (one line each; full briefs in `briefs/`)

| Source | Verdict | Feeds |
|---|---|---|
| asupersync v0.4.9 @9eb0600e | Real lab determinism, exact-dispatch replay receipt, obligations, budget meet, a correct e-process primitive and +∞-aware conformal quantile; RaptorQ real but homeless; "DPOR" is seed sweeping; Lean theorems are about a model. | C2, C7, C12, P1, P4, P6, C14 |
| frankensqlite v0.3.7 @9b1d3ed7 | Negative-results ledger with a machine preflight gate and retry predicates; A/A-null decision band; the valid e-process primitive but an e-process used to skip a check; gate runner + ratchet + fail-closed policy; hash-chained markers; content-addressing with 128-bit truncation (keep 256). Not a store for Cairn. | C2, C5, C6, C8, C9, C14 |
| frankenfs v0.2.0 @77b0a032 | No e-process, no content addressing; RaptorQ is asupersync's and erasure-only; one accretive pattern (fail-closed claim-state evaluator + executed-evidence + provenance-cannot-strengthen) plus a cross-oracle disagreement protocol. | C5, C10 |
| frankensearch v1.6.0 @4302c377 | Certified recall lower bound (a bound, not a witness), conformal rank calibration, golden-vector skill certificate, gauntlet evidence protocol, SimHash, RRF measurements; PhaseGate "e-process" invalid. Not a dependency. | C4 (negative), C7, C8, P5, P7 |
| franken_markdown v0.3.4 @562f4bd9 | Renderer irrelevant; ratcheted conformance corpus, claims registry with proof pointers, planted-failure gate self-tests, determinism by construction. | C5, C7 |
| frankengraphdb @cfac1667 (untagged) | Claim-class lattice + evidence envelope + replay-completeness grades + hash-chained CAS commit log + proof-lane gate; storage/query not accretive; five weeks old, untagged. | C2, C4, C9, C1 (admit scan) |
| Adjacent: CAS / reproducible compute | REAPI canonicalization + cache bits; Nix fixed-output + `--check` + roots; Buildbarn completeness; no off-the-shelf CAS. | C3, C4, C9, C14 |
| Adjacent: anytime-valid statistics | Exact e-process for the gate; no sub-grades; selector martingale; drift weak fit; no dependency worth taking (copy ~150 lines of confseq if needed; `expectation` is GPL + AI-training clause). | P1, P2, P4, C2 |
| Adjacent: agent orchestration | FunSearch reset, Shinka UCB, AlphaEvolve cascade = ladder; incident table; DBOS-shape ticks; SDK subagent isolation. | C5, C10, P3 |
| Adjacent: proof automation | comparator/SafeVerify/leanchecker; mathlib coverage table; sorry-leak errata; statement linters and vacuity checks. | C1, C11 |
| Adjacent: distributed collision search | vOW witness schema; BLS §6 and 2016 verification methodology; Sage/PARI self-test seeds and cross-checks; measured 30/40/50-bit numbers; M0 curve generator. | C4, C6, C7, C13 |
