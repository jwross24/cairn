import pytest

from cairn import gc

ALL_NODES = frozenset({"a", "b", "c", "d", "x", "y"})

SHAPES = [
    pytest.param(
        frozenset({"a"}),
        [("b", "a", "input"), ("c", "b", "input")],
        frozenset({"a", "b", "c"}),
        id="chain",
    ),
    pytest.param(
        frozenset({"a"}),
        [("b", "a", "input"), ("c", "a", "input"), ("d", "b", "member"), ("d", "c", "member")],
        frozenset({"a", "b", "c", "d"}),
        id="diamond",
    ),
    pytest.param(
        frozenset({"a"}),
        [("a", "b", "input"), ("b", "c", "input"), ("c", "a", "input")],
        frozenset({"a", "b", "c"}),
        id="cycle",
    ),
    pytest.param(
        frozenset({"a"}),
        [("a", "b", "input"), ("x", "y", "input")],
        frozenset({"a", "b"}),
        id="disconnected-component",
    ),
    pytest.param(frozenset({"a"}), [], frozenset({"a"}), id="root-without-edges"),
    pytest.param(frozenset(), [("a", "b", "input")], frozenset(), id="empty-root-set"),
]


@pytest.mark.parametrize(("roots", "edges", "expected"), SHAPES)
def test_reachability_shapes(roots, edges, expected):
    assert gc.reachable(roots, edges) == set(expected)
    assert gc.collectable(roots, edges, ALL_NODES) == ALL_NODES - set(expected)
