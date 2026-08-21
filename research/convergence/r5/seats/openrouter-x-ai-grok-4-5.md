# Review of plan-r4.md

§0–§1, §8–§9, §14, the substrate/attempt model, ladder ownership of instances/counters, and gate-bundle immutability are sound. I am not revising those. Below are only places where the written contract is fail-open, internally tense, or too loose to implement safely.

---

### 1. Tier assignment trusts the same self-declaration the ceiling uses  
**Severity:** HIGH · **§5 (tier gate), §2 (skill identity)**

**Rationale.** The plan correctly says a self-declared cost admission is fail-open, then “fixes” it with (a) tier derived from the profile’s production cost at the inputs and (b) a hard ceiling at a bundle multiplier of that same declared expectation. Both knobs share one free variable. Understate the cost function by ~5–10× and a true multi-hour Tier-2 run can finish inside a Tier-1 ticket + 4× ceiling, skipping ladder/hunt tickets. P4’s measured/declared alarm is strategy-layer only and does not restore the ticket. Component fixed: tier gate + skill certification. Cost: per-skill benchmark fixtures and a pinned calibrated model in the identity bundle; small extra M0/M1 work. Evidence: CONJECTURE (same failure shape the plan already names; no need for a new dependency). Does not touch epistemics—tightens a gate input.

```diff
--- a/plan-r4.md §2 / §5
+++ b/plan-r4.md §2 / §5
@@ skill identity
- `{interface version, implementation revision, tool and container digests, numeric profile}`
+ `{interface version, implementation revision, tool and container digests, numeric profile,
+  cost_calibration}` where `cost_calibration` is a gate-recorded table of
+  `(representative inputs, measured production cost, measured verification cost)` run
+  under `skip_cache_lookup` at certification time, spanning the skill's claimed
+  operating range, plus a fitted conservative model (ceiling of declared profile vs
+  calibration extrapolation; never the minimum). An uncertified calibration is
+  treated exactly as an uncertified self-test: revision not launchable above Tier 0.
@@ tier gate
- the gate derives the launch's tier from the profile's production cost at the
- launch's inputs under the bundle's boundary table
+ the gate derives the launch's tier from max(declared production cost,
+ cost_calibration.at(inputs)) under the bundle's boundary table. Inputs outside
+ the calibrated range do not inherit a Tier-1 ticket to Tier-2: the gate refuses
+ with `TierRefused(uncalibrated_inputs)` unless a human `nogo_review`-style
+ waiver node `cost_range_extension` is present (operational, expiring; does not
+ satisfy scrutiny obligations). The runtime ceiling multiplier applies to the
+ same max(...), not to the author declaration alone.
```

---

### 2. Bandit/yield must score negative resolutions or the tree farms “wins”  
**Severity:** HIGH · **§4 orchestrator, §5 allocation, §9, §15 P3**

**Rationale.** Progress is defined as knowledge gained (§9), including refutations, but allocation is “gate-outcome reward per measured cost” with no schedule of which outcomes pay. Under “never give up” pressure a yield-maximizing orchestrator that only scores KEEP/PROVEN/SURVIVED will underfund Skeptic, ladder REJECT paths, and negative-result writeups—the load-bearing outputs for a standing ECDLP baseline. `AlreadySettled` blocks exact re-funding of successes; it does not make refutation valuable. Component: orchestrator reward. Cost: trivial (lookup table); no new deps. Evidence: CONJECTURE from the plan’s own incentive analysis (§1, §9); STRONG-EMPIRICAL analogy in any agent that optimizes a misspecified proxy. Does not put e-values or model probabilities into the reward—only terminal gate verdicts already in the ledger.

```diff
--- a/plan-r4.md §5 / §15 P3
+++ b/plan-r4.md §5 / §15 P3
@@ allocation
- until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome
- reward per measured cost, and no model probability, e-value, posterior or
- similarity term ever enters it.
+ until M3 decides its mechanics (§15 P3) it is implemented as gate-outcome
+ reward per measured cost. The M0 default outcome schedule (bundle field,
+ immutable to the orchestrator) scores, per unit cost, any *terminal epistemic
+ resolution* on a hypothesis/claim version:
+   positive, same class: ladder KEEP | KEEP_IN_SAMPLE (scoped) | REJECT that
+     installs or confirms a REFUTED entry | hunt KILLED | hunt SURVIVED |
+     justify-derived PROVEN | formal negation admitted to the ledger |
+     implementation DISAGREE that yanks a revision;
+   zero: INCONCLUSIVE, BUDGET_EXCEEDED, PARKED-by-strategy, duplicate work
+     refused by preflight;
+   negative: Leaked obligation, cache/serve of disowned nodes, attempt to
+     write a tag or waive an admission gate.
+ No model probability, e-value, posterior, similarity, or "distance to ECDLP
+ break" term ever enters it. "Information per compute-dollar" in this plan is
+ this schedule—not a separate estimator M3 may invent.
@@ P3 (ii)
- reward computed only from gate outcomes, with a relative-improvement
- baseline and a cost-aware blend as the nearest prior for info-per-dollar;
+ reward computed only from the §5 terminal-resolution schedule, with a
+ relative-improvement baseline against the branch's own recent gate outcomes
+ and a cost-aware blend; M3 may reweight classes inside the positive set with
+ a human-attributed bundle update, and may not add non-gate features;
```

---

### 3. Success-side hypothesis farming (near-dup is advisory only)  
**Severity:** MED · **§4 ledger preflight**

**Rationale.** Measured REFUTED reach covers parameter-point inclusion on failures. Successes only get `AlreadySettled` on exact hypothesis-key match plus an advisory SimHash. A worker can mint STRONG-EMPIRICAL tickets by ε-jittering ranges/canonical parameters on a method that already KEEP’d—cheap positive yield under proposal 2’s schedule if unaddressed. Component: ledger preflight. Cost: one structural query; human/Librarian difference-statement path already exists for supersedes. Evidence: CONJECTURE (incentive-compatible reading of §4 as written). Does not make similarity a gate: structure (method identity + cost-model + range dominance) routes; prose still cannot blacklist.

```diff
--- a/plan-r4.md §4 ledger preflight
+++ b/plan-r4.md §4 ledger preflight
@@ AlreadySettled
+ `RequiresDifferenceStatement` = the proposal's method identity and cost-model
+ shape match an existing branch or ledger entry whose claim/ladder stands at
+ KEEP, KEEP_IN_SAMPLE, SURVIVED, PROVEN, or STRONG-EMPIRICAL, and the new
+ declared parameter region is equal to or a subset of that entry's region
+ (same axis-aligned rule as measured REFUTED reach), and the hypothesis key
+ is not identical (exact identity remains `AlreadySettled`). Park with blocker
+ `success_dominates_review` until an attributed difference statement—what
+ semantic field changes the prior resolution's reach—is recorded on the same
+ path as `supersedes_refuted_review` (human before M4, Librarian from M4).
+ The prior KEEP/PROVEN does not transfer; the preflight only refuses silent
+ re-funding of a dominated slice. Advisory SimHash remains advisory and still
+ never sets status.
```

---

### 4. Split M1 — it is not one milestone  
**Severity:** HIGH · **§13 build order**

**Rationale.** M0 is a tight vertical slice. M1 simultaneously delivers ladder physics (trial sizing, A/A, counters, 60-bit ticket split), full formalization/PROVEN derivation, skeptic isolation, counterexample hunts, scrutiny router, no-go consumer, and ≥30 planted fixtures. That is multiple independent fail-closed stacks with one “done when.” A single red fixture class blocks learning on the others; the anti-over-engineering note undercuts this packing. Component: build order only (no epistemic change). Cost: one more integration boundary; net lower risk. Evidence: SPECULATION on calendar, STRONG-EMPIRICAL on “large gated milestones slip as a unit.”

```diff
--- a/plan-r4.md §13
+++ b/plan-r4.md §13
@@ M1
- **M1 — single track.** Prover + independent skeptic + ladder, ...
+ **M1a — empirical track (ladder + hunt + tier tickets).** Baseline skills
+ `rho_dp`, `bsgs`, instance-maker; ladder protocol; counterexample-hunt
+ record; reproducibility re-run policy; tier-gate fixtures for
+ KEEP_IN_SAMPLE/KEEP/yank/cost; scrutiny router + no-go presence check;
+ dispatch canary; P1 decision. *Done when:* planted corpus (a)(b)(e)(f)(i)
+ and positive controls (j)(k)(m) plus listed tier/ladder-execution fixtures
+ under cold cache; formalization fixtures explicitly out of scope.
+
+ **M1b — proof track (depends on M1a substrate + justify only).** Prover +
+ independent skeptic; formalization challenge/solution gate (hasher probe
+ first); statement pre-filters; `review_verdict` in PROVEN derivation;
+ disagreement protocol; planted corpus (c)(d)(g)(h) and control (l).
+ *Done when:* those fixtures pass and skeptic allow-list/dispatch canary
+ hold. M1 in deferred decisions means M1a unless noted (P1 → M1a).
```

---

### 5. Say what actually runs unattended  
**Severity:** MED · **§9–§10 framing (wording + operator contract)**

**Rationale.** “Never stops researching” sits beside non-defaulting human gates (statement review, expert sign-off, waivers, optional Tier-2 session knob). Without an explicit autonomy envelope, operators will read §9 as unattended PROVEN/Tier-3 progress; the honest system will look “stuck” on the human queue while doing correct Tier-0/1 work. This is framing, not a new gate.

```diff
--- a/plan-r4.md §9
+++ b/plan-r4.md §9
@@ persistence
+ **Autonomy envelope (operator-facing):** with no human session, the harness
+ may indefinitely open/fund/refute/park Tier-0/1 work, write REFUTED/PARKED/
+ negative-result entries, run ladder rungs already ticketed, and accumulate
+ CONJECTURE/STRONG-EMPIRICAL under mechanical gates. It may *not* mint PROVEN,
+ grant Tier-3, accept no-go content, or clear `*_review` blockers. Those wait
+ on the human queue without fabricating interim green status. "Never give up"
+ is this envelope, not unattended promotion.
```

---

### 6. Delete aspirational VoI language that contradicts the reward ban  
**Severity:** LOW · **§5**

**Rationale.** “A cheap experiment that halves a conjecture’s probability outranks…” invites implementers to put model probabilities into allocation—the same paragraph forbids that. Proposal 2’s schedule is the resolution; the sentence should not survive as a second objective.

```diff
--- a/plan-r4.md §5
+++ b/plan-r4.md §5
- Allocation currency is expected information per compute-dollar, not raw
- yield — a cheap experiment that halves a conjecture's probability outranks
- an expensive one that nudges a bound; until M3 ...
+ Allocation currency is terminal gate-resolution per measured compute-dollar
+ (§5 schedule), not raw claim count or any model-estimated probability;
+ until M3 ...
```

---

### 7. Formalization: cheap rejects before `leanchecker --fresh`  
**Severity:** LOW · **§7 formalization gate**

**Rationale.** Tier-2 already requires `approve` first. Tier-1 can still burn full closure replay on vacuous/sorry-shaped Solutions. Pre-filters exist but are not ordered as hard predecessors of kernel replay in the gate plan. Cheap fail-closed ordering is free performance and matches “cheap before expensive.”

```diff
--- a/plan-r4.md §7 Green Lean
+++ b/plan-r4.md §7 Green Lean
+ Gate plan order is fixed: (0) bundle pin + Solution names Challenge formal
+ statement hash; (1) mechanical statement pre-filters; (2) for any run whose
+ declared profile is Tier ≥ 2, require `review_verdict=approve` on the claim
+ statement hash; (3) sandbox build; (4) axiom collection; (5) kernel replay;
+ (6) comparator closure check. Steps (1)–(2) failures never start (5).
```

---

**Sections I’d leave alone:** §0, §1, §3 (attempt/disown/checkpoint design), §6 protocol structure (KEEP_IN_SAMPLE split is the right deadlock fix), §8, §12 rejected list, §14 baseline, calibration taxonomy and “tag is derived.”

---

**(a) Stake most on:** **1** (tier/cost self-declaration fail-open), **2** (reward must pay for refutations), **4** (split M1).

**(b) Framing that is wrong or cracked:** The plan sells **value-of-information allocation** while forbidding the quantities VoI needs, and sells **never-give-up autonomy** while PROVEN/Tier-3/no-go content are human-paced. The real product is a **fail-closed, negative-result-first empirical research engine** with a human taste/formalization airlock—not an unattended theorem factory and not a Bayesian bandit. Write that on the tin or M3/M10 will “fix” the wrong objective.

**(c) Facts the plan does not state (needed before locking M1a):**  
(1) Measured paired variance and trial count that KEEP control (j) with margin on the build machine.  
(2) Whether deployment FS supports true non-owner append-only checkpoints (grounding claim).  
(3) `leanchecker --fresh` wall time on a mathlib-importing Challenge (sizes M1b).  
(4) Empirical distribution of skill cost understatement risk on PARI/Sage baselines (calibrates proposal 1).  
(5) Write-throughput ceiling of the single-writer SQLite contract under the M4 “≥4 tracks” stress (whether queue depth suffices).