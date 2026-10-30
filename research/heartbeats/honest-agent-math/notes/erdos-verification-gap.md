# Faster than they can be checked: the Erdős verification gap

Source: Subomi Olagoke, "Faster Than They Can Be Checked: Measuring the verification gap in AI-assisted
solutions to Erdős problems", preprint 2026-09-25, https://www.subomi.net/papers/faster-than-they-can-be-checked.
Data and code: https://github.com/ubmids/erdos-verification-gap.

## Data
251 proof claims on erdosproblems.com, 2026-07-14 to 2026-09-24; 224 on problems open when claimed. Joined with
the teorth/erdosproblems git history (2,614 status changes), Tao's AI-contributions ledger and the LLM Hunter
archive (2,112 attempts). 244 of 251 (97.2%) name an AI tool; no other authorship test.

## Funnel (224 claims on open problems)
Posted 224 → any comment 108 (48.2%) → any verdict 42 (18.8%) → verified full or partial 31 (13.8%) →
accepted by moderators 9 (4.0%). 54 of 116 full-solution claims got no comment at all.
Verdicts: 31 verified, 6 already in the literature, 3 misstated or a technicality, 1 refuted, 1 dismissed in error.

## Time
Median time to verdict 1.1 days (p75 5 days, n=39). Kaplan–Meier share with no verdict: 0.85 at 7 days,
0.82 at 30 and 60. "Verdicts arrive quickly or not at all." 185 claims waiting, median 53 days.

## Lean made no measurable difference
106 claims with a Lean formalization: 11.3% verified; 118 without: 16.1% (p = 0.52). Only 47 of 118 commented
threads discussed the formalization. Claim 172 declared a custom `axiom growth_ineq`, assuming the key
inequality; nobody followed up. Problem 742 had a complete formally verified proof dismissed as "already
solved", which was true only for large n; nobody corrected it.

## Recommendations
Visible timestamped status per claim; a formal-verification checklist (statement from a third party, published
axiom output, kernel replay); review dismissals as well as claims; shared per-problem literature searches.
"expert adjudication, more than proof generation or proof checking, is the scarce resource."

## For cairn
- Base rate for scrutiny scaling (RULE 2): of AI claims on open Erdős problems, about 1 in 7 is verified and
  1 in 25 accepted. A claim arriving without adjudication is the normal case, not the exception.
- Claim 172 is the textbook case for cairn's axiom gate: a custom `axiom` in a "proof". cairn refuses non-permitted
  axioms; the paper shows a public venue does not.
- "Already known" (6 of 42 verdicts) and "misstated" (3) are failures no kernel catches. cairn's no-go checklist
  and statement-level match review are the analogues; a literature check per claim is not something cairn has.
- Wrongful dismissal (problem 742) argues for cairn recording refutations and "known" verdicts with the same
  provenance as proofs.
- The three checklist items match cairn's gates one for one (Formal Conjectures statements, axiom tool, kernel
  replay); the paper is external evidence they are the right three.

## Leads out
- https://github.com/ubmids/erdos-verification-gap (per-claim data)
- https://github.com/teorth/erdosproblems/wiki (Tao's AI-contributions ledger)
- https://github.com/mehmetmars7/Erdosproblems-llm-hunter (2,112 attempts, 22 reviews)
- arXiv 2609.25050 (FrontierMath Erdős), 2608.16753 (Tao ICM)
