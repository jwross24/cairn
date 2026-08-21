# Plan review (plan-r3.md)

§0, §1, §6, §8–§9, §14, and the gate-bundle / pin discipline in §4 are sound; I am not revising them. Below are only places with a real contract hole, fail-open, or milestone gap.

---

### 1. Yank reach must default to the full revision  
**Severity:** HIGH · **§2 (skill yank)**

**Rationale.** As written, a yank names “the revision, plus a **declared** input range where the fault is input-dependent.” The party best able to narrow that predicate is the same one that shipped the bad revision (or an orchestrator under “never give up” pressure). A narrow reach leaves poisoned attempts cacheable and `justify`-able outside the predicate — silent fail-open at the tier where refutations live. Component fixed: skill yank / disown (§2–§3). Cost: negligible (default predicate is one field). Evidence: fail-closed defaults are the plan’s own standard elsewhere (uncertified ≡ yanked; waiver cannot satisfy admission) — **CONJECTURE** as applied here, pattern **STRONG-EMPIRICAL** in-plan. Does not touch §0 or gates.

```diff
- the yank record names the fault's reach as a predicate over recipe-key fields (the
- revision, plus a declared input range where the fault is input-dependent) and every
- attempt inside that reach is disowned (§3)
+ the yank record's reach **defaults to the entire implementation revision** (all
+ recipe keys naming that revision). A narrower predicate (input range, parameter
+ slice) may only be applied by an attributed human ruling recorded beside the yank;
+ workers and the orchestrator may propose a narrowing, never install one. Every
+ attempt inside the effective reach is disowned (§3). *Why:* a self-narrowed yank
+ is a gate that fails open on the un-named slice.
```

---

### 2. Preflight must treat solved hypotheses as non-re-fundable  
**Severity:** HIGH · **§4 (ledger preflight)**

**Rationale.** `Blocked` is only REFUTED (plus retry / null-control / supersedes paths). A `KEEP` / `PROVEN` / `promoted` hypothesis can be funded again forever. With M3 reward = gate-outcome per cost, the dominant policy is to re-ladder known speedups (control (j) forever) rather than explore — the exact rabbit-hole forced pivots cannot fix, because yield is high. Component: dead-end ledger / preflight. Cost: one entry kind + status; no new dependency. Evidence: same structural-key teeth the plan already uses for REFUTED — **CONJECTURE** that promotion keys collide the same way (mechanism is the existing hypothesis key). Strategy only; epistemics unchanged.

```diff
  *Ledger preflight:* before any branch is funded the ledger answers `Allowed | Blocked
- | RequiresNullControl`. `Blocked` = the hypothesis key (§3) matches a REFUTED entry
- whose retry predicate is unmet, or the proposal's declared parameter region contains a
- measured parameter point at which a REFUTED entry records the same method identity
- failing the same cost model ...
+ | RequiresNullControl | AlreadySettled`. `Blocked` = <unchanged REFUTED rules>.
+ `AlreadySettled` = the hypothesis key matches an entry with
+ `decision ∈ {KEEP, KEEP_IN_SAMPLE (only if the launch purpose is not the scoped
+ 60-bit completion), SURVIVED, PROVEN, promoted-equivalent}` whose retry/amendment
+ predicate is unmet; the proposal is parked with blocker `already_settled` (not
+ REFUTED — success is not deadness). Amendment is a new hypothesis object with
+ `supersedes` and an attributed statement of what semantic field changed (same path
+ as `supersedes_refuted_review`). *Why:* REFUTED stops known failures; without
+ `AlreadySettled`, gate-outcome reward re-buys known successes.
```

(Wire `AlreadySettled` into the terminal-status / negative-results story as a settled success pointer, not a blacklist.)

---

### 3. Cost-profile coherence and anti-inflation ceiling  
**Severity:** HIGH · **§5 (tiers & budget)**

**Rationale.** Grant = multiplier × **declared** expectation. Over-declare inside a tier → more wall clock; under-declare → `BUDGET_EXCEEDED` (safe). Cost can force Tier-3 at ~10³ core-hours, but nothing refuses `expected tier = 1` with production cost in the “hours / many cores” band, so the cheap-before-expensive ticket is skippable by self-report. Component: tier gate + budget ceiling. Cost: pure validation rules + tier max table in the gate bundle. Evidence: plan already states admission on self-declared cost is fail-open under §1 — **CONJECTURE** fix; consistent with ceiling rationale already in §5. No strategy→truth path.

```diff
  every skill declares its **cost profile** (complexity in inputs, expected
- tier) as part of its typed interface
+ tier) as part of its typed interface. The profile is **coherent** or the tier
+ gate refuses at dispatch: (i) `expected_tier` must equal the tier implied by
+ production cost under the bundle's boundary table (T0/T1/T2/T3 maxima — same
+ object as §5's prose boundaries, versioned in the gate bundle); (ii) a profile
+ whose production cost exceeds the tier maximum is re-tiered upward (the existing
+ ≥10³ core-hours ⇒ T3 rule is the T2→T3 edge of that table); (iii) the runtime
+ ceiling is `min(multiplier × declared_expectation, multiplier × tier_max_production)`
+ so inflation cannot buy more than the tier admits. Measured≫declared remains a
+ §15 P4 strategy alarm; measured≫tier_max is `BUDGET_EXCEEDED` and a yank-class
+ signal on the revision (persistent mismatch), never a claim-tag input.
```

---

### 4. No-go evasion review needs a typed gate input  
**Severity:** MED · **§8 + §5 ticket rule**

**Rationale.** Presence of a declaration is mechanical; clearing “has been reviewed” is prose. The tier gate must read a node (as it does for `review_verdict`), or “reviewed” becomes an orchestrator-settable bit. Component: no-go consumer path / tier gate. Cost: one small immutable node type + human-path write (same as waiver/verdict). Evidence: same pattern as `review_verdict` — **PROVEN-in-source** as pattern reuse in-plan. Does not soften §8 content review.

```diff
- until the declaration exists and has been reviewed
+ until the declaration exists and a `nogo_review` node
+ `{hypothesis hash, declaration hash, reviewer, verdict ∈ {accept_for_tiering,
+ reject, needs_revision}, gate-bundle hash, time}` is recorded on the human path
+ (Skeptic may attach notes; only human/role identity writes `accept_for_tiering`).
+ The tier gate's “flag cleared” predicate reads that node; absence ≡ flagged.
+ `accept_for_tiering` is not a claim tag and does not satisfy proportional
+ scrutiny's top-class obligations — it only restores ordinary ticket eligibility.
```

---

### 5. M3 done-when is too thin for the contract it freezes  
**Severity:** MED · **§13 M3**

**Rationale.** M3 decides allocation and whether a bandit exists, but done-when only checks that stalls lose funding. It does not lock the §4 invariant that pivots never write REFUTED, nor that high-yield novel branches are not starved by settled re-runs (proposal 2), nor crash-resume. Component: M3 acceptance bar. Cost: more fixtures, no runtime surface. Evidence: plan’s own “decides … against that bar” — **SPECULATION** on numbers; structural fixtures are free.

```diff
  *Done when:* on ≥ 20 seeded runs each containing a
  stalled branch — ... funding is withdrawn from it within `m` ticks unaided,
- with `k` and `m` pinned in the M3 test plan.
+ with `k` and `m` pinned in the M3 test plan; **and** every forced pivot /
+ stall action in those runs writes `PARKED` with
+ `blocker ∈ {low_yield_pivot, budget_preempt}` and zero `REFUTED` rows from the
+ orchestrator path; **and** on ≥ 20 runs containing one settled-KEEP hypothesis
+ and one novel active branch, the settled key receives no new Tier-1+ grant
+ after `AlreadySettled` (prop. 2) while the novel branch still receives grant
+ within `m` ticks; **and** a crash mid-tick resumes without double-applying a
+ completed step (P3 tick table). Decides allocation mechanics ...
```

---

### 6. Rename “info-per-dollar” until it is defined  
**Severity:** LOW · **§5**

**Rationale.** Currency is explicitly gate-outcome / measured cost with no probability term. Calling it “expected information per compute-dollar” invites later insertion of model probabilities into the reward (already rejected shape). Component: allocation wording. Cost: none.

```diff
- **Allocation currency is expected information per compute-dollar**, not raw yield —
- a cheap experiment that halves a conjecture's probability outranks an expensive one
- that nudges a bound; until M3 decides its mechanics (§15 P3) it is implemented as
- gate-outcome reward per measured cost, and no model probability, e-value, posterior
- or similarity term ever enters it.
+ **Allocation currency (M0–M2) is gate-outcome reward per measured cost**, not raw
+ yield. M3 may replace the formula only with another function of gate outcomes,
+ measured cost, and bundle-pinned baselines (§15 P3) — still no model probability,
+ e-value, posterior, or similarity term. Prose goal (“cheap decisive checks beat
+ expensive nudges”) guides the M3 bar; it is not a second hidden currency.
```

---

### 7. REFUTED → negative-results map intake (accretion path)  
**Severity:** MED · **§11 + §4**

**Rationale.** §11’s map is the cross-run asset; ledger rows are operational. Without a mechanical intake when a measured/formal REFUTED lands, accretion depends on taste under load. Component: compounding assets. Cost: draft artifact + human edit-before-cite; no new gate. Evidence: **CONJECTURE** on operator time saved; aligns with stated §11 purpose. Does not auto-cite without human.

```diff
  **Negative-results map (first-class, citable):** ...
+ *Intake:* every new REFUTED entry with `refutation_kind ∈ {formal, measured}`
+ enqueues a map draft pointing at the ledger record and evidence node (ladder table
+ + A/A when measured). Drafts are inadmissible as external citation until a human
+ marks `map_published`; schema is the §11 field list. Implementation faults
+ (`refutation_kind = implementation`) do not draft map entries — they yank/salt.
```

---

### Explicitly sound (no change)
- §0 / immutable gate layer / calibration taxonomy / honest baseline  
- §3 recipe vs attempt append-only model, disowned mark, checkpoint threat model  
- §6 pre-reg → gate entropy → gate-owned op counter → KEEP / KEEP_IN_SAMPLE split  
- §7 tag derivation, Skeptic isolation, statistical monitors non-promoting  
- M0–M2 done-when detail and planted corpus shape  
- Operator defaults and borrowed-mechanism constraint  

---

**(a) Stake most on:** **1** (yank reach), **2** (AlreadySettled), **3** (cost-profile coherence).  

**(b) Framing concern:** The plan’s load-bearing frame is “mutable search, immutable truth,” and that holds. The weaker frame is **M3 optimization**: gate-outcome reward on a ladder that ships known positive controls will, by default, maximize **re-verification of the harness**, not research — unless settled hypotheses are non-re-fundable and M3’s bar tests novelty-vs-settled explicitly. A second mild frame risk: calling allocation “information-per-dollar” while forbidding information measures sets up a future contradiction; keep the prose goal, not the unit name (prop. 6).  

**(c) Facts the plan does not state (needed before implementation, not blockers for the above):**  
1. Numeric **tier production maxima** (T1 vs T2 edge in core-seconds / core-hours) for the coherence table.  
2. Whether **hypothesis key** includes enough method canonicalization that “negation-map rho v1 vs v2” collides or not (settled-duplicate behavior depends on it).  
3. Who may write **yank** records besides automatic self-test failure (operator-only vs auditor).  
4. M0 **environment-manifest** field list for `container-digest` substitute (OS/interpreter/libs — exact set).  
5. Intended **human-queue priority** when sign-off, `nogo_review`, statement review, and null-control remeasure contend (starvation policy).