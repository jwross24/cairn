# Cairn plan-r0 — repository-reading seat review

Checked against `research/PROPOSALS.md`, `research/briefs/`, `research/grounding/`, `HANDOFF.md`,
`CLAUDE.md`. Nothing edited. `research/grounding/` is being written *while* I review
(`lean-statement-linters-vacuity.md` still holds `__ATP_PORT_RESULT__` placeholders); my first listing of
it came back empty and was wrong. Three of the plan's load-bearing facts are contradicted by those
probes — proposals 1–3.

## Fact checks

**Verified.** mathlib coverage (§11) incl. every "absent" item — **`briefs/adjacent-proof-automation.md:9-27`**.
Spot-check bound (§7) — **`briefs/frankenfs.md:38-43`**, algebraically identical. rho witness and `b ≢ d`
rejection (§3) — **`briefs/adjacent-distributed-collision-search.md:11`**; trial counts and `sd ≈ 0.5×mean`
at source 2; 50-bit rho/BSGS at `:51`. License rider (§12) — **`PROPOSALS.md:16-24`** (reviewer-checked).
§7's statement pre-filters are now *feasible*, not just cited: `grounding/lean-statement-linters-vacuity.md`
§1 vendored four files with two import edits and reproduced the upstream messages on `v4.34.0-rc1`.

**Wrong or over-claimed.**
- §2 / §13's "two independent implementations (PARI vs Sage)" — contradicted at
  `grounding/pari-sage-toy-curve-backend.md` §1–2 (proposal 1).
- §13's verifier subprocess — `gp` exits 0 on fatal errors (same file, §3) (proposal 2).
- §7's "by construction" skeptic isolation — `grounding/dbos-sqlite-and-agent-sdk-isolation.md` §B makes
  it the parent's discipline, and context isolation is not filesystem isolation (proposal 3).
- §13's "milliseconds below 60 bits" — true only through 50 bits; at 60 bits `ellcard` is ~75 ms per
  curve, one search took 25.4 s, and it overflows PARI's default stack in both `gp` and `cypari2`.
- §13's "10 / 25 / 130 tries" — the probe measured 20–220 and rules the means CONJECTURE: "run ≥50 seeds
  before quoting a cost profile."
- §6's 60-bit figures are CONJECTURE in `briefs/…collision-search.md:51`; the plan states them flat.
- §7 claims linters catch "the `∃ x, P x → Q` trap"; the probe shows `∃ n > 0, n ≠ 1 → False` and
  `∃ n, (n ≠ 0 → False) ∧ True` are silent. Say "some forms of".
- §12 presents an operator legal ruling as derived; `PROPOSALS.md:24` leaves it to the operator.

**Sound, needs nothing:** §0, §1, §8, §9, §14, §16's invariant list, and the formalization protocol in §7 —
the plan's use of C1's evidence is faithful, if anything understated.

---

## 1 · "PARI vs Sage" agreement does not exist on this stack, and its surrogate always agrees · HIGH · §2, §13

**Rationale.** §2 requires "agreement or raise" where two independent implementations exist; §13 names
`cardinality(algorithm='all')`-style agreement for the exemplar. The probe found **Sage is not installed**
(`sage: command not found`, PROVEN by probe), and the surrogate — `gp` 2.17.4 against `cypari2`'s bundled
libpari 2.17.2 — gave "**bit-identical** `p,a,b,N` and tries for every row… same PRNG/algorithms across the
two builds." A check that cannot disagree never raises: a silent-fail-open gate at Tier 0, where "nearly
every refutation and orchestration decision lives." And the genuine cross-check inside `algorithm='all'` is
BSGS vs SEA — two *algorithms*, not implementations — which the probe shows "is only independent for
b ≤ 50": at 60 bits `ellcard` *is* SEA, so independence evaporates at exactly the size §6 requires a
method to complete at.

```diff
-  ... where two independent implementations exist (PARI vs Sage), require agreement or raise.
+  ... Where a cross-check is claimed the skill declares its axis — `implementation` (distinct
+  codebases) or `algorithm` (distinct methods in one codebase) — and the range over which that axis is
+  actually independent; outside it the skill declares no cross-check and its result is capped
+  accordingly. Two builds of one library (`gp` and `cypari2` both wrap libpari) are one implementation,
+  and a cross-check that has never disagreed is reported as untested, not as passing.
-    `cardinality(algorithm='all')`-style two-implementation agreement on the order; ...
+    a BSGS-vs-SEA *algorithm* cross-check, valid for b ≤ 50 only (at 60 bits PARI's generic path is SEA
+    and the two agree by construction); a second *implementation* needs a non-PARI backend, which is an
+    M0 install decision, not an assumption.
```

## 2 · The Tier-0 verifier's subprocess fails open: `gp` exits 0 on fatal errors · HIGH · §4, §13

**Rationale.** The submission verifier is the plan's hardest gate ("`xP==Q` subprocess or no submit,
ever"), and §13 specifies the subprocess but not its acceptance rule. Three probe-PROVEN ways that fails
open: `gp` returns **rc=0 on fatal errors** (`1/0` and an 8 MB stack overflow both gave rc=0, empty stdout,
message on stderr); `gp` **zero-fills missing arguments**, so `verify(1,2)` runs and returns a verdict; and
60-bit `ellcard` overflows the default stack, which is one of those rc=0 fatals. An implementer checking
the exit code — the obvious reading of §13 — gets a verifier that says nothing and reads as success at
exactly the size the ladder tops out at. This gate is immutable; there is no second chance to specify it.

```diff
   - *Tier-0 verifier:* subgroup membership (`n·Q = O`) then `xP == Q`, in a subprocess ...
+    *Acceptance is affirmative, never residual:* the driver validates arity and every field before
+    spawning (the backend zero-fills missing arguments), passes an explicit stack ceiling (60-bit
+    `ellcard` overflows PARI's default), and accepts only `exit == 0` **and** `stdout == "OK"` **and**
+    empty stderr — a zero exit code is not evidence of anything, since the backend exits 0 on fatal
+    errors including stack overflow. The gate's planted-failure self-test (§4) includes a forced
+    backend crash that must classify FAIL.
```

## 3 · Skeptic isolation is the parent's discipline, not construction — and it is not filesystem isolation · HIGH · §7, §4

**Rationale.** §7 grounds the skeptic's independence "*by construction*", and §4 repeats it for every gated
worker. Two gaps. (a) Context isolation is real — "the only content you pass from parent to subagent is the
Agent tool's prompt string" — but *the parent LLM composes that string*, so statement-only is a request to
the parent, which §1 says is the first thing to fail under pressure; the grounding's fix is to dispatch the
Skeptic as its own top-level `query()` with the statement as `prompt` and `setting_sources=[]`. (b)
"Context isolation is not filesystem isolation: `Read`/`Bash` can open prover artifacts" — and Cairn stores
every prover artifact in a substrate the Skeptic can read. No intent to game is required: the cheapest way
to find a gap is to read the proof.

```diff
-  - *By construction:* the skeptic is a fresh-context worker whose only input is the statement node ...
+  - *By construction, at both layers.* Context: the skeptic is dispatched by the harness, never composed
+    by a parent model — a top-level query whose entire prompt is the statement node, inherited settings
+    sources disabled. Capability: an explicit tool allow-list for counterexample search, no general file
+    read, no shell, a substrate handle scoped to the statement node's closure. Both are gate config
+    (§4), outside the orchestrator's write path, and the dispatch record names the allow-list it ran
+    under, so a widened one is visible in the ledger.
```

## 4 · The ladder's KEEP band names no baseline; BSGS is used as both reject-floor and accept-bar · HIGH · §6

**Rationale.** §6(2) keeps a speedup whose CI clears `1 + 2·radius` — a ratio against *what* is never
stated, and C6(d)'s source does not supply it either. §6(4) answers it wrongly: "beats BSGS at 50 bits" =
"under ~5×10⁷ group ops and under 1 GB". The best generic baseline named in the same sentence is rho at
≈1.25√n ≈ 4×10⁷ ops with negligible memory, so a method costing 4.9×10⁷ ops and 900 MB passes the ladder
while being worse than plain rho on both axes. BSGS is the right *refutation floor*, the wrong
*acceptance bar*.

```diff
-whose CI radius sets the decision band (a speedup is KEPT only if the whole claim CI clears
-`1 + 2·radius`, floor 1%; otherwise INCONCLUSIVE or REJECT).
+whose CI radius sets the decision band. The band is always a ratio against the **best known generic
+baseline, measured in the same harness on the same instances** — rho (1.25√n ops, 0.886√n with the
+negation map; O(1) memory), never BSGS — and KEEP requires the claim CI to clear `1 + 2·radius` on
+group operations *and* memory within the same band.
-(4) The bar is quantitative: ... "beats BSGS at 50 bits" means fewer than ~5×10⁷ group ops, under 1 GB
+(4) Two thresholds. *Refutation floor:* failing to beat BSGS at 50 bits (~5×10⁷ ops, ≈3×10⁷ entries)
+refutes on the spot. *Acceptance bar:* the KEEP band above, against rho. The 60-bit figures carry the
+CONJECTURE tag their source assigns them; the ≤50-bit figures are STRONG-EMPIRICAL.
```

## 5 · The Tier-2 band is off by about a decimal order, which skips a Tier-3 gate · HIGH · §5

**Rationale.** §5 puts "80–100-bit rho for validation" in Tier 2 ("many cores, hours"). At the plan's own
constant (BLS 362 cycles/iteration at 3.2 GHz ≈ 0.11 µs, `briefs/…collision-search.md:51`), 0.886√n
iterations costs ≈30 core-hours at 80 bits, ≈970 at 90, ≈3.1×10⁴ at 100 — 3.5 core-years, ten days on a
128-core box. That is Tier 3 by the plan's own definition, and not cosmetically: Tier 3 is the only tier
requiring "an explicit predicted-cost-vs-payoff justification and a certificate verification plan." A
100-bit run admitted as Tier 2 skips both, and it is precisely the class that cannot be bit-replayed, so
the reproducibility gate has nothing to re-run either.

```diff
-- **Tier 2 — many cores, hours:** larger linear algebra, 80–100-bit rho for *validation*, ...
+- **Tier 2 — many cores, hours:** larger linear algebra, rho up to ≈90 bits for *validation* (≈10³
+  core-hours; the ceiling is arithmetic — at 0.11 µs/iteration, 0.886√n reaches ≈3×10⁴ core-hours by
+  100 bits), ... A declared cost profile above ≈10³ core-hours is a Tier-3 request whatever the skill
+  is called.
```

## 6 · Two independence holes in the epistemic layer · MED · §2, §7, §3

**Rationale.** (a) §6(1) exists because the documented exploit class for automated evaluators is
overfitting a fixed input; §2 then defines the skill self-test as a vendored corpus with a committed
floor — a fixed input. Fine for the exemplar, whose corpus is upstream; for any skill Cairn writes with no
upstream the author supplies the corpus, and a floor over cases the author chose measures nothing. The fix
is nearly free (`PROPOSALS.md:341-343`: Sage's `discrete_log` checks its own answer before returning — a
randomized postcondition, not a corpus). (b) §7's auditor query lets a STRONG-EMPIRICAL claim rest on a
SPECULATION premise, since it names only PROVEN, and a failed re-verification downgrades its own node
while the tower above keeps its tag. (c) §3 says admission re-runs every node and compares bitwise while
§7 gives the auditor a *sampled* cadence; both cannot be the policy, and "always re-run" doubles the cost
of exactly what the tier system rations, uncharged by §5's `meet(parent, declared profile)`.

```diff
   (i) a vendored known-answer corpus ... and a committed pass floor ...
+  A corpus authored by the worker that authored the skill is not a self-test: every skill declares
+  `corpus_origin ∈ {upstream_vendored, independent_oracle, randomized_postcondition, author_supplied}`,
+  and `author_supplied` alone caps its results at CONJECTURE. STRONG-EMPIRICAL needs an upstream corpus,
+  an independent implementation under proposal 1's axis rule, or a postcondition/metamorphic relation
+  checked on inputs from a seed committed *after* the implementation revision is content-addressed.
-    PROVEN claim may carry a `justified_by` edge to a weaker premise.
+    claim, of any class, may carry a `justified_by` edge at any depth to a strictly weaker premise; a
+    failed re-verification downgrades the node *and* re-derives every claim transitively justified by
+    it. `f` and `bits` are named in the gate config (M0: `f = 0.01`, `bits = 20`). Re-run policy is
+    fixed by grade and tier and budgeted before launch: `Verifiable` ⇒ witness always checked;
+    `Replayable` Tier 0/1 ⇒ always; Tier 2/3 ⇒ only when the claim is promoted past CONJECTURE, else
+    sampled with its tag capped meanwhile.
```

## 7 · M0's numbers, the milestone denominators, and P3's version hash · MED · §13, §15

**Rationale.** (a) §13's profile "≈ c·ln p tries" sits beside "10 / 25 / 130 tries at 30/40/50 bits";
`ln p` rises 1.67× over that range, the quoted draw 13×. The probe measured 20–220 at the same sizes and
rules the means CONJECTURE, recommending ≥50 seeds — so M0's first skill trips §5's own
measured-vs-declared alarm on its first run. (b) M1's "caught every time" has no denominator and no ruling
on INCONCLUSIVE; M3's "stall" is undefined while §15 P3 hands three mechanism decisions to it. (c) §15
P3(iii) proposes a tick table with RNG draws stored; the DBOS grounding names that shape's failure in the
wild — the version hash covers workflow source but not *step bodies*, so "stale outputs replay silently",
and Cairn's workers rewrite their own step bodies.

```diff
-    sizes; milliseconds below 60 bits), accept if the order is prime (acceptance ≈ c/ln p;
+    sizes; milliseconds through 50 bits — at 60 bits ≈75 ms per curve and the default PARI stack
+    overflows), accept if the order is prime (acceptance ≈ c/ln p, so expected tries grow like `ln p`
+    with a geometric spread whose sd equals its mean; observed draws span 20–220 at 30–50 bits and are
+    not a profile — M0 measures the constant over ≥50 seeds per size before declaring one;
-**M1** *Done when:* a deliberately-planted false "advance" is caught every time.
+**M1** *Done when:* across ≥30 planted advances spanning the three failure classes (false speedup,
+valid-proof/wrong-statement, non-reproducible measurement) there are zero escapes, INCONCLUSIVE counting
+as an escape, and no matched true advance is rejected.
-**M3** *Done when:* it reallocates off a stall unaided.
+**M3** *Done when:* on ≥20 seeded runs containing a stalled branch — gate-outcome yield over the last
+`k` ticks inside §6's A/A null band — funding is withdrawn within `m` ticks unaided.
   (iii) one tick = ... with its RNG draws stored, so a crash resumes from the last step,
+  with the *source hash of each step* in the tick record: replaying a recorded output from a step whose
+  body has changed is a silent stale read.
```

---

## (a) The three I would stake the most on

**1, 2, 3** — gates the plan calls mechanical that the machine underneath does not deliver, each caught by
a probe rather than by argument. A cross-check that cannot disagree, a verifier that reports success by
returning nothing, and an independence property a `Read` tool dissolves are one failure in three places:
enforcement asserted, not obtained — the exact failure §4 names, landing on the three gates that carry the
most weight. Proposals 4 and 5 are next, pure arithmetic against numbers the repository already holds.

## (b) Where the framing is wrong

**The plan writes its stack facts in the voice of its verified facts.** Its architecture is evidenced at a
standard I have rarely seen; its *stack* claims are inherited from briefs whose own calibration
(`PROPOSALS.md` §5: no repo built or run, citations printed by the agent that wrote them, one benchmark on
one seed) the plan drops. The grounding probes are the project's first executed evidence and they overturned
three stack claims on first contact — Sage is not installed, the verifier subprocess fails open, skeptic
isolation is discipline. Read that as a prior, not an accident: the untested stack claims here are wrong at
a meaningful rate, and each sits *under* a gate. A harness whose founding document tags its own claims less
carefully than it will require of its workers has a credibility problem on day one.

The repair is a paragraph in §16 and a line in §13: every stack fact carries the tag its source assigns it,
and **M0's first act is to populate `research/grounding/` by executing the facts M0 stands on** — which a
parallel session is doing now, and which the plan does not list as M0 work. §13 is right that contact with
a running system reveals what the whiteboard cannot; it should say the same of contact with the *stack*.
Smaller: §12 states an operator legal ruling as a derived constraint — keep it, label it as one.

## (c) Facts I would need that the plan does not state

1. The baseline the ladder's A/A band is a ratio against — the most load-bearing unstated quantity here.
2. Whether a second, non-PARI backend will be installed; if not, what "agreement or raise" means at Tier 0.
3. The verifier's exact acceptance predicate, given a backend that exits 0 on fatal errors.
4. The Skeptic's tool allow-list, and whether it can read the substrate.
5. The core-hour number separating Tier 2 from Tier 3, rather than "hours" versus "days".
6. Who authors a skill's known-answer corpus, and whether it is the worker that authored the skill.
7. The M3 definition of "stall", since three deferred mechanism decisions hang off it.
