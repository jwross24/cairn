import copy
import json

import pytest
from _toy_curve_support import (
    CERTIFICATE_GOLDEN,
    FLOOR_GOLDEN,
    PLATFORM_SKIP,
    TRANSCRIPT_GOLDEN,
    _certificate_rows,
    _config,
    _paths,
    _records,
    _run,
)

from cairn import bundle, canon, cli, env, exits, keys, selftest, substrate
from cairn.skills import toy_curve

pytestmark = PLATFORM_SKIP


def test_selftest_certifies_the_revision_and_records_every_row(tmp_path, pinned_bundle, capsys, json_test_log):
    argv, bundle_path, pin_path = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert out.count("\n") == 1
    assert document["schema_version"] == cli.SCHEMA_VERSION
    assert document["command"] == "selftest"
    assert document["pass"] == 4 and document["floor"] == 4
    assert document["arms"] == {
        "postcondition": "pass",
        "verifier": {"ok": 20, "fail": 20},
    }
    assert document["double_run"] == "byte-equal"
    assert document["bundle"] == bundle.GateBundle.open(bundle_path, pin_path).hash

    identity_hash = toy_curve.skill_identity_hash()
    assert document["identity_bundle_hash"] == identity_hash
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(identity_hash)
        assert sub.get_node(identity_hash) is not None
        assert sub.get_node(document["certificate"]) is not None
        assert sub.is_root("certificate", document["certificate"])
        assert [(r["parent_hash"], r["edge_kind"]) for r in sub.lineage_of(document["certificate"])] == [
            (identity_hash, substrate.EDGE_CERTIFIES)
        ]
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    assert row["transcript_hash"] == document["transcript_hash"]
    assert row["env_manifest_hash"] == keys.env_manifest_digest(env.manifest())

    summary = json.loads(row["selftest_summary"])
    assert summary["pass"] == 4 and summary["floor"] == 4
    assert summary["randomized_arm"] is True
    assert summary["cross_check"] == [
        {"axis": "algorithm", "independent_range": {"bits": [0, 50]}},
        {"axis": "implementation", "independent_range": {"bits": [30, 60]}},
    ]
    origins = summary["corpus_origins"]
    assert origins["F5"]["P"] == "author_supplied"
    assert origins["F5"]["Q"] == "author_supplied"
    assert origins["F5"]["x"] == "author_supplied"
    assert origins["GF101"]["P"] == "author_supplied"
    assert origins["F5"]["p"] == "upstream_vendored"
    assert origins["bits150"]["P"] == "upstream_vendored"

    arms = _records(json_test_log, "arm")
    verifier_record = next(r for r in arms if r["name"] == "verifier")
    assert verifier_record["bundle_hash"] == document["bundle"]
    assert verifier_record["ok"] == verifier_record["fail"] == 20
    assert {r["id"] for r in _records(json_test_log, "case")} == {
        "F5",
        "GF101",
        "bits150",
        "negative_control",
    }


def test_selftest_is_idempotent_for_an_unchanged_revision(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    first_code, first_out, _ = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    second_code, second_out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert (first_code, second_code) == (exits.OK, exits.OK), err
    first, second = json.loads(first_out), json.loads(second_out)
    assert first["recorded"] == "inserted" and second["recorded"] == "present"
    assert first["certificate"] == second["certificate"]
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1


def test_the_alias_resolves(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["self-test", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    assert json.loads(out)["command"] == "selftest"


def test_transcript_and_floor_goldens(tmp_path, pinned_bundle, assert_golden):
    bundle_path, pin_path = pinned_bundle()
    result = selftest.run_once(_config(bundle_path, pin_path))
    assert_golden(
        TRANSCRIPT_GOLDEN,
        "\n".join(selftest.transcript_lines(result["records"])) + "\n",
    )
    assert_golden(
        FLOOR_GOLDEN,
        json.dumps(
            {
                "pass": result["passes"],
                "floor": result["floor"],
                "arms": result["arms"],
            },
            indent=1,
            sort_keys=True,
        )
        + "\n",
    )


def test_transcript_golden_guard(tmp_path, pinned_bundle, assert_golden, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    result = selftest.run_once(_config(bundle_path, pin_path))
    live = "\n".join(selftest.transcript_lines(result["records"])) + "\n"
    assert_golden(TRANSCRIPT_GOLDEN, live)
    with pytest.raises(AssertionError, match="UPDATE_GOLDENS=1"):
        assert_golden(TRANSCRIPT_GOLDEN, live + "0\n")
    # The planted mismatch writes a .actual by design; a run that ends green must
    # leave no artifact that reads as pending work.
    assert_golden(TRANSCRIPT_GOLDEN, live)


def test_the_certificate_is_the_digest_of_its_three_inputs(tmp_path, pinned_bundle, assert_golden):
    bundle_path, pin_path = pinned_bundle()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        result = selftest.certify(sub, _config(bundle_path, pin_path))
    recomputed = canon.digest(
        keys.TAG_SELFTEST_CERT,
        substrate.certificate_canonical(
            result["identity_bundle_hash"],
            result["transcript_hash"],
            keys.env_manifest_digest(env.manifest()),
            result["summary"],
        ),
    )
    assert recomputed == result["certificate"]
    assert_golden(
        CERTIFICATE_GOLDEN,
        json.dumps({"implementation_revision": toy_curve.implementation_revision()}, indent=1, sort_keys=True) + "\n",
    )


def test_a_changed_expected_output_refuses_and_writes_no_certificate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus())
    doc["cases"][0]["fields"]["Q"]["value"] = [3, 2]
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="ellmul"):
            selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
        assert not sub.certified(toy_curve.skill_identity_hash())
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_the_negative_control_point_must_not_be_killed_by_the_order(tmp_path):
    case = next(c for c in selftest.load_corpus()["cases"] if c["id"] == "negative_control")
    observed, held, per_check = selftest.run_case(case)
    assert held and per_check["order_does_not_kill"]
    assert observed["order_does_not_kill"] == [61, 319]
    assert observed["ellorder"] == 21

    killed = copy.deepcopy(case)
    killed["fields"]["Q"]["value"] = killed["fields"]["P"]["value"]
    _, held_after, per_check_after = selftest.run_case(killed)
    assert not held_after and not per_check_after["order_does_not_kill"]


def test_a_bumped_revision_is_not_certified(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.OK, err
    certified_identity = json.loads(out)["identity_bundle_hash"]
    tree = tmp_path / "bumped"
    for rel in toy_curve.IDENTITY_SOURCES:
        target = tree / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((toy_curve.REPO_ROOT / rel).read_bytes())
    edited = tree / toy_curve.IDENTITY_SOURCES[0]
    edited.write_bytes(edited.read_bytes() + b"\n")

    bumped_identity = keys.identity_bundle_hash(toy_curve.identity_bundle(tree))
    assert bumped_identity != certified_identity
    assert toy_curve.implementation_revision(tree) != toy_curve.implementation_revision()
    assert selftest.arm_seed(toy_curve.implementation_revision(tree)) != selftest.arm_seed(
        toy_curve.implementation_revision()
    )
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(certified_identity)
        assert not sub.certified(bumped_identity)
        assert sub.get_certificate(bumped_identity) is None
