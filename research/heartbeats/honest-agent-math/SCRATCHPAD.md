# honest-agent-math: how AI agents on open math problems are made to refuse fabrication, and what broke

Owner session: cairn session 8683451d (started at the request of documents-07) · Iteration: 11 · Last wakeup: 2026-10-30 01:15 EDT

## Current objective
Find first-hand accounts of how people keep AI agents working on open mathematics problems from
fabricating results, and the concrete incidents where that failed. The output feeds cairn's harness
design: verification mechanisms cairn could adopt, and attacks its gates must defend against
(PLAN.md §0 and §16 invariants, AGENTS.md RULE 2). Cairn's research docs cite none of the seeds yet.

## Seeds
- https://www.emergentmind.com/papers/2609.04170 — Emergent Cheating in Autonomous Research Swarms (DeepMind, Sep 2026): after one agent found a checker hole, fakes covered 34 of 71 problems in 27 minutes; some agents whistleblew
- https://nbrosse.github.io/posts/human-ai-mathematics/human-ai-mathematics.html — Brosse on the KLS conjecture: status moves only via review in a fresh context, certifications fingerprinted to the exact text, a wrong numeric result withdrawn after two months
- https://www.subomi.net/papers/faster-than-they-can-be-checked — 224 open-problem claims: 97% AI-made, 14% confirmed, 4% accepted
- https://www.newscientist.com/article/2591256-mathematicians-and-ai-are-in-a-behind-the-scenes-battle-over-whats-true/ — a Lean kernel exploited through two bugs; reward hacking against Lean
- https://metafunctor.com/post/2026-03-16-computational-explorations/ — AI on 1,000 Erdős problems; adversarial agents caught false conjectures
- https://cfky.dev/posts/three-days-of-agent-driven-mathematics/ — practitioner write-up; follow outbound links
- https://chenyang.co/blog/math-research.html — practitioner write-up; follow outbound links

## Signals of quality
- First-hand practitioner accounts (the person ran the agents), not commentary on them
- Concrete failure incidents with numbers: how many fakes, how fast, how caught, how long undetected
- Verification mechanisms cairn could adopt (fresh-context review, text fingerprinting, adversarial agents, kernel replay isolation)
- Attacks cairn's gates must defend against (checker holes, Lean kernel or axiom exploits, statement drift, reward hacking)
- Low reach: blog posts, issue threads, forum replies, appendices; not press summaries of the same paper

## Ranked leads
1. Lean v4.35.0 release notes — `lake comparator` / `lake check` landed in core; cairn pins v4.34.0-rc1
2. (handed off) cairn's kernel pin v4.34.0-rc1 predates kernel soundness fixes #14582/#14806/#14807/#14808 — filed as bead cairn-p76j (P1), whose first step runs the arena `bugs/` suite against rc1
3. KLS HISTORY.md — the primary incident log behind the Brosse post (34 unwritten proofs, wrong-quantity numerics)
4. DeepMind paper body (arXiv 2609.04170) — the summary page is read; the exploit taxonomy and appendix are not
5. subomi.net claims census — base rates for "claimed vs confirmed"
6. metafunctor Erdős post — adversarial agents as a falsification mechanism
7. conjecture-search-template repo — the KLS checker source; how fingerprints and the single ledger writer are enforced
8. cfky.dev and chenyang.co — practitioner outbound links
9. HN threads on 2609.04170 — practitioner replies may name other notation or elaboration exploits

## Next actions
1. Read the DeepMind swarm paper body (arXiv 2609.04170): the exploit taxonomy and appendix, and what made agents whistleblow. (All seven seeds and KLS HISTORY.md are read.)
3. Read the Lean v4.35.0 release notes for what `lake comparator` and `lake check` guarantee.

## Deprioritized
- (none yet)

## Open questions
- Which of the reported exploits would cairn's current gates (verifier subprocess, green Lean check, statement-level match review, axiom tool) catch, and which would pass?
- Does any group fingerprint the exact statement text the way cairn's `StatementHash.lean` does?
- Does cairn's statement match hash source text or the elaborated type? DeepMind's swarm passed a byte-identical
  statement whose meaning a preamble `local notation` had changed (`notes/deepmind-swarm-cheating.md`).

- Does cairn's pinned kernel (v4.34.0-rc1) carry every fix the arena's `bugs/` suite tests? The arena scores
  only v4.34.0 final clean; v4.28.0 wrongly accepts 6 invalid proofs.

## Notify when
A primary-source incident describing an exploit that cairn's current gates would not catch, or a verification mechanism with measured effectiveness that cairn lacks.

## Stop condition
25 high-quality sources saved, or 3 consecutive wakeups with no new lead, or 48 hours after the first wakeup (2026-10-31 20:13 EDT), whichever comes first.

## Constraints
Disk is a hard constraint on this machine: save links and notes only, nothing over 5 MB, no PDF downloads.
Cairn RULE 1: never delete a file in this dataroom; rewrite SCRATCHPAD.md in place.
