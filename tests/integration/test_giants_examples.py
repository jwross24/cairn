import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import campaign, exits, substrate

ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = ROOT / "examples" / "giants"
COMMITMENTS = [
    (
        1,
        "5bd97919d12c57a3829239b6e07f16110dc32c138441348bda1b1d6b23185baa",
        "23ef0bc66ba7eb12646ec3e3801ca685df12322a8d31129646419c42a546c65b",
        198,
    ),
    (
        2,
        "50d2e4ba988aeab5341b945830fc545c2ac24230123e8fc815909800ab118053",
        "9f102f442874362457268e8a973b03ca437db9ee08a5446b063ea5e01430f60a",
        115,
    ),
    (
        3,
        "2741a5894dc794443f21272c83b6a91d3f1598a11ab0b89cd98ad3656cdba1e3",
        "533f3a0e34141d7187025d0aafb4ab9ba5dd2c809fff8d31b91b60e03b612673",
        52,
    ),
]


def _json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _environment(python_path):
    return {
        **os.environ,
        "PYTHONPATH": str(python_path),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    }


def _plan(spec_path, tmp_path):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "cairn.campaign",
            "--spec",
            str(spec_path),
            "--plan-only",
            "--db",
            str(tmp_path / "substrate.sqlite"),
            "--bundle",
            str(tmp_path / "bundle.sqlite"),
            "--pin",
            str(tmp_path / "bundle.pin"),
            "--attest",
            str(tmp_path / "attestations.log"),
        ],
        cwd=ROOT,
        env=_environment(ROOT / "src"),
        capture_output=True,
        text=True,
        timeout=20,
    )


@pytest.mark.parametrize(("number", "spec_digest", "plan_digest", "trial_ceiling"), COMMITMENTS)
def test_frozen_campaign_plan_commitments_are_portable_and_read_only(
    tmp_path, number, spec_digest, plan_digest, trial_ceiling
):
    spec_path = Path("examples/giants") / f"campaign{number}.json"
    spec = json.loads((ROOT / spec_path).read_text())
    assert _json_digest(spec) == spec_digest
    assert spec["module_dir"] == "examples/giants/modules"
    assert sum(row["trial_count"] for row in spec["statements"]) == trial_ceiling
    completed = _plan(spec_path, tmp_path)
    assert completed.returncode == exits.OK, completed.stderr
    report = json.loads(completed.stdout)
    assert report.pop("certification") == "not_checked"
    assert report.pop("runtime_readiness") == "not_checked"
    assert _json_digest(report) == plan_digest
    for name in ("executor", "verifier"):
        program = spec[name]
        assert program["expected_wall_s"] == 120.0
        assert campaign.source_digest(ROOT / spec["module_dir"], program["sources"]) == program["digest"]
        assert report[f"{name}_identity"] == program["digest"]
    repeated = _plan(spec_path, tmp_path)
    assert repeated.returncode == exits.OK, repeated.stderr
    assert repeated.stdout == completed.stdout
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("number", [1, 2, 3])
@pytest.mark.parametrize("program_name", ["executor", "verifier"])
def test_corrupted_frozen_module_refuses_plan_only(tmp_path, number, program_name):
    modules = tmp_path / "modules"
    shutil.copytree(EXAMPLES / "modules", modules)
    spec = json.loads((EXAMPLES / f"campaign{number}.json").read_text())
    spec["module_dir"] = str(modules)
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    untouched = _plan(spec_path, tmp_path)
    assert untouched.returncode == exits.OK, untouched.stderr
    module = modules / spec[program_name]["sources"][0]
    module.write_bytes(module.read_bytes() + b"\n")
    refused = _plan(spec_path, tmp_path)
    assert refused.returncode == exits.GATE_REFUSED
    assert refused.stdout == ""
    assert refused.stderr == f"refused: {program_name} digest differs from the spec\n"
    assert not (tmp_path / "substrate.sqlite").exists()


@pytest.mark.parametrize(("number", "statement_index"), [(1, 0), (1, 1), (2, 1), (2, 2), (3, 1), (3, 2), (3, 3)])
def test_frozen_adapters_run_from_an_isolated_working_directory(tmp_path, number, statement_index):
    spec = json.loads((EXAMPLES / f"campaign{number}.json").read_text())
    prepared = campaign.prepare_statements(spec)[statement_index]
    document = {
        "statement_hash": prepared.statement.hash,
        "plan_hash": prepared.plan.hash,
        "run_id": "adapter-wiring",
        "trial": 0,
        "point": {"t": 1009},
        "seed": "c" * 64,
        "input_blob_hash": "d" * 64,
        "predicate": prepared.spec["predicate"],
    }
    outputs = []
    for name in ("executor", "verifier"):
        completed = subprocess.run(
            [sys.executable, "-m", spec[name]["module"]],
            cwd=tmp_path,
            env=_environment(EXAMPLES / "modules"),
            input=json.dumps(document),
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert completed.returncode == exits.OK, completed.stderr
        output = json.loads(completed.stdout)
        assert output["status"] == "OK"
        for binding in ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash"):
            assert output[binding] == document[binding]
        if name == "executor":
            assert output["predicate"] == document["predicate"]
            document["executor_output_digest"] = substrate.blob_hash(completed.stdout.encode())
        else:
            assert output["executor_output_digest"] == document["executor_output_digest"]
        outputs.append(output)
    for field in ("l", "n", "weight", "last_index"):
        assert type(outputs[0][field]) is int
        assert outputs[0][field] == outputs[1][field]
    assert outputs[0]["l"] == 1009
    assert outputs[0]["candidate"] == outputs[1]["counterexample_valid"]
    if document["predicate"]["kind"] == "weight_within_formula":
        assert outputs[1]["comparison"] == "exact-rational"
        assert type(outputs[1]["prediction_numerator"]) is int
        assert type(outputs[1]["prediction_denominator"]) is int
    assert not list(tmp_path.iterdir())
