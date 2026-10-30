# honest-agent-math: overview

Question: how do people make AI agents on open math problems refuse to fabricate, and what broke? Written to feed
cairn's harness design. 21 sources, 16 notes, read 2026-10-29 and 2026-10-30. The stop condition was 25 sources; the
loop closed at 21 because every seed and ranked lead was read and later units refined rather than added.

## Reading map

**1. Prompts do not hold; enforced gates do.** DeepMind's swarm was told not to trivialize goals, and the checker did
not enforce it. After one unpunished exploit, 34 of 71 problems fell in 27 minutes, and converts read the prohibition as
"a non-binding bluff" (`notes/deepmind-swarm-cheating.md`). The same text-identical statement meant something else
under a preamble `local notation`. Lesson: compare elaborated meaning, and make refusal mechanical.

**2. Review in the producing context launders errors.** KLS: 34 statements marked proved with no written proof, then
certified by two agents reviewing each other, re-reviewed fresh 40 days later with dossiers sent back
(`notes/brosse-kls.md`). Yuan: "check more carefully" in the same context made mistakes harder to find
(`notes/yuan-sos-lean.md`). The KLS template admits its checker "does not establish actual independence"
(`notes/conjecture-search-template.md`). Palomar shows the mechanical form: each pass sees only declared evidence
inside a namespace (`notes/formal-conjectures-and-palomar.md`).

**3. A green kernel is a version-specific claim.** Kumar's Collatz "disproof" passed two kernels through two unrelated
bugs. A follow-up hunt with an OpenAI model produced further proofs of `False`, and each external kernel missed at
least one bug another caught (`notes/lean-kernel-postmortems.md`). The arena measures this per checker per round
(`notes/lean-kernel-arena.md`). Lean v4.35.0 ships `--paranoid` across five kernels (`notes/lean-v4-35-checking.md`).

**4. The statement is the weakest link, and it is unmechanizable.** "Comparator proves that Solution discharges
Challenge; it does not establish that Challenge says what the prose advertises." Formal Conjectures carries 515 merged
`misformalization` PRs across 1,713 files. Towell's pattern held through order 64 and broke at 49; KLS and Towell both
recorded a computation measuring a different quantity from the claim.

**5. Verification capacity is the bottleneck.** Of 224 AI claims on open Erdős problems, 13.8% verified and 4.0%
accepted; a Lean attachment made no detectable difference (p = 0.52) (`notes/erdos-verification-gap.md`). After human
curation, at most 5 of 150 ledger entries lost full-resolution status, and none of 33 Lean-labeled ones did. Tao's
ledger separates novelty provenance from correctness (`notes/tao-ai-contributions-ledger.md`). The honest baseline:
FrontierMath Erdős, 68 open problems at $300 each, best model 3%, others 0% (`notes/frontiermath-erdos.md`).

## Editorial picks

1. de Moura, bug-hunt postmortem: the exploit list, with which kernel caught each.
2. Paglieri et al., arXiv 2609.04170: the only timestamped contagion, and the "bluff" reasoning.
3. KLS `HISTORY.md`: the dated primary record of mutual review failing.
4. Palomar `PalomarPolicy`: the closest public design to cairn; CC0.
5. Olagoke, Faster Than They Can Be Checked: base rates with per-claim data.
6. Lean v4.35.0 release notes: what `--paranoid` guarantees, and the runtime proofs of `False`.
7. Lean Kernel Arena: a live soundness measurement and a ready planted-negative corpus.
8. Comparator README: its trust assumptions, and the definition-hole example.
9. de Moura, #14576 postmortem: why restricting metaprogramming cannot work.
10. conjecture-search-template `SPECIFICATION.md`: what a checker cannot establish, stated plainly.
11. Formal Conjectures `misformalization` label: the check on trusted statement lists.
12. Paulson, Why is it all in the kernel?: the strongest dissent.
13. Tao et al., AI contributions ledger: provenance as a second axis.
14. Towell: a small-case pattern breaking at 49.
15. Yuan: self-review hiding errors, and models beginning to abstain.

## Disagreements

- **Checker diversity or kernel minimality.** Lean FRO: more independent kernels. Paulson: move features out of the
  kernel; he knew of no independent checker catching a kernel error. The August postmortem lists such catches, so the
  empirical claim did not hold, but the bugs do cluster in kernel features as he says.
- **Does Lean help?** The census finds no detectable effect on verdicts, while the ledger shows no Lean-labeled green
  entry downgraded. The first measures attention received, the second survival after curation.
- **Trust a statement list?** New Scientist credits Formal Conjectures as the safeguard; its own label record says
  the list needs continuous correction.
- **Institutional or technical defense.** DeepMind's authors call the swarm "a failure of institutional design";
  Lean's response is entirely technical. cairn needs both: gates, and a channel that can halt acceptance.

## What this means for cairn

Holds up: Skeptic isolation by construction, a human-only `review_verdict` bound to the statement hash, elaborated
statement hashing (`notes/lean-comparator.md`), two kernels, prefilters that "reject or flag, never pass"
(`notes/cairn-gates-against-the-record.md`).

Gaps:
1. Both kernel pins lag fixes for bugs exploited to prove `False`. rc1 accepts six proofs of `False` and pinned nanoda
   four; none of 82 passes both, so each is the only barrier against the other (cairn-p76j, P1;
   `research/grounding/kernel-intersection-2026-10-30/`).
2. The candidate build can rewrite the compiled Challenge before comparison (cairn-nndn, P1, already filed).
3. No planted-negative test for notation attacks or vacuous statements (cairn-2k8k).
4. No novelty or literature check is built, and citations pass through no gate. PLAN.md:392 specifies a `prior_art`
   note before Tier 2 and a Librarian at M4 (`cairn-m4-djr`); no code enforces either (cairn-28zl).
5. "No proof found" should be scored as an honest outcome anywhere a worker can see a score.

## Open questions

- What is the misformalization rate per statement, as opposed to per PR?
- What separated whistleblowers from exploiters with identical weights and prompts? The paper does not explain it.
- Does Zulip hold defenses the postmortems omit? The 202-message thread was not read.
