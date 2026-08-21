# Seat review — Anthropic Opus (repository-grounded) — round 2

Plan: `research/convergence/plan-r1.md`. No invariant is attacked below; two proposals
strengthen gates by refusing launches, none loosens one.

**Sound, needs nothing:** §0, §1, §8, §9, §14. §7's derived-tag rule and append-only tag
history are the cleanest text in the plan. §12's borrowed-mechanism constraint is correctly
labeled an operator ruling (`PROPOSALS.md:23`), not a derivation.

---

## 1 · The Tier-2 ticket and the 60-bit rung are circularly dependent · HIGH · §5, §6

**Rationale.** §5's tier gate: "for Tier 2 on an algorithmic claim the ticket is a ladder
result table with verdict KEEP (§6)." §6 makes KEEP conditional on rung (2b), the 60-bit
rung, and prices it at "≈ 1.3×10⁹ group ops … a quarter hour interpreted" per trial —
verified at `briefs/adjacent-distributed-collision-search.md:51` (1.35×10⁹ ops, ≈15 min
Python, 2–3 min in C). Ten fresh instances interpreted is ≈ 2.5 core-hours: Tier 2 by §5's
own band, not Tier 1 ("one core, minutes"). §6 says so itself — "runs only when the tier
gate grants that budget." So: no Tier-2 grant without KEEP, no KEEP without the 60-bit
rung, no 60-bit rung without a Tier-2 grant. A fresh implementer deadlocks on the first
algorithmic claim, and a refusal is a `TierRefused` record, not an exception to catch
around. No compiled rho skill appears in §13, so the interpreted figure is the default.

**Fix.** Split the ticket: the ≤ 50-bit rungs with a provisional verdict are a *scoped*
Tier-2 ticket funding the 60-bit rung and nothing else. Cheap-before-expensive holds — the
50-bit refutation floor still fires first.

```diff
-absent: for Tier 2 on an algorithmic claim the ticket is a ladder result table with
-verdict KEEP (§6);
+absent: for Tier 2 on an algorithmic claim the ticket is a ladder result table with
+verdict KEEP (§6) — with one scoped exception: a table whose ≤ 50-bit rungs all pass
+(verdict `KEEP-PROVISIONAL`) is a Tier-2 ticket valid for the 60-bit rung of that same
+claim and for no other launch. *Why:* KEEP requires the 60-bit rung and that rung costs
+Tier-2 money, so an unscoped rule is satisfiable by no honest claim;
```

---

## 2 · A superseded claim version escapes its own REFUTED entry · HIGH · §3, §4

**Rationale.** §3's hypothesis key hashes "the claim statement hash of §4" and/or "the
statement hash of the approach." §4 makes a claim statement node immutable and "a change
to any semantic field is a new version with an explicit `supersedes` edge." A new version
therefore has a new statement hash, hence a new hypothesis key, hence `Allowed` at
preflight — a REFUTED entry against v1 does not reach v2.

§4 closes the symmetric hole in the safe direction only ("evidence attached to a
superseded version does not transfer"). Positive evidence is firewalled correctly;
refutations are firewalled too, and that direction is a gate bypass. §4's terminal-status
paragraph anticipates re-opening *the same* statement hash and says nothing about a new
version. The escape needs no bad faith: an honest Reframer restating a refuted conjecture
with a tightened scope mints a fresh key, and the ledger loses its teeth exactly where §3
says it has them ("no agent needing to *remember* that two approaches are secretly the
same").

**Fix.** Make the preflight walk `supersedes` edges.

```diff
   - *Ledger preflight:* … `Blocked` = the hypothesis key (§3) matches a REFUTED entry
     whose retry predicate is unmet;
+    a REFUTED entry against any *ancestor* statement version (following `supersedes` edges)
+    matches too and yields `Blocked` unless the new version's record states, attributed and
+    in writing, which semantic field changed and why the refutation does not reach it — the
+    human reviews that before M4, the Librarian from M4. *Why:* refutations must transfer
+    across versions in the direction evidence must not; otherwise restating a refuted claim
+    mints a fresh key and the ledger has no teeth against the commonest honest move.
```

---

## 3 · The hypothesis object is mutable, so ladder pre-registration is a convention · HIGH · §3, §6

**Rationale.** §6 step (0) is the ladder's anti-fabrication core: "The claim pre-registers
its cost model … in its hypothesis object (§3) before any rung runs; the ladder tests that
model and never a curve fitted afterward." r1 gave the *claim statement node* a full
immutability treatment (§4). The hypothesis object got none: §3 enumerates its fields and
how it is hashed, and never says who writes it, where it lives, or that it cannot be
rewritten. Nothing mechanical stops a worker amending the declared exponent after seeing
the 40-bit rung — and since amending changes the hypothesis key, the ledger does not even
see a second attempt at the same hypothesis. This is the one place where a stated gate has
no enforcement, and §1's own warning applies verbatim.

**Fix.** The machinery exists: §3's hash-chained, CAS-advanced log gives a verifiable
*order*, and §6 has a gate-owned instance-maker whose entropy the worker never sees. Bind
them.

```diff
   - *Hypothesis key:* BLAKE3-256 … over a typed hypothesis object `{target family,
     claimed property or cost model …}`.
+    The hypothesis object is immutable and content-addressed exactly like the claim
+    statement node (§4): appended to the hash-chained log when the branch is opened, and an
+    amendment is a new object with a `supersedes` edge the preflight of proposal 2 sees.
+    Pre-registration is then an order in the chain, not a claim about intent: the ladder
+    gate refuses any rung whose hypothesis-object record does not *precede* the
+    instance-maker's entropy commitment for that rung in the same chain. *Why:* "tests that
+    model and never a curve fitted afterward" is checkable only if the model's commitment
+    is timestamped by something the worker cannot rewrite.
```

---

## 4 · Verification compute is unbudgeted; escrow it at launch · HIGH · §5, §7

**Rationale.** §0's second principle is "cost is predicted before it's spent," and §5 makes
every *skill* declare a cost profile. The gate layer declares nothing, yet four gate
activities are real compute scaling with the work they check: the reproducibility gate's
re-runs (§3), the Skeptic's `skip_cache_lookup` re-runs (§7), `leanchecker --fresh`
(proposal 7), and the auditor's sampled re-verification (§7).

The auditor's arithmetic makes this concrete. §7's bound `l ≥ ln(2^bits)/ln(1/(1−f))` is
correct — `(1−f)^l ≤ 2^−bits` rearranges to exactly that — but at the plan's own M0
defaults (`f = 0.01`, `bits = 20`) it demands `l ≥ 13.86/0.01005 ≈ 1,379` re-verifications
**per tier stratum per cycle**, and §7 requires stratification "so that cheap Tier-0/1
nodes cannot absorb the whole sample." 1,379 Tier-2 replays at hours apiece is ≥ 10³
core-hours — a recurring Tier-3 spend no gate reads and no budget holds. As written that
stratum is either skipped in practice or eats the machine.

Subjecting gates to the tier gate would be wrong — a gate a budget can starve fails open.
The fix runs the other way: refuse the *launch* whose verification is unaffordable.

```diff
 **Mechanism:** every skill declares its **cost profile** (complexity in inputs, expected
 tier) as part of its typed interface, so the orchestrator *predicts* spend before launch
 and the tier gate enforces cheap-before-expensive automatically.
+A cost profile has two components, *production* and *verification* — the latter being what
+the node's replay grade and tier will later cost under the §3 re-run policy plus its share
+of the auditor's sample. The tier gate escrows the verification component out of the grant
+at launch and refuses a launch whose verification the remaining budget cannot cover.
+*Why:* a gate whose compute is unbudgeted is a gate skipped under load — silent fail-open
+by a slower route.
...
     nodes with the largest `justified_by` fan-in are drawn first.
+    Where a stratum's escrow cannot fund the `l` the bound demands, the auditor draws what
+    it can afford and records the *achieved* `bits`; every claim justified by a node in
+    that stratum carries that figure. An unmet target is published, never silent.
```

---

## 5 · The 60-bit out-of-sample check rejects honest methods at ≈ 1 in 5 · MED · §6

**Rationale.** §6 (2b) requires "the model fitted on the ≤ 50-bit rungs must predict the
measured 60-bit mean inside the band," where the band comes from (2)'s A/A null arm run at
≥ 10² trials. But (2b) measures the 60-bit mean over **10** instances, and rho's dispersion
is large: sd ≈ 0.53–0.56 × mean, verified at
`briefs/adjacent-distributed-collision-search.md:16` (BLS PKC 2011 §6, 32k–257k trials).
A 10-instance mean carries a standard error of ≈ 0.5/√10 ≈ 16 % of the mean; the A/A band
at 10² trials has radius ≈ 5 % (95 % CI ≈ ±10 %, band ≈ ±20 %). Comparing a point estimate
with ±16 % noise against a ±20 % band REJECTs an honest method roughly one run in five —
and §6 says "a clean in-sample fit that misses out of sample is REJECT." False REJECTs at
that rate are the mirror image of the fabrication the gate exists to stop, and the first
thing an operator will be tempted to waive.

**Fix.** Compare intervals, not a point against a band, and inflate by the rung's own error.

```diff
-the model fitted on the ≤ 50-bit rungs must predict the measured 60-bit mean inside the
-band,
+the prediction must lie inside a band widened by the rung's own sampling error —
+`1 ± 2·√(radius_AA² + (sd₆₀/(mean₆₀·√m))²)` over `m` measured instances — because at
+`m = 10` and rho's `sd ≈ 0.5·mean` the rung's standard error (≈ 16 %) already exceeds
+`radius_AA`, so a point-estimate comparison REJECTs an honest method about one run in
+five. `m` is fixed in the ladder plan (gate bundle, §4);
```

---

## 6 · §5 and §6 use two different "best generic baseline," differing by 1.41× · MED · §5, §6

**Rationale.** §6 sets the KEEP band against "the best generic baseline the harness ships …
plain rho (≈ 1.25√n ops)"; §5 prices Tier-2 rho at "0.886√n." Both are correct and they are
different algorithms — `briefs/adjacent-distributed-collision-search.md:51`: "rho 1.25√n ops
(**0.886√n with negation**)." So §5 assumes a negation-map rho, which by §6's own wording
would *be* the best baseline the harness ships, and a method beating 1.25√n by 30 % while
losing to 0.886√n is KEPT while worse than the harness's own rho — §6's closing failure
("beats BSGS" while losing to rho) one level up.

```diff
-  the best generic baseline the harness ships, measured in the same harness on the same
-  instances** — plain rho (≈ 1.25√n ops, O(1) memory), never BSGS —
+  the best generic baseline the harness ships, measured in the same harness on the same
+  instances** — plain rho without the negation map (≈ 1.25√n ops, O(1) memory) at M1,
+  never BSGS; if a negation-map rho is ever shipped (≈ 0.886√n, the constant §5 uses to
+  price Tier 2) it becomes the baseline the same day it lands —
```

---

## 7 · The formalization gate has no cost, and its statement hasher is untagged and unbuilt · MED · §5, §7, §16

**Rationale — two verified points.**

(a) **Cost.** §5 puts "a Lean compile" in Tier 1 ("one core, minutes"). §7's gate is not a
compile: step (ii) is `leanchecker --fresh`, which per `grounding/lean-checker-protocol.md:40`
replays "every constant in the transitive closure … by the kernel from empty." Measured at
**32.3 s on a mathlib-free toy project** (`:41`); for a mathlib-importing Challenge the wall
time is **explicitly OPEN** (`:53`). §11 commits the library to mathlib, so that is the
normal case. M1's done-when needs ≥ 30 planted fixtures including two Lean ones; if each
gate run is hours, that corpus is not runnable inside M1.

(b) **Tag.** §7 asserts the statement-hash construction flatly.
`grounding/lean-checker-protocol.md:50` tags that construction **CONJECTURE**, and `:55`
records "OPEN: statement-hash tool does not exist … the proxy above is inferred from
`compareAt`, not run." The *negative* half is probed and solid (two semantically identical
Challenges hashed differently as raw exports, `:50`). §16 requires stack facts to carry
their source's tag; this one speaks in the voice of a verified mechanism.

```diff
     The statement hash is computed over what the comparator compares (the theorem's
     `ConstantVal` and the full `ConstantInfo` of every constant in its transitive closure),
-    never over raw export bytes, which carry position-dependent names.
+    never over raw export bytes, which carry position-dependent names (that raw exports are
+    unstable is PROVEN by probe; that this closure is the right hash is CONJECTURE — the
+    hasher is inferred from `compareAt` and does not yet exist, `grounding/lean-checker-protocol.md:50,55`,
+    and M1 builds and probes it before the gate is trusted). The gate declares a cost
+    profile like any skill; `leanchecker --fresh` replays the whole transitive closure from
+    empty (32.3 s mathlib-free, unmeasured with mathlib, `:41,53`), so M1 measures it on a
+    mathlib-importing Challenge before budgeting its fixture corpus, and §5's "a Lean
+    compile" at Tier 1 names the compile only, never this gate.
```

---

## 8 · M0's "upstream_vendored" corpus is one case, not a corpus · MED · §13

**Rationale.** §13 says the exemplar's "known-answer corpus is seeded from Sage/PARI
doctests (`corpus_origin = upstream_vendored`)." `grounding/pari-sage-toy-curve-backend.md:42`
states the opposite: "No explicit F_p (P,Q,x) triple exists in Sage/PARI docs beyond seed 1;
seeds 2–3 need a locally computed P or Q." Seed 2's `P` is OPEN (`:34`), seed 3 has no `x`
(`:35`), seed 4 is a negative control (`:36`). The vendored corpus for the thing M0 must get
right is one 5-element curve. A locally completed seed is `author_supplied`, capped at
CONJECTURE by §2 — which also names the free escape: `randomized_postcondition`.

```diff
-    Its known-answer corpus is seeded from Sage/PARI doctests
-    (`corpus_origin = upstream_vendored`);
+    Its known-answer corpus is one vendored F_p triple (PARI `usersch3.tex:29031-29032`,
+    `upstream_vendored`), three vendored membership/order/negative-control cases carrying no
+    `x`, and a `randomized_postcondition` arm — draw random `x`, set `Q = xP`, assert `OK`;
+    draw `x' ≠ x`, assert `FAIL` — since `grounding/pari-sage-toy-curve-backend.md:42`
+    records no second complete triple upstream and a locally completed one is
+    `author_supplied` (CONJECTURE cap, §2);
```

---

## (a) The three I would stake the most on

1. **#1 (ladder/tier circularity)** — a deadlock on the first real claim, provable from the
   plan's own numbers.
2. **#2 (superseded versions escape REFUTED)** — the ledger's teeth, lost to a move an
   honest agent makes routinely; the fix is four lines.
3. **#3 (mutable hypothesis object)** — pre-registration is the ladder's whole anti-fabrication
   claim and it is currently unenforced.

## (b) Where the framing is wrong

**§13's M0 contradicts §13's own anti-over-engineering paragraph.** "Build M0 before adding
another design layer" sits directly beneath an M0 requiring the recipe-key canonicalizer
*and* the hypothesis key with test vectors, attempt records, four cache bits, replay grades,
the certificate slot, the claim statement node, `justify` with append-only tag history, a GC
roots table, and the gate-bundle pin — plus exemplar, verifier and tier gate.

Several have no consumer at M0. The hypothesis key's only reader is the ledger preflight
(M2). `justify` needs two evidence kinds to order; M0 has one skill and no claims. GC roots
protect blobs from a collector M0 does not run. Schema with no consumer is schema that will
be wrong, because nothing exercises it.

This does not weaken the gate layer: the gates are invariant, their *build order* is not.
The honest form is M0 = verifier, exemplar, recipe key with attempts and cache bits, tier
gate; hypothesis key with the preflight at M2; `justify` and tag history with the second
evidence kind at M1; GC roots with the first collectable blob. Otherwise this project's
likeliest failure is not fabrication — it is that a plan whose first milestone is most of
the epistemics layer never produces the running 40-bit slice §13's own last sentence says
will teach more than more architecture.

## (c) Facts I would need that the plan does not state

1. Wall time of `leanchecker --fresh` on a mathlib-importing Challenge, and of one full
   comparator run — OPEN at `grounding/lean-checker-protocol.md:53`. Every M1 Lean fixture
   count is a guess until measured.
2. Whether a compiled rho/BSGS skill is in scope at M1. Proposal 1's scoped ticket and the
   60-bit rung's tier both change if the 15-minute interpreted trial becomes 2 minutes.
3. Who writes the hypothesis object, and when relative to the claim statement node — §4
   names an author for the statement node and none for the hypothesis object.
4. The auditor's cadence in wall-clock terms. `f` and `bits` are given, the period is not,
   so proposal 4's recurring cost cannot be sized.
5. What stops the orchestrator process reopening the gate-bundle file writable. §4 says a
   separate read-only SQLite file; a read-only handle inside one process is a convention —
   a file permission or a separate process is the mechanism, and the plan names neither.
