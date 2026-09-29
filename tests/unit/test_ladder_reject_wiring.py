import pytest

from cairn import ladderplan, laddertable, ledger


def _row(*, ops_kind=laddertable.OPS_EXACT, role=ladderplan.ROLE_FIT):
    exact = ops_kind == laddertable.OPS_EXACT
    unknown = ops_kind == laddertable.OPS_UNKNOWN
    return laddertable.RungRow(
        bits=28,
        role=role,
        trials=2,
        ops_kind=ops_kind,
        mean_ops=None if unknown else "1000",
        sd_ops="0" if exact else None,
        cpu_seconds="1",
        reference_rate="1",
        memory_bytes=100,
        success_rate="1",
        radius="0.1",
        model_prediction="100",
        model_band="0.05",
        shape_statistic="10" if exact else None,
        declared_shape="stable",
    )


def _table(row):
    return laddertable.ResultTable(
        run_id="run-1",
        nonce="nonce-1",
        hypothesis_hash="aa" * 32,
        method_identity={"interface_version": "toy/1", "params": {}},
        implementation_revision="bb" * 32,
        gate_bundle_hash="cc" * 32,
        plan_hash="dd" * 32,
        uncounted_backend=None,
        rungs=(row,),
        trials=(),
        created_at="2026-09-02T00:00:00Z",
    )


@pytest.mark.parametrize(
    ("predicate", "ops_kind", "role", "result_kind"),
    [
        (laddertable.REFUTATION_FLOOR, laddertable.OPS_EXACT, ladderplan.ROLE_FIT, ledger.EXACT),
        (laddertable.REFUTATION_FLOOR, laddertable.OPS_LOWER_BOUND, ladderplan.ROLE_FIT, ledger.LOWER_BOUND),
        (laddertable.IN_SAMPLE_MISS, laddertable.OPS_EXACT, ladderplan.ROLE_FIT, ledger.EXACT),
        (laddertable.OUT_OF_SAMPLE_MISS, laddertable.OPS_EXACT, ladderplan.ROLE_HOLD_OUT, ledger.EXACT),
    ],
)
def test_measured_reject_projection_uses_persisted_rung_values(predicate, ops_kind, role, result_kind):
    row = _row(ops_kind=ops_kind, role=role)
    table = _table(row)
    recorded = laddertable.Verdict(
        laddertable.REJECT,
        predicate,
        refutation_kind=ledger.MEASURED,
        rung_bits=row.bits,
    )
    fields = laddertable.measured_entry_fields(table, recorded)
    result = fields["result"]
    point = fields["measured_points"][0]

    assert result == {
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
    }
    assert point["numeric"] == {"bits": row.bits}
    assert point["categorical"]["predicate"] == predicate
    assert point["categorical"]["mean_ops"] == row.mean_ops
    if predicate == laddertable.REFUTATION_FLOOR:
        assert point["categorical"]["ops_kind"] == ops_kind
    else:
        assert point["categorical"]["model_prediction"] == row.model_prediction
        assert point["categorical"]["model_band"] == row.model_band


@pytest.mark.parametrize(
    ("predicate", "ops_kind", "role"),
    [
        (laddertable.MEMORY_CAP, laddertable.OPS_EXACT, ladderplan.ROLE_FIT),
        (laddertable.REFUTATION_FLOOR, laddertable.OPS_UNKNOWN, ladderplan.ROLE_FIT),
        (laddertable.IN_SAMPLE_MISS, laddertable.OPS_LOWER_BOUND, ladderplan.ROLE_FIT),
        (laddertable.OUT_OF_SAMPLE_MISS, laddertable.OPS_EXACT, ladderplan.ROLE_FIT),
    ],
)
def test_unsettled_measured_predicates_have_no_projection(predicate, ops_kind, role):
    row = _row(ops_kind=ops_kind, role=role)
    recorded = laddertable.Verdict(
        laddertable.REJECT,
        predicate,
        refutation_kind=ledger.MEASURED,
        rung_bits=row.bits,
    )

    with pytest.raises(laddertable.LadderTableError):
        laddertable.measured_entry_fields(_table(row), recorded)
