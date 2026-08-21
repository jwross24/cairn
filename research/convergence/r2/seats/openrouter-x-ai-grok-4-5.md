# Plan review (plan-r1.md)

The spine is sound: §0, gate bundle immutability, derived tags, substrate attempts-not-slots, ladder-as-anti-fabrication, and M0-first build order cohere. Below are only changes that fix contracts, bypasses, or untestable done-whens. Several large sections (§0–2, §8–9, §14, §16) need nothing structural.

---

### 1. Split ladder verdicts — break Tier-2 ↔ KEEP deadlock  
**Severity:** HIGH · **§5, §6**

**Rationale:** KEEP requires the 60-bit hold-out (§6.2b). That rung is Tier-2 by cost. The Tier-2 ticket for an algorithmic claim *is* a KEEP table (§5). A fresh implementer cannot admit the hold-out run without already having KEEP, and cannot get KEEP without the hold-out. The ≤50-bit distribution work is the real cheap gate; 60-bit is extrapolation under budget, not the admission ticket.

**Diff:**
```diff
--- a/plan §5 Tier gate predicate
+++ b/plan §5 Tier gate predicate
- for Tier 2 on an algorithmic claim the ticket is a ladder result table with
- verdict KEEP (§6);
+ for Tier 2 on an algorithmic claim the ticket is a ladder result table with
+ verdict KEEP-PROVISIONAL (§6) — ≤50-bit distribution rungs + A/A band only;
+ Tier 3 (and STRONG-EMPIRICAL promotion of an asymptotic cost model) require
+ full KEEP, which adds the 60-bit hold-out under an already-granted Tier-2 budget;

--- a/plan §6 Protocol (2)/(2b)/(5)
+++ b/plan §6 Protocol (2)/(2b)/(5)
+ Verdicts (fixed in the ladder plan, gate bundle):
+ - REJECT / INCONCLUSIVE — as today on the ≤50-bit band and refutation floor.
+ - KEEP-PROVISIONAL — ≤50-bit CI clears the rho band and memory band; method
+   recovers x on all required trials. This is the Tier-2 admission ticket only.
+   Tag ceiling remains CONJECTURE until hold-out (or explicit non-asymptotic scope).
+ - KEEP — KEEP-PROVISIONAL plus 60-bit completion (≥10 fresh recoveries) and
+   in-band out-of-sample prediction of the pre-registered model. Required for
+   STRONG-EMPIRICAL on the cost model and for any Tier-3 request built on it.
+ The 60-bit rung is never itself a Tier-1 self-ticket; it runs only with Tier-2
+ budget granted on KEEP-PROVISIONAL.
```

---

### 2. Enforce cost profiles at runtime (close tier-gate bypass)  
**Severity:** HIGH · **§5 (and pointer in §4 gate layer)**

**Rationale:** The tier gate admits on *declared* profile + ticket. Measured overspend is only a strategy alarm (P4), “never a gate.” A skill that declares Tier-1 and runs Tier-2 wall-time/core-hours skips the ticket that “almost nothing” is supposed to skip—the exact failure cheap-before-expensive is meant to stop. Declaration must be a binding ceiling with a mechanical breach status, not an estimate honored on the honor system.

**Diff:**
```diff
--- a/plan §5 Mechanism / Tier gate
+++ b/plan §5 Mechanism / Tier gate
  Measured cost is compared against the declared profile; a persistent mismatch
- is a strategy-layer alarm (§15 P4), never a gate.
+ is a strategy-layer alarm (§15 P4). Separately, every launch carries a hard
+ spend ceiling = declared profile × slack (slack ∈ gate bundle, default 2×
+ time and 2× peak memory). The harness meters the worker (cgroup/process
+ budget or equivalent). Breach ⇒ kill; attempt status = BUDGET_EXCEEDED;
+ status ≠ OK ⇒ never cached; output is inadmissible as a tier ticket or as
+ justify() evidence. Under-declaring cannot purchase a higher tier. P4 alarms
+ still fire on chronic near-ceiling spend that does not breach.
+ *Why:* admission-time tier checks on self-declared cost are fail-open under
+ "never give up" pressure; the ceiling makes the declaration a gate input.
```

**Adoption bar:** improves tier gate + substrate attempt integrity. Cost: OS metering, one status enum, bundle constant. Evidence: CONJECTURE (standard resource quarantine; no need for e-values). Does not edit truth or dissolve gates—adds enforcement.

---

### 3. M1 corpus needs positive controls  
**Severity:** HIGH · **§13 M1**

**Rationale:** Done-when requires “no matched true advance is rejected,” but (a)–(i) are all planted failures. A harness that rejects everything passes every negative fixture and fails the true-advance clause with no failing test. Same shape as a gate without a must-PASS fixture (§4).

**Diff:**
```diff
--- a/plan §13 M1 Done when
+++ b/plan §13 M1 Done when
  every fixture in the M1 planted corpus is caught under a cold cache
  (`skip_cache_lookup`), INCONCLUSIVE counting as an escape, and no matched true
  advance is rejected; minimum corpus, ≥ 30 plantings across it: (a)…(i)…
+ ; plus ≥ 6 positive controls that must PASS (not merely "not reject"):
+ (j) plain rho_dp on gate instances at 30/40-bit with pre-registered ~1.25√n
+     model → KEEP-PROVISIONAL (or tier-appropriate pass) and xP==Q;
+ (k) bsgs meeting its known cost band on the same instance stream;
+ (l) a minimal Lean Solution of a Challenge with exact statement match, axioms
+     ⊆ allowed set, no sorryAx;
+ (m) a reproducible Tier-1 measurement with repro node admitted to CONJECTURE
+     or STRONG-EMPIRICAL per justify() rules;
+ (n) a deliberate counterexample hunt that correctly kills a false small-numbers
+     pattern (hunt succeeds = gate pass);
+ (o) a null no-go declaration path on a non-target subproblem that must not
+     inflate scrutiny.
+ Scores reported as (caught plantings / plantings) and (passed controls /
+ controls); either ratio below 1.0 fails M1.
```

---

### 4. Ledger preflight: range-subset and method-identity closure  
**Severity:** MED · **§4 ledger / §3 hypothesis key**

**Rationale:** Hypothesis keys drop free text (good) but hash declared parameter ranges. Widening/narrowing ranges or renaming method parameters mints a new key and re-funds work REFUTED on a superset/subset family. Near-dup SimHash is advisory and text-based, so it misses structured range games. Without a structural preflight, REFUTED teeth are cosmetic under orchestrator pressure to keep moving.

**Diff:**
```diff
--- a/plan §4 Ledger preflight
+++ b/plan §4 Ledger preflight
  `Blocked` = the hypothesis key (§3) matches a REFUTED entry whose retry
  predicate is unmet;
+ OR an existing REFUTED entry with the same target family + method identity
+ whose declared parameter region *covers* this proposal's region (axis-aligned
+ range inclusion on numeric params; equality on categorical params) and whose
+ retry predicate is unmet — subset re-probes do not mint a clean key;
+ OR same method identity + overlapping region with only a cost-model constant
+ tweak and no new falsifiable claim field (routes `RequiresNullControl` or
+ human review, not silent Allowed).
  `Allowed` = no match, or a match whose retry predicate is met…
+ Coverage edges are recorded on the new branch when Allowed via retry.
```

Does not use embeddings or majority vote; pure typed inclusion on the object already hashed.

---

### 5. Ladder commit–reveal as a gate step  
**Severity:** MED · **§6 Protocol (0)–(1)**

**Rationale:** “Entropy the worker never sees before committing its method” is the right anti-overfit rule but is not a checkable step sequence. Implementers will pass seeds in the same dispatch record. Make commit–reveal substrate-visible like other gates.

**Diff:**
```diff
--- a/plan §6 Protocol (0)(1)
+++ b/plan §6 Protocol (0)(1)
  (0) The claim pre-registers its cost model … before any rung runs;
+     the hypothesis/claim statement hash is written to the substrate and named
+     in the ladder dispatch record *before* step (1); the ladder refuses to
+     start if the commit is missing or differs from the funded branch hypothesis.
  (1) The ladder generates its own instances…
+     Instance-maker entropy is drawn only after the commit receipt exists;
+     the instance stream seed is gate-owned, stored in the gate-run record, and
+     absent from the worker tool allow-list. A worker-supplied instance list is
+     a planted-failure fixture that must FAIL the ladder gate self-test.
```

---

### 6. Name the conjecture Tier-2 ticket artifact  
**Severity:** MED · **§5, §7 strong-law**

**Rationale:** Algorithmic Tier-2 tickets have a concrete table shape. Conjecture path says only “counterexample-hunt record of §7,” with no fields, trial counts, or status. That is not implementable at the same rigor as the ladder ticket and invites ad-hoc orchestrator PDFs.

**Diff:**
```diff
--- a/plan §5 Tier gate / §7 strong law
+++ b/plan §7 (strong law) + §5 pointer
+ Counterexample-hunt record (substrate node, Tier-2 ticket for conjecture-class
+ branches): {statement hash, sampling distribution D (content-addressed),
+ pre-registered hunt budget (n, family bounds), seed commit receipt, per-trial
+ outcomes, any counterexample certificate with verifier status, verdict ∈
+ {SURVIVED, KILLED, BUDGET_EXHAUSTED_INCONCLUSIVE}, A/A or scramble null when
+ the claim is distributional}. SURVIVED under the declared budget is the ticket;
+ KILLED writes REFUTED/PARKED per ledger rules; INCONCLUSIVE is not a ticket.
+ Tag ceiling without this node: CONJECTURE at most; never STRONG-EMPIRICAL.
```

---

### 7. M4 store concurrency contract (no new DB)  
**Severity:** MED · **§3 Store, §13 M4**

**Rationale:** M4 “parallel tracks” on a single SQLite substrate without a writer contract will lose attempts or interleave chain heads. Plan already rejected franken-DBs and Temporal; still need a boring concurrency rule before scale-out is “done.”

**Diff:**
```diff
--- a/plan §3 Store / §13 M4
+++ b/plan §3 Store
+ Concurrency (M0–M3): one writer connection, WAL mode, busy-timeout; workers
+ are subprocesses that return artifacts to the harness writer — they do not
+ hold substrate write capabilities (mirrors gate-bundle read-only discipline).
+ M4 done-when adds: N≥4 parallel tracks under that contract with zero broken
+ hash-chain heads and zero lost attempt rows in the M4 stress fixture; if the
+ fixture fails, the fix is queue depth / batching / multi-process write proxy,
+ not a new database dependency.
```

---

### 8. Skill self-test failure ⇒ automatic yank  
**Severity:** LOW–MED · **§2**

**Rationale:** Floor + golden certificate are defined; the consumer on regression is not. A skill that fails its corpus mid-campaign should not keep minting OK tickets until a human notices.

**Diff:**
```diff
--- a/plan §2 Skill identity
+++ b/plan §2
+ On self-test failure (floor miss, certificate mismatch, double-run divergence):
+ skill revision is YANKED — new launches refused, in-flight attempts finish as
+ AuditOnly/inadmissible, salt optional for poison namespace, ledger alarm. Only an
+ attributed new revision with a fresh certificate may clear the yank. *Why:*
+ without yank, §2 is documentation; with it, skill identity is a live gate input.
```

---

### 9. Clarity only — don’t advertise info-per-dollar as current  
**Severity:** LOW · **§5**

**Rationale:** Body states allocation currency *is* expected information per dollar, then says until M3 it is gate-outcome/cost. Readers will implement a fictional info estimator.

**Diff:**
```diff
- **Allocation currency is expected information per compute-dollar**, not raw yield
- — …; until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome
- reward per measured cost…
+ **Allocation target (M3+):** expected information per compute-dollar, not raw
+ yield. **M0–M2 / default until P3 decides:** gate-outcome reward per measured
+ cost only; no model probability, e-value, posterior, or similarity term.
```

---

### Sound as written (no change)
§0; §1; §8 no-go presence/consumer split; §9 persistence vs honesty; §10 human-absent = block; §12 borrow-mechanisms-not-code; §14 baseline; §15 P1–P7 deferral shape; §7 derived tags / e-values never promote; challenge/solution Lean protocol; attempt-append substrate.

---

### (a) Three to stake on
1. **#1 KEEP-PROVISIONAL vs KEEP** — without it M1/M2 ladder work cannot lawfully reach its own hold-out.  
2. **#2 runtime budget ceiling** — otherwise declared tiers are advisory under the exact pressure model §0 assumes.  
3. **#3 M1 positive controls** — otherwise M1 “done” can ship a universal rejector.

### (b) Framing concerns
- **Progress = gate outcomes** (until M3) will bias toward *easy, frequent gate passes* (toy refutations, trivial lemmas) unless problem-queue taste (#10) is truly in the loop early. Not wrong, but M3’s bar should explicitly include “does not starve slow high-payoff branches.” The plan underweights that failure mode vs stall-withdrawal.  
- **Ladder is ECDLP-shaped.** For non-algorithmic subproblems the conjecture ticket (#6) is load-bearing; treating the ladder as *the* anti-fabrication story slightly mis-frames the harness as attack-centric. Prefer “every claim class has a named cheap ticket artifact.”  
- No proposal here weakens §0/gates/taxonomy/baseline.

### (c) Facts the plan doesn’t state (needed to implement, not to redesign)
- Operator host: Linux cgroup + `landrun` available for M1 gold path, or macOS-only dev with accepted sandbox gap.  
- Whether 60-bit was *intended* as post-admission (this review assumes yes given cost text).  
- Write rate target for M4 parallel tracks (to size the single-writer fixture).  
- Default budget slack (2×?) and whether wall-time, core-seconds, or both bind.  
- Who may attribute skill yank clearances and salts (human-only vs orchestrator request + human grant, mirroring waivers).