import hashlib
import json
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.grounding import probe_clock_reference_cost
from research.grounding import probe_constant_work as constant_work
from research.grounding import probe_counted_process as probe
from research.grounding import probe_deployed_cpu as deployed_cpu
from research.grounding import probe_deployed_rate as deployed
from research.grounding import probe_paired_rate as paired


def _payload(mode, ops, count, point, child_cpu_ns=None):
    return {
        "mode": mode,
        "requested_ops": ops,
        "count": count,
        "point": point,
        "child_cpu_ns": child_cpu_ns,
    }


def test_the_scalar_oracle_matches_the_reference_point():
    assert probe.expected_point(10_000) == (476377072802646283, 562446501424608226)


@pytest.mark.parametrize(
    ("mode", "count", "point"),
    [
        ("raw", None, list(probe.expected_point(3))),
        ("counted", 3, list(probe.expected_point(3))),
        ("count-only", 3, None),
        ("zero-work", 0, None),
    ],
)
def test_a_valid_result_matches_its_mode_count_and_point(mode, count, point):
    payload = _payload(mode, 3, count, point, 0)
    assert probe.validate_payload(payload, mode, 3, timed=True) == payload


def test_a_wrong_count_is_refused():
    payload = _payload("counted", 3, 2, list(probe.expected_point(3)), 1)
    with pytest.raises(probe.ProbeError, match="count was"):
        probe.validate_payload(payload, "counted", 3, timed=True)


def test_a_boolean_count_is_not_an_integer_count():
    payload = _payload("counted", 1, True, list(probe.expected_point(1)), 1)
    with pytest.raises(probe.ProbeError, match="count was"):
        probe.validate_payload(payload, "counted", 1, timed=True)


def test_a_wrong_point_is_refused():
    x, y = probe.expected_point(3)
    payload = _payload("counted", 3, 3, [x, (y + 1) % probe.P], 1)
    with pytest.raises(probe.ProbeError, match="point was"):
        probe.validate_payload(payload, "counted", 3, timed=True)


def test_a_boolean_coordinate_is_not_an_integer_coordinate():
    payload = _payload("counted", 1, 1, [True, 0], 1)
    with pytest.raises(probe.ProbeError, match="coordinates must be integers"):
        probe.validate_payload(payload, "counted", 1, timed=True)


@pytest.mark.parametrize("stdout", ["not json", "[]", '{"mode":"raw"} trailing', '{"mode":"raw","mode":"raw"}'])
def test_malformed_or_ambiguous_output_is_refused(stdout):
    with pytest.raises(probe.ProbeError):
        probe.decode_output(stdout)


@pytest.mark.parametrize("field", ["count", "point", "child_cpu_ns"])
def test_missing_or_extra_protocol_fields_are_refused(field):
    payload = _payload("counted", 1, 1, list(probe.expected_point(1)), 1)
    del payload[field]
    with pytest.raises(probe.ProbeError, match="closed protocol"):
        probe.validate_payload(payload, "counted", 1, timed=True)
    payload[field] = None
    payload["extra"] = 0
    with pytest.raises(probe.ProbeError, match="closed protocol"):
        probe.validate_payload(payload, "counted", 1, timed=True)


@pytest.mark.parametrize("timing", [-1, probe.MAX_U64 + 1, 1.0, True, float("nan"), float("inf")])
def test_invalid_child_timing_is_refused(timing):
    payload = _payload("counted", 1, 1, list(probe.expected_point(1)), timing)
    with pytest.raises(probe.ProbeError, match="nonnegative integer"):
        probe.validate_payload(payload, "counted", 1, timed=True)


def test_an_untimed_result_cannot_carry_timing_evidence():
    payload = _payload("counted", 1, 1, list(probe.expected_point(1)), 0)
    with pytest.raises(probe.ProbeError, match="untimed process"):
        probe.validate_payload(payload, "counted", 1, timed=False)


def test_missing_compiler_and_binary_fail_loudly(tmp_path):
    with pytest.raises(probe.ProbeError, match="compiler is missing"):
        probe.build_binary(tmp_path / "missing-clang")
    with pytest.raises(probe.ProbeError, match="binary is missing"):
        probe.run_binary(tmp_path / "missing-binary", "counted", 1)


def test_an_external_binary_without_a_source_has_unknown_source_provenance():
    assert probe._source_metadata({"compiler": None}) == {
        "source": None,
        "source_sha256": None,
        "source_provenance": "unknown_external_binary",
    }


def test_an_external_binary_source_is_recorded_as_unverified(tmp_path):
    source = tmp_path / "counted_process.c"
    source.write_text("source artifact\n")
    metadata = probe._source_metadata({"compiler": None}, source)
    assert metadata["source"] == str(source)
    assert metadata["source_sha256"] == probe._sha256(source)
    assert metadata["source_provenance"] == "supplied_source_unverified"


def test_decode_output_rejects_duplicate_keys():
    with pytest.raises(probe.ProbeError, match="duplicate output key"):
        probe.decode_output(json.dumps({"mode": "raw"})[:-1] + ',"mode":"counted"}')


def _reference_payload(ops, cpu_s=0.001234567):
    point = probe.expected_point(ops)
    return {"cpu_s": cpu_s, "x": point[0], "y": point[1], "inf": 0}


def _synthetic_row(pair, reference_cpu_ns, counted_cpu_ns, reference_wall_ns, counted_wall_ns):
    reference = {"child_cpu_ns": reference_cpu_ns, "parent_wall_ns": reference_wall_ns}
    counted_arm = {"child_cpu_ns": counted_cpu_ns, "parent_wall_ns": counted_wall_ns, "count": 10_000}
    return {
        "pair": pair,
        "order": ["reference", "counted"],
        "reference": reference,
        "counted": counted_arm,
        "ratio": paired.pair_ratios(reference, counted_arm),
    }


def test_the_reference_source_is_the_clock_reference_text():
    assert paired.REFERENCE_SOURCE is probe_clock_reference_cost.C_SOURCE
    expected = hashlib.sha256(probe_clock_reference_cost.C_SOURCE.encode()).hexdigest()
    assert paired.reference_source_sha256() == expected


def test_a_valid_reference_payload_yields_child_cpu_ns():
    assert paired.validate_reference(_reference_payload(3), 3) == 1234567


def test_a_wrong_reference_point_is_refused():
    payload = _reference_payload(3)
    payload["y"] = (payload["y"] + 1) % probe.P
    with pytest.raises(probe.ProbeError, match="reference point was"):
        paired.validate_reference(payload, 3)


@pytest.mark.parametrize("cpu_s", [True, -1.0, float("nan"), float("inf")])
def test_a_boolean_or_negative_reference_cpu_is_refused(cpu_s):
    with pytest.raises(probe.ProbeError):
        paired.validate_reference(_reference_payload(3, cpu_s), 3)


@pytest.mark.parametrize(
    "stdout",
    [
        '{"cpu_s": 0.1, "x": 1, "y": 2}',
        '{"cpu_s": 0.1, "x": 1, "y": 2, "inf": 0, "extra": 0}',
        '{"cpu_s": 0.1, "cpu_s": 0.2, "x": 1, "y": 2, "inf": 0}',
        "not json",
        "[]",
    ],
)
def test_reference_output_with_extra_or_missing_fields_is_refused(stdout):
    with pytest.raises(probe.ProbeError):
        paired.decode_reference_output(stdout)


def test_pair_order_is_deterministic_and_uses_both_orders():
    seed = paired.PREREGISTERED["seed"]
    first = [paired.pair_order(seed, pair) for pair in range(1, 32)]
    second = [paired.pair_order(seed, pair) for pair in range(1, 32)]
    assert first == second
    assert set(first) == {("reference", "counted"), ("counted", "reference")}


def test_ratio_summary_and_spread_are_exact_on_synthetic_rows():
    rows = [_synthetic_row(pair, 1000, 1000 + 100 * (pair - 1), 2000, 2000 + 200 * (pair - 1)) for pair in range(1, 6)]
    cpu = paired.summarize_ratios(rows)["cpu"]
    assert cpu["n"] == 5
    assert cpu["min"] == "1.000000000"
    assert cpu["median"] == "1.200000000"
    assert cpu["max"] == "1.400000000"
    assert cpu["spread"] == "0.333333333"
    assert cpu["sd"] == f"{statistics.stdev([1.0, 1.1, 1.2, 1.3, 1.4]):.9f}"


def test_spread_verdict_flips_at_the_preregistered_bound():
    bound = paired.PREREGISTERED["spread_bound"]
    at_bound = {kind: {"spread": "0"} for kind in paired.RATIO_KINDS} | {"cpu": {"spread": "0.30"}}
    over_bound = {kind: {"spread": "0"} for kind in paired.RATIO_KINDS} | {"cpu": {"spread": "0.300000001"}}
    assert paired.spread_verdicts(at_bound, bound)["cpu"] == "within_bound"
    assert paired.spread_verdicts(over_bound, bound)["cpu"] == "exceeded"


def test_non_preregistered_settings_require_the_exploratory_flag():
    with pytest.raises(SystemExit):
        paired._arguments(["--arm", "x", "--pairs", "5"])
    exploratory = paired._arguments(["--arm", "x", "--pairs", "5", "--exploratory"])
    assert exploratory.pairs == 5
    assert exploratory.exploratory is True
    defaults = paired._arguments(["--arm", "x"])
    assert (defaults.pairs, defaults.ops, defaults.seed) == (
        paired.PREREGISTERED["pairs"],
        paired.PREREGISTERED["ops"],
        paired.PREREGISTERED["seed"],
    )
    assert defaults.exploratory is False


def test_host_observations_never_raise_and_carry_a_timestamp(monkeypatch):
    monkeypatch.setattr(paired, "_run_text", lambda argv: None)
    observed = paired.host_observations()
    expected_keys = {
        "load_1m",
        "free_pages_16k",
        "kern_num_files",
        "meminfo_free_kb",
        "file_nr",
        "loadavg_line",
        "taken_at",
    }
    assert set(observed) == expected_keys
    assert datetime.fromisoformat(observed["taken_at"]).tzinfo is not None


def test_host_readers_parse_darwin_text_and_yield_none_for_a_missing_tool(monkeypatch):
    vm_stat = "Pages free:                               25603.\nPages active:  9.\n"
    assert paired._first_int(r"Pages free:\s+(\d+)\.", vm_stat) == 25603
    assert paired._first_int(r"MemFree:\s+(\d+)\s+kB", "MemFree:  4096 kB\n") == 4096
    assert paired._first_int(r"Pages free:\s+(\d+)\.", None) is None
    assert paired._int_list("1 2 3\n", 3) == [1, 2, 3]
    assert paired._int_list("1 2\n", 3) is None
    monkeypatch.setattr(paired, "_run_text", lambda argv: None)
    observed = paired.host_observations()
    assert observed["kern_num_files"] is None
    assert observed["free_pages_16k"] is None


@pytest.mark.parametrize(
    ("median", "verdict"),
    [
        ("0.90", "within_bound"),
        ("1.10", "within_bound"),
        ("1.000000000", "within_bound"),
        ("0.899999999", "exceeded"),
        ("1.100000001", "exceeded"),
    ],
)
def test_null_verdict_flips_outside_the_median_band(median, verdict):
    bound = paired.PREREGISTERED["null_median_bound_cpu"]
    assert paired.null_verdict({"cpu": {"median": median}}, bound) == verdict


def test_ratio_summary_handles_rows_with_two_ratio_kinds():
    rows = [{"ratio": {"cpu": f"{1 + pair / 10:.9f}", "wall": "1.000000000"}} for pair in range(3)]
    summary = paired.summarize_ratios(rows)
    assert set(summary) == {"cpu", "wall"}
    assert summary["cpu"]["median"] == "1.100000000"
    assert summary["wall"]["spread"] == "0.000000000"


def _serve_payload(count, point=None):
    return {"mode": "serve", "requested_ops": 3, "count": count, "point": point, "child_cpu_ns": 5}


def test_a_valid_serve_summary_is_accepted():
    payload = _serve_payload(3)
    assert deployed.validate_serve_summary(payload, 3) == payload


def test_a_serve_summary_with_a_wrong_count_is_refused():
    with pytest.raises(deployed.ServeError, match="serve count was"):
        deployed.validate_serve_summary(_serve_payload(2), 3)


def test_a_serve_summary_that_reports_a_point_is_refused():
    with pytest.raises(deployed.ServeError):
        deployed.validate_serve_summary(_serve_payload(3, [1, 2]), 3)


@pytest.mark.parametrize("junk", ["1\n", "1 2 3\n", "a b\n", f"{deployed.counted.P} 1\n", "True 1\n"])
def test_serve_responses_parse_points_and_refuse_junk(junk):
    assert deployed._parse_response("1 2\n") == (1, 2)
    assert deployed._parse_response("inf\n") is None
    with pytest.raises(deployed.ServeError):
        deployed._parse_response(junk)


def test_requests_alternate_double_and_add_and_refuse_infinity():
    assert deployed._request(0, (5, 7)) == "d 5 7\n"
    assert deployed._request(1, (5, 7)) == f"a 5 7 {deployed.counted.GX} {deployed.counted.GY}\n"
    with pytest.raises(deployed.ServeError):
        deployed._request(0, None)


def test_arm_order_is_deterministic_and_a_permutation():
    seed = deployed.PREREGISTERED["seed"]
    first = [deployed.arm_order(seed, pair) for pair in range(1, 16)]
    second = [deployed.arm_order(seed, pair) for pair in range(1, 16)]
    assert first == second
    assert all(sorted(order) == sorted(deployed.ARMS) for order in first)
    assert len(set(first)) >= 2


def test_pair_ratios_divide_parent_wall_by_reference_child_cpu():
    results = {
        "reference": {"ops": 10_000, "child_cpu_ns": 1_000_000, "parent_wall_ns": 2_000_000},
        "batch": {"ops": 10_000, "parent_wall_ns": 2_500_000, "child_cpu_ns": 1, "count": 10_000},
        "trial_batch": {"ops": 40_000, "parent_wall_ns": 12_000_000, "child_cpu_ns": 1, "count": 40_000},
        "ipc": {"ops": 10_000, "parent_wall_ns": 300_000_000, "child_cpu_ns": 1, "count": 10_000},
    }
    assert deployed.pair_ratios(results) == {
        "deployed_batch": "2.500000000",
        "deployed_trial_batch": "3.000000000",
        "deployed_ipc": "300.000000000",
    }


def test_figures_follow_the_rule_and_the_bound_evaluates_exactly():
    summary = {
        "deployed_batch": {"median": "2.4", "max": "3.9", "spread": "0.1"},
        "deployed_trial_batch": {"median": "1.5", "max": "2.0", "spread": "0.9"},
        "deployed_ipc": {"median": "300", "max": "400", "spread": "0.2"},
    }
    verdicts = deployed.spread_verdicts(summary, deployed.PREREGISTERED["spread_bound"])
    assert verdicts == {
        "deployed_batch": "within_bound",
        "deployed_trial_batch": "exceeded",
        "deployed_ipc": "within_bound",
    }
    chosen = deployed.figures(summary, verdicts)
    assert {kind: entry["figure"] for kind, entry in chosen.items()} == {
        "deployed_batch": "2.4",
        "deployed_trial_batch": "2.0",
        "deployed_ipc": "300",
    }
    bound = {"clock_tolerance": "0.10", "keep_band_excess": "0.2432"}
    evaluation = deployed.evaluate_bound(bound, chosen)
    assert evaluation["deployed_batch"]["product"] == "0.240000000"
    assert [evaluation[kind]["holds"] for kind in deployed.RATIO_KINDS] == [True, True, False]
    committed = deployed.clock_bound()
    assert committed["max_admissible_ratio"] == "2.432000000"
    assert committed["current_rate_ratio"] == "1.0"


def test_verify_chain_refuses_a_wrong_intermediate_point_behind_the_right_endpoint():
    ec = deployed.counted.ec
    base = (deployed.counted.GX, deployed.counted.GY)
    first = ec.double(deployed.counted.P, deployed.counted.A, base)
    second = ec.add(deployed.counted.P, deployed.counted.A, first, base)
    assert deployed.verify_chain([first, second], 2) == deployed.counted.expected_point(2)
    with pytest.raises(deployed.ServeError, match="serve response 0 was"):
        deployed.verify_chain([(1, 2), second], 2)
    with pytest.raises(deployed.ServeError, match="serve returned 1 responses"):
        deployed.verify_chain([first], 2)


def test_a_silent_serve_child_is_killed_at_the_timeout(monkeypatch):
    popen = deployed.subprocess.Popen
    silent = [sys.executable, "-c", "import time; time.sleep(5)"]
    monkeypatch.setattr(deployed, "SERVE_TIMEOUT_S", 0.2)
    monkeypatch.setattr(deployed.subprocess, "Popen", lambda argv, **kw: popen(silent, **kw))
    started = time.monotonic()
    with pytest.raises(deployed.ServeError, match="closed its output"):
        deployed.run_serve(sys.executable, 1)
    assert time.monotonic() - started < 2


def _fake_serve_child(monkeypatch, source):
    popen = deployed.subprocess.Popen
    monkeypatch.setattr(deployed.subprocess, "Popen", lambda argv, **kw: popen([sys.executable, "-c", source], **kw))


def test_output_after_the_serve_summary_is_refused(monkeypatch):
    point = deployed.counted.expected_point(1)
    summary = json.dumps({"mode": "serve", "requested_ops": 1, "count": 1, "point": None, "child_cpu_ns": 1})
    source = "\n".join(
        [
            "import sys, time",
            "sys.stdin.readline()",
            f"print('{point[0]} {point[1]}', flush=True)",
            "sys.stdin.readline()",
            f"sys.stdout.write({summary + chr(10) + 'UNEXPECTED' + chr(10)!r})",
            "sys.stdout.flush()",
            "time.sleep(0.1)",
        ]
    )
    _fake_serve_child(monkeypatch, source)
    with pytest.raises(deployed.ServeError, match="wrote after its summary"):
        deployed.run_serve(sys.executable, 1)


def test_a_refused_serve_child_is_reaped(monkeypatch):
    children = []
    popen = deployed.subprocess.Popen

    def spawn(argv, **kw):
        child = popen([sys.executable, "-c", 'import time; print("bad", flush=True); time.sleep(30)'], **kw)
        children.append(child)
        return child

    monkeypatch.setattr(deployed.subprocess, "Popen", spawn)
    with pytest.raises(deployed.ServeError, match="not a point"):
        deployed.run_serve(sys.executable, 1)
    assert children[0].returncode is not None
    assert all(stream.closed for stream in (children[0].stdin, children[0].stdout, children[0].stderr))


def test_a_child_that_exits_before_the_first_request_is_refused_and_closed(monkeypatch):
    children = []
    popen = deployed.subprocess.Popen

    def spawn(argv, **kw):
        child = popen([sys.executable, "-c", "pass"], **kw)
        child.wait()
        children.append(child)
        return child

    monkeypatch.setattr(deployed.subprocess, "Popen", spawn)
    with pytest.raises(deployed.ServeError):
        deployed.run_serve(sys.executable, 1)
    assert all(stream.closed for stream in (children[0].stdin, children[0].stdout, children[0].stderr))


def test_non_preregistered_deployed_settings_require_the_exploratory_flag():
    with pytest.raises(SystemExit):
        deployed._arguments(["--arm", "x", "--pairs", "3"])
    assert deployed._arguments(["--arm", "x", "--pairs", "3", "--exploratory"]).pairs == 3
    defaults = deployed._arguments(["--arm", "x"])
    assert (defaults.pairs, defaults.ops, defaults.trial_ops, defaults.seed) == (
        deployed.PREREGISTERED["pairs"],
        deployed.PREREGISTERED["ops"],
        deployed.PREREGISTERED["trial_ops"],
        deployed.PREREGISTERED["seed"],
    )


def test_cpu_delta_sums_self_and_children_and_refuses_backwards_counters():
    before = {"self_ns": 100, "children_ns": 1000}
    assert deployed_cpu.cpu_delta(before, {"self_ns": 150, "children_ns": 1600}) == {
        "parent_cpu_ns": 50,
        "children_cpu_ns": 600,
        "tree_cpu_ns": 650,
    }
    with pytest.raises(deployed_cpu.counted.ProbeError, match="backwards"):
        deployed_cpu.cpu_delta(before, {"self_ns": 150, "children_ns": 900})


def test_call_with_cpu_reads_rusage_at_the_reap_hook(monkeypatch):
    phase = {"name": "before"}
    readings = {
        "before": {"self_ns": 0, "children_ns": 0},
        "hook": {"self_ns": 7, "children_ns": 13},
        "after": {"self_ns": 99, "children_ns": 99},
    }
    monkeypatch.setattr(deployed_cpu, "rusage_ns", lambda: dict(readings[phase["name"]]))

    def fake_call(*args, after_reap):
        phase["name"] = "hook"
        after_reap()
        phase["name"] = "after"
        return {"ops": 10, "child_cpu_ns": 5, "parent_wall_ns": 9}

    monkeypatch.setattr(deployed_cpu.deployed, "_call_arm", fake_call)
    assert deployed_cpu.call_with_cpu("batch", "ref", "counted", 10, 20) == {
        "ops": 10,
        "child_cpu_ns": 5,
        "parent_wall_ns": 9,
        "parent_cpu_ns": 7,
        "children_cpu_ns": 13,
        "tree_cpu_ns": 20,
    }


def test_an_arm_call_that_never_reaps_is_refused(monkeypatch):
    monkeypatch.setattr(deployed_cpu, "rusage_ns", lambda: {"self_ns": 0, "children_ns": 0})
    monkeypatch.setattr(
        deployed_cpu.deployed,
        "_call_arm",
        lambda *args, after_reap: {"ops": 10, "child_cpu_ns": 5, "parent_wall_ns": 9},
    )
    with pytest.raises(deployed_cpu.counted.ProbeError, match="reported 0 reaps"):
        deployed_cpu.call_with_cpu("batch", "ref", "counted", 10, 20)


def test_cpu_pair_ratios_divide_tree_cpu_by_reference_child_cpu():
    results = {
        "reference": {"ops": 10_000, "child_cpu_ns": 1_000_000, "tree_cpu_ns": 2_500_000},
        "batch": {"ops": 10_000, "tree_cpu_ns": 2_000_000},
        "trial_batch": {"ops": 40_000, "tree_cpu_ns": 5_000_000},
        "ipc": {"ops": 10_000, "tree_cpu_ns": 60_000_000},
    }
    assert deployed_cpu.pair_ratios(results) == {
        "cpu_deployed_batch": "2.000000000",
        "cpu_deployed_trial_batch": "1.250000000",
        "cpu_deployed_ipc": "60.000000000",
    }
    results["reference"]["child_cpu_ns"] = 0
    with pytest.raises(deployed_cpu.counted.ProbeError):
        deployed_cpu.pair_ratios(results)


def test_cpu_figures_follow_the_rule_and_the_bound_evaluates():
    summary = {
        "cpu_deployed_batch": {"median": "2.3", "max": "2.6", "spread": "0.2"},
        "cpu_deployed_trial_batch": {"median": "1.3", "max": "1.9", "spread": "0.7"},
        "cpu_deployed_ipc": {"median": "60", "max": "70", "spread": "0.1"},
    }
    verdicts = deployed_cpu.spread_verdicts(summary, deployed_cpu.PREREGISTERED["spread_bound"])
    assert verdicts == {
        "cpu_deployed_batch": "within_bound",
        "cpu_deployed_trial_batch": "exceeded",
        "cpu_deployed_ipc": "within_bound",
    }
    figures = deployed_cpu.figures(summary, verdicts)
    assert [figures[kind]["figure"] for kind in deployed_cpu.RATIO_KINDS] == ["2.3", "1.9", "60"]
    evaluation = deployed_cpu.deployed.evaluate_bound(
        {"clock_tolerance": "0.10", "keep_band_excess": "0.2432"}, figures
    )
    assert [evaluation[kind]["holds"] for kind in deployed_cpu.RATIO_KINDS] == [True, True, False]
    assert evaluation["cpu_deployed_batch"]["product"] == "0.230000000"


def test_cpu_preregistration_mirrors_the_wall_probe_and_names_the_quantity():
    cpu = deployed_cpu.PREREGISTERED
    wall = deployed_cpu.deployed.PREREGISTERED
    for field in ("pairs", "ops", "trial_ops", "seed", "warmup_calls_per_arm"):
        assert cpu[field] == wall[field]
    assert cpu["arms"] == list(deployed_cpu.deployed.ARMS)
    spread_bound = cpu["spread_bound"]
    assert isinstance(spread_bound, dict)
    assert set(spread_bound) == set(deployed_cpu.RATIO_KINDS)
    assert set(spread_bound.values()) == {"0.50"}
    quantity = cpu["quantity"]
    assert isinstance(quantity, str)
    assert "RUSAGE_CHILDREN" in quantity
    assert "cpu" not in spread_bound


def test_non_preregistered_cpu_settings_require_the_exploratory_flag():
    with pytest.raises(SystemExit):
        deployed_cpu._arguments(["--arm", "x", "--seed", "1"])
    assert deployed_cpu._arguments(["--arm", "x", "--seed", "1", "--exploratory"]).seed == 1
    defaults = deployed_cpu._arguments(["--arm", "x"])
    assert (defaults.pairs, defaults.ops, defaults.trial_ops, defaults.seed) == (
        deployed_cpu.PREREGISTERED["pairs"],
        deployed_cpu.PREREGISTERED["ops"],
        deployed_cpu.PREREGISTERED["trial_ops"],
        deployed_cpu.PREREGISTERED["seed"],
    )


def test_cpu_summarize_arms_reports_every_clock_per_op():
    def arm_row(tree_cpu_ns):
        return {
            "ops": 10_000,
            "child_cpu_ns": 1_000_000,
            "parent_cpu_ns": 2_000_000,
            "children_cpu_ns": tree_cpu_ns - 2_000_000,
            "tree_cpu_ns": tree_cpu_ns,
            "parent_wall_ns": 5_000_000,
        }

    rows = [
        {arm: arm_row(120_000_000) for arm in deployed_cpu.deployed.ARMS},
        {arm: arm_row(130_000_000) for arm in deployed_cpu.deployed.ARMS},
    ]
    summary = deployed_cpu.summarize_arms(rows)
    assert set(summary) == set(deployed_cpu.deployed.ARMS)
    assert set(summary["batch"]) == {
        "child_cpu_per_group_op",
        "parent_cpu_per_group_op",
        "children_cpu_per_group_op",
        "tree_cpu_per_group_op",
        "parent_wall_per_group_op",
    }
    assert summary["batch"]["tree_cpu_per_group_op"]["median"] == "0.000012500000"
    assert summary["batch"]["child_cpu_per_group_op"]["median"] == "0.000000100000"


def test_expected_kind_points_match_independent_arithmetic():
    counted = constant_work.counted
    base = (counted.GX, counted.GY)
    assert constant_work.expected_kind_point("kind-add", 3) == counted.ec.mul(counted.P, counted.A, base, 4)
    assert constant_work.expected_kind_point("kind-double", 3) == counted.ec.mul(counted.P, counted.A, base, 8)
    assert constant_work.expected_kind_point("kind-inverse", 3) is None
    assert constant_work.expected_kind_point("kind-torsion", 3) is None
    assert constant_work.expected_kind_point("kind-identity", 3) == base
    assert constant_work.expected_kind_point("kind-adjacent", 3) == (
        (0 - counted.GX - (counted.GX + 1)) % counted.P,
        (-counted.GY) % counted.P,
    )
    assert constant_work.expected_kind_point("counted", 3) == probe.expected_point(3)
    with pytest.raises(probe.ProbeError):
        constant_work.expected_kind_point("kind-bogus", 3)


def test_a_kind_payload_with_a_wrong_count_or_point_is_refused():
    payload = _payload("kind-inverse", 3, 3, None, 5)
    assert constant_work.validate_kind_payload(payload, "kind-inverse", 3, True) == payload
    with pytest.raises(probe.ProbeError, match="count was"):
        constant_work.validate_kind_payload(_payload("kind-inverse", 3, 2, None, 5), "kind-inverse", 3, True)
    with pytest.raises(probe.ProbeError, match="expected infinity"):
        constant_work.validate_kind_payload(_payload("kind-inverse", 3, 3, [1, 2], 5), "kind-inverse", 3, True)
    wrong = [constant_work.counted.GX, constant_work.counted.GY + 1]
    with pytest.raises(probe.ProbeError, match="point was"):
        constant_work.validate_kind_payload(_payload("kind-identity", 3, 3, wrong, 5), "kind-identity", 3, True)


def test_kind_order_is_a_permutation_and_deterministic():
    orders = [constant_work.kind_order(constant_work.PREREGISTERED["seed"], pair) for pair in range(1, 16)]
    for pair, order in enumerate(orders, start=1):
        assert sorted(order) == sorted(constant_work.KINDS)
        assert order == constant_work.kind_order(constant_work.PREREGISTERED["seed"], pair)
    assert len(set(orders)) >= 2


def test_pair_ratios_divide_each_kind_by_the_generic_add():
    results = {kind: {"ops": 10_000, "child_cpu_ns": 4_400_000} for kind in constant_work.KINDS}
    results["kind-add"] = {"ops": 10_000, "child_cpu_ns": 4_000_000}
    results["kind-inverse"] = {"ops": 10_000, "child_cpu_ns": 2_000_000}
    ratios = constant_work.pair_ratios(results)
    assert ratios["kind-inverse"] == "0.500000000"
    assert ratios["kind-double"] == "1.100000000"
    assert "kind-add" not in ratios
    results["kind-add"] = {"ops": 10_000, "child_cpu_ns": 0}
    with pytest.raises(probe.ProbeError):
        constant_work.pair_ratios(results)


def test_verdicts_apply_the_band_and_the_spread_bound():
    summary = {
        "kind-inverse": {"median": "0.899999999", "spread": "0.1"},
        "kind-double": {"median": "0.90", "spread": "0.6"},
    }
    band = constant_work.PREREGISTERED["constant_work_band"]
    bound = constant_work.PREREGISTERED["spread_bound"]
    result = constant_work.verdicts(summary, band, bound)
    assert result["kind-inverse"] == {"constant_work": "cheaper", "spread": "within_bound"}
    assert result["kind-double"] == {"constant_work": "constant_work", "spread": "exceeded"}
    assert constant_work.requirement_holds(result) is False
    summary["kind-inverse"]["median"] = "0.90"
    assert constant_work.requirement_holds(constant_work.verdicts(summary, band, bound)) is False
    summary["kind-double"]["spread"] = "0.50"
    assert constant_work.requirement_holds(constant_work.verdicts(summary, band, bound)) is True


def test_planted_outcome_requires_every_expected_kind_to_be_cheaper():
    def entry(label):
        return {"constant_work": label, "spread": "within_bound"}

    partial = {
        "kind-inverse": entry("cheaper"),
        "kind-identity": entry("cheaper"),
        "kind-torsion": entry("constant_work"),
    }
    outcome = constant_work.planted_outcome("early-return", partial)
    assert outcome["fails_for_the_stated_reason"] is False
    assert outcome["observed_cheaper"] == ["kind-identity", "kind-inverse"]
    full = {**partial, "kind-torsion": entry("cheaper")}
    assert constant_work.planted_outcome("early-return", full)["fails_for_the_stated_reason"] is True
    adjacent = {"kind-adjacent": entry("cheaper"), "kind-inverse": entry("constant_work")}
    assert constant_work.planted_outcome("variable-inversion", adjacent)["fails_for_the_stated_reason"] is True


def test_run_kind_reads_rusage_at_the_reap_hook_and_validates(monkeypatch):
    phase = {"name": "before"}
    readings = {
        "before": {"self_ns": 0, "children_ns": 0},
        "hook": {"self_ns": 7, "children_ns": 13},
        "after": {"self_ns": 99, "children_ns": 99},
    }
    calls = []

    def fake_rusage():
        return readings[phase["name"]]

    def fake_run_binary(binary, mode, ops, timed=False, after_reap=None, validate=True):
        calls.append({"timed": timed, "validate": validate})
        phase["name"] = "hook"
        assert after_reap is not None
        after_reap()
        phase["name"] = "after"
        return _payload("kind-inverse", 3, 3, None, 5), 9

    monkeypatch.setattr(constant_work, "rusage_ns", fake_rusage)
    monkeypatch.setattr(constant_work.counted, "run_binary", fake_run_binary)
    assert constant_work.run_kind("bin", "kind-inverse", 3) == {
        "ops": 3,
        "child_cpu_ns": 5,
        "parent_wall_ns": 9,
        "tree_cpu_ns": 20,
    }
    assert calls == [{"timed": True, "validate": False}]


def test_non_preregistered_constant_work_settings_require_the_exploratory_flag():
    with pytest.raises(SystemExit):
        constant_work._arguments(["--arm", "x", "--pairs", "3"])
    assert constant_work._arguments(["--arm", "x", "--pairs", "3", "--exploratory"]).pairs == 3
    assert constant_work._arguments(["--arm", "x", "--planted", "early-return"]).planted == "early-return"
    with pytest.raises(SystemExit):
        constant_work._arguments(["--arm", "x", "--planted", "bogus"])
    defaults = constant_work._arguments(["--arm", "x"])
    assert (defaults.pairs, defaults.ops, defaults.seed) == (
        constant_work.PREREGISTERED["pairs"],
        constant_work.PREREGISTERED["ops"],
        constant_work.PREREGISTERED["seed"],
    )


def test_build_binary_records_extra_cflags_in_its_metadata(monkeypatch, tmp_path):
    compiler = tmp_path / "clang"
    compiler.touch()
    compile_argv = []

    def fake_compiler(command):
        if command[1:] == ["--version"]:
            return SimpleNamespace(returncode=0, stdout="fake clang 1.0\n", stderr="")
        compile_argv.append(list(command))
        Path(command[command.index("-o") + 1]).write_bytes(b"x")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(probe, "_run_compiler", fake_compiler)
    monkeypatch.setattr(probe.os, "access", lambda path, mode: True)
    build = probe.build_binary(compiler, extra_cflags=("-DCAIRN_EARLY_RETURN",))
    cflags = build["cflags"]
    assert isinstance(cflags, list)
    assert cflags[-1:] == ["-DCAIRN_EARLY_RETURN"]
    assert len(compile_argv) == 1
    argv = compile_argv[0]
    assert argv[argv.index("-Wall") + 1] == "-DCAIRN_EARLY_RETURN"
