# Guard review — plan-r5.md

## 1. Coherence of the constraint web

**HOLD (no contradiction):** substrate key / cache bits / disown-by-salt (§3) vs yank reach (§2); recipe key (full identity) vs hypothesis key (interface version only) (§3); replay grades vs tier escrow release (§3/§5); terminal-status vs `INTERRUPTED`/`SKILL_YANKED`/`BUDGET_EXCEEDED` (§4/§5); gate-bundle pin + attestation path (§4); KEEP / KEEP_IN_SAMPLE ticket split (§5/§6); challenge/solution hashes + `justify` (§7); disagreement non-vote (§7/§10); M0→M4 order vs mechanisms (preflight before orchestrator; log/checkpoint at M2 before M3 motion bar); §15 deferred items stay off §0/gates.

**DEFECT A — measured retry vs permanence (HIGH).**  
§4 retry rule: *“a `measured` entry's retry predicate is met only by a gate-owned re-measurement … whose verdict is not REJECT”.*  
Null-control resolution: *“any other verdict is a gate-owned measurement that meets the entry's retry predicate — the answer is `Allowed`”.*  
Same section’s Why: *“REFUTED is permanent unless the retry predicate is met”* and ledger teeth against re-funding known failures.  
**Clash:** `INCONCLUSIVE` (variance, patience, clock band — §6) is “not REJECT”, so it **meets** the retry predicate and re-opens funding while the REFUTED row still stands. Permanence is letter-satisfied and purpose-defeated.

**DEFECT B — “most recent” ticket displacement (MED).**  
§5: *“‘most recent’ ranges over every node of that kind for the hypothesis whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces an older KEEP”* and the verdict rule is applied to that node.  
§6/`justify`: KEEP is the Tier-2/STRONG-EMPIRICAL workhorse; INCONCLUSIVE is an expected variance outcome (*“inside the band”*).  
**Clash:** a later honest/noisy INCONCLUSIVE (or a non-KEEP re-ladder) erases ticket standing from an earlier KEEP without a gate-owned invalidate predicate. Conflicts with cheap-before-expensive continuity and with escrow that keeps Tier-2 nodes re-runnable after branch terminal (§5).

**DEFECT C — range-jitter Why vs preflight (MED).**  
§4 Why: *“recorded as fields so that range jitter cannot mint a clean key”.*  
Mechanism: key includes *“declared parameter ranges”* (§3); `Blocked` on measured reach only when the **proposal region contains** a measured failed point (axis-aligned inclusion).  
**Clash:** a proposal that **excludes** the measured point (micro-shift or hole) gets a new key and is not `Blocked`. Success side explicitly closed the dual loop (*`already_settled`* on sub-regions); failure side did not. The Why overclaims the mechanism.

No milestone depends on an unbuilt mechanism at the raised bar.

---

## 2. Ceremony audit

| Artifact | Code that branches |
|---|---|
| Recipe/attempt rows, cache bits, disowned | Cache serve; tier ticket; `justify` absence |
| Certificates / replay grade | §3 verifier; repro gate; tier admissibility |
| Ladder result table | Tier ticket; `justify`; ledger REFUTED kind |
| Ledger + preflight answers | Branch fund/open |
| Gate plan / bundle pin / planted self-tests | Every gate run fails closed on mismatch |
| Skill self-test + golden cert | Tier gate launch; yank |
| `review_verdict` / `nogo_review` / attestation | `justify` PROVEN; tier >1 on flagged attacks |
| Claim tags (derived) + tag history | `justify`; egress renderer |
| Human queue items | Gate block on absent human input; orchestrator strategy read |
| Hunt record SURVIVED/KILLED | Tier-2 conjecture ticket; ledger |
| `TierRefused`, `Leaked` | Orchestrator tick path; tests/escalation |
| Checkpoint / hash chain | Startup + promotion verification |
| Negative-results map / lemma library | Research products + egress; OK |
| P4 alarms (conformal / cost e-process) | **No named branch** — “strategy-layer alarms only” (§15 P4). Status-report risk. |
| Near-dup SimHash | Advisory route only — OK if kept non-status |
| Panel ranks | No gate — OK by design |

**Name > definition:** none new beyond what §7 already disciplines (*“certificate… never truth”* is explicit).  

**P4 alarms:** either name a consumer (e.g. force `low_yield_pivot` / human-queue class / launch cool-down the tick code reads) + observed defect class + retirement when P4 decides they never fire, or cut from the build surface until that consumer exists.

---

## 3. Gaming the gates as written

**Submission verifier.** Letter: subprocess `n·Q=O` then `xP==Q`, accept only exit 0 + `stdout=="OK"` + empty stderr (§13).  
**Game:** feed any easy prime-order triple (toy curve) where the worker knows `x`; verifier passes; egress calls that a “submission” (*“for the target or for any instance”* — §10).  
**Not closed:** no binding of `(curve,n,P,Q)` to a content-addressed **target/instance claim** the renderer may export as a solve. Instance-maker binding exists for the ladder, not for submission egress.

**Ladder.** Instances/nonce/counter/allow-list/pre-reg/order/KEEP band are gate-owned (§6). Hardcoded seeds fail commit order; uncounted arithmetic → clock INCONCLUSIVE; understated model → in-sample REJECT; `xP≠Q` → implementation yank not method KEEP.  
**Closed** for the dominant fake-advance class. Residual: DEFECT B (noise re-ladder) and patience-as-failure are harsh but not purpose-defeating fakes.

**Formalization gate.** Challenge gate-compiled; Solution must name formal statement hash; axioms gate-owned; closure compare; `sorryAx` rejected; PROVEN needs `approve` verdict via attestation (§7/§4).  
**Closed** for sorry/weaker-export/hash-only games. Residual is human review quality (in scope of §10), not letter bypass.

**Reproducibility gate.** Witness check / re-run / diverge → inadmissible; Tier-2/3 Replayable capped CONJECTURE until check (§3/§7).  
**Closed** for silent promote. Residual: linger at CONJECTURE (does not mint PROVEN/STRONG-EMPIRICAL).

**Ledger preflight.**  
**Game 1:** one gate-owned re-ladder returns `INCONCLUSIVE` → retry met → `Allowed` (DEFECT A).  
**Game 2:** exclude measured parameter point from declared region → new key, not `Blocked` (DEFECT C).  
Success-side `already_settled` is closed (*sub-region of promoted holder*); failure-side dual is not.

**Tier gate.** Ticket bound to hypothesis + method + revision; boundary table vs declaration; yanked/uncertified refused; KEEP_IN_SAMPLE scoped to 60-bit (§5).  
**Closed** for club-card and skip-a-tier declaration (bounded by ceiling multiplier). Not closed: DEFECT B losing KEEP to later INCONCLUSIVE; 4× overrun is acknowledged bound, not a full bypass.

---

## Proposals (raised bar — defects only)

### 1. Measured retry = positive clearance, not non-REJECT  
· **HIGH** · §4 (retry predicate + null-control path)  
· **Rationale:** Quotes in DEFECT A. `INCONCLUSIVE` must not unlock REFUTED.  
· **Diff:**
```diff
- a `measured` entry's retry predicate is met only by a gate-owned re-measurement
- of the same hypothesis object under the current ladder plan whose verdict is not REJECT
+ a `measured` entry's retry predicate is met only by a gate-owned re-measurement
+ of the same hypothesis object under the current ladder plan whose verdict is KEEP
+ (or KEEP_IN_SAMPLE where the entry's measured points lie entirely in the in-sample
+ sizes); INCONCLUSIVE does not meet the predicate; REJECT confirms the entry
...
- any other verdict is a gate-owned measurement that meets the entry's retry predicate
- — the answer is `Allowed`
+ KEEP (or scoped KEEP_IN_SAMPLE as above) meets the retry predicate — `Allowed`,
+ with the re-measurement table as evidence that met it; INCONCLUSIVE leaves the
+ blocker/predicate unmet; REJECT confirms — `Blocked`
```

### 2. Ticket “most recent” only among non-degrading successors  
· **MED** · §5 tier ticket paragraph  
· **Rationale:** DEFECT B — INCONCLUSIVE must not displace KEEP.  
· **Diff:**
```diff
- where "most recent" ranges over every node of that kind for the hypothesis
- whatever its verdict — a later REJECT or INCONCLUSIVE ladder table displaces
- an older KEEP — and the verdict rule below is applied to the node so selected.
+ where "most recent" ranges over admissible nodes of that kind for the hypothesis
+ whose verdict is at least as strong as the ticket lattice requires (KEEP ranks
+ above KEEP_IN_SAMPLE ranks above non-tickets). A later INCONCLUSIVE never
+ displaces a KEEP/KEEP_IN_SAMPLE ticket. A later REJECT displaces and applies the
+ §6 ledger kind for its predicate. A gate-owned re-ladder that returns KEEP
+ replaces the prior ticket; workers cannot schedule displacement runs.
```

### 3. Close failure-side range jitter (mirror `already_settled`)  
· **MED** · §4 ledger preflight + measured reach Why  
· **Rationale:** DEFECT C; success side already blocks sub-region re-funding.  
· **Diff:**
```diff
- Blocked = the hypothesis key (§3) matches a REFUTED entry whose retry predicate
- is unmet, or the proposal's declared parameter region contains a measured
- parameter point at which a REFUTED entry records the same method identity
- failing the same cost model (...);
+ Blocked = the hypothesis key (§3) matches a REFUTED entry whose retry predicate
+ is unmet, or a measured REFUTED entry records the same method identity and
+ cost model and either (i) the proposal region contains a measured failed point,
+ or (ii) the proposal region is axis-aligned-contained in the refuted entry's
+ declared region (failure-side dual of already_settled; prevents hole/micro-jitter
+ clean keys), or (iii) ... existing formal/implementation rules ...
- so that range jitter cannot mint a clean key
+ so that range jitter and hole-drawing cannot mint a clean key on the failure side
+ the way sub-region re-ladder cannot on the success side
```

### 4. Submission binds instance identity  
· **MED** · §4 gate list · §10 egress · §13 verifier  
· **Rationale:** Gaming §3 — `xP==Q` on a worker-chosen easy instance satisfies the letter.  
· **Diff:**
```diff
- submission verifier (`xP==Q` subprocess or no submit, ever)
+ submission verifier (`xP==Q` subprocess or no submit, ever): inputs must name a
+ substrate instance node (curve,n,P,Q) whose content hash matches the claim
+ statement's bound target/instance hash; mismatch is FAIL, not OK
...
- a *submission* — the egress of a recovered `x` for the target or for any
- instance — is the verifier's passing node (§13) or nothing
+ a *submission* is the verifier's passing node on that bound instance hash, or
+ nothing; a pass on an unbound or worker-supplied instance is not egress-eligible
```

### 5. P4 alarms: consumer or cut  
· **LOW** · §15 P4  
· **Rationale:** Ceremony — no running branch.  
· **Diff:** add *“consumer = orchestrator tick cool-down / human-queue class `cost_drift` (not a claim gate); retire if M1–M2 planted drift never fires where ladder/ceiling already caught”* or delete until consumer exists.

---

**(a) Verdict:** **NOT STEADY** — DEFECT A (INCONCLUSIVE unlocks measured REFUTED) is a structural fail-open on the ledger’s core invariant.  

**(b) Fix first:** Proposal 1 (measured retry = KEEP-class clearance only).  

**(c) FRAMING:** No framing error on §0, gates, calibration, or the honest baseline. The failure mode is local over-fitness of retry/ticket “most recent” wording under variance — not a wrong architecture story.

---

### Stake ranking / standing footer
**(a) Stake most on:** 1 (retry), 2 (ticket displacement), 4 (submission bind).  
**(b) FRAMING:** Sound; keep “this stands” load-bearing.  
**(c) Facts not in plan (non-blocking):** whether ladder measured points are only discrete rung sizes (affects how sharp jitter is in practice); exact substrate shape of a “target instance node” for submission binding at M0 vs M1.