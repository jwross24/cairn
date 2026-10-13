import copy
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import campaign, selftest, selftest_skills
from cairn.skills import slope_weight_a, slope_weight_b

SKILLS = (selftest_skills.SLOPE_WEIGHT_A, selftest_skills.SLOPE_WEIGHT_B)
AGREEMENT_PRIMES = {65537, 131101, 300007, 1048583, 2097169, 4194301}


@pytest.mark.parametrize("which", SKILLS)
def test_published_rows_and_author_supplied_agreement_primes(which):
    doc = selftest_skills.load_slope_corpus(which)
    assert doc["pass_floor"] == len(doc["cases"]) == 8
    printed, agreement = [], set()
    for case in doc["cases"]:
        fields = case["fields"]
        assert "page 15" in case["source"]
        assert "https://cr.yp.to/elliptic/grumpy-20120709.pdf" in case["source"]
        if case["id"].startswith("printed"):
            assert {field["origin"] for field in fields.values()} == {"upstream_vendored"}
            printed.append(tuple(fields[name]["value"] for name in ("l", "n", "W")))
        else:
            assert {field["origin"] for field in fields.values()} == {"author_supplied"}
            agreement.add(fields["l"]["value"])
    assert printed == [(65537, 146, 20644183), (1000003, 558, 1205458963)]
    assert agreement == AGREEMENT_PRIMES


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("schema_version",), True),
        (("schema_version",), 2),
        (("pass_floor",), 9),
        (("pass_floor",), True),
        (("cases",), []),
        (("cases", 0, "fields", "W", "value"), True),
        (("cases", 0, "fields", "W", "value"), -1),
        (("cases", 0, "fields", "n", "value"), 65537),
        (("cases", 0, "fields", "l", "value"), 2),
        (("cases", 0, "fields", "W", "origin"), "invented"),
        (("cases", 0, "ledger"), "invented"),
        (("cases", 0, "source"), ""),
        (("cases", 1, "id"), "printed65537"),
    ],
)
def test_malformed_corpus_refuses(path, value):
    doc = copy.deepcopy(selftest_skills.load_slope_corpus(SKILLS[0]))
    target = doc
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value
    with pytest.raises(selftest.CorpusSchemaError):
        selftest_skills.check_slope_corpus(doc)


@pytest.mark.parametrize("location", [(), ("cases", 0), ("cases", 0, "fields"), ("cases", 0, "fields", "W")])
def test_unknown_corpus_fields_refuse(location):
    doc = copy.deepcopy(selftest_skills.load_slope_corpus(SKILLS[0]))
    target = doc
    for part in location:
        target = target[part]
    target["unknown"] = 1
    with pytest.raises(selftest.CorpusSchemaError):
        selftest_skills.check_slope_corpus(doc)


def test_invalid_json_corpus_refuses(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text("{")
    with pytest.raises(selftest.CorpusSchemaError, match="not valid JSON"):
        selftest_skills.load_slope_corpus(SKILLS[0], path)


def test_identity_sources_share_only_initializers_and_new_sources_move_the_revision(tmp_path, monkeypatch):
    initializers = {"src/cairn/__init__.py", "src/cairn/slopemodel/__init__.py"}
    assert set(slope_weight_a.IDENTITY_SOURCES) & set(slope_weight_b.IDENTITY_SOURCES) == initializers
    assert slope_weight_a.skill_identity_hash() != slope_weight_b.skill_identity_hash()
    before = slope_weight_b.implementation_revision()
    for relative in slope_weight_b.IDENTITY_SOURCES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((slope_weight_b.REPO_ROOT / relative).read_bytes())
    shared = slope_weight_a.IDENTITY_SOURCES[0]
    path = tmp_path / shared
    path.write_bytes((slope_weight_a.REPO_ROOT / shared).read_bytes())
    monkeypatch.setattr(slope_weight_b, "IDENTITY_SOURCES", (*slope_weight_b.IDENTITY_SOURCES, shared))
    assert set(slope_weight_a.IDENTITY_SOURCES) & set(slope_weight_b.IDENTITY_SOURCES) == initializers | {shared}
    assert slope_weight_b.implementation_revision(tmp_path) != before


@pytest.mark.parametrize("module", [slope_weight_a, slope_weight_b])
def test_launched_hunt_module_repo_imports_are_identity_sources(module, tmp_path):
    document = {
        "statement_hash": "a" * 64,
        "plan_hash": "b" * 64,
        "run_id": "identity-closure",
        "trial": 0,
        "point": {"t": 7},
        "seed": 1,
        "input_blob_hash": "c" * 64,
        "predicate": {"kind": "weight_le", "num": 10, "den": 1},
        "executor_output_digest": "d" * 64,
    }
    probe = """
import json
import runpy
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
launched = runpy.run_module(sys.argv[2], run_name="__main__")
files = {Path(launched["__file__"]).resolve()}
files.update(
    Path(module.__file__).resolve()
    for module in tuple(sys.modules.values())
    if getattr(module, "__file__", None)
    and Path(module.__file__).resolve().is_relative_to(root / "src")
)
print(json.dumps(sorted(str(path.relative_to(root)) for path in files)))
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-P", "-c", probe, str(module.REPO_ROOT), module.HUNT_MODULE],
        input=json.dumps(document),
        capture_output=True,
        text=True,
        timeout=60,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(module.REPO_ROOT / "src")},
    )
    assert completed.returncode == 0, completed.stderr
    output, loaded = completed.stdout.splitlines()
    assert json.loads(output)["status"] == "OK"
    paths = set(json.loads(loaded))
    assert paths
    assert "src/" + module.HUNT_MODULE.replace(".", "/") + ".py" in paths
    assert paths <= set(module.IDENTITY_SOURCES), sorted(paths - set(module.IDENTITY_SOURCES))


@pytest.mark.parametrize("initializer", ["src/cairn/__init__.py", "src/cairn/slopemodel/__init__.py"])
def test_initializer_mutation_moves_both_identities_and_refuses_old_spec(tmp_path, monkeypatch, initializer):
    for relative in set(slope_weight_a.IDENTITY_SOURCES) | set(slope_weight_b.IDENTITY_SOURCES):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((slope_weight_a.REPO_ROOT / relative).read_bytes())
    spec = {"module_dir": str(tmp_path / "src")}
    programs = {}
    for name, which in (("executor", SKILLS[0]), ("verifier", SKILLS[1])):
        module = selftest_skills.module_for(which)
        sources = [str(Path(relative).relative_to("src")) for relative in module.IDENTITY_SOURCES]
        programs[name] = {
            "module": module.HUNT_MODULE,
            "sources": sources,
            "digest": campaign.source_digest(spec["module_dir"], sources),
            "skill": which,
            "skill_identity_hash": module.skill_identity_hash(tmp_path),
        }
        spec[name] = programs[name]
        monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    campaign.check_digests(spec)
    (tmp_path / initializer).write_text("IDENTITY_PLANT = True\n")
    for name, which in (("executor", SKILLS[0]), ("verifier", SKILLS[1])):
        module = selftest_skills.module_for(which)
        program = programs[name]
        assert module.skill_identity_hash(tmp_path) != program["skill_identity_hash"]
        program["digest"] = campaign.source_digest(spec["module_dir"], program["sources"])
    with pytest.raises(campaign.CampaignRefused, match="executor skill identity differs from the spec"):
        campaign.check_digests(spec)


@pytest.mark.parametrize("module", [slope_weight_a, slope_weight_b])
def test_skill_summary_declares_no_cross_check(module):
    assert selftest.cross_check_summary(module) == []


@pytest.mark.parametrize("module", [slope_weight_a, slope_weight_b])
def test_skill_json_entry_point_and_bad_inputs(module):
    output = io.StringIO()
    assert module.main(io.StringIO('{"l":7,"n":2}'), output, io.StringIO()) == 0
    assert json.loads(output.getvalue()) == module.run(7, 2)
    for document in ("[]", '{"l":9,"n":2}', '{"l":7,"n":2,"unknown":1}'):
        output, error = io.StringIO(), io.StringIO()
        assert module.main(io.StringIO(document), output, error) == 1
        assert output.getvalue() == ""
        assert error.getvalue().startswith("error:")


def test_verifier_entry_point_refuses_wrong_weight():
    output, error = io.StringIO(), io.StringIO()
    assert slope_weight_b.main(io.StringIO('{"l":7,"n":2,"weight":0}'), output, error) == 1
    assert output.getvalue() == ""
    assert "claimed weight" in error.getvalue()
