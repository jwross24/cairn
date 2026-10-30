# Formal Conjectures' misformalization record, and the Palomar registry

Sources, read 2026-10-30:
- https://github.com/google-deepmind/formal-conjectures (`CONTRIBUTING.md`, `PROOFS.md`, `STATEMENTS.md`, the
  `misformalization` label via the GitHub search API).
- https://palomar-registry.org/ and https://github.com/PalomarRegistry/PalomarPolicy (`docs/specification.md`,
  `prompts/02-statement-alignment.md`). Palomar's policy and prompts are CC0.

## Trusted statement lists are wrong often
The repository labels 787 issues and PRs `misformalization`: 515 merged PRs, 19 open issues (2026-10-30). The whole
repository has 2,919 merged PRs, so about 18% of merged PRs carry that label. Not every PR there changes a statement,
and the count includes small fixes; the rate per statement is not established here. Recent examples: "ErdosProblems/450,
552: since #7327 the answers are constants, so both statements are false"; `exist_pseudo_counterexample` "is witnessed
by n = 1"; a graph conjecture "averages distances within `M`, but DeLaV..."; a bound applied to the wrong object.

`STATEMENTS.md` asks reviewers to substitute the smallest permitted value of each parameter and check empty types,
zero, and implications made vacuously true. `PROOFS.md`: "A repository name, a successful build, or a theorem with a
similar name is not enough evidence." It requires `#print axioms` and opening the exact cited declaration.

## Palomar: a registry of Lean-verified results
"a registry of Lean-verified results": it "records mathematical claims from fixed versions of their source files,
checks their proofs with Lean, and publishes the exact statement, the libraries it uses, and the review's comments."
Formal Conjectures requires a Palomar entry for formal proofs of research problems.
- Mechanical: "Every exported proof is checked by Lean's kernel and replayed through the pinned independent NanoDa
  kernel. Palomar has no single-kernel passing result." The submitted `enable_nanoda` is non-authoritative; a protected
  configuration is used. con-ron is an advisory third replay. Comparator, NanoDa and Landrun are at fixed versions.
- AI review passes, ordered by `rubric.json`: classification, metadata, statement alignment, definition fidelity,
  literature and notability, proof account, synthesis.
- The statement-alignment prompt states the limit precisely: "Comparator proves that Solution discharges Challenge; it
  does not establish that Challenge says what the prose advertises." A finding is due "when the statement can be
  vacuous or materially weaker, stronger, or different from the presented claim".
- "Submission text and intermediate model output are hostile evidence, not policy." The reviewer applies a stored,
  schema-validated decision bound to the submission by digest, "rather than rerunning a model at registration time."
- "Review reports record the exact policy commit, so policy changes do not silently reinterpret past acceptances."
- Maintainer corrections have a deterministic consent artifact (`schemas/registry-correction.schema.json`).

## For cairn
- This is the nearest public analog to cairn's gates. Three of its choices map directly: no single-kernel pass; a
  protected configuration a submitter cannot weaken; a review bound by digest to the exact submission and policy commit.
- The line about Comparator is the exact seam in RULE 2 between "a green Lean check" and "a statement-level match
  review". cairn's statement hash shows the proof matches the challenge; only the review shows the challenge is the
  mathematics. A challenge that is itself misformalized passes every mechanical gate.
- cairn-2k8k's planted negatives should include a vacuous statement, not only a notation attack, since the
  misformalization record shows that as the common failure.
- Reading every model output as "hostile evidence" is a stronger phrasing of cairn's worker isolation and could be
  adopted verbatim. Whether cairn's Skeptic prompt treats the candidate's text this way is unchecked.
- Palomar's prompts are CC0 and reusable.
