# ADR 002: Lean CI prerequisites

Status: accepted

## Context

The real Challenge compilation integration test imports a theorem from the
manifest-pinned mathlib revision. A fresh checkout contains no `lean/.lake`
directory, and compiled mathlib artifacts are external to the tracked source.

## Decision

CI restores `lean/.lake` and `~/.cache/mathlib` with a cache key containing the
runner operating system, architecture, Lean toolchain, Lake manifest, and Lake
configuration. CI runs the targeted mathlib cache command on every run and
selects the Lean toolchain declared by `lean/lean-toolchain`.

The preparation step precedes Gates, uses a failing shell configuration, and
checks that `lake-manifest.json` remains unchanged. The integration test treats
an absent mathlib checkout as an assertion failure.

## Rejected alternatives

- A missing-dependency skip: the gate has no compilation evidence.
- A larger test timeout: dependency provisioning and compilation have separate
  failure modes.
- A cache-hit conditional preparation step: a restored cache can be incomplete.
- An unpinned dependency update: the manifest defines the accepted dependency
  revision.

## Verification contract

`tests/unit/test_lean_ci_setup.py` checks cache identity inputs, preparation
ordering, explicit toolchain selection, cache acquisition, and manifest drift
refusal. Its planted negative removes the preparation step and must refuse.
`tests/integration/test_challenge_compile.py` compiles the rendered Challenge
against the manifest-pinned mathlib checkout.
