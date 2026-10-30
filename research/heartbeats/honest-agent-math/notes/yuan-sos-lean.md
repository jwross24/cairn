# Yuan: automating theorem proving on low-rank sum-of-squares

Source: Chenyang Yuan, "Reflections on automating theorem proving", 2026-10-07,
https://chenyang.co/blog/math-research.html; earlier harness post at
https://chenyang.co/blog/automatic-theorem-proving.html; the univariate base result https://arxiv.org/abs/2205.11466.

## Setup and progression
Benign nonconvexity of low-rank sum-of-squares decompositions, case by case in (n, d, r):
- Feb–Mar 2026, GPT 5.3, n=2 d=2: agent-written proofs "either have mistakes or omissions of key details";
  asking agents to "check more carefully" made "the mistakes becoming harder to find". Not verified.
- Apr 2026, GPT 5.4: formalized the existing univariate proof in Lean in a few hours, then n=2 d=2 r=4 in Lean.
- May 2026, GPT 5.5 Pro: n=3 d=2 r=7, about a 20k-line Lean proof in a day.
- Jul 2026, GPT 5.6: n=2 d=3 r=5, about a 100k-line Lean proof over days, up to 10 parallel subagents in sandboxes.
  "when given a problem that is too hard, it will give up and say that no proof has been found, instead of
  returning a false proof."
- Sep 2026, GPT 6: a counterexample to the author's own general conjecture at n=2 d=5 r=7 in about 30 minutes.

"the bottleneck is now in verification, since proof generation is cheap."

## For cairn
- Self-review in the same context made errors harder to find, not rarer: the same lesson as Brosse's shared-context
  certifications, from a single practitioner. Review in the producing context is a polish step, not a check.
- Abstention as model behavior arrived with GPT 5.6 in this account. cairn should count "no proof found" as an
  honest outcome and not penalize it in any score a worker can see, or the incentive runs back toward fabrication.
- The conjecture-refuted-by-a-counterexample outcome is the counterexample hunt RULE 2 requires, run by the model.
- No fabrication incidents with numbers; peripheral to the core question.
