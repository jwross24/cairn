"""Role templates as read-only gate-bundle config: the Skeptic's checklist and the Prover's brief.

A template is claim-agnostic prose pinned by the bundle hash. It names no claim digest and carries no
gate internals, and it reaches a worker only through a dispatch that records the content address
of the text it handed, so which checklist a Skeptic ran under is a ledger fact. The bytes live in
the bundle store the orchestrator opens read-only: a different checklist is a different pin.
"""

import re
from dataclasses import dataclass

from cairn import log
from cairn.bundle import BundleError
from cairn.substrate import blob_hash

lg = log.get("roles")

BUNDLE_KIND = "role_templates"
SKEPTIC = "skeptic_checklist"
SKEPTIC_HUNT = "skeptic_hunt_checklist"
PROVER = "prover_brief"
NAMES = (PROVER, SKEPTIC, SKEPTIC_HUNT)
CLAIM_HASH = re.compile(r"\b[0-9a-fA-F]{32,}\b")
ROLE_FIELDS = frozenset({"template", "tools", "model", "max_turns", "timeout_s"})
OPTIONAL_ROLE_FIELDS = frozenset({"thinking", "effort"})
THINKING_MODES = ("adaptive", "disabled")
EFFORT_LEVELS = ("low", "medium", "high", "xhigh", "max")


class RoleTemplateError(BundleError):
    pass


class RoleConfigError(ValueError):
    pass


@dataclass(frozen=True)
class RoleConfig:
    template: str
    tools: tuple[str, ...]
    model: str
    max_turns: int
    timeout_s: int
    thinking: str
    effort: str | None


def has_role_fields(config):
    return isinstance(config, dict) and ROLE_FIELDS <= set(config) <= ROLE_FIELDS | OPTIONAL_ROLE_FIELDS


def validate_config(config, tool_registry):
    if not has_role_fields(config):
        raise RoleConfigError(
            "worker role fields must be template, tools, model, max_turns, timeout_s and optionally thinking and effort"
        )
    thinking = config.get("thinking", "disabled")
    if not isinstance(thinking, str) or thinking not in THINKING_MODES:
        raise RoleConfigError("worker thinking must be adaptive or disabled")
    effort = config.get("effort")
    if "effort" in config and (not isinstance(effort, str) or effort not in EFFORT_LEVELS):
        raise RoleConfigError("worker effort must be low, medium, high, xhigh or max")
    if not isinstance(config["template"], str) or not config["template"].strip():
        raise RoleConfigError("worker role needs a role-template name")
    tools = config["tools"]
    if not isinstance(tools, list) or any(not isinstance(t, str) or t not in tool_registry for t in tools):
        raise RoleConfigError("worker tool is outside the dispatch tool registry")
    if len(set(tools)) != len(tools):
        raise RoleConfigError("duplicate worker tool")
    if not isinstance(config["model"], str) or not re.fullmatch(r"claude-[a-zA-Z0-9-]+", config["model"]):
        raise RoleConfigError("worker model must be a Claude model identifier")
    for name in ("max_turns", "timeout_s"):
        if type(config[name]) is not int or config[name] <= 0:
            raise RoleConfigError(f"worker {name} must be a positive integer")
    return RoleConfig(
        template=config["template"],
        tools=tuple(tools),
        model=config["model"],
        max_turns=config["max_turns"],
        timeout_s=config["timeout_s"],
        thinking=thinking,
        effort=effort,
    )


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
