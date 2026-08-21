# Review of plan-r3.md — repository-reading seat

## Fact-check pass (my extra duty)

Checked against `research/grounding/` and `research/PROPOSALS.md`:

- Tier-2 rho pricing, §5 (`0.11 µs/iter`, `0.886√n`, ≈30 core-h @80b, 10³ @90b, 3×10⁴ @100b) —
  **arithmetic verified**; the 362 cycles/iteration source is `PROPOSALS.md:C6(c)`.
- Ladder figures §6 (BSGS ≈1.5√n ≈5×10⁷ ops and ≈3×10⁷ entries at 50b; rho ≈1.25√n ≈4×10⁷;
  60-bit ≈1.3×10⁹ ops, "minutes compiled / quarter hour interpreted") — **verified** at
  `PROPOSALS.md:C6(c)`; the interpreted figure follows from the measured 4.2M ops / 2.9 s row.
- Budget ceiling §5 ("2× aborts ≈4 % of honest rho trials, 4× well under 0.1 %") — **verified by
  computation** under a Rayleigh runtime with sd = 0.523·mean: `exp(−π)=4.3 %`, `exp(−4π)=3.5×10⁻⁶`.
- Auditor bound §7 (`l ≈ 1.4×10³` at `f=0.01, bits=20`) — **verified** (1379). 60-bit rung
  SE ≈16 % at `m=10` — **verified** (0.5/√10).
- PARI facts §13 (`ellcard` generic ≤50b, SEA ≈75 ms @60b, default-stack overflow, `ellsea(E,1)`
  early abort, exits 0 on fatal error, zero-fills missing args, `elllog` non-termination) —
  **verified at** `grounding/pari-sage-toy-curve-backend.md:23,24,28,29`.
- M0 corpus §13 (F_5 `[-3,1]` order 7 with `P=(0,1), Q=3P, x=3`; 150-bit composite case; the
  `p=101` case whose `P` is not explicit upstream; `n·Q ≠ O` negative control) — **verified at**
  `grounding/pari-sage-toy-curve-backend.md:33–36`.
- Lean facts §7 (`leanchecker --fresh` 32.3 s mathlib-free, unmeasured with mathlib; comparator
  needs Linux `landrun`, macOS fallback unsandboxed/dev-only; raw exports unstable, closure hasher
  CONJECTURE and does not yet exist) — **verified at** `grounding/lean-checker-protocol.md:41,20,
  50,55,56`.
- Statement pre-filters §7 (vacuity certified-only; `∃ x, P x → Q` linter silent on binder-predicate
  and conjunction-nested forms; `ZMod 0`, `x/0`, `sInf ∅`) — **verified at**
  `grounding/lean-statement-linters-vacuity.md:16,36,43`.
- §13 M0 "observed draws span 20–220 at 30–50 bits" — **could not verify**; the recorded `ellcard`
  tries are 48/148/20, 40/52/57, 36/11/220 (`pari-sage-toy-curve-backend.md:18–20`), i.e. **11–220**.
- §12 license claim — **verified at** `PROPOSALS.md:0` ("Standing constraint", reviewer-checked).
- §15 P3(iii) "a tick table in SQLite; not a workflow server" — **verified**: this is exactly the
  recommendation at `grounding/dbos-sqlite-and-agent-sdk-isolation.md:23`.

Everything above holds except the one flagged line and the two defects below, which are
substantive.

---

## 1 · The ladder's KEEP predicate is inverted against its own estimator · HIGH · §6

**This is a wrong claim in the plan, not a style point.** §6 defines the estimator as "a CI on the
**ratio of claim cost to baseline cost**", then requires "a speedup is KEPT only if the whole claim
CI clears `1 + 2·radius`". Under a cost ratio a speedup is *below* 1; as written, a method 30 %
**slower** than plain rho is KEPT and a genuine 1.4× speedup is REJECTed. The gate the plan calls
its "top anti-fabrication device" fails open on its acceptance predicate.

I checked the evidence before touching it: `PROPOSALS.md:C6(d)` cites
`fsqlite-e2e/benches/pipeline_stage_bench.rs:1262-1283` (PROVEN-in-source) for
`KEEP iff claim CI clears max(1+2·radius, 1.01)` — in that source the statistic is a **speedup
factor**. The band is well-evidenced; the plan's own restatement of the estimator introduced the
sign error. Two internal cross-checks confirm the intended orientation: M1 positive control (j) is
"√2 **on group operations**" (a factor > 1), and §6's "puts the √2 control at the band's edge" only
parses against a threshold near 1.3.

```diff
-protocol as one versioned object: the estimator (a CI on the ratio of claim cost to
-baseline cost — the source's median-CI form or a mean CI, named), the pairing
+protocol as one versioned object: the estimator (a CI on the speedup factor — baseline
+group-operation cost divided by claim group-operation cost, so a real advance is > 1 —
+in the source's median-CI form or a mean CI, named), the pairing
```

**Second, the stated 10² floor cannot pass its own positive control.** At sd = 0.5·mean and
n = 10², the A/A radius is ≈0.15 and the claim CI half-width ≈15 %, so control (j)'s lower bound is
1.414 × 0.85 ≈ 1.20, inside the 1.30 band — INCONCLUSIVE, not KEPT. Solving
`1.414(1 − 1.386/√n) > 1 + 2·(1.386/√n)` gives **n ≳ 130**. (Verified: the algebra. Inferred: that
the arms are effectively independent — pairing buys little because rho's variance is in the method
seed, not the instance. M1 must measure this rather than adopt 130.)

```diff
-and the rule that every rung must pass, the tolerances of step (3), and the baseline skill
-revision; the trial count is sized at M1 so that positive control (j) of §13 is KEPT and
-control (k) INCONCLUSIVE with margin — the 10² figure is a floor, and at rho's sd ≈ 0.5·mean
-the ratio CI at 10² trials is about ±15 %, which puts the √2 control at the band's edge —
+and the rule that every rung must pass, the tolerances of step (3), and the baseline skill
+revision; the trial count is sized at M1 so that positive control (j) of §13 is KEPT and
+control (k) INCONCLUSIVE with margin. 10² is not that count: at sd ≈ 0.5·mean the A/A radius
+is ≈ 0.15 and control (j)'s CI lower bound is ≈ 1.20 against a 1.30 band, so 10² returns
+INCONCLUSIVE on a known-true advance. Solving the KEEP inequality for the √2 control gives
+n ≳ 130 under independent arms; M1 measures the paired variance and records the count it
+derives, which is the ladder plan's floor —
```

---

## 2 · §5's tier-gate contract contradicts §2's yank rule · HIGH · §5, §2

§2 twice assigns the tier gate a duty: "the tier gate refuses new launches of it [a yanked
revision]" and "the tier gate refuses an uncertified revision exactly as it refuses a yanked one."
§5 says "The gate reads **four things and nothing else**" and lists refusal conditions that contain
neither. A fresh implementer building §5 verbatim ships a tier gate that launches yanked and
uncertified revisions — the §2 machinery (floors, certificates, disown-by-reach) then has no
enforcement point at launch. Make it a fifth input, not a footnote elsewhere.

```diff
-**Tier gate predicate.** The gate reads four things and nothing else: the skill's declared
-cost profile, the spawning budget (the meet above), the launch's hypothesis key and method
-identity (and its statement hash where a claim exists; §3, §4), and the launch's *ticket* —
+**Tier gate predicate.** The gate reads five things and nothing else: the skill's declared
+cost profile, the spawning budget (the meet above), the launch's hypothesis key and method
+identity (and its statement hash where a claim exists; §3, §4), the launch revision's
+self-test standing (certified and not yanked, §2), and the launch's *ticket* —
@@
-Tier 2 by more than one, when the declared cost exceeds the remaining budget, or when the
-required ticket is absent.
+Tier 2 by more than one, when the declared cost exceeds the remaining budget, when the
+required ticket is absent, or when the launch revision is yanked or holds no recorded
+self-test certificate.
```

---

## 3 · The formalization gate's axiom check has no named producer · HIGH · §7

§7(iii) "requires `#print axioms` ⊆ {propext, Classical.choice, Quot.sound}" and makes the
*permitted set* gate-bundle-owned — but never says **who emits the axiom list**. This matters
because §7(ii) names `leanchecker --fresh` as the checker, and `leanchecker` explicitly "does NOT
reject `sorryAx` or extra axioms" (`grounding/lean-checker-protocol.md:41`); the axiom check is a
separate step. If the list is emitted by the Solution module's own compilation, it is a number
produced by the party being gated — the exact failure §6(3) refuses for operation counts and §13
refuses for the verifier ("acceptance is affirmative, never residual"). One asymmetry, one gate,
silently fails open.

The gold-tier path is already safe: comparator does the axiom check internally
(`Axioms.lean:45`, PROPOSALS C1) and `landrun` is Linux-only, so the *ordinary* path is the exposed
one. (Verified: leanchecker's guarantees and comparator's internal check. Inferred: that
`Lean.collectAxioms` in a gate-owned module is the cheapest substitute — `lean-statement-linters-
vacuity.md:43` states "an axiom gate alone is `Lean.collectAxioms` plus a whitelist"; I have not
read its source.)

```diff
-    prelude, both inside the gate bundle and outside every worker's write path; the
+    prelude, both inside the gate bundle and outside every worker's write path; the
@@
-    (iii) requires `#print axioms`
-    ⊆ {`propext`, `Classical.choice`, `Quot.sound`}
+    (iii) computes the axiom set itself — a gate-owned module in the bundle imports the
+    Solution and reports `collectAxioms` over the Challenge's theorem names, so the list is
+    never read from output the Solution's own compilation emits — and requires it
+    ⊆ {`propext`, `Classical.choice`, `Quot.sound`}
```

---

## 4 · No milestone demonstrates the system doing research · HIGH · §13

Every "done when" in §13 tests *detection*: 30 plantings caught, 4 positive controls passed, fixtures
refused, chains unbroken. Not one tests *motion*. M0–M4 can all be green on a harness that has never
run an honest research loop end to end, and the failure that produces — a system that only ever says
no — is invisible to a planted corpus, because a gate that rejects everything catches every planting.
The positive controls at M1 are the right instinct but they are fixtures the implementer wrote, not
output the system found.

```diff
   `supersedes_refuted_review` and `null_control_pending` parks, the hash-chained log and its
   head checkpoint (§3, §4), the terminal-status invariant, the statement-review workflow
   that writes `review_verdict` nodes through the human path (§7), and the near-duplicate
   advisory routed to the human or to a `near_dup_review` park (Librarian routing arrives
   with the Librarian at M4).
+  *Honest-yield bar (M2, in addition to the fixtures above).* On a genuinely open small
+  subproblem chosen by the operator, an unattended run under a fixed Tier-0/1 budget must
+  produce: at least one REFUTED ledger entry whose `refutation_kind` is `measured` and whose
+  evidence node carries a ladder table with its A/A arm; at least one claim admitted to
+  STRONG-EMPIRICAL by `justify`; zero `Leaked` records; and zero admissions of any planted
+  fixture re-injected during the run. *Why:* a planted corpus measures only the false-accept
+  rate, and a harness that rejects everything scores perfectly on it. This bar measures the
+  other error, on output the implementer did not write.
```

---

## 5 · Verification escrow is reserved and never released · MED · §5, §7

§5: the tier gate "reserves the verification component from the grant at launch." §7: the auditor
funds re-runs "from the verification component escrowed at each node's launch." Nothing says the
escrow is ever *released*. Two consequences, both real: (a) a `Verifiable` node whose witness was
checked at admission holds its escrow forever, so a long run's usable budget monotonically shrinks
toward zero; (b) a `Replayable` Tier-2 node re-run at `justify` time consumes its escrow, and the
auditor's later uniform sample can then draw a node with nothing left to spend — which silently
degrades the achieved `bits` the auditor is supposed to publish, for a reason unrelated to rot.

```diff
-(what the node's replay grade and tier will cost under the §3 re-run policy); the tier gate
-reserves the verification component from the grant at launch and refuses a launch whose
-verification the remaining budget cannot cover.
+(what the node's replay grade and tier will cost under the §3 re-run policy); the tier gate
+reserves the verification component from the grant at launch, refuses a launch whose
+verification the remaining budget cannot cover, and releases the reservation to the granting
+branch when the node's §3 re-run policy is discharged or the node is disowned. The
+foundations auditor's sampled re-runs (§7) draw from a standing audit budget line the gate
+bundle names, never from a node's escrow, so a node already re-verified at `justify` time is
+still drawable.
```

---

## 6 · The ladder nonce may be reused across runs of one hypothesis object · MED · §6

§6(1): "the gate draws a nonce **after the hypothesis object is recorded**." The hypothesis object
is immutable and content-addressed; a rung that returns INCONCLUSIVE is re-run against the *same*
object. If the nonce is a function of the object — or simply not redrawn — the seeds are already
published in the first run's result table (§6(5)), and the second run's instances are known to the
claimant in advance. That is precisely the overfitting-a-fixed-input class §6(1) cites. One clause
closes it.

```diff
-committing its method — the gate draws a nonce after the hypothesis object is recorded,
+committing its method — the gate draws a fresh nonce at the start of each ladder run, after
+the hypothesis object is recorded and never derived from it, and never reuses a nonce across
+runs of the same object;
```

---

## 7 · Two small fixes · LOW · §13, §6

(a) §13's "observed draws span 20–220" contradicts the grounding it cites (11–220 over the `ellcard`
column, `pari-sage-toy-curve-backend.md:18–20`); since the sentence's whole point is that the sample
is too thin to be a profile, quoting it wrong is gratuitous.

(b) §6(3)'s clock cross-check ("the harness records CPU-seconds per trial") does not say over what.
If it is the trial process only, a method can spawn arithmetic into a child and the clock check goes
blind — the same hole the counter has, reopened one level down.

```diff
-  50 seeds per size before declaring one), with a BSGS-vs-SEA *algorithm* cross-check
+  50 seeds per size before declaring one; the recorded draws span 11–220), with a
+  BSGS-vs-SEA *algorithm* cross-check
@@
-The harness records CPU-seconds per trial beside the
-count,
+The harness records CPU-seconds per trial beside the count, summed over the trial's whole
+process tree, and a ladder-tested method's allow-list permits no process spawn;
```

---

## Sound and needing nothing

§0, §1, §8, §9, §14, §16 — I would change no word. §7's derived-tag lattice and the
`review_verdict` node are the strongest part of the document: `justify` returning a typed
justification rather than a boolean, and the tag being a derived column, is what makes the taxonomy
mechanical rather than declarative. §3's attempt-append model (a recipe key names a computation,
never a result slot) is correct and load-bearing; do not simplify it.

---

**(a) The three I would stake the most on:** #1 (inverted KEEP predicate — the plan is wrong, and
wrong in the direction of accepting a bad claim), #2 (tier gate contract contradiction), #3 (axiom
list with no gate-owned producer).

**(b) Where the framing is wrong.** The plan has become a fabrication-prevention system with a
research system implied. Roughly 85 % of its text specifies how a claim is refused; almost none
specifies how a claim is *produced*, and no milestone measures whether any ever is (#4). The second,
related symptom is form: §2's skill-identity paragraph and §3's retention paragraph are each a
single ~500-word sentence with six levels of subordinate clause. The plan's own bar is "a fresh
implementer could build it from the text," and at that density they cannot — the §5/§2 contradiction
in #2 and the sign error in #1 both survived three review rounds because the sentences are too long
to hold in one reading. Splitting the mega-sentences into numbered clauses is not cosmetics here; it
is the cheapest available defect-detection.

**(c) Facts I would need that the plan does not state.** (i) `leanchecker --fresh` wall time on a
mathlib-importing Challenge — OPEN at `lean-checker-protocol.md:53`, and it sizes the entire M1
fixture corpus. (ii) The paired variance of the ladder's ratio estimator under common instance
streams — it decides whether the trial-count floor is ~130 or ~40, and therefore whether the 50-bit
rungs are Tier-1 at all. (iii) Whether macOS `uappnd` binds against a non-owner writer — the plan
names this as an M0 grounding item but M0's done-when never demonstrates it, and the checkpoint is
the only thing standing between the orchestrator and a truncated ledger. (iv) Who the human is, and
their availability: before M4, statement review, null-control re-measurement, near-dup adjudication
and expert sign-off are all human, and the plan sets no bound on that queue.
