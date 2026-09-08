import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from cairn import attest, claims, disagreement, exits, human_queue, justify, keys
from cairn.justify import CONJECTURE, PROVEN, SPECULATION, STRONG_EMPIRICAL

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories
from _substrate_helpers import (
    ENV_MANIFEST_HASH,
    IDENTITY_A,
    TRANSCRIPT_HASH,
    open_writer,
    recipe,
)

WAIVER_TARGET = "f" * 64
COVERING_CROSS_CHECK = {"axis": "algorithm", "independent_range": {"bits": [0, 60]}}
AUTHOR_ORIGINS = {"F5": {"P": "author_supplied", "p": "author_supplied"}}


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, WAIVER_TARGET)
    return path


def _statement(writer, **kw):
    statement = factories.claim_statement(seed=kw.pop("seed", 1), **kw)
    claims.write_claim_statement(writer, statement)
    return statement


def _wide_population(statement, size=(30, 60)):
    return {
        **statement.scope,
        "size_interval": list(size),
        "param_ranges": {"bits": list(size)},
    }


def _append_verdict(writer, attest_path, statement_hash, verdict="approve"):
    unplaced = factories.review_verdict(statement_hash, verdict=verdict, seed=3)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    placed = factories.review_verdict(statement_hash, verdict=verdict, seed=3, file_offset=offset)
    claims.write_review_verdict(writer, placed)
    return offset


def _certify(writer, revision, summary):
    identity = writer.put_identity_bundle({**IDENTITY_A, "implementation_revision": revision})
    writer.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, summary)
    return identity


def _ladder(
    writer,
    statement,
    population,
    *,
    repro=True,
    verdict="KEEP",
    in_sample=None,
    attempt_id=None,
    replay_grade="Replayable",
    seed=0,
    **kw,
):
    rng_attempt = attempt_id or f"attempt-{seed:08x}"
    record = factories.repro_record(rng_attempt, passed=bool(repro))
    if repro is not None:
        claims.write_repro_record(writer, record)
    node = factories.evidence_node(
        "ladder_table",
        statement.hash,
        population,
        frozenset(population["assumption_set"]),
        verdict=verdict,
        repro=None if repro is None else record,
        seed=seed,
        attempt_id=rng_attempt,
        in_sample_sizes=list(in_sample or population["size_interval"]),
        **kw,
    )
    claims.write_evidence_node(writer, node, replay_grade=replay_grade)
    return node


def case_ladder_keep_covering_with_passed_repro(writer, attest_path):
    statement = _statement(writer)
    node = _ladder(writer, statement, _wide_population(statement))
    return statement, node, None


def case_repro_absent(writer, attest_path):
    statement = _statement(writer, seed=2)
    node = _ladder(writer, statement, _wide_population(statement), repro=None, seed=2)
    return statement, node, None


def case_repro_failed(writer, attest_path):
    statement = _statement(writer, seed=3)
    node = _ladder(writer, statement, _wide_population(statement), repro=False, seed=3)
    return statement, node, None


def case_grade_audit_only(writer, attest_path):
    statement = _statement(writer, seed=4)
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=4,
        replay_grade=justify.AUDIT_ONLY,
    )
    return statement, node, None


def case_population_narrower_than_scope(writer, attest_path):
    statement = _statement(writer, seed=5)
    node = _ladder(writer, statement, _wide_population(statement, size=(40, 50)), seed=5)
    return statement, node, None


def case_extra_assumption(writer, attest_path):
    statement = _statement(writer, seed=6)
    population = {
        **_wide_population(statement),
        "assumption_set": factories.assumption_ids({"A1", "A2"}),
    }
    node = _ladder(writer, statement, population, seed=6)
    return statement, node, None


def case_family_mismatch(writer, attest_path):
    statement = _statement(writer, seed=7)
    population = {**_wide_population(statement), "target_family": "other_curve"}
    node = _ladder(writer, statement, population, seed=7)
    return statement, node, None


def case_statistical_offered_for_proven(writer, attest_path):
    statement = _statement(writer, seed=8)
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=8,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, PROVEN


def case_statistical_for_a_cost_model_statement(writer, attest_path):
    statement = _statement(writer, seed=9, cost_model=True)
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=9,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_keep_in_sample_covering(writer, attest_path):
    statement = _statement(writer, seed=10)
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=10,
        verdict="KEEP_IN_SAMPLE",
        in_sample=(30, 50),
    )
    return statement, node, None


def case_keep_in_sample_not_covering(writer, attest_path):
    statement = _statement(writer, seed=11)
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=11,
        verdict="KEEP_IN_SAMPLE",
        in_sample=(30, 45),
    )
    return statement, node, None


def case_lean_artifact_with_matching_verdict(writer, attest_path):
    statement = _statement(writer, seed=12)
    _append_verdict(writer, attest_path, statement.hash)
    node = factories.evidence_node(
        "lean_artifact",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=12,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_lean_artifact_with_a_reject_verdict(writer, attest_path):
    statement = _statement(writer, seed=18)
    _append_verdict(writer, attest_path, statement.hash, verdict="reject")
    node = factories.evidence_node(
        "lean_artifact",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=18,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_lean_artifact_with_forged_digest(writer, attest_path):
    statement = _statement(writer, seed=13)
    claims.write_review_verdict(writer, factories.review_verdict(statement.hash, seed=13, file_offset=0))
    node = factories.evidence_node(
        "lean_artifact",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=13,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_lean_artifact_with_forged_verdict_fields(writer, attest_path):
    statement = _statement(writer, seed=19)
    offset = _append_verdict(writer, attest_path, statement.hash, verdict="reject")
    honest = factories.review_verdict(statement.hash, verdict="reject", seed=3, file_offset=offset)
    writer.conn.execute(
        "INSERT INTO review_verdicts (statement_hash, reviewer, verdict, checklist_template_hash, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            statement.hash,
            honest.reviewer,
            "approve",
            honest.checklist_template_hash,
            honest.gate_bundle_hash,
            honest.at,
            None,
            honest.record_digest,
            offset,
        ),
    )
    writer.conn.commit()
    assert [r["verdict"] for r in claims.review_verdicts_for(writer, statement.hash)] == ["reject", "approve"]
    node = factories.evidence_node(
        "lean_artifact",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=19,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_disowned_ladder_table(writer, attest_path):
    statement = _statement(writer, seed=14)
    attempt_id = writer.start_attempt(keys.recipe_key(recipe(seed=14)))
    writer.close_attempt(attempt_id, "OK")
    writer.disown(attempt_id)
    node = _ladder(writer, statement, _wide_population(statement), seed=14, attempt_id=attempt_id)
    return statement, node, None


def case_author_supplied_producer(writer, attest_path):
    statement = _statement(writer, seed=15)
    identity = _certify(writer, "1a" * 32, factories.selftest_summary(AUTHOR_ORIGINS, False, None))
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=15,
        producer=(identity, "skill"),
    )
    return statement, node, None


def case_producer_with_a_covering_cross_check(writer, attest_path):
    statement = _statement(writer, seed=16)
    identity = _certify(
        writer,
        "2b" * 32,
        factories.selftest_summary(AUTHOR_ORIGINS, False, COVERING_CROSS_CHECK),
    )
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=16,
        producer=(identity, "skill"),
    )
    return statement, node, None


def case_gate_producer_is_never_capped(writer, attest_path):
    statement = _statement(writer, seed=19)
    identity = _certify(writer, "3c" * 32, factories.selftest_summary(AUTHOR_ORIGINS, False, None))
    node = _ladder(
        writer,
        statement,
        _wide_population(statement),
        seed=19,
        producer=(identity, "gate"),
    )
    return statement, node, None


def case_a_node_carrying_no_attempt(writer, attest_path):
    statement = _statement(writer, seed=25)
    node = factories.evidence_node(
        "repro_node",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=25,
        attempt_id=None,
    )
    claims.write_evidence_node(writer, node)
    return statement, node, None


def case_refuted_statement_with_a_keep_table(writer, attest_path):
    statement = _statement(writer, seed=17)
    node = _ladder(writer, statement, _wide_population(statement), seed=17)
    claims.transition_status(writer, statement.hash, "refuted")
    return statement, node, None


DONE_WHEN = [
    (
        case_ladder_keep_covering_with_passed_repro,
        "Justification",
        STRONG_EMPIRICAL,
        STRONG_EMPIRICAL,
    ),
    (case_repro_absent, "Justification", CONJECTURE, CONJECTURE),
    (case_repro_failed, "Justification", CONJECTURE, CONJECTURE),
    (case_grade_audit_only, "Absent", justify.REASON_AUDIT_ONLY, SPECULATION),
    (
        case_population_narrower_than_scope,
        "CoverageViolation",
        "size_interval",
        SPECULATION,
    ),
    (case_extra_assumption, "CoverageViolation", "assumptions", SPECULATION),
    (case_family_mismatch, "CoverageViolation", "target_family", SPECULATION),
    (
        case_statistical_offered_for_proven,
        "LatticeViolation",
        "statistical-cannot-justify-PROVEN",
        STRONG_EMPIRICAL,
    ),
    (
        case_statistical_for_a_cost_model_statement,
        "Justification",
        CONJECTURE,
        CONJECTURE,
    ),
    (case_keep_in_sample_covering, "Justification", STRONG_EMPIRICAL, STRONG_EMPIRICAL),
    (
        case_keep_in_sample_not_covering,
        "Absent",
        "table-verdict-KEEP_IN_SAMPLE",
        SPECULATION,
    ),
    (case_lean_artifact_with_matching_verdict, "Justification", PROVEN, PROVEN),
    (case_lean_artifact_with_a_reject_verdict, "Pending", "human_review", SPECULATION),
    (case_lean_artifact_with_forged_digest, "Pending", "human_review", SPECULATION),
    (case_lean_artifact_with_forged_verdict_fields, "Pending", "human_review", SPECULATION),
    (case_disowned_ladder_table, "Absent", "disowned", SPECULATION),
    (case_author_supplied_producer, "Justification", CONJECTURE, CONJECTURE),
    (
        case_producer_with_a_covering_cross_check,
        "Justification",
        STRONG_EMPIRICAL,
        STRONG_EMPIRICAL,
    ),
    (case_gate_producer_is_never_capped, "Justification", STRONG_EMPIRICAL, STRONG_EMPIRICAL),
    (case_a_node_carrying_no_attempt, "Justification", STRONG_EMPIRICAL, STRONG_EMPIRICAL),
    (
        case_refuted_statement_with_a_keep_table,
        "LatticeViolation",
        "refuted-statement",
        SPECULATION,
    ),
]


@pytest.mark.parametrize(
    ("build", "result_type", "detail", "tag"),
    DONE_WHEN,
    ids=[build.__name__.removeprefix("case_") for build, *_ in DONE_WHEN],
)
def test_the_done_when_set(writer, attest_path, db_snapshot, build, result_type, detail, tag):
    statement, node, offered = build(writer, attest_path)
    row = claims.get_evidence_node(writer, node.hash)
    stored = claims.get_claim_statement(writer, statement.hash)
    ctx = justify.context_for(writer, row, stored, attest_path, offered_class=offered)
    result = justify.justify(row, stored, ctx)
    assert type(result).__name__ == result_type
    assert (getattr(result, "cls", None) or getattr(result, "field", None) or getattr(result, "reason", None)) == detail

    derived = justify.derive_tag(writer, statement.hash, attest_path)
    db_snapshot(writer.conn, "after-derive")
    assert derived.tag == tag
    assert claims.tag_history_for(writer, statement.hash)[-1]["to_tag"] == tag


def test_a_waiver_naming_the_statement_moves_no_tag(writer, attest_path, db_snapshot):
    statement = _statement(writer, seed=20)
    _ladder(writer, statement, _wide_population(statement), seed=20)
    first = justify.derive_tag(writer, statement.hash, attest_path)
    before = db_snapshot(writer.conn, "before-waiver")

    waiver = {
        "kind": "waiver",
        "target_kind": "claim_statement",
        "target": statement.hash,
        "check": "tier_gate",
        "reason": "operator waiver",
        "issued_by": "operator",
        "expires_at": "2027-01-01T00:00:00Z",
    }
    attest.append_record(attest_path, attest.waiver_canonical(waiver))

    second = justify.derive_tag(writer, statement.hash, attest_path)
    after = db_snapshot(writer.conn, "after-waiver")
    assert second.tag == first.tag == STRONG_EMPIRICAL
    assert not second.appended
    assert after["tag_history"] == before["tag_history"]
    assert len(list(attest.records(attest_path))) == 2


def test_tag_history_holds_one_row_per_transition_and_refuses_update(writer, attest_path):
    statement = _statement(writer, seed=21)
    justify.derive_tag(writer, statement.hash, attest_path)
    justify.derive_tag(writer, statement.hash, attest_path)
    assert [row["to_tag"] for row in claims.tag_history_for(writer, statement.hash)] == [SPECULATION]

    _ladder(writer, statement, _wide_population(statement), seed=21)
    justify.derive_tag(writer, statement.hash, attest_path)
    justify.derive_tag(writer, statement.hash, attest_path)
    history = claims.tag_history_for(writer, statement.hash)
    assert [row["to_tag"] for row in history] == [SPECULATION, STRONG_EMPIRICAL]
    assert [row["actor"] for row in history] == ["gate:justify", "gate:justify"]
    assert history[-1]["evidence_hash"] is not None

    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        writer.conn.execute(
            "UPDATE tag_history SET to_tag = ? WHERE seq = ?",
            (SPECULATION, history[-1]["seq"]),
        )


def test_a_downgrade_carries_the_refuting_evidence_and_moves_the_statement_to_refuted(writer, attest_path):
    statement = _statement(writer, seed=22)
    _ladder(writer, statement, _wide_population(statement), seed=22)
    assert justify.derive_tag(writer, statement.hash, attest_path).tag == STRONG_EMPIRICAL

    hunt = factories.evidence_node(
        "counterexample_hunt_record",
        statement.hash,
        {**statement.scope, "size_interval": [40, 40], "param_ranges": {"bits": [40, 40]}},
        frozenset({"A1"}),
        verdict="KILLED",
        seed=22,
    )
    claims.write_evidence_node(writer, hunt)
    derived = justify.derive_tag(writer, statement.hash, attest_path)

    assert derived.tag == SPECULATION and derived.refuted_by == hunt.hash
    assert derived.justified_by == hunt.hash
    assert claims.get_claim_statement(writer, statement.hash)["status"] == "refuted"
    last = claims.tag_history_for(writer, statement.hash)[-1]
    assert last["from_tag"] == STRONG_EMPIRICAL and last["evidence_hash"] == hunt.hash


def test_an_out_of_scope_counterexample_does_not_downgrade_the_statement(writer, attest_path):
    statement = _statement(writer, seed=22)
    _ladder(writer, statement, _wide_population(statement), seed=22)
    assert justify.derive_tag(writer, statement.hash, attest_path).tag == STRONG_EMPIRICAL
    hunt = factories.evidence_node(
        "counterexample_hunt_record",
        statement.hash,
        {**statement.scope, "size_interval": [60, 60], "param_ranges": {"bits": [60, 60]}},
        frozenset({"A1"}),
        verdict="KILLED",
        seed=22,
    )
    claims.write_evidence_node(writer, hunt)

    derived = justify.derive_tag(writer, statement.hash, attest_path)

    assert derived.tag == STRONG_EMPIRICAL
    assert derived.refuted_by is None
    assert claims.get_claim_statement(writer, statement.hash)["status"] == "open"


def test_every_justify_call_logs_one_record(writer, attest_path, json_test_log):
    statement = _statement(writer, seed=23)
    ladder = _ladder(writer, statement, _wide_population(statement), seed=23)
    model = factories.evidence_node(
        "model_proof",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=23,
    )
    claims.write_evidence_node(writer, model)

    justify.derive_tag(writer, statement.hash, attest_path)
    records = [json.loads(line) for line in json_test_log.read_text().splitlines()]
    justified = [r for r in records if r["event"] == "justify" and r["step"] == "justify"]
    derived = [r for r in records if r["event"] == "derive_tag"]
    assert len(justified) == 2
    assert {(r["evidence"], r["kind"], r["result"], r["detail"]) for r in justified} == {
        (ladder.hash, "ladder_table", "Justification", STRONG_EMPIRICAL),
        (model.hash, "model_proof", "Justification", CONJECTURE),
    }
    assert {r["statement"] for r in justified} == {statement.hash}
    assert len(derived) == 1 and derived[0]["to_tag"] == STRONG_EMPIRICAL


def test_derive_tag_on_an_unknown_statement_raises(writer, attest_path):
    with pytest.raises(claims.UnknownStatement):
        justify.derive_tag(writer, "9" * 64, attest_path)


def test_the_strongest_covering_node_wins_and_a_weaker_one_never_lowers_it(writer, attest_path):
    statement = _statement(writer, seed=24)
    claims.write_evidence_node(
        writer,
        factories.evidence_node(
            "model_proof",
            statement.hash,
            _wide_population(statement),
            frozenset({"A1"}),
            seed=24,
        ),
    )
    assert justify.derive_tag(writer, statement.hash, attest_path).tag == CONJECTURE

    _ladder(writer, statement, _wide_population(statement), seed=124)
    assert justify.derive_tag(writer, statement.hash, attest_path).tag == STRONG_EMPIRICAL

    claims.write_evidence_node(
        writer,
        factories.evidence_node(
            "model_proof",
            statement.hash,
            _wide_population(statement),
            frozenset({"A1"}),
            seed=224,
        ),
    )
    assert justify.derive_tag(writer, statement.hash, attest_path).tag == STRONG_EMPIRICAL


def _cli(argv, capsys):
    from cairn import cli

    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def cli_db(tmp_path, attest_path):
    db = tmp_path / "cli.sqlite"
    with open_writer(tmp_path, "cli.sqlite") as sub:
        statement = _statement(sub, seed=30)
        node = _ladder(sub, statement, _wide_population(statement), seed=30)
    return db, statement, node


def test_the_cli_prints_the_derived_tag_and_the_justifying_evidence(cli_db, attest_path, capsys):
    db, statement, node = cli_db
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            statement.hash,
            "--db",
            str(db),
            "--attest",
            str(attest_path),
        ],
        capsys,
    )
    assert code == exits.OK
    assert out.splitlines() == [
        f"{statement.hash} {STRONG_EMPIRICAL} {node.hash}",
        f"- ladder_table {node.hash} Justification {STRONG_EMPIRICAL}",
    ]


def test_the_cli_json_is_one_document_naming_every_evidence_node(cli_db, attest_path, capsys):
    db, statement, node = cli_db
    weak = factories.evidence_node(
        "model_proof",
        statement.hash,
        _wide_population(statement),
        frozenset({"A1"}),
        seed=31,
    )
    with open_writer(db.parent, "cli.sqlite") as sub:
        claims.write_evidence_node(sub, weak)
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            statement.hash,
            "--db",
            str(db),
            "--attest",
            str(attest_path),
            "--json",
        ],
        capsys,
    )
    assert code == exits.OK and out.count("\n") == 1
    document = json.loads(out)
    assert document["schema_version"] == 1 and document["command"] == "justify"
    assert document["statement_hash"] == statement.hash
    assert document["tag"] == STRONG_EMPIRICAL and document["justified_by"] == node.hash
    assert {(row["hash"], row["kind"], row["result"]) for row in document["evidence"]} == {
        (node.hash, "ladder_table", "Justification"),
        (weak.hash, "model_proof", "Justification"),
    }


def test_a_statement_with_no_evidence_exits_zero_at_speculation(tmp_path, attest_path, capsys):
    db = tmp_path / "empty.sqlite"
    with open_writer(tmp_path, "empty.sqlite") as sub:
        statement = _statement(sub, seed=32)
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            statement.hash,
            "--db",
            str(db),
            "--attest",
            str(attest_path),
            "--json",
        ],
        capsys,
    )
    assert code == exits.OK
    assert json.loads(out)["tag"] == SPECULATION and json.loads(out)["evidence"] == []


def test_an_unknown_statement_hash_exits_user_input(cli_db, attest_path, capsys):
    db, _, _ = cli_db
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            "0" * 64,
            "--db",
            str(db),
            "--attest",
            str(attest_path),
        ],
        capsys,
    )
    assert code == exits.USER_INPUT and out == ""
    assert "no claim statement" in err and "cairn m0-run" in err


def test_a_substrate_that_cannot_be_opened_exits_environment(tmp_path, attest_path, capsys):
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            "0" * 64,
            "--db",
            str(tmp_path / "absent" / "s.sqlite"),
            "--attest",
            str(attest_path),
        ],
        capsys,
    )
    assert code == exits.ENVIRONMENT and out == ""
    assert "could not be opened" in err and "cairn startup-scan" in err


def test_a_missing_attestation_file_exits_environment(cli_db, tmp_path, capsys):
    db, statement, _ = cli_db
    code, out, err = _cli(
        [
            "justify",
            "--statement",
            statement.hash,
            "--db",
            str(db),
            "--attest",
            str(tmp_path / "gone.log"),
        ],
        capsys,
    )
    assert code == exits.ENVIRONMENT and out == ""
    assert "cairn attest init" in err


def test_an_evidence_row_with_no_mirror_node_is_graded_replayable(writer, attest_path):
    statement = _statement(writer, seed=40)
    row = {
        "hash": "4" * 64,
        "kind": "ladder_table",
        "verdict": "KEEP",
        "population": claims.to_json(_wide_population(statement)),
        "assumptions": claims.to_json([]),
        "in_sample_sizes": claims.to_json([30, 60]),
        "producer_identity": "5" * 64,
        "producer_tag": "skill",
        "attempt_id": None,
        "repro_record_hash": None,
    }
    stored = claims.get_claim_statement(writer, statement.hash)
    ctx = justify.context_for(writer, row, stored, attest_path)
    assert writer.get_node(row["hash"]) is None
    assert ctx.grade == "Replayable"
    result = justify.justify(row, stored, ctx)
    assert isinstance(result, justify.Justification) and result.cls == CONJECTURE


def test_a_second_writer_exits_conflict(cli_db, attest_path, capsys):
    db, statement, _ = cli_db
    with open_writer(db.parent, "cli.sqlite"):
        code, out, err = _cli(
            [
                "justify",
                "--statement",
                statement.hash,
                "--db",
                str(db),
                "--attest",
                str(attest_path),
            ],
            capsys,
        )
    assert code == exits.CONFLICT and out == ""
    assert "another writer already holds" in err


def test_a_standing_disagreement_holds_an_upgrading_derivation_at_the_pre_dispute_tag(writer, attest_path):
    statement = _statement(writer, seed=41)
    claims.append_tag_history(
        writer, statement.hash, None, CONJECTURE, None, claims.to_json({"result": "test-fixture"}), "test"
    )
    rec = disagreement.record(
        writer,
        statement_hash=statement.hash,
        left_hash="aa" * 32,
        right_hash="bb" * 32,
        classification=disagreement.STATEMENT_ERROR,
    )
    assert rec.frozen_tag == CONJECTURE
    _ladder(writer, statement, _wide_population(statement), seed=41)
    before = len(claims.tag_history_for(writer, statement.hash))

    held = justify.derive_tag(writer, statement.hash, attest_path)
    assert held.tag == CONJECTURE
    assert not held.appended
    assert len(claims.tag_history_for(writer, statement.hash)) == before

    raised = human_queue.get_item(writer, rec.item_id)["enqueued_at"]
    ruled_at = (datetime.fromisoformat(raised) + timedelta(seconds=1)).isoformat()
    unplaced = factories.review_verdict(statement.hash, verdict="approve", seed=77, at=ruled_at)
    offset = attest.append_record(attest_path, claims.review_verdict_canonical(unplaced))
    ruling = factories.review_verdict(statement.hash, verdict="approve", seed=77, at=ruled_at, file_offset=offset)
    claims.write_review_verdict(writer, ruling)
    with pytest.raises(human_queue.ClosingRuleViolation, match="carries an attestation record"):
        human_queue.close_by_blocker_clear(writer, rec.item_id, attest_path=attest_path, cleared_by="owner-ruling")
    human_queue.close_by_blocker_clear(
        writer,
        rec.item_id,
        attest_path=attest_path,
        cleared_by="owner-ruling",
        record_digest=ruling.record_digest,
        file_offset=ruling.file_offset,
    )
    assert disagreement.freeze_for(writer, statement.hash, attest_path) is None

    released = justify.derive_tag(writer, statement.hash, attest_path)
    assert released.tag == STRONG_EMPIRICAL
    moves = [(r["from_tag"], r["to_tag"]) for r in claims.tag_history_for(writer, statement.hash)]
    assert moves[-1] == (CONJECTURE, STRONG_EMPIRICAL)
