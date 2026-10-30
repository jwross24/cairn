# Lean Comparator (leanprover/comparator)

Source: https://github.com/leanprover/comparator README, read 2026-10-29 (repo last pushed 2026-10-14, 247 stars).
Lean reservoir page: https://reservoir.lean-lang.org/@leanprover/Comparator

## What it is
A judge for Lean proofs built by the Lean FRO for the AIMO competitions. Given a trusted `Challenge` module and an
untrusted `Solution` module, it guarantees that each listed theorem in `Solution` proves the same statement as in
`Challenge`, uses no axioms beyond `permitted_axioms`, and is accepted by the Lean kernel; optionally also by
external kernels such as nanoda. It sandboxes the solution build with `landrun` and exports the environment with
`lean4export`.

Deprecated: merged into Lean core in v4.35.0 as `lake comparator` and `lake check`, "the only ones guaranteed to
receive further security and performance improvements."

## Stated trust assumptions
- Challenge imports and lakefile are trusted.
- The checker has never compiled the Solution or other adversarial files before checking, since that could
  compromise the Challenge.
- landrun's sandbox holds (a systemd-run wrapper guards a landrun hole fixed in Linux 7.1).
- At least one kernel is correct.

## Definition holes
Name, type, universe levels and safety must match, but the README warns these "can be gamed": with
`def ChallengeSolution : Prop := sorry` and `theorem challenge : RiemannHypothesis ↔ ChallengeSolution`, a
solution sets `ChallengeSolution := RiemannHypothesis` and proves by reflexivity. Definition-hole solutions
"must always be checked with an additional (potentially human) verifier."

## For cairn
- cairn's `lean/Cairn/StatementHash.lean` hashes the elaborated `Expr` of a constant, not its source text, so a
  preamble `local notation` that changes what the statement elaborates to changes the hash. That is the defense
  the DeepMind swarm lacked. Verified: the hash walks `Expr`. Not yet verified: that the reference hash is
  computed in an environment the candidate cannot influence (Comparator's assumption 2).
- cairn pins `leanprover/lean4:v4.34.0-rc1`; `lake comparator` arrives in v4.35.0. Candidate adoption as a
  second, independent statement-and-axiom check beside cairn's own.
- The definition-hole gaming example is a template for cairn's no-go checklist: any challenge with an open
  `def` needs a semantic reviewer, not only a type match.

## Leads out
- Lean v4.35.0 release notes for `lake comparator` / `lake check`
- arXiv 2604.03789 (Automated Conjecture Resolution with Formal Verification) used Comparator on a full project
- Axle's comparator endpoint: https://rc.axle.axiommath.ai/v1/docs/endpoints/comparator
