import dataclasses
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from cairn import attest, bundle, claims, human_authority, prefilter, tiergate
from cairn.profile import CostProfile, Production, SizeCost, Verification
from cairn.tiergate import OPERATOR_SESSION_ABSENT, TICKET_ABSENT, Admitted, TierRefused

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories

METHOD = {"interface_version": "toy/1", "params": {}}
AT = "2026-09-08T00:00:00.000000+00:00"
BUDGET = 10_000_000.0


@pytest.fixture
def arena(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "attest.bin"
    attest.init(str(attest_path), gate_bundle.waiver_target())
    sub = helpers.open_writer(tmp_path)
    yield {
        "sub": sub,
        "bundle": gate_bundle,
        "attest": str(attest_path),
        "gate": tiergate.TierGate(sub, gate_bundle, attest_path=str(attest_path)),
    }
    sub.close()


def append_session(arena, *, opened=None, expires=None, bundle_hash=None):
    opened = datetime.now(UTC) if opened is None else opened
    expires = opened + timedelta(seconds=3600) if expires is None else expires
    return human_authority.append(
        arena["sub"],
        arena["attest"],
        human_authority.OPERATOR_SESSION,
        {
            "session_id": "authority-test-session",
            "issued_by": "test-operator",
            "opened_at": opened.isoformat(),
            "expires_at": expires.isoformat(),
        },
        gate_bundle_hash=arena["bundle"].hash if bundle_hash is None else bundle_hash,
    )


def append_ratification(arena, statement_hash, *, bundle_hash=None):
    return human_authority.append(
        arena["sub"],
        arena["attest"],
        human_authority.STATEMENT_RATIFICATION,
        {"statement_hash": statement_hash, "issued_by": "test-operator", "at": datetime.now(UTC).isoformat()},
        gate_bundle_hash=arena["bundle"].hash if bundle_hash is None else bundle_hash,
    )


def identity(arena):
    digest = arena["sub"].put_identity_bundle(helpers.IDENTITY_A)
    arena["sub"].put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return digest


def hypothesis(arena, statement_hash=None):
    obj = factories.hypothesis_object(method_identity=METHOD, claim_statement_hash=statement_hash)
    claims.write_hypothesis_object(arena["sub"], obj)
    return obj


def launch(arena, key, *, tier=1, core_s=0.1, bits=40, statement_hash=None, skill=None):
    profile = CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={bits: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=core_s, mean_wall_s=core_s)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/integration/test_human_authority.py",
    )
    return tiergate.Launch(
        cost_profile=profile,
        inputs={"bits": bits},
        budget_remaining=BUDGET,
        hypothesis_key=key,
        method_identity=METHOD,
        skill_identity_hash=skill,
        declared_tier=tier,
        statement_hash=statement_hash,
    )


def test_operator_session_policy_is_required_and_bounded_by_one_hour(arena):
    assert arena["bundle"].tiers["operator_session"] == {"required": True, "max_duration_s": 3600}
    opened = datetime.now(UTC)
    with pytest.raises(human_authority.HumanAuthorityError, match="within 3600 seconds"):
        append_session(arena, opened=opened, expires=opened + timedelta(seconds=3601))


@pytest.mark.parametrize(
    ("tier", "core_s", "bits"),
    [(2, 0.1, 40), (1, 4000, 50), (3, 0.1, 40)],
    ids=["declared-tier-two", "underdeclared-fit-rung", "tier-three"],
)
def test_every_declared_or_derived_tier_two_launch_needs_a_live_session(arena, tier, core_s, bits):
    skill = identity(arena)
    obj = hypothesis(arena)
    decision = arena["gate"].admit(launch(arena, obj.hash, tier=tier, core_s=core_s, bits=bits, skill=skill))
    assert isinstance(decision, TierRefused)
    assert OPERATOR_SESSION_ABSENT in decision.reasons


@pytest.mark.parametrize("case", ["future", "expired", "wrong-bundle"])
def test_a_future_expired_or_wrong_bundle_session_does_not_open_the_gate(arena, case):
    now = datetime.now(UTC)
    if case == "future":
        append_session(arena, opened=now + timedelta(seconds=60), expires=now + timedelta(seconds=600))
    elif case == "expired":
        append_session(arena, opened=now - timedelta(seconds=7200), expires=now - timedelta(seconds=3600))
    else:
        append_session(arena, bundle_hash="f" * 64)
    assert not human_authority.operator_session_open(arena["sub"], arena["bundle"], arena["attest"], at=now.isoformat())
    decision = arena["gate"].admit(launch(arena, "f" * 64, tier=2))
    assert isinstance(decision, TierRefused)
    assert OPERATOR_SESSION_ABSENT in decision.reasons


def test_an_expired_session_is_not_revived_by_source_date_epoch(arena, monkeypatch):
    now = datetime.now(UTC).replace(microsecond=0)
    opened = now - timedelta(minutes=5)
    expires = now - timedelta(minutes=1)
    reproducible_at = opened + timedelta(minutes=1)
    append_session(arena, opened=opened, expires=expires)
    monkeypatch.setenv("SOURCE_DATE_EPOCH", str(int(reproducible_at.timestamp())))
    assert opened <= datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), UTC) < expires
    decision = arena["gate"].admit(launch(arena, "f" * 64, tier=2))
    assert isinstance(decision, TierRefused)
    assert OPERATOR_SESSION_ABSENT in decision.reasons


def test_a_live_session_allows_an_underdeclared_fit_rung(arena):
    skill = identity(arena)
    obj = hypothesis(arena)
    append_session(arena)
    decision = arena["gate"].admit(launch(arena, obj.hash, tier=1, core_s=4000, bits=50, skill=skill))
    assert isinstance(decision, Admitted), decision.reasons
    assert decision.ticket_tier == tiergate.HYPOTHESIS_TICKET_TIER


def test_an_unratified_statement_in_the_recorded_hypothesis_withholds_its_ticket(arena):
    stmt = factories.claim_statement(formal_source="theorem toy : True := trivial")
    claims.write_claim_statement(arena["sub"], stmt)
    obj = hypothesis(arena, stmt.hash)
    prefilter.record(
        arena["sub"],
        arena["bundle"],
        statement_hash=stmt.hash,
        verdicts=dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET),
        at=AT,
    )
    launch_ = launch(arena, obj.hash, statement_hash=None, skill=identity(arena))
    refused = arena["gate"].admit(launch_)
    assert isinstance(refused, TierRefused) and TICKET_ABSENT in refused.reasons
    append_ratification(arena, stmt.hash)
    admitted = arena["gate"].admit(launch_)
    assert isinstance(admitted, Admitted), admitted.reasons
    assert admitted.ticket_tier == tiergate.HYPOTHESIS_TICKET_TIER


@pytest.mark.parametrize("case", ["unattested-draft", "unrelated", "wrong-bundle"])
def test_a_draft_unrelated_or_wrong_bundle_ratification_does_not_support_a_ticket(arena, case):
    stmt = factories.claim_statement(formal_source="theorem toy : True := trivial")
    claims.write_claim_statement(arena["sub"], stmt)
    obj = hypothesis(arena, stmt.hash)
    prefilter.record(
        arena["sub"],
        arena["bundle"],
        statement_hash=stmt.hash,
        verdicts=dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET),
        at=AT,
    )
    if case == "unattested-draft":
        human_authority.write(
            arena["sub"],
            human_authority.STATEMENT_RATIFICATION,
            {"statement_hash": stmt.hash, "issued_by": "test-operator", "at": datetime.now(UTC).isoformat()},
            gate_bundle_hash=arena["bundle"].hash,
            file_offset=1_000_000,
        )
    elif case == "unrelated":
        append_ratification(arena, "9" * 64)
    else:
        append_ratification(arena, stmt.hash, bundle_hash="f" * 64)
    decision = arena["gate"].admit(launch(arena, obj.hash, skill=identity(arena)))
    assert isinstance(decision, TierRefused) and TICKET_ABSENT in decision.reasons


def test_a_statement_review_verdict_is_not_a_ratification(arena):
    stmt = factories.claim_statement(formal_source="theorem toy : True := trivial")
    claims.write_claim_statement(arena["sub"], stmt)
    obj = hypothesis(arena, stmt.hash)
    prefilter.record(
        arena["sub"],
        arena["bundle"],
        statement_hash=stmt.hash,
        verdicts=dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET),
        at=AT,
    )
    unplaced = factories.review_verdict(stmt.hash, verdict="approve")
    offset = attest.append_record(arena["attest"], claims.review_verdict_canonical(unplaced))
    claims.write_review_verdict(arena["sub"], dataclasses.replace(unplaced, file_offset=offset))
    decision = arena["gate"].admit(launch(arena, obj.hash, skill=identity(arena)))
    assert isinstance(decision, TierRefused) and TICKET_ABSENT in decision.reasons


def test_a_missing_operator_policy_refuses_an_admission_that_needs_a_session(arena):
    skill = identity(arena)
    obj = hypothesis(arena)
    arena["bundle"].tiers.pop("operator_session")
    decision = arena["gate"].admit(launch(arena, obj.hash, tier=2, skill=skill))
    assert isinstance(decision, TierRefused)
    assert OPERATOR_SESSION_ABSENT in decision.reasons
