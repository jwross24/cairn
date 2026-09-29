# Optimal-tests checklist status

**Scope:** the recorded top ten pytest phases and the CI lane harness they exercise. This is a checklist audit, not a prescription to remove or rewrite authority tests. `PASS` applies only to the stated scope; `HOLD` means the checklist claim is unreviewed or unproven; `OOS` means the criterion does not apply to this stack or path; `FAIL` records a directly observed mismatch with a heuristic.

**Evidence boundary:** timings and recorded pytest outcomes come from [evidence.md](evidence.md#L34) and profile run `36524637482`, source commit `7882d17aaaaeff9a652b35092808e32ec53b5ce4`. The source map was read at `41c042c1e600bc00fef0de6c4883d1357db3015f`; [the mapped lane manifest](../../../tests/_ci_lanes.py#L43) contains ten lanes, while [the profiler](profile_ci.py#L12) and retained run contain eight. `container-plan-exact` and `container-plan-refusals` have no recorded timing rows. The measured revision and source-mapped revision are distinct. The profile records lane summaries and pytest `setup`/`call`/`teardown` durations, not branch coverage or isolated operation costs.

The recorded CI run includes a real gold-container positive (`rfl`) and planted refusal (`forged`) at [the fresh-replay test](../../../tests/integration/test_container_statement_hash.py#L223), plus the dev-arm exact/sorry/timeout plan cases at [the ordered-plan test](../../../tests/integration/test_solution_build_compile.py#L511). These are historical results for the recorded revision; this checklist does not establish pilot transport/helper results. Pilot execution results belong in separate evolving pilot-runs evidence and are outside this historical checklist.

## Phase 0: shape decision

| Checklist item | Status | Evidence and limit |
|---|---|---|
| Identify code shape per file | PASS, mapped scope | `tests/_ci_lanes.py` routes pytest nodes ([lines 43–53](../../../tests/_ci_lanes.py#L43)); `solutionplan.py` sequences ordered gate results ([run and outcomes](../../../src/cairn/solutionplan.py#L138)); `solutionchecks.py` orchestrates compilation, axioms, and replay ([replay observer](../../../src/cairn/solutionchecks.py#L98)); `solutionbuild.py` assembles checked project inputs ([assemble](../../../src/cairn/solutionbuild.py#L225)); `container.py` runs the isolated container ([run](../../../src/cairn/container.py#L182)); `lean.py` adapts pinned Lean processes ([run](../../../src/cairn/lean.py#L114)). These paths mix pure decision logic with filesystem and external-tool boundaries.
| Record test shape | PASS, mapped scope | Split shape: keep unit tests for pinned-command/order/refusal decisions and use real integration tests for the Lean/container authority chain. The unit command guard is in [test_solution_build.py](../../../tests/unit/test_solution_build.py#L35); the real proof boundary is the integration test above. This describes existing evidence, not a new architecture decision.
| Write a target unit:integration ratio before Phase 3 | HOLD | No pre-Phase-3 ratio is evidenced in this pilot. No numeric ratio is recommended: counts alone do not show a performance problem and cannot authorize reducing authority coverage.

## Universal checklist

| Checklist item | Status | Evidence and limit |
|---|---|---|
| Every production branch has a test for each path | HOLD | The top-ten map names positive and refusal branches, but there is no complete branch inventory. The lane tests check selection and non-overlap ([test_ci_lanes.py](../../../tests/unit/test_ci_lanes.py#L87)), not every production branch. |
| Every raised exception/error has propagation coverage asserting message | HOLD | Selected nodes assert meaningful refusal reasons, including `kernel-rejected` and `sorryAx`; no inventory of every production error path was performed. |
| No iteration constructs inside a test function | FAIL, sampled scope | The retained ordered-plan test loops over rows ([test_solution_build_compile.py:520–523](../../../tests/integration/test_solution_build_compile.py#L520)); the timeout integration test loops over two stages ([test_container_statement_hash.py:517–523](../../../tests/integration/test_container_statement_hash.py#L517)). This is a literal checklist mismatch, not a measured waste or a performance finding; no rewrite is prescribed from loop presence alone. |
| No near-duplicate tests | HOLD | Unit command refusals and real replay refusals have different boundaries and assertions; a suite-wide behavior-by-behavior comparison was not done. See [unit guard](../../../tests/unit/test_solution_build.py#L35) and [real replay](../../../tests/integration/test_container_statement_hash.py#L223). |
| Assert full output structure where it is the contract | HOLD | Mapped plan tests assert ordered step kinds/results and important refusal reasons ([exact/refusal branches](../../../tests/integration/test_solution_build_compile.py#L535)); output-contract coverage across the suite is not reviewed. |
| Error assertions specify expected message/type | HOLD | Sampled assertions commonly check typed exceptions or reason codes; a whole-suite assertion audit is absent. The Python-specific `match=` requirement has a concrete failure below. |
| No section-comment headers in tests | HOLD | No whole-suite comment-header audit was performed. |
| Share setup used in three or more test files | HOLD | The map traces module-scoped Linux fixtures and the root `popen_spy`; setup reuse across all test files and whether each helper belongs at that scope remain unreviewed. |
| Fixture/setup teardown is symmetric | HOLD | The root autouse `isolation_guard` uses `yield` and checks its before/after snapshot ([conftest.py:108–140](../../../tests/conftest.py#L108)); this does not establish symmetric cleanup for every fixture. |
| Clear class-level shared state before and after each test | HOLD | No suite-wide class-state inventory was performed. |
| Place mocks at the I/O seam | HOLD | The mapped `popen_spy` wraps and delegates to real `Popen` ([conftest.py:143–154](../../../tests/conftest.py#L143)); other mock seams were not audited globally. |
| Assert the return value as well as each mock call | HOLD | No complete mock-assertion audit was performed. The real replay integration checks both subprocess evidence and result reasons ([test_container_statement_hash.py:254–279](../../../tests/integration/test_container_statement_hash.py#L254)). |
| At least one real-data integration test per major component | HOLD | The real Linux proof uses the pinned image, compiled challenge, axiom checker, and fresh Lean replay; the source map does not inventory every major component. |
| Integration exercises full chain without internal mocks | PASS, gold proof path | `test_linux_candidate_fresh_replay` compiles and invokes the real pinned container/Lean path; `popen_spy` records and delegates to `super().__init__` ([conftest.py:148–153](../../../tests/conftest.py#L148)). The planted `forged` case refuses at fresh replay ([assertions](../../../tests/integration/test_container_statement_hash.py#L263)). This pass is for that chain only.
| Test files mirror source structure | HOLD | The selected integration tests group several `cairn` modules by behavior; no full source-to-test inventory was made. |
| Each test directory has a stack-required init/mod declaration | OOS | The harness is Python/pytest (`pyproject.toml` configures `testpaths = ["tests"]`, [lines 36–42](../../../pyproject.toml#L36)); pytest does not require an `__init__.py`/`mod` declaration for these test directories. |

## Cross-layer checklist

| Checklist item | Status | Evidence and limit |
|---|---|---|
| No identical-shape unit/integration duplicate | HOLD | The sampled unit checker-command refusal prevents process and file effects ([unit test](../../../tests/unit/test_solution_build.py#L35)); integration proves the real Lean/container behavior. This is evidence of different scopes, not a complete duplicate audit. |
| No unit test mocks three or more external boundaries | HOLD | Unit mock-boundary counts were not inventoried. |
| No parametrized failure tests converge on one output through different patch targets | HOLD | No complete failure-test/patch-target inventory was performed. |
| No framework-only assertions | HOLD | No suite-wide framework-contract audit was performed. |
| Trophy-shaped components have unit count ≤ integration count | HOLD | No complete test counts by component or shape were collected. Counts alone would not justify reducing authority coverage. |
| Pyramid-shaped components have unit count ≥5× integration count | HOLD | No pure-library component count/ratio was established; a numerical target is not a performance finding. |
| Every mapped branch is covered at its best layer | HOLD | The source map covers the ten slowest recorded phases, not every branch. Real positive/refusal ownership is identified for the gold proof path; exhaustive layer assignment is unproven. |

## Integration non-vacuity

| Checklist item | Status | Evidence and limit |
|---|---|---|
| Trace fixture resolution; no parent autouse mock silently neuters integration | PASS, mapped top-ten paths | The top-ten Linux test uses module fixtures in its integration module ([fixture declarations](../../../tests/integration/test_container_statement_hash.py#L679)). Root `isolation_guard` delegates allowed subprocesses to real `Popen`, and `popen_spy` also delegates ([conftest.py:108–153](../../../tests/conftest.py#L108)). This does not certify unrelated integration modules.
| No assertion can pass on an empty/unseeded result | HOLD | `test_linux_dependency_cache_restores_without_provisioning` uses `all(argv[0] == GIT for argv in popen_spy)` ([line 50](../../../tests/integration/test_container_statement_hash.py#L50)) to assert that restore launched no non-Git/provisioning subprocess. An empty spy is compatible with that negative property, so `all([])` alone is not a reproduced vacuity risk. The concrete statement-hash assertion at line 55 and nonempty Docker/network assertions at lines 56–58 are positive controls ([test](../../../tests/integration/test_container_statement_hash.py#L55)). Broader empty-seed and fixture-mutation review was not executed; no count assertion is prescribed from this expression.
| SQL-string/parameter unit assertions have nonvacuous real-DB integration backing | HOLD | Cairn includes SQLite-backed persistence, but the recorded top-ten scope is the solution/Lean/container path; the broader repository/DB pairing was not audited. |
| Run suite in real environment; every skip is for a legitimately unavailable dependency | HOLD | `evidence.md` records an eight-lane historical CI run and lists skips/xfail ([lines 47–54 and 72–79](evidence.md#L47)). It does not cover the ten-lane mapped manifest or justify each skip. Pilot execution results and skip disposition belong in separate evolving pilot-runs evidence; this historical checklist does not establish them. A skip is not counted as a pass. |

## Python/pytest checklist

| Checklist item | Status | Evidence and limit |
|---|---|---|
| No `@pytest.mark.asyncio` | HOLD | No marker inventory was completed across the suite. |
| Every `pytest.param` has a readable `id=` | HOLD | No whole-suite `pytest.param` audit was completed. |
| Every `pytest.raises` uses `match=` | FAIL, sampled scope | The top-ten timeout test uses `pytest.raises(solutionplan.StepTimeout)` without `match=` ([test_container_statement_hash.py:522](../../../tests/integration/test_container_statement_hash.py#L522)); a unit plan test also has a bare `pytest.raises(solutionplan.PlanInvalid)` ([test_solution_comparison.py:253](../../../tests/unit/test_solution_comparison.py#L253)). The caught timeout's `.step` and `.timeout_s` are checked afterward, but the skill's `match=` rule is not met.
| Autouse fixtures use `yield` | PASS, mapped root fixture | `isolation_guard` performs before-state setup, yields, then compares after-state ([conftest.py:108–140](../../../tests/conftest.py#L108)). This is the autouse fixture used by the mapped paths; no claim is made about all fixtures in the repository.
| Fixtures are at the right conftest level | HOLD | The map traces root guard plus module-local Linux setup; a suite-wide scope/visibility audit was not performed. |
| Share repeated inline entity construction through a factory with complete defaults | HOLD | The sampled tests construct `challenge.Submission` inline in multiple places ([integration solution tests](../../../tests/integration/test_solution_build_compile.py#L474), [container tests](../../../tests/integration/test_container_statement_hash.py#L239)); the convenience helper is local to a unit module ([test_solution_build.py:31](../../../tests/unit/test_solution_build.py#L31)). Whether sharing preserves each proof/input distinction and safe defaults is unproven; no factory change is recommended by this checklist alone.

## Other stack-specific criteria

| Checklist group and criteria | Status | Evidence and limit |
|---|---|---|
| TypeScript/Vitest: `test.for`/`test.each`; `it.extend` cleanup; `.toThrow(/pattern/)`; `vi.mock` at module boundary | OOS | Repository manifests include Python `pyproject.toml` and Lean `lean/lean-toolchain`; no `package.json` was found. These rules do not assess Lean's formal checker. |
| Rust: `rstest`/table cases; expected `should_panic`; `errors.Is/As`; `tests/common/mod.rs` | OOS | No `Cargo.toml` was found. |
| Go: `t.Run`; loop capture; `errors.Is/As`; `t.Helper`; `t.Cleanup` | OOS | No `go.mod` was found. |
| E2E uses `skipif` for external prerequisites | OOS, mapped local CLI path | The discovered E2E module builds a temporary local slice; the mapped top ten is not service/auth E2E. The broader E2E suite's skip policy is not audited here. |
| E2E configures TLS for HTTPS | OOS, mapped local CLI path | The recorded E2E entry-point case invokes `python -m cairn` as a local subprocess ([test_m0_slice.py:345–373](../../../tests/e2e/test_m0_slice.py#L345)); no HTTP/TLS client is part of that path. |
| E2E exercises the real entry point | PASS, one existing path | The E2E test launches `sys.executable -m cairn` and asserts exit status, JSON output, and four arm outcomes ([test_m0_slice.py:345–373](../../../tests/e2e/test_m0_slice.py#L345)). |
| If the feature is not wired to the entry point, integration exists and E2E shape is documented | OOS for this path | The tested slice is wired to the module entry point in the preceding test; no unwired feature is claimed by this scope. |

## Planted false-PASS and no-claim

A tempting false PASS is “the CI profile is green, so all production branches are covered.” The retained extractor checks successful lane conclusions, one pytest summary, and duration rows ([profile_ci.py:82–123](profile_ci.py#L82)); it does not collect branch coverage. The source map covers ten slow phases, and the two plan lanes in the mapped ten-lane manifest have no timing rows in this profile. Therefore global branch coverage remains **HOLD**.

**No-Claim:** This checklist does not complete the global test audit, prove all branches covered, prove the absence of fixture leaks or duplicate tests, establish a performance gain, or authorize test reduction. It does not replace real authority tests. It makes no speedup inference from test counts, repeated fixture setup, or setup-phase durations, and offers no test-reduction prescription without a mechanical reproducer.
