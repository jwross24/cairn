# Ledger — round 5

Plan reviewed: `research/convergence/plan-r4.md` (v3, 1281 lines). Plan produced:
`research/convergence/plan-r5.md` (1473 lines; ≈ 320 changed lines, +192 net). Synthesizer own
view (written before any seat was opened): `research/convergence/r5/own-view-r5.md`. Seats:
GPT-5.6-terra (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-flash (D), Anthropic Opus grounded
(O); synthesizer own view (S). Prior ledgers read in full: `r1/ledger-r1.md`, `r2/ledger-r2.md`,
`r3/ledger-r3.md`, `r4/ledger-r4.md`.

Verdict: **NEEDS-ANOTHER-ROUND** — one accepted cluster is HIGH (the "human path" that every
human-attested node names is given a write boundary the orchestrator's process cannot cross, with
two M0 fixtures), and two factual corrections changed mechanisms (the verification escrow's
release rule contradicted the §3 deferred re-run; the human path was named six times and defined
nowhere while §3 fixes one substrate writer).

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | "The human path" is named for `review_verdict`, `nogo_review`, waivers and sign-off and defined nowhere; §3 fixes one substrate writer (the harness process), so a human-path row is indistinguishable from an orchestrator write | HIGH | O2 | §4, §2, §7, §8, §10, §13 M0, §16 | ACCEPT. §4 gains a *Human path* sub-bullet: the operator, as the operator's OS user, appends the canonical record to an operator-owned, append-only **attestation file** beside the gate-bundle pin, which the orchestrator's process user can read and not write; the harness writer mirrors it as a row carrying the record's digest and offset; `justify`, the tier gate, the waiver check and the preflight treat such a row as absent unless the digest matches; no typed write exposed to a worker or model component produces one; the two OS users are the M0 deployment shape the pin and checkpoint already assume. §2 (yank-reach ruling), §7 (`review_verdict`), §8 (`nogo_review`), §10 (expert sign-off) and §13 M1 (l) / M2 name "the human path of §4". M0 grounds the write boundary and its done-when adds two fixtures (pin and attestation writes refused as the orchestrator's process user; an unmatched `review_verdict` row is absent to `justify`); the schema names the file and the digest/offset fields. Not a re-litigation of r3 R4 (signed `review_attestation` with keys): no keys, no PKI, the boundary is the one r3 cluster 13 accepted for the checkpoint. Evidence: plan-r4 §7:786, §8:886, §13:1093, :1150 (uses), §3:234-241 (one writer), §4:400-406 (pin's operator-owned location); `HANDOFF.md:96` (non-negotiable 2). Re-judged HIGH: it defines the write authority PROVEN and Tier-2/3 admission rest on and adds an M0 deliverable. |
| 2 | The verification escrow is "released to the granting branch at terminal status" yet "spent where the §3 policy's first check ran (… a Tier-2/3 re-run at `justify` time …)", which is after terminal status — the same sentence releases and holds it | MED | O4, G2 | §5, §13 M1 | ACCEPT (merged). The reservation is bound to the *node*: spent where the first §3 check runs (routinely after the attempt, sometimes after the branch, reached terminal status), released unspent only on status ≠ OK or disown; a terminal branch returns its unreserved grant and never an admissible node's escrow; the auditor's exhaustive Tier-2/3 pass (§7, `l ≈ 1.4×10³` exceeding the population) spends every such escrow within one cycle, bounding the residue; why extended. M1 fixtures: refusal when the verification component is uncoverable; spend on first check, release on ≠ OK/disown; a deferred-check node keeps its reservation after attempt and branch terminate. G2's `verification_liability` object name and M0 placement not adopted (a node-bound field; the fixture lands with the behaviors at M1). Evidence: plan-r4 §5:452-456 vs §3:199-203 (internal). |
| 3 | A ladder REJECT on `xP ≠ Q` or a self-reported-count divergence writes a `measured` REFUTED entry on the hypothesis key and blacklists every implementation of a method for one bad executable | MED | G1 (partial), S3 (adjacent) | §2, §4, §6 2c, §7, §13 M1/M2 | ACCEPT-PARTIAL. The verdict stays REJECT (the ladder's verdict set is fixed, r2 #1); the ledger entry's `refutation_kind` follows the predicate — `xP ≠ Q` or a count divergence is an `implementation` entry against the revision the dispatch record names (retry: a new certified revision) and yanks that revision (§2 lists the ladder-detected wrong answer as a yank trigger: a known-answer failure the corpus missed); the floor, memory and model predicates are `measured` entries on the key, the ones §7's `refuted` status and the preflight read; §7 states that an `xP ≠ Q` REJECT refutes no claim version; fixture (b) must yank and write no method-level entry; the M2 fixture says `measured` and adds the `implementation`/new-revision `Allowed` case. G1's `INVALID_EXECUTION` verdict name not adopted. Evidence: plan-r4 §7:753-754 already scoped the refuted status to "a ladder REJECT on the claim's own pre-registered model", leaving the other predicates' effect unstated; §4:309 (`implementation` kind) and :318-320 (its retry predicate) already carry the right reach. |
| 4 | The in-sample model-fit predicate is undefined: (2c) REJECTs "an in-sample miss", KEEP_IN_SAMPLE needs "model fits in sample", fixture (a) is caught by it, and no band, fit rule or statistic is named | MED | S1 | §6, §13 M1 | ACCEPT. The in-sample check has the (2b) band form: the declared free parameters are fit by least squares on the log of the rung means over the ≤ 50-bit rungs and each rung's mean must sit inside `1 ± 2·√(radius² + (sd_s/(mean_s·√n))²)` of the fitted prediction; outside is an in-sample miss (REJECT); the sorted-distribution shape is a diagnostic column that surfaces on the human queue beyond the ladder plan's tolerance and is never a verdict predicate; worked example (exponent 0.4 vs √n misses ≈ 4× between 30 and 50 bits; control (j) fits); why added. Evidence: plan-r4 §6:567-568, :616-620, §13:1076-1078 (internal gap). |
| 5 | Tier 3's ticket is "KEEP + justification, certificate plan, sign-off" (§6 2c, §5) while §5 refuses a declared tier more than one above the ticket's tier and never defines a multi-rung table's tier; "most recent node of the kind" leaves whether a later REJECT displaces an older KEEP open | MED | S2, S5a | §5, §6 2c, §13 M1 | ACCEPT. A ladder table's tier is the tier the gate assigned the launch that completed it; Tier 3's ticket is the most recent admissible Tier-2 node for the same key and method identity (for an algorithmic claim a validation attempt with status OK whose witness verified, launched under KEEP) plus the justification, plan and sign-off — KEEP is the prerequisite and reaches Tier 3 only through that node, the one-tier rule applied; "most recent" ranges over every node of the kind whatever its verdict, so a later REJECT or INCONCLUSIVE table displaces an older KEEP; §6 (2c) reworded; M1 fixture (a Tier-3 request holding KEEP and no Tier-2 node is refused). Evidence: plan-r4 §5:494-495 vs §6:624-625 (internal). |
| 6 | A claim whose hypothesis object carries both a cost model and a correctness conjecture (or a theorem statement) matches two ticket-lattice branches and the text picks none | MED | L1 | §5, §13 M1 | ACCEPT. Such a claim needs the ticket of each kind it carries and is refused while any is absent; a scoped KEEP_IN_SAMPLE admits only the 60-bit rung whatever else is held; M1 fixture. Evidence: plan-r4 §5:503-512 ("never a ladder table unless the claim is also algorithmic" with no rule for the conjunction). |
| 7 | Success-side range jitter: a sub-region of a KEPT/PROVEN hypothesis re-laddered mints a KEEP the existing table already justifies | MED | K3 (partial) | §4, §13 M2 | ACCEPT-PARTIAL. `AlreadySettled` gains a second condition: a proposal whose method identity and claimed cost model equal a *promoted* holder's (claim at PROVEN / STRONG-EMPIRICAL) and whose declared region is contained in the holder's (the REFUTED reach's axis-aligned inclusion) parks with `already_settled` — the holder's evidence already covers it under `justify`'s population rule; why extended; M2 fixture. K3's mid-flight holders (KEEP, KEEP_IN_SAMPLE, SURVIVED) and a new `RequiresDifferenceStatement` answer not adopted (r4 R8: the owning branch's own Tier-2 launch would be blocked; and a sub-region of an *unresolved* broader claim is a legitimately different hypothesis — a narrower claim can hold where the broader fails). Evidence: plan-r4 §4:299-306 (exact-key only), §7:742-746 (population ⊇ scope). |
| 8 | M0's schema names four behaviors no M0 fixture exercises — escrow reservation/release, ceiling enforcement, yank reach, `disowned` propagation — and nothing at M0 spends above Tier 0 | MED | O3 (partial), S (escrow fixture) | §13 M0, M1 | ACCEPT-PARTIAL. M0 keeps the columns (the shape is gotten right once; r1 U, r2 R2 stand) and states that the behaviors are exercised first at M1 with a fixture writing and reading each column at M0; M1's done-when gains the escrow and yank fixtures (cluster 2's plus: a yank disowns every attempt inside its reach — no cache, no ticket, absent to `justify` — and attempts outside stand); M1's "Adds" names the behaviors. O3's relocation of the escrow release *rule* out of the M0 schema not adopted (the rule is schema). Evidence: plan-r4 §13:1059-1068 vs :1019-1032 (no consumer at M0); §13 closing paragraph. |
| 9 | "The human queue" is routed to from §6, §7, §8, §10 and never defined; "never stops researching" sits beside non-defaulting human gates with no stated envelope | MED | O5 (partial), K5 | §10, §13 M1 | ACCEPT-PARTIAL (merged). The human queue is a typed substrate object (class enum, the branch or statement it blocks and its blocker, enqueue time; closed only by a human-path record or a cleared blocker); the orchestrator may read depth and age and prefer branches needing no human input — a strategy choice, never a lowered class, skipped gate or requested waiver — and depth/age are P4 inputs, never gate inputs; an *autonomy envelope* states what runs unattended (Tier-0/1 work, ledger writes, ticketed Tier-2 where the knob permits, CONJECTURE / STRONG-EMPIRICAL accumulation) and what waits (PROVEN, Tier 3, no-go acceptance, `*_review` blockers); M1 builds the object. O5's "declared expected review cost from the gate bundle" not adopted (a service rate is measured, not declared; nothing branches on it at M0–M4). Evidence: plan-r4 §10:934-937, §6:640, §7:792, §7:866-868 (uses); §9:905-913 (the sentence the envelope bounds). |
| 10 | Nothing gates what leaves the harness; "submission" is undefined; the one documented fabrication in the evidence base was an output artifact | MED | O1 (partial) | §10, §4 (bundle), §13 M0/M4 | ACCEPT-PARTIAL (narrowed). An *Egress rule* in §10: negative-results entries, human-queue items, operator reports and submissions are rendered by a gate-owned renderer from claim statement nodes and ledger records — every assertion names a claim statement hash with its derived tag and evidence pointer, a tagless sentence is prose and never a finding, a `refuted`/`withdrawn` version is never a standing assertion, and a *submission* (the egress of a recovered `x`) is the verifier's passing node or nothing ("no submit, ever"); the renderer and refusal predicate are bundle fields with the §4 planted pair; built with the negative-results map at M4, the submission rule with the verifier at M0. O1's "free prose asserting anything that names no statement hash is refused" not adopted ("asserting anything" is undecidable mechanically; the typed-element form is), nor its addition to the immutable gate-layer list (an invariant enumeration). Evidence: `PROPOSALS.md:245` (AI Scientist v1 hallucinated an ablations table, arXiv 2408.06292v3 §8), `HANDOFF.md` non-negotiable 1 ("No submission without a passing verifier subprocess"). |
| 11 | A `measured` REFUTED entry's retry predicate has no author and no default, and the preflight's `Blocked`/`Allowed` turns on it | LOW | S3 | §4 | ACCEPT (makes the implicit explicit). Met only by a gate-owned re-measurement of the same hypothesis object under the current ladder plan whose verdict is not REJECT, enqueued by the human before M4 and the auditor from M4, never by the proposing worker (`null_control_pending` is one instance); a `formal` entry has none; the gate that writes the entry writes the predicate; why added. Evidence: plan-r4 §4:287-296 (the null-control path already says "any other verdict … meets the entry's retry predicate"). |
| 12 | The per-rung memory cap is the BSGS table for that size, 2¹⁵ entries at 30 bits, so an honest constant-memory model is REJECTed at the smallest rung while under the cap at 50/60 | LOW | S4 | §6, §13 M1 | ACCEPT. The cap binds at the rungs where the floor is measured (50 and 60 bits; 2³⁰ entries at 60 named); the pre-registered memory model is checked at every rung and undeclared growth stays REJECT; why added. Not a weakening: the 50-bit floor's cap and the memory-model REJECT are unchanged. Evidence: plan-r4 §6:593 and the floor's own statement at 50 bits (§6:650-652); BSGS √n entries, `briefs/adjacent-distributed-collision-search.md:51`. |
| 13 | "The gate reads five things and nothing else" is contradicted by the boundary-table refusal, the §8 flag and the router class in the same paragraph | LOW | O6 | §5 | ACCEPT (wording): five launch-supplied inputs and no others, judged against three gate-owned objects (boundary table; §8 flag with its `nogo_review`; router class). Evidence: plan-r4 §5:483 vs :497-499, :523; §7:828-832. |
| 14 | A worker subprocess killed with the harness leaves an attempt at a non-terminal status that is neither a `Leaked` worker exit nor a harness-terminated status | LOW | L2 (truncated; rationale recovered) | §4, §13 M0/M3 | ACCEPT. `INTERRUPTED`: the status a restart scan assigns, before any new launch, to every attempt in flight when the process died; ≠ OK (never cached, never a ticket, never evidence); not a leak; why added; M0 schema; M3 crash fixture extended. Evidence: plan-r4 §4:343-347 (two harness-terminated statuses only). |
| 15 | An LLM's echoed context cannot prove what it did not receive; the dispatch canary as written is a smoke test, not a grounding | LOW | G3 (partial) | §4, §13 M1 | ACCEPT-PARTIAL. The dispatch record names node hashes, role-template hash, allow-list and — where the dispatch path exposes the request it emits — the request-bytes hash; the canary is decided on those bytes where observable and on the echo otherwise, an echo omitting a token being a regression signal and not a proof, the grounding record naming which form ran; M1 canary reworded. G3's `dispatch_manifest` node and "the harness verifies the rendered request derives solely from the manifest" not adopted (presumes Cairn renders the provider request; the grounding says the SDK composes it — `grounding/dbos-sqlite-and-agent-sdk-isolation.md:30-35`). Evidence: same file :40 (OPEN). |
| 16 | §6 (0) still says "method identity (skill@version and canonical parameters)" after r4 #10 bound the hypothesis to the interface version; §7's producer identity says `skill@version` | LOW | G4 (partial) | §6, §7 | ACCEPT-PARTIAL in the plan's vocabulary ("the skill's interface version with its canonical parameters"; "the §2 identity bundle hash or the gate-run record"). G4's `method_interface_id` / `implementation_identity` renames re-litigate r4 R6. Evidence: plan-r4 §6:544 vs §3:143-147. |
| 17 | "Gate-outcome reward" names no sign: a reward paying only KEEP/PROVEN/SURVIVED starves the Skeptic and the REJECT paths §9 counts as knowledge | LOW | K2 (partial) | §5 | ACCEPT-PARTIAL (one clause). A gate outcome is a terminal resolution of either sign (KEEP, a REJECT that writes a ledger entry, SURVIVED, KILLED, a derived tag, a machine-checked negation); INCONCLUSIVE, harness-terminated attempts and refused launches are not outcomes; why added. K2's class point schedule, negative rewards for harness faults and P3 (ii) rewrite not adopted (r1 V: schedules invented, P3 decides; `Leaked` and a disowned serve are harness defects, not branch outcomes). Evidence: plan-r4 §5:474-478, §9:908-912. |
| 18 | The tier derivation and the ceiling read the same declared profile, so an understated declaration buys a Tier-1 ticket for Tier-2 work | LOW | K1 (partial) | §5 | ACCEPT-PARTIAL (the bound stated): an understated declaration buys at most a multiplier-wide overrun before `BUDGET_EXCEEDED`, visible as the measured-versus-declared ratio P4 watches. K1's certification-time `cost_calibration` table with a fitted model and a `cost_range_extension` waiver not adopted: it moves the free variable into a benchmark-extrapolation model, adds a human-queue item per new input range, and the exposure is bounded and spend-only (no tag moves); CONJECTURE with no incident evidence. Evidence: plan-r4 §5:441-447, :464-470. |
| 19 | The formalization gate's steps are numbered but not ordered cheapest-first; a `sorry`-shaped Solution can reach `leanchecker --fresh` | LOW | K7 | §7 | ACCEPT. The gate plan orders: pin and formal-statement-hash check, pre-filters, Tier-≥ 2 review verdict, sandbox build, axiom computation, kernel replay, closure comparison; an earlier failure blocks later steps (§4's ordered scopes). Evidence: `grounding/lean-checker-protocol.md:41` (`--fresh` 32.3 s mathlib-free, mathlib OPEN), `grounding/lean-statement-linters-vacuity.md` §4 (`collectAxioms` on the built environment); §4 gate discipline (ordered scopes). |
| 20 | §8 says a flagged attack holds "no ticket above Tier 1 until the declaration exists" while §5's Tier-1 ticket requires the presence check | LOW | S5b | §8 | ACCEPT (wording): no Tier-1 ticket while the declaration is absent; no ticket above Tier 1 until `accept_for_tiering`. |
| 21 | The type of the statement's `scope` and the evidence node's `declared population` is not closed, and `informs` reads like an edge | LOW | O (c.1), O (c.4) | §7 | ACCEPT. Population/scope record pinned: `{target family (categorical), size interval, declared parameter ranges (axis-aligned intervals), assumption set (content-addressed identifiers)}`, compared as the §4 reach compares (interval containment, categorical equality, set inclusion); `justified_by` is the only typed edge, "inform" names none. Evidence: plan-r4 §7:735-741, §4:276-281. |
| 22 | "A rung with any failed trial is at most INCONCLUSIVE" reads against "must complete at 60 bits" | LOW | D (stream A) | §6 | ACCEPT (wording): never KEEP, and REJECT where the ceiling value already misses the model or the floor. D's reading as a contradiction does not reproduce ("at most" in the verdict order). |
| 23 | M1 (l) and M2 both name "the human path"; the M2 fixture "differing only in implementation revision is Blocked" is true for `measured` entries only | LOW | D (stream B), S | §13 M1, M2 | ACCEPT (wording): "the human path of §4" in both; the M2 fixture says `measured` and adds the `implementation`/certified-revision `Allowed` case (with cluster 3); the statement-review workflow "routes green artifacts to the human queue and records verdicts through the human path of §4". |

Accepted clusters: 23 (9 of them partial). Gate-bundle contents re-enumerated to carry the
egress renderer and its refusal predicate; §13 names builders for the human queue object (M1)
and the renderer (M4).

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | Split M1 into M1a (empirical) / M1b (proof) | K4 | Restructuring that moves text without adding a mechanism (rule 8); milestone gates are properties, not calendar units, and the conjunction can be sequenced inside M1; evidence offered is SPECULATION on calendar; r1 AE (milestones by count) adjacent. Recorded as an operator question. |
| R2 | Delete "expected information per compute-dollar" | K6 | Re-litigates r2 R3, r3 R2, r4 R2 (fourth time) with no new evidence; the phrase is `HANDOFF.md`'s and the sentence names the implemented surrogate; cluster 17 sharpens the surrogate instead. |
| R3 | Operator default "Sage/PARI" → "PARI (Sage absent, PROVEN by probe)" | O7 | Re-litigates r1 D, which retained the default with the same evidence (`grounding/pari-sage-toy-curve-backend.md` §1 — reproduced here); a default is a choice, not a description of the machine; the second-backend install decision is already an M0 decision (§13) and open question r1 Q1. |
| R4 | A default estimator (median of per-instance speedup ratios, percentile bootstrap, 10⁴ resamples) | D (stream C) | r3 #4 deferred the estimator's form to M1 inside the versioned comparison protocol; no new evidence; the CI method and coverage are bundle fields M1 names. |
| R5 | M4 bar: one negative-results entry or lemma produced on an unseeded subproblem | O framing (b) | Re-litigates r4 R5 / O4 half: an outcome that depends on the problem drawn is research luck, not a demonstrable property; recorded as an operator question (adopt as a practice, not a milestone gate). |
| R6 | `INVALID_EXECUTION` as a fifth ladder verdict | G1 (half) | The ladder's verdict set is fixed in the ladder plan (r2 #1) and the aim is met by routing the ledger kind from the fired predicate (cluster 3); the trial still fails the ladder. |
| R7 | `method_interface_id` / `implementation_identity` identifiers | G4 (half) | r4 R6: renames for fields the §2 bundle already has; the wording fix was accepted (cluster 16). |
| R8 | Class point schedule with positive/zero/negative sets; P3 (ii) rewrite | K2 (half) | r1 V: a schedule with invented weights; P3 decides the mechanics; harness faults are not branch outcomes. The sign-agnostic clause was accepted (cluster 17). |
| R9 | Certification-time `cost_calibration` table and `cost_range_extension` waiver | K1 (half) | Moves the free variable into a benchmark-extrapolation model and adds a human-queue item per new input range; the exposure is bounded by the multiplier and spend-only; CONJECTURE, no incident. The bound was stated (cluster 18). |
| R10 | Mid-flight KEEP / KEEP_IN_SAMPLE / SURVIVED holders as `AlreadySettled`; a new `RequiresDifferenceStatement` answer | K3 (half) | r4 R8 (the owning branch's own launch would be blocked); a sub-region of an unresolved broader claim is a different hypothesis. Promoted holders accepted (cluster 7). |
| R11 | Declared expected review cost per queue class | O5 (part) | Nothing branches on it at M0–M4; a service rate is measured, not declared. |
| R12 | "Free prose asserting anything that names no statement hash is refused"; egress added to the immutable gate-layer list | O1 (part) | "Asserting anything" is mechanically undecidable; the typed-element form was adopted (cluster 10); the gate-layer list is an invariant enumeration the synthesizer does not extend. |
| R13 | `verification_liability` object and an M0 fixture for it | G2 (part) | A node-bound field of the existing reservation; the fixture lands at M1 with the behaviors (cluster 8). |
| R14 | `dispatch_manifest` node and "the harness verifies the rendered request derives solely from the manifest" | G3 (part) | Presumes Cairn renders the provider request; the grounding records that the SDK composes it (`grounding/dbos-sqlite-and-agent-sdk-isolation.md:30-35`). Fields on the existing dispatch record, where observable, were accepted (cluster 15). |

Rejected clusters: 14 (R6–R14 are partial rejections inside accepted clusters).

## 3. Flagged invariant attacks

None this round. No seat proposed weakening §0, the gate layer's existence or immutability, the
taxonomy, the ladder's verdict rule, the verifier, the no-go checklist or the honest baseline.
G1's `INVALID_EXECUTION` was judged on the verdict-set contract, not as an attack (the trial
still fails the ladder); cluster 12 moves where the memory cap binds and leaves the 50-bit
floor's cap and the memory-model REJECT intact. Every accepted change adds a boundary, a
fixture, a typed field, a ticket requirement or a stated bound; none removes a gate input.

## 4. Factual corrections (each checked against the cited file)

1. The escrow release rule contradicts the §3 deferred re-run — plan-r4 §5:452-456 vs §3:199-203.
   **Changed a mechanism** (reservation bound to the node).
2. "The human path" is used six times (plan-r4 §7:786, §8:886, §13:1093, :1150, §2 by
   implication, §10) and defined nowhere; §3:234-241 fixes one substrate writer. **Changed a
   mechanism** (the attestation file and digest-bound rows; two M0 fixtures).
3. "Five things and nothing else" — plan-r4 §5:483 vs :497-499, :523 and §7:828-832. Wording.
4. GLM's multi-kind gap reproduces — plan-r4 §5:503-512. Ticket-lattice clause.
5. The Tier-3 ticket vs the one-tier rule — plan-r4 §5:494-495 vs §6:624-625. Lattice clause.
6. The in-sample predicate gap — plan-r4 §6:567-568, :616-620, §13:1076-1078. Ladder clause.
7. Opus #1's incident evidence reproduces — `PROPOSALS.md:245` (AI Scientist v1 "hallucinated an
   ablations table", arXiv 2408.06292v3 §8); `HANDOFF.md` non-negotiable 1 defines submission
   as the thing the verifier gates.
8. Opus #7's fact reproduces (`grounding/pari-sage-toy-curve-backend.md` §1: Sage absent, PROVEN
   by probe) — the operator default stands (r1 D); not integrated.
9. D's "a 2× ceiling aborts ≈ 2.3 %, not 4 %" does not reproduce: the plan's figure is under a
   Rayleigh step-count model (`P(T > 2·mean) = exp(−π) ≈ 4.3 %`), re-derived by the Opus seat
   and here; the normal approximation is the wrong model for a collision time. Not integrated.
10. D's "one run in five" — r3 correction 8 stands (the un-widened test); not re-litigated.
11. D's M1 (l) vs M2 "contradiction" does not reproduce (r3 #3 placed the verdict fixture at M1
    and the workflow at M2); wording unified on "the human path of §4".
12. D's 60-bit completion vs "at most INCONCLUSIVE" does not reproduce ("at most" in the verdict
    order); wording clarified (cluster 22).
13. Opus Part 0 fact pass re-verified on a sample: `pari-sage-toy-curve-backend.md` §1–§3 (gp
    exits 0 on fatal errors, zero-fills, 60-bit stack overflow, ellcard tries 11–220),
    `adjacent-distributed-collision-search.md:50-51` (0.11 µs, 0.886√n, 1.25√n, BSGS entries),
    `dbos-sqlite-and-agent-sdk-isolation.md:40` (OPEN). All hold.
14. Grok #7's order is consistent with the grounding: `collectAxioms` runs on the built
    environment (`lean-statement-linters-vacuity.md` §4), `--fresh` is the expensive step
    (`lean-checker-protocol.md:41`).

Corrections 1 and 2 changed mechanisms ⇒ verdict cannot be STEADY (and cluster 1 is HIGH).

## 5. Seat reliability

- **GPT-5.6-terra:** complete; 4 numbered proposals with diffs, format respected. G1 partial
  (MED; verdict name rejected, ledger routing accepted), G2 merged (MED), G3 partial (LOW), G4
  partial (LOW; renames re-litigated r4 R6). Its "facts needed" (native-skill sandbox, budget
  enforcement primitive, countable arithmetic extension, human-ruling authentication) are sound;
  the fourth is answered by cluster 1, the rest are open questions.
- **Grok-4.5:** complete; 7 proposals with diffs. K1 partial (LOW), K2 partial (LOW), K3 partial
  (MED), K4 rejected (churn), K5 accepted (LOW, merged into §10), K6 rejected (fourth
  re-litigation), K7 accepted (LOW). Its framing (b) — "a fail-closed, negative-result-first
  engine with a human airlock" — is met by the autonomy envelope and the sign-agnostic outcome
  clause rather than by deleting the VoI sentence.
- **GLM-5.2:** in format (numbered proposals with diffs) but truncated mid-proposal 2 at "The
  plan's" (3.2 KB); 1.5 proposals. L1 accepted (MED), L2 accepted (LOW) from its recovered
  rationale. No over-severity on L1 (judged MED here, seat said HIGH).
- **DeepSeek-v4-flash:** 41 KB reasoning stream ("Potential issue N … Good."), no numbered
  proposals or diffs, truncated mid-item "T."; exceeded the format for the fifth round. Three
  candidate findings recovered (A, B, C): A accepted as wording (LOW), B does not reproduce
  and is resolved by cluster 1's wording, C rejected (deferred by design). One arithmetic
  claim uses the wrong model (correction 9); its other checks agree with the plan.
- **Opus grounded:** complete; Part 0 fact pass (re-verified on a sample, holds), 7 proposals,
  framing, facts. O1 partial (MED, narrowed), O2 accepted (HIGH — the round's structural
  change), O3 partial (MED), O4 merged (MED), O5 partial (MED), O6 accepted (LOW), O7 rejected
  (re-litigation of r1 D). Framing (b) M4 bar rejected (r4 R5); facts (c) 1 and 4 accepted as
  LOW; (c) 2 folded into cluster 1 (two OS users as M0 deployment shape); (c) 3 answered by
  cluster 10; (c) 5 an open question.

## 6. Open questions for the operator

1. Does the dispatch path (Agent SDK) expose the request bytes it sends — a base-URL or proxy
   hook — so the M1 canary can be byte-level? If not, the isolation property stays
   echo-grounded and the dispatch record says so (cluster 15; GPT c.1).
2. The native-skill sandbox contract: what a Tier-0/1 skill subprocess may reach (host SQLite
   files, the pin/checkpoint/attestation location, network, process table) beyond "no substrate
   write capability" (GPT c.1).
3. The budget-enforcement primitive: cooperative process limits vs cgroup / job-scheduler
   reservations (GPT c.2) — it decides how hard the §5 ceiling and the escrow accounting are.
4. Human review throughput (items per week) to size the P4 queue-age alarm and M4's tracks
   (Opus c.5; r4 Q3 stands).
5. Adopt Opus's M4 honest-yield demonstration (one unseeded negative-results entry or lemma) as
   an operator practice outside the milestone gate? Rejected twice as a gate (research luck).
6. Split M1 into empirical and proof tracks as a project-management choice outside the plan
   (Grok #4)?
7. Operator default wording "Sage/PARI" vs PARI-only (Opus #7) — the second-backend install
   decision (r1 Q1) stands either way.
8. r1–r4 questions that stand: compiled baselines at M1; yank / salt authority; the two OS users
   and host (cluster 1 makes them an M0 deployment shape — confirm macOS `uappnd` vs Linux
   `chattr +a` for who may set and clear the flag); statement-review reviewer identity and
   expiry; Linux host for the PROVEN gold tier; Tier-2 human-session knob; M4 checkpoint writer
   and write rate; M3 starvation bar; pruning P5–P7; auditor self-disagreement practice;
   counted field arithmetic for non-generic methods; tier boundary table values; interface-
   version bump detection; node volumes for the audit line.

## 7. Validation

- **(a) Self-containment.** Most obscure M0 task: the human path — the attestation file with
  its digest-and-offset rows and the `justify` fixture that treats an unmatched row as absent.
  Implementable as written: location (beside the gate-bundle pin), owner (operator), mode (the
  orchestrator's process user reads and cannot write), record form (the canonical record under
  the §3 canonicalizer), row fields (digest, offset), the reader rule (absent unless matched),
  the writer (the harness writer mirrors), and the two M0 fixtures; it presumes the two-OS-user
  deployment M0's grounding step names. The `INTERRUPTED` scan is implementable ("before any
  new launch"). At M1 the in-sample check is a formula with named inputs (fitted parameters,
  rung means, A/A radius, trial count) and fixture (a) is decidable from it.
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism
  added this round: M0 — attestation file and digest/offset fields, write-boundary grounding and
  fixtures, `INTERRUPTED` status, escrow/ceiling columns, the submission rule with the verifier;
  M1 — escrow/ceiling/yank/`disowned` behaviors and fixtures, in-sample check, cap at the floor
  rungs, REJECT-to-ledger-kind routing with the yank trigger and fixture (b), multi-kind and
  Tier-3 ticket fixtures, canary form, gate-plan order, the human queue object; M2 —
  dominated-region `AlreadySettled` fixture, `measured`/`implementation` fixture, workflow
  through the human path; M3 — `INTERRUPTED` crash fixture; M4 — the egress renderer with the
  negative-results map. No orphan: each has a consumer that branches on it (`justify`, the tier
  gate, the preflight, the ladder verdict, the restart scan, the renderer's refusal predicate,
  the milestone gate).
- **(c) Justification sampling.** Human path (why: a verdict the only writer can mint for itself
  is a floor the gated party sets); node-bound escrow (why: release at terminal status leaves
  the deferred re-run unfunded when the derivation waits on it); ledger kind by predicate (why:
  a wrong answer says nothing about the method's cost); in-sample predicate (why: a model miss
  each implementer defines is a different ladder under one name); dominated-region
  `AlreadySettled` (why: the range-jitter loop on the success side). All five carry a why; so
  do the envelope, the egress rule, the measured retry predicate, `INTERRUPTED`, the cap's rungs
  and the M0 scope statement.
- **(d) Steady-state diff.** +192 lines (1281 → 1473), ≈ 320 changed lines. Structural in one
  place — the human path, a new write boundary for every human-attested node with two M0
  fixtures — and mechanism-level elsewhere: §5 (node-bound escrow, ticket lattice for multi-kind
  claims and Tier 3, "most recent" rule, gate inputs, ceiling bound, sign-agnostic outcomes);
  §6 (in-sample predicate, cap at the floor rungs, REJECT-to-ledger-kind routing); §4
  (dominated-region `AlreadySettled`, retry-predicate defaults, `INTERRUPTED`, dispatch record
  fields); §10 (human queue, envelope, egress rule); §7 (scope grammar, gate-plan order); §13
  (M0 scope, fixtures). Section numbering, §0, §8's three items, §9, §14 and §16's invariant
  list unchanged. Comparable in structure to r4 (one structural item), smaller than r1–r3.

## 8. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Expected residual scope for round 6: coherence of the human path with
§3's single-writer contract and the M0 deployment shape (the attestation file beside the
checkpoint file — two operator-owned append-only files with different writers), and of the new
ticket-lattice clauses (multi-kind, Tier-3 node, "most recent") with §6's table tiers —
wording-level unless a seat finds a new contradiction.
