import dataclasses
import json
import sys
from pathlib import Path

import pytest

from cairn import attest, bundle, claims, cli, human_queue, justify, nogo
from cairn.tiergate import NOGO_UNDECLARED, NOGO_UNREVIEWED, TIER_TWO_ABOVE, Admitted, Launch, TierGate, TierRefused

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories
from test_tier_gate import METHOD_IDENTITY, certify, record_hypothesis, synthetic_profile

AT = "2026-09-02T00:00:00.000000+00:00"
EVASIONS = (
    {"no_go": nogo.SHOUP_SQRT_N, "evasion": "exploits the named endomorphism structure"},
    {"no_go": nogo.ISOGENY_INVARIANCE, "evasion": "never walks the isogeny class"},
    {"no_go": nogo.PRIME_FIELD_INDEX_CALCULUS, "evasion": "no point decomposition over F_p"},
)


@pytest.fixture
def arena(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "attest.bin"
    attest.init(str(attest_path), gate_bundle.waiver_target())
    sub = helpers.open_writer(tmp_path)
    identity = certify(sub)
    hypothesis = record_hypothesis(sub)
    arena = {
        "sub": sub,
        "bundle": gate_bundle,
        "bundle_path": bundle_path,
        "pin_path": pin_path,
        "attest": attest_path,
        "gate": TierGate(sub, gate_bundle, attest_path=str(attest_path)),
        "identity": identity,
        "key": hypothesis.hash,
        "db": tmp_path / "substrate.sqlite",
    }
    yield arena
    arena["sub"].close()


def launch(arena, tier, *, core_s):
    return Launch(
        cost_profile=synthetic_profile(core_s),
        inputs=40,
        budget_remaining=10_000_000.0,
        hypothesis_key=arena["key"],
        method_identity=METHOD_IDENTITY,
        skill_identity_hash=arena["identity"],
        declared_tier=tier,
        target_attack=True,
    )


def declare(arena, evasions=EVASIONS):
    return nogo.write_declaration(
        arena["sub"],
        nogo.Declaration(hypothesis_key=arena["key"], evasions=evasions, declared_by="worker", at=AT),
        attest_path=str(arena["attest"]),
    )


def review_at(arena, declaration_hash, verdict, offset):
    return nogo.Review(
        hypothesis_key=arena["key"],
        declaration_hash=declaration_hash,
        reviewer="human-1",
        verdict=verdict,
        gate_bundle_hash=arena["bundle"].hash,
        at=AT,
        file_offset=offset,
    )


def attest_review(arena, declaration_hash, verdict):
    unplaced = review_at(arena, declaration_hash, verdict, 0)
    offset = attest.append_record(str(arena["attest"]), nogo.review_canonical(unplaced))
    placed = review_at(arena, declaration_hash, verdict, offset)
    nogo.write_review(arena["sub"], placed)
    return placed, offset


def test_without_a_declaration_a_target_attack_branch_holds_no_tier_one_ticket(arena):
    decision = arena["gate"].admit(launch(arena, 1, core_s=2))
    assert isinstance(decision, TierRefused)
    assert NOGO_UNDECLARED in decision.reasons
    assert decision.ticket_tier == 0
    assert arena["sub"].conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0] == 0
    plain = dataclasses.replace(launch(arena, 1, core_s=2), target_attack=False)
    assert isinstance(arena["gate"].admit(plain), Admitted)


def test_with_a_declaration_but_no_review_tier_one_admits_and_tier_two_carries_the_no_review_reason(arena):
    digest, item_id = declare(arena)
    one = arena["gate"].admit(launch(arena, 1, core_s=2))
    assert isinstance(one, Admitted) and one.ticket_hash is not None
    two = arena["gate"].admit(launch(arena, 2, core_s=4000))
    assert isinstance(two, TierRefused)
    assert NOGO_UNREVIEWED in two.reasons
    assert TIER_TWO_ABOVE in two.reasons
    assert NOGO_UNDECLARED not in two.reasons
    assert human_queue.visible_closure(arena["sub"], item_id, str(arena["attest"])) is None


def test_an_attested_accept_for_tiering_restores_ordinary_eligibility_and_closes_the_queue_item(arena):
    digest, item_id = declare(arena)
    placed, offset = attest_review(arena, digest, nogo.ACCEPT_FOR_TIERING)
    assert attest.attestation_record_matches(str(arena["attest"]), offset, placed.record_digest)
    human_queue.close_by_attestation(
        arena["sub"], item_id, attest_path=str(arena["attest"]), file_offset=offset, record_digest=placed.record_digest
    )
    closure = human_queue.visible_closure(arena["sub"], item_id, str(arena["attest"]))
    assert closure["path"] == human_queue.PATH_ATTESTATION and closure["record_digest"] == placed.record_digest
    one = arena["gate"].admit(launch(arena, 1, core_s=2))
    assert isinstance(one, Admitted)
    two = arena["gate"].admit(launch(arena, 2, core_s=4000))
    assert isinstance(two, TierRefused)
    assert two.reasons == (TIER_TWO_ABOVE,)


def test_an_accept_for_tiering_is_no_claim_tag(arena):
    digest, _ = declare(arena)
    stmt = factories.claim_statement(seed=7)
    claims.write_claim_statement(arena["sub"], stmt)
    before = justify.derive_tag(arena["sub"], stmt.hash, str(arena["attest"])).tag
    attest_review(arena, digest, nogo.ACCEPT_FOR_TIERING)
    assert nogo.flag(arena["sub"], arena["key"], str(arena["attest"])).accepted
    after = justify.derive_tag(arena["sub"], stmt.hash, str(arena["attest"])).tag
    assert (before, after) == (justify.SPECULATION, justify.SPECULATION)


def test_a_review_row_without_its_attestation_record_is_absent_to_the_gate_and_cannot_close_the_item(arena):
    digest, item_id = declare(arena)
    ghost = nogo.Review(
        hypothesis_key=arena["key"],
        declaration_hash=digest,
        reviewer="human-1",
        verdict=nogo.ACCEPT_FOR_TIERING,
        gate_bundle_hash=arena["bundle"].hash,
        at=AT,
        file_offset=4096,
    )
    nogo.write_review(arena["sub"], ghost)
    assert nogo.visible_reviews(arena["sub"], arena["key"], str(arena["attest"])) == []
    two = arena["gate"].admit(launch(arena, 2, core_s=4000))
    assert isinstance(two, TierRefused) and NOGO_UNREVIEWED in two.reasons
    with pytest.raises(human_queue.ClosingRuleViolation, match=r"holds no record at offset 4096|is mirrored"):
        human_queue.close_by_attestation(
            arena["sub"], item_id, attest_path=str(arena["attest"]), file_offset=4096, record_digest=ghost.record_digest
        )


def test_an_attested_record_that_no_review_row_mirrors_cannot_close_the_item(arena):
    digest, item_id = declare(arena)
    unmirrored = review_at(arena, digest, nogo.ACCEPT_FOR_TIERING, 0)
    offset = attest.append_record(str(arena["attest"]), nogo.review_canonical(unmirrored))
    assert attest.attestation_record_matches(str(arena["attest"]), offset, unmirrored.record_digest)
    with pytest.raises(human_queue.ClosingRuleViolation, match=r"no nogo_review on branch .* is mirrored"):
        human_queue.close_by_attestation(
            arena["sub"],
            item_id,
            attest_path=str(arena["attest"]),
            file_offset=offset,
            record_digest=unmirrored.record_digest,
        )
    assert human_queue.visible_closure(arena["sub"], item_id, str(arena["attest"])) is None


def test_a_revised_declaration_keeps_one_open_item_that_only_a_review_of_the_revision_closes(arena):
    old, item_id = declare(arena)
    revised = tuple({**e, "evasion": e["evasion"] + " (revised)"} for e in EVASIONS)
    new, same_item = declare(arena, revised)
    assert new != old and same_item == item_id
    stale, stale_offset = attest_review(arena, old, nogo.ACCEPT_FOR_TIERING)
    with pytest.raises(human_queue.ClosingRuleViolation, match="is mirrored"):
        human_queue.close_by_attestation(
            arena["sub"],
            item_id,
            attest_path=str(arena["attest"]),
            file_offset=stale_offset,
            record_digest=stale.record_digest,
        )
    two = arena["gate"].admit(launch(arena, 2, core_s=4000))
    assert isinstance(two, TierRefused) and NOGO_UNREVIEWED in two.reasons
    current, offset = attest_review(arena, new, nogo.ACCEPT_FOR_TIERING)
    human_queue.close_by_attestation(
        arena["sub"], item_id, attest_path=str(arena["attest"]), file_offset=offset, record_digest=current.record_digest
    )
    assert human_queue.visible_closure(arena["sub"], item_id, str(arena["attest"])) is not None
    assert arena["gate"].admit(launch(arena, 2, core_s=4000)).reasons == (TIER_TWO_ABOVE,)


def test_a_rejecting_review_leaves_tier_two_refused(arena):
    digest, _ = declare(arena)
    attest_review(arena, digest, nogo.REJECT)
    two = arena["gate"].admit(launch(arena, 2, core_s=4000))
    assert isinstance(two, TierRefused) and NOGO_UNREVIEWED in two.reasons


def test_the_cli_attest_append_writes_the_review_and_closes_the_queue_item(arena, tmp_path, capsys):
    digest, item_id = declare(arena)
    arena["sub"].close()
    record = tmp_path / "review.json"
    record.write_text(
        json.dumps(
            {
                "hypothesis_key": arena["key"],
                "declaration_hash": digest,
                "reviewer": "human-1",
                "verdict": nogo.ACCEPT_FOR_TIERING,
                "at": AT,
            }
        )
    )
    code = cli.main(
        [
            "--db",
            str(arena["db"]),
            "--bundle",
            str(arena["bundle_path"]),
            "--pin",
            str(arena["pin_path"]),
            "--attest",
            str(arena["attest"]),
            "attest",
            "append",
            "--kind",
            "nogo_review",
            "--record",
            str(record),
            "--json",
        ]
    )
    out = capsys.readouterr().out
    assert code == 0, out
    payload = json.loads(out)
    assert payload["kind"] == "nogo_review" and payload["offset"] > 0
    sub = arena["sub"] = helpers.open_writer(tmp_path)
    closure = human_queue.visible_closure(sub, item_id, str(arena["attest"]))
    assert closure is not None and closure["record_digest"] == payload["record_digest"]
    flag = nogo.flag(sub, arena["key"], str(arena["attest"]))
    assert flag.accepted
    two = TierGate(sub, arena["bundle"], attest_path=str(arena["attest"])).admit(launch(arena, 2, core_s=4000))
    assert two.reasons == (TIER_TWO_ABOVE,)
