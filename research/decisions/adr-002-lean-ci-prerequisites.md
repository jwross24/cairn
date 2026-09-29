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

## Linux prerequisite cache

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
the seed.

Linux CI restores the dependency seed and exact image archive with one exact
`actions/cache` key and no `restore-keys` fallback. The key includes runner OS
and architecture; Docker server version, storage driver, and driver status; and
hashes of `bundle/Containerfile`,
`bundle/container.json`, `bundle/lean.json`, `lean/lake-manifest.json`,
`lean/lean-toolchain`, `tests/_linux_dependencies.py`, `src/cairn/container.py`,
`src/cairn/lean.py`, and `src/cairn/solutionbuild.py`. The helper further binds
the seed to the exact image ID and identity, Lean pins, project configuration,
requested modules, and cache layout. The cached paths are only the dependency
directory, `image.tar`, and `image.tar.metadata.json`. ([Workflow key and restore](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/.github/workflows/ci.yml#L47-L121), [helper identity inputs](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/tests/_linux_dependencies.py#L37-L47))

On a cache hit, CI imports `image.tar` by its recorded image ID. The helper checks
the metadata schema and layout, image identity, archive size and digest, then
validates the loaded image and dependency inventory before gates run. An invalid
hit is refused; the import path does not rebuild. A miss prepares prerequisites
on that lane. Only a successful `container` matrix lane on a push to `main` and
on a cache miss exports and saves the cache. A validated hit or prepared miss
proceeds through the ordinary Linux gates; neither the gate nor type step has a
cache-hit condition. ([Archive validation and import](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/tests/_linux_dependencies.py#L233-L410), [workflow gates and publisher](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/.github/workflows/ci.yml#L146-L164))

The cache contains reusable prerequisites, not candidate outputs or verdicts.
A validated cache hit does not skip the Linux gates. Candidate checks still
compile and run the configured axiom checks. A valid `rfl` proof reaches
`leanchecker --fresh`; fresh replay rejects a forged proof, and the axiom check
refuses `sorry` before replay. Statement matching remains part of verification.
([candidate fresh-replay integration test](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/tests/integration/test_container_statement_hash.py#L221-L282))

## Verification contract

`tests/unit/test_lean_ci_setup.py` covers macOS pinned mathlib cache acquisition
and preparation ordering, explicit toolchain selection, and manifest-drift
refusal, along with the Linux identity-bound cache, validation, publisher, and
refusal contract ([macOS setup](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/tests/unit/test_lean_ci_setup.py#L60-L83), [Linux cache contract](https://github.com/jwross24/cairn/blob/09a8a03852ca3473abaae0ce87c907b6aafdee82/tests/unit/test_lean_ci_setup.py#L235-L390)). `tests/integration/test_container_statement_hash.py` covers candidate fresh replay and refusals; `tests/integration/test_challenge_compile.py` compiles the rendered Challenge against the manifest-pinned mathlib checkout. This contract establishes neither CI performance nor completion of the broader verification audit.
