import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from research.grounding import probe_counted_process as probe


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
