import copy
import json
from pathlib import Path

import pytest

from cairn import bundle, campaign, claims, env, hunt, substrate


@pytest.fixture
def spec(tmp_path):
    (tmp_path / "executor.py").write_bytes(b"executor bytes")
    (tmp_path / "verifier.py").write_bytes(b"verifier bytes")
    return {
        "family": "euler",
        "method_identity": {"interface_version": "counterexample_hunt/1", "params": {}},
        "module_dir": str(tmp_path),
        "tool_versions": {"python": "3.14"},
        "executor": {
            "module": "executor",
            "sources": ["executor.py"],
            "digest": campaign.source_digest(tmp_path, ["executor.py"]),
            "expected_wall_s": 0.1,
        },
        "verifier": {
            "module": "verifier",
            "sources": ["verifier.py"],
            "digest": campaign.source_digest(tmp_path, ["verifier.py"]),
            "expected_wall_s": 0.1,
        },
        "statements": [
            {
                "role": "question",
                "claim_id": "euler",
                "informal": "n*n+n+41 is prime",
                "scope": {
                    "target_family": "euler",
                    "size_interval": [0, 39],
                    "param_ranges": {"n": [0, 39]},
                    "assumption_set": [],
                },
                "quantities": {"units": {}, "cost_model": None},
                "predicate": {"kind": "prime"},
                "distribution": {"n": [0, 39]},
                "trial_count": 2,
            }
        ],
    }


def _write_spec(tmp_path, spec):
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    return path


@pytest.mark.parametrize(
    "location",
    [
        (),
        ("executor",),
        ("verifier",),
        ("method_identity",),
        ("statements", 0),
        ("statements", 0, "scope"),
        ("statements", 0, "quantities"),
    ],
)
def test_unknown_keys_are_malformed_before_substrate_creation(tmp_path, spec, capsys, location):
    target = spec
    for part in location:
        target = target[part]
    target["unknown"] = True
    path = _write_spec(tmp_path, spec)
    db = tmp_path / "absent.sqlite"
    assert campaign.main(["--spec", str(path), "--db", str(db), "--scratch", str(tmp_path / "runs")]) == 1
    assert not db.exists()
    assert "unknown" in capsys.readouterr().err


@pytest.mark.parametrize("field", ["role", "trial_count", "predicate"])
def test_missing_statement_keys_are_malformed(tmp_path, spec, capsys, field):
    spec["statements"][0].pop(field)
    path = _write_spec(tmp_path, spec)
    db = tmp_path / "absent.sqlite"
    assert campaign.main(["--spec", str(path), "--db", str(db), "--scratch", str(tmp_path / "runs")]) == 1
    assert not db.exists()
    assert field in capsys.readouterr().err


@pytest.mark.parametrize("value", [True, 0, -1, "1", float("inf"), float("nan")])
def test_expected_wall_must_be_finite_positive_number(spec, value):
    spec["executor"]["expected_wall_s"] = value
    with pytest.raises(ValueError, match="finite and positive"):
        campaign.parse_spec(spec)


@pytest.mark.parametrize(
    "sources", [["../executor.py"], ["/executor.py"], ["./executor.py"], ["executor.py", "executor.py"], []]
)
def test_source_paths_are_closed_relative_names(spec, sources):
    spec["executor"]["sources"] = sources
    with pytest.raises(ValueError, match="sources"):
        campaign.parse_spec(spec)


def test_source_digest_frames_path_and_file_boundaries_in_listed_order(tmp_path):
    (tmp_path / "a").write_bytes(b"ab")
    (tmp_path / "b").write_bytes(b"c")
    framed = b"\x00" * 7 + b"\x01a" + b"\x00" * 7 + b"\x02ab" + b"\x00" * 7 + b"\x01b" + b"\x00" * 7 + b"\x01c"
    original = campaign.source_digest(tmp_path, ["a", "b"])
    assert original == substrate.blob_hash(framed)
    assert original != campaign.source_digest(tmp_path, ["b", "a"])
    (tmp_path / "a").write_bytes(b"a")
    (tmp_path / "b").write_bytes(b"bc")
    assert original != campaign.source_digest(tmp_path, ["a", "b"])
    (tmp_path / "c").write_bytes(b"a")
    assert campaign.source_digest(tmp_path, ["a"]) != campaign.source_digest(tmp_path, ["c"])


@pytest.mark.parametrize("producer", ["executor", "verifier"])
def test_plan_only_refuses_modified_source(tmp_path, spec, capsys, producer):
    path = _write_spec(tmp_path, spec)
    source = Path(spec["module_dir"]) / spec[producer]["sources"][0]
    source.write_bytes(source.read_bytes() + b"\n")
    assert campaign.main(["--spec", str(path), "--plan-only"]) == 2
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == f"refused: {producer} digest differs from the spec\n"


def test_plan_only_is_pure_repeatable_and_matches_direct_hunt_hashes(tmp_path, spec, capsys, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("plan-only accessed runtime state")

    monkeypatch.setattr(substrate.Substrate, "open", forbidden)
    monkeypatch.setattr(bundle.GateBundle, "open", forbidden)
    monkeypatch.setattr(env, "manifest", forbidden)
    path = _write_spec(tmp_path, spec)
    db = tmp_path / "absent.sqlite"
    argv = [
        "--spec",
        str(path),
        "--plan-only",
        "--db",
        str(db),
        "--bundle",
        str(tmp_path / "absent.bundle"),
        "--pin",
        str(tmp_path / "absent.pin"),
        "--attest",
        str(tmp_path / "absent.attest"),
    ]
    before = set(tmp_path.iterdir())
    assert campaign.main(argv) == 0
    first = capsys.readouterr()
    assert campaign.main(argv) == 0
    second = capsys.readouterr()
    assert first.out.encode() == second.out.encode()
    assert first.err == second.err == ""
    assert set(tmp_path.iterdir()) == before
    assert not db.exists()
    row = spec["statements"][0]
    statement = claims.ClaimStatement(row["claim_id"], 1, row["informal"], row["scope"], row["quantities"])
    distribution = hunt.Distribution(row["distribution"])
    hypothesis = claims.HypothesisObject(
        spec["family"],
        {"statement_hash": statement.hash, "predicate": claims.to_json(row["predicate"]), "role": row["role"]},
        spec["method_identity"],
        row["distribution"],
        distribution.hash,
        statement.hash,
    )
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        row["trial_count"],
        row["distribution"],
        method_identity=spec["method_identity"],
        target_family=spec["family"],
        executor_identity=spec["executor"]["digest"],
        verifier_identity=spec["verifier"]["digest"],
    )
    report = json.loads(first.out)
    assert report["certification"] == "not_checked"
    assert report["runtime_readiness"] == "not_checked"
    assert report["statements"][0]["statement_hash"] == statement.hash
    assert report["statements"][0]["hypothesis_hash"] == hypothesis.hash
    assert report["statements"][0]["distribution_hash"] == distribution.hash
    assert report["statements"][0]["plan_hash"] == plan.hash
    assert report["executor_identity"] == spec["executor"]["digest"]
    assert report["verifier_identity"] == spec["verifier"]["digest"]
    with pytest.raises(SystemExit) as info:
        campaign.main(["--help"])
    assert info.value.code == 0
    help_output = capsys.readouterr()
    assert "certification and runtime readiness are not checked" in " ".join(help_output.out.split())
    assert help_output.err == ""


def test_hypothesis_binds_distinct_statements(spec):
    duplicate = copy.deepcopy(spec["statements"][0])
    duplicate["claim_id"] = "euler-second"
    spec["statements"].append(duplicate)
    prepared = campaign.prepare_statements(campaign.parse_spec(spec))
    assert prepared[0].hypothesis.hash != prepared[1].hypothesis.hash


def test_multi_axis_uses_unique_scope_size_match(spec):
    row = spec["statements"][0]
    row["distribution"] = {"a": [1, 2], "n": [3, 4]}
    row["scope"]["param_ranges"] = {"a": [1, 2], "n": [0, 39]}
    prepared = campaign.prepare_statements(campaign.parse_spec(spec))
    assert prepared[0].plan.size_axis == "n"
    row["scope"]["param_ranges"]["a"] = [0, 39]
    with pytest.raises(ValueError, match="one scope parameter"):
        campaign.parse_spec(spec)


@pytest.mark.parametrize("argv", [[], ["--unknown"], ["--spec", "not-needed.json"]])
def test_malformed_arguments_exit_one(argv, capsys):
    assert campaign.main(argv) == 1
    assert capsys.readouterr().err.startswith("invalid: ")
