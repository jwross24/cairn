from dataclasses import dataclass

from cairn import claims, cli, log, nogo, scrutiny
from cairn.profile import ProfileUndeclared

lg = log.get("tiergate")

PROFILE_UNDECLARED = "profile-undeclared"
TICKET_ABSENT = "ticket-absent"
TIER_TWO_ABOVE = "tier-two-above"
NOGO_UNDECLARED = "nogo-undeclared"
NOGO_UNREVIEWED = "nogo-unreviewed"
BOUNDARY_TABLE = "boundary-table"
UNCERTIFIED = "uncertified"
YANKED = "yanked"
BUDGET = "budget"
TICKET_BUNDLE_MISMATCH = "ticket-bundle-mismatch"

REASON_ORDER = (
    PROFILE_UNDECLARED,
    TICKET_ABSENT,
    TIER_TWO_ABOVE,
    NOGO_UNDECLARED,
    NOGO_UNREVIEWED,
    BOUNDARY_TABLE,
    UNCERTIFIED,
    YANKED,
    BUDGET,
    TICKET_BUNDLE_MISMATCH,
    *scrutiny.REASONS,
)
COST_DEPENDENT = (BOUNDARY_TABLE, BUDGET)
HYPOTHESIS_TICKET_KIND = "hypothesis_object"
HYPOTHESIS_TICKET_TIER = 0


@dataclass(frozen=True)
class Launch:
    cost_profile: object
    inputs: object
    budget_remaining: float
    hypothesis_key: str
    method_identity: dict
    skill_identity_hash: str | None
    declared_tier: int
    statement_hash: str | None = None
    target_attack: bool = False


@dataclass(frozen=True)
class Admitted:
    launch: object
    ticket_hash: str | None
    ticket_tier: int | None
    gate_run_hash: str
    reasons: tuple = ()


@dataclass(frozen=True)
class TierRefused:
    launch: object
    reasons: tuple
    ticket_tier: int | None
    gate_run_hash: str
    refusal_ids: tuple
    reminted_ticket_hash: str | None = None


def tier_for_cost(boundary_table, core_s):
    for row in boundary_table:
        ceiling = row["max_core_s"]
        if ceiling is None or core_s <= ceiling:
            return row["tier"]
    return boundary_table[-1]["tier"]


def ordered_reasons(reasons):
    return tuple(r for r in REASON_ORDER if r in reasons)


def predicate_reasons(
    *,
    declared_tier,
    ticket_tier,
    cost_tier,
    certified,
    yanked,
    budget_ok,
    ticket_bundle_matches,
    profile_declared,
    target_attack=False,
    nogo_declared=False,
    nogo_accepted=False,
    scrutiny_unmet=(),
):
    """The tier gate's whole truth table, over resolved facts. No substrate, no bundle, no I/O."""
    reasons: set[str] = set(scrutiny_unmet)
    if not profile_declared:
        reasons.add(PROFILE_UNDECLARED)
    if declared_tier > 0 and ticket_tier is None:
        reasons.add(TICKET_ABSENT)
    if ticket_tier is not None and declared_tier > ticket_tier + 1:
        reasons.add(TIER_TWO_ABOVE)
    if target_attack and declared_tier >= 1:
        if not nogo_declared:
            reasons.add(NOGO_UNDECLARED)
        elif declared_tier >= 2 and not nogo_accepted:
            reasons.add(NOGO_UNREVIEWED)
    if profile_declared:
        if declared_tier < cost_tier:
            reasons.add(BOUNDARY_TABLE)
        if not budget_ok:
            reasons.add(BUDGET)
    if not certified:
        reasons.add(UNCERTIFIED)
    if yanked:
        reasons.add(YANKED)
    if not ticket_bundle_matches:
        reasons.add(TICKET_BUNDLE_MISMATCH)
    return ordered_reasons(reasons)


class TierGate:
    def __init__(self, sub, gate_bundle, *, attest_path=None):
        self.sub = sub
        self.bundle = gate_bundle
        self.attest_path = attest_path

    @property
    def boundary_table(self):
        return self.bundle.tiers["boundary_table"]

    def _selected_ticket(self, launch):
        if launch.declared_tier == 0:
            return None
        node = claims.get_hypothesis_object(self.sub, launch.hypothesis_key)
        if node is None:
            return None
        return (HYPOTHESIS_TICKET_TIER, HYPOTHESIS_TICKET_KIND, node["hash"])

    def _recorded_ticket(self, launch):
        rows = self.sub.conn.execute(
            "SELECT * FROM tickets WHERE hypothesis_key = ? AND method_identity = ? ORDER BY rowid",
            (launch.hypothesis_key, claims.to_json(launch.method_identity)),
        ).fetchall()
        return dict(rows[-1]) if rows else None

    def admit(self, launch):
        try:
            evaluation = launch.cost_profile.evaluate(launch.inputs)
        except ProfileUndeclared:
            evaluation = None

        selected = self._selected_ticket(launch)
        ticket_tier = None if selected is None else selected[0]
        recorded = self._recorded_ticket(launch) if selected is not None else None
        stale = recorded is not None and recorded["bundle_hash"] != self.bundle.hash
        nogo_flag = nogo.flag(self.sub, launch.hypothesis_key, self.attest_path) if launch.target_attack else None
        read = scrutiny.gate_read(
            self.sub,
            self.bundle,
            hypothesis_key=launch.hypothesis_key,
            statement_hash=launch.statement_hash,
            declared_tier=launch.declared_tier,
            nogo_flagged=launch.target_attack,
            attest_path=self.attest_path,
        )

        reasons = predicate_reasons(
            declared_tier=launch.declared_tier,
            ticket_tier=ticket_tier,
            cost_tier=None if evaluation is None else tier_for_cost(self.boundary_table, evaluation.expected_core_s),
            certified=self.sub.certified(launch.skill_identity_hash),
            yanked=self.sub.yanked(launch.skill_identity_hash),
            budget_ok=evaluation is None
            or evaluation.expected_core_s + evaluation.expected_verification_core_s <= launch.budget_remaining,
            ticket_bundle_matches=not stale,
            profile_declared=evaluation is not None,
            target_attack=launch.target_attack,
            nogo_declared=nogo_flag is not None and nogo_flag.declared,
            nogo_accepted=nogo_flag is not None and nogo_flag.accepted,
            scrutiny_unmet=read.unmet,
        )

        run = claims.GateRun(
            gate="tier_gate",
            bundle_hash=self.bundle.hash,
            pin_hash=self.bundle.pin_hash,
            result="refused" if reasons else "admitted",
            reasons=reasons,
            at=cli.now_iso(),
            statement_hash=launch.statement_hash,
        )
        claims.write_gate_run(self.sub, run)
        lg.info(
            "admit",
            hypothesis_key=launch.hypothesis_key,
            declared_tier=launch.declared_tier,
            ticket_tier=ticket_tier,
            target_attack=launch.target_attack,
            nogo_declaration=None if nogo_flag is None else nogo_flag.declaration_hash,
            scrutiny_class=read.scrutiny_class,
            reasons=list(reasons),
            result=run.result,
            bundle_hash=self.bundle.hash,
        )

        if reasons:
            refusal_ids = tuple(
                claims.add_tier_refusal(self.sub, launch.hypothesis_key, launch.declared_tier, ticket_tier, reason)
                for reason in reasons
            )
            reminted = self._mint(launch, selected) if stale else None
            return TierRefused(launch, reasons, ticket_tier, run.hash, refusal_ids, reminted)

        minted = (
            self._mint(launch, selected)
            if selected is not None and recorded is None
            else (recorded["ticket_hash"] if recorded else None)
        )
        return Admitted(launch, minted, ticket_tier, run.hash)

    def _mint(self, launch, selected):
        tier, kind, node_hash = selected
        ticket = claims.Ticket(
            hypothesis_key=launch.hypothesis_key,
            method_identity=launch.method_identity,
            statement_hash=launch.statement_hash,
            tier=tier,
            kind=kind,
            node_hash=node_hash,
            bundle_hash=self.bundle.hash,
        )
        claims.write_ticket(self.sub, ticket)
        lg.info(
            "mint", ticket=ticket.hash, hypothesis_key=launch.hypothesis_key, tier=tier, bundle_hash=self.bundle.hash
        )
        return ticket.hash
