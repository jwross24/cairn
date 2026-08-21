# plan-r2 review — grounded seat (repository-reading)

## Evidence checks (this seat's duty)

**Verified.**

- The plan's arithmetic all checks out. §5 budget ceiling: rho's collision time is Rayleigh in the limit, so `P(T > 2·mean) = e^−π = 4.3 %` and `P(T > 4·mean) = 3.5×10⁻⁶` ("≈ 4 %", "well under 0.1 %"), and `sd/mean = 0.655/1.253 = 0.52`. §6 out-of-sample band: at `m = 10` the hold-out standard error is 15.8 % ("≈ 16 %"), and against an A/A radius of ≈10 % (10² trials) a point-against-band test rejects at `P(|Z| > 1.25) ≈ 0.21` — "about one run in five" is exactly derivable. §7 auditor bound: `ln(2²⁰)/ln(1/0.99) = 1379`. §5 Tier-2 pricing: `0.886·2⁴⁰·0.11 µs = 29.8` core-hours, ×32 and ×1024 giving 10³ and 3×10⁴; the 0.11 µs is BLS 362 cycles at 3.2 GHz, verified at `briefs/adjacent-distributed-collision-search.md:51`.
- §6 ladder constants (BSGS ≈1.5√n and ≈3×10⁷ entries at 50 bits; rho ≈1.25√n ≈4×10⁷; 60-bit ≈1.3×10⁹ ops and 2³⁰ entries; ≈1 GB table) — verified at `briefs/adjacent-distributed-collision-search.md:50-51` and `PROPOSALS.md:282,311`.
- §7 Lean protocol. `leanchecker --fresh` replays the closure from empty and does **not** reject `sorryAx` — hence the separate `#print axioms` step, correctly placed; 32.3 s mathlib-free, mathlib cost OPEN (`grounding/lean-checker-protocol.md:40-41,53`). Raw `lean4export` bytes unstable, `compareAt`-closure hash CONJECTURE and the tool nonexistent (`:50,55`). Real `landrun` Linux-only, macOS fidelity dev-only (`:20,56`). Each is carried in the plan with the tag its probe assigns.
- §13 M0 backend. 60-bit `ellcard` is SEA at ≈75 ms and overflows PARI's default stack; `gp` exits 0 on fatal errors and zero-fills missing arguments; membership must precede `elllog` — `grounding/pari-sage-toy-curve-backend.md:23,24,28,29`. All carried with the right consequence.
- §15 P3(iii). The source-hash-per-step tick is the exact remedy for the measured DBOS failure — step body changed, hash unchanged, stale output replayed silently (`grounding/dbos-sqlite-and-agent-sdk-isolation.md:14,23`). Sound; needs nothing.

**Wrong or unverifiable:** see P3 (a corpus-origin claim contradicted by the grounding) and P5 (an isolation property whose probe is recorded OPEN).

**Sound and needing nothing:** §0, §1, §8, §9, §12, §14, and §6's verdict lattice — I checked that positive control (j) clears its own band (1.25/0.886 = 1.41 against ≈1.20), so the KEEP threshold is not accidentally unreachable by the one method known to beat the baseline.

---

## 1 · The ladder's primary metric has no measurer · HIGH · §6

**Rationale.** §6(2) assigns memory to the harness explicitly ("measured by the harness as peak algorithmic table and spill bytes"). §6(3) says only "It reports group operations against √n". Across 951 lines nothing says who counts them. A fresh implementer resolves that the obvious way — the skill returns its op count — and the top anti-fabrication device gates on a number produced by the party being gated. Every other ladder input is gate-owned: instances, nonce, seeds, patience ceiling, memory, verdict. The exception is the one the KEEP band is computed from, and the plan's own incident catalogue (§4: "hallucinating an ablation table") is this failure under another name. The fix is nearly free: the ladder already ships a gate-owned instance-maker.

```diff
-the hold-out run. (3) It reports group operations against `√n`, never seconds.
+the hold-out run. (3) It reports group operations against `√n`, never seconds, and the
+count is the gate's measurement, never the claimant's: the instance-maker hands the method
+a gate-owned group object that counts every addition, doubling and inversion, and the
+method's Tier-1 allow-list contains no other arithmetic backend. A self-reported count is a
+diagnostic column; a divergence from the gate's count beyond the ladder plan's tolerance is
+REJECT. A method that requires an uncounted backend declares that in its hypothesis object
+and its rung is INCONCLUSIVE at best.
```

**Cost.** One counting wrapper on the baseline arithmetic skill; interpreted counting slows ≤50-bit rungs, which are minutes. **Evidence:** STRONG-EMPIRICAL for the failure class (the incident table behind `PROPOSALS.md` C5); the remedy is an instrumentation choice, not a claim. Strengthens a gate; touches nothing in §0.

## 2 · The formalization gate's checker configuration sits outside the gate bundle · HIGH · §4, §7

**Rationale.** comparator is driven by a config naming `challenge_module`, `theorem_names`, `definition_names`, `permitted_axioms` and `external_kernels` (`grounding/lean-checker-protocol.md:21`, PROVEN-in-source). The plan pins the *renderer* and *prelude* in the bundle and states the three-axiom rule in prose — but never pins that config. Whoever writes the JSON decides what "green Lean" means: one more name in `permitted_axioms` admits a custom axiom, and an `external_kernels` entry pointing at a trivially-succeeding binary dissolves the gold tier while every sentence of §7 stays true. The same hole appears twice more: §5's tier cost boundaries and the Tier-0 verifier's invocation (backend path, stack ceiling, accept predicate — the three things `grounding/pari-sage-toy-curve-backend.md:29` shows are load-bearing) are gate semantics living in prose rather than in the pinned bundle.

```diff
     The gate plan, the no-go set, the non-goal sets of skill corpora, the waiver registry,
     the ladder plan (sizes, trial counts, the hold-out instance count `m`, the per-rung
     memory cap, the per-trial patience ceiling, the fit and hold-out split), the worker role
-    templates, the budget ceiling multiplier (§5), the auditor's `f`, `bits` and cadence
+    templates, the formalization gate's checker configuration (challenge module, theorem and
+    definition names, the permitted-axiom set, external-kernel commands) and its
+    `lean-toolchain` and `lake-manifest` pins, the Tier-0 verifier's invocation (backend
+    path, stack ceiling, accept predicate), the tier cost boundaries of §5,
+    the budget ceiling multiplier (§5), the auditor's `f`, `bits` and cadence
     (§7) and every worker tool allow-list form the **gate bundle**
```

and in §7: a gate run whose checker configuration is not the bundle's fails closed before compilation; the permitted-axiom set is a bundle field, not a literal in a per-run config.

**Cost.** Four more bundle fields. **Evidence:** PROVEN-in-source that these are configuration rather than code. Makes §0's immutability claim true where it is currently asserted.

## 3 · The M0 corpus's declared origin contradicts the grounding · MED · §13

**Rationale.** §13 calls the exemplar's four cases "four vendored cases (`corpus_origin = upstream_vendored`)". `grounding/pari-sage-toy-curve-backend.md:33` records seed 1's curve and order as PROVEN-in-source but its `P`, `Q` and `x` as locally enumerated and STRONG-EMPIRICAL; `:34` records seed 2's `P` as OPEN, "not explicit in the doctest"; `:42` states that no explicit F_p `(P,Q,x)` triple exists upstream at all. The plan's one complete triple is therefore upstream in its curve and locally completed in its point data — which §2's own rule calls `author_supplied` and caps at CONJECTURE. The taxonomy has no bucket for "derived by the operator and re-checkable by postcondition", which is what this is, and the plan closes the gap by mislabeling.

```diff
-    assumption (§2 axis rule). Its known-answer corpus is four vendored cases
-    (`corpus_origin = upstream_vendored`) — one complete F_p triple (PARI's
-    `y² = x³ − 3x + 1` over F_5, order 7, with `P` and `Q = 3P`), two vendored
+    assumption (§2 axis rule). Its known-answer corpus is four cases with per-field origin —
+    one F_p triple whose curve and order are `upstream_vendored` (PARI's
+    `y² = x³ − 3x + 1` over F_5, order 7) and whose `P`, `Q = 3P` and `x` are
+    `randomized_postcondition`, re-derived by the Tier-0 verifier at every self-test run
+    (`ord(P) = 7`, `3P = Q`) rather than trusted as vendored, two vendored
```
plus an M0 obligation to record seed 2's `P` (OPEN upstream) or drop the case to curve-and-order only.

**Cost.** None; it makes the corpus's advertised strength match what the grounding supports.

## 4 · KEEP checks memory against a cap, never against the pre-registered memory model · MED · §6

**Rationale.** Step (0) pre-registers "exponent, constant or crossover, and memory". Step (2)'s KEEP condition tests the CI against the band *on group operations* and memory *only against the rung's cap*, which is fixed at the BSGS table (≈1 GB at 50 bits). The acceptance baseline is plain rho at O(1) memory. So a method that pre-registers O(1) memory, consumes 900 MB and beats rho by 30 % on operations is KEPT — a time-memory tradeoff sold as an algorithmic advance, which is the classical failure in exactly this literature. §6's own *Why two thresholds* names the 4.9×10⁷-ops/900 MB case and then leaves it ungated on the acceptance side.

```diff
-speedup is KEPT only if the whole claim CI clears `1 + 2·radius` (floor 1%) on group
-operations *and* peak memory stays under the rung's cap, fixed in the ladder plan as the
+speedup is KEPT only if the whole claim CI clears `1 + 2·radius` on group
+operations *and* the measured peak memory both stays under the rung's cap and satisfies the
+pre-registered memory model on the sizes measured — memory growth the model did not declare
+is a missed model and REJECT, not KEEP. The cap is fixed in the ladder plan as the
```

**Cost.** One comparison on a number the harness already measures. **Evidence:** STRONG-EMPIRICAL — rho is O(1) memory and BSGS √n (`briefs/adjacent-distributed-collision-search.md:31,51`).

## 5 · Worker context isolation rests on a path the grounding records as unprobed · MED · §4, §7, §13

**Rationale.** The plan makes isolation "a property of the dispatch" and names "inherited settings sources disabled". `grounding/dbos-sqlite-and-agent-sdk-isolation.md:30` records that a subagent *does* receive "Project CLAUDE.md (loaded via settingSources)"; `:33` that startup context includes "every CLAUDE.md level and a git-status snapshot"; and the OPEN at `:40` says whether `setting_sources=[]` suppresses `~/.claude/CLAUDE.md` was never probed. By §16's own rule the isolation property is CONJECTURE, and its failure is silent — a Skeptic that has read the invariants file still returns a green verdict. Twenty lines settle it.

```diff
-  templates, the budget ceiling multiplier (§5)
+[§13 M0 done-when, appended] and a context canary passes: a distinct token planted in each
+settings source (project CLAUDE.md, user-level CLAUDE.md, a skill file, the working-tree git
+status) is absent from a dispatched worker's echoed context, the canary re-runs on every
+toolchain or SDK upgrade, and its failure yanks the dispatch path the way a failed self-test
+yanks a skill revision (§2).
```

**Cost.** One fixture and one recurring check. **Evidence:** the leak paths are PROVEN-in-docs; that they reach a Cairn worker is the CONJECTURE the canary resolves.

## 6 · The Skeptic's substrate closure hands it the proof for Lean claims · MED · §7

**Rationale.** The handle is "scoped to the statement node's closure — the recipes and certificates of its evidence nodes, which a re-run needs, never the Prover's transcript or proof text". For a `lean_artifact` node the re-run inputs *are* the proof text: the Solution module is the recipe's input. The sentence contradicts itself precisely where independence matters most, and an implementer resolving toward "a re-run needs it" builds a Skeptic that reads the proof — which §7 says is worth nothing.

```diff
-    substrate handle scoped to the statement node's closure — the statement and the recipes
-    and certificates of its evidence nodes, which a re-run needs, never the Prover's
-    transcript or proof text — so no prover output
+    substrate handle scoped to the statement node's closure and filtered by evidence kind —
+    the statement, plus the recipes and certificates of `repro_node`, `ladder_table` and
+    `counterexample_hunt_record` evidence, which a re-run needs; for `lean_artifact` evidence
+    the Challenge statement hash and the gate-run verdict only, never the Solution blob or
+    its recipe inputs, the checker re-run being the gate's job — so no prover output
```

## 7 · Untagged stack constants and two pieces of dead text · LOW · §4, §5, §6

**Rationale.** §16 requires every stack fact to carry its source's tag. §5's Tier-2 pricing carries none, and its source tags the derivation "CONJECTURE beyond 50 bits" (`briefs/adjacent-distributed-collision-search.md:51`); since that constant sets the Tier-2/Tier-3 boundary the omission is load-bearing. §6's "(floor 1%)" can never bind — with rho's variance the A/A radius at 10² trials is ≈10 %, so the band is ≈1.20. And §4 opens a linear obligation on every branch while §5's `BUDGET_EXCEEDED` never says what becomes of it.

```diff
-  *validation* (the ceiling is arithmetic: at ≈ 0.11 µs per iteration a negation-map rho
-  at 0.886√n costs ≈ 30 core-hours at 80 bits, ≈ 10³ at 90 and ≈ 3×10⁴ at 100)
+  *validation* (the ceiling is arithmetic: at ≈ 0.11 µs per iteration a negation-map rho
+  at 0.886√n costs ≈ 30 core-hours at 80 bits, ≈ 10³ at 90 and ≈ 3×10⁴ at 100 —
+  CONJECTURE, the tag its source assigns the extrapolation above 50 bits)
```
plus: delete "(floor 1%)"; and in §5, a `BUDGET_EXCEEDED` attempt parks its branch with blocker `budget_preempt` rather than leaving a `Leaked` obligation.

---

## (a) Where I would stake the most

**1, 2, 5.** One defect in three places: a gate whose input is produced by, or reachable to, the party it judges. 1 is worst — §6 is the plan's own nominated top anti-fabrication device and its central number has no owner. 2 is cheapest and rests on PROVEN-in-source config facts. 5 is the only one whose evidence file says in its own words that the property was never tested.

## (b) Where the framing is wrong

**The specification is outgrowing the thing it specifies.** r0 37 KB, r1 56 KB, r2 71 KB, with zero lines of M0 written; each round adds precision and none removes a mechanism. §13's anti-over-engineering paragraph is the least-obeyed sentence in the document, and no rule forces the text to shrink as M0 lands. The dominant risk here is not a gate that fails open, it is a document nobody finishes implementing. §13 needs a rule: nothing enters §§2–8 that M0–M1 does not exercise. §15's P5, P6 and P7 are the honest first deletions — P5 the plan itself calls "plausibly homeless", P6 is conditional on a concurrency that does not exist, P7 is a retrieval stack for a worker arriving at M4.

**Every gate is aimed at a fabricating worker; nothing measures the operator.** The human issues waivers, signs off on Tier 3, supplies the statement-review verdict, and terminally routes near-duplicate and `supersedes_refuted_review` parks. §10 audits the *selector* under "taste is held to the system's own standard" — and exempts the component that is actually the taste anchor. For a solo operator running this for months the realistic failure is not a model inventing a table; it is a tired human approving the eleventh statement review of the evening. Inside the existing frame this costs one number: the foundations auditor re-presents a small blind sample of past human statement-review verdicts after a delay and publishes the self-disagreement rate. No gate changes and no verdict is overridden — the operator simply gets the calibration signal the system demands of everything else.

## (c) Facts I would need that the plan does not state

1. **Who executes ladder trials, and in what process** — a worker subprocess returning a table, or a gate-driven harness calling the method as a library. Proposal 1's fix turns on the answer and the plan never says.
2. **The formalization gate's cost on a mathlib-importing Challenge** (`grounding/lean-checker-protocol.md:53`, OPEN). M1's corpus of ≥30 plantings is sized by it: at 32 s per replay the corpus runs in minutes; at 30 minutes it is a day per run and the gate becomes Tier-2 spend on every PROVEN claim.
3. **Whether the statement-hash tool can be built at all** (`:55`, OPEN — the closure hash is inferred from `compareAt` and does not exist). PROVEN's identity property rests on it, and if the closure hash is unstable across mathlib revisions the Challenge/Solution identity needs a different anchor.
4. **The intended steady-state verification share of total compute.** §7's Tier-2/3 stratum is checked exhaustively on a cadence against a one-time per-node escrow; the plan degrades honestly when underfunded but never states what fraction of spend verification should consume.
5. **Whether `~/.claude/CLAUDE.md` reaches a dispatched worker** (`grounding/dbos-sqlite-and-agent-sdk-isolation.md:40`, OPEN).
