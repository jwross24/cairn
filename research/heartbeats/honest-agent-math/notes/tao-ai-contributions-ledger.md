# Tao's ledger of AI contributions to Erdős problems

Source: https://github.com/teorth/erdosproblems/wiki/AI-contributions-to-Erd%C5%91s-problems, read 2026-10-30.
"The wiki is no longer updated. The latest data is as of Jun 30, 2026." Last edit shown by Nat Sothanaphan.
"The information provided on this wiki is provisional rather than final." "This page is not a benchmark."

## Taxonomy
Sections by provenance of the idea, not by outcome:
- 1(a) AI standalone: comparable literature unknown, human involvement non-significant.
- 1(b) AI alongside literature: comparable literature "discovered _afterwards_", with a "Similar?" column
  (problem 333: "Yes"; 120: "No"; 1026: "Only after applying an argument from Seidenberg (1959)").
- 1(c) AI building on literature known beforehand; 1(d) AI collaborating with humans (significant involvement).
- 2(a) literature search, 2(b) formalization, 2(c) rewriting, 2(d) computation.
Outcome per entry: 🟢 full resolution, 🟡 partial, 🔴 incorrect, ⚪ unverified; labels like "Full solution (Lean)",
"Solution to variant problem", "Candidate full solution".

## Recorded failures (examples)
11 "Incorrect claim made"; 51 and 616 "Incorrect proof found"; 358 "Argument with major gaps made"; 1040 partial on
one part, "incorrect solution to other part"; 1105 a correct literature find that "Gave some wrong references";
851 literature search "Confused with another problem"; 481 "Unwittingly reproduced existing proof". No formal
retraction process is described.

## For cairn
- Two axes recorded separately: where the idea came from (standalone, found-afterwards, building-on) and whether it
  holds (full, partial, incorrect, unverified). cairn's calibration tag covers the second; the first, novelty
  provenance, is what Olagoke's census found most costly ("already known", 6 of 42 verdicts) and cairn does not record.
- "Solution to variant problem" as a named outcome is the statement-drift case made visible rather than hidden.
- Wrong references and problem confusion in literature search (1105, 851) are fabrication in the citation channel,
  which no kernel sees; cairn's empirical-claim reproducibility node does not cover citations either.
- A maintainer-run ledger that stopped updating on 2026-06-30 is itself evidence of Olagoke's "verification debt".
