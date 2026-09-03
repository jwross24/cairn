"""The no-go presence check (PLAN §8) and the nogo_review node.

A target-attack branch declares how it evades the three no-gos: Shoup's sqrt(n) bound, isogeny
invariance, and the prime-field index-calculus obstruction. The declaration is a content-addressed
node outside the hypothesis key, written under the branch; its absence is the flag. A nogo_review
records a human verdict on one declaration and reaches the substrate only through the attestation
file, so a review row is visible exactly when the digest re-derived from its own fields matches
the record at its offset. accept_for_tiering restores ordinary ticket eligibility and nothing else:
it is no claim tag and satisfies none of the top scrutiny class's obligations. Presence is the
only mechanical dimension here; whether an evasion argument is sound is the Skeptic's and the
human's.
"""

from dataclasses import dataclass, field

from cairn import attest, canon, human_queue, keys, log
from cairn.canon import NON_EMPTY_STR, STR, Field, List, Optional, Struct
from cairn.substrate import SubstrateError, _now, blob_hash

lg = log.get("nogo")

SHOUP_SQRT_N = "shoup_sqrt_n"
ISOGENY_INVARIANCE = "isogeny_invariance"
PRIME_FIELD_INDEX_CALCULUS = "prime_field_index_calculus"
NO_GOS = (SHOUP_SQRT_N, ISOGENY_INVARIANCE, PRIME_FIELD_INDEX_CALCULUS)

ACCEPT_FOR_TIERING = "accept_for_tiering"
REJECT = "reject"
NEEDS_REVISION = "needs_revision"
VERDICTS = (ACCEPT_FOR_TIERING, REJECT, NEEDS_REVISION)

DECLARATION_KIND = "nogo_declaration"
REVIEW_KIND = "nogo_review"
DECLARATIONS = "nogo_declarations"
REVIEWS = "nogo_reviews"
REVIEW_RECORD_FIELDS = ("hypothesis_key", "declaration_hash", "reviewer", "verdict", "at", "supersedes")

EVASION = Struct("nogo_evasion", [Field("no_go", NON_EMPTY_STR), Field("evasion", NON_EMPTY_STR)])
DECLARATION = Struct(
    DECLARATION_KIND,
    [
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("evasions", List(EVASION)),
        Field("declared_by", NON_EMPTY_STR),
        Field("at", NON_EMPTY_STR),
    ],
)
REVIEW = Struct(
    REVIEW_KIND,
    [
        Field("hypothesis_key", NON_EMPTY_STR),
        Field("declaration_hash", NON_EMPTY_STR),
        Field("reviewer", NON_EMPTY_STR),
        Field("verdict", NON_EMPTY_STR),
        Field("gate_bundle_hash", NON_EMPTY_STR),
        Field("at", NON_EMPTY_STR),
        Field("supersedes", Optional(STR)),
    ],
)


class NogoError(SubstrateError):
    pass


def missing_no_gos(evasions):
    """The no-gos a declaration fails to evade in words: absent, blank, unknown, or named twice."""
    seen = {}
    problems = []
    for entry in evasions:
        name = entry.get("no_go") if isinstance(entry, dict) else None
        if name not in NO_GOS:
            problems.append(f"unknown no-go {name!r}")
            continue
        if name in seen:
            problems.append(f"{name} named twice")
            continue
        text = entry.get("evasion")
        seen[name] = isinstance(text, str) and bool(text.strip())
        if not seen[name]:
            problems.append(f"{name} has an empty evasion")
    problems.extend(f"{name} not addressed" for name in NO_GOS if name not in seen)
    return tuple(problems)


@dataclass(frozen=True)
class Declaration:
    hypothesis_key: str
    evasions: tuple
    declared_by: str
    at: str
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        object.__setattr__(self, "evasions", tuple(dict(e) for e in self.evasions))
        problems = missing_no_gos(self.evasions)
        if problems:
            raise NogoError(f"declaration for {self.hypothesis_key}: {'; '.join(problems)}")
        object.__setattr__(self, "hash", keys.node_hash(DECLARATION_KIND, declaration_canonical(self)))


def declaration_canonical(declaration):
    try:
        return canon.encode(
            DECLARATION,
            {
                "hypothesis_key": declaration.hypothesis_key,
                "evasions": [
                    {"no_go": name, "evasion": next(e["evasion"] for e in declaration.evasions if e["no_go"] == name)}
                    for name in NO_GOS
                ],
                "declared_by": declaration.declared_by,
                "at": declaration.at,
            },
        )
    except canon.CanonError as exc:
        raise NogoError(f"declaration: {exc}") from None


@dataclass(frozen=True)
class Review:
    hypothesis_key: str
    declaration_hash: str
    reviewer: str
    verdict: str
    gate_bundle_hash: str
    at: str
    supersedes: str | None = None
    file_offset: int = 0
    record_digest: str = field(init=False, compare=False)
    hash: str = field(init=False, compare=False)

    def __post_init__(self):
        if self.verdict not in VERDICTS:
            raise NogoError(f"verdict must be one of {VERDICTS}, got {self.verdict!r}")
        canonical = review_canonical(self)
        object.__setattr__(self, "record_digest", blob_hash(canonical))
        object.__setattr__(self, "hash", keys.node_hash(REVIEW_KIND, canonical))


def review_canonical(review):
    try:
        return canon.encode(
            REVIEW,
            {
                "hypothesis_key": review.hypothesis_key,
                "declaration_hash": review.declaration_hash,
                "reviewer": review.reviewer,
                "verdict": review.verdict,
                "gate_bundle_hash": review.gate_bundle_hash,
                "at": review.at,
                "supersedes": review.supersedes,
            },
        )
    except canon.CanonError as exc:
        raise NogoError(f"nogo_review: {exc}") from None


def review_from_fields(fields, gate_bundle_hash, file_offset):
    unknown = sorted(set(fields) - set(REVIEW_RECORD_FIELDS))
    if unknown:
        raise NogoError(f"a nogo_review record carries no field {', '.join(unknown)}")
    missing = sorted(f for f in REVIEW_RECORD_FIELDS if f != "supersedes" and f not in fields)
    if missing:
        raise NogoError(f"a nogo_review record is missing {', '.join(missing)}")
    return Review(
        hypothesis_key=str(fields["hypothesis_key"]),
        declaration_hash=str(fields["declaration_hash"]),
        reviewer=str(fields["reviewer"]),
        verdict=str(fields["verdict"]),
        gate_bundle_hash=str(gate_bundle_hash),
        at=str(fields["at"]),
        supersedes=fields.get("supersedes"),
        file_offset=file_offset,
    )


def _review_of(row):
    return Review(
        hypothesis_key=row["hypothesis_key"],
        declaration_hash=row["declaration_hash"],
        reviewer=row["reviewer"],
        verdict=row["verdict"],
        gate_bundle_hash=row["gate_bundle_hash"],
        at=row["at"],
        supersedes=row["supersedes"],
        file_offset=row["file_offset"],
    )


def write_declaration(sub, declaration, *, attest_path=None, enqueue=True):
    """Write the declaration; one open review item per branch stands for whichever declaration is current."""
    if enqueue and attest_path is None:
        raise NogoError("enqueuing the review needs the attestation path, which decides whether an item is still open")
    canonical = declaration_canonical(declaration)
    with sub._tx():
        sub._put_node(DECLARATION_KIND, canonical, declaration.hash, "Replayable", declaration.declared_by)
        cur = sub.conn.execute(
            f"INSERT OR IGNORE INTO {DECLARATIONS} (hypothesis_key, declaration_hash, declared_by, at) VALUES (?, ?, ?, ?)",
            (declaration.hypothesis_key, declaration.hash, declaration.declared_by, declaration.at),
        )
    lg.info(
        "write",
        table=DECLARATIONS,
        hash=declaration.hash,
        hypothesis_key=declaration.hypothesis_key,
        status="inserted" if cur.rowcount else "exists",
    )
    item_id = None
    if enqueue and cur.rowcount:
        item_id = open_review_item(sub, declaration.hypothesis_key, attest_path)
        if item_id is None:
            item_id = enqueue_review(sub, declaration.hypothesis_key, at=declaration.at)
    return declaration.hash, item_id


def enqueue_review(sub, hypothesis_key, *, at=None):
    item = human_queue.Item(
        human_queue.NOGO_REVIEW, human_queue.BRANCH, hypothesis_key, at or _now(), blocker=human_queue.NOGO_REVIEW
    )
    return human_queue.enqueue(sub, item)


def current_declaration(sub, hypothesis_key):
    row = sub.conn.execute(
        f"SELECT * FROM {DECLARATIONS} WHERE hypothesis_key = ? ORDER BY rowid DESC LIMIT 1", (hypothesis_key,)
    ).fetchone()
    return None if row is None else dict(row)


def write_review(sub, review):
    canonical = review_canonical(review)
    with sub._tx():
        sub._put_node(REVIEW_KIND, canonical, review.hash, "Replayable", review.reviewer)
        existing = sub.conn.execute(
            f"SELECT row_id FROM {REVIEWS} WHERE record_digest = ? AND file_offset = ?",
            (review.record_digest, review.file_offset),
        ).fetchone()
        if existing is not None:
            lg.info("write", table=REVIEWS, hash=review.hash, status="exists", row_id=existing["row_id"])
            return existing["row_id"]
        cur = sub.conn.execute(
            f"INSERT INTO {REVIEWS} (hypothesis_key, declaration_hash, reviewer, verdict, gate_bundle_hash, at, supersedes, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                review.hypothesis_key,
                review.declaration_hash,
                review.reviewer,
                review.verdict,
                review.gate_bundle_hash,
                review.at,
                review.supersedes,
                review.record_digest,
                review.file_offset,
            ),
        )
        row_id = cur.lastrowid
    lg.info("write", table=REVIEWS, hash=review.hash, status="inserted", row_id=row_id, verdict=review.verdict)
    return row_id


def reviews_for(sub, hypothesis_key):
    rows = sub.conn.execute(
        f"SELECT * FROM {REVIEWS} WHERE hypothesis_key = ? ORDER BY row_id", (hypothesis_key,)
    ).fetchall()
    return [dict(r) for r in rows]


def row_visible(row, attest_path):
    """A row counts only when the digest re-derived from its fields is the record at its offset."""
    derived = _review_of(row).record_digest
    if derived != row["record_digest"]:
        return False
    return attest.attestation_record_matches(attest_path, row["file_offset"], derived)


def visible_reviews(sub, hypothesis_key, attest_path):
    return [row for row in reviews_for(sub, hypothesis_key) if row_visible(row, attest_path)]


def mirrored(sub, hypothesis_key, record_digest, file_offset):
    """A review row at that digest and offset, honest to its fields, and naming the current declaration."""
    current = current_declaration(sub, hypothesis_key)
    if current is None:
        return False
    return any(
        row["record_digest"] == record_digest
        and row["file_offset"] == file_offset
        and row["declaration_hash"] == current["declaration_hash"]
        and _review_of(row).record_digest == record_digest
        for row in reviews_for(sub, hypothesis_key)
    )


@dataclass(frozen=True)
class Flag:
    hypothesis_key: str
    declaration_hash: str | None
    review_verdict: str | None

    @property
    def declared(self):
        return self.declaration_hash is not None

    @property
    def accepted(self):
        return self.review_verdict == ACCEPT_FOR_TIERING

    @property
    def flagged(self):
        return not self.declared


def flag(sub, hypothesis_key, attest_path=None):
    declaration = current_declaration(sub, hypothesis_key)
    if declaration is None:
        return Flag(hypothesis_key, None, None)
    verdict = None
    if attest_path is not None:
        for row in visible_reviews(sub, hypothesis_key, attest_path):
            if row["declaration_hash"] == declaration["declaration_hash"]:
                verdict = row["verdict"]
    return Flag(hypothesis_key, declaration["declaration_hash"], verdict)


def open_review_item(sub, hypothesis_key, attest_path):
    rows = sub.conn.execute(
        f"SELECT item_id FROM {human_queue.ITEMS} WHERE class = ? AND target_kind = ? AND target = ? ORDER BY rowid",
        (human_queue.NOGO_REVIEW, human_queue.BRANCH, hypothesis_key),
    ).fetchall()
    for row in rows:
        if human_queue.visible_closure(sub, row["item_id"], attest_path) is None:
            return row["item_id"]
    return None
