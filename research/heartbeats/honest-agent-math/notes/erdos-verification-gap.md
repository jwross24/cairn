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
  and statement-level match review are the analogs; a literature check per claim is not something cairn has.
- Wrongful dismissal (problem 742) argues for cairn recording refutations and "known" verdicts with the same
  provenance as proofs.
- The three checklist items match cairn's gates one for one (Formal Conjectures statements, axiom tool, kernel
  replay); the paper is external evidence they are the right three.

## Leads out
- https://github.com/ubmids/erdos-verification-gap (per-claim data)
- https://github.com/teorth/erdosproblems/wiki (Tao's AI-contributions ledger)
- https://github.com/mehmetmars7/Erdosproblems-llm-hunter (2,112 attempts, 22 reviews)
- arXiv 2609.25050 (FrontierMath Erdős), 2608.16753 (Tao ICM)

## Downgrades across Tao's ledger (own analysis, 2026-10-30)
Data: `data/ledger_events.json` from https://github.com/ubmids/erdos-verification-gap (1,086 parsed events across the
wiki's edit history, frozen 2026-06-30; 174,984 bytes, not stored here). Script: a one-off over that file.
- 727 distinct (section, problem) rows were ever added. 150 were first added green (full resolution), 33 of them
  labeled Lean.
- Colors changed 33 times; 16 of those are rows gaining a parsable color and carry no status change. The other 17
  are 8 upgrades and 9 downgrades. 3 of the 150 first-green rows were downgraded from green (problem 1190 in two
  sections, and 202), all to partial or candidate status, none to red. 0 of the 33 Lean-labeled green rows were
  downgraded. The one move into red was ⚪ → 🔴 on 503, "Argument with major gaps made", after 6 days.
- Downgrades came fast: 1, 5, 6, 7, 7, 7, 34, 35, 35 days after the row was added.
- 65 green or yellow rows were removed; 58 of those problems remain elsewhere in the final ledger, so these read as
  reclassifications between sections. 7 vanish entirely (2 green: 391, 1077; 5 yellow). Their reason is not recorded.
Limits: 359 rows were first added with no parsable color, so the denominator is uncertain. Rows here passed a human
curator, unlike the raw claims in the census above, so this measures survival after curation: at most 5 of 150
(about 3%) first-green rows lost their status, against 13.8% of raw claims ever reaching verified.
Consistent with "Verdicts arrive quickly or not at all", but a row the ledger stopped tracking after 2026-06-30 has
no further chance of a downgrade. I have not established how many downgrades would have followed.
