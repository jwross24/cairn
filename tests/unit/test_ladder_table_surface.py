import inspect

from cairn import laddertable

FAMILY = {laddertable.__name__, *(f"cairn.laddertable_{part}" for part in ("rows", "aggregate", "verdict", "write"))}


def test_struct_field_names_are_exact():
    assert laddertable.TRIAL.names == (
        "arm",
        "bits",
        "trial",
        "seed",
        "instance_hash",
        "status",
        "output_complete",
        "recovered",
        "gate_ops_kind",
        "gate_ops",
        "reported_ops",
        "cpu_seconds",
        "wall_seconds",
        "peak_rss_bytes",
        "scratch_bytes",
        "reported_memory_bytes",
        "replay_grade",
        "measurement_scope",
        "witness_hash",
    )
    assert laddertable.RUNG.names == (
        "bits",
        "role",
        "trials",
        "ops_kind",
        "mean_ops",
        "sd_ops",
        "cpu_seconds",
        "reference_rate",
        "memory_bytes",
        "success_rate",
        "radius",
        "claim_ci_low",
        "claim_ci_high",
        "model_prediction",
        "model_band",
        "shape_statistic",
        "declared_shape",
    )
    assert laddertable.TABLE_STRUCT.names == (
        "run_id",
        "nonce",
        "hypothesis_hash",
        "method_identity",
        "implementation_revision",
        "gate_bundle_hash",
        "plan_hash",
        "uncounted_backend",
        "rungs",
        "trials",
    )


def test_module_defined_public_api_is_closed():
    public = set()
    for name, value in vars(laddertable).items():
        if name.startswith("_") or inspect.ismodule(value):
            continue
        if getattr(value, "__module__", laddertable.__name__) not in FAMILY:
            continue
        public.add(name)
    assert public == {
        "LadderTableError",
        "Trial",
        "RungRow",
        "ResultTable",
        "Verdict",
        "Recomputation",
        "OpsObservation",
        "aggregate_rung",
        "verdict",
        "in_sample_sizes",
        "inputs_for_attempt",
        "membership_for_table",
        "mapped_table_for_attempt",
        "table_for_attempt",
        "attempt_ids_for_table",
        "replay_grade",
        "shape_departures",
        "enqueue_shape_departures",
        "enqueue_clock_inconclusive",
        "effective_clock_tolerance",
        "write",
        "read",
        "recorded_verdict",
        "recompute",
        "policy",
        "record",
        "evidence_node",
        "write_evidence_node",
        "KEEP",
        "KEEP_IN_SAMPLE",
        "REJECT",
        "INCONCLUSIVE",
        "VERDICTS",
        "NODE_KIND",
        "ATTEMPT_MEMBERSHIP_KIND",
        "TABLES",
        "RUNGS",
        "TRIALS",
        "OPS_EXACT",
        "OPS_LOWER_BOUND",
        "OPS_UNKNOWN",
        "OPS_KINDS",
        "RECOVERY",
        "COUNT_DIVERGENCE",
        "MEMORY_CAP",
        "REFUTATION_FLOOR",
        "IN_SAMPLE_MISS",
        "OUT_OF_SAMPLE_MISS",
        "UNCOUNTED_BACKEND",
        "MEASUREMENT_SCOPE",
        "CLOCK",
        "WALL",
        "FAILED_TRIAL",
        "INSIDE_BAND",
        "ALL_RUNGS_PASS",
        "REJECT_PREDICATES",
        "INCONCLUSIVE_PREDICATES",
        "CLOCK_QUEUE_PREDICATES",
        "PREDICATES",
        "REFUTATION_KIND",
    }
