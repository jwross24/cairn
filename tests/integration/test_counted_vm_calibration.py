import importlib.util
import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[2] / "research" / "grounding" / "probe_counted_vm_calibration.py"
spec = importlib.util.spec_from_file_location("probe_counted_vm_calibration", SOURCE)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def test_real_vm_native_and_gp_measurements_cover_each_field_size(tmp_path):
    output = tmp_path / "smoke.json"
    arm = "dev-macos" if sys.platform == "darwin" else "gold-linux-container"
    completed = subprocess.run(
        [
            sys.executable,
            str(SOURCE),
            "--arm",
            arm,
            "--exploratory",
            "--ops",
            "16",
            "--pairs",
            "2",
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text())
    assert report["kind"] == "counted_vm_calibration_exploratory"
    assert report["preregistered"] is False
    assert report["preregistration_sha"] is None
    assert report["status"] == "INCONCLUSIVE"
    assert report["preregistration"]["c_floor_s_per_op"] == "0"
    assert [rung["bits"] for rung in report["rungs"]] == [30, 40, 50, 60]
    for rung in report["rungs"]:
        assert rung["instance"]["p"].bit_length() == rung["bits"]
        assert all(check["rc"] == 0 and check["stderr"] == "" for check in rung["gp_checks"])
        assert set(rung["warmups"]) == set(probe.ARMS)
        assert len(rung["pairs"]) == 2
        assert "aa_radius" in rung["holds"]
        assert "emulation_floor" in rung["holds"]
        for arm_control in rung["startup_controls"].values():
            assert arm_control["counted_ops"] == 0
            assert arm_control["rates"] == {}
        for pair in rung["pairs"]:
            native = pair["measurements"]["native"]
            assert Decimal(native["inner_cpu_s"]) > 0
            assert native["receipt"]["measurement_scope"] == "tree"
            for kind in probe.KINDS:
                measured = pair["measurements"][kind]
                assert measured["setup_counted_ops"] == 0
                assert measured["counted_ops"] == (64 if kind == "scalar_mul" else 16)
                assert measured["receipt"]["outcome"]["status"] == "OK"
                assert measured["receipt"]["measurement_scope"] == "tree"
                assert Decimal(measured["rates"]["seconds_per_op"]) > 0
                assert measured["receipt"]["binary_digest"] == report["build"]["vm_binary_digest"]


def test_rate_mapping_uses_seconds_per_operation_and_reciprocal_throughput():
    assert probe.rate_values("0.000010", 10) == {"seconds_per_op": "0.000001", "ops_per_second": "1E+6"}
    with pytest.raises(ValueError, match="reciprocal"):
        probe.validate_rate({"seconds_per_op": "0.000001", "ops_per_second": "0.000001"})
    with pytest.raises(ValueError, match="units"):
        probe.validate_rate({"rate": "1000000", "cost": "0.000001"})


def test_excess_spread_is_inconclusive_without_a_maximum_rescue():
    exceeded = probe.spread_summary(["1", "1", "2"])
    assert exceeded["status"] == "INCONCLUSIVE"
    assert exceeded["figure"] is None
    assert exceeded["sample_max"] == "2"
    within = probe.spread_summary(["1", "1", "1.1"])
    assert within["status"] == "OBSERVED_WITHIN_SPREAD"
    assert within["figure"] == "1"


def test_confirmatory_run_requires_a_committed_preregistration_before_building(tmp_path):
    output = tmp_path / "confirmatory.json"
    arm = "dev-macos" if sys.platform == "darwin" else "gold-linux-container"
    completed = subprocess.run(
        [
            sys.executable,
            str(SOURCE),
            "--arm",
            arm,
            "--image-digest",
            "sha256:" + "0" * 64,
            "--out",
            str(output),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode != 0
    assert "committed preregistration SHA" in completed.stderr
    assert not output.exists()


def test_preregistration_digest_refuses_different_source_bytes():
    digest = probe.hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    probe.check_preregistration("a" * 40, digest)
    with pytest.raises(ValueError, match="differs"):
        probe.check_preregistration("a" * 40, "0" * 64)
