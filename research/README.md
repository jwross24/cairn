# research/ — mechanism mining for Cairn (2026-08-21)

What this directory is: the evidence behind `PROPOSALS.md`, which proposes revisions to
`../PLAN.md`. `PLAN.md` itself is untouched; the proposals are for review before anything lands.

## How it was produced

- Six primary repos cloned at their latest stable tag (frankengraphdb has no tag; default branch):
  asupersync v0.4.9 @ 9eb0600e · frankensqlite v0.3.7 @ 9b1d3ed7 · frankenfs v0.2.0 @ 77b0a032 ·
  frankensearch v1.6.0 @ 4302c377 · franken_markdown v0.3.4 @ 562f4bd9 · frankengraphdb @ cfac1667.
  Together ≈7M lines of Rust, so every dive is mechanism-targeted: locate, read implementation
  bodies, find the tests, classify status (real / partial / stub / vestigial / dependency-only).
- One dedicated deep-dive agent per repo (`briefs/<repo>.md`), two focused second reads on the
  e-process / conformal / certificate / gate family that spans the suite
  (`briefs/focus-*.md`), and five adjacent-space fan-outs (`briefs/adjacent-*.md`) over
  content-addressed stores, anytime-valid statistics, agent orchestration, proof automation, and
  distributed collision search. Reviewer spot-checks of the load-bearing lines are recorded in
  `PROPOSALS.md` where they were done.
- Every brief cites repo@commit and file:line, or paper section / spec section, for each claim.

## Evidence tags used throughout

- **PROVEN-in-source**: implementation read and judged correct, and tests that exercise it read.
- **STRONG-EMPIRICAL**: implementation read and tests/benchmarks seen; correctness not fully verified.
- **CONJECTURE**: plausible from code/paper; fit for Cairn unverified.
- **SPECULATION**: README-only, stub, or vestigial.

These are the same four tags Cairn uses for claims (PLAN §7); using them on the proposals themselves
is deliberate.

## Standing constraint surfaced by the dives (read before borrowing anything)

All six repos ship the same `LICENSE`: "MIT License (with OpenAI/Anthropic Rider)"
(`LICENSE:1-45` in each; text identical). "Restricted Parties" include anyone acting on behalf of
or for the benefit of OpenAI or Anthropic, and "use" is defined to include analyzing, indexing, or
incorporating the software into "any dataset, training corpus, evaluation harness, or pipeline for
machine learning or other automated systems." Cairn is an agent-operated harness. The engineering
consequence adopted in `PROPOSALS.md`: **borrow mechanisms re-implemented from the primary papers
and specs; never vendor code from, or take a crate dependency on, any of the six.** Every
mechanism worth borrowing is small (tens to a few hundred lines) and textbook, so this costs little.
Whether any further legal question exists is the operator's call, not something this review decides.

## Index

| File | What |
|---|---|
| `PROPOSALS.md` | Consolidated proposed revisions to PLAN.md: rationale + diff each, confident vs. needs-prototype, explicit rejects, naming, where the reviewer would stake most / least. |
| `briefs/asupersync.md` | Deep dive: lab determinism + exact-dispatch replay receipt, obligations, budgets, e-process, conformal, RaptorQ (real, homeless), Lean/TLA posture. |
| `briefs/frankensqlite.md` | Deep dive: negative-results ledger preflight gate, A/A-null decision band, e-process gates (as a gate-skipper: do not copy), release certificate, provenance, hash-chained markers. |
| `briefs/frankenfs.md` | Deep dive: fail-closed claim-state evaluator, executed-evidence type, Beta-posterior redundancy autopilot; no e-process, no content addressing; RaptorQ is asupersync's. |
| `briefs/frankensearch.md` | Deep dive: certified recall lower bound, conformal rank calibration, an INVALID phase-gate "e-process", golden-vector skill certificate, gauntlet evidence protocol, SimHash, RRF. |
| `briefs/franken_markdown.md` | Deep dive: conformance corpus + ratcheted floor, claims registry with proof pointers, planted-failure gate self-tests, determinism by construction. Renderer irrelevant. |
| `briefs/frankengraphdb.md` | Deep dive: claim-class lattice + evidence envelope, proof-lane gate, hash-chained commit markers with CAS heads, fork-at-boundary semantics. Storage not accretive. |
| `briefs/focus-frankensqlite-eprocess-family.md` | Second read of fsqlite's statistical-gate files: ratchet policy, gate runner, split-conformal threshold; misuse catalog. |
| `briefs/focus-calibrate-evidence-certificate-family.md` | Second read across fgdb-calibrate / fgdb-evidence / frankensearch certificates / frankenfs repair: what "certificate" and "conformal" actually mean in each. |
| `briefs/adjacent-cas-reproducible-compute.md` | REAPI canonicalization + cache bits, Nix fixed-output + `--check` + GC roots, Buildbarn completeness, in-toto, Hermit/FDB; no off-the-shelf CAS fits. |
| `briefs/adjacent-anytime-valid-stats.md` | Exact e-process for the small-numbers gate, why no sub-grades, selector audit martingale, why conformal drift detection is a weak fit; libraries. |
| `briefs/adjacent-agent-orchestration.md` | FunSearch/AlphaEvolve/Shinka allocation as actually coded, AI-Scientist/CUDA-Engineer/DGM failure incidents mapped to Cairn gates, durable execution, skeptic isolation. |
| `briefs/adjacent-proof-automation.md` | mathlib coverage table @1f29011, comparator/SafeVerify/leanchecker as the PROVEN verdict, sorry-leak errata, statement-review linters and vacuity checks, tooling maturity. |
| `briefs/adjacent-distributed-collision-search.md` | vOW certificate schema, BLS §6 ladder protocol, 2016 record verification methodology, Sage/PARI self-test seeds, measured 30/40/50-bit ladder numbers, M0 curve generator. |
