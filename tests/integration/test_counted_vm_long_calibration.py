import hashlib
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "research" / "grounding" / "probe_counted_vm_long_calibration.py"
spec = importlib.util.spec_from_file_location("probe_counted_vm_long_calibration", SOURCE)
assert spec is not None and spec.loader is not None
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

ARM = "dev-macos" if sys.platform == "darwin" else "gold-linux-container"
TINY = ["--low-ops", "64", "--high-ops", "128", "--inner", "16", "--pairs", "2"]


class GateOpened(Exception):
    pass


def scratch_dirs():
    return sorted(Path(tempfile.gettempdir()).glob("cairn-vm-long-calibration-*"))


def forbid(*_args, **_kwargs):
    raise AssertionError("work started after the load gate refused")


def test_two_point_difference_cancels_startup_exactly():
    for startup in ("0", "0.0012", "0.0121"):
        low = Decimal(startup) + Decimal("1E-7") * 10_000_000
        high = Decimal(startup) + Decimal("1E-7") * 20_000_000
        figure = probe.two_point_cost(low, high, 10_000_000, 20_000_000)
        assert Decimal(figure["seconds_per_op"]) == Decimal("1E-7")
        assert Decimal(figure["startup_cpu_s"]) == Decimal(startup)
        assert abs(Decimal(figure["seconds_per_op"]) * Decimal(figure["ops_per_second"]) - 1) < Decimal("1e-24")


@pytest.mark.parametrize(
    ("cpu_low", "cpu_high", "ops_low", "ops_high"),
    [
        ("1.5", "1.5", 100, 200),
        ("2.0", "1.0", 100, 200),
        ("1.0", "2.0", 200, 200),
        ("1.0", "2.0", 300, 200),
        ("1.0", "2.0", 0, 200),
        ("1.0", "2.0", 100.0, 200),
    ],
)
def test_two_point_difference_refuses_a_non_positive_or_ill_posed_pair(cpu_low, cpu_high, ops_low, ops_high):
    with pytest.raises(ValueError, match=r"not positive|two distinct positive"):
        probe.two_point_cost(cpu_low, cpu_high, ops_low, ops_high)


@pytest.mark.parametrize(
    ("readings", "admitted"),
    [
        ([("local", (0.0, 0.0, 0.0))], True),
        ([("local", (1.99, 9.0, 9.0))], True),
        ([("local", (2.0, 0.0, 0.0))], False),
        ([("local", (9.16, 9.84, 10.54))], False),
        ([("local", (0.1, 0.1, 0.1)), ("host", (3.0, 0.1, 0.1))], False),
        ([("local", (0.1, 0.1, 0.1)), ("host", (0.5, 0.1, 0.1))], True),
    ],
)
def test_load_gate_admits_only_a_one_minute_average_strictly_below_two(readings, admitted):
    gate = probe.load_gate(readings)
    assert gate["admitted"] is admitted
    assert gate["limit"] == "2"
    assert [record["source"] for record in gate["readings"]] == [label for label, _ in readings]


def test_a_loaded_host_refuses_before_any_work_and_consumes_nothing(tmp_path, monkeypatch, capsys):
    out = tmp_path / "report.json"
    monkeypatch.setattr(probe.prior, "build_binaries", forbid)
    monkeypatch.setattr(probe.toy_curve, "run", forbid)
    monkeypatch.setattr(probe, "plan_inputs", forbid)
    before = scratch_dirs()
    code = probe.main(["--arm", ARM, "--exploratory", "--out", str(out), *TINY], load_reader=lambda: (2.5, 1.0, 0.5))
    assert code == probe.EXIT_LOAD_REFUSED
    record = json.loads(capsys.readouterr().out)
    assert record["kind"] == "counted_vm_long_calibration_refusal"
    assert record["run_consumed"] is False
    assert record["reason"] == "host_load_not_below_limit"
    assert record["gate"]["readings"][0]["load_1m"] == "2.5"
    assert json.loads(out.read_text()) == record
    assert scratch_dirs() == before


def test_the_same_invocation_passes_the_gate_when_the_host_is_idle(tmp_path, monkeypatch):
    def gate_opened():
        raise GateOpened

    monkeypatch.setattr(probe, "plan_inputs", gate_opened)
    with pytest.raises(GateOpened):
        probe.main(
            ["--arm", ARM, "--exploratory", "--out", str(tmp_path / "r.json"), *TINY],
            load_reader=lambda: (0.5, 1.0, 1.0),
        )


def test_the_confirmatory_run_refuses_the_container_arm(tmp_path):
    output = tmp_path / "container.json"
    completed = subprocess.run(
        [sys.executable, str(SOURCE), "--arm", "gold-linux-container", "--out", str(output)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode != 0
    assert "dev-macos arm only" in completed.stderr
    assert not output.exists()


def synthetic(native=("1E-7",) * 4, vm=None, warmup_load="0.5", load="0.5", pairs=15):
    vm = vm or {}
    rungs = []
    for index, bits in enumerate(probe.PREREGISTERED["bits"]):

        def stamp(level):
            return {"load_before": [level] * 3, "load_after": [level] * 3}

        rows = []
        for pair in range(pairs):
            costs = {"native": {"seconds_per_op": native[index]}}
            for kind in probe.KINDS:
                value = vm.get((index, kind), "1.5E-7")
                value = value[pair % len(value)] if isinstance(value, list) else value
                costs[kind] = value if isinstance(value, dict) else {"seconds_per_op": value}
            rows.append(
                {"costs": costs, "samples": {arm: {"low": stamp(load), "high": stamp(load)} for arm in probe.ARMS}}
            )
        rungs.append({"bits": bits, "warmups": {arm: stamp(warmup_load) for arm in probe.ARMS}, "pairs": rows})
    return rungs


def test_rate_ratio_divides_the_largest_vm_median_by_the_smallest_native_median():
    native = ("2E-7", "1E-7", "3E-7", "4E-7")
    result = probe.rate_ratio_candidate(synthetic(native=native, vm={(3, "double"): "2.2E-7"}))
    assert Decimal(result["reference_cost_s_per_group_op"]) == Decimal("1E-7")
    assert Decimal(result["slowest_vm_cost_s_per_op"]) == Decimal("2.2E-7")
    assert Decimal(result["unrounded_ratio"]) == Decimal("2.2")
    assert Decimal(result["candidate"]) == Decimal("2.2")
    assert result["plan_inequality_holds"] is True


def test_rate_ratio_rounds_up_then_applies_the_plan_inequality():
    for slowest, candidate, holds in (
        ("2.4321E-7", "2.44", False),
        ("2.43E-7", "2.43", True),
        ("2.1301E-7", "2.14", True),
    ):
        result = probe.rate_ratio_candidate(synthetic(vm={(0, "add"): slowest}))
        assert (result["candidate"], result["plan_inequality_holds"]) == (candidate, holds)


def test_the_unrounded_ratio_decides_the_below_one_refusal():
    result = probe.rate_ratio_candidate(synthetic(vm={(i, k): "0.9999E-7" for i in range(4) for k in probe.KINDS}))
    assert Decimal(result["unrounded_ratio"]) == Decimal("0.9999")
    assert result["candidate"] is None
    assert result["plan_inequality_holds"] is False


def test_status_is_recomputed_from_the_cells_and_a_caller_status_is_refused():
    with pytest.raises(TypeError):
        probe.rate_ratio_candidate(synthetic(), "WITHIN_BOUND")
    assert probe.classify(synthetic()) == ("WITHIN_BOUND", True)
    wide = {(1, "chain"): ["1E-7", "3E-7"]}
    assert probe.classify(synthetic(vm=wide)) == ("EXCEEDED_ON_IDLE_HOST", True)
    assert probe.rate_ratio_candidate(synthetic(vm=wide))["candidate"] is None


def test_warmup_load_makes_the_run_not_clean():
    assert probe.classify(synthetic(warmup_load="2.5")) == ("LOAD_NOT_CLEAN", False)
    assert probe.classify(synthetic(load="2.0")) == ("LOAD_NOT_CLEAN", False)
    assert probe.rate_ratio_candidate(synthetic(warmup_load="2.5"))["candidate"] is None


def test_an_invalid_pair_is_its_own_status_unless_a_valid_cell_exceeded():
    invalid = {(0, "chain"): [{"invalid": "two-point difference is not positive"}] + ["1.5E-7"] * 14}
    assert probe.classify(synthetic(vm=invalid)) == ("INVALID_SAMPLE", True)
    assert probe.rate_ratio_candidate(synthetic(vm=invalid))["candidate"] is None
    both = {**invalid, (2, "add"): ["1E-7", "3E-7"]}
    assert probe.classify(synthetic(vm=both)) == ("EXCEEDED_ON_IDLE_HOST", True)


def test_the_conversion_refuses_a_subset_of_rungs_or_kinds():
    whole = synthetic()
    with pytest.raises(ValueError, match="every preregistered rung"):
        probe.rate_ratio_candidate(whole[:1])
    with pytest.raises(ValueError, match="every preregistered rung"):
        probe.classify(whole[::-1])
    for row in whole[0]["pairs"]:
        del row["costs"]["chain"]
    with pytest.raises(ValueError, match="six kinds"):
        probe.rate_ratio_candidate(whole)
    whole[1]["pairs"] = []
    with pytest.raises(ValueError, match="six kinds"):
        probe.classify(whole)


def test_the_bound_is_zero_point_five_and_unchanged_from_the_earlier_preregistration():
    assert probe.PREREGISTERED["spread_bound"] == "0.50"
    assert Decimal("0.50") == probe.SPREAD_BOUND
    assert probe.PREREGISTERED["spread_bound"] == probe.prior.PREREGISTERED["spread_bound"]
    assert probe.PREREGISTERED["load_limit"] == "2"
    assert "0.50" in (ROOT / "research/grounding/counted-vm-long-calibration-preregistration.md").read_text()


def test_the_bound_decides_at_its_edge_and_never_rescues_an_excess():
    assert probe.spread_summary(["1", "1", "1.5"])["status"] == "OBSERVED_WITHIN_SPREAD"
    for sample in (["1", "1", "1.51"], ["1", "1", "1.55"], ["1", "1", "2"]):
        exceeded = probe.spread_summary(sample)
        assert exceeded["status"] == "INCONCLUSIVE"
        assert exceeded["figure"] is None
    invalid = probe.spread_summary(["1", None, "1"])
    assert invalid["status"] == "INCONCLUSIVE"
    assert invalid["figure"] is None


def test_samples_reach_ten_million_operations_inside_the_vm_limits():
    vm_source = (ROOT / "src/cairn/countedvm/vm.c").read_text()
    assert f"#define MAX_INDEX {probe.MAX_INDEX}\n" in vm_source
    pre = probe.PREREGISTERED
    assert pre["low_ops"] >= 10**7
    assert pre["high_ops"] > pre["low_ops"]
    bounds = probe.fixed_bounds(
        pre["bits"], pre["low_ops"], pre["high_ops"], pre["inner_iterations"], pre["instruction_budget"]
    )
    assert max(bounds["expected_executed"].values()) < pre["instruction_budget"]
    for kind in probe.KINDS:
        for ops in (pre["low_ops"], pre["high_ops"]):
            iterations = ops // probe.OPS_PER_ITERATION[kind]
            assert iterations * probe.OPS_PER_ITERATION[kind] == ops
            text = probe.program(kind, ops, pre["inner_iterations"])
            outer = int(re.findall(r"iset i1 (\d+)", text)[0])
            assert outer * pre["inner_iterations"] == iterations
            assert max(outer, pre["inner_iterations"]) <= probe.MAX_INDEX


def test_a_program_is_blind_to_the_curve_and_refuses_a_loop_that_does_not_fill():
    text = probe.program("add", 64, 16)
    assert re.search(r"\d{4,}", text) is None
    with pytest.raises(ValueError, match="whole iterations"):
        probe.program("add", 65, 16)
    with pytest.raises(ValueError, match="whole iterations"):
        probe.program("add", 64, probe.MAX_INDEX + 1)
    with pytest.raises(ValueError, match="whole iterations"):
        probe.program("scalar_mul", 10, 1)
    with pytest.raises(ValueError, match="budget"):
        probe.fixed_bounds([30], 64, 128, 16, 100)


def test_the_rung_sizes_and_baseline_come_from_the_plan(tmp_path):
    assert probe.plan_inputs() == probe.PREREGISTERED["bits"]
    plan = json.loads(probe.PLAN.read_text())
    plan["rungs"][0]["bits"] = 31
    mismatched = tmp_path / "bits.json"
    mismatched.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="rung sizes"):
        probe.plan_inputs(mismatched)
    plan["rungs"][0]["bits"] = 30
    plan["baseline"]["method_identity"]["params"]["variant"] = "negation"
    other = tmp_path / "variant.json"
    other.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="plain"):
        probe.plan_inputs(other)


def test_a_mismatched_plan_refuses_before_any_curve_is_drawn(tmp_path, monkeypatch):
    plan = json.loads(probe.PLAN.read_text())
    plan["rungs"][1]["bits"] = 41
    mismatched = tmp_path / "plan.json"
    mismatched.write_text(json.dumps(plan))
    monkeypatch.setattr(probe, "PLAN", mismatched)
    monkeypatch.setattr(probe.toy_curve, "run", forbid)
    monkeypatch.setattr(probe.prior, "build_binaries", forbid)
    with pytest.raises(ValueError, match="rung sizes"):
        probe.main(
            ["--arm", ARM, "--exploratory", "--out", str(tmp_path / "r.json"), *TINY],
            load_reader=lambda: (0.0, 0.0, 0.0),
        )


def test_preregistration_digests_refuse_different_source_or_document_bytes():
    source = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = hashlib.sha256(probe.DOCUMENT.read_bytes()).hexdigest()
    probe.check_preregistration("a" * 40, source, document)
    with pytest.raises(ValueError, match="source differs"):
        probe.check_preregistration("a" * 40, "0" * 64, document)
    with pytest.raises(ValueError, match="document differs"):
        probe.check_preregistration("a" * 40, source, "0" * 64)
    with pytest.raises(ValueError, match="document SHA256"):
        probe.check_preregistration("a" * 40, source, None)


def run_probe(*args):
    return subprocess.run(
        [sys.executable, str(SOURCE), "--arm", ARM, *args], capture_output=True, text=True, timeout=120, check=False
    )


def test_confirmatory_run_refuses_unbound_or_injected_invocations_before_building(tmp_path):
    output = tmp_path / "confirmatory.json"
    unbound = run_probe("--out", str(output))
    assert unbound.returncode != 0
    assert "committed preregistration SHA" in unbound.stderr
    injected = run_probe("--injected-load", "0,0,0", "--out", str(output))
    assert injected.returncode != 0
    assert "exploratory only" in injected.stderr
    shrunk = run_probe("--pairs", "2", "--out", str(output))
    assert shrunk.returncode != 0
    assert "must match preregistration" in shrunk.stderr
    assert not output.exists()


def test_tiny_end_to_end_run_records_load_beside_every_figure(tmp_path):
    output = tmp_path / "tiny.json"
    completed = run_probe("--exploratory", "--injected-load", "0.5,0.5,0.5", "--out", str(output), *TINY)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(output.read_text())
    assert report["kind"] == "counted_vm_long_calibration_exploratory"
    assert report["preregistered"] is False
    assert report["run_consumed"] is False
    assert report["rate_ratio"] == {"candidate": None, "reason": "exploratory run"}
    assert report["load_gate"]["admitted"] is True
    assert report["load_clean_throughout"] is True
    assert report["bounds_fixed_before_any_curve"]["bits"] == [30, 40, 50, 60]
    assert report["preregistration"]["spread_bound"] == "0.50"
    assert [rung["bits"] for rung in report["rungs"]] == [30, 40, 50, 60]
    for rung in report["rungs"]:
        assert rung["instance"]["p"].bit_length() == rung["bits"]
        assert all(check["rc"] == 0 and check["stderr"] == "" for check in rung["gp_checks"])
        assert set(rung["kind_ratio_summaries"]) == set(probe.KINDS)
        assert len(rung["pairs"]) == 2
        for row in rung["pairs"]:
            assert set(row["samples"]) == set(probe.ARMS)
            for arm, points in row["samples"].items():
                assert [points[key]["counted_ops"] for key in ("low", "high")] == [64, 128]
                for sample in points.values():
                    assert sample["load_before"] == ["0.5", "0.5", "0.5"]
                    assert sample["load_after"] == ["0.5", "0.5", "0.5"]
                    assert Decimal(sample["cpu_s"]) > 0
                    assert sample["receipt"]["measurement_scope"] == "tree"
                    if arm != "native":
                        assert sample["receipt"]["outcome"]["status"] == "OK"
                        assert sample["receipt"]["outcome"]["count"] == sample["counted_ops"]
