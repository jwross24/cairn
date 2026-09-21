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

## Linux developer cache

`tests/_linux_dependencies.py` provisions a dependency-only seed outside pytest.
Its key binds the exact image ID, gate container identity, Lean pins, canonical
manifest, Lake configuration, requested modules, and cache layout. A separate
Docker tag retains that image; an atomic image record selects it without a rebuild.
Per-key locks serialize population, and publication follows successful provisioning
and complete inventory validation. Failed work remains available for diagnosis.

The configured cache is read-only to tests. Readers validate file bytes, modes,
types, symlink containment, and pinned Git checkouts before copying to private
projects, then check the copy against the same inventory. The inventory assumes
a trusted producer; it does not authenticate one. Candidate code never mounts
the seed. Proof replay, statement matching, and axiom checks retain their execution
requirements. CI uses the temporary cold path until exact-image persistence is
available across runners.

## Verification contract

`tests/unit/test_lean_ci_setup.py` checks cache identity inputs, preparation
ordering, explicit toolchain selection, cache acquisition, and manifest drift
refusal. Its planted negative removes the preparation step and must refuse.
`tests/integration/test_challenge_compile.py` compiles the rendered Challenge
against the manifest-pinned mathlib checkout.
