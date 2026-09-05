import dataclasses
import json
import sys
from pathlib import Path

import pytest

from cairn import attest, claims, cli, nogo, scrutiny
from cairn.tiergate import REASON_ORDER, Launch, TierGate, TierRefused

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories
from test_nogo_tier_wiring import arena, attest_review, declare, launch
from test_repro_gate import ladder_evidence
from test_tier_gate import METHOD_IDENTITY, synthetic_profile

AT = "2026-09-05T00:00:00.000000+00:00"
PAYLOAD = {"out.json": b'{"x": 1}'}
BELOW_BOUND = {"exponent": "1/3", "constant": "1", "crossover": 40}

__all__ = ["arena"]


@pytest.fixture
def statement(arena):
    stmt = factories.claim_statement(seed=21, family="toy_curve")
    claims.write_claim_statement(arena["sub"], stmt)
    return stmt


def hypothesis(arena, family="toy_curve", cost_model=None, seed=9):
    obj = factories.hypothesis_object(family=family, cost_model=cost_model, seed=seed, method_identity=METHOD_IDENTITY)
    claims.write_hypothesis_object(arena["sub"], obj)
    return obj.hash


def tier_launch(arena, tier, *, key=None, statement_hash=None, target_attack=False):
    return Launch(
        cost_profile=synthetic_profile(4000 if tier >= 2 else 2),
        inputs=40,
        budget_remaining=10_000_000.0,
        hypothesis_key=key or arena["key"],
        method_identity=METHOD_IDENTITY,
        skill_identity_hash=arena["identity"],
        declared_tier=tier,
        statement_hash=statement_hash,
        target_attack=target_attack,
    )


def reasons_of(arena, launch_):
    decision = arena["gate"].admit(launch_)
    return set(decision.reasons) if isinstance(decision, TierRefused) else set()


def scrutiny_reasons(arena, launch_):
    return reasons_of(arena, launch_) & set(scrutiny.REASONS)


def signoff(arena, statement_hash, *, expert="expert-1", offset=None):
    unplaced = scrutiny.SignOff(
        statement_hash=statement_hash, expert=expert, gate_bundle_hash=arena["bundle"].hash, at=AT
    )
    if offset is None:
        offset = attest.append_record(str(arena["attest"]), scrutiny.signoff_canonical(unplaced))
    placed = dataclasses.replace(unplaced, file_offset=offset)
    scrutiny.write_signoff(arena["sub"], placed)
    return placed


def test_the_gate_bundle_carries_the_scrutiny_policy(arena):
    pol = scrutiny.policy(arena["bundle"])
    assert pol.target_family == "toy_curve" and pol.obligations == scrutiny.OBLIGATIONS
    assert tuple(REASON_ORDER[-5:]) == scrutiny.REASONS


def test_a_routine_hypothesis_carries_no_scrutiny_reason_at_any_tier(arena, statement):
    key = hypothesis(arena, family="model_curve", cost_model=BELOW_BOUND)
    plain = factories.claim_statement(seed=22, family="model_curve")
    claims.write_claim_statement(arena["sub"], plain)
    for tier in (0, 1, 2, 3):
        assert scrutiny_reasons(arena, tier_launch(arena, tier, key=key, statement_hash=plain.hash)) == set()
    read = scrutiny.gate_read(
        arena["sub"],
        arena["bundle"],
        hypothesis_key=key,
        statement_hash=plain.hash,
        declared_tier=3,
        nogo_flagged=False,
        attest_path=str(arena["attest"]),
    )
    assert read.scrutiny_class == scrutiny.ROUTINE and read.unmet == ()


def test_an_elevated_hypothesis_at_tier_three_carries_no_obligation(arena, statement):
    assert scrutiny_reasons(arena, tier_launch(arena, 3, statement_hash=statement.hash)) == set()


def test_a_target_attack_on_the_family_is_top_and_tier_three_names_every_unmet_obligation(arena, statement):
    for tier in (0, 1, 2):
        assert (
            scrutiny_reasons(arena, tier_launch(arena, tier, statement_hash=statement.hash, target_attack=True))
            == set()
        )
    unmet = scrutiny_reasons(arena, tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True))
    assert unmet == {
        scrutiny.SCRUTINY_LADDER_KEEP_ABSENT,
        scrutiny.SCRUTINY_REPRO_ABSENT,
        scrutiny.EXPERT_SIGNOFF_ABSENT,
    }
    run = (
        arena["sub"]
        .conn.execute("SELECT reasons FROM gate_runs WHERE gate = 'tier_gate' ORDER BY rowid DESC")
        .fetchone()
    )
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in json.loads(run["reasons"])


def test_a_claimed_exponent_below_the_generic_bound_is_top_without_any_no_go_flag(arena, statement):
    key = hypothesis(arena, cost_model=BELOW_BOUND)
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(
        arena, tier_launch(arena, 3, key=key, statement_hash=statement.hash)
    )
    assert scrutiny_reasons(arena, tier_launch(arena, 2, key=key, statement_hash=statement.hash)) == set()


def test_a_cost_model_on_either_side_raises_the_class_and_neither_side_lowers_it(arena):
    weak = {"exponent": "2/3", "constant": "1", "crossover": 40}
    weak_statement = factories.claim_statement(seed=22, family="toy_curve", cost_model=weak)
    strong_statement = factories.claim_statement(seed=24, family="toy_curve", cost_model=BELOW_BOUND)
    for stmt in (weak_statement, strong_statement):
        claims.write_claim_statement(arena["sub"], stmt)
    strong_key = hypothesis(arena, cost_model=BELOW_BOUND)
    weak_key = hypothesis(arena, cost_model=weak, seed=10)
    for key, stmt in ((strong_key, weak_statement), (weak_key, strong_statement)):
        read = scrutiny.gate_read(
            arena["sub"],
            arena["bundle"],
            hypothesis_key=key,
            statement_hash=stmt.hash,
            declared_tier=3,
            nogo_flagged=False,
            attest_path=str(arena["attest"]),
        )
        assert read.scrutiny_class == scrutiny.TOP
        assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(
            arena, tier_launch(arena, 3, key=key, statement_hash=stmt.hash)
        )
    assert scrutiny_reasons(arena, tier_launch(arena, 3, key=weak_key, statement_hash=weak_statement.hash)) == set()


def test_a_theorem_at_top_class_needs_the_formalization_gate_and_the_statement_review(arena):
    theorem = factories.claim_statement(seed=23, family="toy_curve", formal_source="theorem T : True := trivial")
    claims.write_claim_statement(arena["sub"], theorem)
    key = hypothesis(arena, cost_model=BELOW_BOUND)
    launch_ = tier_launch(arena, 3, key=key, statement_hash=theorem.hash)
    before = scrutiny_reasons(arena, launch_)
    assert {scrutiny.SCRUTINY_FORMALIZATION_ABSENT, scrutiny.SCRUTINY_STATEMENT_REVIEW_ABSENT} <= before
    claims.write_gate_run(
        arena["sub"],
        factories.gate_run(
            gate="challenge_render", result="pass", statement_hash=theorem.hash, seed=4, arm="dev-macos-fake-landrun"
        ),
    )
    unplaced = factories.review_verdict(theorem.hash, verdict="approve", seed=3)
    offset = attest.append_record(str(arena["attest"]), claims.review_verdict_canonical(unplaced))
    claims.write_review_verdict(
        arena["sub"], factories.review_verdict(theorem.hash, verdict="approve", seed=3, file_offset=offset)
    )
    after = scrutiny_reasons(arena, launch_)
    assert scrutiny.SCRUTINY_FORMALIZATION_ABSENT not in after
    assert scrutiny.SCRUTINY_STATEMENT_REVIEW_ABSENT not in after
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in after


def test_a_ladder_keep_and_a_passed_repro_record_meet_their_obligations_until_the_attempt_is_disowned(arena, statement):
    sub = arena["sub"]
    key = sub.put_recipe(helpers.recipe(seed=1, skill_identity_hash=arena["identity"]))
    attempt_id, _ = helpers.launch(sub, key, payloads=PAYLOAD)
    launch_ = tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True)
    ladder_evidence(sub, statement, attempt_id)
    after_keep = scrutiny_reasons(arena, launch_)
    assert scrutiny.SCRUTINY_LADDER_KEEP_ABSENT not in after_keep
    assert scrutiny.SCRUTINY_REPRO_ABSENT in after_keep
    record = claims.ReproRecord(attempt_id=attempt_id, kind="second_attempt_agree", passed=True, at=AT)
    claims.write_repro_record(sub, record)
    assert scrutiny.SCRUTINY_REPRO_ABSENT not in scrutiny_reasons(arena, launch_)
    sub.disown(attempt_id, at=AT)
    assert scrutiny.SCRUTINY_LADDER_KEEP_ABSENT in scrutiny_reasons(arena, launch_)


def test_an_accept_for_tiering_review_satisfies_no_top_class_obligation(arena, statement):
    digest, _ = declare(arena)
    attest_review(arena, digest, nogo.ACCEPT_FOR_TIERING)
    assert nogo.flag(arena["sub"], arena["key"], str(arena["attest"])).accepted
    unmet = scrutiny_reasons(arena, tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True))
    assert unmet == {
        scrutiny.SCRUTINY_LADDER_KEEP_ABSENT,
        scrutiny.SCRUTINY_REPRO_ABSENT,
        scrutiny.EXPERT_SIGNOFF_ABSENT,
    }


def test_an_attested_sign_off_meets_the_obligation_and_a_ghost_row_does_not(arena, statement):
    launch_ = tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True)
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(arena, launch_)
    ghost = signoff(arena, statement.hash, expert="ghost", offset=4096)
    assert scrutiny.visible_signoffs(arena["sub"], statement.hash, str(arena["attest"])) == []
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(arena, launch_)
    placed = signoff(arena, statement.hash)
    visible = scrutiny.visible_signoffs(arena["sub"], statement.hash, str(arena["attest"]))
    assert [(r["expert"], r["record_digest"]) for r in visible] == [("expert-1", placed.record_digest)]
    assert placed.record_digest != ghost.record_digest
    assert scrutiny.EXPERT_SIGNOFF_ABSENT not in scrutiny_reasons(arena, launch_)


def test_a_sign_off_row_whose_fields_disagree_with_its_digest_is_absent(arena, statement):
    placed = signoff(arena, statement.hash)
    with arena["sub"]._tx():
        arena["sub"].conn.execute(
            "INSERT INTO expert_signoffs (statement_hash, expert, gate_bundle_hash, at, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?)",
            (statement.hash, "impostor", placed.gate_bundle_hash, placed.at, placed.record_digest, placed.file_offset),
        )
    visible = scrutiny.visible_signoffs(arena["sub"], statement.hash, str(arena["attest"]))
    assert [r["expert"] for r in visible] == ["expert-1"]


def test_a_sign_off_on_another_statement_meets_nothing_here(arena, statement):
    other = factories.claim_statement(seed=24, family="toy_curve")
    claims.write_claim_statement(arena["sub"], other)
    signoff(arena, other.hash)
    launch_ = tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True)
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(arena, launch_)
    assert not scrutiny.signed_off(arena["sub"], statement.hash, str(arena["attest"]))
    assert scrutiny.signed_off(arena["sub"], other.hash, str(arena["attest"]))


def test_writing_the_same_sign_off_twice_keeps_one_row(arena, statement):
    placed = signoff(arena, statement.hash)
    again = signoff(arena, statement.hash, offset=placed.file_offset)
    assert again.record_digest == placed.record_digest
    assert len(scrutiny.signoffs_for(arena["sub"], statement.hash)) == 1


def test_a_request_raises_the_class_and_never_lowers_it(arena, statement):
    sub = arena["sub"]
    key = hypothesis(arena, family="model_curve", seed=30)
    launch_ = tier_launch(arena, 3, key=key, statement_hash=statement.hash)
    assert scrutiny_reasons(arena, launch_) == set()
    scrutiny.request(sub, key, scrutiny.TOP, assigned_class=scrutiny.ROUTINE, requested_by="human-1", at=AT)
    assert scrutiny.floor(sub, key) == scrutiny.TOP
    assert scrutiny.EXPERT_SIGNOFF_ABSENT in scrutiny_reasons(arena, launch_)
    with pytest.raises(scrutiny.LoweringRefused, match="lowers it and is refused"):
        scrutiny.request(sub, key, scrutiny.ELEVATED, assigned_class=scrutiny.ROUTINE, requested_by="human-1")
    assert scrutiny.floor(sub, key) == scrutiny.TOP
    assert sub.conn.execute("SELECT COUNT(*) FROM scrutiny_requests").fetchone()[0] == 1
    with pytest.raises(Exception, match="append-only"):
        sub.conn.execute("DELETE FROM scrutiny_requests")


def test_a_request_below_the_assigned_class_is_refused_even_with_no_prior_request(arena, statement):
    with pytest.raises(scrutiny.LoweringRefused):
        scrutiny.request(arena["sub"], arena["key"], scrutiny.ROUTINE, assigned_class=scrutiny.TOP, requested_by="h")
    assert scrutiny.floor(arena["sub"], arena["key"]) is None


def test_the_cli_attest_append_writes_a_visible_sign_off(arena, statement, tmp_path, capsys):
    arena["sub"].close()
    record = tmp_path / "signoff.json"
    record.write_text(json.dumps({"statement_hash": statement.hash, "expert": "expert-cli", "at": AT}))
    argv = [
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
        "expert_signoff",
        "--record",
        str(record),
        "--json",
    ]
    code = cli.main(argv)
    out = capsys.readouterr().out
    assert code == 0, out
    payload = json.loads(out)
    assert payload["kind"] == "expert_signoff" and payload["offset"] > 0
    sub = arena["sub"] = helpers.open_writer(tmp_path)
    visible = scrutiny.visible_signoffs(sub, statement.hash, str(arena["attest"]))
    assert [r["expert"] for r in visible] == ["expert-cli"]
    gate = TierGate(sub, arena["bundle"], attest_path=str(arena["attest"]))
    decision = gate.admit(tier_launch(arena, 3, statement_hash=statement.hash, target_attack=True))
    assert scrutiny.EXPERT_SIGNOFF_ABSENT not in decision.reasons


def test_a_malformed_sign_off_record_is_refused_by_the_cli(arena, statement, tmp_path, capsys):
    arena["sub"].close()
    record = tmp_path / "signoff.json"
    record.write_text(json.dumps({"statement_hash": statement.hash, "expert": "expert-cli"}))
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
            "expert_signoff",
            "--record",
            str(record),
            "--json",
        ]
    )
    assert code != 0
    assert "missing at" in capsys.readouterr().err
    arena["sub"] = helpers.open_writer(tmp_path)
    assert scrutiny.signoffs_for(arena["sub"], statement.hash) == []


def test_an_admission_logs_the_scrutiny_class(arena, statement, json_test_log):
    arena["gate"].admit(tier_launch(arena, 1, statement_hash=statement.hash, target_attack=True))
    records = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    admits = [r for r in records if r.get("event") == "admit"]
    assert admits and admits[-1]["scrutiny_class"] == scrutiny.TOP


def test_launch_helper_from_the_no_go_arena_still_admits(arena):
    assert launch(arena, 0, core_s=0.1).declared_tier == 0
