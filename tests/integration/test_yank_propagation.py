import sys
from pathlib import Path

import pytest

from cairn import claims, escrow, human_authority, justify, ledger, status, yank

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
import factories
from test_repro_gate import ladder_evidence, ticket_at

ATTEST = "unused-attestation-file"
AT = "2026-09-05T00:00:00.000000+00:00"
GATE_HASH = "ee" * 32
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


def authorize_yank(sub, attest_path, *, yank_id, revision, reach, ruling_ref="ruling-1"):
    Path(attest_path).touch(exist_ok=True)
    record = human_authority.append(
        sub,
        attest_path,
        human_authority.YANK_RULING,
        {
            "ruling_ref": ruling_ref,
            "yank_id": yank_id,
            "skill_identity_hash": revision,
            "reach_predicate": yank.reach_json(reach),
            "issued_by": "test-operator",
            "at": AT,
        },
        gate_bundle_hash=GATE_HASH,
    )
    return yank.Ruling(ruling_ref, record["record_digest"], record["file_offset"])


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


def test_a_human_path_yank_with_a_seed_range_leaves_the_seeds_outside_it_standing(writer, revision, tmp_path):
    attempts = attempts_by_seed(writer, revision)
    kept = statement_on(writer, attempts[3], seed=12)
    attest_path = str(tmp_path / "attest.log")
    reach = {"skill_identity_hash": revision, "seed": BAD_REACH_SEEDS}
    authority = authorize_yank(writer, attest_path, yank_id="yank-narrow", revision=revision, reach=reach)
    outcome = yank.record(
        writer,
        yank_id="yank-narrow",
        skill_identity_hash=revision,
        kind=yank.HUMAN_PATH,
        attest_path=attest_path,
        reach=reach,
        ruling=authority,
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
    assert writer.yanked(revision, attest_path=attest_path) is True
    record = yank.records_for(writer, revision, attest_path=attest_path)[0]
    status_row = next(
        item
        for item in status._skill_revisions(writer, attest_path)["revisions"]
        if item["identity_bundle_hash"] == revision
    )
    assert status_row["status"] == "yanked" and status_row["yank_reach"] == [
        {
            "yank_id": "yank-narrow",
            "predicate": reach,
            "kind": yank.HUMAN_PATH,
            "verdict_ref": None,
            "ruling_ref": authority.ruling_ref,
            "record_digest": authority.record_digest,
            "file_offset": authority.file_offset,
            "created_at": AT,
        }
    ]
    assert (record["kind"], record["ruling_ref"], record["record_digest"], record["file_offset"]) == (
        yank.HUMAN_PATH,
        authority.ruling_ref,
        authority.record_digest,
        authority.file_offset,
    )
    salt = writer.conn.execute("SELECT * FROM salts WHERE class_key = ?", (revision,)).fetchone()
    assert (salt["kind"], salt["verdict_ref"], salt["record_digest"], salt["file_offset"]) == (
        yank.HUMAN_PATH,
        None,
        authority.record_digest,
        authority.file_offset,
    )


def test_a_second_yank_advances_the_salt_and_disowns_nothing_twice(writer, revision, tmp_path):
    attempts = attempts_by_seed(writer, revision)
    attest_path = str(tmp_path / "attest.log")
    reach = {"skill_identity_hash": revision, "seed": 1}
    authority = authorize_yank(writer, attest_path, yank_id="yank-a", revision=revision, reach=reach)
    first = yank.record(
        writer,
        yank_id="yank-a",
        skill_identity_hash=revision,
        kind=yank.HUMAN_PATH,
        attest_path=attest_path,
        reach=reach,
        ruling=authority,
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
    assert yank.current_salt(writer, revision, attest_path=attest_path) == "yank-b"
    history = writer.conn.execute("SELECT seq, salt FROM salts WHERE class_key = ? ORDER BY seq", (revision,))
    assert [tuple(r) for r in history] == [(1, "yank-a"), (2, "yank-b")]
    assert escrow.reservation(writer, attempts[1])["released_at"] == AT


@pytest.mark.parametrize("mismatch", ["yank_id", "revision", "reach", "digest", "offset"])
def test_a_ruling_for_another_yank_action_refuses_before_mutation(writer, revision, tmp_path, mismatch):
    attempts = attempts_by_seed(writer, revision, seeds=(1,))
    attest_path = str(tmp_path / "attest.log")
    reach = yank.default_reach(revision)
    authority = authorize_yank(writer, attest_path, yank_id="authorized-yank", revision=revision, reach=reach)
    yank_id = "authorized-yank"
    target_revision = revision
    target_reach = reach
    target_ruling = authority
    if mismatch == "yank_id":
        yank_id = "copied-yank"
    elif mismatch == "revision":
        target_revision = writer.put_identity_bundle(helpers.IDENTITY_B)
        target_reach = yank.default_reach(target_revision)
    elif mismatch == "reach":
        target_reach = {"skill_identity_hash": revision, "seed": 1}
    elif mismatch == "digest":
        target_ruling = yank.Ruling(authority.ruling_ref, "ff" * 32, authority.file_offset)
    else:
        target_ruling = yank.Ruling(authority.ruling_ref, authority.record_digest, authority.file_offset + 1)
    with pytest.raises(yank.RulingRequired, match="no ruling for this yank action"):
        yank.record(
            writer,
            yank_id=yank_id,
            skill_identity_hash=target_revision,
            kind=yank.HUMAN_PATH,
            attest_path=attest_path,
            reach=target_reach,
            ruling=target_ruling,
            at=AT,
        )
    assert writer.conn.execute("SELECT COUNT(*) FROM yank_records").fetchone()[0] == 0
    assert writer.conn.execute("SELECT COUNT(*) FROM salts").fetchone()[0] == 0
    assert writer.get_attempt(attempts[1])["disowned_at"] is None
    assert escrow.standing(writer, attempts[1])


def test_a_fake_human_ruling_writes_nothing(writer, revision, tmp_path):
    attempts = attempts_by_seed(writer, revision, seeds=(1,))
    attest_path = tmp_path / "attest.log"
    attest_path.touch()
    with pytest.raises(yank.RulingRequired, match="no ruling for this yank action"):
        yank.record(
            writer,
            yank_id="planted-human-yank",
            skill_identity_hash=revision,
            kind=yank.HUMAN_PATH,
            attest_path=attest_path,
            ruling=yank.Ruling("planted-ruling", "bb" * 32, 0),
            at=AT,
        )
    assert writer.yanked(revision, attest_path=attest_path) is False
    assert yank.current_salt(writer, revision, attest_path=attest_path) is None
    assert writer.get_attempt(attempts[1])["disowned_at"] is None
    assert escrow.standing(writer, attempts[1])


def test_standalone_salt_requires_and_exposes_its_own_authority(writer, revision, tmp_path):
    attest_path = str(tmp_path / "attest.log")
    record = human_authority.append(
        writer,
        attest_path,
        human_authority.SALT_ISSUANCE,
        {"class_key": revision, "salt": "issued-salt", "issued_by": "test-operator", "at": AT},
        gate_bundle_hash=GATE_HASH,
    )
    assert (
        yank.issue_salt(
            writer,
            class_key=revision,
            salt="issued-salt",
            record_digest=record["record_digest"],
            file_offset=record["file_offset"],
            attest_path=attest_path,
        )
        == "issued-salt"
    )
    assert yank.current_salt(writer, revision, attest_path=attest_path) == "issued-salt"
    with pytest.raises(yank.RulingRequired, match="no issuance for this salt"):
        yank.issue_salt(
            writer,
            class_key=revision,
            salt="forged-salt",
            record_digest=record["record_digest"],
            file_offset=record["file_offset"],
            attest_path=attest_path,
        )


def test_planted_human_rows_are_absent_from_yank_readers(writer, revision, tmp_path):
    key = writer.put_recipe(helpers.recipe(seed=1, skill_identity_hash=revision))
    writer.conn.execute(
        "INSERT INTO yank_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "planted",
            revision,
            yank.reach_json(yank.default_reach(revision)),
            yank.HUMAN_PATH,
            None,
            "planted-ruling",
            "dd" * 32,
            0,
            AT,
        ),
    )
    writer.conn.execute(
        "INSERT INTO salts (class_key, salt, kind, verdict_ref, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?)",
        (revision, "planted", yank.HUMAN_PATH, None, "dd" * 32, 0),
    )
    attest_path = tmp_path / "attest.log"
    attest_path.touch()
    assert yank.records_for(writer, revision, attest_path=attest_path) == []
    assert writer.yanked(revision, attest_path=attest_path) is False
    assert yank.current_salt(writer, revision, attest_path=attest_path) is None
    assert yank.covers_recipe(writer, key, attest_path=attest_path) is False
    rows = status._skill_revisions(writer, attest_path)
    row = next(item for item in rows["revisions"] if item["identity_bundle_hash"] == revision)
    assert row["status"] != "yanked" and row["yank_reach"] == []


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
        result={
            "kind": "statistical_interval",
            "quantity": "mean_group_operations",
            "summary": "in-sample model miss",
            "value": "1310000000",
            "ci": ["1200000000", "1400000000"],
            "ci_method": "normal_mean",
            "coverage": "0.95",
        },
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


class Injected(RuntimeError):
    pass


@pytest.mark.parametrize("failing", ["add_salt", "disown"])
def test_a_failure_partway_through_the_propagation_leaves_no_row_behind(writer, revision, monkeypatch, failing):
    attempts = attempts_by_seed(writer, revision)
    stmt = statement_on(writer, attempts[1])
    verdict = recorded_verdict(writer)

    def refuse(*args, **kwargs):
        raise Injected(f"injected at {failing}")

    monkeypatch.setattr(writer, failing, refuse)
    with pytest.raises(Injected):
        yank.record(
            writer,
            yank_id="yank-1",
            skill_identity_hash=revision,
            kind=yank.GATE_VERDICT,
            attest_path=ATTEST,
            verdict_ref=verdict,
            at=AT,
        )
    monkeypatch.undo()

    assert yank.records_for(writer, revision) == []
    assert yank.current_salt(writer, revision) is None
    assert writer.yanked(revision) is False
    for attempt_id in attempts.values():
        assert writer.get_attempt(attempt_id)["disowned_at"] is None
        assert escrow.reservation(writer, attempt_id)["released_at"] is None
    assert justify.derive_tag(writer, stmt.hash, ATTEST).tag == justify.CONJECTURE


def test_the_whole_propagation_lands_again_after_a_failed_attempt(writer, revision, monkeypatch):
    attempts = attempts_by_seed(writer, revision)
    verdict = recorded_verdict(writer)

    def refuse(*args, **kwargs):
        raise Injected("injected at add_salt")

    monkeypatch.setattr(writer, "add_salt", refuse)
    with pytest.raises(Injected):
        yank.record(
            writer,
            yank_id="yank-1",
            skill_identity_hash=revision,
            kind=yank.GATE_VERDICT,
            attest_path=ATTEST,
            verdict_ref=verdict,
            at=AT,
        )
    monkeypatch.undo()

    outcome = yank.record(
        writer,
        yank_id="yank-1",
        skill_identity_hash=revision,
        kind=yank.GATE_VERDICT,
        attest_path=ATTEST,
        verdict_ref=verdict,
        at=AT,
    )
    assert set(outcome.disowned) == set(attempts.values())
    assert yank.current_salt(writer, revision) == "yank-1"
    assert len(yank.records_for(writer, revision)) == 1
