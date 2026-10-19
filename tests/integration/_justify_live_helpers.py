import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path

import factories
import pytest
from _substrate_helpers import ENV_MANIFEST_HASH, IDENTITY_A, TRANSCRIPT_HASH

from cairn import (
    attest,
    claims,
    human_authority,
    justify,
    ladder,
    ladderplan,
    laddertable,
    runner,
)
from cairn.skills import bsgs, rho_dp

BITS = (30, 40, 50, 60)
FIT_BITS = BITS[:-1]
HOLD_OUT_BITS = BITS[-1]
COVERING_CROSS_CHECK = {"axis": "algorithm", "independent_range": {"bits": [0, 60]}}
AUTHOR_ORIGINS = {"F5": {"P": justify.AUTHOR_SUPPLIED, "p": justify.AUTHOR_SUPPLIED}}
GENERATED_ORIGINS = {"F5": {"P": "generated", "p": "generated"}}

TRIAL = laddertable.Trial(
    arm=ladderplan.ARMS[0],
    bits=0,
    trial=0,
    seed=1,
    instance_hash="aa" * 32,
    status=runner.STATUS_OK,
    output_complete=True,
    recovered=True,
    gate_ops=laddertable.OpsObservation(laddertable.OPS_EXACT, 1000000),
    reported_ops=1000000,
    cpu_seconds="1",
    wall_seconds="1",
    peak_rss_bytes=1000,
    scratch_bytes=1000,
    reported_memory_bytes=1000,
    replay_grade="Replayable",
    measurement_scope=runner.SCOPE_TREE,
)
RUNG = laddertable.RungRow(
    bits=0,
    role=ladderplan.ROLE_FIT,
    trials=2,
    ops_kind=laddertable.OPS_EXACT,
    mean_ops="1000000.000000",
    sd_ops="0.000000",
    cpu_seconds="1",
    reference_rate="1000000",
    memory_bytes=100000,
    success_rate="1.0000",
    radius="0.1216",
    claim_ci_low="2.000000",
    claim_ci_high="2.000000",
    model_prediction="1000000",
    model_band="0.05",
    shape_statistic="1.000000",
    declared_shape="stable",
)
TABLE = laddertable.ResultTable(
    run_id="run-live",
    nonce="nonce-live",
    hypothesis_hash="aa" * 32,
    method_identity={"interface_version": "toy_curve/1", "params": {"r": "20"}},
    implementation_revision="aa" * 32,
    gate_bundle_hash="cc" * 32,
    plan_hash="dd" * 32,
    uncounted_backend=None,
    rungs=(),
    trials=(),
)


def real_table(hypothesis_hash, run_id="run-live"):
    return dataclasses.replace(
        TABLE,
        run_id=run_id,
        hypothesis_hash=hypothesis_hash,
        rungs=tuple(
            dataclasses.replace(
                RUNG,
                bits=b,
                role=ladderplan.ROLE_HOLD_OUT if b == HOLD_OUT_BITS else ladderplan.ROLE_FIT,
                claim_ci_low=None if b == HOLD_OUT_BITS else RUNG.claim_ci_low,
                claim_ci_high=None if b == HOLD_OUT_BITS else RUNG.claim_ci_high,
            )
            for b in BITS
        ),
        trials=tuple(
            dataclasses.replace(
                TRIAL,
                arm=arm,
                bits=b,
                trial=t,
                gate_ops=laddertable.OpsObservation(
                    laddertable.OPS_EXACT, 2000000 if arm == ladder.BASELINE else 1000000
                ),
            )
            for b in BITS
            for arm in ((ladder.CLAIMANT,) if b == HOLD_OUT_BITS else ladderplan.ARMS)
            for t in (0, 1)
        ),
    )


def statement_with(writer, *, cost_model, seed=1, size=(30, 60)):
    stmt = factories.claim_statement(cost_model=cost_model, seed=seed, size=size)
    claims.write_claim_statement(writer, stmt)
    return stmt


def certify(writer, revision, summary):
    identity = writer.put_identity_bundle({**IDENTITY_A, "implementation_revision": revision})
    writer.put_certificate(identity, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, summary)
    return identity


def live_ladder_node(writer, plan, statement, *, producer_identity, producer_tag="skill", run_id="run-live"):
    """A ladder_table node over a table the substrate actually holds, with a real repro record."""
    table = real_table(statement.hash, run_id=run_id)
    attempt_id = f"attempt-{run_id}"
    laddertable.write(writer, table, plan, attempt_id=attempt_id)
    verified = tuple((t.arm, t.bits, t.trial) for t in table.trials)
    record, recomputation = laddertable.record(writer, table, plan, verified, attempt_id=attempt_id)
    node = laddertable.evidence_node(
        table,
        plan,
        target_statement_hash=statement.hash,
        population=statement.scope,
        assumptions=frozenset(statement.scope["assumption_set"]),
        producer_identity=producer_identity,
        producer_tag=producer_tag,
        attempt_id=attempt_id,
        repro_record_hash=record.hash,
    )
    claims.write_evidence_node(writer, node)
    return table, node, recomputation


def statistical_node(writer, statement, *, producer_identity, population=None):
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        population or statement.scope,
        frozenset(statement.scope["assumption_set"]),
        producer=(producer_identity, "skill"),
        seed=7,
    )
    claims.write_evidence_node(writer, node)
    return node


def judge(writer, node, statement, attest_path, **kw):
    row = dict(writer.conn.execute("SELECT * FROM evidence_nodes WHERE hash = ?", (node.hash,)).fetchone())
    ctx = justify.context_for(writer, row, {"hash": statement.hash, **dataclasses.asdict(statement)}, attest_path, **kw)
    return justify.justify(row, {"hash": statement.hash, "scope": statement.scope}, ctx)


def production_plan():
    obj = json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    obj["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    full = ladderplan.LadderPlan.load(obj)
    fit = dataclasses.replace(full.rung(30), bits=28, trials=2)
    hold_out = dataclasses.replace(full.rung(40), bits=30, role=ladderplan.ROLE_HOLD_OUT, trials=2)
    return dataclasses.replace(full, rungs=(fit, hold_out), hold_out_m=2, patience_multiplier=60)


def bound_production_run(writer, shipped, tmp_path, run_id, declared_size=(7, 77)):
    from test_ladder_run import _dispatch_run

    plan = production_plan()
    statement = factories.claim_statement(
        family="dlp",
        size=declared_size,
        param_ranges={"bits": list(declared_size)},
        seed=91,
    )
    claims.write_claim_statement(writer, statement)
    hypothesis = claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": list(declared_size)},
        claim_statement_hash=statement.hash,
    )
    nonce = _dispatch_run(writer, shipped, tmp_path, plan, hypothesis, run_id)
    scratch = tmp_path / f"bound-{run_id}"
    scratch.mkdir()
    attestation_log = scratch / "attestations.log"
    attest.init(str(attestation_log), shipped.waiver_target())
    human_authority.append(
        writer,
        str(attestation_log),
        human_authority.STATEMENT_RATIFICATION,
        {"statement_hash": statement.hash, "issued_by": "test-operator", "at": datetime.now(UTC).isoformat()},
        gate_bundle_hash=shipped.hash,
    )
    table, arm_trials = ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
        run_id=run_id,
        hypothesis_hash=hypothesis.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=60,
        attest_path=attestation_log,
    )
    claimant_ids = {trial.attempt_id for trial in arm_trials if trial.arm == ladder.CLAIMANT}
    evidence = [
        dict(row)
        for row in writer.conn.execute(
            "SELECT * FROM evidence_nodes WHERE kind = ? AND target_statement_hash = ? ORDER BY attempt_id",
            (laddertable.NODE_KIND, statement.hash),
        ).fetchall()
        if row["attempt_id"] in claimant_ids
    ]
    return plan, statement, table, arm_trials, evidence


def replay_attempt(writer, attempt_id):
    original = writer.get_attempt(attempt_id)
    replay = writer.start_attempt(
        original["recipe_key"],
        replay_grade=original["replay_grade"],
        skip_cache_lookup=True,
    )
    writer.close_attempt(
        replay,
        original["status"],
        output_manifest_hash=original["output_manifest_hash"],
        receipt_hash=original["receipt_hash"],
        verifier_result_hash=original["verifier_result_hash"],
        certificate_hash=original["certificate_hash"],
    )
    return replay


def assert_membership_refused(writer, table, plan, mapping, slot, replacement, match, before, db_snapshot):
    with pytest.raises(laddertable.LadderTableError, match=match):
        laddertable.write(writer, table, plan, trial_attempts={**mapping, slot: replacement})
    assert db_snapshot(writer.conn, f"after-{replacement}") == before


def assert_evidence_refused(writer, table, node, match, before, db_snapshot):
    with pytest.raises(laddertable.LadderTableError, match=match):
        laddertable.write_evidence_node(writer, table, node)
    assert claims.get_evidence_node(writer, node.hash) is None
    assert db_snapshot(writer.conn, f"after-{node.hash}") == before
