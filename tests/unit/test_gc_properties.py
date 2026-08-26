import pytest
from hypothesis import given
from hypothesis import strategies as st
from mutants import gc_mutants

from cairn import gc

NODE_POOL = tuple(f"h{i:02d}" for i in range(30))
EDGE_KINDS = ("output_of", "input", "member", "certifies")

node = st.sampled_from(NODE_POOL)
edge = st.tuples(node, node, st.sampled_from(EDGE_KINDS))
edges_strategy = st.lists(edge)
roots_strategy = st.frozensets(node)
blobs_strategy = st.frozensets(node)


def check_mr_r(roots, edges, new_root):
    before = gc.reachable(roots, edges)
    after = gc.reachable(set(roots) | {new_root}, edges)
    assert after >= before


def check_mr_e(roots, edges, e):
    before = gc.reachable(roots, edges)
    edges_minus = list(edges)
    edges_minus.remove(e)
    after = gc.reachable(roots, edges_minus)
    assert after <= before


def check_mr_e_only_edge_drops_node(roots, edges, e, v):
    before = gc.reachable(roots, edges)
    if v not in before:
        return
    edges_minus = [x for x in edges if x != e]
    after = gc.reachable(roots, edges_minus)
    assert v not in after


def check_mr_sym(roots, edges):
    reversed_edges = [(parent, child, kind) for child, parent, kind in edges]
    assert gc.reachable(roots, edges) == gc.reachable(roots, reversed_edges)


def check_mr_comp(roots, edges, blobs):
    reach = gc.reachable(roots, edges)
    coll = gc.collectable(roots, edges, blobs)
    assert coll == set(blobs) - reach
    assert coll & reach == set()


@given(roots_strategy, edges_strategy, node)
def test_mr_r_adding_a_root_never_shrinks_reachability(roots, edges, new_root):
    check_mr_r(roots, edges, new_root)


@given(roots_strategy, edges_strategy, st.data())
def test_mr_e_removing_an_edge_never_grows_reachability(roots, edges, data):
    if not edges:
        return
    e = data.draw(st.sampled_from(edges))
    check_mr_e(roots, edges, e)


@given(v=node, other=node, kind=st.sampled_from(EDGE_KINDS), roots=roots_strategy, edges=edges_strategy)
def test_mr_e_the_only_edge_touching_a_node_drops_it(v, other, kind, roots, edges):
    if v == other or v in roots:
        return
    filtered = [x for x in edges if v not in (x[0], x[1])]
    e = (v, other, kind)
    full_edges = [*filtered, e]
    check_mr_e_only_edge_drops_node(roots, full_edges, e, v)


@given(roots_strategy, edges_strategy)
def test_mr_sym_reachability_is_symmetric_in_edge_direction(roots, edges):
    check_mr_sym(roots, edges)


@given(roots_strategy, edges_strategy, blobs_strategy)
def test_mr_comp_collectable_is_the_reachability_complement(roots, edges, blobs):
    check_mr_comp(roots, edges, blobs)


def test_mutant_reachable_from_last_root_only_is_killed():
    with gc_mutants.reachable_from_last_root_only(), pytest.raises(AssertionError):
        check_mr_r({"h00"}, [("h01", "h02", "input")], "h01")


def test_mutant_reachable_cached_by_roots_only_is_killed():
    roots = {"h00"}
    edges = [("h00", "h01", "input")]
    e = ("h00", "h01", "input")
    with gc_mutants.reachable_cached_by_roots_only(), pytest.raises(AssertionError):
        check_mr_e_only_edge_drops_node(roots, edges, e, "h01")


def test_mutant_reachable_directed_child_to_parent_is_killed():
    with gc_mutants.reachable_directed_child_to_parent(), pytest.raises(AssertionError):
        check_mr_sym({"h00"}, [("h01", "h00", "output_of")])


def test_mutant_collectable_includes_rooted_blob_is_killed():
    with gc_mutants.collectable_includes_rooted_blob(), pytest.raises(AssertionError):
        check_mr_comp({"h00"}, [("h01", "h00", "member")], {"h01"})
