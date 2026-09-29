# ADR-015: Bead class routing

## Status

Accepted by owner decision through MagentaSparrow, agent-mail 415, 2026-09-29.

## Context

Dispatch needs a repeatable class for the scrutiny a bead receives. Path-derived floors provide deterministic decisions for documentation work and identity-sensitive work. Other work requires a bounded judgment call. A label or judge must not lower scrutiny established by the path floor.

## Decision

The router reads `br show <id> --json`. It derives skill identity paths from each skill's `IDENTITY_SOURCES` and gate identity paths from the same module constants and bundle files used by `tests/unit/test_identity_sources.py`. Identity-bearing paths and RULE 2 surfaces set a Critical floor. A bead whose identified paths are only under `docs/`, `research/`, `.beads/`, or Markdown files has a Mechanical floor, unless a path has a recognized code extension. Other, missing, or unrecognized paths have a Standard floor.

The judge runs only for a Standard floor. It uses the first-party Luna model at low effort through global Codex and may return Standard or Demanding with a one-line reason. An unavailable judge, timeout, malformed response, or invalid answer selects Demanding. A `route:<class>` label may raise the selected class; it cannot lower the path floor. Unknown route classes and identity-registry failures refuse routing.

The command emits exactly `class`, `reasons`, `floor`, and `judge`. Cairn owns class selection. Class-to-model assignments and checker selection belong to fleet routing.

## Consequences

Callers receive the final class, its path floor, the reasons for selection, and whether the judge was used. Tests cover Critical-path protection, raise-only labels, judge refusals, and dynamic identity-source derivation.

Routing assigns a work class. It establishes neither correctness nor model quality.
