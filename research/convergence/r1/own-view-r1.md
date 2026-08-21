# Synthesizer own view — round 1 (written before opening any seat file)

Plan under review: `research/convergence/plan-r0.md` (v3). Five weaknesses, ranked by what
a fresh implementer would hit first.

## 1. REFUTED-by-hash keys on an undefined object (§3, §4) — HIGH

§3 hashes an *artifact* by `(skill@version, inputs-by-hash, seed, tool-versions,
container-digest)`. §3 and §4 then say a proposed branch is recognized as dead when "its
hash matches a REFUTED entry" and the ledger record carries a `hypothesis hash`. These are
different objects and the plan never says what the hypothesis hash is computed over. The
ladder (§6 step 1) generates a fresh random instance and seed per run, so two honest
attempts at the same hypothesis never share an artifact key; `Blocked` can only fire if
the hypothesis is canonicalized separately (e.g. recipe with instance/seed fields
elided, or a typed hypothesis object with its own canonical encoding and test vector).
Without this the ledger has no teeth, which is the whole point of §3 "dead-ends become
structural". Fix: define the hypothesis key (what is in, what is out, canonicalizer and
known-answer vector, where it is computed — at preflight, by the gate layer).

## 2. Ladder trial counts do not fit the tier it is assigned to (§5, §6) — MED

§5 places the ladder in Tier 1 ("one core, minutes"; "toy DLPs 30–60 bit"). §6 requires
≥10² independent trials per size and completion at 60 bits. At 60 bits generic rho is
≈1.25·2³⁰ ≈ 1.3×10⁹ group ops per trial; 10² trials ≈ 1.3×10¹¹ ops, i.e. tens of
core-hours in PARI/Sage, not minutes. Either the 60-bit rung is a Tier-2 validation step,
or trial counts scale down with size while the scaling fit carries the evidence, or the
baseline at 60 bits is a model (not re-measured each run). A fresh implementer will build
a ladder that cannot run inside its own tier budget and the tier gate (§5) will refuse it.

## 3. "Outside the orchestrator's write path" is a property, not a mechanism (§4) — MED

The gate plan, no-go set, non-goal sets and waiver registry "live with the gates, outside
the orchestrator's write path." In an M0 single-process SQLite system this is a code
convention. §0 says meta-level fixed; §3 gives the ledger a tamper-evident log, but gate
*configuration* has no stated enforcement boundary (separate process and read-only
mount? separate DB file the orchestrator's connection cannot open? hash-pinned gate
bundle verified at gate start?). A fresh implementer needs the boundary named so that
"the orchestrator cannot bypass a gate" is checkable.

## 4. The tier gate's admission ticket is undefined (§5, §13 M0) — MED

"Each tier's admission ticket is a result from the tier below" and "entered only holding
a strong Tier-1 signal" are not predicates. M0 builds a tier gate and its done-when is a
cost-tagged node, but nothing says what the gate reads (declared profile, remaining
budget, a ticket node of which status/grade) and what it refuses. Without a ticket
predicate the gate is either vacuous or invented at build time by the implementer.

## 5. Orphan prerequisites in the build order (§13) — MED/LOW

- The ladder (§6, built at M1) compares against generic baselines (rho with distinguished
  points, BSGS) and needs an instance-maker (`x` random, `Q = xP`) — none of these appear
  as built components in any milestone; M0's exemplar returns `(p, a, b, n, P)` only, yet
  M0's verifier checks `xP == Q`.
- §7's Challenge module: who authors it and by what path does it reach the gate's store?
  If the Formalizer (a gated worker) writes the Challenge, the "thing stated" half of the
  check is unguarded. Authorship should be the Reframer/human, stored with the gates.
- The near-duplicate advisory (M2) routes to the Librarian, who is built at M4.

## Factual items to check against grounding/briefs during evidence review

- `leanchecker --fresh` (§7): the Lean 4 external kernel checker is `lean4checker`.
- `ellcard` / `cardinality(algorithm='all')` (§13 M0): confirm names and behavior.
- mathlib coverage and pin (`@1f29011`, `v4.34.0-rc1`) (§11): confirm recorded in grounding.
- "MIT with OpenAI/Anthropic Rider" (§12): confirm in briefs.
