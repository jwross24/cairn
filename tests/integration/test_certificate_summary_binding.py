import copy
import json

import pytest
from _substrate_helpers import (
    ENV_MANIFEST_HASH,
    IDENTITY_A,
    IDENTITY_B,
    SELFTEST_SUMMARY,
    TRANSCRIPT_HASH,
    open_writer,
)

from cairn import bundle, repro, selftest, selftest_skills, substrate
from cairn.skills import slope_weight_b

WHICH = selftest_skills.SLOPE_WEIGHT_B
SUMMARY_WITH_WITNESS = {**SELFTEST_SUMMARY, "must_fail_witnesses": 1}


def _skill_verifier(identity):
    return repro.Verifier(repro.SKILL_VERIFIER, identity)


def test_the_summary_is_part_of_the_certificate_hash(tmp_path):
    writer = open_writer(tmp_path)
    identity = writer.put_identity_bundle(IDENTITY_A)
    honest = writer.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SUMMARY_WITH_WITNESS)
    inflated = {**SUMMARY_WITH_WITNESS, "must_fail_witnesses": 7}
    assert honest == selftest.certificate_hash(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SUMMARY_WITH_WITNESS)
    assert honest != selftest.certificate_hash(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, inflated)
    writer.close()


def test_a_row_whose_summary_was_swapped_under_the_minted_hash_is_uncertified(tmp_path):
    source = open_writer(tmp_path, "source.sqlite")
    identity = source.put_identity_bundle(IDENTITY_B)
    cert = source.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SUMMARY_WITH_WITNESS)
    row = source.get_certificate(identity)
    assert source.certified(identity) is True
    assert repro.owner_grade(source, "producer", _skill_verifier(identity))[0] == repro.VERIFIABLE
    source.close()
    target = open_writer(tmp_path, "target.sqlite")
    try:
        target.put_identity_bundle(IDENTITY_B)
        inflated = json.dumps({**SUMMARY_WITH_WITNESS, "must_fail_witnesses": 7}, sort_keys=True, separators=(",", ":"))
        target.conn.execute(
            "INSERT INTO skill_certificates VALUES (?, ?, ?, ?, ?, ?)",
            (identity, cert, row["transcript_hash"], row["env_manifest_hash"], inflated, row["at"]),
        )
        assert target.get_certificate(identity)["cert_hash"] == cert
        assert target.certified(identity) is False
        grade = repro.owner_grade(target, "producer", _skill_verifier(identity))
        assert grade == (repro.AUDIT_ONLY, "verifier-uncertified")
    finally:
        target.close()


@pytest.fixture
def deployed(tmp_path, clear_flags):
    bundle_path, pin_path = tmp_path / "gate-bundle.sqlite", tmp_path / "gate-bundle.pin"
    bundle.build(bundle.REPO_ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    clear_flags(pin_path)
    return bundle_path, pin_path


@pytest.mark.parametrize("count", [7, 0])
def test_recertification_refuses_a_stored_count_the_self_test_does_not_compute(tmp_path, deployed, count):
    bundle_path, pin_path = deployed
    config = bundle.GateBundle.open(bundle_path, pin_path).verifier_config()
    doc = copy.deepcopy(selftest_skills.load_slope_corpus(WHICH))
    doc["cases"], doc["pass_floor"] = doc["cases"][:1], 1
    with substrate.Substrate.open(tmp_path / "honest.sqlite") as sub:
        honest = selftest_skills.certify(sub, config, WHICH, doc=doc)
        assert selftest_skills.certify(sub, config, WHICH, doc=doc)["recorded"] == "present"
    with substrate.Substrate.open(tmp_path / "planted.sqlite") as sub:
        sub.put_identity_bundle(slope_weight_b.identity_bundle())
        sub.put_certificate(
            honest["identity_bundle_hash"],
            honest["transcript_hash"],
            honest["env_manifest_hash"],
            {**honest["summary"], "must_fail_witnesses": count},
        )
        with pytest.raises(selftest.SelftestFailed, match="differs from the minted"):
            selftest_skills.certify(sub, config, WHICH, doc=doc)
