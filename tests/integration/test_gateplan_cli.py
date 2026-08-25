import json
import shutil
from pathlib import Path

import pytest

from cairn import attest, bundle, cli, exits

ROOT = Path(__file__).resolve().parents[2]
WEAK_ACCEPT = {"rc": 0, "stdout": None, "stderr_empty": False}


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _source_copy(tmp_path, name, edit):
    directory = tmp_path / f"src-{name}"
    shutil.copytree(ROOT / "bundle", directory)
    edit(directory)
    return directory


@pytest.fixture
def selftest_argv(tmp_path, pinned_bundle, clear_flags):
    def make(name="deploy", src=ROOT / "bundle"):
        bundle_path, pin_path = pinned_bundle(name=name, src=src)
        attest_path = tmp_path / f"{name}.log"
        clear_flags(attest_path)
        attest.init(attest_path, bundle.GateBundle.open(bundle_path, pin_path).waiver_target())
        return [
            "gate",
            "selftest",
            "--db",
            str(tmp_path / f"{name}.sqlite"),
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
            "--attest",
            str(attest_path),
        ]

    return make


def test_a_green_plan_exits_zero_and_names_every_step_with_its_gate_runs_row_id(selftest_argv, capsys):
    code, out, err = _run([*selftest_argv(), "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert out.count("\n") == 1
    assert document["schema_version"] == cli.SCHEMA_VERSION and document["command"] == "gate"
    assert document["ok"] is True
    assert [step["step"] for step in document["steps"]] == [
        "canon_kat",
        "verifier_selftest_pass",
        "verifier_selftest_fail_xP_ne_Q",
        "verifier_selftest_crash",
        "verifier_selftest_crash_control",
        "waiver_cannot_advance",
        "tier_gate_selftest_two_above",
    ]
    assert all(step["result"] == "pass" for step in document["steps"])
    run_ids = [step["run_id"] for step in document["steps"]]
    assert len(set(run_ids)) == len(run_ids) and all(len(r) == 64 for r in run_ids)


def test_the_human_rendering_names_each_step_with_its_expectation(selftest_argv, capsys):
    code, out, err = _run(selftest_argv(), capsys)
    assert code == exits.OK, err
    lines = out.strip().splitlines()
    assert len(lines) == 7
    assert lines[0].startswith("pass canon_kat expected=pass observed=pass run=")
    assert "expected=FAIL backend-crash observed=FAIL backend-crash" in lines[3]


def test_a_plan_missing_a_required_self_test_exits_gate_refused_before_any_step_runs(tmp_path, selftest_argv, capsys):
    def drop(directory):
        path = directory / "gate_plan.json"
        obj = json.loads(path.read_text())
        obj["steps"] = [s for s in obj["steps"] if s["step"] != "verifier_selftest_fail_xP_ne_Q"]
        path.write_text(json.dumps(obj))

    argv = selftest_argv(name="no-xp", src=_source_copy(tmp_path, "no-xp", drop))
    code, out, err = _run(argv, capsys)
    assert code == exits.GATE_REFUSED
    assert "missing-required-selftest:verifier_selftest_fail_xP_ne_Q" in err
    assert "no step ran" in err
    assert out == ""
    assert not (tmp_path / "no-xp.sqlite").exists()


def test_a_failing_step_exits_gate_refused_and_names_a_debug_next_command(tmp_path, selftest_argv, capsys):
    def weaken(directory):
        path = directory / "verifier.json"
        obj = json.loads(path.read_text())
        obj["accept"] = WEAK_ACCEPT
        path.write_text(json.dumps(obj))

    argv = selftest_argv(name="weak", src=_source_copy(tmp_path, "weak", weaken))
    code, out, err = _run([*argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED
    document = json.loads(out)
    assert document["ok"] is False
    assert [step["result"] for step in document["steps"]] == ["pass", "pass", "pass", "fail", "blocked", "blocked", "blocked"]
    assert "verifier_selftest_crash" in err and "every later step is blocked" in err
    assert "cairn gate selftest --json --log DEBUG" in err


def test_a_missing_bundle_exits_environment_with_a_runnable_next_command(selftest_argv, capsys, tmp_path):
    argv = selftest_argv()
    argv[argv.index("--bundle") + 1] = str(tmp_path / "absent.sqlite")
    code, out, err = _run(argv, capsys)
    assert code == exits.ENVIRONMENT
    assert "does not exist" in err and "cairn bundle build" in err


def test_a_missing_attestation_file_exits_environment_and_names_attest_init(selftest_argv, capsys, tmp_path):
    argv = selftest_argv()
    argv[argv.index("--attest") + 1] = str(tmp_path / "absent.log")
    code, out, err = _run(argv, capsys)
    assert code == exits.ENVIRONMENT
    assert "attestation file" in err and "cairn attest init" in err


def test_a_bundle_that_does_not_match_its_pin_exits_gate_refused_with_the_repin_sequence(selftest_argv, capsys, tmp_path):
    argv = selftest_argv()
    stale = tmp_path / "stale.pin"
    stale.write_text("0" * 64 + "\n")
    argv[argv.index("--pin") + 1] = str(stale)
    code, out, err = _run(argv, capsys)
    assert code == exits.GATE_REFUSED
    assert "differs from the pin" in err and "cairn bundle pin" in err
