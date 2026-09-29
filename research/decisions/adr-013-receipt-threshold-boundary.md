# ADR 013: Receipt threshold boundary

Status: accepted

Implementation: held for the next session

`runner.launch` computes `ceiling_s` as `subprocess_startup_ms / 1000 + ceiling_multiplier * evaluation.expected_wall_s` and `wall_cap_s` as `max(wall_cap_multiplier * ceiling_s, ceiling_s + wall_cap_floor_s)` (`src/cairn/runner.py:113-123,441-465`). The receipt records measurements, the gate bundle hash, and `measurement_scope`, but neither effective threshold (`src/cairn/runner.py:530-545`, `src/cairn/substrate.py:29-46`). Escrow stores the effective CPU multiplier and declared production cost (`src/cairn/runner.py:486-492`, `src/cairn/schema.sql:110-123`).

## Decision

Record the effective `ceiling_s` and `wall_cap_s` in each hashed receipt, using the exact values passed to `status_for` and `spawn_and_wait`. Owner ruling 362 selects this decision over the threshold-omission position in `cairn-wdg` comment 227. A reader must be able to inspect the stored evidence without knowing which caller supplied unpinned runner arguments.

The real counterexample uses two `instance_maker` subprocesses with the same skill identity, recipe, full pinned bundle, profile, and escrow multiplier `4.0`. Startup `77 ms` produces a `0.2734 s` ceiling; startup `0 ms` produces `0.1964 s`. Both receipts measure about `0.59 s` CPU and both attempts report `BUDGET_EXCEEDED`. A reader using only stored records and the bundle reconstructs `0.2734 s` for both, which is wrong for the second attempt (`/tmp/cairn-lane2-day.HCyLdO/wdg-unstored-startup.py`, `/tmp/cairn-lane2-day.HCyLdO/wdg-unstored-startup.log`). The caller's startup override is not stored in the recipe, receipt, or escrow.

`measurement_scope` remains a separate receipt field for observed measurement provenance, as settled by `cairn-m1-cqt.1.5`. Comment 227 records that adding that field changed no golden files; this does not settle the impact of adding threshold fields.

## Implementation acceptance

Before implementation, name every golden file the schema change moves. A scratch inventory that omits a moving golden must fail; restoration requires matching byte lengths and SHA-256 digests. A planted threshold mismatch must fail against the exact effective values used by `status_for` and `spawn_and_wait`, including explicit overrides. Bundle defaults alone are not that authority. These checks and the schema change remain outstanding while implementation is held.

No-Claim: this decision settles which effective thresholds the receipt records. It establishes neither CPU or wall refusal correctness nor runtime CPU monitoring.
