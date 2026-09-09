import json
import random
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cairn import ec
from cairn.skills import order_bsgs_gmpy2 as gm

ROOT = Path(__file__).resolve().parents[2]
DLP = json.loads((ROOT / "tests" / "vectors" / "dlp_instances.json").read_text())["instances"]
CURVE60 = json.loads((ROOT / "tests" / "vectors" / "curve60_seed1.json").read_text())
LIBPARI = ("cairn.pari", "cypari2", "cypari2.pari_instance")
TINY = (23, 0, 1, (0, 1), 24)


def _curve(row):
    return int(row["p"]), int(row["a"]), int(row["b"]), int(row["n"]), tuple(int(c) for c in row["P"])


KNOWN = [(name, _curve(row)) for name, row in DLP.items()] + [("bits60_seed1", _curve(CURVE60))]


def _brute_force_order(p, a, b):
    return 1 + sum(1 for x in range(p) for y in range(p) if ec.is_on_curve(p, a, b, (x, y)))


def _imported_modules(source):
    proc = subprocess.run(
        [sys.executable, "-c", f"{source}\nimport json, sys\nprint(json.dumps(sorted(sys.modules)))"],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    )
    return set(json.loads(proc.stdout))


@pytest.mark.parametrize(("name", "curve"), KNOWN, ids=[n for n, _ in KNOWN])
def test_the_recovered_order_matches_the_recorded_order_on_every_known_curve(name, curve):
    p, a, b, n, point = curve
    assert gm.orders_in_hasse(p, a, b, point) == (n,)
    assert gm.group_order(p, a, b, [point]) == n


@pytest.mark.parametrize(("name", "curve"), KNOWN, ids=[n for n, _ in KNOWN])
def test_every_order_the_search_returns_annihilates_the_point(name, curve):
    p, a, b, _, point = curve
    for m in gm.orders_in_hasse(p, a, b, point):
        assert gm.mul(p, a, gm.require_on_curve(p, a, b, point, "P"), m) is None


@pytest.mark.parametrize(("name", "curve"), KNOWN, ids=[n for n, _ in KNOWN])
def test_the_recovered_order_lies_inside_the_hasse_interval(name, curve):
    p, a, b, n, _ = curve
    low, high = gm.hasse_interval(p)
    assert low <= n <= high
    assert (n - (p + 1)) ** 2 <= 4 * p


@pytest.mark.parametrize("p", [23, 175757327, 922854029, int(CURVE60["p"])])
def test_the_interval_bound_is_the_floor_of_two_root_p(p):
    low, high = gm.hasse_interval(p)
    bound = (high - low) // 2
    assert bound * bound <= 4 * p < (bound + 1) * (bound + 1)
    assert low == p + 1 - bound and high == p + 1 + bound


@pytest.mark.parametrize("p", [23, 175757327, 922854029, int(CURVE60["p"])])
def test_the_search_width_covers_the_interval_in_about_its_square_root_of_steps(p):
    low, high = gm.hasse_interval(p)
    width = gm.search_width(p)
    assert width * width >= high - low
    assert (width - 1) * (width - 1) <= high - low


def test_the_gmp_arithmetic_agrees_with_the_plain_python_implementation():
    p, a, b, n, point = _curve(DLP["bits30_seed1"])
    rng = random.Random(20260909)
    left, right = point, ec.mul(p, a, point, rng.randrange(1, n))
    walked = tuple(int(c) for c in gm.add(p, a, gm.mul(p, a, point, 1), tuple(right)))
    assert walked == ec.add(p, a, left, right)
    for _ in range(200):
        k = rng.randrange(1, n)
        theirs = ec.mul(p, a, point, k)
        ours = gm.mul(p, a, gm.require_on_curve(p, a, b, point, "P"), k)
        assert (None if ours is None else tuple(int(c) for c in ours)) == theirs
        assert ec.sub(p, a, theirs, theirs) is None


def test_a_point_that_is_not_on_the_curve_refuses():
    p, a, b, _, point = _curve(DLP["bits30_seed1"])
    with pytest.raises(gm.NotOnCurve):
        gm.orders_in_hasse(p, a, b, (point[0], point[1] + 1))
    with pytest.raises(gm.NotOnCurve):
        gm.orders_in_hasse(p, a, b, None)


def test_a_small_order_point_leaves_several_candidates_that_a_second_point_settles():
    p, a, b, small, order = TINY
    assert _brute_force_order(p, a, b) == order
    candidates = gm.orders_in_hasse(p, a, b, small)
    assert len(candidates) > 1
    assert order in candidates
    with pytest.raises(gm.OrderAmbiguous) as raised:
        gm.group_order(p, a, b, [small])
    assert tuple(int(m) for m in raised.value.candidates) == tuple(int(m) for m in candidates)
    generator = next(
        (x, y)
        for x in range(p)
        for y in range(p)
        if ec.is_on_curve(p, a, b, (x, y)) and gm.orders_in_hasse(p, a, b, (x, y)) == (order,)
    )
    assert gm.group_order(p, a, b, [small, generator]) == order


def test_a_point_from_another_curve_refuses_before_any_search():
    p, a, b, _, point = _curve(DLP["bits30_seed1"])
    with pytest.raises(gm.NotOnCurve):
        gm.group_order(p, a + 1, b, [point])


def test_naming_no_point_at_all_settles_no_order():
    p, a, b, _, _ = _curve(DLP["bits30_seed1"])
    with pytest.raises(gm.OrderAmbiguous) as raised:
        gm.group_order(p, a, b, [])
    assert raised.value.candidates == ()


def test_importing_the_module_pulls_in_no_libpari():
    loaded = _imported_modules("from cairn.skills import order_bsgs_gmpy2")
    assert "gmpy2" in loaded
    assert loaded.isdisjoint(LIBPARI)


def test_the_import_graph_assertion_can_fail():
    assert not _imported_modules("import cairn.pari").isdisjoint(LIBPARI)


def test_module_defined_public_api_is_closed():
    public = {
        name
        for name, value in vars(gm).items()
        if not name.startswith("_") and callable(value) and getattr(value, "__module__", None) == gm.__name__
    }
    assert public == {
        "NotOnCurve",
        "OrderAmbiguous",
        "add",
        "double",
        "group_order",
        "hasse_interval",
        "is_on_curve",
        "mul",
        "neg",
        "orders_in_hasse",
        "require_on_curve",
        "search_width",
        "sub",
    }


SMALL_PRIMES = (23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97, 101, 103, 107, 109, 113, 127)


@given(
    p=st.sampled_from(SMALL_PRIMES),
    a=st.integers(min_value=0, max_value=126),
    b=st.integers(min_value=0, max_value=126),
)
@settings(max_examples=60, deadline=None)
def test_property_the_true_group_order_is_always_among_the_candidates(p, a, b):
    a, b = a % p, b % p
    assume((4 * a * a * a + 27 * b * b) % p != 0)
    points = [(x, y) for x in range(p) for y in range(p) if ec.is_on_curve(p, a, b, (x, y))]
    assume(points)
    order = len(points) + 1
    low, high = gm.hasse_interval(p)
    for point in points:
        candidates = gm.orders_in_hasse(p, a, b, point)
        assert order in candidates
        for m in candidates:
            assert low <= m <= high
            assert gm.mul(p, a, gm.require_on_curve(p, a, b, point, "P"), m) is None
