# Lean lane timeout observation

Two CI receipts for `tests/integration/test_solution_build_compile.py::test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison` show different elapsed times. Receipt `36596493998` at `2de797830071146bc4433983e8ff8e5d3f90bebe` records 82.857811 s and a passing test event. Receipt `36598858989` at `0e9b47018c788df4904b836865deab755b814429` records a 177.53711 s test event, followed by pytest's 180 s timeout during `tmp_path` teardown. The slower duration is 2.14× the earlier duration.

The CI output and both per-test JSONL receipts are preserved in [`lane-partition/raw/`](lane-partition/raw/); their original and compressed lengths and SHA-256 digests are in [`lane-partition/raw/manifest.json`](lane-partition/raw/manifest.json). The failed receipt identifies cleanup in pytest's `tmp_path` teardown when the timeout fired. It does not identify why the test took longer.

The source comparison below returned exit 0, with no diff for the selected test, fixture, logging, build, and comparison files between the two receipt revisions:

```bash
git diff --exit-code 2de797830071146bc4433983e8ff8e5d3f90bebe 0e9b47018c788df4904b836865deab755b814429 -- tests/integration/test_solution_build_compile.py tests/conftest.py tests/_test_logging.py src/cairn/solutionbuild.py src/cairn/solutionchecks.py
```

An owner-authorized 900 s timeout applies to this weaker-statement test in commit `822498a3beca1eefcba55c3a25fd45eb68bd4f78`, matching its real-prelude siblings. The 1080 s session limit and 20-minute job limit remain in place. The receipts show observed runtime variance; they do not establish a cause, a flake, or a test defect.
