"""The proportional-scrutiny router (PLAN §7) and the expert sign-off record (§10).

A scrutiny class is a pure function of the typed fields of the hypothesis object and claim statement
(target family, cost model, scope, formal source) and the §8 flag; no prose reaches the predicate. The
top class is a claim that names the bundle's target family and claims a cost below the generic bound,
or a flagged target attack. The orchestrator may request a class and never lower one: the router's
assignment is a floor, and a request below it is refused before it is recorded. A top-class Tier-3
launch holds no ticket until every obligation the bundle names is discharged; the gate reads each one
from the substrate and carries one reason per obligation still open. The expert sign-off is a human-path
record: appended to the attestation file, mirrored as a row carrying the record's digest and offset,
visible only while the digest re-derived from the row's fields is the record at that offset, and bound
to the one statement hash it signs.
"""

import json
from dataclasses import dataclass, field
from fractions import Fraction

from cairn import attest, canon, claims, keys, log
from cairn.canon import NON_EMPTY_STR, Field, Struct
from cairn.substrate import SubstrateError, _now, blob_hash

lg = log.get("scrutiny")

ROUTINE = "routine"
ELEVATED = "elevated"
TOP = "top"
CLASSES = (ROUTINE, ELEVATED, TOP)
BUNDLE_KIND = "scrutiny"
TIER_THREE = 3

LADDER_KEEP = "ladder_keep"
FORMALIZATION_GATE = "formalization_gate"
STATEMENT_REVIEW = "statement_review"
REPRODUCIBILITY = "reproducibility"
EXPERT_SIGNOFF = "expert_signoff"
OBLIGATIONS = (LADDER_KEEP, FORMALIZATION_GATE, STATEMENT_REVIEW, REPRODUCIBILITY, EXPERT_SIGNOFF)

SCRUTINY_LADDER_KEEP_ABSENT = "scrutiny-ladder-keep-absent"
SCRUTINY_FORMALIZATION_ABSENT = "scrutiny-formalization-absent"
SCRUTINY_STATEMENT_REVIEW_ABSENT = "scrutiny-statement-review-absent"
SCRUTINY_REPRO_ABSENT = "scrutiny-repro-absent"
EXPERT_SIGNOFF_ABSENT = "expert-signoff-absent"
REASON_FOR = {
    LADDER_KEEP: SCRUTINY_LADDER_KEEP_ABSENT,
    FORMALIZATION_GATE: SCRUTINY_FORMALIZATION_ABSENT,
    STATEMENT_REVIEW: SCRUTINY_STATEMENT_REVIEW_ABSENT,
    REPRODUCIBILITY: SCRUTINY_REPRO_ABSENT,
    EXPERT_SIGNOFF: EXPERT_SIGNOFF_ABSENT,
}
REASONS = tuple(REASON_FOR[o] for o in OBLIGATIONS)

SIGNOFF_KIND = "expert_signoff"
SIGNOFFS = "expert_signoffs"
REQUESTS = "scrutiny_requests"
SIGNOFF_RECORD_FIELDS = ("statement_hash", "expert", "at")
SIGNOFF = Struct(
    SIGNOFF_KIND,
    [
        Field("statement_hash", NON_EMPTY_STR),
        Field("expert", NON_EMPTY_STR),
        Field("gate_bundle_hash", NON_EMPTY_STR),
        Field("at", NON_EMPTY_STR),
    ],
)
COST_MODEL_KIND = "cost_model"
FORMALIZATION_GATE_NAME = "challenge_render"
LADDER_TABLE = "ladder_table"
KEEP = "KEEP"
APPROVE = "approve"


class ScrutinyError(SubstrateError):
    pass


class LoweringRefused(ScrutinyError):
    pass


class PolicyError(ScrutinyError):
    pass


@dataclass(frozen=True)
class Policy:
    target_family: str
    generic_bound_exponent: Fraction
    obligations: tuple

    @classmethod
    def from_object(cls, obj):
        if not isinstance(obj, dict):
            raise PolicyError(f"the {BUNDLE_KIND} object must be a mapping")
        for name in ("target_family", "generic_bound_exponent", "classes", "top_obligations"):
            if name not in obj:
                raise PolicyError(f"the {BUNDLE_KIND} object carries no {name}")
        if tuple(obj["classes"]) != CLASSES:
            raise PolicyError(f"the {BUNDLE_KIND} object's classes must be {CLASSES}, got {obj['classes']!r}")
        obligations = tuple(obj["top_obligations"])
        unknown = sorted(set(obligations) - set(OBLIGATIONS))
        if unknown:
            raise PolicyError(f"the {BUNDLE_KIND} object names no obligation {', '.join(unknown)}")
        if not isinstance(obj["target_family"], str) or not obj["target_family"]:
            raise PolicyError("target_family must be a non-empty str")
        return cls(obj["target_family"], _exponent(obj["generic_bound_exponent"]), obligations)


def policy(gate_bundle):
    return Policy.from_object(gate_bundle.object(BUNDLE_KIND))


def _exponent(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise PolicyError(f"an exponent is a str or int, got {type(value).__name__}")
    try:
        return Fraction(value)
    except ValueError, ZeroDivisionError:
        raise PolicyError(f"exponent {value!r} is not a rational") from None


@dataclass(frozen=True)
class Typed:
    target_family: str | None
    scope_target_family: str | None
    cost_model: dict | None
    theorem: bool

    @property
    def algorithmic(self):
        return self.cost_model is not None


def rank(cls):
    if cls not in CLASSES:
        raise ScrutinyError(f"class must be one of {CLASSES}, got {cls!r}")
    return CLASSES.index(cls)


def classify(policy, *, target_family, scope_target_family, cost_model, nogo_flagged):
    names_target = policy.target_family in (target_family, scope_target_family)
    if not names_target:
        return ROUTINE
    if nogo_flagged:
        return TOP
    if cost_model is not None and _exponent(cost_model["exponent"]) < policy.generic_bound_exponent:
        return TOP
    return ELEVATED


def _hypothesis_fields(sub, hypothesis_key):
    row = claims.get_hypothesis_object(sub, hypothesis_key)
    if row is None:
        return None
    return canon.decode(keys.HYPOTHESIS_OBJECT, row["canonical"])


def _claimed_cost_model(claimed):
    if claimed.get("kind") != COST_MODEL_KIND or "exponent" not in claimed:
        return None
    return {"exponent": claimed["exponent"], "constant": claimed.get("constant"), "crossover": claimed.get("crossover")}


def stronger(claimed, stated):
    if claimed is None or stated is None:
        return claimed if stated is None else stated
    return stated if _exponent(stated["exponent"]) < _exponent(claimed["exponent"]) else claimed


def typed_fields(sub, hypothesis_key, statement_hash):
    hypothesis = _hypothesis_fields(sub, hypothesis_key) if hypothesis_key else None
    statement = claims.get_claim_statement(sub, statement_hash) if statement_hash else None
    target_family = None if hypothesis is None else hypothesis["target_family"]
    cost_model = None if hypothesis is None else _claimed_cost_model(hypothesis["claimed"])
    scope_target_family, theorem = None, False
    if statement is not None:
        scope_target_family = json.loads(statement["scope"]).get("target_family")
        quantities = json.loads(statement["quantities"])
        cost_model = stronger(cost_model, quantities.get("cost_model"))
        theorem = statement["formal_source"] is not None
    return Typed(target_family, scope_target_family, cost_model, theorem)


def assigned(policy, typed, *, nogo_flagged):
    return classify(
        policy,
        target_family=typed.target_family,
        scope_target_family=typed.scope_target_family,
        cost_model=typed.cost_model,
        nogo_flagged=nogo_flagged,
    )


def floor(sub, hypothesis_key):
    row = sub.conn.execute(
        f"SELECT requested_class FROM {REQUESTS} WHERE hypothesis_key = ? ORDER BY seq DESC LIMIT 1", (hypothesis_key,)
    ).fetchone()
    return None if row is None else row["requested_class"]


def effective(sub, hypothesis_key, assigned_class):
    requested = floor(sub, hypothesis_key)
    if requested is None or rank(requested) <= rank(assigned_class):
        return assigned_class
    return requested


def request(sub, hypothesis_key, requested, *, assigned_class, requested_by, at=None):
    current = effective(sub, hypothesis_key, assigned_class)
    if rank(requested) < rank(current):
        raise LoweringRefused(
            f"branch {hypothesis_key} holds scrutiny class {current}; a request for {requested} lowers it and is refused"
        )
    at = at or _now()
    with sub._tx():
        cur = sub.conn.execute(
            f"INSERT INTO {REQUESTS} (hypothesis_key, requested_class, assigned_class, requested_by, at) VALUES (?, ?, ?, ?, ?)",
            (hypothesis_key, requested, assigned_class, requested_by, at),
        )
        seq = cur.lastrowid
    lg.info(
        "request",
        hypothesis_key=hypothesis_key,
        requested=requested,
        assigned=assigned_class,
        effective=requested,
        requested_by=requested_by,
        seq=seq,
    )
    return seq


def _ladder_keep(sub, statement_hash):
    for row in claims.evidence_for(sub, statement_hash):
        if row["kind"] != LADDER_TABLE or row["verdict"] != KEEP:
            continue
        attempt = sub.get_attempt(row["attempt_id"]) if row["attempt_id"] else None
        if attempt is None or attempt["disowned_at"] is None:
            return True
    return False


def _formalization_passed(sub, statement_hash):
    row = sub.conn.execute(
        "SELECT 1 FROM gate_runs WHERE gate = ? AND statement_hash = ? AND result = 'pass' LIMIT 1",
        (FORMALIZATION_GATE_NAME, statement_hash),
    ).fetchone()
    return row is not None


def _reviewed(sub, statement_hash, attest_path):
    if attest_path is None:
        return False
    return any(row["verdict"] == APPROVE for row in claims.visible_review_verdicts(sub, statement_hash, attest_path))


def _reproduced(sub, statement_hash):
    for row in claims.evidence_for(sub, statement_hash):
        if row["repro_record_hash"]:
            record = claims.get_repro_record(sub, row["repro_record_hash"])
            if record is not None and record["passed"]:
                return True
        if row["attempt_id"] and any(r["passed"] for r in claims.repro_records_for_attempt(sub, row["attempt_id"])):
            return True
    return False


def unmet(sub, policy, typed, statement_hash, attest_path):
    checks = {
        LADDER_KEEP: lambda: (
            not typed.algorithmic or (statement_hash is not None and _ladder_keep(sub, statement_hash))
        ),
        FORMALIZATION_GATE: lambda: not typed.theorem or _formalization_passed(sub, statement_hash),
        STATEMENT_REVIEW: lambda: not typed.theorem or _reviewed(sub, statement_hash, attest_path),
        REPRODUCIBILITY: lambda: statement_hash is not None and _reproduced(sub, statement_hash),
        EXPERT_SIGNOFF: lambda: statement_hash is not None and signed_off(sub, statement_hash, attest_path),
    }
    return tuple(REASON_FOR[o] for o in policy.obligations if not checks[o]())


@dataclass(frozen=True)
class Read:
    scrutiny_class: str
    assigned_class: str
    unmet: tuple


def gate_read(sub, gate_bundle, *, hypothesis_key, statement_hash, declared_tier, nogo_flagged, attest_path):
    pol = policy(gate_bundle)
    typed = typed_fields(sub, hypothesis_key, statement_hash)
    base = assigned(pol, typed, nogo_flagged=nogo_flagged)
    cls = effective(sub, hypothesis_key, base) if hypothesis_key else base
    open_obligations = ()
    if cls == TOP and declared_tier >= TIER_THREE:
        open_obligations = unmet(sub, pol, typed, statement_hash, attest_path)
    return Read(cls, base, open_obligations)


@dataclass(frozen=True)
class SignOff:
    statement_hash: str
    expert: str
    gate_bundle_hash: str
    at: str
    file_offset: int = 0
    record_digest: str = field(init=False, compare=False)
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        canonical = signoff_canonical(self)
        object.__setattr__(self, "record_digest", blob_hash(canonical))
        object.__setattr__(self, "hash", keys.node_hash(SIGNOFF_KIND, canonical))


def signoff_canonical(signoff):
    try:
        return canon.encode(
            SIGNOFF,
            {
                "statement_hash": signoff.statement_hash,
                "expert": signoff.expert,
                "gate_bundle_hash": signoff.gate_bundle_hash,
                "at": signoff.at,
            },
        )
    except canon.CanonError as exc:
        raise ScrutinyError(f"{SIGNOFF_KIND}: {exc}") from None


def signoff_from_fields(fields, gate_bundle_hash, file_offset):
    unknown = sorted(set(fields) - set(SIGNOFF_RECORD_FIELDS))
    if unknown:
        raise ScrutinyError(f"an {SIGNOFF_KIND} record carries no field {', '.join(unknown)}")
    missing = sorted(f for f in SIGNOFF_RECORD_FIELDS if f not in fields)
    if missing:
        raise ScrutinyError(f"an {SIGNOFF_KIND} record is missing {', '.join(missing)}")
    return SignOff(
        statement_hash=str(fields["statement_hash"]),
        expert=str(fields["expert"]),
        gate_bundle_hash=str(gate_bundle_hash),
        at=str(fields["at"]),
        file_offset=file_offset,
    )


def _signoff_of(row):
    return SignOff(
        statement_hash=row["statement_hash"],
        expert=row["expert"],
        gate_bundle_hash=row["gate_bundle_hash"],
        at=row["at"],
        file_offset=row["file_offset"],
    )


def write_signoff(sub, signoff):
    canonical = signoff_canonical(signoff)
    with sub._tx():
        sub._put_node(SIGNOFF_KIND, canonical, signoff.hash, "Replayable", signoff.expert)
        existing = sub.conn.execute(
            f"SELECT row_id FROM {SIGNOFFS} WHERE record_digest = ? AND file_offset = ?",
            (signoff.record_digest, signoff.file_offset),
        ).fetchone()
        if existing is not None:
            lg.info("write", table=SIGNOFFS, hash=signoff.hash, status="exists", row_id=existing["row_id"])
            return existing["row_id"]
        cur = sub.conn.execute(
            f"INSERT INTO {SIGNOFFS} (statement_hash, expert, gate_bundle_hash, at, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?)",
            (
                signoff.statement_hash,
                signoff.expert,
                signoff.gate_bundle_hash,
                signoff.at,
                signoff.record_digest,
                signoff.file_offset,
            ),
        )
        row_id = cur.lastrowid
    lg.info("write", table=SIGNOFFS, hash=signoff.hash, status="inserted", row_id=row_id)
    return row_id


def signoffs_for(sub, statement_hash):
    rows = sub.conn.execute(
        f"SELECT * FROM {SIGNOFFS} WHERE statement_hash = ? ORDER BY row_id", (statement_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def row_visible(row, attest_path):
    """A row counts only when the digest re-derived from its fields is the record at its offset."""
    derived = _signoff_of(row).record_digest
    if derived != row["record_digest"]:
        return False
    return attest.attestation_record_matches(attest_path, row["file_offset"], derived)


def visible_signoffs(sub, statement_hash, attest_path):
    if attest_path is None:
        return []
    return [row for row in signoffs_for(sub, statement_hash) if row_visible(row, attest_path)]


def signed_off(sub, statement_hash, attest_path):
    return bool(visible_signoffs(sub, statement_hash, attest_path))
