# Ledger — round 1

Plan reviewed: `research/convergence/plan-r0.md` (v3). Plan produced:
`research/convergence/plan-r1.md`. Synthesizer own view (written before any seat was opened):
`research/convergence/r1/own-view-r1.md`. Seats: GPT-5.6-terra (G), Grok-4.5 (K), GLM-5.2 (L),
DeepSeek-v4-flash (D), Anthropic Opus grounded (O); synthesizer own view (S).

Verdict: **NEEDS-ANOTHER-ROUND** — accepted changes reach HIGH, and several factual corrections
from the grounding probes changed mechanisms (verifier acceptance predicate, cross-check axis,
skeptic dispatch, M0 exemplar numbers, Tier-2 ceiling, ladder rung budgets).

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| A | Ladder tier/cost contradiction at 60 bits; pre-registered cost model; KEEP band baseline = rho (BSGS = refutation floor only); out-of-sample 60-bit rung; 60-bit figures tagged CONJECTURE | HIGH | G3, L1, O4, K6, D(A,L), S2 | §5, §6 | ACCEPT. Rungs ≤ 50 bits are Tier-1 with ≥ 10² trials; the 60-bit rung is completion (≥ 10 fresh instances) + out-of-sample prediction inside the A/A band, tiered by its own profile (≈ 1.3×10⁹ ops per trial ⇒ 10² trials is Tier-2 work). Model is pre-registered in the hypothesis object before any rung. Band is a ratio against plain rho in the same harness on the same instances, never BSGS. Evidence: `briefs/adjacent-distributed-collision-search.md:51` (0.11 µs/iteration, 60-bit ≈ 1.35×10⁹ ops, CONJECTURE at 60), `:16-17` (sd ≈ 0.5× mean), `PROPOSALS.md` C6 (A/A band). G3's re-scoping of "refuted on the spot" REJECTED (see §3 below). |
| B | Ladder instances from a gate-owned instance-maker with gate-held entropy; A/A arm = baseline vs itself, same harness/trial count/instance stream | MED | D(J,K) | §6 | ACCEPT. Closes the seed-visibility and cross-talk holes; evidence class already cited in C6(a) (`briefs/adjacent-agent-orchestration.md:27`). |
| C | Tier-0 verifier acceptance predicate: `gp` exits 0 on fatal errors, zero-fills missing args, 60-bit `ellcard` overflows default stack | HIGH | O2 | §13 M0 | ACCEPT. Driver validates arity/fields, passes a stack ceiling, accepts only `exit==0 ∧ stdout=="OK" ∧ empty stderr`; forced-crash fixture in the gate self-test. Verified `grounding/pari-sage-toy-curve-backend.md:24,29`. |
| D | "PARI vs Sage" agreement does not exist on this stack; declare cross-check axis (implementation vs algorithm) and independence range; disagreement is a `DISAGREE` substrate record, never a silent retry | HIGH | O1, K8 | §2, §13 M0 | ACCEPT. Verified `grounding/pari-sage-toy-curve-backend.md:8` (Sage not installed), `:14` (gp and cypari2 bit-identical), `:23` (BSGS-vs-SEA independent only for b ≤ 50). Second implementation is an M0 install decision; operator default "Sage/PARI" stands. |
| E | Worker/Skeptic isolation is the parent's discipline, not construction; context isolation ≠ filesystem isolation | HIGH | O3 | §4, §7 | ACCEPT. Workers are dispatched by the harness as top-level queries with an explicit tool allow-list named in the dispatch record; Skeptic has no general file read/shell and a substrate handle scoped to the statement closure. Verified `grounding/dbos-sqlite-and-agent-sdk-isolation.md:29,31,35`. |
| F | Immutable, content-addressed claim statement node; Challenge compiled by the gate from it; Formalizer never authors Challenge; Solution names the statement hash; statement hash over what the comparator compares | HIGH | G1, K3, D(N), S5 | §4, §7 | ACCEPT (merged). Evidence: `grounding/lean-checker-protocol.md:50` (raw export hash unstable; hash ConstantVal + closure), `PROPOSALS.md` C1 (comparator `compareAt`). Authorship (Reframer/Prover/human at claim-open, before proof) recorded as an open question on the default. |
| G | REFUTED-by-hash keys an undefined object; define the hypothesis key; type the refutation (`formal / measured / implementation`) | HIGH | G4 (partial), S1 | §3, §4, §11 | ACCEPT-PARTIAL. Hypothesis key = BLAKE3 over a typed hypothesis object excluding per-run seeds, ladder instances and free text (paraphrase is the advisory's job); a measured refutation reaches exactly the hashed object. G4's typed-scope containment checker REJECTED (no representation of mathematical assumptions named; G4 itself lists it as a fact it would need). |
| H | Recipe key vs append-only attempts; `skip_cache_lookup` records a fresh attempt, never overwrites; `salt` is a key field | MED | G2 | §3, §13 M0 | ACCEPT-PARTIAL. REAPI semantics say overwrite (`briefs/adjacent-cas-reproducible-compute.md:9`); Nix `--check` keeps the divergent copy (`:9,23`); the plan's own reproducibility gate already keeps divergences, so attempts make that uniform. |
| I | Admission gates are non-waivable; waivers human-issued only; a fixture proves a waiver cannot advance a claim or tier | MED | G5, D(G) | §4 | ACCEPT. `PROPOSALS.md` C5 notes the source repo counts `Waived` as satisfied and that Cairn must invert it; who may issue a waiver was unstated. |
| J | Tier-2 band off by an order: 100-bit rho is Tier 3 | MED | O5 | §5 | ACCEPT. Recomputed: 0.886·2⁴⁰·0.11 µs ≈ 30 core-hours (80 bits), ≈ 10³ (90), ≈ 3×10⁴ (100). Tier 2 = rho up to ≈ 90 bits; > ≈ 10³ core-hours is a Tier-3 request. |
| K | Tier gate admission ticket undefined | MED | S4, D(13) | §5 | ACCEPT (synthesizer-defined from existing text: ladder KEEP table for algorithmic claims; counterexample-hunt record (+P1 floor) for conjectures; Tier 3 adds justification/certificate plan/sign-off; `TierRefused` is a ledger record). |
| L | "Outside the orchestrator's write path" needs a mechanism: the gate bundle | MED | S3, O3, D(G) | §4 | ACCEPT. Content-addressed bundle in a separate read-only store (separate SQLite file at M0), hash pinned and recorded in every gate-run record; mismatch fails closed. Code branches on it (the gate refuses to run). |
| M | Forced pivot / stall parks, never refutes | MED | K1 | §4, §15 P3 | ACCEPT. REFUTED is evidence-only; PARKED with blocker `∈ {low_yield_pivot, budget_preempt, human_park}` and a clearing predicate. `PROPOSALS.md` P3 names FunSearch's reset; the status it writes was unstated. |
| N | Near-duplicate advisory routes to the Librarian before the Librarian exists (M2 vs M4); embeddings pre-M4 | MED | K2, S5 | §4, §13 M2 | ACCEPT. Pre-M4: SimHash → human or `near_dup_review` park; M4+: Librarian; no embedding model before P7. |
| O | M0 done-when does not exercise the verifier; M0 numbers wrong (ms "below 60 bits", "10/25/130 tries") | MED | G7, L2, O7a, S5 | §13 M0 | ACCEPT. Fixture derives `x`, `Q = xP`; negative and forced-crash fixtures; `ellsea(E,1)` early-abort + stack ceiling at 60 bits; tries measured over ≥ 50 seeds. Verified `grounding/pari-sage-toy-curve-backend.md:21-24,43`. |
| P | M1 done-when has no denominator; planted corpus enumerated; ladder baseline skills (`rho_dp`, `bsgs`, instance-maker) built at M1 | MED | K9, O7b, S5, K4 (its M1 fixtures only) | §13 M1 | ACCEPT. ≥ 30 plantings, INCONCLUSIVE = escape, no true advance rejected; nine fixture classes. |
| Q | M3 "stall" undefined; P3 tick records step source hash; P3 may drop the bandit | MED | O7b/c, K (framing) | §13 M3, §15 P3 | ACCEPT. Verified `grounding/dbos-sqlite-and-agent-sdk-isolation.md:14,23` (stale step outputs replay silently when only the body changes). |
| R | P2 martingale stake range missing | MED (factual) | G6 | §15 P2 | ACCEPT. `λ_t ∈ [−1/(1−q_t), 1/q_t]` restored from `PROPOSALS.md:626-627` and `briefs/adjacent-anytime-valid-stats.md:19`. |
| S | Self-test corpus authored by the skill's author measures nothing; `corpus_origin`; `author_supplied` caps at CONJECTURE; randomized postcondition | MED | O6a | §2 | ACCEPT. `PROPOSALS.md` C7 (Sage `discrete_log` verifies its answer, `generic.py:807-809`); exploit class C6(a). |
| T | Auditor query generalized to all classes; downgrade propagation; `f`, `bits` named; re-run policy by grade and tier; stratified sampling by tier and fan-in | MED | O6b/c, L4, D(25) | §3, §7 | ACCEPT. `briefs/frankenfs.md:38-43` (bound), C2 lattice rule ("weaker may inform, never justify", all classes). |
| V′ | Allocation currency until M3: gate-outcome reward per measured cost; no model probability / e-value / posterior / similarity term | LOW | K5 (partial) | §5 | ACCEPT-PARTIAL (one clause). |
| W′ | Human-required gate inputs block when no human session is open; Tier-2 cap is an operator knob, not a plan default | LOW | K7 (partial) | §10 | ACCEPT-PARTIAL. |
| Y | No-go checklist: presence is mechanical, content is Skeptic/human; the flag has a consumer (router → top scrutiny class; tier gate grants no ticket above Tier 1) | MED | L3, K7(ii) partial | §8, §5 | ACCEPT-PARTIAL (process-porn rule: a flag must have a consumer). |
| Z | Stack facts carry their source's tag; M0 begins by executing the facts it stands on; §12 license "therefore" is an operator ruling; linters catch only some `∃` forms; comparator gold tier needs Linux `landrun`; `leanchecker` name confirmed | LOW | O (fact checks, framing) | §16, §13, §12, §7 | ACCEPT. Verified `grounding/lean-statement-linters-vacuity.md:16`, `grounding/lean-checker-protocol.md:19-20,41,56`, `PROPOSALS.md:15-23`. |
| AA | Lead paragraph "open-ended attack research" pulls against the honest baseline | LOW | G (framing) | lead | ACCEPT. |
| AB | Wording: selector swap is a human decision; tag is a derived column the gate layer computes; withdrawal is not an escape from recorded gate outcomes; `Allowed` when the retry predicate is met; replay-grade order | LOW | D(Q,P,F,7,4) | §10, §7, §4, §3 | ACCEPT. |

Accepted clusters: 26 (5 of them partial).

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| U | Slim M0: move `justify`, tag history, derived PROVEN/STRONG-EMPIRICAL rules to M1 | K4 | §13 says the shape is gotten right once; C2 costs ~200 lines; a tag column retrofitted after M1's gates exist is the churn this avoids. Its M1 fixtures (statistical evidence for PROVEN; weaker premise in closure) were folded into P. |
| V | Fixed gate-outcome point schedule `{+1.0, +1.5, +2.0, −1.0 …}` as the M3 reward | K5 | Numbers carry no evidence tag (invented); P3 already pins "reward = gate outcomes only, relative baseline, cost-aware blend" and M3's bar decides. One clause accepted (V′). |
| W | Human-absent profile: hard Tier-1 cap; no-go unanswered ⇒ auto-PARK | K7 | Tier-1 cap is operator policy, not an evidenced defect (Tier 2 is designed to run unattended under the tier gate); auto-PARK duplicates the flag consumer accepted in Y. Blocking of human-required inputs accepted (W′). |
| X | `reduces_to` edge on the branch tree | K10 | No code branches on it (advisory for allocation/UI); process-porn rule; the seat itself offers to skip it. |
| AC | Skill pass floor "may raise" should be "may change/lower" | D(B) | No defect: the floor is a monotone ratchet (`PROPOSALS.md` C7, `--update-floor` may only raise); a regression is fixed or the skill retired, never floored down. |
| AD | Ladder: "a method that misses a preregistered 50-bit superiority prediction is rejected for that prediction; it is not a refutation of a separately stated higher-crossover claim" | G3 (part) | Softens the ladder's refutation rule; flagged as an invariant attack (below). The retry predicate on the REFUTED entry is the designed path for a crossover claim. |
| AE | A separate skill-library milestone ("N skills with self-tests") | K (framing b) | Count-based bar with no demonstrable property; the real dependency (ladder baseline skills at M1) accepted in P. |
| AF | Typed refutation scope with a containment checker over mathematical assumptions | G4 (part) | Homeless: no representation named; the hypothesis key already bounds a measured refutation to the hashed object. |

Rejected clusters: 8.

## 3. Flagged invariant attacks

- **G3 (part):** re-scoping "refuted on the spot" to "rejected for that prediction" weakens the
  ladder (an immutable gate). Rejected; not integrated. The accepted half of G3 (pre-registered
  model; finite sizes test a model and do not establish an asymptotic; tier-consistent rungs)
  strengthens the ladder.

No seat proposed weakening §0, the gate layer's existence, the taxonomy, the verifier, the
no-go checklist or the honest baseline.

## 4. Factual corrections (each checked against the cited file)

1. "milliseconds below 60 bits" → through 50 bits; at 60 bits `ellcard` is SEA (≈ 75 ms/curve, one search 25.4 s) and overflows PARI's default stack — `grounding/pari-sage-toy-curve-backend.md:21-24`. **Changed a mechanism** (M0 exemplar search path, stack ceiling).
2. "10 / 25 / 130 tries" → observed 20–220 over 3 seeds, means CONJECTURE; ≥ 50 seeds before a profile — `:23,43`. Changed M0's cost-profile procedure.
3. "two independent implementations (PARI vs Sage)" → Sage not installed; gp + cypari2 are one implementation; BSGS-vs-SEA independent only for b ≤ 50 — `:8,14,23`. **Changed §2/§13 mechanism** (axis rule).
4. Verifier subprocess: gp exits 0 on fatal errors, zero-fills args — `:29`. **Changed the verifier's acceptance predicate.**
5. "Skeptic isolation by construction" → parent's discipline; context isolation ≠ filesystem isolation — `grounding/dbos-sqlite-and-agent-sdk-isolation.md:29-35`. **Changed the worker dispatch contract.**
6. P2 stake range restored — `PROPOSALS.md:626-627`.
7. Linters catch only some `∃ x, P x → Q` forms — `grounding/lean-statement-linters-vacuity.md:16`.
8. Tier 2 "80–100-bit rho" → ceiling ≈ 90 bits by arithmetic from `briefs/adjacent-distributed-collision-search.md:51`. Changed the tier band.
9. 60-bit ladder figures are CONJECTURE at `briefs/adjacent-distributed-collision-search.md:51`; ≤ 50-bit STRONG-EMPIRICAL.
10. 10² trials at 60 bits ≈ 1.3×10¹¹ group ops — not "one core, minutes" — from `:51`. Changed the ladder's rung budgets.
11. `leanchecker --fresh` is the shipped name (lean4checker README; `grounding/lean-checker-protocol.md:41`) — plan was right; clause added that it does not reject `sorryAx` (the axiom check does) and that the gold tier needs Linux.
12. §12 license constraint is an operator ruling (`PROPOSALS.md:23`), not a derivation.
13. D's claim "Classical.choice may be opaque" — not reproduced; it is one of the three standard axioms (`briefs/adjacent-proof-automation.md:27`). Not integrated.

Corrections 1, 3, 4, 5, 8, 10 changed mechanisms ⇒ verdict cannot be STEADY.

## 5. Seat reliability

- **GPT-5.6-terra:** complete; 7 numbered proposals with diffs; format respected (~2.5k words). Four HIGH items survived in whole or part (A, F, G, I); one part flagged (AD); one homeless (AF).
- **Grok-4.5:** complete; 10 proposals; strongest on build-order dependencies (K1, K2, K9). K4, K5, K10 rejected. Framing (b) partly folded into P and Q.
- **GLM-5.2:** first run returned 328 chars (counted failed); retry at 7000 max-tokens truncated mid-proposal 4 ("…and by dependency fan-in ("). 3.5 usable proposals, all consistent with other seats; L3 contributed the no-go consumer.
- **DeepSeek-v4-flash:** exceeded the format — 42 KB of reasoning draft, no numbered proposals, no diffs, no closing sections; truncated. Observations were counted toward consensus only where stated as findings (A, G, J, K, L, N, P, Q, F, 7, 4, 25, B).
- **Opus grounded:** complete; 7 proposals; every fact check re-verified here at the cited lines; no over-claim found. Its re-run policy (6c) and `f`/`bits` values are its own design and were accepted as CONJECTURE-tagged defaults.

## 6. Open questions for the operator

1. Install a non-PARI second implementation at M0 (Sage, or a gmpy2 Hasse-interval BSGS like the session script) so Tier-0 cross-checks have an `implementation` axis — or accept `algorithm`-axis checks through 50 bits only?
2. Should Tier-2 spend require an open operator session (human-absent cap)? The plan records it as a gate-bundle knob with no default.
3. Default author of claim statement nodes: Reframer with human ratification, or human-only?
4. When does a Linux host or container for the PROVEN gold tier (`landrun` + comparator) enter the build? macOS runs the comparator unsandboxed.
5. The ladder's 60-bit rung: accept its Tier-2 classification at interpreted speed, or fund a compiled rho skill so the full distribution check stays on one host?

## 7. Validation

- **(a) Self-containment.** Most obscure M0 task: the hypothesis-key canonicalizer with its known-answer vector and the gate-bundle pin. Implementable as written: the hypothesis object's fields are enumerated (§3), the encoding rules and domain separation are inherited from the recipe key, the exclusions (seeds, instances, free text) are stated, the bundle's contents are enumerated (§4), its store is a separate read-only SQLite file, and the gate-run record names the pinned hash. The Tier-0 verifier is implementable from §13 plus `grounding/pari-sage-toy-curve-backend.md` §3 (exact PARI calls and the acceptance predicate).
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Every mechanism has a builder: recipe/attempt/hypothesis keys, claim statement node, `justify`, roots table, gate-bundle pin, verifier, tier gate, exemplar (M0); ladder + baseline skills + instance-maker, formalization gate (gate-compiled Challenge), pre-filters, reproducibility re-run policy, disagreement protocol, scrutiny router, no-go presence check, skeptic dispatch (M1); preflight, hash-chained log, terminal-status, near-dup advisory → human/park, formalizer, statement review (M2); orchestrator, pivot-park, tick table (M3); Librarian + routing, selector audit, lemma library, negative-results map, foundations auditor (M4). Fixed this round: the router, no-go presence check, disagreement protocol and re-run policy had no milestone in r0 and are listed under M1 in r1; the Librarian routing no longer precedes the Librarian.
- **(c) Justification sampling.** Recipe attempts (why: divergence is the evidence); hypothesis key (why: the recipe key carries the seed); gate bundle (why: a checkable boundary and a visible hash); two ladder thresholds (why: BSGS is the right floor and the wrong bar); Tier-2 ceiling (why: Tier 3 is the only tier demanding a payoff justification). All five carry a one-sentence why; so do the pivot-park, corpus-origin, skeptic two-layer and claim-identity additions.
- **(d) Steady-state diff.** Structural. r1 changes the contracts of §2 (cross-check axis, corpus origin), §3 (recipe vs attempts, hypothesis key, re-run policy), §4 (claim statement node, typed preflight, non-waivable gates, gate bundle, dispatch rule), §5 (Tier-2 ceiling, tier-gate predicate), §6 (pre-registration, rho baseline, 60-bit rung), §7 (gate-compiled Challenge, two-layer skeptic, auditor generalization) and the done-whens of M0/M1/M3; +224 lines. Section numbering, §0, §8's three items, §9, §14 and §16's invariant list are unchanged.

## 8. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Expected residual scope for round 2: coherence of the newly named
mechanisms against each other (hypothesis key vs claim statement hash overlap, tier-gate ticket
definitions for non-algorithmic claims, the 60-bit rung's budget and the A/A band at 60 bits, the
gate bundle's contents vs the M0 store layout), not new areas.
