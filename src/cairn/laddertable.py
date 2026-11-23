"""The ladder result table: a run's rungs and trials, its typed verdict, and its shape diagnostic.

A table is a content-addressed node holding one run's rung rows and trial rows. `verdict`
scans a table against a `ladderplan.LadderPlan` and returns the first predicate that fires,
in the fixed order PLAN section 6 sets: the REJECT predicates, then the INCONCLUSIVE ones,
then a pass. Nothing here measures a claim; the module composes predicates over numbers a
caller already produced. The shape diagnostic is separate from the verdict: a departure is
queued for a human and never moves what the verdict says.

A trial whose receipt scope is weaker than a verified-complete process-tree figure makes the
run INCONCLUSIVE, and that check sits after the REJECT predicates: a scope short of `tree`
undercounts, so a refutation drawn from it stands, while a pass drawn from it does not.
"""

import dataclasses
import json

from cairn import claims, ladderplan, ledger, log, repro, substrate
from cairn.laddertable_aggregate import _decimal_text as _decimal_text
from cairn.laddertable_aggregate import _speedup_ci as _speedup_ci
from cairn.laddertable_aggregate import aggregate_rung as aggregate_rung
from cairn.laddertable_rows import _MEASURED_SETTLEMENT_PREDICATES as _MEASURED_SETTLEMENT_PREDICATES
from cairn.laddertable_rows import ALL_RUNGS_PASS as ALL_RUNGS_PASS
from cairn.laddertable_rows import ATTEMPT_MEMBER as ATTEMPT_MEMBER
from cairn.laddertable_rows import ATTEMPT_MEMBERSHIP as ATTEMPT_MEMBERSHIP
from cairn.laddertable_rows import ATTEMPT_MEMBERSHIP_KIND as ATTEMPT_MEMBERSHIP_KIND
from cairn.laddertable_rows import CLOCK as CLOCK
from cairn.laddertable_rows import CLOCK_QUEUE_PREDICATES as CLOCK_QUEUE_PREDICATES
from cairn.laddertable_rows import COUNT_DIVERGENCE as COUNT_DIVERGENCE
from cairn.laddertable_rows import FAILED_TRIAL as FAILED_TRIAL
from cairn.laddertable_rows import IN_SAMPLE_MISS as IN_SAMPLE_MISS
from cairn.laddertable_rows import INCONCLUSIVE as INCONCLUSIVE
from cairn.laddertable_rows import INCONCLUSIVE_PREDICATES as INCONCLUSIVE_PREDICATES
from cairn.laddertable_rows import INSIDE_BAND as INSIDE_BAND
from cairn.laddertable_rows import KEEP as KEEP
from cairn.laddertable_rows import KEEP_IN_SAMPLE as KEEP_IN_SAMPLE
from cairn.laddertable_rows import MEASUREMENT_SCOPE as MEASUREMENT_SCOPE
from cairn.laddertable_rows import MEMORY_CAP as MEMORY_CAP
from cairn.laddertable_rows import NODE_KIND as NODE_KIND
from cairn.laddertable_rows import OPS_EXACT as OPS_EXACT
from cairn.laddertable_rows import OPS_KINDS as OPS_KINDS
from cairn.laddertable_rows import OPS_LOWER_BOUND as OPS_LOWER_BOUND
from cairn.laddertable_rows import OPS_UNKNOWN as OPS_UNKNOWN
from cairn.laddertable_rows import OUT_OF_SAMPLE_MISS as OUT_OF_SAMPLE_MISS
from cairn.laddertable_rows import PREDICATES as PREDICATES
from cairn.laddertable_rows import RECOVERY as RECOVERY
from cairn.laddertable_rows import REFUTATION_FLOOR as REFUTATION_FLOOR
from cairn.laddertable_rows import REFUTATION_KIND as REFUTATION_KIND
from cairn.laddertable_rows import REJECT as REJECT
from cairn.laddertable_rows import REJECT_PREDICATES as REJECT_PREDICATES
from cairn.laddertable_rows import RUNG as RUNG
from cairn.laddertable_rows import RUNGS as RUNGS
from cairn.laddertable_rows import TABLE_STRUCT as TABLE_STRUCT
from cairn.laddertable_rows import TABLES as TABLES
from cairn.laddertable_rows import TRIAL as TRIAL
from cairn.laddertable_rows import TRIALS as TRIALS
from cairn.laddertable_rows import UNCOUNTED_BACKEND as UNCOUNTED_BACKEND
from cairn.laddertable_rows import VERDICTS as VERDICTS
from cairn.laddertable_rows import WALL as WALL
from cairn.laddertable_rows import LadderTableError as LadderTableError
from cairn.laddertable_rows import OpsObservation as OpsObservation
from cairn.laddertable_rows import Recomputation as Recomputation
from cairn.laddertable_rows import ResultTable as ResultTable
from cairn.laddertable_rows import RungRow as RungRow
from cairn.laddertable_rows import Trial as Trial
from cairn.laddertable_rows import Verdict as Verdict
from cairn.laddertable_rows import _rung_canonical as _rung_canonical
from cairn.laddertable_rows import _rung_fields as _rung_fields
from cairn.laddertable_rows import _table_canonical as _table_canonical
from cairn.laddertable_rows import _table_fields as _table_fields
from cairn.laddertable_rows import _trial_canonical as _trial_canonical
from cairn.laddertable_rows import _trial_fields as _trial_fields
from cairn.laddertable_verdict import _clock as _clock
from cairn.laddertable_verdict import _clock_overrun_rungs as _clock_overrun_rungs
from cairn.laddertable_verdict import _count_divergence as _count_divergence
from cairn.laddertable_verdict import _failed_trial as _failed_trial
from cairn.laddertable_verdict import _inside_band as _inside_band
from cairn.laddertable_verdict import _measurement_scope as _measurement_scope
from cairn.laddertable_verdict import _memory_cap as _memory_cap
from cairn.laddertable_verdict import _model_miss as _model_miss
from cairn.laddertable_verdict import _recovery as _recovery
from cairn.laddertable_verdict import _refutation_floor as _refutation_floor
from cairn.laddertable_verdict import _trial_numeric as _trial_numeric
from cairn.laddertable_verdict import _uncounted_backend as _uncounted_backend
from cairn.laddertable_verdict import _validate_rungs as _validate_rungs
from cairn.laddertable_verdict import _wall as _wall
from cairn.laddertable_verdict import effective_clock_tolerance as effective_clock_tolerance
from cairn.laddertable_verdict import enqueue_clock_inconclusive as enqueue_clock_inconclusive
from cairn.laddertable_verdict import enqueue_shape_departures as enqueue_shape_departures
from cairn.laddertable_verdict import in_sample_sizes as in_sample_sizes
from cairn.laddertable_verdict import replay_grade as replay_grade
from cairn.laddertable_verdict import shape_departures as shape_departures
from cairn.laddertable_verdict import verdict as verdict
from cairn.laddertable_write import _binding_table_hashes as _binding_table_hashes
from cairn.laddertable_write import _canonical_members as _canonical_members
from cairn.laddertable_write import _claimant_dispatch as _claimant_dispatch
from cairn.laddertable_write import _expected_trial_slots as _expected_trial_slots
from cairn.laddertable_write import _insert_rung as _insert_rung
from cairn.laddertable_write import _insert_trial as _insert_trial
from cairn.laddertable_write import _members_fields as _members_fields
from cairn.laddertable_write import _membership_rows as _membership_rows
from cairn.laddertable_write import _store_membership as _store_membership
from cairn.laddertable_write import _validate_evidence_node as _validate_evidence_node
from cairn.laddertable_write import _validate_trial_attempts as _validate_trial_attempts
from cairn.laddertable_write import attempt_ids_for_table as attempt_ids_for_table
from cairn.laddertable_write import mapped_table_for_attempt as mapped_table_for_attempt
from cairn.laddertable_write import membership_for_table as membership_for_table
from cairn.laddertable_write import table_for_attempt as table_for_attempt
from cairn.laddertable_write import write as write
from cairn.laddertable_write import write_evidence_node as write_evidence_node
from cairn.substrate import _now

lg = log.get("laddertable")


def _rung_from_row(r):
    return RungRow(
        bits=r["bits"],
        role=r["role"],
        trials=r["trials"],
        ops_kind=r["ops_kind"],
        mean_ops=r["mean_ops"],
        sd_ops=r["sd_ops"],
        cpu_seconds=r["cpu_seconds"],
        reference_rate=r["reference_rate"],
        memory_bytes=r["memory_bytes"],
        success_rate=r["success_rate"],
        radius=r["radius"],
        model_prediction=r["model_prediction"],
        model_band=r["model_band"],
        shape_statistic=r["shape_statistic"],
        declared_shape=r["declared_shape"],
        claim_ci_low=r["claim_ci_low"],
        claim_ci_high=r["claim_ci_high"],
    )


def _trial_from_row(r):
    return Trial(
        arm=r["arm"],
        bits=r["bits"],
        trial=r["trial"],
        seed=r["seed"],
        instance_hash=r["instance_hash"],
        status=r["status"],
        output_complete=bool(r["output_complete"]),
        recovered=bool(r["recovered"]),
        gate_ops=OpsObservation(r["gate_ops_kind"], r["gate_ops"]),
        reported_ops=r["reported_ops"],
        cpu_seconds=r["cpu_seconds"],
        wall_seconds=r["wall_seconds"],
        peak_rss_bytes=r["peak_rss_bytes"],
        scratch_bytes=r["scratch_bytes"],
        reported_memory_bytes=r["reported_memory_bytes"],
        replay_grade=r["replay_grade"],
        measurement_scope=r["measurement_scope"],
        witness_hash=r["witness_hash"],
    )


def inputs_for_attempt(sub, attempt_id):
    """The size bound the run behind this attempt spanned, as a param_ranges map: an interval, not the set of sizes run."""
    table_hash = table_for_attempt(sub, attempt_id)
    if table_hash is None:
        return None
    bits = [
        r["bits"] for r in sub.conn.execute(f"SELECT DISTINCT bits FROM {TRIALS} WHERE table_hash = ?", (table_hash,))
    ]
    return {"bits": [min(bits), max(bits)]} if bits else None


def read(sub, table_hash):
    row = sub.conn.execute(f"SELECT * FROM {TABLES} WHERE hash = ?", (table_hash,)).fetchone()
    if row is None:
        return None
    rung_rows = sub.conn.execute(f"SELECT * FROM {RUNGS} WHERE table_hash = ? ORDER BY bits", (table_hash,)).fetchall()
    trial_rows = sub.conn.execute(
        f"SELECT * FROM {TRIALS} WHERE table_hash = ? ORDER BY arm, bits, trial", (table_hash,)
    ).fetchall()
    table = ResultTable(
        run_id=row["run_id"],
        nonce=row["nonce"],
        hypothesis_hash=row["hypothesis_hash"],
        method_identity=json.loads(row["method_identity"]),
        implementation_revision=row["implementation_revision"],
        gate_bundle_hash=row["gate_bundle_hash"],
        plan_hash=row["plan_hash"],
        uncounted_backend=row["uncounted_backend"],
        rungs=tuple(_rung_from_row(r) for r in rung_rows),
        trials=tuple(_trial_from_row(r) for r in trial_rows),
        created_at=row["created_at"],
    )
    if table.hash != table_hash:
        raise LadderTableError(f"reconstructed table hash {table.hash} does not match {table_hash}")
    return table


def recorded_verdict(sub, table_hash):
    row = sub.conn.execute(
        f"SELECT verdict, verdict_predicate, refutation_kind, verdict_rung FROM {TABLES} WHERE hash = ?",
        (table_hash,),
    ).fetchone()
    if row is None:
        return None
    return Verdict(
        kind=row["verdict"],
        predicate=row["verdict_predicate"],
        refutation_kind=row["refutation_kind"],
        rung_bits=row["verdict_rung"],
    )


def _measured_entry_fields(table, recorded):
    if recorded.kind != REJECT or recorded.refutation_kind != ledger.MEASURED:
        raise LadderTableError("measured settlement requires a recorded measured REJECT")
    if recorded.predicate not in _MEASURED_SETTLEMENT_PREDICATES:
        raise LadderTableError(f"measured settlement is unavailable for predicate {recorded.predicate!r}")
    if recorded.rung_bits is None:
        raise LadderTableError("measured settlement requires a recorded rung")
    rows = [row for row in table.rungs if row.bits == recorded.rung_bits]
    if len(rows) != 1:
        raise LadderTableError(f"measured settlement requires one rung at {recorded.rung_bits} bits")
    row = rows[0]
    if recorded.predicate == REFUTATION_FLOOR:
        if row.ops_kind not in (OPS_EXACT, OPS_LOWER_BOUND) or row.mean_ops is None:
            raise LadderTableError("a refutation-floor entry requires an exact or lower-bound operation mean")
        result_kind = ledger.EXACT if row.ops_kind == OPS_EXACT else ledger.LOWER_BOUND
        categorical = {
            "predicate": recorded.predicate,
            "ops_kind": row.ops_kind,
            "mean_ops": row.mean_ops,
        }
    else:
        expected_role = ladderplan.ROLE_FIT if recorded.predicate == IN_SAMPLE_MISS else ladderplan.ROLE_HOLD_OUT
        if row.role != expected_role:
            raise LadderTableError(f"{recorded.predicate} requires a {expected_role} rung")
        if row.ops_kind != OPS_EXACT or row.mean_ops is None:
            raise LadderTableError(f"{recorded.predicate} requires an exact operation mean")
        result_kind = ledger.EXACT
        categorical = {
            "predicate": recorded.predicate,
            "mean_ops": row.mean_ops,
            "model_prediction": row.model_prediction,
            "model_band": row.model_band,
        }
    return {
        "measured_points": ({"numeric": {"bits": row.bits}, "categorical": categorical},),
        "result": {
            "kind": result_kind,
            "quantity": "mean_group_operations",
            "summary": (
                f"lower bound on mean gate operation count at {row.bits} bits"
                if result_kind == ledger.LOWER_BOUND
                else f"finite-sample mean of gate operation counts at {row.bits} bits"
            ),
            "value": row.mean_ops,
            "ci": None,
            "ci_method": None,
            "coverage": None,
        },
    }


def recompute(table, plan, verified):
    verified_set = set(verified)
    restricted_trials = tuple(t for t in table.trials if (t.arm, t.bits, t.trial) in verified_set)
    grouped = {}
    for t in restricted_trials:
        grouped.setdefault(t.bits, []).append(t)

    new_rows = []
    divergences = []
    for row in table.rungs:
        group = grouped.get(row.bits, [])
        if not group:
            new_rows.append(row)
            divergences.append(f"{row.bits}: no verified trials")
            continue

        prung = plan.rung(row.bits)
        rebuilt = aggregate_rung(
            plan,
            prung,
            group,
            model_prediction=row.model_prediction,
            reference_rate=row.reference_rate,
            declared_shape=row.declared_shape,
        )
        for name in (
            "trials",
            "ops_kind",
            "mean_ops",
            "sd_ops",
            "success_rate",
            "claim_ci_low",
            "claim_ci_high",
            "shape_statistic",
        ):
            old, new = getattr(row, name), getattr(rebuilt, name)
            if str(old) != str(new):
                divergences.append(f"{row.bits}: {name} recorded {old} recomputed {new}")
        new_rows.append(rebuilt)

    new_table = dataclasses.replace(table, rungs=tuple(new_rows), trials=restricted_trials)
    recomputed_verdict = verdict(new_table, plan)
    original_verdict = verdict(table, plan)
    if (recomputed_verdict.kind, recomputed_verdict.predicate) != (original_verdict.kind, original_verdict.predicate):
        divergences.append(
            f"verdict recorded {original_verdict.kind}/{original_verdict.predicate} "
            f"recomputed {recomputed_verdict.kind}/{recomputed_verdict.predicate}"
        )

    ordered = tuple(sorted(divergences))
    return Recomputation(verdict=recomputed_verdict, rungs=tuple(new_rows), agrees=not ordered, divergences=ordered)


def policy(table, tier):
    return {(t.arm, t.bits, t.trial): repro.policy(t.replay_grade, tier) for t in table.trials}


def record(sub, table, plan, verified, *, attempt_id, at=None):
    """A second derivation of the table; its agreement with the first is what the record carries."""
    members = membership_for_table(sub, table.hash)
    if members is not None:
        member_ids = {member_attempt_id for arm, _, _, member_attempt_id in members if arm == ladderplan.ARMS[0]}
        expected = {(t.arm, t.bits, t.trial) for t in table.trials}
        if attempt_id not in member_ids:
            raise LadderTableError(f"recomputation attempt {attempt_id} is not a claimant member of table {table.hash}")
        if set(verified) != expected:
            raise LadderTableError(f"recomputation for table {table.hash} must verify every trial")
    recomputation = recompute(table, plan, verified)
    repro_record = claims.ReproRecord(
        attempt_id=attempt_id, kind=claims.REPRO_KINDS[0], passed=recomputation.agrees, at=at or _now()
    )
    with sub.transaction():
        bindings = _binding_table_hashes(sub, repro_record.hash)
        if bindings and bindings != {table.hash}:
            raise substrate.HashCollision(f"repro record {repro_record.hash} is already bound to another ladder table")
        claims.write_repro_record(sub, repro_record)
        sub.add_lineage(repro_record.hash, table.hash, substrate.EDGE_INPUT)
    return repro_record, recomputation


def evidence_node(
    table,
    plan,
    *,
    target_statement_hash,
    population,
    assumptions,
    producer_identity,
    producer_tag,
    attempt_id=None,
    repro_record_hash=None,
):
    return claims.EvidenceNode(
        kind=NODE_KIND,
        target_statement_hash=target_statement_hash,
        population=population,
        assumptions=assumptions,
        producer_identity=producer_identity,
        producer_tag=producer_tag,
        verdict=verdict(table, plan).kind,
        in_sample_sizes=in_sample_sizes(table),
        attempt_id=attempt_id,
        repro_record_hash=repro_record_hash,
    )
