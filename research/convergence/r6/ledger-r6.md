# Ledger — guard round 6

Plan reviewed: `research/convergence/plan-r5.md` (v3, 1473 lines). Plan produced:
`research/convergence/plan-r6.md` (1592 lines; 235 diff lines, +119 net). Synthesizer own view
(written before any seat was opened): `research/convergence/r6/own-view-r6.md`. Seats:
GPT-5.6-sol (G), Grok-4.5 (K), GLM-5.2 (L), DeepSeek-v4-pro (D), Anthropic Fable grounded (F);
synthesizer own view (S). Prior ledgers read: r4 and r5 in full, r1–r3 rejected lists, flagged
attacks and checkpoint history. Guard-round bar applied: accept only demonstrable defects
(contradiction quoted, gaming path the text does not close, factual error against evidence,
ceremony artifact failing the boundary test); never polish.

Verdict: **NEEDS-ANOTHER-ROUND** — seven accepted clusters are MED (six gate-gaming closures
and two section-level contradictions, one of them a ticket-lattice deadlock), and one factual
correction changed a mechanism (the ladder's memory axis was "measured by the harness as peak
algorithmic table", a quantity the harness cannot see; the measurer is now RSS and scratch-path
bytes from the execution receipt). No HIGH change; no section renumbered; §0, §8's three items,
§9, §14 and §16's invariant list untouched.

---

## 1. Accepted (cluster · severity as re-judged · seats · section · what landed · evidence)

| # | Cluster | Sev | Seats | § | Disposition and what landed |
|---|---|---|---|---|---|
| 1 | Submission verifier not bound to the claimed instance: `xP == Q` on a worker-chosen `(P, Q)` satisfies the letter; the egress rule makes "the verifier's passing node" the submission with no instance check | MED | G2, K4, S4 | §4 gate layer, §10 egress, §13 M0 | ACCEPT. §4: the verifier run takes curve, `n`, `P`, `Q` from the claim statement node it is invoked against (or the ladder's dispatch record), never from the submitter, who supplies `x` alone; the passing node records the instance; the egress renderer refuses a submission whose verifier node names another instance (§10: "on the instance the claim statement node names, or nothing"). §13 M0 Tier-0 verifier paragraph names the input source; M0 done-when adds the refusal-before-spawn fixture. Why added. Evidence: plan-r5 §13:1214-1215 (decimal-string inputs, source unnamed), §10:1099-1101 (passing node = submission), §7:850-856 (the scope grammar has no instance field, so `justify`'s coverage check could not be relied on to catch it). Re-judged MED: a gate-input contract, not a restructuring. |
| 2 | Checkpoint verification reads "the last checkpoint" only; the process user that can extend the file can truncate the log behind a fork and append the forked head, and the older heads nothing checks are the only trace | MED | S1 | §3, §13 M2 | ACCEPT. The log must extend every checkpointed head (each a prefix head of the current chain; the checkpoint sequence monotone along it); the why names the attack; M2 fixture extended (truncated, re-extended, forked head appended — fails). Not a re-litigation of r2 #11 / r3 R3 / r4 R4 (signing, remote anchoring, helper process, compaction): no new writer or key; one word of the rule and the sequence it already keeps. Evidence: plan-r5 §3:218-230 ("writable by the orchestrator's process user", "a log that does not extend the last checkpoint fails verification"), §3:213-214 (the purpose sentence the rule did not deliver). |
| 3 | §5 "the ladder's distribution rungs (≤ 50 bits) are Tier-1" vs §6 "each rung's tier follows its declared cost profile under the chosen count (an interpreted 50-bit baseline at that count runs for hours …)"; a rung the table assigns Tier 2 has no ticket (KEEP is what it mints; KEEP_IN_SAMPLE admits only the 60-bit rung) | MED | F3, S2 | §5, §6 | ACCEPT (F3's formulation). The rungs are admitted on the Tier-1 ticket whatever tier the boundary table would assign their ladder-plan-bounded cost — gate-owned launches whose count, arms and patience ceiling are plan fields and the launches that mint the Tier-2 ticket; §6 "each rung's tier" → "budget", with the ticket clause. S2's alternative (constrain the plan so the rungs are Tier 1 by the table) not taken: it would force the compiled-baseline decision M1 is told to record rather than make. Evidence: plan-r5 §5:470-471 vs §6:666-668; §5:571-577 (ticket kinds). |
| 4 | `Verifiable` names no verifier owner: a producer-shipped always-pass verifier satisfies "a witness checked by a deterministic verifier", the witness "is always checked", and fixture (m) carries the node to STRONG-EMPIRICAL; the Skeptic's and auditor's re-checks run the same verifier | MED | F1, G (repro-gate gaming) | §3, §13 M1 | ACCEPT. `Verifiable` only where the verifier is a gate-bundle object (Tier-0 verifier, the rho witness check) or a certified skill whose identity bundle differs from the producer's with a must-FAIL witness in its self-test; otherwise `AuditOnly`; why (the one ladder-shaped input left to the producer); M1 fixture. Evidence: plan-r5 §3:185-186, :142-143, §7:846-847, §13:1265-1266; `PROPOSALS.md:180-228` (C4 specifies the rho verifier's equations and no owner — F's fact, reproduced). |
| 5 | Tier-1 sharding: the tier is derived per launch, the branch grant is §0-mutable, and a 90-bit validation rho as a thousand honest one-core-minute walks needs no KEEP and trips no `TierRefused` or drift signal | MED | G7, F4, S (gaming table) | §5, §4 bundle, §13 M1 | ACCEPT (merged; minimal form). The gate charges every non-refused launch's production cost to its hypothesis key under the admitting ticket; the boundary table names a cumulative edge per ticket tier; the crossing launch is `TierRefused` until the next tier's ticket exists; M1 sets the Tier-1 edge above the ladder's own cost on one key; why added; bundle list carries the edges; M1 fixture. Adoption bar: component (tier gate + boundary table), cost (one counter, one column, one fixture), evidence CONJECTURE (no incident; `PROPOSALS.md:492-521` C12 budget = meet(parent, profile) with no cumulative term — F's fact, reproduced), spend-only (no tag moves). G7's batch identity / aggregate reservation object not adopted (a per-key charge needs no new object). |
| 6 | The memory predicate names a quantity the harness cannot measure ("peak algorithmic table and spill bytes with RSS as a diagnostic"): a method holds the BSGS table in process memory and reports zero; "an unaccounted storage channel failing closed" had no predicate; no line forbids network egress or writes outside a gate-owned path for a ladder-tested method | MED | F5, S3 | §6 (2), (3), §4 bundle, §13 M1 | ACCEPT (merged). The gate measures peak RSS over the process tree less the A/A arm's peak on the same instances (the clock calibration run's at 60 bits) plus bytes written to the gate-owned scratch path, from the execution receipt; reported table bytes are the diagnostic; the ladder-tested method's allow-list (a bundle object) names no other arithmetic backend, no network egress and no writable path but the scratch path; an unnamed channel is a planted-failure fixture; why (the harness sees the table only through what the method reports). M1 fixtures: table-in-RSS-reporting-zero exceeds the cap; socket or out-of-path write fails the self-test. Factual correction 1 below. Evidence: plan-r5 §6:679-681 (r2 #? wording, never examined for measurability), §6:739-745 (allow-list names backends and process spawn only), no occurrence of "network" in the plan; r5 open question 2 left the sandbox contract open — this is the ladder-scoped part of it. |
| 7 | The clock check's why ("the counter cannot see arithmetic done around it, but the clock can") holds only while the counted object is at least as fast as any arithmetic a method can carry: a method computing on extracted coordinates with its own faster arithmetic and issuing dummy counted calls sits inside the tolerance; a remote oracle shows low CPU and low count | MED | G6 (partial), S3 | §6 (3), §13 M1 | ACCEPT-PARTIAL. Stated bound (tolerance × counted work at the reference rate); condition: the counted object is compiled, M1 records the ratio of its per-operation cost to the fastest implementation on the build machine, and tolerance × ratio must stay below the band's excess over 1 (`2·radius`), a plan failing it refusing to start; wall-clock recorded, and wall-clock exceeding CPU beyond the tolerance marks the rung INCONCLUSIVE (an idle wait on a channel the counter cannot see); planted fixture (own arithmetic + dummy calls must not reach KEEP). G6's opaque-handle API as the mechanism not adopted: it constrains every coordinate-dependent method and the witness serialization, is tagged SPECULATION by the seat, and the rate condition closes the path the text can state. Evidence: plan-r5 §6:744-751 (tolerance check and its why); arithmetic re-done here: hidden fraction `h ≤ tol × ratio`, a non-advance reaches KEEP iff `h > 2·radius`. |
| 8 | The orchestrator "may withdraw" (§4:365-366, §5:594) while §13 M3 requires "no terminal `withdrawn` status is written by the orchestrator's path in any run" — both landed in r3/r4 | LOW | F2 | §4, §5 | ACCEPT (M3's side, the milestone gate that already binds): fund or park with `budget_preempt`; withdrawal is the worker's or the human's reason-bearing act, never the orchestrator's, whose vocabulary is PARKED. Wording; the M3 bar is unchanged. Evidence: plan-r5 §4:365-366, §5:594, §13:1346-1347. |
| 9 | "Terminal status (refuted / parked / promoted / withdrawn)" lists a status that auto-revives | LOW | G1 (partial) | §4 | ACCEPT (wording): resolved (refuted / promoted / withdrawn) or handed off to a park under a typed blocker; a park is a hand-off, not a terminal status. G1's new state set, owner field and blocker-validity rule not adopted (workers do not park — the orchestrator, the preflight and the human do, under typed blockers with stated predicates; no gaming path). |
| 10 | "Five launch-supplied inputs" counts two the gate resolves (self-test standing, ticket) and omits the launch's inputs the profile is evaluated at; "declared purpose" is a sixth | LOW | F6, S5b | §5 | ACCEPT (wording): three launch-supplied inputs (profile at the launch's inputs, budget, key and method identity / statement hash), two the gate resolves (standing, ticket — selected by the gate's rule, never supplied); the KEEP_IN_SAMPLE refusal reads the launch's skill and inputs. |
| 11 | The human-queue class enum is closed (§10) while the shape diagnostic (§6) and `Leaked` (§4, "escalated") route to no class; `Leaked` has no production consumer | LOW | F9, S5c/d | §10, §4 | ACCEPT. Classes `shape_departure`, `leaked`, `cost_drift`; a `Leaked` record is a `leaked` queue item while the obligation stays with the branch, which remains active for the orchestrator's next tick as after a harness-terminated attempt. |
| 12 | P4 alarms name no consumer (ceremony audit) | LOW | K5, G5 (part) | §15 P4 | ACCEPT (re-justification, not a cut): a fired alarm is a `cost_drift` queue item and a strategy input the orchestrator's tick may read to park with `budget_preempt`; moves no tag, ticket or class; retirement stated (never fires where the ladder or ceiling did not ⇒ dropped). |
| 13 | "Execution receipt" is undefined and the provenance check ("dry run, missing raw output, stale tool digest") has nothing named to read; `do_not_cache` has no setter | LOW | G5 (part), F8 | §3 | ACCEPT (re-justification): receipt fields named, written by the harness writer never the skill, readers named (ceiling, clock and memory measurements, provenance check); `do_not_cache` set by a skill whose interface declares its output non-memoizable (instance-maker, nonce draws, unseeded samplers), read by the serve path — REAPI's client-set semantics (`PROPOSALS.md:145,150`). |
| 14 | `justify`'s kind map lets `statistical` or `repro_node` evidence reach STRONG-EMPIRICAL for a cost-model claim without the ladder, while the taxonomy defines the class for such a claim as "ladder + repro node" | LOW | S (own; no seat) | §7, §13 M1 (m) | ACCEPT. A statement whose typed fields carry a cost model takes STRONG-EMPIRICAL from a `ladder_table` produced by a ladder gate run and from no other kind; `statistical`/`repro_node` offered for it cap at CONJECTURE; fixture (m) scoped to a computed fact with the cost-claim negative. Judged LOW, not MED: the router's top class (target family, below the generic bound) already requires ladder KEEP for promotion (plan-r5 §7:928-934, §4 gate discipline "inadmissible for promotion"), so the reachable mis-tag is a side claim. Evidence: plan-r5 §7:843-845 vs §7:836-838. |
| 15 | M1's fixtures write ledger entries (a REJECT "writes" one; fixture (b); KILLED) while "Dead-end ledger" is an M2 deliverable; M1 (h) needs the transitive `justified_by` walk §7 gives the M4 auditor and M1's Adds never names it | LOW | F10, S5a | §13 M1 | ACCEPT (dependency sanity): M1's Adds name the REFUTED/PARKED entry record (the preflight that reads it arrives at M2) and the transitive query (the auditor's sampling cadence arrives at M4). |
| 16 | Under the P3 surrogate a cheap REJECT at the 30-bit rung is a gate outcome, so a branch family pre-registering junk models on one method is reward-positive; no M3 bar tests it | LOW | F11 | §13 M3 | ACCEPT (milestone bar, no mechanism): a seeded run where one family pre-registers `k` junk models or jittered regions on one method must not out-earn control (j)'s branch; P3 still decides the mechanics. |
| 17 | §0 "worker prompts" are mutable while §4 puts role templates in the bundle | LOW | F7 | §4 | ACCEPT in §4 only (§0's text untouched): the handed nodes and subproblem text are the "worker prompts" §0 lets the orchestrator rewrite; a role template is bundle config it cannot touch. |
| 18 | "The whole research history is one replayable-or-verifiable DAG" while `AuditOnly` nodes exist and are inadmissible | LOW | G (framing) | §3 | ACCEPT (one clause): the admissible evidence graph is the DAG; `AuditOnly` nodes are kept and not in it. |
| 19 | §2 "Sage's `discrete_log` checks `base^res == a`" — the brief's L807-809 is `discrete_log_rho`; `discrete_log(verify=True)` re-checks its CRT result (L1117) | LOW | F (Part 0) | §2 | ACCEPT (precision): both named. Evidence: `briefs/adjacent-distributed-collision-search.md:40-41`. |

Accepted clusters: 19 (three partial). Gate-bundle contents re-enumerated to carry the cumulative
edges and the ladder-tested method's allow-list with its scratch path.

## 2. Rejected (cluster · seats · cause)

| # | Cluster | Seats | Cause |
|---|---|---|---|
| R1 | A `measured` entry's retry predicate should be met only by KEEP (or scoped KEEP_IN_SAMPLE), never by INCONCLUSIVE | K1 (HIGH claimed) | Re-litigates r4 #18 and r5 #11 (the null-control resolution and the retry default, both deliberate) with no new evidence; no worker path: the re-measurement is "enqueued by the human before M4 and by the foundations auditor from M4, never by the proposing worker"; a gate-owned re-measurement under the current plan that does not reproduce the REJECT is the gate's own standard failing to confirm the entry, and KEEP-only would leave a wrongly refuted non-advance permanently blocked. |
| R2 | "Most recent" should range over non-degrading successors only; INCONCLUSIVE must not displace KEEP | K2 | Re-litigates r5 #5 with no new evidence; the displacement is fail-closed by design and a worker cannot schedule a ladder run; the cost of a 60-bit INCONCLUSIVE is a Tier-1 re-ladder, not a deadlock. |
| R3 | Failure-side containment: `Blocked` when the proposal region is contained in a REFUTED entry's declared region | K3 | Over-blocks legitimately narrower hypotheses (the dual of r4 R8 / r5 R10: a narrower claim can hold where the broader fails); the measured reach is the minimal logical reach (r1 AF lineage); hole-drawing around the measured point is re-refuted by the floor at Tier-1 cost ("failing to beat it … refutes on the spot"), and the reward-side residue is met by cluster 16. |
| R4 | Interface-version laundering: `method_successor` edge and `method_identity_review` park | G3 | Re-litigates r4 #10 / R6 (renamed interface version routed by the near-dup advisory and the Librarian) with no new evidence; r4 open question 5 stands; the exposure is a Tier-1 re-refutation, not a tag. |
| R5 | Opaque group-element handles as the ladder's arithmetic API | G6 (half) | Constrains coordinate-dependent methods and witness serialization; SPECULATION by the seat's own tag; the rate condition plus planted fixture (cluster 7) closes the stated path. |
| R6 | Batch/fan-out identity with aggregate reservation as a new object | G7 (half) | A per-key charge against a bundle edge needs no new object (cluster 5). |
| R7 | Cut or operationalize tag history | G5 (half) | No defect: the write path branches on it (a transition without an evidence pointer is refused), the disagreement protocol reads the pre-dispute level, the renderer prints the derived tag; not an audit-only artifact. |
| R8 | Ticket minted under a prior gate bundle admissible after a bundle change | D (stream, unfinished) | Not a worker path (a bundle change is an operator deployment) and "a verdict is never recomputed under a later bundle" is deliberate; recorded as open question 1. |
| R9 | Worker-disposition state set `{active_with_owner, parked_with_valid_blocker, …}` and an owner field | G1 (half) | Renames and a new field for a wording defect; workers do not park; accepted as wording (cluster 9). |
| R10 | Edit §0's sentence ("worker prompts") | F7 (placement) | §0 is not revisable by review; the clarification lives in §4 where the role template is defined (cluster 17). |

## 3. Ceremony audit (artifact → running code that branches on it)

| Artifact | Consumer | Result |
|---|---|---|
| Golden certificate, self-test floor, yank record | Tier gate refusal (uncertified/yanked), `disowned` propagation, cache serve | holds |
| Recipe key / attempt rows / cache bits / salt | Cache serve, reproducibility gate, `justify` absence, preflight (hypothesis key) | holds; `do_not_cache` re-justified (setter and reader named) |
| Execution receipt | Budget ceiling, clock and memory measurements, provenance check | **re-justified** (was undefined; fields, writer and readers now named) |
| Witness certificate / replay grade | Witness verifier, reproducibility gate, tier admissibility | holds; `Verifiable` owner rule added (cluster 4) |
| Hash-chained log + checkpoint | Startup and pre-promotion verification | holds; rule corrected (cluster 2) |
| Ledger entries + preflight answers | Branch fund/open, retry predicates, §11 map | holds |
| Gate plan, bundle pin, planted pairs, waiver registry | Every gate run (fail closed), waiver check | holds |
| Attestation file / `review_verdict` / `nogo_review` | `justify` PROVEN, tier gate, waiver check, preflight | holds |
| Ladder result table (incl. shape diagnostic column) | Tier ticket, `justify`, ledger kind; shape column → human queue | holds; shape column given class `shape_departure` |
| Hunt record | Tier-2 conjecture ticket, ledger KILLED | holds |
| Tag history | Write-path transition rule, disagreement protocol, renderer | holds (R7) |
| Dispatch record | Ladder identity refusal, dispatch canary | holds |
| `TierRefused`, `Leaked` | Orchestrator tick path; `Leaked` → `leaked` queue item | `Leaked` **re-justified** (production consumer named) |
| Human queue items | Gate block on absent human input; orchestrator reads depth/age | holds; three classes added |
| Audit record (cycle grant, charges, critical set, seed, bits) | `audit_shortfall` item; the committed seed makes the random guarantee checkable; M4 done-when | holds |
| P4 alarms | `cost_drift` item + orchestrator tick input; retirement stated | **re-justified** |
| Negative-results map, lemma library | Egress renderer, research products | holds |
| Near-dup SimHash, panel ranks | Routing only, never status | holds by design |

Nothing cut: every artifact names a consumer after this round. Names promising more than
delivered, corrected: "measured by the harness" (memory), "the clock can" (condition stated),
"launch-supplied" (three, not five), "Verifiable" (owner), "whole research history".

## 4. Gate-gaming table (gate · path a worker could take · closing line)

| Gate | Gaming path | Closing line (plan-r6) |
|---|---|---|
| Submission verifier | Verify `xP == Q` on a self-chosen `(P, Q' = x'P)` and attach the passing node to a claim about the target | §4: "takes the curve, `n`, `P` and `Q` from the claim statement node … never from the submitter, who supplies `x` alone; … a submission whose verifier node names any other instance is refused by the egress renderer"; M0 fixture refuses before spawn |
| Ladder (i) | Offload the solve to a remote service: near-zero count, near-zero CPU | §6 (3): allow-list "names no other arithmetic backend, no network egress and no writable path but the gate-owned scratch path"; wall-clock exceeding CPU beyond the tolerance ⇒ INCONCLUSIVE; planted socket fixture fails the self-test |
| Ladder (ii) | Own faster coordinate arithmetic plus dummy counted calls inside the clock tolerance | §6 (3): tolerance × (object cost / fastest available) < `2·radius`, plan refuses to start otherwise; planted fixture must not reach KEEP |
| Ladder (iii) | BSGS table in process memory, report zero table bytes | §6 (2): RSS-and-scratch measurement is the predicate, reported bytes the diagnostic; planted fixture exceeds the cap |
| Ladder (iv) | Seen instances, self-reported counts, understated models, `xP ≠ Q` | already closed: gate-owned nonce and instances ("never a fixed instance the worker has seen"), "the count is the gate's measurement, never the claimant's", in-sample band, `implementation` yank |
| Formalization gate | Weak Challenge, `sorryAx`, shadowed constant, self-reported axioms | already closed: "the Formalizer never creates or edits Challenge text and submits a Solution module that names the Challenge's formal statement hash"; gate-owned `collectAxioms`; closure comparison; PROVEN needs an `approve` verdict through the human path — residual is review quality, §10's anchor |
| Reproducibility gate | Producer-shipped always-pass witness verifier | §3: "`Verifiable` is assigned only where the verifier is a gate-bundle object … or a certified skill whose §2 identity bundle differs from the witness producer's …; a witness whose only verifier ships in its producer's own revision is graded `AuditOnly`" |
| Ledger preflight (i) | Trigger a re-measurement that returns INCONCLUSIVE to unlock a REFUTED entry | already closed: "enqueued by the human before M4 and by the foundations auditor from M4, never by the proposing worker" |
| Ledger preflight (ii) | Region excluding the measured point, or junk models, to mint clean keys | bounded: the floor re-refutes at Tier-1 cost ("refutes on the spot"); reward side closed by the M3 bar (cluster 16); interface-version laundering stays open (r4 Q5) |
| Tier gate (i) | Shard Tier-2/3 work into Tier-1 launches | §5: cumulative edge per ticket tier; "the launch that would carry the key's charge … past that edge is `TierRefused` until the next tier's ticket exists" |
| Tier gate (ii) | Understate the declared cost | already closed (bounded): "a launch runs past the tier its declaration earned by at most the multiplier before it is stopped" |
| Tier gate (iii) | Spend a KEEP minted as A under branch B | already closed: "A ticket is bound to a hypothesis, never to a branch" |
| Tier gate (iv) | The ≤ 50-bit rung that the table assigns Tier 2 has no ticket | closed by cluster 3 |

## 5. Flagged invariant attacks

None. No seat proposed weakening §0, the gate layer's existence or immutability, the taxonomy,
the ladder's verdict rule, the verifier, the no-go checklist or the honest baseline. G1's
renaming of the terminal-status invariant is not in the protected set; F7's §0 wording was kept
out of §0. Every accepted change adds a binding, a measurer, a refusal, a fixture, a class or a
named consumer; none removes a gate input.

## 6. Factual corrections (each checked)

1. "Measured by the harness as peak algorithmic table and spill bytes with RSS as a diagnostic"
   (plan-r5 §6:679-681): the harness has no access to a method's table except the method's own
   report; RSS over the process tree and scratch-path bytes are what it can measure. **Changed a
   mechanism** (the memory predicate's measurer) ⇒ verdict cannot be STEADY.
2. "The counter cannot see arithmetic done around it, but the clock can" (plan-r5 §6:749-750)
   holds only under the rate condition now stated; arithmetic re-done (`h ≤ tol × ratio`).
3. "Five launch-supplied inputs" (plan-r5 §5:546-553): two are gate-resolved. Wording.
4. "The whole research history is one replayable-or-verifiable DAG" (plan-r5 §3:247-248) vs
   `AuditOnly` (§3:186-188). Wording.
5. "Sage's `discrete_log` checks `base^res == a`" — `discrete_log_rho` L807-809 and
   `discrete_log(verify=True)` L1117 (`briefs/adjacent-distributed-collision-search.md:40-41`).
   Wording.
6. Seat facts that reproduce: F — budget = meet(parent, profile), no cumulative term
   (`PROPOSALS.md:492-521`); C4 names the rho verifier's equations and no owner
   (`PROPOSALS.md:180-228`); REAPI `do_not_cache` is client-set (`PROPOSALS.md:145,150`); the
   hallucinated-table incident (`PROPOSALS.md:245-246`). F Part 0 re-verified here on a sample:
   0.14 radius, n ≳ 130 (≈ 137), `exp(−π) ≈ 4.3 %`, `l ≈ 1.4×10³`, 30 / 10³ / 3×10⁴ core-hours,
   1.3×10⁹ ops at 60 bits, BSGS 2²⁵ entries ≈ 1 GB at 50 bits — all hold.
7. "network" occurs nowhere in plan-r5; the sandbox contract is r5 open question 2 — the
   ladder-scoped closure is the plan's own line, not an evidenced stack fact.
8. K1's "INCONCLUSIVE unlocks REFUTED" reproduces as text and is the r4 #18 / r5 #11 design;
   not a defect. K3's "hole-drawing mints a clean key" reproduces as text and is the minimal
   reach by design; the floor re-refutes.

## 7. Seat reliability

- **GPT-5.6-sol:** complete; in format; 7 proposals with diffs under the word cap. G1 partial
  (LOW; HIGH claimed), G2 accepted (MED, merged), G3 rejected (re-litigation), G4 "no defect" on
  milestones (agreed), G5 partial (LOW; receipts accepted, tag history rejected), G6 partial
  (MED; rate condition and fixture, not the API), G7 merged (MED). Framing remark accepted as one
  clause. Its "facts needed" (transparent coordinates, verifier registry, batch identity) are
  answered by clusters 7, 4 and 5.
- **Grok-4.5:** complete; in format; 5 proposals plus a ceremony table and a gaming table. K1
  rejected (HIGH claimed; re-litigation), K2 rejected, K3 rejected, K4 accepted (MED, merged),
  K5 accepted (LOW). Over-severity on K1; its gate-by-gate closure quotes are accurate.
- **GLM-5.2:** 42 KB reasoning stream ("Let me check …"), no numbered proposals, truncated at
  "5. Ledger preflight:"; found no contradiction and flagged nothing actionable (P4 judged
  fine; "invariant" name noted). Exceeded the format; counted toward no cluster.
- **DeepSeek-v4-pro:** 43 KB reasoning stream, no numbered proposals, truncated mid-sentence;
  one candidate recovered (ticket vs later bundle) → open question 1. Exceeded the format for
  the sixth round.
- **Fable grounded:** complete; Part 0 fact pass (re-verified on a sample, holds; one nuance
  accepted as wording), 11 proposals, duties 2 and 3 answered gate by gate. F1 MED accepted,
  F2 LOW accepted (MED claimed), F3 MED accepted, F4 MED merged, F5 MED merged, F6–F11 LOW
  accepted (F7 placed in §4). The strongest seat this round; its framing remark — after these
  one-clause edits, build M0 rather than run a seventh mechanism round — is recorded below.

## 8. Open questions for the operator

1. Should a gate-bundle change that alters the ladder plan invalidate tickets minted under the
   prior bundle? The plan says a verdict is never recomputed under a later bundle and the tier
   gate does not compare the ticket's bundle hash with the pin (DeepSeek stream).
2. The Tier-1 cumulative edge's value and unit (core-seconds?) and how the ladder's own rungs
   are charged; the plan says M1 sets the edge above the ladder's cost on one key (cluster 5).
3. Which "fastest implementation available on the build machine" M1 measures the counted
   object against (a C reference, gmpy2, PARI) — it decides the tolerance inequality of
   cluster 7 and the compiled-baseline decision (r1 Q stands).
4. The funding line for gate-owned null-control re-measurements before M4 (human-enqueued; no
   budget line named).
5. Whether `leaked`, `shape_departure`, `cost_drift`, `clock_inconclusive` and
   `audit_shortfall` items close by an operator acknowledgment record through the human path
   (§10's closing rule names a human-path record and the plan names no such record type).
6. Interface-version laundering (G3; r4 Q5) and the native-skill sandbox contract beyond the
   ladder (r5 Q2) stand.
7. F's framing: declare the plan converged on mechanisms and start M0 — "a running 40-bit slice
   will reveal more than more architecture will" (§13) — rather than schedule round 7.
8. r1–r5 questions that stand: dispatch request-byte observability; budget-enforcement
   primitive; human review throughput; yank/salt authority; two OS users and host; Linux host
   for the gold tier; Tier-2 human-session knob; M4 checkpoint writer; tier boundary values.

## 9. Validation

- **(a) Self-containment.** Most obscure M0 task: the submission verifier's instance binding
  with its refusal-before-spawn fixture. Implementable as written: the gate run reads curve, `n`,
  `P`, `Q` from the claim statement node (or the ladder's dispatch record), the submitter
  supplies `x` alone, the passing node records the instance, the renderer refuses a mismatch,
  and the M0 fixture hands the verifier a worker-named `(P, Q)` and expects refusal before the
  subprocess spawns. The execution receipt at M0 is likewise buildable: fields, writer (the
  harness writer) and readers are named. At M1 the cumulative edge is a per-key sum compared
  with a bundle column; the memory predicate is RSS over the process tree less the A/A arm's
  plus scratch bytes, both from the receipt; the clock condition is an inequality over three
  recorded numbers.
- **(b) Dependency sanity.** M0 → M1 → M2 → M3 → M4 is a DAG. Builders for every mechanism
  added this round: M0 — verifier instance binding and fixture, receipt fields and `do_not_cache`
  setter (schema), the egress submission rule's instance clause (renderer at M4); M1 —
  `Verifiable` owner rule and fixture, cumulative edge column and fixture, RSS-and-scratch
  measurer, ladder allow-list (network, scratch path), wall-clock and rate condition with
  planted fixtures, cost-model scoping of `justify` with fixture (m), queue classes
  `shape_departure` and `cost_drift` (P4, M1–M2), the REFUTED/PARKED entry record and the
  transitive `justified_by` query; M2 — every-head checkpoint rule and fork fixture, `leaked`
  consumer with the `Leaked` record; M3 — REJECT-farming bar; M4 — renderer refusal on instance
  mismatch. No orphan: each has a consumer that branches on it (the verifier gate run, the
  renderer, the tier gate, the ladder verdict, the reproducibility gate, `justify`, startup
  verification, the milestone gate).
- **(c) Justification sampling.** Every-head checkpoint (why: the last head alone is no check
  because the extending process can append a forked head); cumulative edge (why: a per-launch
  tier is satisfiable by sharding and §0 lets the orchestrator fund it); `Verifiable` owner
  (why: a re-check running the producer's verifier is a count from the gated party); memory
  measurer (why: the harness sees the table only through what the method reports); verifier
  instance binding (why: a true statement about the wrong problem). All five carry a why; so do
  the clock condition, the cost-model scoping, the rung ticket and the terminal-status wording.
- **(d) Steady-state diff.** +119 lines (1473 → 1592), 235 diff lines. No structural change:
  no component's build order moved, no section renumbered, §0, §8's three items, §9, §14 and
  §16's invariant list unchanged. Mechanism-level in §3 (checkpoint rule, `Verifiable` owner,
  receipt, `do_not_cache`), §4 (verifier binding, terminal-status wording, `Leaked` consumer,
  bundle contents), §5 (rung ticket, cumulative edge, three inputs, withdraw), §6 (memory
  measurer, allow-list, wall-clock, rate condition), §7 (kind-map scoping); wording and fixtures
  in §10, §13, §15. Smaller than r5 (which added a write boundary) and r4 (which re-oriented the
  KEEP predicate); comparable to r3 in mechanism count, all of it closing stated gaming paths.

## 10. Verdict and residual scope

**NEEDS-ANOTHER-ROUND.** Seven MED clusters (1–7) and factual correction 1 changed a mechanism.
Expected residual scope for round 7: coherence of the new ladder allow-list and measurement
clauses with the sandbox contract r5 Q2 leaves open, of the cumulative edge with the escrow
accounting and the ladder's own rung charges, and of the verifier instance binding with the
scope grammar of §7 — wording-level unless a seat finds a new gaming path; the operator may
prefer F's framing (start M0) to a seventh round.
