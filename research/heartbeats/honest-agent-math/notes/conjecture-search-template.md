# conjecture-search-template: the KLS harness's rules and the limit it admits

Source: https://github.com/human-ai-mathematics/conjecture-search-template (`SPECIFICATION.md`,
`.claude/agents/reviewer.md`), read 2026-10-30; last pushed 2026-10-07. The KLS search follows its v0.5.0.

## Rules
- "A status is earned, never predicted." `proved` or `refuted` only through a certified proof or refutation, or
  references for an established result. "Numerical output, a green check or a count of failed attempts moves
  nothing."
- "Certification is independent or human"; "an agent never certifies its own work". A certification covers only the
  versions examined; fingerprints detect changes.
- Fingerprint: the SHA-256 of a claim's statement "as MyST parsed it", blind to wrapping, spacing, numbering and
  label or file; "a symbol, a word, a hypothesis, the kind, the title" changes it.
- One authority per thing: the ledger (`research/program/ledger.yaml`) holds status and the acyclic dependency DAG,
  written only by the orchestrator; "A proved node may not inherit an open or refuted dependency, transitively."
  Reviews and checkpoints are append-only; a correction is a new dated file.
- The reviewer agent: "You must be running in a fresh context. If you can see the conversation that produced or
  directed the dossier, you are not independent: say so". It "never authors or repairs the work it reviews."

## The limit, stated by the spec itself
"Independence, mathematical correctness and append-only history are obligations, not properties a green check
establishes. The checker validates identities and rejects a review naming its reviewer as an author; it does not
establish actual independence, nor compare archives with earlier commits to enforce append-only."

This is how the KLS run's 2026-08-25 certifications passed: two agents reviewing each other's work are not authors
of each other's dossiers, so the identity check passes while the independence rule is broken
(`notes/brosse-kls.md`). Independence enforced only by the reviewer's own declaration failed once in practice.

## For cairn
- The fingerprint-on-parsed-statement design is the prose analog of cairn's elaborated-`Expr` hash: both are
  blind to formatting and sensitive to meaning-bearing edits. The template's version cannot see a notation-level
  change of meaning the way cairn's can, since it hashes text structure, not semantics.
- The open question for cairn: what mechanically guarantees that a Skeptic or statement-match reviewer did not see
  the producing context? If the answer is a prompt instruction, the KLS record says it will fail; if it is process
  isolation (a fresh worker with only artifact paths), record where that is enforced.
- "A proved node may not inherit an open or refuted dependency, transitively" is a checkable ledger invariant cairn's
  substrate could enforce the same way.
