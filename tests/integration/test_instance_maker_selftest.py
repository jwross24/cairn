import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, canon, cli, env, exits, keys, selftest, selftest_skills, substrate
from cairn.skills import instance_maker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conformance"))
skill_contract = importlib.import_module("skill_contract")

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

WHICH = selftest_skills.INSTANCE_MAKER
TRANSCRIPT_GOLDEN = "instance_maker_selftest_transcript"
FLOOR_GOLDEN = "instance_maker_floor"
CERTIFICATE_GOLDEN = "instance_maker_certificate"


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _paths(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    argv = ("--bundle", str(bundle_path), "--pin", str(pin_path), "--db", str(tmp_path / "substrate.sqlite"))
    return argv, bundle_path, pin_path


def _config(bundle_path, pin_path):
    return bundle.GateBundle.open(bundle_path, pin_path).verifier_config()


def test_the_cli_certifies_the_maker_and_records_its_certificate(tmp_path, pinned_bundle, capsys):
    argv, bundle_path, pin_path = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert document["which"] == WHICH and document["pass"] == 4 and document["floor"] == 4
    assert document["arms"] == {"postcondition": "pass", "verifier": {"ok": 1, "fail": 1}}
    assert document["double_run"] == "byte-equal" and document["recorded"] == "inserted"
    identity_hash = instance_maker.skill_identity_hash()
    assert document["identity_bundle_hash"] == identity_hash
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(identity_hash)
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    summary = json.loads(row["selftest_summary"])
    assert summary["cross_check"] == {"axis": "algorithm", "independent_range": {"bits": [0, 28]}}
    assert summary["randomized_arm"] is True
    assert set(summary["corpus_origins"]) == {
        "vector_bits40_trial7",
        "vector_bits50_trial0",
        "instance_bits20_trial0",
        "instance_bits28_trial3",
    }
    code, out, _ = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.OK and json.loads(out)["recorded"] == "present"


def test_transcript_floor_and_certificate_goldens(tmp_path, pinned_bundle, assert_golden):
    bundle_path, pin_path = pinned_bundle()
    result = selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))
    assert_golden(TRANSCRIPT_GOLDEN, "\n".join(selftest.transcript_lines(result["records"])) + "\n")
    assert_golden(
        FLOOR_GOLDEN,
        json.dumps(
            {"pass": result["passes"], "floor": result["floor"], "arms": result["arms"]}, indent=1, sort_keys=True
        )
        + "\n",
    )
    assert_golden(
        CERTIFICATE_GOLDEN,
        json.dumps({"implementation_revision": instance_maker.implementation_revision()}, indent=1, sort_keys=True)
        + "\n",
    )


def test_the_certificate_is_the_digest_of_its_three_inputs_and_the_double_run_is_byte_equal(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    first, second = selftest_skills.run_once(WHICH, config), selftest_skills.run_once(WHICH, config)
    assert (len(first["transcript"]), hashlib.sha256(first["transcript"]).hexdigest()) == (
        len(second["transcript"]),
        hashlib.sha256(second["transcript"]).hexdigest(),
    )
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        result = selftest_skills.certify(sub, config, WHICH)
    recomputed = canon.digest(
        keys.TAG_SELFTEST_CERT,
        substrate.certificate_canonical(
            result["identity_bundle_hash"], result["transcript_hash"], keys.env_manifest_digest(env.manifest())
        ),
    )
    assert recomputed == result["certificate"] and result["transcript_hash"] == first["transcript_hash"]


def test_a_derivation_vector_with_one_flipped_byte_fails_the_known_answer_test(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest_skills.load_maker_corpus())
    case = next(c for c in doc["cases"] if c["id"] == "vector_bits40_trial7")
    case["fields"]["nonce"]["value"] = "ac" + case["fields"]["nonce"]["value"][2:]
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="declares pass but the maker reported"):
            selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


def test_a_pinned_instance_altered_by_one_byte_fails_the_certificate_check(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest_skills.load_maker_corpus())
    case = next(c for c in doc["cases"] if c["id"] == "instance_bits20_trial0")
    case["fields"]["x"]["value"] += 1
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="ledger"),
    ):
        selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)


def test_the_cli_maps_a_malformed_corpus_and_a_failed_selftest_to_their_exit_codes(
    tmp_path, pinned_bundle, capsys, monkeypatch
):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    bad = tmp_path / "corpus.json"
    bad.write_text("{")
    monkeypatch.setitem(selftest_skills.CORPUS_PATHS, WHICH, bad)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.USER_INPUT and out == ""
    assert "instance-maker corpus is malformed" in err and str(bad) in err
    monkeypatch.setitem(selftest_skills.CORPUS_PATHS, WHICH, selftest_skills.SKILLS_DIR / "instance_maker_corpus.json")

    def failing(config, *, doc=None, root=None):
        raise selftest.SelftestFailed("derivation-arm", "planted")

    monkeypatch.setitem(selftest_skills.RUN_ONCE, WHICH, failing)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED and out == ""
    assert "planted" in err and "--log DEBUG" in err


def test_the_maker_is_a_conforming_subject_of_the_contract_harness():
    subject = skill_contract.SUBJECTS_BY_NAME["instance_maker"]
    assert subject.conforming and subject.module == "cairn.skills.instance_maker"
    assert subject.floor_golden == FLOOR_GOLDEN and subject.postcondition is not None
    assert subject in skill_contract.CONFORMING


def test_a_corpus_below_its_committed_floor_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest_skills.load_maker_corpus())
    doc["cases"][0]["ledger"] = "known_gap"
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="3 passing cases is below the floor 4"),
    ):
        selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)


def test_a_derivation_that_ignores_an_input_fails_the_arm(tmp_path, pinned_bundle, monkeypatch):
    from cairn import instances

    bundle_path, pin_path = pinned_bundle()
    real = instances.trial_seed
    arm_nonce = selftest_skills._nonce_from(
        selftest_skills._instance_seed(instance_maker.implementation_revision()), selftest_skills.LABEL_NONCE
    )

    def ignoring_trial(nonce, hypothesis_key, bits, trial):
        return real(nonce, hypothesis_key, bits, 0 if nonce == arm_nonce else trial)

    monkeypatch.setattr(instances, "trial_seed", ignoring_trial)
    with pytest.raises(selftest.SelftestFailed, match="a flipped input did not diverge"):
        selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))
