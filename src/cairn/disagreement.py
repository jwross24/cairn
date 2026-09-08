"""Disagreement records and the freeze they place on a statement's tag.

Raising a disagreement records the statement's tag at the moment of the dispute and enqueues a
human_queue DISAGREEMENT blocker item naming the statement. While that item stands open (no
lawful closure through human_queue's own paths), `freeze_for` returns the recorded tag as a
CEILING: a caller such as justify.derive_tag may still lower a statement's tag below the freeze
on a refutation, but may never raise it above the freeze while the item is open. A refutation is
evidence, so it must still be able to move a claim, and a freeze that also blocked downgrades
would let raising a disagreement shield a claim from its own counterevidence. There is no pin,
and there is no `resolve()`: the only way a freeze lifts is a lawful closure of its queue item
through `human_queue.close_by_attestation`, `close_by_blocker_clear`, `close_by_terminal_status`
or an acknowledgment.
"""

from dataclasses import dataclass, field

from cairn import canon, claims, human_queue, keys, log
from cairn.canon import NON_EMPTY_STR, Field, Struct
from cairn.substrate import SubstrateError, _now

lg = log.get("disagreement")

KIND = "disagreement_record"

STATEMENT_ERROR = "statement_error"
PROOF_GAP = "proof_gap"
HARNESS_BUG = "harness_bug"
OUT_OF_SCOPE = "out_of_scope"
INCONCLUSIVE = "inconclusive"
CLASSIFICATIONS = (STATEMENT_ERROR, PROOF_GAP, HARNESS_BUG, OUT_OF_SCOPE, INCONCLUSIVE)

OWNER_HUMAN = "human"
OWNER_PROVER = "prover"
OWNER_HARNESS = "harness"
OWNER_ORCHESTRATOR = "orchestrator"
OWNERS = (OWNER_HUMAN, OWNER_PROVER, OWNER_HARNESS, OWNER_ORCHESTRATOR)

ROUTING = {
    STATEMENT_ERROR: OWNER_HUMAN,
    PROOF_GAP: OWNER_PROVER,
    HARNESS_BUG: OWNER_HARNESS,
    OUT_OF_SCOPE: OWNER_ORCHESTRATOR,
    INCONCLUSIVE: OWNER_HUMAN,
}

DISAGREEMENT_RECORD = Struct(
    KIND,
    [
        Field("statement_hash", NON_EMPTY_STR),
        Field("left_hash", NON_EMPTY_STR),
        Field("right_hash", NON_EMPTY_STR),
        Field("classification", NON_EMPTY_STR),
        Field("owner", NON_EMPTY_STR),
        Field("frozen_tag", NON_EMPTY_STR),
        Field("item_id", NON_EMPTY_STR),
        Field("raised_at", NON_EMPTY_STR),
    ],
)


class DisagreementError(SubstrateError):
    pass


@dataclass(frozen=True)
class DisagreementRecord:
    statement_hash: str
    left_hash: str
    right_hash: str
    classification: str
    owner: str
    frozen_tag: str
    item_id: str
    raised_at: str
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.classification not in CLASSIFICATIONS:
            raise DisagreementError(f"classification must be one of {CLASSIFICATIONS}, got {self.classification!r}")
        if self.owner != ROUTING[self.classification]:
            raise DisagreementError(
                f"owner for {self.classification} must be {ROUTING[self.classification]!r}, got {self.owner!r}"
            )
        if self.frozen_tag not in claims.TAGS:
            raise DisagreementError(f"frozen_tag must be one of {claims.TAGS}, got {self.frozen_tag!r}")
        check_artifacts(self.left_hash, self.right_hash)
        object.__setattr__(self, "hash", keys.node_hash(KIND, canonical(self)))


def check_artifacts(left_hash, right_hash):
    for name, value in (("left_hash", left_hash), ("right_hash", right_hash)):
        if not isinstance(value, str) or not value.strip():
            raise DisagreementError(f"a disagreement {name} must be nonempty text, got {value!r}")
    if left_hash == right_hash:
        raise DisagreementError("a disagreement names two distinct artifacts")


def canonical(record):
    try:
        return canon.encode(
            DISAGREEMENT_RECORD,
            {
                "statement_hash": record.statement_hash,
                "left_hash": record.left_hash,
                "right_hash": record.right_hash,
                "classification": record.classification,
                "owner": record.owner,
                "frozen_tag": record.frozen_tag,
                "item_id": record.item_id,
                "raised_at": record.raised_at,
            },
        )
    except canon.CanonError as exc:
        raise DisagreementError(f"disagreement record: {exc}") from None


def _rank(tag):
    return claims.TAGS.index(tag)


def record(sub, *, statement_hash, left_hash, right_hash, classification, at=None):
    if classification not in CLASSIFICATIONS:
        raise DisagreementError(f"classification must be one of {CLASSIFICATIONS}, got {classification!r}")
    check_artifacts(left_hash, right_hash)
    statement = claims.get_claim_statement(sub, statement_hash)
    if statement is None:
        raise DisagreementError(f"no claim statement {statement_hash}")
    history = claims.tag_history_for(sub, statement_hash)
    frozen_tag = history[-1]["to_tag"] if history else "SPECULATION"
    owner = ROUTING[classification]
    raised_at = at or _now()
    item_id = human_queue.enqueue(
        sub,
        human_queue.Item(
            human_queue.DISAGREEMENT, human_queue.STATEMENT, statement_hash, raised_at, blocker=human_queue.DISAGREEMENT
        ),
    )
    rec = DisagreementRecord(
        statement_hash=statement_hash,
        left_hash=left_hash,
        right_hash=right_hash,
        classification=classification,
        owner=owner,
        frozen_tag=frozen_tag,
        item_id=item_id,
        raised_at=raised_at,
    )
    rec_canonical = canonical(rec)
    with sub._tx():
        sub._put_node(KIND, rec_canonical, rec.hash, "Replayable", None)
        row = sub.conn.execute(
            "SELECT disagreement_id FROM disagreements WHERE disagreement_id = ?", (rec.hash,)
        ).fetchone()
        if row is None:
            sub.conn.execute(
                "INSERT INTO disagreements "
                "(disagreement_id, statement_hash, left_hash, right_hash, classification, owner, frozen_tag, "
                "item_id, raised_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rec.hash,
                    rec.statement_hash,
                    rec.left_hash,
                    rec.right_hash,
                    rec.classification,
                    rec.owner,
                    rec.frozen_tag,
                    rec.item_id,
                    rec.raised_at,
                ),
            )
    lg.info(
        "record",
        statement=statement_hash,
        classification=classification,
        owner=owner,
        frozen_tag=frozen_tag,
        item_id=item_id,
    )
    return rec


def records_for(sub, statement_hash):
    rows = sub.conn.execute(
        "SELECT * FROM disagreements WHERE statement_hash = ? ORDER BY raised_at, disagreement_id",
        (statement_hash,),
    ).fetchall()
    return [dict(r) for r in rows]


def standing(sub, statement_hash, attest_path):
    return [
        row
        for row in records_for(sub, statement_hash)
        if human_queue.visible_closure(sub, row["item_id"], attest_path) is None
    ]


def freeze_for(sub, statement_hash, attest_path):
    weakest = None
    for row in standing(sub, statement_hash, attest_path):
        candidate = (row["frozen_tag"], row["left_hash"], row["disagreement_id"])
        if (
            weakest is None
            or _rank(candidate[0]) < _rank(weakest[0])
            or (_rank(candidate[0]) == _rank(weakest[0]) and candidate[2] < weakest[2])
        ):
            weakest = candidate
    return weakest


def released(sub, disagreement_hash, attest_path):
    row = sub.conn.execute("SELECT * FROM disagreements WHERE disagreement_id = ?", (disagreement_hash,)).fetchone()
    if row is None:
        return None
    return human_queue.visible_closure(sub, row["item_id"], attest_path)
