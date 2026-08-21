# Ledger — round 4

Plan reviewed: `research/convergence/plan-r3.md` (v3, 1117 lines). Plan produced:
`research/convergence/plan-r4.md` (1281 lines; 326 diff lines against r3 before rewrapping).
Synthesizer own view (written before any seat was opened): `research/convergence/r4/own-view-r4.md`.
Seats: GPT-5.6-terra (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-flash (D), Anthropic Opus
grounded (O); synthesizer own view (S). Prior ledgers read in full: `r1/ledger-r1.md`,
`r2/ledger-r2.md`, `r3/ledger-r3.md`.

Verdict: **NEEDS-ANOTHER-ROUND** — one accepted cluster is HIGH (the ladder's KEEP predicate
named its estimator as the cost ratio claim/baseline while requiring the CI to clear `1 + 2·radius`,
the inverse of the source statistic; the correction re-orients the acceptance predicate of the
plan's top anti-fabrication gate), and that factual correction changed a mechanism.

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | KEEP predicate inverted against its own estimator: "a CI on the ratio of claim cost to baseline cost" must "clear `1 + 2·radius`" | HIGH | O1; D ("clears" is ambiguous) | §6 | ACCEPT. The estimator is a CI on the speedup factor — baseline group-operation cost divided by claim cost, a real advance above 1 — and "clears" is pinned: the CI's lower bound exceeds the band, floor `1.01`. Verified: `briefs/frankensqlite.md:22` (`min_gain = max(1 + 2·radius, 1.01)`, "KEEP only if the entire claim CI clears the band" — the statistic is a gain), `PROPOSALS.md:288-289`; plan-r3 §6:494-495 introduced the inverse wording in r3 (cluster 4). Internal cross-checks agree with the corrected orientation: control (j) is "√2 on group operations" and "the √2 control at the band's edge" parses only against ≈ 1.28. Re-judged HIGH: a literal implementation KEEPs a method 30 % slower than rho and REJECTs a √2 speedup. |
| 2 | The 10² trial floor cannot pass positive control (j); solved count n ≳ 130 | LOW | O1 (second half) | §6 | ACCEPT-PARTIAL (wording with a number). At sd ≈ 0.5·mean the A/A radius at 10² is ≈ 0.14, band ≈ 1.28, the control's CI lower bound ≈ 1.22 ⇒ INCONCLUSIVE; solving `1.414(1 − 1.386/√n) > 1 + 2·1.386/√n` gives n ≳ 130 under independent arms; M1 measures the paired variance and records the count. Arithmetic re-done (agrees with r3 correction 7). The plan already said M1 sizes the count; the number is stated so the floor is not mistaken for the count. |
| 3 | §5's "four things and nothing else" contradicts §2's tier-gate duties (refuse yanked and uncertified revisions) | MED | O2 | §5, §13 M1 | ACCEPT. Fifth input: the launch revision's self-test standing (certified, not yanked); refusal conditions name it; M1 fixture: a yanked or uncertified revision is refused whatever ticket it holds. Verified: plan-r3 §2:77-78, 83-84 vs §5:425, 433-435 (internal contradiction). Re-judged MED from HIGH: the mechanism exists in §2; §5's predicate gains an input. |
| 4 | The axiom check has no named producer; `leanchecker` does not reject `sorryAx`; a list emitted by the Solution's build is a count reported by the party gated | MED | O3 | §7, §13 M1 | ACCEPT. (iii) the gate computes the axiom set itself — comparator's check at the gold tier, a gate-owned module in the bundle running `Lean.collectAxioms` over the Challenge's theorem names on the ordinary path — never a list read from the Solution's own build output; why sentence added. Verified: `grounding/lean-checker-protocol.md` §3 ("does NOT reject `sorryAx` or extra axioms"), §2 (`Axioms.lean:45`), `grounding/lean-statement-linters-vacuity.md` §4 ("an axiom gate alone is `Lean.collectAxioms` plus a whitelist"). Re-judged MED from HIGH: a producer pinned on an existing check. |
| 5 | No milestone demonstrates motion: every done-when tests detection; a harness that refuses everything passes a planted corpus | MED | O4 | §13 M3 | ACCEPT-PARTIAL. M3's done-when gains the motion half on known answers: on seeded runs holding one branch whose hypothesis is control (j)'s true advance and one whose hypothesis is fixture (a)'s method, the orchestrator's own dispatch carries the first to KEEP and a STRONG-EMPIRICAL tag through `justify` and the second to a measured REFUTED entry, unaided. O4's bar on "a genuinely open small subproblem chosen by the operator" at M2 not integrated: M2 has no orchestrator to run unattended, and an outcome that depends on the problem drawn is research luck, not a demonstrable property (r1 AE precedent on count-based bars). Code branches on the accepted half (the milestone gate). |
| 6 | Verification escrow is reserved and never released; the auditor's periodic re-runs cannot be funded from a one-time per-node escrow; reservation not released on failure | MED | O5, G2, L3 | §5, §7, §4, §13 M0/M4 | ACCEPT (merged). Reservation released to the granting branch at terminal status — spent where the §3 policy's first check ran (admission witness check, Tier-0/1 re-run, Tier-2/3 re-run at `justify` time or on the auditor's first draw), released unspent on status ≠ OK or disown; every later re-verification is funded from a standing per-cycle audit line the gate bundle names (bundle contents updated); auditor text restated; M4 done-when: the audit record names its cycle grant and per-stratum charges, which reconcile; M0 schema names the escrow and its release rule. Evidence: plan-r3 §5:401-403 and §7:738-741 (internal accounting contradiction: "periodically re-audit" from a single launch escrow). |
| 7 | The ladder nonce may be reused across runs of one immutable hypothesis object; the first run's table publishes its seeds | LOW | O6 | §6 | ACCEPT (one clause): a fresh nonce per ladder run, never derived from the object, never reused; a rung re-run after INCONCLUSIVE sees fresh instances. Evidence: plan-r3 §6:482-486 (nonce drawn "after the hypothesis object is recorded", seeds recorded in the table); the fixed-input exploit class the same step cites. |
| 8 | M0 "observed draws span 20–220" vs the grounding table's 11–220 | LOW (factual) | O7a | §13 M0 | ACCEPT. Verified: `grounding/pari-sage-toy-curve-backend.md:17-19` (ellcard tries 48/148/20, 40/52/57, 36/11/220); the grounding's own prose at `:21` says "20–220" and the plan quoted it — the table governs. Wording; no mechanism. |
| 9 | CPU-seconds per trial "over what": a child process hides arithmetic from the clock | LOW | O7b | §6 | ACCEPT. User and system time summed over the trial's whole process tree; a ladder-tested method's allow-list permits no process spawn beyond the backends its hypothesis object declares. |
| 10 | `skill@version` names two duties: the recipe key needs the executable, the hypothesis key needs the method; a revision bump mints a clean key, or an old ticket spends for a new executable | MED | G1 | §2, §3, §5, §6, §13 M1/M2 | ACCEPT-PARTIAL, in the plan's own vocabulary. The hypothesis key's method identity is the skill at its §2 *interface version* with canonical parameters, never the implementation revision (a measured refutation reaches every revision; an `implementation` entry's retry predicate is met by a new certified revision, so it blocks the executable and never the method); the recipe key's `skill@version` is the hash of the full §2 identity bundle; the ladder's dispatch record and result table name the implementation revision and the tier gate refuses a ladder ticket whose revision differs from the launch's (a new revision re-ladders before it spends); M1 fixture (revision mismatch refused), M2 fixture (a proposal differing only in implementation revision is Blocked). G1's new identifiers (`method_semantics_id`, `implementation_id`) and its "explicit review when a purported implementation-only revision changes semantics" not integrated: the interface version is the existing field, and no decider for "semantic" is named (G1 lists it as a fact it would need) — a renamed interface version is a worker's claim the near-dup advisory and the Librarian already route. Evidence: plan-r3 §2:50-52 (bundle separates interface version from implementation revision), §3:100 and §3:142 (one token, two keys), §6:473. |
| 11 | M3's "funding is withdrawn" reads as the terminal `withdrawn` status; M3's done-when does not lock "pivots never write REFUTED", revival, or crash-resume | LOW | G4, K5 | §13 M3 | ACCEPT (merged into the M3 done-when with cluster 5): the stalled branch is force-parked with `low_yield_pivot`; no REFUTED row and no terminal `withdrawn` is written by the orchestrator's path; the parked branch auto-revives when its pinned predicate clears; a crash mid-tick resumes without double-applying a completed step (§15 P3). K5's `AlreadySettled` run condition folded into cluster 13's M2 fixture rather than M3. Evidence: plan-r3 §4:307-311 vs §13:1002 (internal). |
| 12 | The conjectural statement hash must not be the equality decision; the comparator decides | LOW | G5 | §7 | ACCEPT-PARTIAL (one clause): the hash names and binds, decides nothing; check (iv) is the comparator's own closure comparison; a hash match with a comparator mismatch fails closed. G5's readiness flag not integrated: before M1 no PROVEN derivation exists (no gate), and after M1 the gate is the comparator — a flag no code branches on. Evidence: plan-r3 §7:604-606 already made (iv) the comparator check. |
| 13 | A settled success can be re-funded forever; under gate-outcome reward the cheapest loop is re-laddering known positives | MED | K2 | §4, §13 M2 | ACCEPT-PARTIAL (narrowed). The preflight answers `AlreadySettled` when a proposal opens a new branch on a hypothesis key a branch already holds (active, parked, or promoted with its claim at PROVEN / STRONG-EMPIRICAL) and is not a superseding object: park with blocker `already_settled`, clearing on a superseding object with its attributed difference statement or when the holder withdraws; the holding branch's own launches and gate-owned re-runs never see it. K2's inclusion of KEEP / KEEP_IN_SAMPLE / SURVIVED as "settled" not adopted — those are mid-flight tickets and the owning branch's Tier-2 launches must not be blocked by its own ticket. Why recorded. Evidence: plan-r3 §5:415-419 (reward = gate outcome per cost) and §4:251-267 (preflight blocks on REFUTED only); CONJECTURE as K2 tags it. |
| 14 | Yank reach is narrowed by the party that shipped the fault; default must be the full revision | MED | K1 | §2 | ACCEPT. Reach defaults to the whole implementation revision; a narrower predicate is installed only by an attributed human ruling recorded beside the yank, which workers and the orchestrator may propose and never install; why added. Evidence: plan-r3 §2:79-81 (reach "declared" with no author); the waiver pattern (`PROPOSALS.md` C5) is the model. |
| 15 | Tier gate admits a self-declared tier inconsistent with the profile's production cost | MED | K3 (i)-(ii) | §5, §13 M1 | ACCEPT-PARTIAL. The declared tier is a claim the gate checks: the gate derives the launch's tier from the production cost at the launch's inputs under the bundle's boundary table (in the bundle since r3 #7) and refuses a lower declaration with `TierRefused`; the ≈ 10³ core-hour rule is that table's Tier-2/3 edge; M1 fixture. K3 (iii) `min(multiplier × declared, multiplier × tier_max)` not integrated: redundant once (i)–(ii) hold (declared ≤ tier max). Evidence: plan-r3 §5:389-392 (only the T2→T3 edge stated), §5:403-415 (ceiling is per-run enforcement after the spend begins). |
| 16 | "has been reviewed" (§8) is prose; the tier gate needs a node | MED | K4 | §8, §13 M1 | ACCEPT-PARTIAL. `nogo_review {hypothesis hash, declaration hash, reviewer, verdict ∈ {accept_for_tiering, reject, needs_revision}, gate-bundle hash, time, supersedes?}`, immutable, human-path only, absence ≡ flagged; `accept_for_tiering` restores ordinary ticket eligibility only; the declaration is a content-addressed node the branch points at, outside the hypothesis key (its words are prose); M1 adds the node with the presence check. K4's "Skeptic may attach notes" kept; nothing else changed. Evidence: plan-r3 §8:757-758; the `review_verdict` pattern (r3 cluster 3). |
| 17 | `TierRefused` has no defined disposition for the orchestrator | LOW | L1 | §5, §15 P4 | ACCEPT-PARTIAL. The branch stays active; the next tick funds the tier-below work that would produce the ticket, parks with `budget_preempt` or withdraws; an unchanged re-submission is refused again; repeated `TierRefused` on one key is a P4 drift-monitor input, never a claim input. L1's `tier_refused` blocker not adopted: a parked branch is not funded, so the ladder that would mint the ticket could never run. Evidence: plan-r3 §4:300-303 (the `BUDGET_EXCEEDED` disposition is the model). |
| 18 | `RequiresNullControl` re-measurement that overturns the original has no resolution rule | LOW | L2 | §4, §13 M2 | ACCEPT-PARTIAL under existing rules: a REJECT under the current ladder plan confirms the entry (`Blocked`); any other verdict is a gate-owned measurement that meets the retry predicate (`Allowed`, the new branch records the table as the evidence that met it); the original evidence node keeps its rows and gains an append-only `superseded_by` pointer; the entry is never rewritten; M2 fixture. L2's `retracted` mark and REFUTED→PARKED status move not adopted: the plan's `Allowed`-when-retry-predicate-met path already expresses it without a status transition on a REFUTED row. |
| 19 | `justify`'s "cover" names no direction | MED | L4 | §7 | ACCEPT. Population: evidence ⊇ statement's scope; assumptions: evidence ⊆ statement's (evidence under weaker assumptions is stronger and covers it); target names the exact statement. Direction checked against the plan's own examples (a model proof's extra assumption ⇒ not covered; a ladder table on sizes ⊇ scope ⇒ covered). |
| 20 | `BUDGET_EXHAUSTED` (hunt) vs `BUDGET_EXCEEDED` (attempt) one letter apart | LOW | L6 | §7 | ACCEPT with the reading corrected: the hunt verdict is `INCOMPLETE` — the §5 ceiling stopped the hunt before its declared count, the attempt's status being `BUDGET_EXCEEDED`; L6's reading of it as a planned non-failing outcome does not reproduce (plan-r3 §7:716-718: "no ticket"). Not a taste rename: two names for one event. |
| 21 | Branch status enum lacks `withdrawn` though the terminal-status invariant names it | LOW | D | §4 | ACCEPT. Verified plan-r3 §4:235-236 vs §4:295-296. |
| 22 | Two differing attempts mark a recipe non-reproducible even when one is disowned | LOW | D | §3 | ACCEPT: "two successful, non-disowned attempts". |
| 23 | "ladder + repro node → STRONG-EMPIRICAL" names no verdict; a REJECT table has the same kind | LOW | D | §7, §13 M0 | ACCEPT: a `ladder_table` justifies STRONG-EMPIRICAL only with verdict KEEP (KEEP_IN_SAMPLE for a statement scoped to the in-sample sizes) on the population it measured; any other verdict justifies nothing; the M0 fixture names verdict KEEP. |
| 24 | A claim with a verified refutation keeps "the strongest class some evidence justifies" | LOW | D | §7 | ACCEPT: a KILLED hunt record with a verified counterexample, a machine-checked negation, or a ladder REJECT on the claim's own model moves the version to terminal `refuted` with the evidence pointer in its tag history, and `justify` returns a lattice violation for any positive class on a refuted version (the §7 downgrade rule made explicit). |
| 25 | The clock cross-check has no reference rate at the 60-bit rung, which runs no A/A arm | MED | S1 | §6, §13 M1 | ACCEPT. The reference rate is gate-measured on the rung's own instances: the A/A arm's rate at ≤ 50 bits; at 60 bits a gate-owned calibration run of the counted arithmetic object (a fixed operation count, never a baseline distribution) recorded in the table, so the clock check applies at every rung. Evidence: plan-r3 §6:524-526 ("no baseline and no A/A arm run there") vs §6:549-553 ("the A/A arm of the same rung"). |
| 26 | "Statement hash" names the claim statement node's content address (§4) and the Lean closure hash (§7); `justify`'s "same statement hash" is not implementable | MED | S2; G5 (adjacent) | §4, §7, §13 M1 | ACCEPT. *Claim statement hash* = the node's content address, named by tags, verdicts, disputes, evidence nodes and `justify`; *formal statement hash* = the closure hash the gate derives when it compiles the Challenge, named by the Solution; the gate-run record binds the two under the bundle hash; a `lean_artifact` evidence node reaches its claim statement through that binding; the Skeptic's closure and M1 (l) re-worded accordingly. Evidence: plan-r3 §4:241-250 (node written before any proof, content-addressed over its fields) vs §7:582-589 (hash over the compiled closure). |
| 27 | M1 fixture (a) is uncatchable as typed: an honest ≥ rho claim that beats BSGS is INCONCLUSIVE, which the done-when counts as an escape | LOW | S3 | §13 M1 | ACCEPT: fixture (a) pre-registers a sub-rho cost, so the catch is the in-sample model-miss REJECT; a claim honest about ≥ rho cost sits inside the band and INCONCLUSIVE is its correct verdict, as for control (k). |
| 28 | The ladder table's replay grade and reproducibility record are unspecified, so its verification escrow cannot be priced | MED | S4 | §6, §13 M1 | ACCEPT. The table's grade is the weakest among its trials (a rho trial with its DP witness is Verifiable, a deterministic trial Replayable); its repro record is the §3 policy per trial plus a recomputation of the statistics and verdict from the verified rows; that is the verification component its launch escrows. |
| 29 | Patience-abort verdict unspecified; free vs fixed model parameters unstated; "at M0 a file" reads as built at M0 | LOW | S (also noticed) | §6, §3 | ACCEPT (wording): an aborted trial enters the model check at the ceiling as a lower bound and a rung with any failed trial is at most INCONCLUSIVE; the hypothesis object declares which model parameters are fixed (exponent and memory shape always) and which the ≤ 50-bit rungs fit; the checkpoint sentence names the M0 deployment shape with M2 as the builder. |
| 30 | M0's done-when never demonstrates the append-only flag binding | LOW | O (c.iii), L (c) | §13 M0 | ACCEPT (wording): M0's grounding step names the §3 facts (WAL, busy timeout, the flag refusing truncation by the orchestrator's process user) among those it records. |

Accepted clusters: 30 (9 of them partial). Gate-bundle contents re-enumerated to carry the
per-cycle audit line.

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | Narrow "a subexponential attack that can't beat BSGS at 50 bits is refuted on the spot" to "refuted on that finite predicate"; measured refutation "does not refute an asymptotic claim ... or a different crossover claim outside that region" | G3 | Re-litigates r1 AD, r2 R1 and r3 R5 (the same re-scoping, fourth time) with no new evidence; the hypothesis object already carries `crossover`, the measured-refutation reach in §4 is already exact, and the retry predicate is the designed path. Softens the ladder — flagged below. |
| R2 | Rename "expected information per compute-dollar" | K6 | Re-litigates r2 R3 and r3 R2 (K9, K7) — the sentence already names the implemented surrogate and forbids every model term; the phrase is `HANDOFF.md`'s own ("allocation currency = expected information per compute-dollar"). |
| R3 | REFUTED → negative-results map intake with a `map_published` flag and draft queue | K7 | Ceremony under rule 13: §11 already defines every entry as the §4 ledger record plus the table and A/A arm, so intake is the definition; no gate branches on `map_published` and no retirement condition is named. |
| R4 | Checkpoint compaction protocol (operator-signed compacted form) | L5 | No defect: startup verification reads the last checkpoint entry, not the file; the file grows by one hash per gate run; r2 #11 already rejected signed / remote anchoring as over-engineering at M0. |
| R5 | Honest-yield bar on a genuinely open subproblem at M2 | O4 (half) | See cluster 5: no orchestrator at M2 to run unattended; research-luck outcome is not a demonstrable property (r1 AE). The known-answer motion half was accepted at M3. |
| R6 | `method_semantics_id` / `implementation_id` identifiers and a semantic-change review step | G1 (half) | Rename for a field the §2 bundle already has (interface version); the review step names no decider (G1's own "fact needed" 1). The duty split was accepted (cluster 10). |
| R7 | Ceiling `min(multiplier × declared, multiplier × tier_max)` | K3 (iii) | Redundant once the coherence refusal holds (declared ≤ tier max). |
| R8 | KEEP / KEEP_IN_SAMPLE / SURVIVED as `AlreadySettled` | K2 (part) | Mid-flight tickets; the owning branch's own Tier-2 launch would be blocked by its own ticket. Narrowed (cluster 13). |
| R9 | `tier_refused` PARKED blocker | L1 (part) | A parked branch is not funded, so the ladder that would mint the missing ticket never runs; the active-branch disposition was accepted (cluster 17). |
| R10 | `retracted` mark and REFUTED → PARKED `null_control_contradicted` transition | L2 (part) | The existing `Allowed`-when-retry-predicate-met path expresses the resolution without a status move on a REFUTED row (cluster 18). |
| R11 | Formalization-gate "readiness flag" until the comparator is qualified | G5 (part) | No code branches on it: before M1 no PROVEN derivation exists; after M1 the comparator is the gate (cluster 12). |
| R12 | GC roots must include claim statement nodes, evidence nodes, hypothesis objects, verdicts | D (stream) | Does not reproduce: §3 says only blobs are collectable; rows are never collected, and every blob an evidence node needs hangs off a recipe root through its attempt. Not integrated. |
| R13 | Split §2's skill-identity paragraph and §3's retention paragraph into numbered clauses | O framing (b) | Restructuring that moves text without adding information (rule 8) and a cross-citation risk; recorded as an operator question (a prose-only pass outside review). Touched sentences were written shorter. |

Rejected clusters: 13 (R5–R11 are partial rejections inside accepted clusters).

## 3. Flagged invariant attacks

- **G3:** re-scoping "refuted on the spot" to "refuted on that finite predicate" and a §4 reach
  sentence that exempts "an asymptotic claim [or] a different crossover claim" weakens the ladder
  (an immutable gate); the same attack as r1 AD, r2 R1 and r3 R5. Rejected, not integrated.

No seat proposed weakening §0, the gate layer's existence or immutability, the taxonomy, the
verifier, the no-go checklist or the honest baseline. Every accepted change adds an input, a
refusal, a node, a fixture or a binding; the one correction (cluster 1) restores the source
mechanism's orientation.

## 4. Factual corrections (each checked against the cited file)

1. The KEEP band's statistic is a gain / speedup factor — `briefs/frankensqlite.md:22`,
   `PROPOSALS.md:288-289`; plan-r3 §6:494-495 stated the inverse ratio. **Changed a mechanism**
   (the ladder's acceptance predicate orientation) ⇒ verdict cannot be STEADY.
2. M0 exemplar draws: 11–220 per the table at `grounding/pari-sage-toy-curve-backend.md:17-19`;
   the grounding's prose at `:21` says "20–220" and the plan quoted it. Wording.
3. At 10² trials control (j) is INCONCLUSIVE (lower bound ≈ 1.22 vs band ≈ 1.28); n ≳ 130 under
   independent arms (arithmetic re-done; agrees with O1 and r3 correction 7). Wording; M1 sizes.
4. `leanchecker --fresh` rejects neither `sorryAx` nor extra axioms —
   `grounding/lean-checker-protocol.md` §3 (already in the plan since r1 correction 11); the
   comparator's axiom check is `Axioms.lean:45` (§2 of the same file); `Lean.collectAxioms` plus a
   whitelist is the standalone form (`grounding/lean-statement-linters-vacuity.md` §4). O3's point
   is a producer pinned, not a new fact.
5. O2's contradiction reproduces: plan-r3 §2:77-78, 83-84 ("the tier gate refuses …") vs
   §5:425 ("four things and nothing else").
6. G1's ambiguity reproduces: plan-r3 §2:50-52 separates interface version from implementation
   revision; §3:100, §3:142 and §6:473 use one token `skill@version` for the recipe key, the
   hypothesis key and the dispatch record.
7. L6's reading of `BUDGET_EXHAUSTED` as a planned non-failing terminal state does not
   reproduce (plan-r3 §7:716-718: "no ticket", i.e. an incomplete hunt). The rename stands on the
   collision alone.
8. D's GC-roots concern does not reproduce (§3: only blobs are collectable). Not integrated.
9. Opus fact-check pass re-verified here on a sample: `exp(−π) ≈ 4.3 %`, `exp(−4π) ≈ 3.5×10⁻⁶`
   (Rayleigh, sd ≈ 0.52·mean); auditor bound ≈ 1379; 60-bit SE ≈ 16 % at m = 10. All hold.

Correction 1 changed a mechanism ⇒ verdict cannot be STEADY.

## 5. Seat reliability

- **GPT-5.6-terra:** complete; 5 numbered proposals with diffs, format respected. G1 accepted in
  part (MED, in the plan's vocabulary), G2 merged (MED), G3 rejected (fourth re-litigation,
  flagged), G4 accepted (LOW), G5 accepted in part (LOW). Its "facts needed" 1–4 are sound and
  appear below.
- **Grok-4.5:** complete; 7 proposals with diffs. K1 (MED), K2 partial (MED, narrowed), K3 partial
  (MED), K4 partial (MED), K5 merged (LOW); K6 rejected (re-litigation), K7 rejected (ceremony).
  Strongest on gate-binding holes again; its framing (b) on M3 optimization is met by K2's park.
- **GLM-5.2:** complete and in format for the first time — 6 numbered proposals with diffs. L1
  partial (LOW), L2 partial (LOW), L3 merged (MED), L4 accepted (MED), L5 rejected, L6 accepted
  (LOW) with its reading corrected. One over-severity (L1, L2 HIGH → LOW).
- **DeepSeek-v4-flash:** 44 KB reasoning stream of "Potential issue … Good.", no numbered
  proposals or diffs, truncated mid-sentence at line 132. Four findings recovered and accepted as
  LOW (withdrawn enum, non-disowned attempts, ladder verdict qualifier, refuted-claim floor); one
  does not reproduce (GC roots). Exceeded the format; counted toward consensus only where stated
  as a finding.
- **Opus grounded:** complete; fact-check pass, 7 proposals, framing, facts. O1 accepted (HIGH —
  the round's one structural correction, evidence verified at the cited brief line), O2–O3 (MED),
  O4 in part (MED), O5 merged (MED), O6–O7 (LOW). Every cited line re-verified here; its one
  loose spot is the "20–220" flag, which the grounding's own prose also states — the table
  governs. Its framing (b) on sentence length is recorded as an operator question, not integrated.

## 6. Open questions for the operator

1. Non-generic methods: the ladder counts group operations, so a method whose cost lives in field
   or polynomial arithmetic (every index-calculus-shaped approach) is INCONCLUSIVE at best
   until a counted implementation exists (§6). Should M1's gate-owned arithmetic object expose
   counted field arithmetic as its base unit so such methods can be laddered, or is the ladder
   deliberately generic-only with the BSGS floor as the universal check? (Synthesizer own view
   #5; not integrated without evidence.)
2. A prose-only pass splitting §2's skill-identity and §3's retention paragraphs into numbered
   clauses, no semantic change, outside the review rounds (Opus framing b).
3. Who the human is and the human-queue bound: before M4 statement review, `nogo_review`,
   null-control re-measurement, near-dup adjudication and expert sign-off all queue to one person
   (Opus c.iv, Grok c.5 — priority or starvation policy).
4. Tier boundary table values (the bundle object K3's refusal reads): set at M1 from the measured
   baselines, or pinned now? (Grok c.1.)
5. Whether an interface-version bump can be distinguished mechanically from an implementation
   revision (GPT c.1): the plan binds the hypothesis to the interface version and leaves a renamed
   method to the near-dup advisory and the Librarian.
6. Node volumes and audit cadence to size the per-cycle audit line (GPT c.2).
7. r1–r3 questions that stand: compiled baselines at M1 (now with n ≳ 130 per arm per rung);
   yank / salt authority; the orchestrator's OS user and host; statement-review reviewer identity
   and expiry; Linux host for the PROVEN gold tier; Tier-2 human-session knob; second
   implementation at M0; M4 checkpoint writer and write rate; M3 starvation bar; pruning P5–P7;
   the auditor's self-disagreement practice.

## 7. Validation

- **(a) Self-containment.** Most obscure M0 task: the tier gate's five-input predicate with the
  verification escrow and its release rule. Implementable as written: the inputs are enumerated
  (profile, budget meet, hypothesis key and method identity or statement hash, the revision's
  certificate / yank standing from the §2 records, the ticket of the tier's kind); the refusal
  conditions are listed, including the boundary-table check against the bundle object r3 placed
  there; the escrow is reserved at launch, spent on the §3 policy's first check (for M0's Tier-0
  exemplar, its re-run), released unspent on status ≠ OK or disown; `TierRefused` is a ledger
  record with a stated disposition. `justify` at M0 is likewise buildable: coverage direction
  pinned, verdict qualifier for `ladder_table`, refuted-version lattice violation, and the
  claim-statement-hash identity it names. The `nogo_review` node and the formal-statement-hash
  binding land at M1 with the gates that read them.
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism added
  this round: M0 — escrow release, `withdrawn` status, claim statement hash as the named
  identity, `justify` direction / verdict / refuted rule, fifth tier-gate input and
  boundary-table refusal (the gate exists at M0; the fixtures run at M1), yank-reach default;
  M1 — speedup-factor estimator and pinned "clears", trial-count derivation, fresh nonce,
  implementation-revision binding in dispatch record, table and ticket, per-rung reference rate
  and process-tree CPU, table replay grade and repro record, fixture (a) pin, `nogo_review`,
  gate-owned axiom computation, formal-statement-hash binding, `INCOMPLETE`; M2 —
  `AlreadySettled` park, null-control resolution, revision-only `Blocked` fixture; M3 —
  force-park / no-REFUTED / revival / crash-resume fixtures and the known-answer motion bar;
  M4 — audit line reconciliation. No orphan: the consumer of each is a gate or fixture that
  branches on it (tier gate, preflight, clock check, `justify`, Solution naming, auditor, the
  milestone gate).
- **(c) Justification sampling.** Speedup-factor estimator (why: a real advance is above 1 and
  the band is the source's gain band); fifth tier-gate input (why: §2's refusals need an
  enforcement point at launch); `AlreadySettled` (why: a settled success re-funded unchanged is
  the cheapest loop a gate-outcome reward can find); yank-reach default (why: a self-narrowed yank
  fails open on the unnamed slice); claim vs formal statement hash (why: two hashes under one
  name are a join no implementer can write). All five carry a why; so do the escrow release, the
  `nogo_review` node, the 60-bit reference rate and the coherence refusal.
- **(d) Steady-state diff.** +164 lines (1117 → 1281), 326 diff lines before rewrapping.
  Structural in one place — the ladder's acceptance predicate, re-oriented to the source's
  speedup factor (cluster 1) — and mechanism-level elsewhere: §5 (fifth input, revision
  binding, coherence refusal, escrow lifecycle, `TierRefused` disposition), §4 (`AlreadySettled`,
  null-control resolution, two named hashes, `withdrawn`), §7 (gate-owned axiom set, hash binds
  and the comparator decides, `justify` direction and refuted floor, `INCOMPLETE`), §8
  (`nogo_review`), §6 (reference rate at every rung, fresh nonce, table grade, fixture pins),
  §2/§3 (interface version vs implementation revision, yank-reach default), §13 (fixtures and the
  M3 motion bar). Section numbering, §0, §8's three items, §9, §14 and §16's invariant list
  unchanged. Less structural than r3 (which changed the ladder's execution contract) and far less
  than r1–r2.

## 8. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Expected residual scope for round 5: coherence of the tier gate's new
inputs (revision binding, coherence refusal, escrow release) with §2's identity bundle and §3's
keys, and of `AlreadySettled` and `nogo_review` with the M2/M3 done-whens — wording-level unless
a seat finds a new contradiction.
