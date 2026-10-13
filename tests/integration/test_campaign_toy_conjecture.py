import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import bundle, campaign, canon, env, hunt, keys, substrate


def make_spec(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "toy_executor.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "assert 'nonce' not in d\n"
        "n = d['point']['n']\n"
        "value = n*n + n + 41\n"
        "candidate = any(value % divisor == 0 for divisor in range(2, value))\n"
        "out = {key: d[key] for key in ('statement_hash', 'plan_hash', 'run_id', 'trial', 'point', 'seed', 'input_blob_hash')}\n"
        "out.update(status='OK', candidate=candidate, value=value, predicate=d['predicate'])\n"
        "print(json.dumps(out, sort_keys=True))\n"
    )
    (root / "toy_verifier.py").write_text(
        "import json, math, sys\n"
        "d = json.load(sys.stdin)\n"
        "assert 'nonce' not in d\n"
        "n = d['point']['n']\n"
        "value = n*n + n + 41\n"
        "valid = any(value % divisor == 0 for divisor in range(2, math.isqrt(value)+1))\n"
        "out = {key: d[key] for key in ('statement_hash', 'plan_hash', 'run_id', 'trial', 'point', 'seed', 'input_blob_hash', 'executor_output_digest')}\n"
        "out.update(status='OK', counterexample_valid=valid and d['predicate'].get('accept', True), value=value)\n"
        "print(json.dumps(out, sort_keys=True))\n"
    )
    statements = []
    for role, bounds in (("question", [40, 40]), ("plant_must_be_killed", [40, 40]), ("control_must_survive", [0, 2])):
        statements.append(
            {
                "role": role,
                "claim_id": "euler-" + role,
                "informal": "n*n+n+41 is prime",
                "scope": {
                    "target_family": "euler",
                    "size_interval": bounds,
                    "param_ranges": {"n": bounds},
                    "assumption_set": [],
                },
                "quantities": {"units": {}, "cost_model": None},
                "predicate": {"kind": "prime"},
                "distribution": {"n": bounds},
                "trial_count": 2,
            }
        )
    return {
        "family": "euler",
        "method_identity": {"interface_version": "counterexample_hunt/1", "params": {}},
        "module_dir": str(root),
        "tool_versions": {"python": sys.version},
        "executor": {
            "module": "toy_executor",
            "sources": ["toy_executor.py"],
            "digest": campaign.source_digest(root, ["toy_executor.py"]),
            "expected_wall_s": 0.1,
        },
        "verifier": {
            "module": "toy_verifier",
            "sources": ["toy_verifier.py"],
            "digest": campaign.source_digest(root, ["toy_verifier.py"]),
            "expected_wall_s": 0.1,
        },
        "statements": statements,
    }


def run_spec(tmp_path, spec, pinned_bundle, *, chronology=False):
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec))
    db = tmp_path / "substrate.sqlite"
    if chronology:
        with substrate.Substrate.open(db) as sub:
            sub.conn.executescript(
                "CREATE TABLE campaign_chronology (seq INTEGER PRIMARY KEY, kind TEXT, hash TEXT);"
                "CREATE TRIGGER campaign_node AFTER INSERT ON nodes BEGIN "
                "INSERT INTO campaign_chronology(kind,hash) VALUES (NEW.kind,NEW.hash); END;"
                "CREATE TRIGGER campaign_nonce AFTER INSERT ON instance_nonces BEGIN "
                "INSERT INTO campaign_chronology(kind,hash) VALUES ('nonce',NEW.hypothesis_key); END;"
            )
    bundle_path, pin = pinned_bundle()
    argv = [
        sys.executable,
        "-m",
        "cairn.campaign",
        "--spec",
        str(spec_path),
        "--db",
        str(db),
        "--bundle",
        str(bundle_path),
        "--pin",
        str(pin),
        "--attest",
        str(tmp_path / "attest.log"),
        "--scratch",
        str(tmp_path / "runs"),
    ]
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return completed, db, bundle.GateBundle.open(bundle_path, pin), argv


def test_toy_campaign_runs_real_trials_and_preregisters_before_entropy(tmp_path, pinned_bundle):
    spec = make_spec(tmp_path / "modules")
    completed, db, gate_bundle, argv = run_spec(tmp_path, spec, pinned_bundle, chronology=True)
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert "stopped" not in report
    assert report["bundle_hash"] == gate_bundle.hash
    assert report["container_digest"] == keys.env_manifest_digest(env.manifest())
    assert report["executor_identity"] == spec["executor"]["digest"]
    assert report["verifier_identity"] == spec["verifier"]["digest"]
    assert [row["role"] for row in report["statements"]] == ["control_must_survive", "plant_must_be_killed", "question"]
    assert [row["verdict"] for row in report["statements"]] == ["SURVIVED", "KILLED", "KILLED"]
    assert [row["expected_verdict"] for row in report["statements"]] == ["SURVIVED", "KILLED", None]
    with substrate.Substrate.open(db) as sub:
        chronology = {
            (row["kind"], row["hash"]): row["seq"] for row in sub.conn.execute("SELECT * FROM campaign_chronology")
        }
        first_nonce = min(seq for (kind, _), seq in chronology.items() if kind == "nonce")
        for row in report["statements"]:
            assert chronology["claim_statement", row["statement_hash"]] < first_nonce
            assert chronology["hypothesis_object", row["hypothesis_hash"]] < first_nonce
            assert chronology["hunt_plan", row["plan_hash"]] < chronology["nonce", row["hypothesis_hash"]]
            assert row["trial_count"] == 2
            record = hunt.record_for(sub, row["run_hash"])
            assert record.verdict == row["verdict"]
            assert row["evidence_hash"] is not None
            assert row["derived_tag"] is not None
            for trial in record.trials:
                for attempt_id in (trial.attempt_id, trial.verifier_attempt_id):
                    if attempt_id is None:
                        continue
                    attempt = sub.get_attempt(attempt_id)
                    recipe_row = sub.get_recipe(attempt["recipe_key"])
                    recipe = canon.decode(keys.RECIPE, sub.get_node(attempt["recipe_key"])["canonical"])
                    assert recipe["container_digest"] == report["container_digest"]
                    assert recipe["tool_versions"] == {"python": substrate.blob_hash(sys.version.encode())}
                    assert recipe["skill_identity_hash"] in (report["executor_identity"], report["verifier_identity"])
                    assert recipe_row["do_not_cache"] == 1
                    assert attempt["skip_cache_lookup"] == 1
                    assert sub.get_receipt(attempt["receipt_hash"])["gate_bundle_hash"] == gate_bundle.hash
        assert sub.conn.execute("SELECT count(*) FROM instance_nonces").fetchone()[0] == 3
    print(json.dumps({"argv": argv, "stdout": report}, sort_keys=True))


@pytest.mark.parametrize(
    ("role", "bounds", "accept", "verdict"),
    [
        ("plant_must_be_killed", [0, 2], True, "SURVIVED"),
        ("control_must_survive", [40, 40], True, "KILLED"),
        ("plant_must_be_killed", [40, 40], False, "INCOMPLETE"),
        ("control_must_survive", [40, 40], False, "INCOMPLETE"),
    ],
)
def test_failed_control_or_plant_stops_before_question_nonce(tmp_path, pinned_bundle, role, bounds, accept, verdict):
    spec = make_spec(tmp_path / "modules")
    statement = next(row for row in spec["statements"] if row["role"] == role)
    statement["scope"]["size_interval"] = bounds
    statement["scope"]["param_ranges"] = {"n": bounds}
    statement["distribution"] = {"n": bounds}
    statement["predicate"]["accept"] = accept
    completed, db, _, _ = run_spec(tmp_path, spec, pinned_bundle)
    assert completed.returncode == 2, completed.stderr
    report = json.loads(completed.stdout)
    assert report["stopped"] == {"role": role, "claim_id": statement["claim_id"], "verdict": verdict}
    assert "refused: " in completed.stderr
    question = campaign.prepare_statements(campaign.parse_spec(spec))[0]
    with sqlite3.connect(db) as conn:
        assert (
            conn.execute(
                "SELECT count(*) FROM instance_nonces WHERE hypothesis_key = ?", (question.hypothesis.hash,)
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT count(*) FROM hypothesis_objects WHERE hash = ?", (question.hypothesis.hash,)
            ).fetchone()[0]
            == 1
        )


@pytest.mark.parametrize("producer", ["executor", "verifier"])
def test_modified_source_refuses_before_attempt(tmp_path, pinned_bundle, producer):
    spec = make_spec(tmp_path / "modules")
    path = Path(spec["module_dir"]) / spec[producer]["sources"][0]
    path.write_bytes(path.read_bytes() + b"\n")
    with substrate.Substrate.open(tmp_path / "substrate.sqlite"):
        pass
    completed, db, _, _ = run_spec(tmp_path, spec, pinned_bundle)
    assert completed.returncode == 2
    assert completed.stderr.strip() == f"refused: {producer} digest differs from the spec"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM instance_nonces").fetchone()[0] == 0


def test_incomplete_question_prints_document_and_refuses(tmp_path, pinned_bundle):
    spec = make_spec(tmp_path / "modules")
    spec["statements"][0]["predicate"]["accept"] = False
    completed, db, _, _ = run_spec(tmp_path, spec, pinned_bundle)
    assert completed.returncode == 2
    report = json.loads(completed.stdout)
    assert report["stopped"] == {"role": "question", "claim_id": "euler-question", "verdict": "INCOMPLETE"}
    assert report["statements"][-1]["verdict"] == "INCOMPLETE"
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT count(*) FROM instance_nonces").fetchone()[0] == 3


@pytest.mark.parametrize("failure", ["bad_pin", "missing_bundle"])
def test_invalid_bundle_refuses_before_substrate_creation(tmp_path, failure):
    spec = make_spec(tmp_path / "modules")
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    bundle_path = tmp_path / "bundle.sqlite"
    if failure == "bad_pin":
        bundle.build(Path(__file__).resolve().parents[2] / "bundle", bundle_path)
    pin = tmp_path / "bundle.pin"
    pin.write_text("0" * 64 + "\n")
    db = tmp_path / "absent.sqlite"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "cairn.campaign",
            "--spec",
            str(path),
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin),
            "--db",
            str(db),
            "--scratch",
            str(tmp_path / "runs"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 2
    assert completed.stderr.startswith("refused: ")
    assert "Traceback" not in completed.stderr
    assert not db.exists()
