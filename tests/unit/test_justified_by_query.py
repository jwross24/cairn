from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cairn import foundations
from cairn.foundations import CONJECTURE, PROVEN, SPECULATION, STRONG_EMPIRICAL, Violation

ROOT, A, B, C = ("r" * 64, "a" * 64, "b" * 64, "c" * 64)
CHAIN = [(ROOT, A), (A, B), (B, C)]
CLASSES = foundations.CLASSES


def test_fixture_h_a_proven_claim_over_a_conjecture_three_hops_down_is_found_with_its_path():
    tags = {ROOT: PROVEN, A: PROVEN, B: PROVEN, C: CONJECTURE}
    found = foundations.violations_in(CHAIN, tags, ROOT)
    assert found == [Violation((ROOT, A, B, C), PROVEN, CONJECTURE)]
    assert (found[0].dependent, found[0].premise, found[0].depth) == (B, C, 3)


def test_a_chain_of_equal_or_stronger_premises_yields_nothing():
    assert foundations.violations_in(CHAIN, {ROOT: PROVEN, A: PROVEN, B: PROVEN, C: PROVEN}, ROOT) == []
    assert foundations.violations_in(CHAIN, {ROOT: CONJECTURE, A: STRONG_EMPIRICAL, B: PROVEN, C: PROVEN}, ROOT) == []
    assert foundations.violations_in(CHAIN, {}, ROOT) == []


def test_a_weak_premise_is_reported_at_every_depth_it_sits_under_a_stronger_dependent():
    tags = {ROOT: PROVEN, A: CONJECTURE, B: PROVEN, C: STRONG_EMPIRICAL}
    found = foundations.violations_in(CHAIN, tags, ROOT)
    assert [(v.dependent, v.premise) for v in found] == [(ROOT, A), (B, C)]


def test_a_missing_tag_reads_as_speculation():
    assert foundations.rank(None) == 0
    found = foundations.violations_in([(ROOT, A)], {ROOT: CONJECTURE}, ROOT)
    assert found == [Violation((ROOT, A), CONJECTURE, SPECULATION)]


def test_paths_follow_every_branch_of_a_diamond_and_never_loop():
    edges = [(ROOT, A), (ROOT, B), (A, C), (B, C), (C, ROOT)]
    paths = foundations.paths_in(foundations._edge_map(edges), ROOT)
    assert paths == [(ROOT, A), (ROOT, B), (ROOT, A, C), (ROOT, B, C)]


@st.composite
def dags(draw):
    n = draw(st.integers(min_value=2, max_value=7))
    nodes = [f"{i:064d}" for i in range(n)]
    edges = [(nodes[i], nodes[j]) for i in range(n) for j in range(i + 1, n) if draw(st.booleans())]
    tags = {}
    for i in reversed(range(n)):
        premises = [p for c, p in edges if c == nodes[i]]
        ceiling = min((CLASSES.index(tags[p]) for p in premises), default=len(CLASSES) - 1)
        tags[nodes[i]] = CLASSES[draw(st.integers(min_value=0, max_value=ceiling))]
    return nodes, edges, tags


@settings(max_examples=150)
@given(dags())
def test_property_a_monotone_dag_has_no_violation_from_any_root(case):
    nodes, edges, tags = case
    for root in nodes:
        assert foundations.violations_in(edges, tags, root) == []


@settings(max_examples=150)
@given(dags(), st.data())
def test_property_lowering_one_premise_below_its_dependent_is_always_found(case, data):
    nodes, edges, tags = case
    candidates = [(c, p) for c, p in edges if CLASSES.index(tags[c]) > 0]
    assume(candidates)
    child, premise = data.draw(st.sampled_from(candidates))
    lowered = {**tags, premise: CLASSES[data.draw(st.integers(min_value=0, max_value=CLASSES.index(tags[child]) - 1))]}
    found = foundations.violations_in(edges, lowered, child)
    assert any(v.dependent == child and v.premise == premise for v in found)
    for root in nodes:
        for violation in foundations.violations_in(edges, lowered, root):
            assert CLASSES.index(violation.premise_tag) < CLASSES.index(violation.dependent_tag)
