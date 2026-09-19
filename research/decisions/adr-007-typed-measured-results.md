# ADR 007: Typed measured results

## Status

Accepted by the operator on 2026-09-19.

## Decision

A measured ledger result declares its quantity and one of three kinds: `exact`, `lower_bound`, or `statistical_interval`. Its numeric value is a finite decimal string. Exact refers to the recorded observation or finite-sample statistic, never certainty about a population parameter.

An exact observation and a lower bound carry no confidence interval, coverage, or interval method. A statistical interval carries two ordered finite decimal endpoints, a named method, and coverage strictly between zero and one. A decision threshold or model tolerance band is not a statistical interval. A verified counterexample count is an exact observation.

The ladder's rejection predicates, thresholds, calibration tags, retry authority, and verification requirements are unchanged. ADR 004 governs censored operation observations: a lower bound cannot acquire a finite upper endpoint or a sample standard deviation. Typed ledger results do not supply missing instrumentation or establish the validity of a caller's measurement.

## Consequences

The canonical result representation carries the kind and measurement metadata. Writers refuse untyped results; there is no compatibility decoder or invented interval. Existing stored nodes retain their bytes and identity. Raw record retrieval does not certify conformance to the typed contract. The hunt producer records its verified counterexample count without a degenerate CI. Ladder settlement must derive the quantity and result kind from its persisted observations before it can write measured refutations.
