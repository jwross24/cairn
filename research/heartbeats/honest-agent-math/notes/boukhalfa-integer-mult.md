# Boukhalfa: three days of agent-driven work on integer multiplication bounds

Source: Chafik Boukhalfa, "Three days of agent-driven mathematics", 2026-10-11,
https://cfky.dev/posts/three-days-of-agent-driven-mathematics/. Project repository:
https://github.com/CrocSwap/integer-mult-bounds (maintained by Douglas Colkitt, a "research, review, and
integration record"); the framework comes from the preprint at
https://github.com/openai/math/tree/adc7f1241b42e322a6451854ab7e4b4c146bf78a/preprints/Integer-multiplication-below-n-log-n-September-23-2026.

## Setup
A harness engineer ran agents with separate workspaces, bounded compute and distinct roles (exploit near the
current best construction, explore larger departures, check proposed improvements) across a Mac and two DGX
Sparks. 55 PRs from this author into a public multi-contributor repository; 48 bound submissions took the exponent
saving κ from about 0.000041 to 0.001020. Models not named.

## No fabrication reported; the failures were subtler
- Proxy metrics misled: PR #233 improved one component about 1.28% and PR #417 another about 2.2%, and κ did not
  move either time because a different component was the bottleneck.
- The obvious objective was wrong: a 29-addition circuit beat a 27-addition one through reuse.
- Gains were not additive: two valid improvements to overlapping parts interfered and had to be repriced together.
- Stale work: agents improved a construction after someone else had published a stronger starting point.
- Scope: PR #256 machine-checked specific properties in a Lean framework but did not prove the full theorem.

## Evidence tiers
"a promising construction, a successful finite replay, and a complete theorem are different levels of evidence."
Figure 1: "These are conditional claims, not a verified leaderboard." Useful negative results: an exact constraint
solver proved the local design optimal within its search class (PR #296); PR #212 bounded the remaining gain of
one tuning approach at about 1.8%.

## For cairn
- The three tiers map onto cairn's calibration ladder (CONJECTURE, empirical, PROVEN); a public, multi-agent
  project drew the same lines without being asked to.
- A proven bound on how much a search can still gain (PR #212) is a result cairn's ladder should be able to record:
  it closes a branch with evidence rather than with an absence of progress.
- Peripheral to the fabrication question: no false claim is described. Kept for the evidence-tier language and the
  review-record repository.

## Leads out
- https://github.com/CrocSwap/integer-mult-bounds (how the maintainer reviews and integrates agent PRs)
- The openai/math preprint directory (OpenAI's own statement of what is proved)
