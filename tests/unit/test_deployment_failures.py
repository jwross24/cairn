import json
from pathlib import Path

import pytest

from cairn import attest, bundle, deployment, substrate

SRC = Path(__file__).resolve().parents[2] / "bundle"


def test_source_hash_change_stops_before_pinning(tmp_path, monkeypatch, capsys):
    src = tmp_path / "source"
    src.mkdir()
    plan_path = src / "gate_plan.json"
    plan_path.write_bytes((SRC / "gate_plan.json").read_bytes())
    original = bundle.build

    def changed_source(source, output):
        plan = json.loads(plan_path.read_text())
        plan["planted_change"] = "different source hash"
        plan_path.write_text(json.dumps(plan))
        return original(source, output)

    monkeypatch.setattr(bundle, "build", changed_source)
    directory = tmp_path / "deployment"
    assert deployment.main(["--src", str(src), "--directory", str(directory)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    refusal = json.loads(output.err.splitlines()[-1])
    assert refusal["stage"] == "build"
    assert "hash differs" in refusal["error"]
    assert refusal["retained"] == [str(directory), str(directory / "gate-bundle.sqlite")]
    assert (directory / "gate-bundle.sqlite").is_file()
    assert not (directory / "gate-bundle.pin").exists()
    assert not (directory / "attestations.log").exists()


@pytest.mark.parametrize("stage", ["pin", "attest"])
def test_append_flag_failure_retains_created_files(tmp_path, monkeypatch, capsys, clear_flags, stage):
    module = bundle if stage == "pin" else attest

    def refuse_flag(path):
        raise PermissionError(f"append-only unavailable for {path}")

    monkeypatch.setattr(module, "_set_append_only", refuse_flag)
    directory = tmp_path / "deployment"
    pin = directory / "gate-bundle.pin"
    attestation = directory / "attestations.log"
    clear_flags(pin)
    clear_flags(attestation)
    assert deployment.main(["--src", str(SRC), "--directory", str(directory)]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    refusal = json.loads(output.err.splitlines()[-1])
    assert refusal["stage"] == stage
    assert "append-only unavailable" in refusal["error"]
    retained = [str(directory), str(directory / "gate-bundle.sqlite"), str(pin)]
    if stage == "attest":
        retained.append(str(attestation))
        gate = bundle.GateBundle.open(directory / "gate-bundle.sqlite", pin)
        assert attest.read_record(attestation, 0) == attest.waiver_canonical(
            attest.fixture_waiver(gate.waiver_target())
        )
    else:
        assert not attestation.exists()
    assert refusal["retained"] == retained
    assert all(Path(path).exists() for path in retained)


def test_wrong_pin_digest_stops_before_attestation(tmp_path, monkeypatch, capsys, clear_flags):
    original = bundle.write_pin
    directory = tmp_path / "deployment"
    clear_flags(directory / "gate-bundle.pin")

    def wrong_pin(bundle_path, pin_path):
        digest = original(bundle_path, pin_path)
        return "0" * len(digest)

    monkeypatch.setattr(bundle, "write_pin", wrong_pin)
    assert deployment.main(["--src", str(SRC), "--directory", str(directory)]) == 2
    output = capsys.readouterr()
    refusal = json.loads(output.err.splitlines()[-1])
    assert output.out == ""
    assert refusal["stage"] == "pin"
    assert "pin hash differs" in refusal["error"]
    assert not (directory / "attestations.log").exists()


def test_preparation_never_opens_a_substrate(tmp_path, monkeypatch, clear_flags):
    def refuse_substrate(*args, **kwargs):
        pytest.fail("deployment opened a substrate")

    monkeypatch.setattr(substrate.Substrate, "open", refuse_substrate)
    directory = tmp_path / "deployment"
    clear_flags(directory / "gate-bundle.pin")
    clear_flags(directory / "attestations.log")
    assert deployment.prepare(SRC, directory)["status"] == "ready"


def test_missing_directory_argument_returns_user_input(capsys):
    assert deployment.main([]) == 1
    output = capsys.readouterr()
    assert output.out == ""
    assert "--directory" in output.err
