# Review of plan-r0.md

The spine is sound: §0, gates, calibration lattice, substrate, ladder, and the honest baseline are coherent and mutually reinforcing. Below are only changes that fix contradictions, close gameable holes, or sharpen implementability. Sections not named are fine as written.

---

### 1. Forced pivot must park, not kill
· **severity:** HIGH · **§4 Orchestrator / §15 P3 / §9**

**Rationale.** P3’s “kills the worst half of branches regardless of agent opinion” collides with §4’s terminal taxonomy (`refuted | parked | promoted | withdrawn`), §4’s auto-revive-on-blocker-clear, and §9’s “never give up = always a next legitimate action.” A yield-based kill is not a refutation; treating it as terminal either (a) invents a backdoor status the ledger doesn’t know, or (b) mis-tags low-yield work as `REFUTED` and permanently blacklists it by hash—exactly the failure §3’s teeth are for. Force-**park** with an explicit, clearable blocker preserves persistence, keeps hash-blacklist sacred, and still stops rabbit-holing.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4 Orchestrator
- bandit allocation over active branches (fund yield, prune stalls, revive parked,
- force periodic pivots so it can't rabbit-hole)
+ bandit allocation over active branches (fund yield, park stalls, revive parked,
+ force periodic pivots so it can't rabbit-hole). A pivot never writes REFUTED:
+ it writes PARKED with blocker ∈ {low_yield_pivot, budget_preempt, human_park},
+ which auto-revives under the same rule as any other blocker.
@@ §15 P3
- (i) The forced pivot as a periodic, mechanical reset that kills the worst half
- of branches regardless of agent opinion;
+ (i) The forced pivot as a periodic, mechanical reset that force-parks the worst
+ half of *active* branches (blocker=low_yield_pivot) regardless of agent opinion;
+ REFUTED remains evidence-only;
```

---

### 2. Near-duplicate → Librarian before Librarian exists
· **severity:** HIGH · **§4 ledger preflight vs §13 M2/M4**

**Rationale.** §4 routes near-duplicates to the Librarian; M2 ships “near-duplicate advisory”; Librarian arrives at M4. As written M2 is unimplementable or silently no-ops the route. Also SimHash/embeddings at M2 pull a retrieval stack the plan itself defers to P7/M4, and embeddings sit next to already-rejected “similarity as authority” failure modes. Keep M2 exact-hash + optional cheap SimHash advisory to **human/park**; bind fuzzy routing to Librarian at M4.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4 ledger preflight
- A near-duplicate signal (SimHash or embedding similarity to a REFUTED entry) is
- advisory only: it routes the proposal to the Librarian, who must state the
- difference in writing; it never sets a status.
+ A near-duplicate signal is advisory only and never sets a status.
+ Pre-M4: optional SimHash-over-hypothesis-text flag → route to human review or
+ auto-PARK with blocker=near_dup_review (no embedding model required).
+ M4+: same signal routes to the Librarian, who must state the difference in
+ writing before funding; embeddings only inside the P7 retrieval stack, still
+ advisory.
@@ §13 M2
- and the near-duplicate advisory.
+ and the near-duplicate advisory routed to human/park (Librarian routing is M4).
```

---

### 3. Challenge-module authorship (statement provenance)
· **severity:** HIGH · **§7 Green Lean / statement-level review**

**Rationale.** “The gate owns a Challenge module” does not say who **authors** the statement. If the Formalizer/Prover supplies Challenge and Solution, the strongest fabrication class the section fears (verified-but-weaker-statement) is available in one step; human review becomes a load-bearing single point without a mechanical chain of custody. Fix: Challenge is compiled only from an already-admitted **claim statement node** (content-addressed, calibration-tagged), by a gate-side renderer the Formalizer cannot write; Solution may only target that hash; mismatch fails closed. This is provenance, not a new gate.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §7 "Green Lean"
- The gate owns a Challenge module holding the statement; the Formalizer submits
- a Solution module;
+ The gate *compiles* the Challenge module from a single content-addressed claim
+ statement node already in the substrate (renderer + pinned prelude live in the
+ gate write-path, outside every worker). The Formalizer may not create or edit
+ Challenge text; it submits a Solution module targeting `challenge_hash`;
+ Solutions that do not target the gate-compiled hash fail closed before kernel
+ replay.
+ (iv) ... identical over the statement's transitive constant closure ...
+ plus Solution.challenge_hash == gate-compiled challenge_hash.
```

---

### 4. Slim M0 — tag lattice is M1
· **severity:** HIGH · **§13 M0 vs M1 / anti-over-engineering**

**Rationale.** M0 “done when” is one skill → one hashed node on a 40-bit curve. The schema bullet also demands the full §7 `justify` lattice, append-only tag history, certificate slot, GC roots, cache bits, replay grades. That is the epistemic core of M1 (Prover/Skeptic/ladder), not a substrate slice. Overloaded M0 delays the contact-with-reality the anti-over-engineering paragraph correctly wants. M0 keeps store mechanics + a **tag column stub** (`SPECULATION` default, no upward moves); `justify` + history + PROVEN/STRONG-EMPIRICAL derivation ship with the gates that alone can feed them.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §13 M0 schema includes
- the §3 key construction and cache bits, the replay grade and certificate slot,
- the §7 derived-tag rule (`justify`) with append-only tag history, and a GC
- roots table.
+ the §3 key construction and cache bits, the replay grade and certificate
+ *slot* (unused until a verifiable skill exists), a GC roots table, and a
+ claims.tag column defaulting to SPECULATION with no upward transitions
+ implemented yet. The §7 `justify` lattice, append-only tag history, and
+ derived PROVEN / STRONG-EMPIRICAL rules are M1 deliverables—they land with
+ the ladder and formalization gate that are their only legal producers.
@@ §13 M1
+ Adds `justify` + append-only tag history wired to ladder/formalization
+ evidence nodes; planted tests include “statistical evidence cannot justify
+ PROVEN” and “weaker premise in the transitive closure blocks PROVEN.”
```

---

### 5. Define a minimal gate-outcome reward until M3 decides
· **severity:** MED · **§5 vs §15 P3 / rejected e-value-in-reward**

**Rationale.** §5 states allocation currency **is** expected information-per-compute-dollar; P3 admits the mechanics are undecided and branch-level bandits are unvalidated; e-values-as-reward are already rejected. As written an implementer either invents a multiplicative “evidence” score (forbidden) or leaves M3’s bandit with no legal reward. Pin a dumb, gate-only proxy now; let P3 replace it only if the proxy fails the “reallocates off a stall” bar.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §5
- **Allocation currency is expected information per compute-dollar**, not raw
- yield — a cheap experiment that halves a conjecture's probability outranks an
- expensive one that nudges a bound.
+ **Allocation currency (M3 default proxy, replaceable under P3):** gate-outcome
+ points per measured compute-dollar, with fixed schedule
+ `{REFUTED_by_gate: +1.0, ladder_REJECT: +1.0, ladder_INCONCLUSIVE: +0.2,
+  ladder_KEEP: +1.5, PROVEN_lemma: +2.0, PARKED: 0, repro_fail: +0.5,
+  Leaked_terminal: −1.0}`, always divided by measured cost, never by a model
+ probability. No e-value, posterior, or similarity term enters the score
+ (rejected class). “Info-per-dollar” in prose means this proxy until P3
+ evidences a strictly better gate-only alternative against M3’s done-when bar.
```

---

### 6. Ladder: out-of-sample size prediction
· **severity:** MED · **§6**

**Rationale.** Fitting mean ops at 30/40/50/60 to a claimed exponent still allows curves that match on a short window and diverge above it—the exact “proof-shaped / chart-shaped” miss the ladder exists to catch. Require the model fitted on sizes ≤ B to predict size B+10 inside the A/A band before KEEP. Cheap; no new dependency; tightens the dominant anti-fabrication device without touching calibration boundaries.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §6 Protocol (2)/(4)
+ (2b) Out-of-sample size check: fit the claimed cost model on trials at sizes
+ ≤ B (e.g. 30/40/50); the model’s predicted mean ops at B+10 (e.g. 60) must
+ land inside the A/A-derived decision band of the *measured* mean at B+10.
+ Failure ⇒ REJECT even if in-sample fit looks clean. The fit-on / hold-out
+ split is fixed in the ladder plan, not chosen by the worker.
```

---

### 7. Human-absent profile (tier cap + no-go escalation)
· **severity:** MED · **§8 / §10 / §7 proportional scrutiny**

**Rationale.** §10 makes taste the bottleneck and human-anchors expensive calls, but never defines the system’s contract when no human is present—the steady state of an autonomous harness. Without it the orchestrator can burn Tier-2 on no-go-violating branches and queue “broke ECDLP” claims indefinitely. Not a new gate: a **profile** that tightens existing routers when `human_available=false`.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §10
+ **Human-absent profile (default when no operator session is open):**
+ (i) hard cap at Tier-1 spend (Tier-2/3 require a non-expired human/expert
+ waiver); (ii) any attack that fails to answer §8’s three evasions is
+ auto-PARKED with blocker=nogo_unanswered rather than merely flagged;
+ (iii) claims whose proportional-scrutiny class is “target break” or above
+ stay non-promotable and surface on the human queue; (iv) the orchestrator
+ still runs—reframe, refute, ladder, formalize lemmas, map dead ends.
+ Profile is config next to the gate plan, outside the orchestrator write path.
```

---

### 8. Two-implementation disagreement is a substrate record
· **severity:** MED · **§2 Tier-0 arithmetic skills**

**Rationale.** “Require agreement or raise” leaves the branch, cache, and claim in an undefined state—the kind of hole §4’s terminal-status invariant is meant to close. Disagreement is itself evidence (tool bug vs math bug) and must not be retry-looped away.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §2
- where two independent implementations exist (PARI vs Sage), require
- agreement or raise.
+ where two independent implementations exist (PARI vs Sage), require
+ agreement; on disagreement the skill returns status=DISAGREE (not OK ⇒ not
+ cached), writes both transcripts and digests to a substrate node, and the
+ caller must park or refute—silent retry with a third tool is forbidden
+ without an attributed waiver.
```

---

### 9. M1 done-when: fixed planted corpus
· **severity:** LOW · **§13 M1**

**Rationale.** “Caught every time” is not a test suite. Enumerate the minimum corpus so a fresh implementer knows when to stop and so the gate self-test discipline in §4 has teeth at milestone scope.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §13 M1 Done when
- a deliberately-planted false "advance" is caught every time.
+ every fixture in the M1 planted corpus is caught, minimum set:
+ (a) BSGS-beating claim whose ops at 50-bit are ≥ generic rho;
+ (b) correct-ops claim that fails xP==Q on a fresh ladder instance;
+ (c) Lean Solution with sorryAx / extra axiom;
+ (d) Lean Solution proving a strictly weaker statement than Challenge;
+ (e) small-numbers pattern that dies under the counterexample hunt;
+ (f) claim seeking STRONG-EMPIRICAL with no repro node.
+ “Done when” = 100% catch on this list under cold cache (skip_cache_lookup).
```

---

### 10. Reduction edges (light)
· **severity:** LOW · **§4 state layer / §9 progress**

**Rationale.** ECDLP work is reduction-heavy (full DLP → low-HW → structured scalars). Parent/child hypotheses bury “A reduces to B” in prose. A single optional edge type makes progress legible to the bandit and the human without a new subsystem. Skip if you want zero M3 surface growth—parent pointers can encode it by convention.

```diff
--- a/plan-r0.md
+++ b/plan-r0.md
@@ §4 branch tree
- branch tree (`{id, parent, hypothesis, status∈{...}, priors, effort, yield, blocker?}`)
+ branch tree (`{id, parent, hypothesis, status∈{...}, priors, effort, yield,
+ blocker?, reduces_to?: branch_id}`). `reduces_to` is advisory structure for
+ allocation and UI; it does not inherit tags or bypass gates—the target’s
+ evidence still has to earn its own calibration class.
```

---

## Sound as written (no change)
§0; §1; §3 key/canonicalizer/cache-bits/GC/hash-chain; §6 quantitative bars and fresh instances; §7 tag derivation, statistical-monitors-never-promote, skeptic isolation, disagreement-not-vote; §11 compounding assets; §12 borrowed-mechanism constraint; §14 baseline; §15 P1/P2/P4/P5 drop-if-it-doesn’t-bind posture; operator defaults.

---

### (a) Three to stake on
1. **#1 park-not-kill** — real contradiction with §0/§4/§9; cheap fix.  
2. **#3 Challenge authorship** — closes the highest-value fabrication path the formalization gate currently leaves open.  
3. **#2 / #4 (tie)** — M2/M4 Librarian contradiction and M0 scope; both decide whether the build order is executable.

### (b) Framing that may be wrong
Harness-before-skills is right for *epistemic* safety, but the plan’s implicit bet is that process machinery is the long pole. For publishable ECDLP-adjacent increments, the long pole is more likely a **versioned skill pack** (rho/kangaroo with DP certificates, summation polynomials, small Gröbner, known-attack reimplementations as negative-result generators). M0’s one exemplar is correct; absence of an explicit **M2.5 / M3 skill-library milestone** with its own done-when risks a beautiful orchestrator scheduling an empty capability surface. Consider one milestone whose bar is “N skills with self-tests + cost profiles, including one negative-result producer that populates §11 from a known obstruction,” not more bandit math.

Secondary frame risk: §5/P3 treat allocation as a research problem worthy of e-processes and martingales. Given unvalidated branch-level bandits, a boring priority queue + force-park + human taste may beat a “smart” bandit for a long time—P3 should be allowed to **drop the bandit**, not only tune it.

### (c) Facts the plan does not state (needed before locking more mechanism)
- Authoritative writer of claim statement nodes (human-only vs Reframer-with-human-ratify vs panel-propose).  
- Expected human duty cycle (hours/week) and max Tier-1 spend between sessions.  
- Concrete first open subproblems on the queue (not just the 254-bit north star).  
- Whether Magma is ever in-scope or PARI/Sage is a hard ceiling.  
- Target skill inventory for the first research-useful run (names + tier + self-test sources).  
- Single-operator vs multi-expert sign-off path for “target break” scrutiny class.