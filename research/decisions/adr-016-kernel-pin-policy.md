# ADR-016: Kernel pin policy

## Status

Accepted by owner decision, 2026-10-30: the operator selected `v4.35.0` for `cairn-p76j`.

## Context

A proof reaches `PROVEN` only through the gold arm, whose comparator runs an external kernel and then the official kernel. The gate is an intersection: a proof of `False` must pass both.

`research/grounding/kernel-intersection-2026-10-30/` measured 82 invalid proofs against the two pinned kernels. Official `v4.34.0-rc1` accepted six proofs of `False` and nanoda `3a24072` accepted four invalid inputs. None passed both, so each kernel was the only barrier against the other's bugs. `leanchecker --fresh` passed the five of those six it could read, which is why a single-kernel replay never decides `PROVEN`.

End to end on those pins, the #14807 exploit submitted as a Solution compiled, passed the axiom check with `propext` alone, and was refused only by nanoda at the comparator.

A higher version number is not evidence of a fix. `v4.33.1` carried fixes that `v4.34.0-rc1` lacked.

## Decision

Pin a final release of the official kernel, never a release candidate.

Move the official kernel and the external kernel in one attributed commit, because a toolchain bump leaves the external kernel's holes open and the reverse is equally true.

A pin target is admissible only after both kernels run the arena's invalid proofs and the `tests/vectors/kernel_negatives/` corpus in the image the pins build. Every invalid proof must be refused by at least one kernel, and every valid control accepted by both. An invalid input a pinned kernel accepts is recorded in the corpus manifest with its open upstream issue, and `tests/integration/test_kernel_negatives.py` fails when the recorded verdict changes in either direction.

The official kernel's corpus row is expected to refuse every invalid proof. A row where the official kernel accepts an invalid proof blocks the pin.

Soundness fixes in either kernel are a reason to move the pins. Release cadence is not.

## Consequences

Every move changes identity-bearing files, so goldens and deployed pins move with it. That cost is accepted against the alternative of a known proof of `False` standing behind one kernel.

A Mathlib move re-keys every statement that imports Mathlib, because the statement hash covers the elaborated closure. Mathlib-free statements keep their hash. The hash of `W.Δ = W.Δ` moved between Mathlib `1f29011` and `56a0058` while `WeierstrassCurve.Δ` kept its type and value: the closure changed from 641 to 644 constants through refactors of the algebra hierarchy and core's `Decidable`. A review verdict names one hash and does not transfer, so a claim over Mathlib is re-reviewed after a move.

The corpus bounds known exploits, not unknown ones. A green run shows these proofs are refused and establishes nothing about soundness in general.

The dev arm runs the official kernel alone and stays development-only: `justify` refuses a run from any arm but the gold one.

The comparator's nanoda config is duplicated in the test, and a test reads the comparator source in the image to hold the two equal.
