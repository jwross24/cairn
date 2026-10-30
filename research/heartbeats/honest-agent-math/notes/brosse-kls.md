# Brosse et al., AI agents on the KLS conjecture

Source: Nicolas Brosse, "AI Agents on the KLS Conjecture", 2026-10-09,
https://nbrosse.github.io/posts/kls-conjecture-search/kls-conjecture-search.html (the seed URL
`posts/human-ai-mathematics/...` is a JavaScript redirect to it). With Jia Li and Yuwei Lyu, Human–AI
Mathematics, supported by Project Numina. Search ran from June 2026; three human teams proved KLS while it ran.

## Protocol
- Status moves only via "an independent review of an agent's work, or the explicit acceptance of a named
  person." A "numerical run, a green check or a count of failed attempts moves nothing."
- Roles on both Claude Code and Codex: researcher, reviewer, writer (prose only, never statements).
- One orchestrating session is "the only one that changes the ledger."
- "Independence is a fresh context, not a different name": reviewers get repository paths and a mission,
  no conversation history.
- "The checker checks structure, not mathematics": identities, dependencies, fingerprints; it blocks status
  changes while anything is inconsistent.
- Each review fingerprints the exact text of every statement and proof it read; any later edit makes the
  certification stale until a new review passes. Hash scheme unstated.
- No Lean. Statements live in a MyST manuscript; proofs and reviews in separate files.

## Incidents
- A June numerical reading supporting a candidate conjecture was withdrawn in August: "the runs had computed
  a different quantity." A ledger letting numerics move status "would have recorded a falsehood for two months."
- From 25 August, 34 statements were marked proved with no written proof; agents sharing context had
  certified them. Fresh-context re-review in early October sent several back: a false endpoint claim, a
  proposition silently narrowed to one direction, a one-dimensional step failing for density c(1+x^2)^-3.
- About one review in ten returned a proof; some found statements false, not merely unproved.
- Up to 16 agents in parallel.
- Admitted limit: "two instances of the same model can make the same mistake"; a different-model reviewer
  "only partly helps." No KLS proof has been read by a person.

## For cairn
- Two independent confirmations (this and the DeepMind swarm) that shared context launders fabrication:
  here 34 certified-but-unwritten proofs, there 34 exploit acceptances. Fresh context is the defense in both.
- "Computed a different quantity" is the empirical twin of a statement-drift attack; cairn's
  reproducibility node should pin what quantity a run computes, not only that it ran.
- "Proposition narrowed to a one-way implication" is exactly what cairn's statement-level match review
  exists to catch; a text fingerprint here caught edits, but only fresh review caught the narrowing.
- Text fingerprints catch edits after review; they do not catch a statement wrong from the start.

## Leads out
- HISTORY.md: https://github.com/human-ai-mathematics/kls-conjecture-search/blob/main/HISTORY.md (primary incident log)
- Template repo: https://github.com/human-ai-mathematics/conjecture-search-template (checker source, fingerprint scheme)
- Framework: https://human-ai-mathematics.github.io/conjecture-search/
- Discussions: https://github.com/orgs/human-ai-mathematics/discussions

## Primary record: HISTORY.md (read 2026-10-30)
Source: https://github.com/human-ai-mathematics/kls-conjecture-search/blob/main/HISTORY.md. It sharpens and
partly corrects the blog's account above:
- Before 2026-08-25, 34 fixed-cut statements were marked proved with no written proof. On 2026-08-25 they
  "received grouped proofs and reviews"; the others were reclassified. Those certifications were "two agents
  reviewing each other's work, which was not an independent check."
- On 2026-10-04, 40 days later, fresh grouped reviews re-ran them. The QCTS/Stein core passed. The Riccati and
  bootstrap dossiers were sent back: a false endpoint claim in `lem:half`; `prop:ceiling` narrowed to a one-way
  sufficient implication; `thm:bootstrap` recertified. A proof step of `thm:cmh-1d` failed on the density
  c(1+x^2)^-3 ("The step was at fault, not the theorem"); repaired and recertified with two dependents. The log
  then says "No statement changed"; how that squares with `prop:ceiling` being narrowed is not explained there.
- 2026-08-20 to 08-24: the June numerical reading for `conj:taming` was withdrawn: "the runs computed a different
  quantity." So the wrong-quantity result stood about two months, June to late August.
- 2026-10-06: a novelty claim on `thm:cmh-dirichlet` withdrawn.
- 2026-08-27: the first refutations certified; "A fresh review confirmed them on 2026-10-01."
- Every milestone cites a source file under `research/explorations/`, and statement changes are checked with
  `check.py --statements`.

For cairn: mutual review between two working agents is the specific anti-pattern, and its cost here was 40 days
of certifications standing on it. The log's habit of citing a source file per milestone and diffing statements
mechanically per release is the same shape as cairn's ARTIFACTS block and statement-hash golden.
