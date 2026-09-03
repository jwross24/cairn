import json
import sys
from pathlib import Path

import pytest

from cairn import repro
from cairn.substrate import GradeError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

PRODUCER = helpers.IDENTITY_A
INDEPENDENT = helpers.IDENTITY_B
WITH_MUST_FAIL = {**helpers.SELFTEST_SUMMARY, repro.MUST_FAIL_KEY: 20}


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


def certify(sub, identity, summary=WITH_MUST_FAIL):
    identity_hash = sub.put_identity_bundle(identity)
    sub.put_certificate(identity_hash, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, summary)
    return identity_hash


@pytest.mark.parametrize(
    ("grade", "tier", "decision"),
    [
        ("Verifiable", 0, repro.CHECK_WITNESS),
        ("Verifiable", 1, repro.CHECK_WITNESS),
        ("Verifiable", 2, repro.CHECK_WITNESS),
        ("Verifiable", 3, repro.CHECK_WITNESS),
        ("Replayable", 0, repro.RERUN_NOW),
        ("Replayable", 1, repro.RERUN_NOW),
        ("Replayable", 2, repro.RERUN_ON_DERIVE),
        ("Replayable", 3, repro.RERUN_ON_DERIVE),
        ("AuditOnly", 0, repro.INADMISSIBLE),
        ("AuditOnly", 1, repro.INADMISSIBLE),
        ("AuditOnly", 2, repro.INADMISSIBLE),
        ("AuditOnly", 3, repro.INADMISSIBLE),
    ],
)
def test_the_policy_is_fixed_by_grade_and_tier(grade, tier, decision):
    assert repro.policy(grade, tier) == decision
    assert repro.TABLE[(grade, tier)] == decision


def test_the_table_covers_every_cell_once_and_nothing_else():
    assert len(repro.TABLE) == 12
    assert set(repro.TABLE.values()) == set(repro.DECISIONS)
    with pytest.raises(repro.ReproError, match="grade must be one of"):
        repro.policy("Verified", 0)
    with pytest.raises(repro.ReproError, match="tier must be one of"):
        repro.policy("Replayable", 4)


def test_a_verifier_names_its_identity_exactly_when_it_is_a_skill():
    assert repro.Verifier(repro.GATE_VERIFIER).identity_bundle_hash is None
    assert repro.Verifier(repro.SKILL_VERIFIER, "ab" * 32).identity_bundle_hash == "ab" * 32
    with pytest.raises(repro.ReproError, match="names its identity bundle hash"):
        repro.Verifier(repro.SKILL_VERIFIER)
    with pytest.raises(repro.ReproError, match="names its identity bundle hash"):
        repro.Verifier(repro.GATE_VERIFIER, "ab" * 32)
    with pytest.raises(repro.ReproError, match="verifier kind must be"):
        repro.Verifier("human")


@pytest.mark.parametrize(
    ("summary", "count"),
    [
        (WITH_MUST_FAIL, 20),
        (json.dumps(WITH_MUST_FAIL), 20),
        ({repro.MUST_FAIL_KEY: 0}, 0),
        (helpers.SELFTEST_SUMMARY, None),
        ({repro.MUST_FAIL_KEY: -3}, None),
        ({repro.MUST_FAIL_KEY: True}, None),
        ({repro.MUST_FAIL_KEY: "20"}, None),
        ("not json", None),
        (None, None),
    ],
)
def test_the_must_fail_count_is_a_non_negative_integer_or_unknown(summary, count):
    assert repro.must_fail_witnesses(summary) == count


def test_a_gate_bundle_verifier_makes_a_witness_verifiable(writer):
    producer = certify(writer, PRODUCER)
    assert repro.owner_grade(writer, producer, repro.Verifier(repro.GATE_VERIFIER)) == (
        repro.VERIFIABLE,
        "gate-bundle-verifier",
    )


def test_a_certified_independent_skill_with_a_must_fail_witness_makes_a_witness_verifiable(writer):
    producer = certify(writer, PRODUCER)
    other = certify(writer, INDEPENDENT)
    assert repro.owner_grade(writer, producer, repro.Verifier(repro.SKILL_VERIFIER, other)) == (
        repro.VERIFIABLE,
        "certified-independent-verifier-with-must-fail-witness",
    )


def test_a_verifier_shipping_in_the_producer_s_own_revision_grades_audit_only(writer):
    producer = certify(writer, PRODUCER)
    assert repro.owner_grade(writer, producer, repro.Verifier(repro.SKILL_VERIFIER, producer)) == (
        repro.AUDIT_ONLY,
        "verifier-ships-in-producer-revision",
    )


def test_an_uncertified_or_must_fail_less_verifier_grades_audit_only(writer):
    producer = certify(writer, PRODUCER)
    uncertified = writer.put_identity_bundle(INDEPENDENT)
    assert repro.owner_grade(writer, producer, repro.Verifier(repro.SKILL_VERIFIER, uncertified)) == (
        repro.AUDIT_ONLY,
        "verifier-uncertified",
    )
    none_refused = certify(
        writer,
        {**INDEPENDENT, "implementation_revision": "cc" * 32},
        {**helpers.SELFTEST_SUMMARY, repro.MUST_FAIL_KEY: 0},
    )
    assert repro.owner_grade(writer, producer, repro.Verifier(repro.SKILL_VERIFIER, none_refused)) == (
        repro.AUDIT_ONLY,
        "verifier-selftest-carries-no-must-fail-witness",
    )


def test_a_certificate_that_predates_the_must_fail_count_is_refused_not_read_as_zero(writer):
    producer = certify(writer, PRODUCER)
    older = certify(writer, {**INDEPENDENT, "implementation_revision": "dd" * 32}, helpers.SELFTEST_SUMMARY)
    with pytest.raises(repro.ReproError, match="carries no must_fail_witnesses count; re-certify"):
        repro.owner_grade(writer, producer, repro.Verifier(repro.SKILL_VERIFIER, older))
    node = writer.put_node("witness", b"\x01", replay_grade=repro.VERIFIABLE)
    with pytest.raises(repro.ReproError):
        repro.apply_owner_grade(writer, node, producer, repro.Verifier(repro.SKILL_VERIFIER, older))
    assert writer.effective_grade(node) == repro.VERIFIABLE


def test_applying_the_owner_grade_only_weakens(writer):
    producer = certify(writer, PRODUCER)
    node = writer.put_node("witness", b"\x00", replay_grade=repro.VERIFIABLE)
    grade, reason = repro.apply_owner_grade(writer, node, producer, repro.Verifier(repro.SKILL_VERIFIER, producer))
    assert (grade, reason, writer.effective_grade(node)) == (
        repro.AUDIT_ONLY,
        "verifier-ships-in-producer-revision",
        repro.AUDIT_ONLY,
    )
    assert [(r["from_grade"], r["to_grade"]) for r in writer.grade_history(node)] == [
        (repro.VERIFIABLE, repro.AUDIT_ONLY)
    ]
    with pytest.raises(GradeError, match="cannot strengthen"):
        repro.apply_owner_grade(writer, node, producer, repro.Verifier(repro.GATE_VERIFIER))
    assert writer.effective_grade(node) == repro.AUDIT_ONLY


def test_a_re_run_launches_with_the_cache_closed():
    assert repro.rerun_launch_kwargs() == {"skip_cache_lookup": True, "replay": repro.REPLAYABLE}


def test_a_ticket_tier_is_bounded_at_construction():
    import factories

    assert factories.ticket(tier=3).tier == 3
    for bad in (4, -1, True):
        with pytest.raises(ValueError, match="tier must be one of"):
            factories.ticket(tier=bad)
    assert repro.TIERS == (0, 1, 2, 3)
