import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import bundle, campaign, canon, env, exits, hunt, keys, repro, selftest, selftest_skills, substrate
from cairn.skills import slope_weight_a, slope_weight_b

SKILLS = (selftest_skills.SLOPE_WEIGHT_A, selftest_skills.SLOPE_WEIGHT_B)
ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def certified_pair(tmp_path_factory):
    root = tmp_path_factory.mktemp("slope-certification")
    bundle_path, pin = root / "bundle.sqlite", root / "bundle.pin"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin)
    db = root / "substrate.sqlite"
    documents = {}
    try:
        for which in SKILLS:
            argv = [
                sys.executable,
                "-m",
                "cairn",
                "selftest",
                which,
                "--db",
                str(db),
                "--bundle",
                str(bundle_path),
                "--pin",
                str(pin),
                "--json",
            ]
            results = [subprocess.run(argv, capture_output=True, text=True, timeout=120) for _ in range(2)]
            assert all(result.returncode == exits.OK for result in results), [result.stderr for result in results]
            first, second = [json.loads(result.stdout) for result in results]
            assert first["recorded"] == "inserted" and second["recorded"] == "present"
            assert first["certificate"] == second["certificate"]
            assert first["double_run"] == second["double_run"] == "byte-equal"
            assert first["pass"] == first["floor"] == 8
            documents[which] = first
            print(json.dumps({"argv": argv, "first": first, "repeat": second}, sort_keys=True))
        yield root, db, bundle_path, pin, documents
    finally:
        if hasattr(os, "chflags"):
            os.chflags(pin, 0)


@pytest.mark.parametrize("which", SKILLS)
def test_cli_certifies_real_pair_and_records_origins(certified_pair, which):
    _, db, _, _, documents = certified_pair
    module = selftest_skills.module_for(which)
    document = documents[which]
    assert document["identity_bundle_hash"] == module.skill_identity_hash()
    assert document["arms"] == {
        "postcondition": "pass",
        "executor": {"candidate": 1, "non_candidate": 2},
        "verifier": {"ok": 1, "fail": 2},
    }
    with substrate.Substrate.open(db, role="reader") as sub:
        row = sub.get_certificate(document["identity_bundle_hash"])
    assert row["cert_hash"] == document["certificate"]
    summary = json.loads(row["selftest_summary"])
    assert summary["must_fail_witnesses"] == 2
    assert summary["cross_check"] == []
    assert summary["corpus_origins"]["printed65537"]["W"] == "upstream_vendored"
    assert summary["corpus_origins"]["agreement65537"]["W"] == "author_supplied"


@pytest.mark.parametrize("which", SKILLS)
def test_transcript_floor_and_certificate_goldens(certified_pair, which):
    _, _, bundle_path, pin, documents = certified_pair
    config = bundle.GateBundle.open(bundle_path, pin).verifier_config()
    first = selftest_skills.run_once(which, config)
    second = selftest_skills.run_once(which, config)
    assert first["transcript"] == second["transcript"]
    assert (len(first["transcript"]), hashlib.sha256(first["transcript"]).hexdigest()) == (
        len(second["transcript"]),
        hashlib.sha256(second["transcript"]).hexdigest(),
    )
    module = selftest_skills.module_for(which)
    identity = module.skill_identity_hash()
    assert (
        selftest.certificate_hash(identity, first["transcript_hash"], keys.env_manifest_digest(env.manifest()))
        == documents[which]["certificate"]
    )
    stem = which.replace("-", "_")
    expected = {
        "selftest_transcript": "\n".join(selftest.transcript_lines(first["records"])) + "\n",
        "floor": json.dumps(
            {"pass": first["passes"], "floor": first["floor"], "arms": first["arms"]}, indent=1, sort_keys=True
        )
        + "\n",
        "certificate": json.dumps(
            {"implementation_revision": module.implementation_revision()}, indent=1, sort_keys=True
        )
        + "\n",
    }
    for suffix, text in expected.items():
        assert (ROOT / "tests" / "goldens" / f"{stem}_{suffix}.golden").read_text() == text


def test_owner_grade_requires_distinct_certified_verifier(certified_pair, tmp_path):
    _, db, _, _, _ = certified_pair
    producer, verifier = slope_weight_a.skill_identity_hash(), slope_weight_b.skill_identity_hash()
    with substrate.Substrate.open(db, role="reader") as sub:
        assert repro.owner_grade(sub, producer, repro.Verifier(repro.SKILL_VERIFIER, verifier)) == (
            repro.VERIFIABLE,
            "certified-independent-verifier-with-must-fail-witness",
        )
        assert repro.owner_grade(sub, producer, repro.Verifier(repro.SKILL_VERIFIER, producer)) == (
            repro.AUDIT_ONLY,
            "verifier-ships-in-producer-revision",
        )
    with substrate.Substrate.open(tmp_path / "uncertified.sqlite") as sub:
        assert repro.owner_grade(sub, producer, repro.Verifier(repro.SKILL_VERIFIER, verifier)) == (
            repro.AUDIT_ONLY,
            "verifier-uncertified",
        )


def test_overlap_mutation_moves_identity_and_has_no_certificate(certified_pair, tmp_path, monkeypatch):
    _, db, _, _, _ = certified_pair
    sources = (*slope_weight_b.IDENTITY_SOURCES, slope_weight_a.IDENTITY_SOURCES[0])
    for relative in sources:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / relative).read_bytes())
    monkeypatch.setattr(slope_weight_b, "IDENTITY_SOURCES", sources)
    changed = slope_weight_b.skill_identity_hash(tmp_path)
    with substrate.Substrate.open(db, role="reader") as sub:
        assert repro.owner_grade(
            sub, slope_weight_a.skill_identity_hash(), repro.Verifier(repro.SKILL_VERIFIER, changed)
        ) == (
            repro.AUDIT_ONLY,
            "verifier-uncertified",
        )


@pytest.mark.parametrize("which", SKILLS)
def test_corpus_weight_byte_mutation_refuses_before_certificate(tmp_path, pinned_bundle, which):
    bundle_path, pin = pinned_bundle()
    path = selftest_skills.CORPUS_PATHS[which]
    original = path.read_bytes()
    assert original.count(b'"value": 20644183') == 1
    mutated = original.replace(b'"value": 20644183', b'"value": 20644184')
    assert len(original) == len(mutated)
    assert sum(left != right for left, right in zip(original, mutated, strict=True)) == 1
    with substrate.Substrate.open(tmp_path / "mutated.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="declares pass"):
            selftest_skills.certify(
                sub, bundle.GateBundle.open(bundle_path, pin).verifier_config(), which, doc=json.loads(mutated)
            )
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


def test_diverging_double_run_refuses(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin = pinned_bundle()
    which = selftest_skills.SLOPE_WEIGHT_B
    real = selftest_skills.RUN_ONCE[which]
    calls = []
    doc = copy.deepcopy(selftest_skills.load_slope_corpus(which))
    doc["cases"] = doc["cases"][:1]
    doc["pass_floor"] = 1

    def diverging(config, *, doc=None, root=None):
        result = real(config, doc=doc, root=root)
        calls.append(1)
        if len(calls) == 2:
            result["transcript"] += b"\x00"
        return result

    monkeypatch.setitem(selftest_skills.RUN_ONCE, which, diverging)
    with substrate.Substrate.open(tmp_path / "diverging.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="double-run"):
            selftest_skills.certify(sub, bundle.GateBundle.open(bundle_path, pin).verifier_config(), which, doc=doc)
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


def test_constant_accept_verifier_fails_without_minting_certificate(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin = pinned_bundle()
    monkeypatch.setattr(slope_weight_b, "check_weight", lambda ell, n, claimed: {"status": "OK"})
    which = selftest_skills.SLOPE_WEIGHT_B
    doc = copy.deepcopy(selftest_skills.load_slope_corpus(which))
    doc["cases"] = doc["cases"][:1]
    doc["pass_floor"] = 1
    with substrate.Substrate.open(tmp_path / "constant-accept.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match=r"planted weight 20644183 at \(65537, 145\) was accepted"):
            selftest_skills.certify(sub, bundle.GateBundle.open(bundle_path, pin).verifier_config(), which, doc=doc)
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


@pytest.mark.parametrize(
    ("role", "kind_only"),
    [("executor", False), ("verifier", False), ("executor", True), ("verifier", True)],
    ids=["executor-global", "verifier-global", "executor-weight-le", "verifier-weight-le"],
)
def test_constant_accept_hunt_decision_on_disk_refuses_cli_certificate(tmp_path, pinned_bundle, role, kind_only):
    bundle_path, pin = pinned_bundle()
    root = tmp_path / "mutated"
    shutil.copytree(ROOT / "src", root / "src", ignore=shutil.ignore_patterns("__pycache__"))
    if role == "verifier":
        relative, signature, value = (
            "src/cairn/slopemodel/slope_hunt_verifier.py",
            "def statement_fails(predicate: dict, ell: int, weight: int) -> bool:\n",
            "True",
        )
        expected = "hunt-verifier-arm: the holding statement returned counterexample_valid=True, expected False"
    else:
        relative, signature, value = (
            "src/cairn/slopemodel/slope_predicates.py",
            "def holds(predicate: dict, ell: int, weight: int) -> bool:\n",
            "True",
        )
        expected = "hunt-executor-arm: the failing statement returned candidate=False, expected True"
    path = root / relative
    original = path.read_text()
    assert original.count(signature) == 1
    if kind_only:
        value = "True" if role == "verifier" else "False"
        mutation = f'    if predicate["kind"] == "weight_le":\n        return {value}\n'
        decision = "counterexample_valid" if role == "verifier" else "candidate"
        expected = f"hunt-{role}-arm: the holding_weight_le statement returned {decision}=True, expected False"
    else:
        mutation = f"    return {value}\n"
    path.write_text(original.replace(signature, signature + mutation))
    db = tmp_path / "refused.sqlite"
    argv = [
        sys.executable,
        "-m",
        "cairn",
        "selftest",
        selftest_skills.SLOPE_WEIGHT_B,
        "--db",
        str(db),
        "--bundle",
        str(bundle_path),
        "--pin",
        str(pin),
        "--json",
    ]
    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "PYTHONPATH": str(root / "src"), "PYTHONSAFEPATH": "1"},
    )
    assert completed.returncode == exits.GATE_REFUSED, completed.stderr
    assert expected in completed.stderr
    assert completed.stdout == ""
    with substrate.Substrate.open(db, role="reader") as sub:
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0
    print(json.dumps({"argv": argv, "source": str(path), "exit": completed.returncode, "stderr": completed.stderr}))


def _campaign_spec():
    spec = {
        "family": "two-grumpy-giants-slope-model",
        "method_identity": {"interface_version": "slope-model/fitted-1", "params": {}},
        "module_dir": str(ROOT / "src"),
        "tool_versions": {"python": sys.version},
        "statements": [],
    }
    for name, which in (("executor", SKILLS[0]), ("verifier", SKILLS[1])):
        module = selftest_skills.module_for(which)
        sources = [str(Path(relative).relative_to("src")) for relative in module.IDENTITY_SOURCES]
        spec[name] = {
            "module": module.HUNT_MODULE,
            "sources": sources,
            "digest": campaign.source_digest(ROOT / "src", sources),
            "expected_wall_s": 1,
            "skill": which,
            "skill_identity_hash": module.skill_identity_hash(),
        }
    for role, predicate in (
        ("control_must_survive", {"kind": "weight_ge_counting_bound"}),
        ("plant_must_be_killed", {"kind": "weight_le", "num": 0, "den": 1}),
        ("question", {"kind": "weight_ge_counting_bound"}),
    ):
        spec["statements"].append(
            {
                "role": role,
                "claim_id": "slope-" + role,
                "informal": "The slope schedule obeys the declared weight bound.",
                "scope": {
                    "target_family": spec["family"],
                    "size_interval": [7, 11],
                    "param_ranges": {"t": [7, 11]},
                    "assumption_set": [],
                },
                "quantities": {"units": {}, "cost_model": None},
                "predicate": predicate,
                "distribution": {"t": [7, 11]},
                "trial_count": 2,
            }
        )
    return spec


def test_real_certified_skills_run_through_campaign_module(certified_pair, tmp_path):
    _, source_db, bundle_path, pin, _ = certified_pair
    db = tmp_path / "campaign.sqlite"
    shutil.copyfile(source_db, db)
    spec = _campaign_spec()
    path = tmp_path / "spec.json"
    path.write_text(json.dumps(spec))
    attest = tmp_path / "attest.log"
    attest.touch()
    argv = [
        sys.executable,
        "-m",
        "cairn.campaign",
        "--spec",
        str(path),
        "--db",
        str(db),
        "--bundle",
        str(bundle_path),
        "--pin",
        str(pin),
        "--attest",
        str(attest),
        "--scratch",
        str(tmp_path / "runs"),
    ]
    completed = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert completed.returncode == exits.OK, completed.stderr
    report = json.loads(completed.stdout)
    assert [row["verdict"] for row in report["statements"]] == ["SURVIVED", "KILLED", "SURVIVED"]
    assert report["executor_identity"] == slope_weight_a.skill_identity_hash()
    assert report["verifier_identity"] == slope_weight_b.skill_identity_hash()
    with substrate.Substrate.open(db, role="reader") as sub:
        for row in report["statements"]:
            record = hunt.record_for(sub, row["run_hash"])
            for trial in record.trials:
                for attempt_id, name in ((trial.attempt_id, "executor"), (trial.verifier_attempt_id, "verifier")):
                    if attempt_id is None:
                        continue
                    attempt = sub.get_attempt(attempt_id)
                    recipe = canon.decode(keys.RECIPE, sub.get_node(attempt["recipe_key"])["canonical"])
                    assert recipe["skill_identity_hash"] == spec[name]["skill_identity_hash"]
    assert report["statements"][0]["derived_tag"] == report["statements"][2]["derived_tag"] == "CONJECTURE"
    print(json.dumps({"argv": argv, "stdout": report, "stderr": completed.stderr}, sort_keys=True))


@pytest.mark.parametrize("mutation", ["wrong_identity", "wrong_module", "missing_source", "unpaired_field"])
def test_certified_spec_cannot_impersonate_skill(mutation):
    spec = _campaign_spec()
    if mutation == "wrong_identity":
        spec["verifier"]["skill_identity_hash"] = "f" * 64
    elif mutation == "wrong_module":
        spec["verifier"]["module"] = "cairn.slopemodel.slope_hunt_executor"
    elif mutation == "missing_source":
        spec["verifier"]["sources"] = spec["verifier"]["sources"][:-1]
        spec["verifier"]["digest"] = campaign.source_digest(spec["module_dir"], spec["verifier"]["sources"])
    else:
        spec["verifier"].pop("skill")
    with pytest.raises((campaign.CampaignRefused, ValueError)):
        campaign.check_digests(campaign.parse_spec(spec))


def test_shadow_package_initializer_outside_installed_root_refuses(tmp_path):
    spec = _campaign_spec()
    source_root = tmp_path / "src"
    shutil.copytree(ROOT / "src", source_root)
    initializer = source_root / "cairn" / "slopemodel" / "__init__.py"
    initializer.write_text("from . import slopemodel_b\nslopemodel_b.weight = lambda ell, n: (0, 0)\n")
    spec["module_dir"] = str(source_root)
    for name in ("executor", "verifier"):
        spec[name]["digest"] = campaign.source_digest(source_root, spec[name]["sources"])
    campaign.parse_spec(spec)
    with pytest.raises(campaign.CampaignRefused, match="installed skill's source root"):
        campaign.check_digests(spec)


def test_registered_skill_launch_ignores_shadow_working_directory(certified_pair, tmp_path, monkeypatch):
    _, source_db, bundle_path, pin, _ = certified_pair
    db = tmp_path / "campaign.sqlite"
    shutil.copyfile(source_db, db)
    source_root = tmp_path / "shadow" / "src"
    shutil.copytree(ROOT / "src", source_root)
    initializer = source_root / "cairn" / "slopemodel" / "__init__.py"
    initializer.write_text("from . import slopemodel_b\nslopemodel_b.weight = lambda ell, n: (0, 0)\n")
    spec = campaign.parse_spec(_campaign_spec())
    monkeypatch.chdir(source_root)
    report, code = campaign.run_campaign(
        spec,
        campaign.prepare_statements(spec),
        db=db,
        bundle_path=bundle_path,
        pin=pin,
        attest=tmp_path / "attest.log",
        scratch=tmp_path / "runs",
    )
    assert code == exits.OK
    assert [row["verdict"] for row in report["statements"]] == ["SURVIVED", "KILLED", "SURVIVED"]
