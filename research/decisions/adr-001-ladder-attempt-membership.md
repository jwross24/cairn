# ADR 001: Ladder table attempt membership

Status: accepted

## Context

A ladder table combines claimant measurements from several trial attempts. A
recipe identifies inputs, not an execution: a reproduction can share its recipe
with the original attempt. A table-level representative cannot identify every
execution contributing to the measurements.

The substrate requires exact shipped SQL DDL. Canonical nodes and lineage can
carry additional relationships without a schema migration or a change to table
and trial identity.

## Decision

A canonical membership node binds each claimant trial slot to its actual attempt
and names the table hash. Membership is complete, unique, immutable, and checked
against the claimant dispatch, recipe, seed, and implementation identity.
Baseline and instance-maker attempts are not claimant members. Recipe equality
does not confer membership on a replay.

Each member resolves the table's full measured size range, including hold-out
trials. The nullable table attempt companion remains available for existing
records; production membership does not select a representative attempt.

For a hypothesis bound to a claim statement, production evidence names each
claimant member and retains the claimant skill's identity and certificate
standing. Evidence links to the exact table. A disowned or inadmissible member
invalidates the aggregate evidence, regardless of which member its node names.

Table reproduction requires a recomputation record linked to that table. A
single-trial rerun cannot establish reproducibility of aggregate measurements.
These bindings do not alter ladder verdicts, calibration classes, verification
requirements, or the meaning of PROVEN.

## Rejected alternatives

- First or last attempt: an arbitrary execution cannot represent all trials.
- Recipe-only lookup: reruns share recipes but have distinct attempt identities.
- Additional SQL columns or tables: existing stores require exact shipped DDL.
- Gate-produced evidence: it would lose the claimant skill's certificate ceiling.

## Verification contract

`tests/integration/test_justify_live_producers.py` exercises a real `ladder.run`
with small local fixtures. Every claimant resolves measured sizes rather than a
wider declared population. Foreign, baseline, and replay attempts are refused.
Conflicting membership, cross-table reproduction, and a revoked sibling trial
provide negative cases. Helper-only inserts do not establish production wiring.
