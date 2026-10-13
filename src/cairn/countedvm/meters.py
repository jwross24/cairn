from decimal import Decimal
from fractions import Fraction

from cairn import laddertable


def _nonnegative_integer(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def _relative_tolerance(value):
    if type(value) not in (int, float, Decimal):
        raise ValueError("tolerance must be a finite nonnegative number")
    try:
        result = Fraction(value) if type(value) is int else Fraction(str(value))
    except ValueError, OverflowError:
        raise ValueError("tolerance must be a finite nonnegative number") from None
    if result < 0:
        raise ValueError("tolerance must be a finite nonnegative number")
    return result


def instructions_per_operation(executed, count, reference_executed, reference_count, *, tolerance):
    for name, value in (
        ("executed", executed),
        ("count", count),
        ("reference_executed", reference_executed),
        ("reference_count", reference_count),
    ):
        _nonnegative_integer(value, name)
    relative_tolerance = _relative_tolerance(tolerance)
    if count == 0 or reference_count == 0 or reference_executed == 0:
        return laddertable.INCONCLUSIVE
    ratio = Fraction(executed * reference_count, count * reference_executed)
    if abs(ratio - 1) > relative_tolerance:
        return laddertable.INCONCLUSIVE
    return None


def table_allocation(table_rows, table_bytes, *, row_cap, byte_cap):
    for name, value in (
        ("table_rows", table_rows),
        ("table_bytes", table_bytes),
        ("row_cap", row_cap),
        ("byte_cap", byte_cap),
    ):
        _nonnegative_integer(value, name)
    if table_rows > row_cap or table_bytes > byte_cap:
        return laddertable.REJECT
    return None


def program_size(program_bytes, program_lines, *, byte_cap, line_cap):
    for name, value in (
        ("program_bytes", program_bytes),
        ("program_lines", program_lines),
        ("byte_cap", byte_cap),
        ("line_cap", line_cap),
    ):
        _nonnegative_integer(value, name)
    if program_bytes > byte_cap or program_lines > line_cap:
        return laddertable.INCONCLUSIVE
    return None


def combine(verdict, meter_results):
    if type(verdict) is not str or verdict not in laddertable.VERDICTS:
        raise ValueError("initial verdict is outside the ladder verdict domain")
    found = set()
    for result in meter_results:
        if result is not None and (
            type(result) is not str or result not in (laddertable.INCONCLUSIVE, laddertable.REJECT)
        ):
            raise ValueError("meter result must be None, INCONCLUSIVE or REJECT")
        found.add(result)
    if verdict == laddertable.REJECT or laddertable.REJECT in found:
        return laddertable.REJECT
    if verdict == laddertable.INCONCLUSIVE or laddertable.INCONCLUSIVE in found:
        return laddertable.INCONCLUSIVE
    return verdict
