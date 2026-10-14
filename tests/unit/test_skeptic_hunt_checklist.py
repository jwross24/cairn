import re

import pytest

from cairn import bundle, dispatch, roles

ITEMS = (
    "Predicate fidelity",
    "Population",
    "Budget and calibration",
    "Standing",
    "Controls and plants",
    "Seeds and entropy",
    "Exactness",
    "Independence",
)
ITEM_KEYWORDS = (
    "quantifier order",
    "the sampled point",
    "every derived quantity",
    "declared sampling distribution",
    "do not cover",
    "declared and completed trial counts",
    "CONJECTURE ceiling",
    "supplies no proof",
    "must-FAIL observations",
    "certificate-authenticated fields from companion metadata",
    "known-true and known-false controls",
    "outside the handed statement's scope or absent, report a gap",
    "typed entropy commitment",
    "withholding and order",
    "integer, rational, and floating-point",
    "boundary behavior",
    "arithmetic backend",
    "an independent check that did not occur",
)
RESPONSE_KEYWORDS = (
    "one JSON object and nothing else",
    "no code fence",
    "statement_hash, verdict and items",
    "id, outcome, answer and cited_node_hashes",
    "clear, gap or issue",
    "a hash that was not read is not a citation",
    "no proof or tag promotion",
)


@pytest.fixture
def checklist(pinned_bundle):
    return roles.load(bundle.GateBundle.open(*pinned_bundle()), roles.SKEPTIC_HUNT)[0]


def test_the_items_are_numbered_one_to_eight_in_the_order_the_record_binds(checklist):
    numbered = re.findall(r"^\s*(\d+)\.\s+([^.]+)\.", checklist, re.MULTILINE)
    assert tuple(int(number) for number, _ in numbered) == tuple(range(1, len(ITEMS) + 1))
    assert tuple(title for _, title in numbered) == ITEMS


@pytest.mark.parametrize("keyword", ITEM_KEYWORDS + RESPONSE_KEYWORDS)
def test_the_checklist_carries_its_wording(checklist, keyword):
    assert keyword in checklist


def test_the_checklist_names_no_claim_digest(checklist):
    assert roles.claim_reference(checklist) is None


def test_a_checklist_naming_a_claim_digest_is_refused(checklist):
    with pytest.raises(roles.RoleTemplateError, match="claim-agnostic"):
        roles.check_claim_agnostic(roles.SKEPTIC_HUNT, checklist + "\n" + "ab" * 16)


def test_the_shipped_skeptic_role_runs_the_hunt_checklist_with_read_only_tools(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    registry = gate.object(dispatch.ROLE_CONFIG)
    assert registry == {
        "skeptic": {
            "template": roles.SKEPTIC_HUNT,
            "tools": ["mcp__cairn_skeptic__list_nodes", "mcp__cairn_skeptic__read_node"],
            "model": "claude-opus-5-5",
            "max_turns": 32,
            "timeout_s": 600,
            "thinking": "adaptive",
        }
    }
    assert gate.object("skeptic_scope") == {"evidence_kinds": ["counterexample_hunt_record"]}
