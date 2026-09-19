# ADR 004: Bound-aware ladder accounting

## Status

Accepted

## Decision

Ladder trials record a gate operation observation with one of three kinds: `exact`, `lower_bound`, or `unknown`.

An exact observation requires a gate-owned count for the complete execution. A lower bound requires verified gate instrumentation for an enforced termination. Unknown has no numeric value. Timing allowances, ceilings, and claimant-reported operations do not create gate observations.

Execution status, output completeness, verifier recovery, reported operations, and gate observations are independent fields. A claimant trial succeeds only when it has terminal status `OK`, complete output, and verifier recovery. A non-OK claimant trial prevents KEEP and KEEP_IN_SAMPLE.

Every arm required by the rung topology is persisted and belongs to immutable attempt membership. Evidence nodes bind claimant attempts only. A paired speedup interval requires complete exact claimant and baseline pairs with matching trial and instance identity. Missing, failed, incomplete, mismatched, or non-exact pairs produce no interval.

Exact claimant observations produce an exact mean, sample standard deviation, and shape statistic. Mixed exact and lower-bound observations produce only a mean lower bound. Any unknown claimant observation produces no aggregate operation statistic. A lower bound can support a refutation floor. Model-miss and shape checks require exact statistics because the current model-band field lacks censored-sample provenance.

## Consequences

Production without a gate-owned operation counter records unknown observations. Missing counts cannot support operation-statistic verdicts; independently verified recovery failures can still REJECT. Injected counters test the accounting boundary only and do not establish a production counter provider. CPU-time enforcement remains outside this decision.

Existing databases with the prior ladder schema are refused by the shipped-schema check. There is no migration, compatibility decoder, or fabricated default.
