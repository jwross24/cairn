"""Role templates as read-only gate-bundle config: the Skeptic's checklist and the Prover's brief.

A template is claim-agnostic prose pinned by the bundle hash. It names no claim digest and carries no
gate internals, and it reaches a worker only through a dispatch that records the content address
of the text it handed, so which checklist a Skeptic ran under is a ledger fact. The bytes live in
the bundle store the orchestrator opens read-only: a different checklist is a different pin.
"""

import re

from cairn import log
from cairn.bundle import BundleError
from cairn.substrate import blob_hash

lg = log.get("roles")

BUNDLE_KIND = "role_templates"
SKEPTIC = "skeptic_checklist"
PROVER = "prover_brief"
NAMES = (PROVER, SKEPTIC)
CLAIM_HASH = re.compile(r"\b[0-9a-fA-F]{32,}\b")


class RoleTemplateError(BundleError):
    pass


def templates(gate_bundle):
    obj = gate_bundle.object(BUNDLE_KIND)
    if not isinstance(obj, dict) or not obj:
        raise RoleTemplateError(f"the {BUNDLE_KIND} object must be a nonempty mapping")
    for name, text in sorted(obj.items()):
        if not isinstance(name, str) or not isinstance(text, str) or not text.strip():
            raise RoleTemplateError(f"role template {name!r} must be nonempty text")
    return obj


def claim_reference(text):
    found = CLAIM_HASH.search(text)
    return None if found is None else found.group(0)


def check_claim_agnostic(name, text):
    found = claim_reference(text)
    if found is not None:
        raise RoleTemplateError(f"role template {name!r} names claim digest {found}; a role template is claim-agnostic")


def load(gate_bundle, name):
    obj = templates(gate_bundle)
    if name not in obj:
        raise RoleTemplateError(f"gate bundle {gate_bundle.hash} carries no {BUNDLE_KIND} entry {name!r}")
    text = obj[name]
    check_claim_agnostic(name, text)
    digest = blob_hash(text.encode())
    lg.info("load", bundle_hash=gate_bundle.hash, template=name, template_hash=digest)
    return text, digest
