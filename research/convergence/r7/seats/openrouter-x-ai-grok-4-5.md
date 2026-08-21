# Guard round — plan-r6.md

Raised bar: changes only for defects evidenced in the plan text.

---

## 1. Coherence of the constraint web

Checked cross-links: substrate/cache/disown (§3), replay grades/certificates (§3), ledger preflight + terminal-status (§4), gate bundle/discipline (§4), budget meet + escrow + cumulative edge + tickets (§5), ladder (§6), Lean challenge/solution + derived tags (§7), disagreement (§7/§10), deferred P1–P7 (§15), milestones (§13).

**Holds (no defect):** Recipe vs hypothesis identity split (interface in hypothesis; full bundle in recipe/ladder/ticket) is consistent with re-ladder-on-revision. `KEEP_IN_SAMPLE` ↔ 60-bit scoped ticket is stated the same way in §5 and §6. Ladder ≤50-bit Tier-1 exception + “M1 sets the Tier-1 edge above the ladder’s own cost on one key” removes cumulative-edge deadlock. `status ≠ OK ⇒ never cached/ticket/evidence` is repeated but aligned (§2/§3/§5). Null-control / retry enqueue (“never with the proposing worker”) matches gate-owned measurement. M1 writes REFUTED rows; M2 installs preflight — ordered, not contradictory. Hash-chained log/checkpoint at M2 with M0 grounding the append-only flag matches §3’s parenthetical. Submission instance gate-read + egress eligibility agree (§4/§10). Rejected list (no LLM judges as gates, no majority vote, no off-the-shelf CA cache binaries, no e-value sub-grades) is respected; P1 e-process is resource-only and non-promoting.

**Defect — `AlreadySettled` clear vs standing success**

| Side | Quote |
|------|--------|
| Purpose | “a settled success re-funded unchanged buys no knowledge and is the cheapest loop a gate-outcome reward can find” (§4 preflight why) |
| Fire condition | “`AlreadySettled` = the proposal opens a new branch on a hypothesis key that a **branch already holds** — an active or parked one, or a **promoted** one whose claim statement stands at PROVEN or STRONG-EMPIRICAL” |
| Clear condition | “blocker `already_settled`, which clears when … or **when the holding branch withdraws**” |
| Withdrawal | “Withdrawal is terminal … act of the branch’s worker or of the human”; “erases **no** gate outcome already recorded against the statement hash” (§4 terminal-status) |

After KEEP/`justify` → STRONG-EMPIRICAL, a worker can **withdraw** the holding branch. No branch still “holds” the key, so `AlreadySettled` does not fire, while tags and ladder tables remain. That is a direct self-defeat of the stated anti-refund loop (worse under §5 gate-outcome allocation).

**Not a contradiction (intentional build gaps):** preflight absent until M2; auditor cadence at M4; full egress renderer at M4 with submission rule at M0 — all explicit.

**Milestones vs mechanisms:** No §13 done-when depends on a mechanism never introduced; auditor/escrow/justify/ladder/preflight ordering is buildable.

---

## 2. Ceremony audit

| Artifact | Runtime consumer |
|----------|------------------|
| Recipe/attempt/cache bits/`disowned` | Cache serve, tier gate, `justify` |
| Execution receipt | Budget ceiling, ladder RSS/clock, §4 provenance |
| Replay grade + certificates | Repro gate, ticket admissibility, `justify` ceilings |
| Ladder result table | Tier ticket, ledger REJECT, `justify`, §11 map |
| Ledger + preflight answers | Funding/open path |
| Gate bundle + pin + planted self-tests | Every gate run; fail closed on hash mismatch |
| `review_verdict` / `nogo_review` / attestation file | `justify` PROVEN; tier presence/`accept_for_tiering` |
| Human queue items | Blockers + autonomy envelope; orchestrator read for scheduling only |
| Tag history | Derived tag, egress, auditor re-derive |
| Checkpoint / hash chain | Startup + promotion block (from M2) |
| Dispatch canary / allow-lists | M1 self-test; yank path on fail |
| Hunt record | Tier-2 conjecture ticket; KILLED → ledger |
| Cost/drift alarms | Human queue `cost_drift`; strategy park — **not** claim gates (stated) |
| Near-dup SimHash | Advisory route only (stated) |
| Negative-results map / lemma library | Accretive outputs; renderer refusal predicate |

**No cut required** at guard bar: each either branches in gate/scheduler code or is an explicit §11 product with egress gating.

**Name vs definition:** “Certificate … never truth” and “info-per-dollar … until M3 … gate-outcome reward per measured cost” are honestly scoped. No empty ceremony name above LOW.

---

## 3. Gaming the gates as written

**Submission verifier.** Letter-game: put an easy `(P,Q)` in a claim the worker authors and submit `x`. **Closed for “broke the target”:** instance is gate-read from the claim/dispatch, not the submitter; egress submission = passing node only on that instance; top scrutiny is a **bundle predicate on typed fields** (“scope names the target family and … solve below the generic bound”) plus §10 sign-off; informal brag without coverage still fails `justify` population rules. Toy claims are honest toys.

**Ladder.** Sharding 90-bit into many Tier-1 walks: **closed** — “per-launch rule alone is not cheap-before-expensive” + cumulative edge on hypothesis key. Worker instances / dummy counters / side storage: **closed** by planted self-tests and gate-owned counter + allow-list. Post-hoc model: **closed** by append order before nonce. Scoped `KEEP_IN_SAMPLE`: **closed** — “valid for the 60-bit rung … and for no other launch.”

**Formalization.** `sorry`/extra axioms/weaker statement/Challenge edit: **closed** — gate-compiled Challenge, gate-owned axioms, closure compare, ordered scopes, `approve` on same statement hash via human path.

**Reproducibility.** Producer-only verifier: **closed** — “graded `AuditOnly`.” Missing repro on ladder: ceiling CONJECTURE. Skeptic/`justify` re-runs set `skip_cache_lookup`.

**Ledger preflight.** Paraphrase: **closed** — key is structural; free text excluded. Param jitter off measured points: acknowledged limit (“nothing broader; a broader blacklist needs a formal entry”), not a letter hole. **Not closed:** withdraw → clear `already_settled` (above).

**Tier gate.** Lowball declaration: boundary table + ceiling multiplier. Ticket club-card: bound to hypothesis + method + ladder revision. Multi-kind claims need every ticket kind.

**Extra ticket fragility (game/pressure):** “a later REJECT or **INCONCLUSIVE** ladder table displaces an older KEEP.” A re-ladder that lands `INCONCLUSIVE` (noise/clock) strips the Tier-2 ticket though §6 defines INCONCLUSIVE as non-refutation. Hostile or obligatory re-run can brick an honest KEEP without a ledger REJECT.

---

## Proposals (guard bar)

### 1. `AlreadySettled` must survive branch withdrawal  
· **HIGH** · §4 ledger preflight  

· **Rationale:** Clearing `already_settled` on withdraw while gate outcomes and STRONG-EMPIRICAL/PROVEN tags remain re-opens the exact “settled success re-funded unchanged” loop the mechanism exists to stop; withdrawal is worker-operable and erases no outcomes.  

· **Diff:**
```diff
- AlreadySettled = the proposal opens a new branch on a hypothesis key that a
- branch already holds — an active or parked one, or a promoted one whose claim
- statement stands at PROVEN or STRONG-EMPIRICAL — or opens a branch whose method
- identity and claimed cost model equal such a promoted holder's and whose
- declared parameter region is contained in the holder's ...
- parked with blocker already_settled, which clears when a superseding hypothesis
- object with the attributed difference statement ... is recorded, or when the
- holding branch withdraws
+ AlreadySettled = the proposal opens a new branch on a hypothesis key for which
+ (a) any non-withdrawn branch (active|parked|promoted) already holds that key, or
+ (b) an admissible KEEP/KEEP_IN_SAMPLE ladder_table or claim tag at PROVEN or
+ STRONG-EMPIRICAL already stands for that key (or for the same method identity +
+ cost model on a region containing the proposal's region under the same
+ axis-aligned rule) — unless the proposal is a superseding hypothesis object...
+ Blocker already_settled clears only when: a superseding object with the
+ attributed difference statement is recorded; or the standing claim is refuted
+ or withdrawn at the statement-hash level; or every admissible KEEP ticket for
+ that key is displaced by a measured REJECT (ledger path). Branch withdrawal
+ alone never clears (b) and never erases standing tickets/tags.
```

### 2. INCONCLUSIVE must not displace KEEP for ticket selection  
· **MED** · §5 Tier gate predicate (+ align §6 ticket prose if needed)  

· **Rationale:** Ticket rule treats INCONCLUSIVE like REJECT for recency, but §6 verdict taxonomy treats INCONCLUSIVE as non-KEEP/non-REJECT. One noisy re-ladder removes cheap-before-expensive admission without writing REFUTED.  

· **Diff:**
```diff
- the ticket is the most recent admissible substrate node of the kind the tier
- requires ... where "most recent" ranges over every node of that kind for the
- hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table
- displaces an older KEEP — and the verdict rule below is applied to the node
- so selected
+ the ticket is the most recent admissible node of the required kind whose
+ verdict satisfies the tier's verdict rule (e.g. KEEP / scoped KEEP_IN_SAMPLE /
+ SURVIVED). A later REJECT (ledger-measured or table verdict REJECT) invalidates
+ older KEEP tickets for that key/method/revision via the ledger reach rules.
+ INCONCLUSIVE tables are retained and do not displace or invalidate an older
+ KEEP for ticket selection; they are not tickets.
```

### 3. (No further mechanism proposals)

Ceremony: **no defect found** requiring cuts.  
Other coherence pairs: **no defect found**.  
Gates other than already_settled / INCONCLUSIVE-displace: **letter closed** as quoted in §3.

---

**(a) Verdict:** **NOT STEADY** — one HIGH structural hole: `already_settled` clears on withdraw while success evidence remains.  

**(b) Fix first:** Proposal 1 (`AlreadySettled` standing-success predicate).  

**(c) FRAMING:** No framing error on §0 / gates / honest baseline / calibration. Secondary note (not a third proposal): gate-outcome-per-cost until M3 is explicitly farm-prone; M3’s junk-family bar is the right place to bind it — leave framing, don’t pre-solve P3 here.

**Stake order:** 1, then 2.  
**Facts not in plan (non-blocking):** who writes branch status `promoted` vs tag derivation only — fix (1) should key off tags/tickets so that gap stops mattering.