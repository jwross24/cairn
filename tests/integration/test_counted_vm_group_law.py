import pytest
from _counted_vm import BUDGET, CURVE, P_FIELD, POINTS, N, lift, make_instance, pari_point, run, run_batch

from cairn import countedvm, ec
from cairn.countedvm import Instance
from cairn.pari import pari


def test_the_fixture_enumerates_the_whole_group():
    assert len(POINTS) == N
    assert int(pari.ellcard(CURVE)) == N


def test_every_pair_of_points_adds_like_pari():
    pairs = [(point_p, point_q) for point_p in POINTS for point_q in POINTS]
    outcomes = run_batch(
        [
            countedvm.document(make_instance(point_p, point_q), "setp p0 P\nsetp p1 Q\naddp p0 p0 p1\nhalt", BUDGET)
            for point_p, point_q in pairs
        ]
    )
    assert len(outcomes) == N * N
    for (point_p, point_q), outcome in zip(pairs, outcomes, strict=True):
        expected = lift(pari.elladd(CURVE, pari_point(point_p), pari_point(point_q)))
        assert outcome.status == "OK", (point_p, point_q)
        assert outcome.p0 == expected, (point_p, point_q)
        assert outcome.count == 1, (point_p, point_q)


def test_every_point_doubles_like_pari():
    documents = []
    for point in POINTS:
        documents.append(countedvm.document(make_instance(point, point), "setp p0 P\ndblp p0 p0\nhalt", BUDGET))
        documents.append(
            countedvm.document(make_instance(point, point), "setp p0 P\nsetp p1 P\naddp p0 p0 p1\nhalt", BUDGET)
        )
    outcomes = run_batch(documents)
    assert len(outcomes) == 2 * N
    for index, point in enumerate(POINTS):
        expected = lift(pari.elladd(CURVE, pari_point(point), pari_point(point)))
        doubled, added = outcomes[2 * index], outcomes[2 * index + 1]
        assert doubled.status == "OK", point
        assert doubled.p0 == expected, point
        assert doubled.count == 1, point
        assert added.status == "OK", point
        assert added.p0 == expected, point
        assert added.count == 1, point


def test_every_point_negates_like_pari_and_counts_nothing(tmp_path):
    for point in POINTS:
        outcome = run(tmp_path, make_instance(point, point), "setp p0 P\nnegp p0 p0\nhalt", BUDGET)
        assert outcome.status == "OK", point
        assert outcome.p0 == lift(pari.ellneg(CURVE, pari_point(point))), point
        assert outcome.count == 0, point


@pytest.mark.parametrize("in_place", [False, True])
def test_every_point_canonicalizes_like_the_python_rule_without_counting(tmp_path, in_place):
    for point in POINTS:
        source = "p0" if in_place else "p1"
        program = f"setp {source} P\niset i0 1\ncanonicalp p0 {source} i0\nhalt"
        outcome = run(tmp_path, make_instance(point, point), program, BUDGET, instruction_set="signed/1")
        representative, flipped = ec.canonical(P_FIELD, point)
        assert outcome.status == "OK", point
        assert outcome.p0 == representative, point
        assert outcome.i0 == int(flipped), point
        assert outcome.count == 0, point
        assert outcome.executed == 4, point
        assert outcome.instruction_set == "signed/1"


def test_scalar_multiplication_matches_pari_and_the_counting_convention(tmp_path):
    point = next(candidate for candidate in POINTS if candidate is not None and candidate[1] != 0)
    instance = make_instance(point, point)
    for k in range(2 * N):
        scalar = k % N
        outcome = run(tmp_path, instance, f"setp p0 P\nsset s0 {scalar}\nmulp p0 p0 s0\nhalt", BUDGET)
        assert outcome.status == "OK", k
        assert outcome.p0 == lift(pari.ellmul(CURVE, pari_point(point), scalar)), k
        assert outcome.count == countedvm.expected_mul_ops(scalar), k
        if scalar == 0:
            assert outcome.p0 is None
            assert outcome.count == 0


EVEN_A = 1
EVEN_B = 0
EVEN_CURVE = pari.ellinit([0, 0, 0, EVEN_A, EVEN_B], P_FIELD)
EVEN_N = int(pari.ellcard(EVEN_CURVE))
EVEN_POINTS = [None] + [
    (x, y) for x in range(P_FIELD) for y in range(P_FIELD) if (y * y - (x**3 + EVEN_A * x + EVEN_B)) % P_FIELD == 0
]


def test_the_even_order_curve_adds_and_doubles_like_pari_including_two_torsion(tmp_path):
    assert EVEN_N == 24
    assert len(EVEN_POINTS) == EVEN_N
    torsion = [point for point in EVEN_POINTS if point is not None and point[1] == 0]
    assert torsion == [(0, 0)]
    doubled = run_batch(
        [
            countedvm.document(
                Instance(P_FIELD, EVEN_A, EVEN_B, EVEN_N, point_p, point_p), "setp p0 P\ndblp p0 p0\nhalt", BUDGET
            )
            for point_p in EVEN_POINTS
        ]
    )
    assert len(doubled) == EVEN_N
    for point_p, outcome in zip(EVEN_POINTS, doubled, strict=True):
        expected = lift(pari.elladd(EVEN_CURVE, pari_point(point_p), pari_point(point_p)))
        assert (outcome.status, outcome.count, outcome.p0) == ("OK", 1, expected), point_p
    pairs = [(point_p, point_q) for point_p in EVEN_POINTS for point_q in EVEN_POINTS]
    added = run_batch(
        [
            countedvm.document(
                Instance(P_FIELD, EVEN_A, EVEN_B, EVEN_N, point_p, point_q),
                "setp p0 P\nsetp p1 Q\naddp p0 p0 p1\nhalt",
                BUDGET,
            )
            for point_p, point_q in pairs
        ]
    )
    assert len(added) == EVEN_N * EVEN_N
    for (point_p, point_q), outcome in zip(pairs, added, strict=True):
        expected = lift(pari.elladd(EVEN_CURVE, pari_point(point_p), pari_point(point_q)))
        assert (outcome.status, outcome.count, outcome.p0) == ("OK", 1, expected), (point_p, point_q)
    torsion_instance = Instance(P_FIELD, EVEN_A, EVEN_B, EVEN_N, (0, 0), (0, 0))
    doubled_torsion = run(tmp_path, torsion_instance, "setp p0 P\ndblp p0 p0\nhalt", BUDGET)
    assert (doubled_torsion.status, doubled_torsion.count, doubled_torsion.p0) == ("OK", 1, None)
    via_add = run(tmp_path, torsion_instance, "setp p0 P\nsetp p1 Q\naddp p0 p0 p1\nhalt", BUDGET)
    assert (via_add.status, via_add.count, via_add.p0) == ("OK", 1, None)
