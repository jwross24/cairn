# Bead classification evidence

Scope authority: MagentaSparrow agent-mail 415, 2026-09-29. Cairn emits the class decision; fleet routing owns model assignments. Classification is not correctness or model-quality evidence.

## Source and checks

`bead-routing-2026-09-29/manifest.json` records the base revision, source byte counts, SHA-256 digests, mutation patches, and exit codes. The implementation and test changes were reviewed line by line by the parent agent.

```sh
scripts/check.sh --fast --paths scripts/route.py tests/unit/test_route.py AGENTS.md research/decisions/adr-015-bead-model-routing.md
uv run pytest --no-header -q --tb=short --disable-warnings tests/unit/test_route.py tests/unit/test_identity_sources.py
```

The scoped fast gate passed. The affected suite passed 64 tests with no skips. The 2,140 warnings concern pytest cleanup of retained temporary directories; `--disable-warnings` suppresses their repeated detail, not tests. Raw result: `bead-routing-2026-09-29/tests.txt`.

## Real CLI observations

```sh
uv run python scripts/route.py cairn-readme-3zd
uv run python scripts/route.py cairn-m1-cqt.5.6
uv run python scripts/route.py cairn-fjd7
```

All three commands exited 0 and emitted exactly `class`, `reasons`, `floor`, and `judge`. Their JSON is retained in `mechanical.json`, `critical.json`, and `gray.json` beneath `bead-routing-2026-09-29/`.

The README bead has a Mechanical floor and does not call the judge. It identifies `README.md` in its body but has no literal `Touches:` line; it alone does not satisfy an acceptance clause requiring that literal field. Documentation-only `Touches:` lines have automated coverage.

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

The first five mutations used test bytes differing from the final test module only in the unrelated unknown-class test. The unknown-class mutation uses the final test module. No identity-bearing production source or golden is modified by this work.

## Verification boundary

This artifact records local evidence. Pushed CI and committed-code replay are separate close requirements recorded in the bead. Unknown-model validation and a model assignment table are outside the scope authorized in mail 415. The untracked table file is excluded from this change.
