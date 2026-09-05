import sys
from pathlib import Path

import pytest

from cairn import claims, escrow, justify, ledger, yank

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories
from test_repro_gate import ladder_evidence, ticket_at

ATTEST = "unused-attestation-file"
AT = "2026-09-05T00:00:00.000000+00:00"
PAYLOAD = {"out.json": b'{"x": 1}'}
BAD_REACH_SEEDS = [1, 2]


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def revision(writer):
    identity = writer.put_identity_bundle(helpers.IDENTITY_A)
    writer.put_certificate(identity, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return identity


def attempts_by_seed(writer, revision, seeds=(1, 2, 3)):
    out = {}
    for seed in seeds:
        key = writer.put_recipe(helpers.recipe(seed=seed, skill_identity_hash=revision))
        attempt_id, _ = helpers.launch(writer, key, payloads=PAYLOAD)
        writer.add_escrow(
            attempt_id,
            declared_production_cost=1.0,
            declared_verification_cost=0.5,
            reserved=0.5,
            ceiling_multiplier=4.0,
        )
        out[seed] = attempt_id
    return out


def statement_on(writer, attempt_id, seed=11):
    stmt = factories.claim_statement(seed=seed)
    claims.write_claim_statement(writer, stmt)
    ticket_at(writer, stmt, 1)
    ladder_evidence(writer, stmt, attempt_id, repro_record=factories.repro_record(attempt_id))
    assert justify.derive_tag(writer, stmt.hash, ATTEST).tag == justify.CONJECTURE
    return stmt


def recorded_verdict(writer):
    run = factories.gate_run(result="refused", reasons=("verifier-mismatch",), seed=5)
    claims.write_gate_run(writer, run)
    return run.hash


def ruling(seed=1):
    return yank.Ruling(ruling_ref=f"ruling-{seed}", record_digest=f"{seed:02x}" * 32, file_offset=seed * 64)


def test_a_gate_verdict_yank_disowns_the_whole_revision_and_bumps_the_salt(writer, revision, db_snapshot):
    attempts = attempts_by_seed(writer, revision)
    stmt = statement_on(writer, attempts[1])
    outcome = yank.record(
        writer,
        yank_id="yank-1",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=recorded_verdict(writer),
        at=AT,
    )
    db_snapshot(writer.conn, "gate-verdict-yank")
    assert set(outcome.disowned) == set(attempts.values()) and outcome.standing == ()
    assert set(outcome.released) == set(attempts.values())
    assert outcome.rederived == (stmt.hash,)
    assert writer.yanked(revision) is True
    assert yank.current_salt(writer, revision) == "yank-1" == outcome.salt
    for attempt_id in attempts.values():
        assert writer.get_attempt(attempt_id)["disowned_at"] == AT
        row = escrow.reservation(writer, attempt_id)
        assert row["released_by"] == escrow.RELEASE_DISOWNED and row["released_at"] == AT
    record = yank.records_for(writer, revision)[0]
    assert record["kind"] == yank.GATE_VERDICT and record["ruling_ref"] is None and record["record_digest"] is None
    assert yank.reach_from_json(record["reach_predicate"]) == yank.default_reach(revision)
    derived = justify.derive_tag(writer, stmt.hash, ATTEST)
    assert derived.tag == justify.SPECULATION
    assert isinstance(derived.results[0][1], justify.Absent) and derived.results[0][1].reason == "disowned"


def test_a_disowned_node_is_no_ticket(writer, revision):
    attempts = attempts_by_seed(writer, revision, seeds=(1,))
    assert yank.offer_as_ticket(writer, attempts[1])["attempt_id"] == attempts[1]
    yank.record(
        writer,
        yank_id="yank-1",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=recorded_verdict(writer),
    )
    with pytest.raises(yank.DisownedTicket, match="is no ticket"):
        yank.offer_as_ticket(writer, attempts[1])
    with pytest.raises(yank.UnknownAttempt):
        yank.offer_as_ticket(writer, "ghost")


def test_a_failed_attempt_is_no_ticket_either(writer, revision):
    key = writer.put_recipe(helpers.recipe(seed=1, skill_identity_hash=revision))
    failed, _ = helpers.launch(writer, key, "FAIL")
    with pytest.raises(yank.YankError, match="only an OK attempt is a ticket"):
        yank.offer_as_ticket(writer, failed)


def test_a_human_path_yank_with_a_seed_range_leaves_the_seeds_outside_it_standing(writer, revision):
    attempts = attempts_by_seed(writer, revision)
    kept = statement_on(writer, attempts[3], seed=12)
    outcome = yank.record(
        writer,
        yank_id="yank-narrow",
        skill_identity_hash=revision,
        kind=yank.HUMAN_PATH,
        attest_path=ATTEST,
        reach={"skill_identity_hash": revision, "seed": BAD_REACH_SEEDS},
        ruling=ruling(1),
        at=AT,
    )
    assert set(outcome.disowned) == {attempts[1], attempts[2]}
    assert outcome.standing == (attempts[3],)
    assert outcome.rederived == ()
    assert writer.get_attempt(attempts[3])["disowned_at"] is None
    assert escrow.standing(writer, attempts[3])
    assert justify.derive_tag(writer, kept.hash, ATTEST).tag == justify.CONJECTURE
    served = {seed: writer.serve(writer.get_attempt(a)["recipe_key"]) for seed, a in attempts.items()}
    assert served[1] is None and served[2] is None
    assert served[3] is not None and served[3].attempt_id == attempts[3]
    assert writer.yanked(revision) is True
    record = yank.records_for(writer, revision)[0]
    assert (record["kind"], record["ruling_ref"], record["record_digest"], record["file_offset"]) == (
        yank.HUMAN_PATH,
        "ruling-1",
        "01" * 32,
        64,
    )
    salt = writer.conn.execute("SELECT * FROM salts WHERE class_key = ?", (revision,)).fetchone()
    assert (salt["kind"], salt["verdict_ref"], salt["record_digest"], salt["file_offset"]) == (
        yank.HUMAN_PATH,
        None,
        "01" * 32,
        64,
    )


def test_a_second_yank_advances_the_salt_and_disowns_nothing_twice(writer, revision):
    attempts = attempts_by_seed(writer, revision)
    first = yank.record(
        writer,
        yank_id="yank-a",
        skill_identity_hash=revision,
        kind=yank.HUMAN_PATH,
        attest_path=ATTEST,
        reach={"skill_identity_hash": revision, "seed": 1},
        ruling=ruling(1),
        at=AT,
    )
    second = yank.record(
        writer,
        yank_id="yank-b",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=recorded_verdict(writer),
    )
    assert first.disowned == (attempts[1],) and set(second.disowned) == {attempts[2], attempts[3]}
    assert second.released == second.disowned
    assert yank.current_salt(writer, revision) == "yank-b"
    history = writer.conn.execute("SELECT seq, salt FROM salts WHERE class_key = ? ORDER BY seq", (revision,))
    assert [tuple(r) for r in history] == [(1, "yank-a"), (2, "yank-b")]
    assert escrow.reservation(writer, attempts[1])["released_at"] == AT


def test_a_yank_on_another_revision_touches_nothing_here(writer, revision):
    attempts = attempts_by_seed(writer, revision)
    other = writer.put_identity_bundle(helpers.IDENTITY_B)
    outcome = yank.record(
        writer,
        yank_id="yank-other",
        skill_identity_hash=other,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=recorded_verdict(writer),
    )
    assert outcome.disowned == () and outcome.standing == () and outcome.released == ()
    assert all(writer.get_attempt(a)["disowned_at"] is None for a in attempts.values())
    assert all(writer.serve(writer.get_attempt(a)["recipe_key"]).attempt_id == a for a in attempts.values())
    assert writer.yanked(revision) is False and writer.yanked(other) is True
    assert yank.current_salt(writer, revision) is None


@pytest.mark.parametrize(
    ("kind", "extra", "error", "match"),
    [
        (yank.GATE_VERDICT, {}, yank.VerdictRefRequired, "names the gate run or ledger entry"),
        (yank.GATE_VERDICT, {"verdict_ref": "no-such-run"}, yank.UnknownVerdictRef, "is recorded"),
        (yank.GATE_VERDICT, {"ruling": ruling(1)}, yank.YankError, "carries no ruling"),
        (
            yank.GATE_VERDICT,
            {"verdict_ref": "RECORDED", "reach": {"skill_identity_hash": "REVISION", "seed": 1}},
            yank.ReachRulingRequired,
            "attributed human ruling",
        ),
        (yank.HUMAN_PATH, {}, yank.RulingRequired, "names an attributed ruling"),
        (yank.HUMAN_PATH, {"verdict_ref": "RECORDED"}, yank.YankError, "names its ruling"),
        (
            yank.HUMAN_PATH,
            {"ruling": yank.Ruling(ruling_ref="", record_digest="00" * 32, file_offset=0)},
            yank.RulingRequired,
            "carries ruling_ref",
        ),
        (
            yank.HUMAN_PATH,
            {"ruling": yank.Ruling(ruling_ref="r", record_digest="00" * 32, file_offset=-1)},
            yank.RulingRequired,
            "non-negative int",
        ),
        ("discretionary", {}, yank.YankError, "kind must be one of"),
        (yank.GATE_VERDICT, {"verdict_ref": "RECORDED", "reach": {"seed": 1}}, yank.MalformedReach, "yanked revision"),
    ],
)
def test_a_yank_without_its_authority_writes_nothing(writer, revision, kind, extra, error, match):
    attempts = attempts_by_seed(writer, revision, seeds=(1,))
    verdict = recorded_verdict(writer)
    extra = dict(extra)
    if extra.get("verdict_ref") == "RECORDED":
        extra["verdict_ref"] = verdict
    if "reach" in extra and extra["reach"].get("skill_identity_hash") == "REVISION":
        extra["reach"] = {**extra["reach"], "skill_identity_hash": revision}
    with pytest.raises(error, match=match):
        yank.record(writer, yank_id="yank-x", skill_identity_hash=revision, kind=kind, attest_path=ATTEST, **extra)
    assert writer.yanked(revision) is False
    assert yank.current_salt(writer, revision) is None
    assert writer.get_attempt(attempts[1])["disowned_at"] is None
    assert escrow.standing(writer, attempts[1])


def test_a_ledger_entry_hash_is_a_recorded_verdict_too(writer, revision):
    stmt = factories.claim_statement(cost_model=True, seed=5)
    claims.write_claim_statement(writer, stmt)
    hyp = factories.hypothesis_object(claim_statement_hash=stmt.hash, seed=5)
    claims.write_hypothesis_object(writer, hyp)
    node = factories.evidence_node(
        "ladder_table",
        stmt.hash,
        stmt.scope,
        stmt.scope["assumption_set"],
        verdict="REJECT",
        seed=1,
        producer=(revision, "skill"),
    )
    claims.write_evidence_node(writer, node)
    entry = ledger.write(
        writer,
        hypothesis_key=hyp.hash,
        decision=ledger.REFUTED,
        refutation_kind=ledger.MEASURED,
        evidence_node=node.hash,
        method=hyp.method_identity,
        measured_points=({"numeric": {"bits": 50, "trials": 40}, "categorical": {"model": "c_sqrt_n"}},),
        result={"summary": "in-sample model miss", "value": "1310000000", "ci": ["1200000000", "1400000000"]},
        caught_by="ladder:in_sample_model_miss",
        at=AT,
    )
    assert yank.verdict_recorded(writer, entry)
    assert yank.verdict_recorded(writer, recorded_verdict(writer))
    assert not yank.verdict_recorded(writer, "ff" * 32)
    attempts = attempts_by_seed(writer, revision, seeds=(1,))
    outcome = yank.record(
        writer,
        yank_id="yank-ledger",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        verdict_ref=entry,
        attest_path=ATTEST,
    )
    assert outcome.disowned == (attempts[1],)
    assert yank.records_for(writer, revision)[0]["verdict_ref"] == entry


def test_a_yank_id_is_written_once(writer, revision):
    verdict = recorded_verdict(writer)
    yank.record(
        writer,
        yank_id="yank-1",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=verdict,
    )
    with pytest.raises(Exception, match="UNIQUE"):
        yank.record(
            writer,
            yank_id="yank-1",
            skill_identity_hash=revision,
            kind=yank.GATE_VERDICT,
            attest_path=ATTEST,
            verdict_ref=verdict,
        )
    assert len(yank.records_for(writer, revision)) == 1
