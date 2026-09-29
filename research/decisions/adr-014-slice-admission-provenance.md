# ADR-014: Slice admission provenance and verifier spawn reporting

## Status

Accepted.

## Context

Ticket tier and derived cost tier describe different decisions. Tier 0 needs no ticket, so a ticket cannot supply the cost tag for every admitted launch. The four slice nodes share the generator launch's admission; their tags do not measure each downstream node's cost.

An absent verifier exit code can describe either a pre-spawn refusal or a timeout after process creation. Spawn status is therefore a separate result fact.

## Decision

An admitted tier-gate decision carries the cost tier derived from its declared cost profile and the hash of its persisted gate run. M0 exposes one admission summary containing that hash, the declared tier, and the derived cost tier. The generator's canonical cost tag and the four slice-node cost tags use that summary. All four nodes inherit the generator launch's admission; they do not represent separate measurements of derivation or verifier cost.

Verifier results carry an explicit `spawned` boolean. Pre-spawn refusals set it to false. A normal process result or timeout after process creation sets it to true, even when the timeout has no exit code. The value appears in the verifier result node, M0 arm, and correlated verifier logs.

The persisted gate-run schema and vocabulary remain unchanged. Verifier acceptance rules, mathematical gates, and the cost-tier calculation remain unchanged.

## Consequences

M0 output can be checked against the persisted admission and the boundary table that produced it. A timeout record reports process creation without inventing an exit code. The cost tag connects the slice's nodes to one launch admission and does not measure the cost of each downstream node.
