import subprocess
import sys

import pytest

from cairn import countedvm
from cairn.countedvm import Instance
from cairn.pari import pari

REPO_ROOT = countedvm.REPO_ROOT
P_FIELD = 23
A = 1
B = 1
N = 28
POINTS = [None] + [
    (x, y) for x in range(P_FIELD) for y in range(P_FIELD) if (y * y - (x**3 + A * x + B)) % P_FIELD == 0
]
CURVE = pari.ellinit([0, 0, 0, A, B], P_FIELD)
BUDGET = 10_000


def _run_text(tmp_path, text):
    file = tmp_path / "input.txt"
    file.write_text(text)
    completed = subprocess.run(
        [sys.executable, "-m", "cairn.countedvm", "--input", str(file)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
        check=False,
    )
    assert completed.stderr == ""
    return countedvm.decode(completed.stdout, completed.returncode)


def _run(tmp_path, instance, program, budget):
    return _run_text(tmp_path, countedvm.document(instance, program, budget))


def _pari_point(point):
    if point is None:
        return pari([0])
    return pari([point[0], point[1]])


def _lift(point):
    if len(point) == 1:
        return None
    return (int(point[0].lift()), int(point[1].lift()))


def _instance(point_p=None, point_q=None):
    return Instance(P_FIELD, A, B, N, point_p, point_q)


def _inf_or_text(point):
    return "inf" if point is None else f"{point[0]} {point[1]}"


def test_the_fixture_enumerates_the_whole_group():
    assert len(POINTS) == N
    assert int(pari.ellcard(CURVE)) == N


def test_every_pair_of_points_adds_like_pari(tmp_path):
    for point_p in POINTS:
        for point_q in POINTS:
            outcome = _run(tmp_path, _instance(point_p, point_q), "setp p0 P\nsetp p1 Q\naddp p0 p0 p1\nhalt", BUDGET)
            expected = _lift(pari.elladd(CURVE, _pari_point(point_p), _pari_point(point_q)))
            assert outcome.status == "OK", (point_p, point_q)
            assert outcome.p0 == expected, (point_p, point_q)
            assert outcome.count == 1, (point_p, point_q)


def test_every_point_doubles_like_pari(tmp_path):
    for point in POINTS:
        pari_point = _pari_point(point)
        expected = _lift(pari.elladd(CURVE, pari_point, pari_point))
        doubled = _run(tmp_path, _instance(point, point), "setp p0 P\ndblp p0 p0\nhalt", BUDGET)
        added = _run(tmp_path, _instance(point, point), "setp p0 P\nsetp p1 P\naddp p0 p0 p1\nhalt", BUDGET)
        assert doubled.status == "OK", point
        assert doubled.p0 == expected, point
        assert doubled.count == 1, point
        assert added.status == "OK", point
        assert added.p0 == expected, point
        assert added.count == 1, point


def test_every_point_negates_like_pari_and_counts_nothing(tmp_path):
    for point in POINTS:
        outcome = _run(tmp_path, _instance(point, point), "setp p0 P\nnegp p0 p0\nhalt", BUDGET)
        assert outcome.status == "OK", point
        assert outcome.p0 == _lift(pari.ellneg(CURVE, _pari_point(point))), point
        assert outcome.count == 0, point


def test_scalar_multiplication_matches_pari_and_the_counting_convention(tmp_path):
    point = next(candidate for candidate in POINTS if candidate is not None and candidate[1] != 0)
    instance = _instance(point, point)
    for k in range(2 * N):
        scalar = k % N
        outcome = _run(tmp_path, instance, f"setp p0 P\nsset s0 {scalar}\nmulp p0 p0 s0\nhalt", BUDGET)
        assert outcome.status == "OK", k
        assert outcome.p0 == _lift(pari.ellmul(CURVE, _pari_point(point), scalar)), k
        assert outcome.count == countedvm.expected_mul_ops(scalar), k
        if scalar == 0:
            assert outcome.p0 is None
            assert outcome.count == 0


def _solve_program(a1, a2, b1, b2):
    return f"sset s0 {a1}\nsset s1 {a2}\nsset s2 {b1}\nsset s3 {b2}\nsolve s4 s0 s1 s2 s3\nresult s4\nhalt"


def test_solve_recovers_the_collision_scalar_and_refuses_a_zero_denominator(tmp_path):
    instance = _instance(POINTS[1], POINTS[1])
    a1, a2, b1, b2 = 17, 5, 4, 7
    outcome = _run(tmp_path, instance, _solve_program(a1, a2, b1, b2), BUDGET)
    assert outcome.status == "OK"
    assert outcome.result == (a1 - a2) * pow(b2 - b1, -1, N) % N
    assert outcome.count == 0

    refused = _run(tmp_path, instance, _solve_program(a1, a2, 6, 6), BUDGET)
    assert refused.status == "REFUSED"
    assert refused.reason == "zero_denominator"
    assert refused.exit_code == 3


NESTED_LOOP = "iset i0 10\nouter:\niset i1 10\ninner:\nisub i1 i1 1\njnz i1 inner\nisub i0 i0 1\njnz i0 outer\nhalt"


@pytest.mark.parametrize(
    ("program", "budget", "reason"),
    [
        pytest.param(
            "iset i0 1048575\niadd i0 i0 1\nhalt", BUDGET, "index_out_of_range", id="counter_or_index_overflow"
        ),
        pytest.param(NESTED_LOOP, 50, "budget_exhausted", id="nested_loop_budget"),
        pytest.param(
            "table t0 4\niset i0 4\nsetp p0 P\ntstore t0 i0 p0 s0 s1\nhalt",
            BUDGET,
            "index_out_of_bounds",
            id="out_of_bounds",
        ),
        pytest.param(_solve_program(3, 1, 6, 6), BUDGET, "zero_denominator", id="zero_denominator"),
    ],
)
def test_the_five_planted_negatives_refuse_for_the_stated_reason(tmp_path, program, budget, reason):
    outcome = _run(tmp_path, _instance(POINTS[1], POINTS[1]), program, budget)
    assert outcome.status == "REFUSED"
    assert outcome.reason == reason
    assert outcome.exit_code == 3


def test_the_nested_loop_completes_under_a_sufficient_budget(tmp_path):
    outcome = _run(tmp_path, _instance(POINTS[1], POINTS[1]), NESTED_LOOP, BUDGET)
    assert outcome.status == "OK"


def test_a_malformed_or_off_curve_point_is_refused_ahead_of_execution(tmp_path):
    program = "setp p0 P\nhalt"
    off_curve = _run(tmp_path, _instance((1, 2), POINTS[1]), program, BUDGET)
    assert (off_curve.status, off_curve.reason, off_curve.exit_code) == ("REFUSED", "point_not_on_curve", 2)

    text = countedvm.document(_instance(POINTS[1], POINTS[1]), program, BUDGET)
    malformed = _run_text(tmp_path, text.replace("P " + _inf_or_text(POINTS[1]), "P 1 x", 1))
    assert (malformed.status, malformed.reason, malformed.exit_code) == ("REFUSED", "point_malformed", 2)

    even = _run(tmp_path, Instance(22, A, B, N, None, None), program, BUDGET)
    assert (even.status, even.reason, even.exit_code) == ("REFUSED", "field_not_odd_or_too_wide", 2)

    singular = _run(tmp_path, Instance(P_FIELD, 0, 0, N, None, None), program, BUDGET)
    assert (singular.status, singular.reason, singular.exit_code) == ("REFUSED", "curve_singular", 2)


def test_an_unknown_instruction_and_a_missing_halt_are_refused(tmp_path):
    instance = _instance(POINTS[1], POINTS[1])
    unknown = _run(tmp_path, instance, "frobnicate p0\nhalt", BUDGET)
    assert (unknown.status, unknown.reason, unknown.exit_code) == ("REFUSED", "instruction_malformed", 3)

    unfinished = _run(tmp_path, instance, "setp p0 P", BUDGET)
    assert (unfinished.status, unfinished.reason, unfinished.exit_code) == ("REFUSED", "no_halt", 3)


def test_the_counting_convention_is_written_and_names_every_group_opcode():
    for opcode in ("addp", "dblp", "negp", "mulp", "solve"):
        assert opcode in countedvm.COUNTING_CONVENTION
        assert isinstance(countedvm.COUNTING_CONVENTION[opcode], str)
        assert countedvm.COUNTING_CONVENTION[opcode].strip()


def _table_program(query_multiple):
    lines = ["setp p1 P", "table t0 8"]
    for index, multiple in enumerate((2, 3, 4)):
        lines += [
            f"sset s0 {multiple}",
            "mulp p2 p1 s0",
            f"iset i1 {index}",
            "tstore t0 i1 p2 s0 s0",
        ]
    lines += [f"sset s0 {query_multiple}", "mulp p3 p1 s0", "tfind i0 t0 p3", "halt"]
    return "\n".join(lines)


def test_partition_and_table_lookup_report_through_i0(tmp_path):
    for point in POINTS:
        outcome = _run(tmp_path, _instance(point, point), "setp p0 P\npartition i0 p0 4\nhalt", BUDGET)
        assert outcome.status == "OK", point
        assert outcome.i0 == (0 if point is None else point[0] & 15), point

    generator = max(
        (point for point in POINTS if point is not None), key=lambda c: int(pari.ellorder(CURVE, _pari_point(c)))
    )
    assert int(pari.ellorder(CURVE, _pari_point(generator))) >= 6
    instance = _instance(generator, generator)
    for multiple, expected in ((2, 1), (3, 2), (4, 3), (1, 0), (5, 0)):
        outcome = _run(tmp_path, instance, _table_program(multiple), BUDGET)
        assert outcome.status == "OK", multiple
        assert outcome.i0 == expected, multiple


@pytest.mark.parametrize(
    ("instance", "reason"),
    [
        (Instance(9, 1, 1, 9, (0, 1), (0, 1)), "field_not_prime"),
        (Instance(561, 1, 1, 5, None, None), "field_not_prime"),
        (Instance(675405061, 0, 2, 675405061, (123456789, 75222517), (123456789, 75222517)), "order_equals_field"),
    ],
)
def test_a_composite_field_or_an_anomalous_order_is_refused(tmp_path, instance, reason):
    outcome = _run(tmp_path, instance, "halt", BUDGET)
    assert (outcome.status, outcome.reason, outcome.exit_code) == ("REFUSED", reason, 2)


def test_input_after_end_is_refused(tmp_path):
    text = countedvm.document(_instance(POINTS[1], POINTS[1]), "halt", BUDGET) + "p 23\n"
    outcome = _run_text(tmp_path, text)
    assert (outcome.status, outcome.reason, outcome.exit_code) == ("REFUSED", "trailing_input", 2)


def test_a_table_scan_stops_at_the_budget(tmp_path):
    program = "table t0 1048575\nsetp p1 P\ntfind i0 t0 p1\nhalt"
    outcome = _run(tmp_path, _instance(POINTS[1], POINTS[1]), program, 10)
    assert (outcome.status, outcome.reason, outcome.executed, outcome.exit_code) == (
        "REFUSED",
        "budget_exhausted",
        10,
        3,
    )
    enough = _run(tmp_path, _instance(POINTS[1], POINTS[1]), "table t0 4\nsetp p1 P\ntfind i0 t0 p1\nhalt", 10)
    assert (enough.status, enough.i0, enough.executed) == ("OK", 0, 8)


def test_the_last_slot_of_the_largest_table_is_found(tmp_path):
    program = "table t0 1048575\niset i1 1048574\ntstore t0 i1 p0 s0 s0\ntfind i0 t0 p0\nhalt"
    outcome = _run(tmp_path, _instance(None, None), program, 2_000_000)
    assert (outcome.status, outcome.i0) == ("OK", 1048575)
    too_large = _run(tmp_path, _instance(None, None), "table t0 1048576\nhalt", 10)
    assert (too_large.status, too_large.reason) == ("REFUSED", "instruction_malformed")


def test_a_table_name_past_the_last_table_is_refused(tmp_path):
    outcome = _run(tmp_path, _instance(POINTS[1], POINTS[1]), "table t4 1\nhalt", BUDGET)
    assert (outcome.status, outcome.reason, outcome.exit_code) == ("REFUSED", "instruction_malformed", 3)


def test_solve_is_a_once_only_finalization(tmp_path):
    prelude = "sset s0 5\nsset s1 1\nsset s2 0\nsset s3 3\nsolve s4 s0 s1 s2 s3\n"
    reused = _run(tmp_path, _instance(POINTS[1], POINTS[1]), prelude + "sadd s5 s4 s4\nhalt", BUDGET)
    assert (reused.status, reused.reason, reused.exit_code) == ("REFUSED", "solve_not_final", 3)
    final = _run(tmp_path, _instance(POINTS[1], POINTS[1]), prelude + "result s4\nhalt", BUDGET)
    assert final.status == "OK"
    assert final.result == (4 * pow(3, -1, N)) % N


def test_untouched_point_registers_hold_infinity(tmp_path):
    point = POINTS[1]
    outcome = _run(tmp_path, _instance(point, point), "setp p1 P\naddp p0 p1 p2\nhalt", BUDGET)
    assert (outcome.status, outcome.count, outcome.p0) == ("OK", 1, point)


def test_tfind_matches_a_stored_infinity(tmp_path):
    program = "table t0 2\nsetp p1 inf\niset i1 0\ntstore t0 i1 p1 s0 s0\ntfind i0 t0 p1\nhalt"
    outcome = _run(tmp_path, _instance(POINTS[1], POINTS[1]), program, BUDGET)
    assert (outcome.status, outcome.i0) == ("OK", 1)


@pytest.mark.parametrize(
    ("stdout", "exit_code"),
    [
        ('{"status":"REFUSED","reason":"x","count":0,"executed":1}', 2),
        ('{"status":"REFUSED","reason":"x"}', 3),
        ('{"status":"REFUSED","reason":"x","count":-1,"executed":[]}', 3),
        ('{"status":"REFUSED","reason":""}', 2),
    ],
)
def test_a_refusal_whose_shape_does_not_match_its_exit_code_is_refused_by_the_decoder(stdout, exit_code):
    with pytest.raises(countedvm.CountedVmError):
        countedvm.decode(stdout, exit_code)
    accepted = countedvm.decode('{"status":"REFUSED","reason":"x","count":0,"executed":1}', 3)
    assert (accepted.status, accepted.reason, accepted.count, accepted.executed) == ("REFUSED", "x", 0, 1)
