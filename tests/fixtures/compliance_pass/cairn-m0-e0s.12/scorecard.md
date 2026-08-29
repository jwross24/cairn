# Scorecard — cairn-m0-e0s.12

**Title:** M0: justify(evidence, statement_hash): kind→max-class map, producer-standing ceiling, coverage check (interval containment / categorical equality / assumption ⊆), lattice violations, review_verdict digest rule, refuted-version rule, append-only attributed tag history
**Type:** task  **Priority:** P1
**Status (claimed):** closed
**Close reason:** "justify derives the §7 calibration tag: kind ceilings, producer standing, structural coverage, lattice violations, and an append-only attributed tag history, reachable as cairn justify --statement. Evidence in the close comment at 8836bb1." (2026-08-25T14:37:27.108882Z)

**Score: 780 / 1000**
**Verdict: 🟡 Partial**
**Denominator:** scored over the 500 of 1000 weight measured (390/500), rescaled; unmeasured: test_depth, tests
**⚠ DETERMINISTIC-ONLY PASS:** Phase 4 (Required tests), Phase 6 (Test depth) ran in stub mode (no subagent re-ran tests). Under unmeasured_dimensions=excluded those dimensions carry no credit: their weight leaves the numerator and the denominator both. The score above is an UPPER BOUND over the 500 of 1000 weight that was measured — re-run with the real compliance-verifier and test-depth-auditor subagents to score the rest.

## Dimension scores

| Dimension | Score | Max | Why |
|-----------|------:|----:|-----|
| Implementation completeness vs. spec | 175 | 250 | Phase 4 in stub mode — Implementation scored from evidence.json with reduced credit (FOUND→70%, AMBIGUOUS→40%); upper bound, see scorecard banner; code.primary: FOUND in evidence → 70% (Phase 4 stubbed; upper bound) |
| Required tests present and meaningfully passing | — | — | EXCLUDED from numerator and denominator — WAIVED — Phase 4 ran in stub mode (executor='single-bead-stub'); no subagent re-ran the tests |
| Anti-theater | 200 | 200 | BLOCKING=0 MAJOR=0 MINOR=0 → -0 |
| Test depth | — | — | EXCLUDED from numerator and denominator — WAIVED — Phase 6 ran in stub mode (auditor='single-bead-stub'); no subagent audited depth |
| Docs / migrations / telemetry / flags | 0 | 25 | 0/1 non-code items found |
| Cross-bead integration | 15 | 25 | 1 synthesis findings owned → -10; 8 ignored by policy |
| **TOTAL** | **780** | **1000** | 390 of 500 measured weight, rescaled to 1000 |

## Citations

- spec.json: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/spec.json`
- evidence.json: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/evidence.json`
- compliance.json: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/compliance.json`
- theater.json: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/theater.json`
- test_depth.json: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/test_depth.json`
- raw logs: `beads_compliance_audit/passes/2026-08-27T18-09-58Z/beads/cairn-m0-e0s.12/raw/`

## Missing items (verbatim)

- spec item `tests.integration.primary` — type=integration desc=integration test required by bead body
- spec item `tests.e2e.primary` — type=e2e desc=e2e test required by bead body
- spec item `tests.fuzz.primary` — type=fuzz desc=fuzz test required by bead body
- spec item `tests.metamorphic.primary` — type=metamorphic desc=metamorphic test required by bead body
- spec item `telemetry.primary` — category=telemetry
