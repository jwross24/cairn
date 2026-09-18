# ADR 003: Budget test observables

Status: accepted

A CPU budget compares measured execution time with a declared expectation. A
random input and an arbitrary host do not guarantee budget exhaustion.

The real ladder integration test verifies its stored success rates against the
observed claimant outcomes. Failure diagnostics identify each seed, terminal
status, measured CPU time and configured ceiling. The deterministic boundary
test covers CPU equal to and strictly greater than the ceiling. An over-budget
trial lowers the aggregate success rate and cannot produce KEEP. The real
CPU-burner integration test supplies subprocess evidence for budget refusal.

Neither a fixed nonce nor a fitted timing constant establishes these properties
across hosts. Synthetic aggregation tests do not establish production wiring;
the real ladder and CPU-burner tests retain that responsibility.

This test contract does not establish correctness of operation accounting or
runtime CPU enforcement. Those questions belong to `cairn-kjgf` and its related
implementation work.
