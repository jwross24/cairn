# §2 skill contract — clause coverage

Every row is one extracted clause of PLAN §2, its requirement level, the sentence it is
extracted from, and the check function in `skill_contract.py` that decides it. The set of
ids here and the set in `CLAUSES` are asserted equal by
`test_skill_contract.py::test_coverage_table_matches_clauses`, so a clause cannot exist in
one and not the other.

A MUST verdict of FAIL is a test failure for any subject registered with `conforming=True`.
A subject registered with `conforming=False` carries the exact set of MUST clauses it is
built to fail; the harness asserts that set exactly, which is what catches a check that
returns PASS without looking.

| id | level | PLAN §2 sentence | check |
|---|---|---|---|
| S2-01 | MUST | a skill has a typed interface and a fixed version, so it's testable, cacheable, and reproducible (L44) | `check_typed_interface` |
| S2-02 | MUST | the whole bundle names the executable that a recipe key, a ladder run and a tier ticket bind (L52) | `check_content_addressed_io` |
| S2-03 | MUST | every nondeterminism source pinned (seed, hashers, clock) (L60) | `check_captured_seed` |
| S2-04 | MUST | a vendored known-answer corpus … every corpus declares its origin, `corpus_origin ∈ {upstream_vendored, independent_oracle, randomized_postcondition, author_supplied}` (L54, L61) | `check_corpus_origins` |
| S2-05 | MUST | a per-case ledger over `pass`, `intentional_non_goal` and `known_gap`, and a committed pass floor (L54) | `check_ledger_and_floor` |
| S2-06 | MUST | a lower bound that only an explicit, attributed update may raise, so the advertised floor and the measured floor cannot drift apart (L56) | `check_floor_is_attributed` |
| S2-07 | MUST | a golden certificate = hash over the canonical transcript of the corpus and the exact outputs (L57) | `check_golden_certificate` |
| S2-08 | MUST | a byte-equal double run asserted (L60) | `check_byte_equal_double_run` |
| S2-09 | MUST | grain a skill at a capability with a stable interface, a self-test, and a declared cost profile (L104) | `check_declared_cost_profile` |
| S2-10 | MUST | on disagreement the skill returns `status = DISAGREE` (not OK, so never cached), writes both transcripts and digests to a substrate node (L77) | `check_disagree_semantics` |
| S2-11 | MUST | the launch contract of cairn-m0-e0s.9: an environment allowlist and no substrate handle in the child | `check_no_substrate_handle` |
| S2-12 | MUST | the skill declares its axis — `implementation` or `algorithm` — and the input range over which that axis is independent … a cross-check that has never disagreed is reported as untested, not as passing (L71, L76) | `check_axis_declaration` |
| S2-13 | SHOULD | skills that produce floats declare a numeric profile or a tolerance (L61) | `check_numeric_profile` |
| S2-14 | SHOULD | Tier-0 arithmetic skills verify their own answer before returning (L68) | `check_postcondition_arm` |

## Where a check reads more than the sentence

**S2-01.** PLAN §2 says "typed interface" without naming a mechanism. The check reads it as:
`INTERFACE_VERSION` matches `<name>/<int>`; `run` and `main` are callable; `run` takes a fixed
parameter list rather than `*args`/`**kwargs`; `identity_bundle()` carries all five fields of
the L50 bundle; and `implementation_revision` is derived from file content, proved by copying
`IDENTITY_SOURCES` into a scratch root (same revision) and appending one byte (different
revision).

**S2-11 is not a PLAN §2 clause.** PLAN §2 states nothing about stdin, stdout, `python -m`, an
entry point or canonical JSON. The wire contract is an M0 operator decision recorded in
cairn-m0-e0s.9 and in CLAUDE.md, and the clause cites that decision rather than the plan. Its
check has two arms: an in-child environment dump through the real runner, with a `CAIRN_DB`
planted in the parent environment, showing no `CAIRN_DB*` key, no value holding a `.sqlite`
path and no such path in argv; and a source read of the subject module showing it names no
`CAIRN_DB*` variable of its own. Either arm alone can fail the clause.

**S2-12's ledger arm.** "Reported as untested, not as passing" is checked as: the certificate's
`selftest_summary.cross_check` block holds exactly `axis` and `independent_range`, so the
ledger cannot record a cross-check as having passed.

**Vocabulary width.** S2-04 accepts the four origins PLAN L62 names. `cairn.selftest.ORIGINS`
admits three of them; a §2-legal corpus declaring `independent_oracle` is refused by
`check_corpus`. The conformance clause holds the plan's vocabulary; the narrower validator is
tracked as its own bead.

## What the harness produces

The compliance matrix is a `pytest_terminal_summary` section, printed by
`tests/conformance/conftest.py` from the verdicts of the module-scoped sweep. No file is
generated. Every verdict is logged through `cairn.log` as one `verdict` event carrying
`(subject, clause_id, level, status, reason)`.

`DISCREPANCIES.md` exists only when some subject records an XFAIL verdict, asserted by
`test_discrepancies_exist_only_for_an_xfail`. No subject records one.
