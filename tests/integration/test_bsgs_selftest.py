import copy
import hashlib
import importlib
import json
import math
import sys
from pathlib import Path

import pytest

from cairn import bundle, canon, cli, env, exits, keys, selftest, selftest_skills, substrate
from cairn.skills import bsgs, instance_maker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "conformance"))
skill_contract = importlib.import_module("skill_contract")

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

WHICH = selftest_skills.BSGS
TRANSCRIPT_GOLDEN = "bsgs_selftest_transcript"
FLOOR_GOLDEN = "bsgs_floor"
CERTIFICATE_GOLDEN = "bsgs_certificate"
FRESH_INSTANCES = 20
FRESH_BITS = 40


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


def test_the_cli_certifies_bsgs_and_records_its_certificate(tmp_path, pinned_bundle, capsys):
    argv, bundle_path, pin_path = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", WHICH, *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert document["which"] == WHICH and document["pass"] == 5 and document["floor"] == 5
    assert document["arms"] == {"postcondition": "pass", "verifier": {"ok": 1, "fail": 1}}
    assert document["double_run"] == "byte-equal" and document["recorded"] == "inserted"
    identity_hash = bsgs.skill_identity_hash()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        assert sub.certified(identity_hash)
        row = sub.get_certificate(identity_hash)
    assert row["cert_hash"] == document["certificate"]
    assert json.loads(row["selftest_summary"])["cross_check"]["independent_range"] == {"bits": [0, 28]}


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
        json.dumps({"implementation_revision": bsgs.implementation_revision()}, indent=1, sort_keys=True) + "\n",
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


def test_a_corpus_case_altered_by_one_byte_fails_the_certificate_check(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus(selftest_skills.CORPUS_PATHS[WHICH]))
    case = next(c for c in doc["cases"] if c["id"] == "bits24_seed1")
    case["fields"]["x"]["value"] += 1
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        with pytest.raises(selftest.SelftestFailed, match="declares pass but ellmul failed"):
            selftest_skills.certify(sub, _config(bundle_path, pin_path), WHICH, doc=doc)
        assert sub.conn.execute("SELECT count(*) FROM skill_certificates").fetchone()[0] == 0


def test_the_postcondition_arms_wrong_draw_is_refused(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    real = selftest_skills._other_scalar
    monkeypatch.setattr(selftest_skills, "_other_scalar", lambda seed, n, x, label: x)
    with pytest.raises(selftest.SelftestFailed, match="was accepted"):
        selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))
    monkeypatch.setattr(selftest_skills, "_other_scalar", real)
    assert selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))["arms"]["verifier"] == {"ok": 1, "fail": 1}


@pytest.mark.timeout(900)
def test_twenty_fresh_forty_bit_instances_drawn_by_postcondition_are_recovered():
    for seed in range(1, FRESH_INSTANCES + 1):
        inst = instance_maker.run(FRESH_BITS, 1000 + seed)
        out = bsgs.run(FRESH_BITS, seed, inst.p, inst.a, inst.b, inst.n, inst.P, inst.Q)
        assert out.x == inst.x and out.status == "OK" and out.cross_check["result"] == "untested"
        assert out.memory["entries"] == math.isqrt(inst.n - 1)


@pytest.mark.parametrize("bits", [20, 24, 28, 30])
def test_measured_table_growth_follows_the_declared_sqrt_n_shape(bits):
    inst = instance_maker.run(bits, 7)
    out = bsgs.run(bits, 1, inst.p, inst.a, inst.b, inst.n, inst.P, inst.Q)
    entries = out.memory["entries"]
    assert entries == math.isqrt(inst.n - 1)
    assert out.memory["table_bytes"] == entries * bsgs.KEY_BYTES + out.memory["slots"] * bsgs.SLOT_BYTES
    assert 2 * (entries + 1) <= out.memory["slots"] < 4 * (entries + 1)
    assert 2 ** (bits / 2 - 1) <= entries + 1 <= 2 ** (bits / 2 + 0.5)


def test_bsgs_is_a_conforming_subject_of_the_contract_harness():
    subject = skill_contract.SUBJECTS_BY_NAME["bsgs"]
    assert subject.conforming and subject.module == "cairn.skills.bsgs"
    assert subject.floor_golden == FLOOR_GOLDEN and subject in skill_contract.CONFORMING


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


class _Fixed:
    def __init__(self, accepted, reason):
        self.accepted = accepted
        self.reason = reason


@pytest.mark.parametrize(
    ("outcomes", "match"),
    [
        ([_Fixed(False, "timeout"), _Fixed(False, "xP-ne-Q")], "was refused: timeout"),
        ([_Fixed(True, None), _Fixed(False, "timeout")], "unexpected refusal reason 'timeout'"),
    ],
    ids=["own-answer-refused", "wrong-refusal-reason"],
)
def test_the_verifier_arm_refuses_a_driver_that_misbehaves(tmp_path, pinned_bundle, monkeypatch, outcomes, match):
    from cairn import verifier

    bundle_path, pin_path = pinned_bundle()
    replies = iter(outcomes)
    monkeypatch.setattr(verifier.Verifier, "run", lambda self, instance, x: next(replies))
    with pytest.raises(selftest.SelftestFailed, match=match):
        selftest_skills.run_once(WHICH, _config(bundle_path, pin_path))


LADDER_PLAN = json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
MEASURED_TABLE = {30: (29396, 497314), 40: (881490, 15440525), 50: (26116919, 477370808)}


def test_the_ladder_plan_floor_and_cap_carry_this_skills_measured_figures_not_the_seed():
    rungs = {rung["bits"]: rung for rung in LADDER_PLAN["rungs"]}
    per_size = bsgs.COST_PROFILE.production.per_size
    for bits, (entries, table_bytes) in MEASURED_TABLE.items():
        floor = rungs[bits]["refutation_floor"]
        assert floor["group_ops"] == round(per_size[bits].mean_tries)
        assert (floor["table_entries"], floor["memory_bytes"]) == (entries, table_bytes)
    assert rungs[50]["memory_cap_bytes"] == rungs[50]["refutation_floor"]["memory_bytes"] == 477370808
    memory = bsgs.COST_PROFILE.memory
    assert memory is not None
    bytes_per_entry = memory.measured_bytes_per_entry[50]
    assert rungs[60]["memory_cap_bytes"] == int(2**30 * bytes_per_entry) == 19625853059
    for key in ("rungs.refutation_floor", "rungs.memory_cap_bytes"):
        assert LADDER_PLAN["provenance"][key].startswith("measured:research/grounding/m1-dlp-skill-costs.md")
