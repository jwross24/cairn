import copy
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest

from cairn import bundle, canon, cli, env, exits, keys, selftest, selftest_skills, substrate, verifier, witness
from cairn.skills import instance_maker, rho_dp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conformance"))
skill_contract = importlib.import_module("skill_contract")

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

WHICH = selftest_skills.RHO_DP
TRANSCRIPT_GOLDEN = "rho_dp_selftest_transcript"
FLOOR_GOLDEN = "rho_dp_floor"
CERTIFICATE_GOLDEN = "rho_dp_certificate"


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


def test_the_cli_certifies_rho_dp_and_records_its_certificate(tmp_path, pinned_bundle, capsys, json_test_log):
    argv, bundle_path, pin_path = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert document["which"] == WHICH and document["pass"] == 5 and document["floor"] == 5
    assert document["arms"] == {
        "postcondition": "pass",
        "verifier": {"ok": 1, "fail": 1},
        "witness": {"accepted": 1, "refused": 3},
    }
    assert document["double_run"] == "byte-equal" and document["recorded"] == "inserted"
    identity_hash = rho_dp.skill_identity_hash()
    assert document["identity_bundle_hash"] == identity_hash
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(identity_hash)
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    summary = json.loads(row["selftest_summary"])
    assert summary["cross_check"] == {"axis": "algorithm", "independent_range": {"bits": [0, 28]}}
    assert summary["corpus_origins"]["F5"]["p"] == "upstream_vendored"
    assert summary["corpus_origins"]["bits28_seed1"]["x"] == "author_supplied"
    cases = [json.loads(line) for line in json_test_log.read_text().splitlines() if '"event": "case"' in line]
    assert {c["id"] for c in cases} >= {
        "F5",
        "GF101",
        "bits20_seed1",
        "bits24_seed1",
        "bits28_seed1",
        "composite_order",
    }
    refused = next(c for c in cases if c["id"] == "composite_order")
    assert json.loads(refused["skill"])["outcome"] == "refused"
    code, out, _ = _run(["selftest", WHICH, *argv], capsys)
    assert code == exits.OK and out.strip() == document["certificate"]


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
        json.dumps({"implementation_revision": rho_dp.implementation_revision()}, indent=1, sort_keys=True) + "\n",
    )


def test_the_double_run_is_byte_equal_and_the_certificate_recomputes(tmp_path, pinned_bundle):
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
    assert recomputed == result["certificate"]


@pytest.mark.parametrize(
    ("case_id", "field", "delta", "match"),
    [("bits20_seed1", "x", 1, "declares pass but ellmul failed"), ("F5", "Q", (0, 1), "ellmul")],
    ids=["x-off-by-one", "Q-off-by-one"],
)
def test_a_corpus_case_altered_by_one_byte_fails_the_certificate_check(
    tmp_path, pinned_bundle, case_id, field, delta, match
):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus(selftest_skills.CORPUS_PATHS[WHICH]))
    case = next(c for c in doc["cases"] if c["id"] == case_id)
    value = case["fields"][field]["value"]
    case["fields"][field]["value"] = (
        value + delta if isinstance(value, int) else [value[0] + delta[0], value[1] + delta[1]]
    )
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match=match):
            selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


def test_a_diverging_double_run_refuses(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    real = selftest_skills.rho_dp_run_once
    calls = []

    def diverging(config, *, doc=None, root=None):
        result = real(config, doc=doc, root=root)
        calls.append(1)
        if len(calls) == 2:
            result = {**result, "transcript": result["transcript"] + b"\x00"}
        return result

    monkeypatch.setitem(selftest_skills.RUN_ONCE, WHICH, diverging)
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="double-run"),
    ):
        selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH)


def test_a_fresh_forty_bit_instance_verifies_gate_side_and_passes_the_tier_zero_verifier(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    inst = instance_maker.run(40, 20260901)
    out = rho_dp.run(40, 1, inst.p, inst.a, inst.b, inst.n, inst.P, inst.Q)
    assert out.x == inst.x and out.cross_check["result"] == "untested"
    verdict = witness.verify(witness.witness_from_output(out.to_wire()))
    assert verdict.accepted and verdict.x == inst.x
    driver = verifier.Verifier(_config(bundle_path, pin_path))
    instance = verifier.Instance(inst.p, inst.a, inst.b, inst.n, tuple(inst.P), tuple(inst.Q))
    assert driver.run(instance, out.x).accepted
    refused = driver.run(instance, out.x % (inst.n - 1) + 1)
    assert not refused.accepted and refused.reason == "xP-ne-Q"


def test_the_cli_maps_a_failed_selftest_to_gate_refused(tmp_path, pinned_bundle, capsys, monkeypatch):
    argv, _, _ = _paths(tmp_path, pinned_bundle)

    def failing(config, *, doc=None, root=None):
        raise rho_dp.PostconditionFailed("xP-eq-Q", "planted")

    monkeypatch.setitem(selftest_skills.RUN_ONCE, WHICH, failing)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED and out == ""
    assert "planted" in err and "--log DEBUG" in err and "rho_dp_corpus.json" in err


def test_rho_dp_is_a_conforming_subject_of_the_contract_harness():
    subject = skill_contract.SUBJECTS_BY_NAME["rho_dp"]
    assert subject.conforming and subject.module == "cairn.skills.rho_dp"
    assert subject.floor_golden == FLOOR_GOLDEN and subject in skill_contract.CONFORMING
    assert subject.inputs["bits"] == 28 and subject.out_of_range_inputs["bits"] == 30


def test_a_case_whose_recorded_x_is_wrong_but_whose_fields_check_out_is_the_skills_refusal(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus(selftest_skills.CORPUS_PATHS[WHICH]))
    case = next(c for c in doc["cases"] if c["id"] == "bits20_seed1")
    case["postconditions"] = ["oncurve"]
    case["fields"]["x"]["value"] += 1
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="declares pass but the skill reported"),
    ):
        selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)


def test_a_corpus_below_its_committed_floor_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus(selftest_skills.CORPUS_PATHS[WHICH]))
    next(c for c in doc["cases"] if c["id"] == "F5")["ledger"] = "known_gap"
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="4 passing cases is below the floor 5"),
    ):
        selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)


def test_the_witness_arm_refuses_all_three_planted_forms(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    result = selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))
    body = next(body for kind, name, body in result["records"] if kind == "arm" and name == "witness")
    assert body["refused"] == {witness.B_EQ_D: 1, witness.FIRST_TRIPLE_NE_X: 1, witness.XP_NE_Q: 1}
    assert result["arms"]["witness"] == {"accepted": 1, "refused": 3}
