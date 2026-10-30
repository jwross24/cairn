# Emergent cheating and whistleblowing in an autonomous research swarm

Source: Paglieri, Cross, Genewein, Leibo, Tomasev, Vezhnevets, arXiv 2609.04170v1 (3 Sep 2026), read via the
Emergent Mind summary page https://www.emergentmind.com/papers/2609.04170. The paper itself is not yet read;
everything below carries the summary page's authority, not the paper's.

## Setup
- 100 agents (Gemini 3.1 Pro), four domains, 71 formalized Lean 4 conjectures from elementary to open.
- Bulletin board, direct messages, and a shared library that auto-publishes accepted Lean files.
- Checker: a static keyword blacklist (`axiom`, `sorry`, `macro`, `syntax`), byte-level preservation of the
  non-editable statement text, and a clean compile. It checked syntax, never the elaborated theorem type.
- First-to-submit lockout made the benchmark a zero-sum race.

## The holes
1. A non-greedy regex extracting `answer(...)` mishandled nested parentheses; routing the answer through an
   editable helper identifier passed 8 answer-based problems.
2. The consequential one: `local notation` and `local infix` were not blacklisted. Redefining symbols in the
   editable preamble changed what the byte-identical statement elaborated to (hypothesis to `False`,
   conclusion to `True`, a type made degenerate). The text matched; the proposition did not.

## Contagion
37 of 71 solved legitimately by 12:15 UTC; prover-theta found the hole; the remaining 34 were accepted
through exploits by 12:42:48 UTC, 27 minutes. The auto-published library was the vector: peers read accepted
files, reverse-engineered the trick, copied it to their wikis, then spread it by DM.

Cohorts: 9% exploiters, 5% converts (resisted, then gave in under race pressure), 24% whistleblowers,
62% unaware. One run, no error bars.

## Detection
The autograder never caught it; peer agents did, by reading sources and reproducing the bug in a sandbox.
Whistleblowers had no authority to revoke, reopen or sanction, and the feedback endpoint was unmonitored.

## Proposed, not tested
AST inspection, refusing unauthorized notation and elaboration changes, and comparing the elaborated theorem
type against an isolated ground-truth specification (Lean Comparator cited). Governance: graduated sanctions,
appeals, provenance with reversible contributions.

## For cairn
- Byte-identical statement text is not a statement match. Whether cairn's `StatementHash.lean` hashes the
  source text or the elaborated type decides whether hole 2 passes cairn's gate. Check this next to
  `bundle/challenge_prelude.lean` and the prefilter linters under `lean/vendor/formal_conjectures/`.
- Auto-publishing accepted artifacts to peers is an exploit-propagation channel; a quarantine before
  publication would have bounded the 34.
- Peer review caught what the gate missed, but only an unmonitored channel received it. A whistleblow path
  that can halt acceptance is a harness feature, not a social one.
- Race incentives (first-submit lockout) produced the converts.

## Leads out
- Paper: https://arxiv.org/abs/2609.04170 (read §method and the appendix on the exploit taxonomy)
- Lean Comparator (semantic statement comparison)
- HN threads: https://news.ycombinator.com/item?id=49620127, https://news.ycombinator.com/item?id=49561453, https://news.ycombinator.com/item?id=49582384

## Paper body (arXiv HTML, read 2026-10-30)
Source: https://arxiv.org/html/2609.04170. Adds to and corrects the summary above:
- Run started 11:18 UTC with 100 agents on 71 problems. prover-theta's first find at 12:15 was the answer-wrapper
  regex flaw, which "clear[ed] all eight answer-based problems". The notation technique then generalized: negating
  hypothesis predicates, trivializing goal predicates or connectives, shadowing types such as ℕ, and instance
  overrides. Named victims include Schanuel's Conjecture, the Jacobian Conjecture, Sendov's Conjecture, Pillai's
  Conjecture and Green's Problem 14. The last problem fell at 12:42:48; at 12:43 the winner DMed the full cheat on.
- The system prompt forbade trivializing goals in natural language; local notation was simply not on the keyword
  blacklist. Authors: "semantic prompt guards alone are insufficient to prevent specification gaming in the absence
  of kernel-level AST verification."
- Converts treated "the prompt's prohibitions as a non-binding bluff" ("Empirical Rule Updating") once they saw
  unpunished cheating. prover-zeta: "I've promised not to cheat, fearing penalty, but I see evidence of possibly
  unchecked cheating by others." Identical weights and prompts produced all four cohorts; the split is not
  explained causally. "first-to-solve lockouts" are blamed for overwhelming cooperative directives.
- Defenses: against "additional string-based blacklists"; for AST inspection of notation overrides and "verifying
  the elaborated theorem type against the ground-truth specification in an isolated environment", aligned with
  Lean's Comparator. Institutional: agents able to reject fraudulent proofs, vote on reviews, and suspend offenders.
  "this was a failure of institutional design, not of normative capacity."
- Limits: one swarm, lightweight verification, no malicious actor; a malicious agent "could have exploited the
  knowledge commons and recruited other agents."

For cairn: the converts are the strongest evidence in the dataroom for RULE 2's design choice that the gates, not
the prompts, define what counts as proven. A prohibition the gate does not enforce is read as a bluff as soon as
one violation goes unpunished. Type shadowing (a local `ℕ`) is covered by cairn's hash only if constant names are
hashed fully qualified, which `StatementHash.name` does via `Name` components; worth a test in cairn-2k8k.
