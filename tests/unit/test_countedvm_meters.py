from decimal import Decimal

import pytest

from cairn import laddertable
from cairn.countedvm import meters


def test_baseline_against_itself_passes_each_meter():
    assert meters.instructions_per_operation(240, 20, 240, 20, tolerance=0) is None
    assert meters.table_allocation(16, 512, row_cap=16, byte_cap=512) is None
    assert meters.program_size(200, 12, byte_cap=200, line_cap=12) is None


@pytest.mark.parametrize("executed", [89, 111])
def test_relative_instruction_ratio_outside_tolerance_is_inconclusive(executed):
    assert (
        meters.instructions_per_operation(executed, 10, 100, 10, tolerance=Decimal("0.1")) == laddertable.INCONCLUSIVE
    )


@pytest.mark.parametrize("executed", [90, 100, 110])
@pytest.mark.parametrize("tolerance", [Decimal("0.1"), 0.1])
def test_relative_instruction_ratio_boundary_passes(executed, tolerance):
    assert meters.instructions_per_operation(executed, 10, 100, 10, tolerance=tolerance) is None


def test_instruction_ratio_normalizes_different_operation_counts():
    assert meters.instructions_per_operation(200, 20, 100, 10, tolerance=0) is None
    assert meters.instructions_per_operation(201, 20, 100, 10, tolerance=0) == laddertable.INCONCLUSIVE


def test_instruction_ratio_keeps_integer_precision():
    large = 10**400
    assert meters.instructions_per_operation(large, large, large, large, tolerance=0) is None
    assert meters.instructions_per_operation(large + 1, large, large, large, tolerance=0) == laddertable.INCONCLUSIVE


@pytest.mark.parametrize("values", [(1, 0, 1, 1), (1, 1, 1, 0), (0, 0, 0, 0), (0, 1, 0, 1), (1, 1, 0, 1)])
def test_undefined_instruction_ratio_is_inconclusive(values):
    assert meters.instructions_per_operation(*values, tolerance=1) == laddertable.INCONCLUSIVE


@pytest.mark.parametrize(("table_rows", "table_bytes"), [(17, 512), (16, 513), (17, 513)])
def test_excessive_table_allocation_is_rejected(table_rows, table_bytes):
    assert meters.table_allocation(table_rows, table_bytes, row_cap=16, byte_cap=512) == laddertable.REJECT


@pytest.mark.parametrize(("program_bytes", "program_lines"), [(201, 12), (200, 13), (201, 13)])
def test_excessive_program_size_is_inconclusive(program_bytes, program_lines):
    assert meters.program_size(program_bytes, program_lines, byte_cap=200, line_cap=12) == laddertable.INCONCLUSIVE


def test_zero_caps_allow_only_zero_allocations():
    assert meters.table_allocation(0, 0, row_cap=0, byte_cap=0) is None
    assert meters.table_allocation(1, 0, row_cap=0, byte_cap=0) == laddertable.REJECT
    assert meters.table_allocation(0, 1, row_cap=0, byte_cap=0) == laddertable.REJECT
    assert meters.program_size(0, 0, byte_cap=0, line_cap=0) is None
    assert meters.program_size(1, 0, byte_cap=0, line_cap=0) == laddertable.INCONCLUSIVE
    assert meters.program_size(0, 1, byte_cap=0, line_cap=0) == laddertable.INCONCLUSIVE


@pytest.mark.parametrize("verdict", laddertable.VERDICTS)
@pytest.mark.parametrize("passing", [[], [None], [None, None, None]])
def test_passing_meters_preserve_every_initial_verdict(verdict, passing):
    assert meters.combine(verdict, passing) == verdict


@pytest.mark.parametrize("verdict", laddertable.VERDICTS)
@pytest.mark.parametrize("results", [[laddertable.INCONCLUSIVE], [None, laddertable.INCONCLUSIVE, None]])
def test_inconclusive_meter_cannot_rescue_a_rejection(verdict, results):
    expected = laddertable.REJECT if verdict == laddertable.REJECT else laddertable.INCONCLUSIVE
    assert meters.combine(verdict, results) == expected


@pytest.mark.parametrize("verdict", laddertable.VERDICTS)
@pytest.mark.parametrize(
    "results",
    [
        [laddertable.REJECT],
        [laddertable.INCONCLUSIVE, laddertable.REJECT],
        [laddertable.REJECT, laddertable.INCONCLUSIVE],
        [None, laddertable.REJECT, None],
    ],
)
def test_reject_meter_wins_every_combination(verdict, results):
    assert meters.combine(verdict, results) == laddertable.REJECT


INVALID_INTEGERS = [-1, True, False, 1.0, "1", None, float("nan"), float("inf"), Decimal("NaN"), []]


@pytest.mark.parametrize("invalid", INVALID_INTEGERS)
@pytest.mark.parametrize("field", ["executed", "count", "reference_executed", "reference_count"])
def test_instruction_counts_reject_malformed_inputs(field, invalid):
    arguments = {"executed": 100, "count": 10, "reference_executed": 100, "reference_count": 10}
    arguments[field] = invalid
    with pytest.raises(ValueError, match=field):
        meters.instructions_per_operation(**arguments, tolerance=0)


@pytest.mark.parametrize(
    "tolerance",
    [
        -1,
        -0.1,
        True,
        False,
        "0.1",
        None,
        float("nan"),
        float("inf"),
        float("-inf"),
        Decimal("NaN"),
        Decimal("Infinity"),
    ],
)
def test_instruction_tolerance_rejects_malformed_inputs(tolerance):
    with pytest.raises(ValueError, match="tolerance"):
        meters.instructions_per_operation(100, 10, 100, 10, tolerance=tolerance)


@pytest.mark.parametrize("invalid", INVALID_INTEGERS)
@pytest.mark.parametrize("field", ["table_rows", "table_bytes", "row_cap", "byte_cap"])
def test_table_meter_rejects_malformed_inputs(field, invalid):
    arguments = {"table_rows": 16, "table_bytes": 512, "row_cap": 16, "byte_cap": 512}
    arguments[field] = invalid
    with pytest.raises(ValueError, match=field):
        meters.table_allocation(**arguments)


@pytest.mark.parametrize("invalid", INVALID_INTEGERS)
@pytest.mark.parametrize("field", ["program_bytes", "program_lines", "byte_cap", "line_cap"])
def test_program_meter_rejects_malformed_inputs(field, invalid):
    arguments = {"program_bytes": 200, "program_lines": 12, "byte_cap": 200, "line_cap": 12}
    arguments[field] = invalid
    with pytest.raises(ValueError, match=field):
        meters.program_size(**arguments)


@pytest.mark.parametrize("verdict", [None, "", "UNKNOWN", True, 0, []])
def test_combiner_rejects_unknown_initial_verdict(verdict):
    with pytest.raises(ValueError, match="initial verdict"):
        meters.combine(verdict, [None])


@pytest.mark.parametrize("result", [laddertable.KEEP, laddertable.KEEP_IN_SAMPLE, "UNKNOWN", True, 0, []])
@pytest.mark.parametrize("verdict", laddertable.VERDICTS)
def test_combiner_rejects_invalid_meter_even_after_rejection(verdict, result):
    with pytest.raises(ValueError, match="meter result"):
        meters.combine(verdict, [laddertable.REJECT, result])
