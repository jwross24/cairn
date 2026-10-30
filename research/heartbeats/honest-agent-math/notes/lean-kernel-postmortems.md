# Lean kernel postmortems: the Collatz exploit and the bug hunt that followed

Sources:
- Leonardo de Moura, "Postmortem for Kernel Soundness Bug #14576", 2026-08-01,
  https://leodemoura.github.io/blog/2026-8-1-postmortem-for-kernel-soundness-bug-14576/
- Leonardo de Moura, "Postmortem for the Kernel Soundness Bug Hunt", 2026-08-24,
  https://leodemoura.github.io/blog/2026-8-24-postmortem-for-the-kernel-soundness-bug-hunt/
- A timeline digest (Chinese): https://arch.gh.wzhecnu.cn/ChatBlog/blog/lean-conjecture-soundness-bug-collatz-comparator-nanoda
- Lawrence Paulson, "Why is it all in the kernel?", 2026-07-30, https://lawrencecpaulson.github.io/2026/07/30/Collatz.html
Read via Exa search extracts 2026-10-30; the full posts are not yet read.

## The Collatz exploit (#14576)
- 2026-07-25: Ramana Kumar published `xrchz/CollatzLean` (commit `a793574`, "Finish disproof"), a `sorry`-free,
  axiom-free AI-assisted "disproof" under 500 lines. It built `Expr`, projections and `Declaration`s by
  metaprogramming and sent them to the kernel with `addDecl`.
- Official kernel bug: when eliminating a nested occurrence under an inductive `T` with phantom parameters `Ds`, the
  parameters vanished from the generated auxiliary type and escaped type checking. "only reachable through
  metaprogramming"; the elaborator catches it on normal input. "an implementation bug, not a hole in Lean's
  meta-theory."
- nanoda bug (separate): it "did not verify the type name in a projection node"; fixed in `ammkrn/nanoda_lib#22`
  (2026-07-27) a week before the Lean report, after Jeremy Chen reported it. "The proof was built so that the
  expression the kernel never inspects is one that the old nanoda accepted." Joachim Breitner: "a proof that passes
  two independent checkers with two independent bugs." lean4lean shared the official bug (a port).
- 2026-07-28 03:28 UTC Kiran Gopinathan reduced it to a proof of `False` (#14576); fix #14577 merged 13:39; released
  in Lean 4.32.2 the same day. A Zulip thread drew 202 messages from 39 participants.
- Follow-ups: #14582 checks that nested-occurrence parameters behave as parameters; regression tests in the Kernel
  Arena; comparator.live runs nanoda by default and tracks it daily; LeanEval requires both the standard kernel and
  nanoda to accept (lean-eval #486, 2026-07-30).

## The bug hunt (2026-08-24 postmortem)
Daniel Selsam at OpenAI, with a security-specialized model, found further kernel bugs (#14607–#14616, all caught
by nanoda), then soundness bugs "The OpenAI internal model managed to exploit all of them to get the official
kernel to accept a proof of `False`":
- #14613 sorts as Prop up to universe normalization; #14616 declarations naming nested auxiliary types; #14806
  order-independent `is_def_eq` caching (nanoda and ind-models rejected the bogus proofs);
- #14807 with #14843, the `is_prop` check: **"The bogus proof was accepted by `nanoda`."** ind-models rejected it;
  lean4lean did not have the bug.
So no single external kernel caught every bug: nanoda missed #14807, lean4lean shared #14576.

## cairn's pin, by git ancestry (verified 2026-10-30)
`gh api repos/leanprover/lean4/compare/<merge>...v4.34.0-rc1`: #14577 (merged 07-28), #14613 and #14616 (07-31) are
in rc1. #14582 (08-12), #14806, #14807, #14808 (08-18) and #14843 (08-19) are not. rc1 therefore carries kernel bugs
that a model is documented to have exploited into a proof of `False`.

## For cairn
- Moves cairn-p76j's R5 from inference to documented: the missing fixes are exploited soundness bugs, not hygiene.
- Kernel diversity is necessary but not sufficient: each external kernel missed at least one bug the others caught.
  `--paranoid` with all bundled kernels (v4.35.0) is the configuration no documented exploit has beaten.
- Paulson's counterpoint: he knows of no prior case where an independent checker caught a soundness error that got
  past a proof assistant's kernel, and argues for a smaller kernel instead of proof-object rechecking.

## Full bug-hunt postmortem (read 2026-10-30)
- Ran 2026-07-30 to 2026-08-20, when the AI "could not find additional issues". Daniel Selsam (OpenAI) with internal
  models; a document explaining comparator and external checkers was in the agents' prompt, which told them "not to
  spend time trying to corrupt memory". "None of the groups using publicly available models reported any bugs."
- Runtime soundness, exploited to corrupt memory and prove `False`: #14838 (freeze objects on reference-count
  overflow, Koka-style sticky counts; "rejected by `nanoda`, and any other external checker not based on the Lean
  runtime") and #14833 (require GMP 6.3.0: Linux CI built binaries against GMP 6.1.2, which has an exploitable bug;
  the model found it by noticing the distribution's GMP version). #14849 bounds kernel `Nat` numerals after the model
  built a multi-gigabyte numeral hitting another GMP 6.1.2 bug.
- Not soundness: #14607, #14608, #14609, #14615.
- "Lean v4.33.1 (released August 21) contains fixes for all issues found in the kernel bug hunt." `lake check` from
  v4.35.0; two lean4checker builds planned (GMP and mpn); `lean-inductive-models` (Breitner) models inductive types
  from first principles; verified kernels "are not immune to bugs in the Lean runtime".
- Threat model: "We consider AI-generated proofs a potential source of malicious proofs." "`lake build` does not
  protect users from adversarial proofs."

For cairn: v4.33.1 (2026-08-21) carries every fix; v4.34.0-rc1 (2026-08-10) does not, despite the higher version
number. cairn's container (`bundle/Containerfile`) installs the official Linux aarch64 rc1 release, and #14833 is
in the rc1→v4.34.0 diff, so the GMP 6.1.2 exploit plausibly reaches cairn's gold-arm checker. Not verified: which
GMP the rc1 Linux release statically links.
