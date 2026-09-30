import hashlib
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.grounding import probe_clock_reference_cost
from research.grounding import probe_counted_process as probe
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
