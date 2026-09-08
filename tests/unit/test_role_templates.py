import json

import pytest

from cairn import bundle, roles
from cairn.substrate import blob_hash

SKEPTIC_KEYWORDS = (
    "Quantifier order",
    "Strict versus non-strict",
    "Implication direction",
    "Domain and boundary",
    "ZMod 0",
    "Division by zero",
    "infimum and supremum of the empty set",
    "hypothesis set nothing satisfies",
    "existential-implication trap",
    "binder predicate",
    "conjunction-nested",
    "Linter-green is not trap-free",
    "ExistsImplicationLinter",
    "Implicit binders and universes",
    "Coercions and inferred instances",
    "Existence versus uniqueness",
    "purpose of a contradiction argument",
    "fidelity defect",
    "Independence axes",
    "author and context",
    "mathematical route",
    "encoding of the statement",
    "implementation",
    "arithmetic backend",
    "kernel",
)
PROVER_KEYWORDS = (
    "handed nodes are the problem",
    "no gate internals",
    "typed objects and never as prose",
    "named gap is progress",
)


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


def test_module_defined_public_api_is_closed():
    public = {
        name
        for name, value in vars(roles).items()
        if not name.startswith("_") and callable(value) and getattr(value, "__module__", None) == roles.__name__
    }
    assert public == {"RoleTemplateError", "templates", "claim_reference", "check_claim_agnostic", "load"}
    assert (roles.BUNDLE_KIND, roles.SKEPTIC, roles.PROVER, roles.NAMES) == (
        "role_templates",
        "skeptic_checklist",
        "prover_brief",
        ("prover_brief", "skeptic_checklist"),
    )


@pytest.mark.parametrize("name", roles.NAMES)
def test_every_named_template_loads_from_the_bundle_by_its_content_address(shipped, name):
    text, digest = roles.load(shipped, name)
    assert text.strip()
    assert digest == blob_hash(text.encode())
    assert shipped.object(roles.BUNDLE_KIND)[name] == text


def test_the_bundle_carries_exactly_the_named_templates(shipped):
    assert tuple(sorted(roles.templates(shipped))) == roles.NAMES


@pytest.mark.parametrize("keyword", SKEPTIC_KEYWORDS)
def test_the_skeptic_checklist_carries_its_item(shipped, keyword):
    assert keyword in roles.load(shipped, roles.SKEPTIC)[0]


@pytest.mark.parametrize("keyword", PROVER_KEYWORDS)
def test_the_prover_brief_carries_its_item(shipped, keyword):
    assert keyword in roles.load(shipped, roles.PROVER)[0]


@pytest.mark.parametrize("name", roles.NAMES)
def test_a_shipped_template_carries_no_claim_digest(shipped, name):
    assert roles.claim_reference(roles.load(shipped, name)[0]) is None


@pytest.mark.parametrize(
    "text",
    [
        "Audit statement " + "ab" * 32 + ".",
        "Audit statement " + "AB" * 32 + ".",
        "Audit statement " + "a" * 65 + ".",
        "Audit statement " + "ab" * 16 + "-" + "cd" * 16 + ".",
        "Audit statement " + "ab" * 16 + ".",
    ],
)
def test_every_digest_shape_a_claim_can_wear_is_refused(text):
    assert roles.claim_reference(text) is not None
    with pytest.raises(roles.RoleTemplateError, match="claim-agnostic"):
        roles.check_claim_agnostic(roles.SKEPTIC, text)


def test_the_predicate_reaches_only_digests_and_not_prose():
    assert roles.claim_reference("Prove rho-60 falls on curve P-256 under 2^40 operations.") is None
    assert roles.claim_reference("See cairn-m1-cqt.6.2 for the statement.") is None


def test_a_template_naming_a_claim_statement_hash_is_refused(tmp_path, pinned_bundle):
    source = tmp_path / "source"
    source.mkdir()
    for path in (bundle.REPO_ROOT / "bundle").glob("*.json"):
        (source / path.name).write_text(path.read_text())
    statement = "ab" * 32
    (source / "role_templates.json").write_text(
        json.dumps({roles.PROVER: "Fine.", roles.SKEPTIC: f"Audit statement {statement} closely."})
    )
    gate_bundle = bundle.GateBundle.open(*pinned_bundle(name="planted", src=source))
    with pytest.raises(roles.RoleTemplateError, match=f"names claim digest {statement}"):
        roles.load(gate_bundle, roles.SKEPTIC)
    assert roles.load(gate_bundle, roles.PROVER)[0] == "Fine."


def test_an_absent_template_fails_closed(shipped):
    with pytest.raises(roles.RoleTemplateError, match="carries no role_templates entry 'auditor_brief'"):
        roles.load(shipped, "auditor_brief")


@pytest.mark.parametrize("obj", [{}, {"prover_brief": "   "}, {"prover_brief": 7}])
def test_a_malformed_templates_object_fails_closed(shipped, monkeypatch, obj):
    monkeypatch.setitem(shipped._decoded, roles.BUNDLE_KIND, obj)
    with pytest.raises(roles.RoleTemplateError):
        roles.templates(shipped)


def test_editing_a_template_moves_the_bundle_hash(tmp_path, pinned_bundle):
    source = tmp_path / "source"
    source.mkdir()
    for path in (bundle.REPO_ROOT / "bundle").glob("*.json"):
        (source / path.name).write_text(path.read_text())
    before = bundle.GateBundle.open(*pinned_bundle(name="before", src=source))
    edited = dict(before.object(roles.BUNDLE_KIND))
    edited[roles.SKEPTIC] = edited[roles.SKEPTIC] + "\n11. One more item.\n"
    (source / "role_templates.json").write_text(json.dumps(edited))
    after = bundle.GateBundle.open(*pinned_bundle(name="after", src=source))
    assert after.hash != before.hash
    assert roles.load(after, roles.SKEPTIC)[1] != roles.load(before, roles.SKEPTIC)[1]
