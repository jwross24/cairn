# Bead classification evidence

Scope authority: MagentaSparrow agent-mail 415, 2026-09-29. Cairn emits the class decision; fleet routing owns model assignments. Classification is not correctness or model-quality evidence.

## Source and checks

`bead-routing-2026-09-29/manifest.json` records the base revision, source byte counts, SHA-256 digests, mutation patches, and exit codes. The implementation and test changes were reviewed line by line by the parent agent. Committed acceptance uses `561f0f0213731b36d5d5993a105448fb109e15e8`; the four reviewed source files match the recorded byte counts and digests.

```sh
scripts/check.sh --fast --paths scripts/route.py tests/unit/test_route.py AGENTS.md research/decisions/adr-015-bead-model-routing.md
uv run pytest --no-header -q --tb=short --disable-warnings tests/unit/test_route.py tests/unit/test_identity_sources.py
```

The scoped fast gate passed. The affected suite passed 64 tests with no skips, including the replay on committed code. The 2,140 warnings concern pytest cleanup of retained temporary directories; `--disable-warnings` suppresses their repeated detail, not tests. Raw committed result: `bead-routing-2026-09-29/committed/tests.txt`.

## Real CLI observations

```sh
uv run python scripts/route.py cairn-readme-3zd
uv run python scripts/route.py cairn-m1-cqt.5.6
uv run python scripts/route.py cairn-fjd7
```

All three commands exited 0 on committed code and emitted exactly `class`, `reasons`, `floor`, and `judge`. Their JSON is retained in `mechanical-with-touches.json`, `critical.json`, and `gray.json` beneath `bead-routing-2026-09-29/committed/`.

The README bead has the accurate `Touches: README.md` metadata authorized by MagentaSparrow in agent-mail 419. It receives a Mechanical floor without calling the judge. Documentation-only `Touches:` lines also have automated coverage.

The formalization bead has a Critical floor and does not call the judge. The gate-reporting bead has a Standard floor and received a live Demanding answer with no judge error. The call used `/Users/jwross/.local/bin/codex`, version `0.155.0-alpha.16`, with the fixed first-party judge and low effort. A single response establishes adapter execution, not classifier calibration.

## Guard-removal experiments

Each experiment uses a separate scratch copy of the repository. The production router is unchanged. The retained patch identifies the exact guard removed; the corresponding text file contains the failing assertion. Every invocation exited 1 for the assertion stated below.

- `mutation-critical.patch`: removing the Critical floor yields Demanding instead of Critical in `test_critical_body_path_cannot_be_lowered_by_route_label`.
- `mutation-label.patch`: permitting a lowering label yields Mechanical instead of Critical in the same test.
- `mutation-judge.patch`: accepting a Mechanical judge answer yields Mechanical instead of Demanding in `test_gray_judge_cannot_select_mechanical`.
- `mutation-fallback.patch`: lowering the failure fallback yields Standard instead of Demanding for timeout, garbage, list/dict classes, empty reasons, and multiline reasons in `test_judge_timeout_and_garbage_route_demanding`.
- `mutation-identity.patch`: omitting the skill registry leaves the added identity source Mechanical instead of Critical in `test_new_skill_identity_source_changes_classification_without_router_edit`.
- `mutation-unknown-class.patch`: accepting an unknown label produces `DID NOT RAISE RouteError` in `test_unknown_route_label_refuses`.

For each scratch tree, run the corresponding test node with its own sources on the import path:

```sh
cd "$scratch_tree"
PYTHONPATH="$scratch_tree/src:$scratch_tree/tests" \
  uv run --no-project --python /Users/jwross/Documents/cairn/.venv/bin/python \
  -m pytest --no-header -q --tb=short --disable-warnings \
  "tests/unit/test_route.py::$test_name"
```

Committed mutation replays use exact committed test bytes and the committed router plus the corresponding retained patch. Patch-byte and SHA-256 comparisons passed. The `committed/` directory retains each replay's failing output. No identity-bearing production source or golden is modified by this work.

## Verification boundary

CI run [36644266988](https://github.com/jwross24/cairn/actions/runs/36644266988) completed successfully on pushed commit `561f0f0213731b36d5d5993a105448fb109e15e8`. All 20 jobs succeeded. The parent independently checked the exact SHA, terminal conclusions, and all 26 router cases marked PASSED in the Python lane. Raw job metadata is in `bead-routing-2026-09-29/committed/implementation-ci.json`.

Exclusions are explicit: the existing live compliance gatherer and renderer drift checks were skipped, and `test_the_corpus_bars_are_met` was xfailed. None is counted as passed or as evidence supplied by this router change.

Unknown-model validation and a model assignment table are outside the scope authorized in mail 415. The untracked table file is excluded from this change. Owner mail 419 authorizes the standalone closure/evidence push after green implementation CI.
