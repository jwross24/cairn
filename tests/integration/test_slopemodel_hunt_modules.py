import hashlib
import json
import subprocess
import sys

import pytest

from cairn.runner import parse_skill_output

BINDING = ("statement_hash", "plan_hash", "run_id", "trial", "point", "seed", "input_blob_hash")
EXECUTOR = "cairn.slopemodel.slope_hunt_executor"
VERIFIER = "cairn.slopemodel.slope_hunt_verifier"


def trial_document(numerator=11, denominator=10):
    return {
        "statement_hash": "a" * 64,
        "plan_hash": "b" * 64,
        "run_id": "slope-protocol",
        "trial": 7,
        "point": {"t": 971152},
        "seed": 12345,
        "input_blob_hash": "c" * 64,
        "predicate": {"kind": "weight_le", "num": numerator, "den": denominator},
    }


def invoke(module, document):
    return subprocess.run(
        [sys.executable, "-m", module],
        input=json.dumps(document).encode(),
        capture_output=True,
        timeout=120,
        check=False,
    )


def parsed_document(result, trial):
    assert result.returncode == 0, result.stderr.decode()
    parsed = parse_skill_output(result.stdout)
    assert parsed.well_formed, parsed.reason
    assert parsed.status == "OK"
    for field in BINDING:
        assert parsed.document[field] == trial[field]
    assert parsed.document["l"] == 971153
    assert parsed.document["n"] == 556
    assert parsed.document["weight"] == 1159387505
    return parsed.document


@pytest.mark.parametrize(("numerator", "denominator", "fails"), [(11, 10, True), (5, 4, False)])
def test_modules_bind_and_recompute_counterexample(numerator, denominator, fails):
    trial = trial_document(numerator, denominator)
    executor = invoke(EXECUTOR, trial)
    produced = parsed_document(executor, trial)
    assert produced["candidate"] is fails
    assert produced["predicate"] == trial["predicate"]
    assert produced["reading"] == "bl2012-two-grumpy-giants/fitted-1"
    assert produced["n_rule"] == "n = (564 * isqrt(l) + 500) // 1000"
    claimed_output = dict(produced, candidate=True)
    digest = hashlib.sha256(json.dumps(claimed_output, sort_keys=True).encode()).hexdigest()
    verifier_trial = dict(trial, executor_output_digest=digest, executor_output=claimed_output)
    verified = parsed_document(invoke(VERIFIER, verifier_trial), trial)
    assert verified["executor_output_digest"] == digest
    assert verified["last_index"] == produced["last_index"]
    assert verified["counterexample_valid"] is fails


@pytest.mark.parametrize("module", [EXECUTOR, VERIFIER])
def test_modules_refuse_nonce(module):
    result = invoke(module, dict(trial_document(), nonce="forbidden", executor_output_digest="d" * 64))
    assert result.returncode != 0
    assert result.stdout == b""
    assert b"must never see the nonce" in result.stderr


@pytest.mark.parametrize("module", [EXECUTOR, VERIFIER])
@pytest.mark.parametrize("t", [2, True, 4194304, 4194305])
def test_modules_refuse_out_of_bound_trial(module, t):
    document = dict(trial_document(), point={"t": t}, executor_output_digest="d" * 64)
    result = invoke(module, document)
    assert result.returncode != 0
    assert result.stdout == b""


def test_verifier_requires_executor_output_digest():
    result = invoke(VERIFIER, dict(trial_document(), point={"t": 3}))
    assert result.returncode != 0
    assert b"executor_output_digest" in result.stderr
