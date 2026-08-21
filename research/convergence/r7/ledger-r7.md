# Ledger — guard round 7

Plan reviewed: `research/convergence/plan-r6.md` (v3, 1592 lines). Plan produced:
`research/convergence/plan-r7.md` (1659 lines; 109 added lines, +67 net after rewrapping).
Synthesizer own view (written before any seat was opened): `research/convergence/r7/own-view-r7.md`.
Seats: GPT-5.6-sol (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-pro (D), Anthropic Fable grounded
(F); synthesizer own view (S). Prior ledgers read: r4, r5 and r6 in full; r1–r3 rejected lists
and flagged attacks. Guard-round bar applied: accept only demonstrable defects (a contradiction
quoted from the plan text, a gaming path the text does not close, a factual error against the
evidence, a ceremony artifact failing the boundary test); never polish; a ceremony cut or
re-justification does not by itself break STEADY; a HIGH structural change does.

Verdict: **NEEDS-ANOTHER-ROUND** — two accepted clusters are MED (the cumulative edge's operand
is narrowed to a worker's fresh launches after it was found to refuse the re-ladder §3, §5 and §6
require; `justify`'s maximum class gains the producer's self-test standing as an input after the
§2 `author_supplied` cap was found to have no consumer), and both are plan-internal contradictions
whose resolution changes what a gate reads. No HIGH; no section renumbered; §0, §8's three items,
§9, §14 and §16's invariant list untouched; twelve further clusters LOW; one ceremony
re-justification (`shape_departure`), no cut.

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | The Tier-1 cumulative edge refuses the second ladder run the plan itself requires on one key — after INCONCLUSIVE ("a rung re-run after INCONCLUSIVE sees fresh instances"), for a new revision ("a new implementation revision re-ladders before it spends"), and as the re-measurement a `measured` entry's retry predicate names — because the ≤ 50-bit rungs are admitted on the Tier-1 ticket and charged to the key, the edge is set "above the ladder's own cost on one key" (1.1× satisfies the text), and the refused run is the one that mints the ticket that lifts the edge | MED | F2; L (ladder plus hunt on one key, reasoning stream) | §5, §13 M1 | ACCEPT. The edge ranges over the charge of a worker's *fresh* launches; gate-owned launches (ladder rungs, null-control and retry-predicate re-measurements, the auditor's draws) and re-runs of recorded recipes (the Skeptic's, the reproducibility gate's) are charged to the key and never compared against the edge — their counts, arms and patience ceilings are ladder-plan fields and a re-run of a recorded recipe is no new work, so neither is a launch a worker can shard; M1 sets the Tier-1 edge as a multiple of the ladder's measured per-run cost beside the trial count it derives; why extended (the refused run mints the lifting ticket); M1 fixture: the edge refuses the crossing worker launch while a second ladder run on the same key is admitted. F2's "edge from control (j)'s measured pre-ladder Tier-1 spend" not taken (the M1 planted corpus measures no worker-side spend). Evidence: plan-r6 §5:562-567 (the charge and edge), §5:509-514 (rungs on the Tier-1 ticket), §6:692-695 (fresh instances after INCONCLUSIVE), §5:616-618 (new revision re-ladders), §4:346-351 (retry predicate is a re-measurement). Re-judged MED: the operand of a tier-gate refusal changes; the sharding closure of r6 cluster 5 is unchanged. |
| 2 | §2 says an `author_supplied`-only corpus "caps the skill's results at CONJECTURE" and a measurement outside the cross-check's independent range "is capped accordingly", while §7 derives the tag with "the maximum class is a function of `kind`" and nothing else reads `corpus_origin`; a worker-authored deterministic skill with a self-supplied corpus re-runs bit-for-bit and fixture (m) carries it to STRONG-EMPIRICAL | MED | F3 | §7, §2, §13 M1 (m) | ACCEPT. The maximum class is a function of `kind` and — where the producer is a certified skill rather than a gate-bundle object or a gate run — of that revision's self-test standing: no STRONG-EMPIRICAL basis covering the attempt's inputs (every origin `author_supplied`, no randomized-postcondition arm, no cross-check whose independent range contains them) caps the node at CONJECTURE; why (a bit-identical re-run of an author-tuned skill proves determinism, not correctness); §2 names `justify` as the cap's consumer; fixture (m) gains the negative; M1 Adds names the producer-standing ceiling. A ladder table is unaffected (its producer is the gate run and `xP == Q` on gate instances is the gate's own postcondition). Evidence: plan-r6 §2:62-66, :73-74, §7:938-939, §13:1300 (the exemplar's origins), :1357-1360 (fixture m); r1 ledger S (O6a) introduced the cap in §2 and named no §7 consumer. Re-judged MED: `justify` gains an input; the analog of r4 cluster 3 (§2's refusals given an enforcement point in §5). |
| 3 | One ladder step states the tested method's allow-list three ways, two of them incompatible: "names no other arithmetic backend" (r6 cluster 6) versus "no process spawn beyond the backends its hypothesis object declares" and "a method that needs an uncounted backend declares it in its hypothesis object, and its rungs are INCONCLUSIVE at best" | LOW | F1 | §6 (3), §13 M1 | ACCEPT (F1's formulation). The allow-list is a gate-bundle template instantiated per dispatch and named in the dispatch record (the §4 pattern every worker allow-list already follows) naming no arithmetic backend but the gate-owned counted object and the uncounted backends the hypothesis object declares (whose rungs are INCONCLUSIVE at best), no network egress and no writable path but the scratch path; the uncounted-backend sentence cross-references the admission; M1 Adds reads "no undeclared arithmetic backend". Evidence: plan-r6 §6:805-806 vs :811-812 vs :834-836 (internal). Re-judged LOW: the reading two of the three clauses and the INCONCLUSIVE ceiling already state; the remote-offload closure of r6 stands (an undeclared backend, socket or path is still the planted fixture); no gate input changes. |
| 4 | `AlreadySettled` keys its success condition on "a promoted one whose claim statement stands at PROVEN or STRONG-EMPIRICAL" and clears "when the holding branch withdraws", while withdrawal is the worker's act that "erases no gate outcome already recorded against the statement hash" and no line says who writes `promoted` — a worker that withdraws once its KEEP and tag have landed frees the key for the re-fund loop the mechanism exists to stop | LOW | K1 (HIGH claimed) | §4, §13 M2 | ACCEPT-PARTIAL. The condition is keyed on the statement's standing tag whatever the status of the branch that earned it (promoted, or withdrawn afterwards); the blocker clears on a superseding object, when the statement moves to `refuted`, or on withdrawal only while the statement stands below STRONG-EMPIRICAL; `promoted` is written by the gate layer when `justify` first derives STRONG-EMPIRICAL or PROVEN for the branch's claim statement and by no other path (so the status follows the tag); M2 fixture gains the withdrawn-after-tag holder. K1's full rewrite — every admissible KEEP / KEEP_IN_SAMPLE table as settled, clearing only when every KEEP is displaced by REJECT — not adopted (r4 R8 / r5 R10: mid-flight tickets as settled block the owner's own launch). Evidence: plan-r6 §4:324-334, §4:385-388, §4:278 (status enum, no writer). Re-judged LOW: the preflight already reads the statement's tag; a branch-status qualifier is dropped and a writer named; no new input. |
| 5 | "An item closes only by a human-path record (§4) or by its blocker clearing" while `leaked`, `clock_inconclusive`, `shape_departure`, `cost_drift` and `audit_shortfall` park no branch and match no human-path record type, so they never close and queue depth and age — drift-monitor inputs — degrade monotonically | LOW | F4, S2 (r6 open question 5) | §10, §4, §13 M1 | ACCEPT. An item holding no blocker closes when the branch, rung or audit cycle it names reaches a terminal status, re-runs or next meets its target, or by an attributed `acknowledgment` record through the human path naming the item; it closes by no other path (so depth and age cannot be edited down); §4's human-path list gains the acknowledgment; M1 Adds names the closing rule. Evidence: plan-r6 §10:1165-1166, §4:483-485, §4:382-384 (`leaked` branch stays active). |
| 6 | The gate bundle — content-addressed, "whose hash is pinned at deployment" — lists "the waiver registry", while the human path makes a waiver an attestation-file record "issued only by a human" at runtime that "the waiver check" reads as a substrate row; a runtime waiver cannot live in a pinned bundle without a re-pin | LOW | S1 | §4 | ACCEPT (wording). The bundle holds the waivable-check set (which operational checks a waiver may let continue as `AuditOnly`); a waiver itself is a human-path record, never a pinned field. Evidence: plan-r6 §4:454 vs §4:483-490; `PROPOSALS.md:237,265` (C5's "waiver registry" is serialized config in the source; r5 cluster 1 made Cairn's waivers attestation records). |
| 7 | The clock-tolerance inequality "tolerance × ratio must stay below `2·radius` — a plan failing that inequality refuses to start" names a plan-load check against a quantity (`radius`) that is the A/A arm's measured CI radius, known only after the rung runs | LOW | S3 | §6 (3) | ACCEPT. Checked at plan load against the design radius the plan's trial count targets (a ladder-plan field M1 records with the count), and again at every rung against the measured A/A radius, the tolerance applied there being the smaller of the plan's value and `2·radius/ratio` — a tighter band tightens the clock rather than opening a gap beneath it. Evidence: plan-r6 §6:824-828 vs §6:709-712 (radius is per rung, measured). Re-judged LOW: the operand is pinned; the per-rung minimum binds only where the measured radius falls below half of tolerance × ratio; no new input (radius and ratio are already recorded). |
| 8 | "Charges every non-refused launch's production cost" names no operand; a worker that understates every declaration by the multiplier and finishes inside the 4× ceiling carries a key past the cumulative edge by up to 4× before any refusal | LOW | G2 (partial; HIGH claimed) | §5 | ACCEPT-PARTIAL. The charge is the declared cost at launch, reconciled to the execution receipt's measured cost when the attempt closes, so an understated declaration misstates the key's charge by no more than the attempt in flight. G2's continuous termination at the edge ("an attempt may not finish OK after actual cumulative spend has crossed its ticket's edge") not adopted (R4). Evidence: plan-r6 §5:562-563, §5:585-589 (the per-launch bound r5 #18 stated). Re-judged LOW: pins an operand against a receipt the ceiling already reads; the per-launch bound stands. |
| 9 | A ladder KEEP on an executable labeled as a novel mechanism earns STRONG-EMPIRICAL for "the claim attributing the measured performance to the fictitious mechanism" | LOW | G1 (partial; HIGH claimed) | §7 | ACCEPT-PARTIAL (one clause where the kind map is read): the class a table justifies is about the typed statement — the method identity the table names, its cost model, the population measured — and never about why the executable is fast; a mechanism or novelty attribution in the informal statement is the Librarian's and the human's question (§10), not a calibration class. G1's kind-map rewrite ("`justify` rejects a ladder table whose target statement asserts more than the executable behavior") not adopted (R5): coverage is already a typed comparison and the informal statement is not a `justify` input. Evidence: plan-r6 §6:661-665 ("evidence for the model on the sizes measured"), §7:938-942 (typed coverage, "never a text match"). |
| 10 | M2's title claims "formalizer + statement-level review" while M1 builds the formalization gate, the statement pre-filters, the `review_verdict` node and the PROVEN derivation | LOW | G4 (MED claimed) | §13 M2 | ACCEPT (wording): M2 adds the Formalizer worker and the statement-review workflow; the gate and pre-filters it submits to are M1's. Evidence: plan-r6 §13:1426 vs :1412-1420; r3 #3 / r5 #23 placed the workflow at M2. |
| 11 | Submission egress admits "a recovered `x` for the target or for any instance" on "the instance the claim statement node names": a worker opens its own claim node on a self-chosen `(P′, Q′ = x′P)` and mints true submissions by volume — §9's forbidden state | LOW | F (duty 3) | §10 | ACCEPT. A submission is the passing node only where the instance is one the human path registered (the target, a problem-queue entry) or the gate's instance-maker drew; a passing node on a worker-chosen instance is rendered as a finding about that instance, never as a submission. Evidence: plan-r6 §10:1185-1188; `HANDOFF.md:95`. |
| 12 | The tier-gate refusal list ("refused … when the declared tier is lower than the tier the bundle's boundary table assigns its production cost") omits the ≤ 50-bit rung exception stated in the same section ("admitted on the Tier-1 ticket whatever tier the boundary table would assign") | LOW | S4 | §5 | ACCEPT (cross-reference in the refusal list). Evidence: plan-r6 §5:623-624 vs §5:509-514. |
| 13 | A `TierRefused` whose absent ticket is a human verdict (a Tier-2 formalization run without its `review_verdict`, a Tier-3 request without its sign-off) has a disposition of "fund the tier-below work that would produce the ticket or park", and no tier-below work produces a human verdict; M2's workflow routes only *green* artifacts to the queue | LOW | S (lesser) | §5 | ACCEPT: the refusal enqueues the human-queue item of that class for the statement hash. Evidence: plan-r6 §5:649-651, §5:636-639, §13:1447-1449. |
| 14 | Wording: §3 "entropy commitment for that rung" while the nonce is drawn per ladder run (§6 (1)); §5 "an unspent reservation outlives its branch by at most that cycle" holds only from M4 | LOW | S, F (wording note) | §3, §5 | ACCEPT (wording): "for that run"; "from M4 (before the auditor exists it stands until `justify` draws it)". Evidence: plan-r6 §3:184 vs §6:692-695; §5:550-551. |

Accepted clusters: 14 (three partial). Gate-bundle contents re-enumerated only for the
waivable-check set; no component added.

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | Mandatory `supersedes_interface` edge within a registered skill family, followed by the preflight; narrow §3's "two approaches are secretly the same" | G3 | Re-litigates r6 R4 (`method_successor` edge) and r4 #10 / R6 with no new evidence; r4 open question 5 stands; the exposure is a Tier-1 re-refutation, not a tag. The framing remark does not reproduce as a defect: the same §3 bullet already bounds the sentence ("free-text fields are excluded, so the key is about structure — paraphrase is the near-duplicate advisory's job"). |
| R2 | Cut tag history as ceremony | G5 | Re-litigates r6 R7: the write path branches on it (a transition without an evidence pointer is refused), the disagreement protocol reads the pre-dispute level, the renderer prints the derived tag; not an audit-only artifact. |
| R3 | INCONCLUSIVE must not displace KEEP for ticket selection | K2 | Re-litigates r6 R2 and r5 #5 with no new evidence; the displacement is fail-closed by design, a worker cannot schedule a ladder run, and the cost of a 60-bit INCONCLUSIVE is a Tier-1 re-ladder — which cluster 1 keeps admissible. |
| R4 | Continuous charging of actual cost with termination at the cumulative edge; "an attempt may not finish OK after actual cumulative spend has crossed its ticket's edge" | G2 (half) | Terminates honest jobs near the edge; the multiplier ceiling is the per-run enforcement (r5 #18) and the reconciliation of cluster 8 closes the stated residual to one launch's overrun. |
| R5 | Rewrite the kind map so `justify` "rejects a ladder table whose target statement asserts more than the executable behavior the ladder observed" | G1 (half) | Coverage is already a typed comparison of population and assumptions against the statement's scope ("never a text match"); the informal statement is not a `justify` input; one clause naming what the class certifies was accepted (cluster 9). |
| R6 | Every admissible KEEP / KEEP_IN_SAMPLE table or standing tag as `AlreadySettled`, clearing only when every KEEP ticket is displaced by a measured REJECT | K1 (half) | Re-litigates r4 R8 / r5 R10 (mid-flight tickets as settled block the owning branch's own Tier-2 launch); the withdrawal path is closed by keying the condition on the statement's tag (cluster 4). |
| R7 | "M1 sets the Tier-1 edge from control (j)'s measured pre-ladder Tier-1 spend" | F2 (clause) | The M1 planted corpus measures no worker-side spend; the edge is set as a multiple of the ladder's measured per-run cost (cluster 1). |
| R8 | Sharding a Tier-2 computation across minted hypothesis keys (jittered regions on one method, each under its own Tier-1 edge) | S5 (own view) | No evidenced constant for a per-method or per-instance edge, and a per-`(P, Q)` charge is defeated by `Q + kP`; the path mints no tag or ticket (no KEEP ⇒ CONJECTURE ceiling) and is bounded by the orchestrator's total grant and the M3 junk-family bar; recorded as open question 2 and in the gaming table. |
| R9 | (no proposals) | L, D | GLM's stream considered "INCONCLUSIVE displaces KEEP" and dismissed it itself, and raised the ladder-plus-hunt charge on one key (folded into cluster 1); DeepSeek's stream found no defect and ended mid-walk. Neither counted toward a cluster except as stated. |

Rejected clusters: 9 (R4–R7 are partial rejections inside accepted clusters).

## 3. Ceremony audit (artifact → running code that branches on it)

| Artifact | Consumer | Result |
|---|---|---|
| Golden certificate, self-test floor, yank record, `corpus_origin` | Tier gate refusal (uncertified/yanked), `disowned` propagation, cache serve; `corpus_origin` → `justify`'s producer-standing ceiling | holds; **`corpus_origin` re-justified** (consumer named: cluster 2) |
| Recipe key / attempt rows / cache bits / salt | Cache serve, reproducibility gate, `justify` absence, preflight | holds |
| Execution receipt | Budget ceiling, clock and memory measurements, provenance check, the reconciled key charge (cluster 8) | holds |
| Witness certificate / replay grade | Witness verifier, reproducibility gate, tier admissibility | holds |
| Hash-chained log + checkpoint | Startup and pre-promotion verification | holds |
| Ledger entries + preflight answers | Branch fund/open, retry predicates, §11 map; `AlreadySettled` reads the statement's tag | holds |
| Gate plan, bundle pin, planted pairs, waivable-check set | Every gate run (fail closed), the waiver check (reads attestation rows against the set) | holds; "waiver registry" renamed to what the bundle can hold |
| Attestation file / `review_verdict` / `nogo_review` / acknowledgment | `justify` PROVEN, tier gate, waiver check, preflight; queue-item close | holds; acknowledgment's consumer is the close rule (cluster 5) |
| Ladder result table (incl. shape diagnostic column) | Tier ticket, `justify`, ledger kind; shape column → `shape_departure` item | holds; **`shape_departure` re-justified**: defect class (a truncated or bimodal distribution a mean check cannot see — the short-walk bias the source protocol sorts its walks to avoid, `briefs/adjacent-distributed-collision-search.md:16,22`) and retirement (dropped if by M3 no item preceded a REJECT or yank the verdict predicates missed; the column stays as table data) |
| Hunt record | Tier-2 conjecture ticket, ledger KILLED | holds |
| Tag history | Write-path transition rule, disagreement protocol, renderer, `promoted` status | holds (R2) |
| Dispatch record (incl. the instantiated ladder allow-list) | Ladder identity refusal, dispatch canary, allow-list visibility | holds |
| `TierRefused`, `Leaked` | Orchestrator tick path; `Leaked` → `leaked` item; a human-verdict refusal → queue item of that class | holds |
| Human queue items | Gate block on absent human input; orchestrator reads depth/age; close rule | holds; close rule for blocker-less classes added |
| Audit record | `audit_shortfall` item; committed seed; M4 done-when | holds |
| P4 alarms | `cost_drift` item + tick input; retirement stated | holds |
| Negative-results map, lemma library, submission class | Egress renderer and its refusal predicate (instance provenance, cluster 11) | holds |
| Near-dup SimHash, panel ranks | Routing only, never status | holds by design |

Nothing cut. Names promising more than delivered, corrected: "waiver registry" (a pinned bundle
cannot hold runtime waivers), "closes only by a human-path record" (five classes could not),
"charges … production cost" (operand named), "a plan failing that inequality refuses to start"
(operand named).

## 4. Gate-gaming table (gate · path a worker could take · closing line in plan-r7)

| Gate | Gaming path | Closing line |
|---|---|---|
| Submission verifier (i) | Verify on a self-chosen `(P, Q)` attached to prose about the target | already closed (r6): "takes the curve, `n`, `P` and `Q` from the claim statement node … never from the submitter, who supplies `x` alone"; refused before spawn |
| Submission verifier (ii) | Open a claim node on a self-chosen instance and submit the `x` already held, by volume | §10: "only where that instance is one the human path registered … or the gate's instance-maker drew: a passing node on an instance the worker chose is rendered as a finding about that instance, never as a submission" |
| Ladder (i) | Offload to an uncounted backend or remote service | §6 (3): the allow-list names "no arithmetic backend but the gate-owned counted object and the uncounted backends the hypothesis object declares (whose rungs are INCONCLUSIVE at best)", no network egress; planted socket fixture; wall-clock > CPU ⇒ INCONCLUSIVE |
| Ladder (ii) | Own faster coordinate arithmetic plus dummy counted calls at a tight A/A radius | §6 (3): the tolerance applied at a rung is "the smaller of the plan's value and `2·radius/ratio`", checked at load against the design radius and again at every rung |
| Ladder (iii) | Relabel a known method as a novel mechanism and collect STRONG-EMPIRICAL for the mechanism | §7: the class "is about the typed statement … and never about why the executable is fast"; once the relabeled method is a shipped baseline the claim is INCONCLUSIVE against it; novelty is §10's question |
| Ladder (iv) | Seen instances, self-reported counts, understated models, in-RSS table, `xP ≠ Q` | already closed (r6) |
| Formalization gate | Weak Challenge, `sorryAx`, shadowed constant, self-reported axioms | already closed: "the Formalizer never creates or edits Challenge text"; gate-owned `collectAxioms`; closure comparison; PROVEN needs an `approve` verdict through the human path |
| Reproducibility gate | Author a skill with a self-supplied corpus, compute a deterministic "fact", re-run bit-for-bit | §7: a producer "whose self-test record carries no STRONG-EMPIRICAL basis covering the attempt's inputs … caps the node at CONJECTURE"; fixture (m) negative |
| Ledger preflight (i) | Withdraw the branch after its KEEP lands and re-open the key | §4: `AlreadySettled` holds "whatever the status of the branch that earned it (promoted, or withdrawn afterwards …)"; clears on withdrawal only "while its claim statement stands below STRONG-EMPIRICAL" |
| Ledger preflight (ii) | Re-version the interface to mint a fresh method identity | open (r4 Q5, r6 R4): the exposure is a Tier-1 re-refutation; the near-dup advisory and Librarian route it |
| Tier gate (i) | Shard Tier-2 work into Tier-1 launches on one key | §5 cumulative edge over a worker's fresh launches (gate-owned launches and re-runs exempt: "neither is a launch a worker can shard") |
| Tier gate (ii) | Understate every declaration by the multiplier and stay inside the per-launch ceiling | §5: the charge is "reconciled to the execution receipt's measured cost when the attempt closes, so an understated declaration misstates the key's charge by no more than the attempt in flight" |
| Tier gate (iii) | Shard across minted keys (jittered regions on one method) | open in compute only: no KEEP ⇒ CONJECTURE ceiling and no ticket; bounded by the orchestrator's total grant and the M3 junk-family bar (open question 2) |
| Tier gate (iv) | Block a human-verdict ticket forever by never asking | §5: a refusal for an absent human verdict "enqueues the human-queue item of that class" |

## 5. Flagged invariant attacks

None. No seat proposed weakening §0, the gate layer's existence or immutability, the taxonomy,
the ladder's verdict rule, the verifier, the no-go checklist or the honest baseline. G1 tightens
what STRONG-EMPIRICAL certifies; G5 and K2 were judged on prior REJECTs, not as attacks. Every
accepted change adds a consumer, a qualifier, a closing rule, an operand or a fixture; none
removes a gate input.

## 6. Factual corrections (each checked)

1. §6 (3) states the ladder-tested allow-list three ways, two incompatible (plan-r6 §6:805-806
   vs :811-812, :834-836). Wording reconciliation toward the reading two clauses state; no
   mechanism changed.
2. The cumulative edge (§5:562-567) refuses the re-ladder §6:692-695, §5:616-618 and §4:346-351
   require. **Changed a mechanism** (the edge's operand) — cluster 1, MED.
3. §2's `author_supplied` cap (§2:62-66) has no consumer in §7's derivation (§7:938-939).
   **Changed a mechanism** (`justify`'s inputs) — cluster 2, MED.
4. "The waiver registry" as a pinned bundle field (§4:454) vs waivers as runtime human-path
   records (§4:483-490). Wording.
5. "Entropy commitment for that rung" (§3:184) vs the nonce drawn per run (§6:692-695). Wording.
6. Seat facts that reproduce (re-verified here on a sample): F Part 0 —
   `briefs/adjacent-distributed-collision-search.md:16` (sd ≈ 0.5·mean; sorted DPs to avoid
   bias), `:40-41` (`discrete_log_rho` checks `power(base,res)==a` L807-809), `:51-52` (1.25√n,
   0.886√n, BSGS ≈ 1.5√n, 1.35G ops at 60 bits); `grounding/lean-checker-protocol.md:19-20`
   (landrun Linux-only, fake-landrun unsandboxed), `:40-41` (`--fresh` 32.3 s; `sorry` passes
   `lake build`), `:56` (gold tier on Linux); `grounding/pari-sage-toy-curve-backend.md:16-24`
   (tries 11–220, 60-bit stack overflow, 75 ms SEA), `:29-33` (verifier calls, F₅ curve of order
   7). F's "could not verify WAL / busy timeout" is consistent with the plan, which states them as
   facts M0 grounds (§3, §13); `grounding/dbos-…md:19` carries no WAL pragma. No factual error
   in the plan against the evidence.
7. G2's arithmetic (3.9× inside a 4× ceiling, repeated per launch) reproduces as a bound on the
   declared charge; the fix is the reconciliation (cluster 8), not termination.
8. G1's quoted "cannot see a method's algorithmic table" is the memory clause (§6:745-747), not
   a statement about mechanism attribution; the inferred limit is real and already the design
   (§6:661-665); one clause names it (cluster 9).
9. K1's path reproduces as text only because `promoted`'s writer is unnamed (§4:278); cluster 4
   closes it on both the status and the tag side.
10. `PROPOSALS.md:237,265` — C5's "waiver registry" is the source's serialized-config waiver
    flag; the bundle-held form after r5 cluster 1 is the waivable-check set.

Corrections 2 and 3 changed mechanisms ⇒ verdict cannot be STEADY.

## 7. Seat reliability

- **GPT-5.6-sol:** complete; in format; 5 proposals with diffs under the word cap, a ceremony
  table and a gaming table. G1 partial (LOW; HIGH claimed), G2 partial (LOW; HIGH claimed), G3
  rejected (re-litigation, HIGH claimed), G4 accepted (LOW; MED claimed), G5 rejected
  (re-litigation). Over-severity on three of five; its gaming-table closures for the verifier,
  formalization and reproducibility gates are accurate; its "facts needed" (skill-family
  registry, declared vs measured charge, extensional vs mechanism claims) are answered by R1,
  cluster 8 and cluster 9.
- **Grok-4.5:** complete; in format; 2 proposals with diffs plus a coherence walk, a ceremony
  table and a gaming table. K1 partial (LOW; HIGH claimed — the withdrawal path is real, the
  rewrite re-litigates r4 R8), K2 rejected (third re-litigation). Its coherence walk ("holds")
  and ceremony table ("no cut required") are accurate; its "fact needed" (who writes
  `promoted`) was the real gap and is answered.
- **GLM-5.2:** 42 KB reasoning stream ("Let me check …"), no numbered proposals, no verdict,
  ended mid-walk at the cumulative-edge question; one candidate (ladder plus hunt charged to one
  key) folded into cluster 1. Exceeded the format for the seventh round.
- **DeepSeek-v4-pro:** 44 KB reasoning stream, no numbered proposals, no verdict, ended
  mid-walk; found no defect. Exceeded the format for the seventh round.
- **Fable grounded:** complete; Part 0 fact pass (re-verified on a sample, holds), four numbered
  defects, duties 2 and 3 answered gate by gate, verdict and framing. F1 accepted (LOW; MED
  claimed), F2 accepted (MED, one clause replaced), F3 accepted (MED), F4 accepted (LOW); its
  duty-2 `shape_departure` re-justification and duty-3 submission residue accepted (LOW). The
  strongest seat again; its framing — build M0 after these clauses — is recorded below.

## 8. Open questions for the operator

1. The value of the Tier-1 cumulative edge as a multiple of the ladder's per-run cost (the plan
   now says M1 sets and records it; the multiple is an operator choice) and the unit the charge
   is kept in (core-seconds of CPU from the receipt is the implied unit).
2. Sharding across minted hypothesis keys (jittered regions on one method) stays open in compute:
   should the boundary table also carry a per-method-identity edge summed over keys holding no
   ticket above Tier 1, at the cost of throttling honest parallel exploration of one method?
   (R8; no evidenced constant.)
3. Whether a human-queue `acknowledgment` should also be able to close a blocker-holding item's
   *escalation* (the blocker stays) — the plan lets it close blocker-less items only.
4. Which instances count as "registered through the human path" for the submission class before
   the problem queue exists at M4 (the target alone, presumably).
5. The design radius the ladder plan targets (cluster 7): set from the n ≳ 130 derivation at M1
   or from the measured paired variance; it decides the clock tolerance the plan can carry.
6. r6 questions that stand: ticket validity across a bundle change (r6 Q1); the fastest
   implementation M1 measures the counted object against (r6 Q3); the funding line for
   human-enqueued re-measurements before M4 (r6 Q4); interface-version laundering (r4 Q5) and
   the native-skill sandbox contract beyond the ladder (r5 Q2); dispatch request-byte
   observability; budget-enforcement primitive; human review throughput; yank/salt authority;
   two OS users and host; Linux host for the gold tier; Tier-2 human-session knob; M4
   checkpoint writer; tier boundary values.
7. F's framing, unchanged from r6: after these clauses the plan is converged on mechanisms and
   §13's own rule applies — build M0; a running 40-bit slice will reveal more than an eighth
   round will. The verdict below follows the rules; the operator may prefer the framing.

## 9. Validation

- **(a) Self-containment.** Most obscure M0 task: `justify`'s producer-standing ceiling
  (cluster 2) as it reaches M0's synthetic fixtures. Implementable as written: the evidence node
  already carries the producer identity (the §2 identity bundle hash or the gate-run record);
  the lookup is from that hash to the revision's self-test record (a substrate node since M0's
  schema: corpus origins per case, postcondition arm, cross-check axis and range); the rule is
  a three-way test (origins all `author_supplied`, no postcondition arm, no covering cross-check)
  on a node whose producer is a certified skill, bypassed for a gate-bundle object or gate run;
  the ceiling is CONJECTURE; M0's synthetic `ladder_table` (producer: gate run) is unaffected
  and fixture (m) at M1 carries the positive and the negative. The other M0-visible change, the
  `promoted` writer, is one rule at the derivation. At M1 the cumulative edge is a per-key sum
  over launches whose dispatcher is a worker, compared with a bundle column; the reconciliation
  reads the receipt's CPU seconds at attempt close; the allow-list template is the per-dispatch
  instantiation every worker allow-list already has; the clock minimum is two numbers already in
  the table.
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism
  added this round: M0 — `promoted` writer (the derivation exists at M0), the waivable-check set
  (bundle schema), the `acknowledgment` record (the human path exists at M0); M1 — edge scope
  and reconciliation with the worker-launch fixture and the second-ladder admission, the
  producer-standing ceiling with fixture (m)'s negative, the allow-list template, the clock
  design radius and per-rung minimum, the human queue's closing rule, the human-verdict
  `TierRefused` enqueue (the human queue object lands at M1); M2 — the withdrawn-after-tag
  `AlreadySettled` fixture; M4 — the submission instance-provenance clause in the renderer's
  refusal predicate. No orphan: each has a consumer that branches on it (the tier gate,
  `justify`, the preflight, the ladder verdict and clock, the queue close path, the renderer,
  the milestone gate).
- **(c) Justification sampling.** Edge scope (why: gate-owned launches cannot be sharded, and
  an edge that metered them refuses the run that mints the lifting ticket); producer-standing
  ceiling (why: a bit-identical re-run of an author-tuned skill proves determinism, not
  correctness); `AlreadySettled` on the tag (why: a withdrawal erases no gate outcome, so a
  worker that withdraws after its KEEP frees no key); queue close rule (why: an item closing by
  no other path keeps depth and age un-editable); submission provenance (why: a worker that
  mints `(P, x·P)` pairs can mint true submissions by volume, §9's forbidden state). All five
  carry a why; so do the clock minimum (a tighter band tightens the clock rather than opening a
  gap), the reconciliation (the misstatement is bounded to the attempt in flight), the
  `shape_departure` defect class and the `promoted` writer.
- **(d) Steady-state diff.** +67 net lines (1592 → 1659), 109 added lines. No structural
  change: no component added, no build order moved, no section renumbered, §0, §8's three
  items, §9, §14 and §16's invariant list unchanged. Mechanism-level in two places — §5 (the
  edge's operand and the charge's reconciliation) and §7 (`justify`'s producer-standing input)
  — and wording, cross-reference, closing-rule and fixture level elsewhere (§2, §3, §4, §6,
  §10, §13). Smaller than r6 (+119 lines, seven MED) and r5 (a HIGH); the smallest diff since
  r1, and the first round in which every accepted change reconciles text the plan already
  carried rather than adding a gate input the plan lacked.

## 10. Verdict and residual scope

**NEEDS-ANOTHER-ROUND** — clusters 1 and 2 are MED (a tier-gate operand and a `justify` input
changed), and factual corrections 2 and 3 changed those mechanisms; the rule admits no STEADY
above LOW. Expected residual scope for round 8: coherence of the narrowed cumulative edge with
the escrow accounting and the allocation surrogate's cost denominator, and of `justify`'s
producer-standing ceiling with the `Verifiable` owner rule and the ladder table's gate-run
producer — wording-level unless a seat finds a new gaming path; the operator may prefer F's
framing (start M0) to an eighth round, since nothing this round added a component or moved the
build order.
