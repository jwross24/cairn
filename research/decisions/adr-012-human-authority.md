# ADR-012: Attested authority for sessions, statements, yanks, and salts

## Status

Accepted by owner decision through MagentaSparrow, agent-mail 327, 2026-09-29.

## Context

PLAN decisions 3, 4, and 5 reserve expensive admission, statement ratification,
and discretionary yank or salt actions to the human path. A substrate row is
worker-writable evidence of an assertion. Authority requires the matching record
in the operator-owned attestation file.

A digest alone cannot authorize an action: a valid record for one statement or
reach does not authorize another. Checking authority after a yank propagates also
cannot protect attempts, escrow, or dependent claims from an unauthorized action.

## Decision

Four distinct canonical record kinds bind their attributed issuer and action:
`operator_session`, `statement_ratification`, `yank_ruling`, and `salt_issuance`.
An append-only substrate mirror carries canonical bytes, digest, and file offset.
Readers rederive the digest, verify the attestation record at that offset, and
match the action's bindings. Missing, malformed, or mismatched authority is absent.

The gate bundle requires an open operator session whenever either the declared
tier or the tier derived from cost is at least 2. This includes Tier 3 and fit-rung
boundary exemptions. Sessions bind the bundle, last no more than 3600 seconds,
and stand from their opening instant inclusive to their expiry exclusive.
Renewal requires a fresh attested record. The requirement defaults to enabled;
disabling it at M3 is an explicit bundle change.
Liveness uses the real UTC clock. `SOURCE_DATE_EPOCH` controls reproducible output
timestamps and cannot extend an authority record's lifetime.

A claim statement supports a ticket only with a matching statement-ratification
record for its hash and the gate bundle. Inserting a claim statement grants no
ratification. The gate resolves the statement from the recorded hypothesis, so
omitting its hash from a launch cannot remove the requirement. Review approval
retains its separate statement-match purpose and grants no ratification.

A discretionary yank requires an attested ruling bound to its identifier,
implementation revision, and canonical reach predicate. Validation precedes
the transaction that records the yank, advances salt, disowns covered attempts,
releases escrow, and rederives dependent claims. A gate-verdict yank remains
autonomous when it names a recorded verdict and covers the whole revision.
Narrowing the reach requires human authority.

A salt following a yank inherits authority only from that visible, matching yank.
A standalone salt requires an attested salt-issuance record bound to its class
and value. Reader checks cover directly planted storage rows as well as public
action writers. Runtime callers pass the operator attestation path through
admission and yank observation.

## Consequences

Tests for admitted expensive work and statement-bearing tickets require real
attestation records. Positive controls preserve gate-written yanks without human
records. Negative controls include copied authority for a different action and
unauthorized writes that must leave propagation state unchanged.

The bundle policy and required identity-bearing caller plumbing move their
content hashes and require attributed golden regeneration. These controls prove
authority boundaries at write and read paths; they establish neither operator
practice nor a mathematical result.
