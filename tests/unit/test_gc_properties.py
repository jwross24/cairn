import pytest
from hypothesis import assume, given
from hypothesis import strategies as st
from mutants import gc_mutants

from cairn import gc

NODE_POOL = tuple(f"h{i:02d}" for i in range(30))
EDGE_KINDS = ("output_of", "input", "member", "certifies")

node = st.sampled_from(NODE_POOL)
edge = st.tuples(node, node, st.sampled_from(EDGE_KINDS))
edges_strategy = st.lists(edge)
connected_edges_strategy = st.lists(edge, min_size=1)
roots_strategy = st.frozensets(node)
blobs_strategy = st.frozensets(node)

INTEGRATION_KILLED = frozenset({"collect_one_page_only"})


def draw_roots_touching(edges, data):
    pool = sorted({n for child, parent, _kind in edges for n in (child, parent)})
    return frozenset(data.draw(st.lists(st.sampled_from(pool), min_size=1, unique=True)))


def walks_to_a_root(start, roots, edges):
    frontier = [start]
    visited = {start}
    while frontier:
        current = frontier.pop(0)
        if current in roots:
            return True
        for child, parent, _kind in edges:
            for near, far in ((child, parent), (parent, child)):
                if near == current and far not in visited:
                    visited.add(far)
                    frontier.append(far)
    return False


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
    assume(v in before)
    edges_minus = [x for x in edges if x != e]
    after = gc.reachable(roots, edges_minus)
    assert v not in after


def check_mr_sym(roots, edges):
    reversed_edges = [(parent, child, kind) for child, parent, kind in edges]
    assert gc.reachable(roots, edges) == gc.reachable(roots, reversed_edges)


def check_mr_comp(roots, edges, blobs):
    reach = gc.reachable(roots, edges)
    coll = gc.collectable(roots, edges, blobs)
    for candidate in coll:
        assert not walks_to_a_root(candidate, roots, edges)
    assert coll & reach == set()


@given(roots_strategy, edges_strategy, node)
def test_mr_r_adding_a_root_never_shrinks_reachability(roots, edges, new_root):
    check_mr_r(roots, edges, new_root)


@given(connected_edges_strategy, st.data())
def test_mr_e_removing_an_edge_never_grows_reachability(edges, data):
    assume(edges)
    roots = draw_roots_touching(edges, data)
    e = data.draw(st.sampled_from(edges))
    check_mr_e(roots, edges, e)


@given(connected_edges_strategy, st.sampled_from(EDGE_KINDS), st.data())
def test_mr_e_the_only_edge_touching_a_node_drops_it(edges, kind, data):
    roots = draw_roots_touching(edges, data)
    v = data.draw(node)
    assume(v not in roots)
    filtered = [x for x in edges if v not in (x[0], x[1])]
    attachments = sorted(gc.reachable(roots, filtered) - {v})
    assume(attachments)
    e = (v, data.draw(st.sampled_from(attachments)), kind)
    check_mr_e_only_edge_drops_node(roots, [*filtered, e], e, v)


@given(roots_strategy, edges_strategy)
def test_mr_sym_reachability_is_symmetric_in_edge_direction(roots, edges):
    check_mr_sym(roots, edges)


@given(roots_strategy, edges_strategy, blobs_strategy)
def test_mr_comp_no_candidate_walks_to_a_root(roots, edges, blobs):
    check_mr_comp(roots, edges, blobs)


KILLED_BY = {
    "reachable_from_last_root_only": lambda: check_mr_r({"h00"}, [("h01", "h02", "input")], "h01"),
    "reachable_cached_by_roots_only": lambda: check_mr_e_only_edge_drops_node(
        {"h00"}, [("h00", "h01", "input")], ("h00", "h01", "input"), "h01"
    ),
    "reachable_directed_child_to_parent": lambda: check_mr_sym({"h00"}, [("h01", "h00", "output_of")]),
    "collectable_includes_rooted_blob": lambda: check_mr_comp({"h00"}, [("h01", "h00", "member")], {"h01"}),
}


@pytest.mark.parametrize("name", sorted(KILLED_BY))
def test_every_named_mutant_is_killed_by_its_relation(name):
    relation = KILLED_BY[name]
    relation()
    with gc_mutants.ALL[name](), pytest.raises(AssertionError):
        relation()


def test_the_mutant_catalog_and_the_relation_map_agree():
    assert sorted(gc_mutants.ALL) == sorted(set(KILLED_BY) | INTEGRATION_KILLED)
