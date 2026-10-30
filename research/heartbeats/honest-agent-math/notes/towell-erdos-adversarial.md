# Towell: one Claude Code session on the Erdős problems database

Source: Alex Towell, "What Happens When You Let an AI Loose on 1,000 Erdős Problems", metafunctor.com,
2026-03-16, updated 2026-07-09, https://metafunctor.com/post/2026-03-16-computational-explorations/.
Code and provenance: https://github.com/queelius/computational-explorations (`docs/provenance_and_verification.md`).

## Setup
One Claude Code session (Opus 4.6), 131 subagents, about 70 of Tao's 1,183 Erdős problems attacked
computationally. 92 Python modules, a Glucose4 SAT solver, 5,922 tests, 8 Lean files (2 with zero `sorry`),
5 LaTeX papers on Zenodo. The human's main instruction: "Try to disprove our discoveries." "Claude is good at
building things. It needed to be told to try to tear them down."

## What the adversarial pass caught
1. A small-case pattern that broke: S(G,2) looked to depend only on group order, holding for abelian 2-groups
   through order 64 and for squarefree orders, then failed at 49: S(Z/49Z, 2) = 32, S(Z/7Z × Z/7Z, 2) = 28.
2. Overfitting: MS(k) = 2^((3^k+1)/2) − 1 fit three data points; four other three-parameter formulas fit them too.
   "Three data points is three data points."
3. Definition drift between code and proof: code and a Lean file used 0- and 1-based indexing for density Schur
   numbers and gave different answers.
4. A heuristic that failed silently: random sampling estimated R_cop(4) at 20; the SAT-verified value is 59.
   "random search fails silently on rare objects."
No fabricated results reported. The author says he can verify the engineering, not the deep mathematics.

## For cairn
- Item 1 is RULE 2's "small-case patterns stay CONJECTURE until they survive larger cases plus a deliberate
  counterexample hunt" happening in the wild: a pattern true across every 2-group through 64 broke at 49.
- Item 3 is the same failure as Brosse's "computed a different quantity": the claim and the computation disagree on
  what is being measured. A reproducibility node should pin the definition and index convention, not only the code.
- Item 4: a negative result from a heuristic search is not evidence of absence. cairn's no-go checklist should keep
  heuristic and exact searches in separate calibration tiers.
- A single practitioner account, low reach, no numbers beyond these four incidents.

## Leads out
- https://github.com/queelius/computational-explorations/blob/main/docs/provenance_and_verification.md
