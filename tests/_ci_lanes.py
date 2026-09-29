from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LEAN_PREREQUISITE_TEST_PATHS = (
    "tests/unit/test_solution_build.py",
    "tests/unit/test_solution_comparison.py",
)
LEAN_TEST_PATHS = (
    "tests/integration/test_lean_toolchain.py",
    "tests/integration/test_axiom_computation.py",
    "tests/integration/test_challenge_compile.py",
    "tests/integration/test_hasher_stability.py",
    "tests/integration/test_solution_forgery_steps.py",
    "tests/integration/test_prefilters_in_gate.py",
    "tests/unit/test_formal_statement_hasher.py",
    *LEAN_PREREQUISITE_TEST_PATHS,
)
M0_LINEAGE_TESTS = (
    "test_the_operator_sequence_produces_four_nodes_two_negatives_and_one_refusal",
    "test_the_slice_records_its_hypothesis_object_and_the_derivation_lineage",
    "test_the_derivation_commits_to_the_x_the_generator_output_determines",
    "test_the_human_rendering_names_every_node_negative_and_refusal",
)
M0_REPLAY_TESTS = (
    "test_the_same_seed_replays_from_cache_without_another_toy_curve_attempt",
    "test_a_different_seed_derives_a_different_instance",
)
M0_TRANSCRIPT_TESTS = (
    "test_skip_cache_lookup_runs_toy_curve_again_for_the_same_content",
    "test_the_green_run_logs_one_record_per_step_in_order",
    "test_the_step_transcript_matches_its_golden_after_scrubbing",
)
M0_ABORT_TEST = "test_each_abort_path_exits_gate_refused_before_m0_launch"
M0_BOUNDARY_TESTS = (
    M0_ABORT_TEST,
    "test_a_refusal_names_a_next_command_that_actually_resolves_it",
    "test_a_missing_attestation_file_exits_environment",
    "test_the_module_entry_point_runs_the_slice_with_globals_before_the_subcommand",
    "test_the_scratch_root_sits_beside_the_db_path_as_written",
    "test_the_selftest_parent_is_the_db_path_as_written",
)
M0_TEST_CASES = {
    "m0-lineage": M0_LINEAGE_TESTS,
    "m0-replay": M0_REPLAY_TESTS,
    "m0-transcript": M0_TRANSCRIPT_TESTS,
    "m0-boundaries": M0_BOUNDARY_TESTS,
}
M0_LANES = tuple(M0_TEST_CASES)
M0_ABORT_CASES = ("pin_mismatch", "uncertified_skill", "gate_plan_failure")
M0_TEST_PATHS = ("tests/e2e/test_m0_slice.py",)
GATEPLAN_TEST_PATHS = (
    "tests/integration/test_gateplan.py",
    "tests/integration/test_gateplan_cli.py",
    "tests/integration/test_ladder_gate_selftest.py",
)
SOLUTION_TEST_PATHS = ("tests/integration/test_solution_build_compile.py",)
SOLUTION_LIBRARY_TEST_PATHS = ("tests/integration/test_challenge_gate.py",)
SOLUTION_LIBRARY_CASE_TEST = "test_library_items_pass_gate"
SOLUTION_LIBRARY_BINDING_TEST = "test_a_stale_formal_statement_hash_stops_at_statement_binding_without_a_subprocess"
SOLUTION_LIBRARY_ITEMS = ("dlp", "finite_point")
SOLUTION_LIBRARY_ITEM_LANES = {
    "dlp": "solution-library-dlp",
    "finite_point": "solution-library-finite-point",
}
SOLUTION_LIBRARY_LANES = (
    "solution-library-dlp",
    "solution-library-finite-point",
    "solution-library-binding",
)
CONTAINER_TEST_PATHS = (
    "tests/integration/test_container_statement_hash.py",
    "tests/integration/test_lean_container.py",
)
LEAN_SOLUTION_TESTS = (
    "test_a_compiling_weaker_statement_fails_real_prelude_closure_comparison",
    "test_real_prelude_forgery_passes_axioms_but_fails_fresh_replay",
)
LEAN_REPLAY_TEST = LEAN_SOLUTION_TESTS[1]
LEAN_LANES = ("lean-core", "lean-replay")
SOLUTION_PLAN_TESTS = ("test_real_prelude_ordered_plan_uses_fresh_replay_and_blocks_later_checks",)
SOLUTION_PLAN_CASES = ("exact", "sorry", "timeout")
SOLUTION_PLAN_LANES = ("solution-plan-exact", "solution-plan-refusals")
CONTAINER_REPLAY_TESTS = (
    "test_linux_candidate_fresh_replay",
    "test_linux_replay_timeouts_keep_their_stage_and_check_inputs",
)
CONTAINER_COMPARISON_TESTS = (
    "test_linux_candidate_closure_comparison_matches_exact_statement",
    "test_linux_candidate_closure_comparison_refuses_weaker_statement",
)
CONTAINER_PLAN_TESTS = ("test_linux_ordered_plan_runs_each_step_in_order",)
CONTAINER_PLAN_CASES = ("exact", "sorry", "weaker", "stale-hash")
CI_LANES = (
    "python",
    "python-integration",
    *M0_LANES,
    "gateplan",
    *LEAN_LANES,
    "solution",
    *SOLUTION_LIBRARY_LANES,
    *SOLUTION_PLAN_LANES,
    "container",
    "container-replay-exact",
    "container-replay-refusals",
    "container-plan-exact",
    "container-plan-refusals",
)


def validate_manifest(root, paths):
    if not paths or len(set(paths)) != len(paths):
        raise pytest.UsageError("CI lane manifest must be nonempty and contain no duplicate paths")
    for path in paths:
        relative = Path(path)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not path.startswith("tests/")
            or not relative.name.startswith("test_")
            or relative.suffix != ".py"
            or not (root / relative).is_file()
        ):
            raise pytest.UsageError(f"CI lane manifest has an invalid or missing test file: {path}")


def pytest_addoption(parser):
    parser.addoption(
        "--cairn-ci-lane",
        choices=(
            "all",
            "m0",
            "lean",
            "solution-library",
            "solution-plan",
            "container-replay",
            "container-plan",
            *CI_LANES,
        ),
        default="all",
    )


def pytest_ignore_collect(collection_path, config):
    if not config.getoption("--cairn-ci-lane").startswith("container") or not collection_path.is_file():
        return None
    if not collection_path.is_relative_to(config.rootpath):
        return None
    if collection_path.relative_to(config.rootpath).as_posix() not in CONTAINER_TEST_PATHS:
        return True
    return None


def pytest_collection_modifyitems(config, items):
    validate_manifest(ROOT, LEAN_TEST_PATHS)
    validate_manifest(ROOT, M0_TEST_PATHS)
    validate_manifest(ROOT, GATEPLAN_TEST_PATHS)
    validate_manifest(ROOT, SOLUTION_TEST_PATHS)
    validate_manifest(ROOT, SOLUTION_LIBRARY_TEST_PATHS)
    validate_manifest(ROOT, CONTAINER_TEST_PATHS)
    validate_manifest(
        ROOT,
        (
            *LEAN_TEST_PATHS,
            *M0_TEST_PATHS,
            *GATEPLAN_TEST_PATHS,
            *SOLUTION_TEST_PATHS,
            *SOLUTION_LIBRARY_TEST_PATHS,
            *CONTAINER_TEST_PATHS,
        ),
    )
    lane = config.getoption("--cairn-ci-lane")
    selected = []
    deselected = []
    for item in items:
        path = item.path.relative_to(config.rootpath).as_posix()
        if path in SOLUTION_TEST_PATHS:
            if item.originalname in SOLUTION_PLAN_TESTS:
                case = getattr(item, "callspec", None)
                case = case.params.get("case") if case is not None else None
                if case not in SOLUTION_PLAN_CASES:
                    raise pytest.UsageError(f"invalid ordered-plan case: {item.nodeid}: {case!r}")
                item_lane = "solution-plan-exact" if case == "exact" else "solution-plan-refusals"
            else:
                if item.originalname in LEAN_SOLUTION_TESTS:
                    item_lane = "lean-replay" if item.originalname == LEAN_REPLAY_TEST else "lean-core"
                else:
                    item_lane = "solution"
        elif path in M0_TEST_PATHS:
            item_lane = next(
                (group for group, names in M0_TEST_CASES.items() if item.originalname in names),
                "m0-boundaries",
            )
        elif path in GATEPLAN_TEST_PATHS:
            item_lane = "gateplan"
        elif path in SOLUTION_LIBRARY_TEST_PATHS:
            if item.originalname == SOLUTION_LIBRARY_CASE_TEST:
                callspec = getattr(item, "callspec", None)
                library_item = None if callspec is None or "item" not in callspec.params else callspec.params["item"]
                if library_item not in SOLUTION_LIBRARY_ITEM_LANES:
                    raise pytest.UsageError(f"invalid solution-library item: {item.nodeid}: {library_item!r}")
                item_lane = SOLUTION_LIBRARY_ITEM_LANES[library_item]
            elif item.originalname == SOLUTION_LIBRARY_BINDING_TEST:
                item_lane = "solution-library-binding"
            else:
                raise pytest.UsageError(f"unassigned solution-library test: {item.nodeid}")
        elif path in LEAN_TEST_PATHS:
            item_lane = "lean-core"
        elif path in CONTAINER_TEST_PATHS:
            if item.originalname in CONTAINER_REPLAY_TESTS:
                case = getattr(item, "callspec", None)
                proof = case.params.get("proof") if case is not None else None
                item_lane = "container-replay-exact" if proof == "rfl" else "container-replay-refusals"
            elif item.originalname in CONTAINER_PLAN_TESTS:
                case = getattr(item, "callspec", None)
                case = case.params.get("case") if case is not None else None
                if case not in CONTAINER_PLAN_CASES:
                    raise pytest.UsageError(f"invalid container plan case: {item.nodeid}: {case!r}")
                item_lane = "container-plan-exact" if case == "exact" else "container-plan-refusals"
            elif item.originalname in CONTAINER_COMPARISON_TESTS:
                item_lane = (
                    "container-replay-exact"
                    if item.originalname == CONTAINER_COMPARISON_TESTS[0]
                    else "container-replay-refusals"
                )
            else:
                item_lane = "container"
        elif path.startswith("tests/integration/"):
            item_lane = "python-integration"
        else:
            item_lane = "python"
        matches = (
            lane == "all"
            or item_lane == lane
            or (
                lane in ("lean", "solution-library", "solution-plan", "container-replay", "container-plan")
                and item_lane.startswith(f"{lane}-")
            )
            or (lane == "m0" and item_lane.startswith("m0-"))
        )
        (selected if matches else deselected).append(item)
    items[:] = selected
    config.hook.pytest_deselected(items=deselected)
