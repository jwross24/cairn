# GUARD round 7 — Anthropic Fable grounded seat

Plan: `research/convergence/plan-r6.md` (1592 lines), read in full. Evidence read:
`PROPOSALS.md`; `briefs/adjacent-distributed-collision-search.md`,
`briefs/adjacent-proof-automation.md`, `briefs/frankenfs.md`; every file in `grounding/`;
`HANDOFF.md`; ledgers r5 §8 and r6 in full. Line numbers are plan-r6.

## Part 0 — Fact pass

- §2 `discrete_log_rho` checks `power(base,res)==a` (L807-809), `discrete_log(verify=True)`
  re-checks CRT (L1117) — verified at `briefs/adjacent-distributed-collision-search.md:41`.
- §5/§6 0.11 µs/iteration, 0.886√n, 1.25√n, BSGS ≈ 1.5√n and ≈ 3.4×10⁷ entries at 50 bits,
  1.3×10⁹ ops at 60 bits, sd ≈ 0.5·mean — `…collision-search.md:16-17,51-52`; 30 / 10³ / 3×10⁴
  core-hours, exp(−π) ≈ 4.3 % at 2×, radius 0.14, band 1.28, n ≳ 136, l ≈ 1.38×10³
  (`briefs/frankenfs.md:39`) — all re-derived, hold.
- §7 `leanchecker --fresh` 32.3 s, rejects neither `sorryAx` nor extra axioms, `landrun`
  Linux-only — `grounding/lean-checker-protocol.md:19-20,40-41,56`; `collectAxioms`, ∃-linter
  blind spots — `grounding/lean-statement-linters-vacuity.md:16,24,43`; §11 mathlib @1f29011 /
  v4.34.0-rc1 — `briefs/adjacent-proof-automation.md:9`.
- §13 M0 `ellcard` 75 ms at 60 bits, stack overflow, `ellsea(E,1)`, draws 11–220, F₅ curve of
  order 7 with `x = 3`, gp exit 0 on fatal error, zero-filled args —
  `grounding/pari-sage-toy-curve-backend.md:16-24,29,33,35`.
- §3 REAPI cache bits — `PROPOSALS.md:145-150`; §10 hallucinated table — `:245-246`; SimHash
  `:371`; RRF k ≈ 10 `:689-690`; rider `:17`; §7 — `HANDOFF.md:96`.
- Could not verify (stated as facts M0 grounds, so no defect): WAL mode / busy timeout
  (`grounding/dbos-…md:19` shows DBOS's `busy_timeout=30000`, no WAL pragma); the append-only
  flag against a non-owner writer. No factual error found.

## Duty 1 — Coherence of the constraint web

**1. Ladder allow-list: three clauses in one step, two incompatible** · MED · §6 (3), §13 M1
Line 805: "a ladder-tested method's allow-list (a gate-bundle object, §4) names no other
arithmetic backend, no network egress and no writable path but the gate-owned scratch path."
Line 811: "a ladder-tested method's allow-list permitting no process spawn beyond the backends
its hypothesis object declares". Lines 834-836: "A method that needs an uncounted backend
declares it in its hypothesis object, and its rungs are INCONCLUSIVE at best until a counted
implementation exists." The first fixes the allow-list as a bundle object with one arithmetic
backend; the second makes it vary with the hypothesis object; the third says a declared
uncounted backend runs. A Gröbner engine declared in the hypothesis object either spawns or trips
the planted out-of-allow-list fixture; the text says both (r6 cluster 6 added the first clause
over the other two — `ledger-r6.md` cites "§6:739-745 (allow-list names backends and process
spawn only)"). Reconcile toward the INCONCLUSIVE ceiling the clock check already enforces:

```diff
- ladder-tested method's allow-list (a gate-bundle object, §4) names no other arithmetic
- backend, no network egress and no writable path but the gate-owned scratch path.
+ ladder-tested method's allow-list (a gate-bundle template, §4, instantiated per dispatch and
+ named in the dispatch record) names no arithmetic backend but the gate-owned counted object
+ and the uncounted backends the hypothesis object declares (whose rungs are INCONCLUSIVE at
+ best, below), no network egress and no writable path but the gate-owned scratch path.
```
§13 M1 Adds (lines 1404-1405): "no other arithmetic backend" → "no undeclared arithmetic backend".

**2. The Tier-1 cumulative edge refuses the re-ladder the plan itself requires** · MED · §5, §3, §6
Lines 562-567: "The gate also charges every non-refused launch's production cost to its
hypothesis key under the ticket that admitted it … the launch that would carry the key's charge
under its current best ticket past that edge is `TierRefused` until the next tier's ticket exists
(M1 sets the Tier-1 edge above the ladder's own cost on one key)." Line 511: the ≤ 50-bit rungs
"are … admitted on the Tier-1 ticket", so their cost is charged to the key under Tier 1. The plan
requires a second ladder on the same key in three places: line 695 "a rung re-run after
INCONCLUSIVE sees fresh instances"; line 618 "so a new revision re-ladders before it spends" (the
hypothesis key excludes the revision, §3); line 349 the `measured` retry predicate "is met only by
a gate-owned re-measurement of the same hypothesis object under the current ladder plan". An edge
"above the ladder's own cost" — 1.1× satisfies the text — refuses each at the crossing rung, and
"until the next tier's ticket exists" cannot be met because the refused run is the one that mints
it; a clock-INCONCLUSIVE on an honest method has no exit. Gate-owned launches cannot be sharded
by a worker (counts, arms and patience are plan fields), so exempting them costs the sharding
closure nothing:

```diff
- it, and the boundary table names a *cumulative edge* per ticket tier: the launch that would
- carry the key's charge under its current best ticket past that edge is `TierRefused` until
- the next tier's ticket exists (M1 sets the Tier-1 edge above the ladder's own cost on one
- key).
+ it, and the boundary table names a *cumulative edge* per ticket tier over the charge of
+ worker-dispatched launches: the worker launch that would carry the key's charge under its
+ current best ticket past that edge is `TierRefused` until the next tier's ticket exists.
+ Gate-owned launches — ladder rungs, gate-owned re-measurements, the Skeptic's and the
+ auditor's re-runs — are charged to the key for the drift monitor (§15 P4) and never compared
+ against the edge: their counts, arms and patience ceilings are ladder-plan fields a worker
+ cannot shard (M1 sets the Tier-1 edge from control (j)'s measured pre-ladder Tier-1 spend).
```
Checked: the ticket and charge text. Assumed: the M1 fixture at line 1371 ("a branch … whose
launches would carry its hypothesis key's charge past … the Tier-1 cumulative edge") means worker
launches, which its wording supports.

**3. §2's `author_supplied` cap has no consumer; `justify` derives from `kind` alone** · MED ·
§2, §7, §13 M1 (m)
Lines 64-66: "a corpus supplied only by the worker that authored the skill is not a self-test,
and `author_supplied` alone caps the skill's results at CONJECTURE"; line 74: a cross-check
outside its independent range "is capped accordingly". Line 939: "the maximum class is a
function of `kind`"; `corpus_origin` occurs nowhere else (line 1300 only declares the
exemplar's). "The tag is derived, never set" (§7), so no other code can apply the cap. Fixture
(m), line 1357, admits "a reproducible Tier-1 measurement of a computed fact … with its repro
node" to STRONG-EMPIRICAL with no condition on the producer's corpus. Path: a worker authors a
skill, supplies a corpus of the skill's own outputs, computes a "fact" deterministically; the
re-run matches bit-for-bit (same code); `justify` returns STRONG-EMPIRICAL — the boundary §2
draws is crossed by the derivation. Also the duty-3 entry for the reproducibility gate.

```diff
-    producer's own tag}`; the maximum class is a function of `kind`, and coverage is a
+    producer's own tag}`; the maximum class is a function of `kind` and of the producer's
+    self-test standing — where the producer is a certified skill and not a gate-bundle object,
+    a corpus whose every origin is `author_supplied`, or a measurement outside the producer's
+    declared cross-check range, caps the class at CONJECTURE (§2) — and coverage is a
```
Fixture (m) gains: "and the same measurement from a revision whose only corpus is
`author_supplied` returns the CONJECTURE ceiling". Cost: one lookup from producer identity to
its self-test record, already a substrate node.

**4. Diagnostic queue items cannot close** · LOW · §10, §4 (r6 open question 5)
Line 1165: "an item closes only by a human-path record (§4) or by its blocker clearing." Lines
483-484 enumerate the human-path records (`review_verdict`, `nogo_review`, waiver, expert
sign-off, yank-reach ruling, Tier-2 revision admission). `leaked`, `shape_departure`,
`clock_inconclusive`, `cost_drift`, `audit_shortfall` hold no blocker (the `leaked` branch
"remains active", lines 382-384) and match no record type, so they never close and "depth and
age are drift-monitor inputs" (§10) degrade monotonically. Diff: §4 list gains "an
`acknowledgment` naming a queue item"; §10 gains "or, for an item holding no blocker, by the
branch or rung it names reaching a terminal status or re-running".

No defect found: §3 cache bits and grades vs the reproducibility gate and §7 kind map; §4
preflight vs the terminal-status invariant; §4 gate discipline vs the §10 envelope; §6 verdicts
vs the §5 ticket lattice; §7 tags vs the disagreement protocol; §15 deferrals vs §13 deciders. §13 dependency walk: every mechanism a done-when exercises is named in that or an
earlier milestone's Adds. Wording only: lines 550-551 "outlives its branch by at most that cycle"
holds from M4; before M4 the reservation stands until `justify` draws it.

## Duty 2 — Ceremony audit

Every artifact in r6's ceremony table still names running code that branches on it; I re-walked
each (tier-gate refusal, serve path, reproducibility gate, preflight, `justify`, startup
verification, gate runs, tick path, `audit_shortfall`, `cost_drift`) and found the consumers as
stated. Two fail the bar: `corpus_origin` (#3 — no consumer until `justify` reads it) and the
shape diagnostic column, line 706: "never a verdict predicate", the human queue its only
consumer, no defect class, no retirement. LOW · §6: state both or drop the class and keep the
column as table data — "defect class: a truncated or bimodal distribution the mean check cannot
see (BLS's bias toward short walks, `briefs/…collision-search.md:16,22`); retired if, by M3, no
`shape_departure` item preceded a REJECT or yank the verdict predicates missed." Names promising
more than delivered: none new.

## Duty 3 — Gaming the gates as written

- **Submission verifier.** Substitution closed ("never from the submitter, who supplies `x`
  alone"; M0 refusal before spawn). Residue: a worker opens its own claim statement node on a
  self-chosen `(P′, Q′)` on the target curve and submits the `x` it already holds; the verifier
  passes on the named instance and line 1186 admits egress "for the target or for any
  instance" — true, trivial, countable as "submissions", §9's forbidden state by volume. LOW ·
  §10: "a *submission* is the passing node on the instance a claim statement node written
  through the human path names; a passing node on a worker-opened instance is rendered as a
  finding, never as a submission."
- **Ladder.** Offload, own arithmetic, in-RSS table, seen instances, self-counts, understated
  models — closed by the §6 (2)–(3) lines r6 quoted. Residue is #1.
- **Formalization gate.** Closed: "the Formalizer never creates or edits Challenge text";
  gate-owned `collectAxioms`; closure comparison; PROVEN needs `approve` via the human path.
- **Reproducibility gate.** Producer-shipped verifier closed (`Verifiable` owner rule). Open:
  #3 — a bit-identical re-run proves determinism, not correctness.
- **Ledger preflight.** INCONCLUSIVE unlock closed ("never by the proposing worker"); region
  jitter bounded ("refutes on the spot").
- **Tier gate.** Sharding closed by the edge; understatement bounded by the multiplier;
  repointing closed ("bound to a hypothesis, never to a branch"). Residue is #2's inverse.

## Verdict

(a) **NOT STEADY** — three MED defects: a contradiction inside §6 (3) (#1), a §5 rule that
refuses a re-ladder §3, §5 and §6 require (#2), and a §2 calibration cap with no consumer in §7
(#3). None touches §0, the gate layer, the taxonomy or the baseline; each is a clause.
(b) Fix first: #3 — the only one that moves a tag across a calibration boundary
(STRONG-EMPIRICAL from an author-tuned skill); one input to `justify` plus one fixture.
(c) Framing: none wrong. r6's residual scope is what I found; after these clauses the plan is
converged on mechanisms and §13's own rule applies — build M0. One standing limitation, not a
defect: the ladder counts group operations, so a method whose cost lives in field or polynomial
arithmetic is INCONCLUSIVE until a counted object for its primitives exists (r5 open question);
that gate fails closed and should stay so.
