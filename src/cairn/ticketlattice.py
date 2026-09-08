"""The gate's ticket selection over tiers and claim kinds (PLAN §5).

The launching party supplies no ticket and names no claim kind. Both are read off substrate state:
the kinds a claim carries come from its recorded typed fields, and the ticket for each kind is the
most recent node of that kind for the same hypothesis key and method identity, whatever its verdict,
with the verdict rule applied to the node so selected. A later REJECT or INCONCLUSIVE table
therefore displaces an older KEEP rather than being skipped over for it.

A claim carrying several kinds needs the ticket of each and is refused while any is absent. A
KEEP_IN_SAMPLE table is a ticket for the ladder plan's hold-out rung of its own hypothesis key and
for no other launch; a ticket is compared against the launch's hypothesis key, method identity and,
for a ladder table, the implementation revision it ran with, so a new revision re-ladders before it
spends.
"""

import json
from dataclasses import dataclass

from cairn import canon, claims, hunt, keys, ladderplan, laddertable, log, profile, scrutiny

lg = log.get("ticketlattice")

ALGORITHMIC = "algorithmic"
CONJECTURE = "conjecture"
THEOREM = "theorem"
KINDS = (ALGORITHMIC, CONJECTURE, THEOREM)

CONJECTURE_MARKER = "correctness_conjecture"
MARKER_TRUE = "true"

KEY_MISMATCH = "key"
METHOD_MISMATCH = "method_identity"
REVISION_MISMATCH = "implementation_revision"
SCOPE_MISMATCH = "scope"


class ClaimKindMalformed(ValueError):
    pass


@dataclass(frozen=True)
class Candidate:
    claim_kind: str
    node_kind: str
    node_hash: str
    verdict: str
    hypothesis_key: str
    method_identity: dict
    implementation_revision: str | None = None
    scoped_rung_bits: int | None = None


@dataclass(frozen=True)
class Selection:
    claim_kind: str
    candidate: object
    admits: bool
    mismatches: tuple = ()


def _hypothesis_claimed(sub, hypothesis_key):
    row = claims.get_hypothesis_object(sub, hypothesis_key) if hypothesis_key else None
    if row is None:
        return {}
    return canon.decode(keys.HYPOTHESIS_OBJECT, row["canonical"])["claimed"]


def claim_kinds(sub, hypothesis_key, statement_hash=None):
    """Every claim kind the recorded hypothesis and statement carry; never a launch argument."""
    typed = scrutiny.typed_fields(sub, hypothesis_key, statement_hash)
    carried = set()
    if typed.cost_model is not None:
        carried.add(ALGORITHMIC)
    if typed.theorem:
        carried.add(THEOREM)
    marker = _hypothesis_claimed(sub, hypothesis_key).get(CONJECTURE_MARKER)
    if marker is not None:
        if marker != MARKER_TRUE:
            raise ClaimKindMalformed(
                f"{CONJECTURE_MARKER} is {marker!r}; the marker is present as {MARKER_TRUE!r} or absent"
            )
        carried.add(CONJECTURE)
    return tuple(kind for kind in KINDS if kind in carried)


def _hold_out_bits(gate_bundle):
    return ladderplan.LadderPlan.from_bundle(gate_bundle).hold_out_rung.bits


def rung_role(gate_bundle, inputs):
    """The pinned plan's role for the size a launch declares, or None where the plan has no such rung.

    The plan comes from the gate bundle and the size from the launch's recorded inputs, so neither
    operand is a caller's assertion about which rung this is.
    """
    bits = profile.declared_bits(inputs)
    if bits is None:
        return None
    try:
        return ladderplan.LadderPlan.from_bundle(gate_bundle).rung(bits).role
    except KeyError:
        return None


def ladder_candidate(sub, gate_bundle, hypothesis_key, method_identity):
    """The most recent ladder table for the key and method, whatever verdict it carries."""
    rows = sub.conn.execute(
        f"SELECT * FROM {laddertable.TABLES} WHERE hypothesis_hash = ? AND method_identity = ? ORDER BY rowid",
        (hypothesis_key, claims.to_json(method_identity)),
    ).fetchall()
    if not rows:
        return None
    row = dict(rows[-1])
    scoped = _hold_out_bits(gate_bundle) if row["verdict"] == laddertable.KEEP_IN_SAMPLE else None
    return Candidate(
        claim_kind=ALGORITHMIC,
        node_kind=laddertable.NODE_KIND,
        node_hash=row["hash"],
        verdict=row["verdict"],
        hypothesis_key=row["hypothesis_hash"],
        method_identity=json.loads(row["method_identity"]),
        implementation_revision=row["implementation_revision"],
        scoped_rung_bits=scoped,
    )


def _hunt_record(sub, evidence_hash):
    for edge in sub.lineage_of(evidence_hash):
        record = hunt.record_for(sub, edge["parent_hash"])
        if record is not None:
            return record
    return None


def hunt_candidate(sub, hypothesis_key, method_identity):
    """The most recent counterexample-hunt record for the key and method, whatever verdict it carries."""
    rows = sub.conn.execute("SELECT hash FROM evidence_nodes WHERE kind = ? ORDER BY rowid", (hunt.KIND,)).fetchall()
    found = None
    for row in rows:
        record = _hunt_record(sub, row["hash"])
        if record is None or record.hypothesis_key != hypothesis_key:
            continue
        found = Candidate(
            claim_kind=CONJECTURE,
            node_kind=hunt.KIND,
            node_hash=row["hash"],
            verdict=record.verdict,
            hypothesis_key=record.hypothesis_key,
            method_identity=dict(method_identity),
        )
    return found


def mismatches(candidate, *, hypothesis_key, method_identity, implementation_revision, rung_bits):
    """Every way the selected ticket fails to bind to this launch, by name."""
    found = []
    if candidate.hypothesis_key != hypothesis_key:
        found.append(KEY_MISMATCH)
    if candidate.method_identity != method_identity:
        found.append(METHOD_MISMATCH)
    if (
        candidate.implementation_revision is not None
        and implementation_revision is not None
        and candidate.implementation_revision != implementation_revision
    ):
        found.append(REVISION_MISMATCH)
    if candidate.scoped_rung_bits is not None and candidate.scoped_rung_bits != rung_bits:
        found.append(SCOPE_MISMATCH)
    return tuple(found)


ADMITTING_VERDICTS = {
    ALGORITHMIC: (laddertable.KEEP, laddertable.KEEP_IN_SAMPLE),
    CONJECTURE: ("SURVIVED",),
}


def select_kind(sub, gate_bundle, claim_kind, *, hypothesis_key, method_identity, inputs, implementation_revision):
    candidate = (
        ladder_candidate(sub, gate_bundle, hypothesis_key, method_identity)
        if claim_kind == ALGORITHMIC
        else hunt_candidate(sub, hypothesis_key, method_identity)
    )
    if candidate is None:
        return Selection(claim_kind, None, False)
    unbound = mismatches(
        candidate,
        hypothesis_key=hypothesis_key,
        method_identity=method_identity,
        implementation_revision=implementation_revision,
        rung_bits=profile.declared_bits(inputs),
    )
    admits = not unbound and candidate.verdict in ADMITTING_VERDICTS[claim_kind]
    return Selection(claim_kind, candidate, admits, unbound)


def tier_two_selections(sub, gate_bundle, *, hypothesis_key, statement_hash, method_identity, inputs, revision):
    """One selection per claim kind the hypothesis carries; a theorem kind is the human review's, not this reader's."""
    selections = []
    for claim_kind in claim_kinds(sub, hypothesis_key, statement_hash):
        if claim_kind == THEOREM:
            continue
        selections.append(
            select_kind(
                sub,
                gate_bundle,
                claim_kind,
                hypothesis_key=hypothesis_key,
                method_identity=method_identity,
                inputs=inputs,
                implementation_revision=revision,
            )
        )
    return tuple(selections)


def admits_tier_two(selections):
    return bool(selections) and all(selection.admits for selection in selections)
