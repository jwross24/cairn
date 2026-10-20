Read this when you need to locate a section of `PLAN.md` by line number or want the meaning of the three uses of "skill".

# PLAN.md section map

§0 principle 15 · §1 prompt⊂harness 30 · §2 skills 40 · §3 substrate 122 · §4 components 288 · §5 tiers 533 · §6 ladder 709 · §7 epistemics 921 · §8 no-go 1153 · §9 never-give-up 1179 · §10 problem selection 1192 · §11 compounding 1279 · §12 research-software 1306 · §13 build order 1348 · §14 outcomes 1614 · §15 deferred 1625 · §16 evidence/defaults 1685.

`research/SESSION-PROMPTS.md` holds openers for the five session types; research modes require M1.

# "Skill" means three different things

- A Cairn skill is a deterministic Python capability under `src/cairn/skills/`, run as `uv run python -m cairn.skills.<name>` with canonical JSON on stdin and stdout, content-addressed by its identity bundle and shipped with a known-answer corpus, golden certificate and byte-equal double run.
- A worker role template (the Skeptic's checklist, PLAN §4) is read-only, claim-agnostic prompt text pinned in the gate bundle, not loaded from a skills directory.
- An agent skill (Claude Code or Codex: `beads-workflow`, `optimal-tests`, `beads-br`) builds Cairn and never runs inside it. A prompt is non-deterministic, so it cannot be content-addressed or cached by recipe key.
