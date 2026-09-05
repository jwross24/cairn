"""Yank reach, disowned propagation and the salt bump (PLAN §2, §3; decision 5).

A yank names the fault's reach as a predicate over recipe-key fields, by default the whole
implementation revision. Two kinds of row are told apart on the row itself: a `gate_verdict` yank
names the gate run or ledger entry whose verdict produced it and carries no attestation record; a
`human_path` yank names an attributed ruling by its record digest and file offset. A reach narrower
than the revision is a human ruling, whatever wrote the yank. Every attempt inside the reach gains the
append-only disowned mark and releases its unspent escrow; the class's salt advances; every claim
resting on a disowned attempt re-derives; attempts outside the reach keep their standing and serve
from cache. The ruling's coordinates are stored as given: reading the attested ruling back is the
human path's (PLAN §7 decision 5), and the tier gate refuses a new launch on any yanked revision,
whatever the reach, because its yanked read is row existence.
"""

import json
from dataclasses import dataclass

from cairn import canon, escrow, foundations, keys, log
from cairn.substrate import SubstrateError, UnknownAttempt, _now

lg = log.get("yank")

GATE_VERDICT = "gate_verdict"
HUMAN_PATH = "human_path"
KINDS = (GATE_VERDICT, HUMAN_PATH)
TABLE = "yank_records"
SALTS = "salts"
REVISION = "skill_identity_hash"
SEED = "seed"
INPUTS = "inputs"
EQUALITY_FIELDS = ("tool_versions_hash", "container_digest", "salt")
REACH_FIELDS = (REVISION, SEED, INPUTS, *EQUALITY_FIELDS)
STATUS_OK = "OK"


class YankError(SubstrateError):
    pass


class MalformedReach(YankError):
    pass


class ReachRulingRequired(YankError):
    pass


class VerdictRefRequired(YankError):
    pass


class UnknownVerdictRef(YankError):
    pass


class RulingRequired(YankError):
    pass


class DisownedTicket(YankError):
    pass


@dataclass(frozen=True)
class Ruling:
    ruling_ref: str
    record_digest: str
    file_offset: int


@dataclass(frozen=True)
class Outcome:
    yank_id: str
    kind: str
    reach: dict
    disowned: tuple
    standing: tuple
    released: tuple
    rederived: tuple
    salt: str


def default_reach(skill_identity_hash):
    return {REVISION: skill_identity_hash}


def reach_json(reach):
    return json.dumps(reach, sort_keys=True, separators=(",", ":"))


def reach_from_json(text):
    try:
        reach = json.loads(text)
    except ValueError as exc:
        raise MalformedReach(f"reach predicate is not JSON: {exc}") from None
    return reach


def _int_range(value, field):
    if isinstance(value, bool):
        raise MalformedReach(f"{field}: a bool is neither an int nor a range")
    if isinstance(value, int):
        return (value, value)
    if (
        isinstance(value, list)
        and len(value) == 2
        and all(isinstance(v, int) and not isinstance(v, bool) for v in value)
    ):
        lo, hi = value
        if lo > hi:
            raise MalformedReach(f"{field}: range [{lo}, {hi}] is empty")
        return (lo, hi)
    raise MalformedReach(f"{field}: expected an int or [lo, hi], got {value!r}")


def validate_reach(reach, skill_identity_hash):
    if not isinstance(reach, dict):
        raise MalformedReach(f"reach predicate must be a mapping, got {type(reach).__name__}")
    unknown = sorted(set(reach) - set(REACH_FIELDS))
    if unknown:
        raise MalformedReach(f"reach predicate names no recipe-key field {', '.join(unknown)}")
    if reach.get(REVISION) != skill_identity_hash:
        raise MalformedReach(f"reach predicate must name the yanked revision {skill_identity_hash} under {REVISION}")
    if SEED in reach:
        _int_range(reach[SEED], SEED)
    if INPUTS in reach:
        inputs = reach[INPUTS]
        if not isinstance(inputs, dict) or not inputs:
            raise MalformedReach(f"{INPUTS}: expected a non-empty mapping of input name to blob hashes")
        for name, hashes in inputs.items():
            if not isinstance(hashes, list) or not hashes or not all(isinstance(h, str) and h for h in hashes):
                raise MalformedReach(f"{INPUTS}.{name}: expected a non-empty list of blob hashes")
    for field in EQUALITY_FIELDS:
        if field in reach and (not isinstance(reach[field], str) or not reach[field]):
            raise MalformedReach(f"{field}: expected a non-empty str")
    return reach


def narrower(reach):
    return bool(set(reach) - {REVISION})


def covers(reach, recipe_row, recipe_fields):
    if recipe_row[REVISION] != reach[REVISION]:
        return False
    if SEED in reach:
        lo, hi = _int_range(reach[SEED], SEED)
        if not lo <= recipe_row[SEED] <= hi:
            return False
    for field in EQUALITY_FIELDS:
        if field in reach and recipe_row[field] != reach[field]:
            return False
    if INPUTS in reach:
        actual = recipe_fields[INPUTS]
        for name, hashes in reach[INPUTS].items():
            if name not in actual or actual[name][0] not in hashes:
                return False
    return True


def recipe_fields(sub, recipe_key):
    node = sub.get_node(recipe_key)
    if node is None:
        raise YankError(f"no recipe node {recipe_key}")
    return canon.decode(keys.RECIPE, node["canonical"])


def recipes_of(sub, skill_identity_hash):
    rows = sub.conn.execute(
        f"SELECT * FROM recipes WHERE {REVISION} = ? ORDER BY rowid", (skill_identity_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def in_reach(sub, reach):
    covered, outside = [], []
    for row in recipes_of(sub, reach[REVISION]):
        (covered if covers(reach, row, recipe_fields(sub, row["recipe_key"])) else outside).append(row["recipe_key"])
    return covered, outside


def _attempts(sub, recipe_keys):
    out = []
    for key in recipe_keys:
        out.extend(r["attempt_id"] for r in sub.attempts_for(key))
    return out


def verdict_recorded(sub, verdict_ref):
    if sub.conn.execute("SELECT 1 FROM gate_runs WHERE run_id = ?", (verdict_ref,)).fetchone():
        return True
    return sub.conn.execute("SELECT 1 FROM ledger_entries WHERE hash = ?", (verdict_ref,)).fetchone() is not None


def _check_authority(sub, kind, reach, verdict_ref, ruling):
    if kind not in KINDS:
        raise YankError(f"kind must be one of {KINDS}, got {kind!r}")
    if kind == GATE_VERDICT:
        if ruling is not None:
            raise YankError("a gate-verdict yank carries no ruling; a ruling makes it a human-path yank")
        if not verdict_ref:
            raise VerdictRefRequired("a gate-verdict yank names the gate run or ledger entry whose verdict produced it")
        if not verdict_recorded(sub, verdict_ref):
            raise UnknownVerdictRef(f"no gate run or ledger entry {verdict_ref} is recorded")
        if narrower(reach):
            raise ReachRulingRequired(
                "a reach narrower than the revision is installed only by an attributed human ruling beside the yank"
            )
        return
    if verdict_ref is not None:
        raise YankError("a human-path yank names its ruling, not a gate verdict")
    if ruling is None:
        raise RulingRequired("a human-path yank names an attributed ruling by record digest and file offset")
    if not ruling.ruling_ref or not ruling.record_digest or isinstance(ruling.file_offset, bool):
        raise RulingRequired("a ruling carries ruling_ref, record_digest and file_offset")
    if not isinstance(ruling.file_offset, int) or ruling.file_offset < 0:
        raise RulingRequired(f"file_offset must be a non-negative int, got {ruling.file_offset!r}")


def record(
    sub,
    *,
    yank_id,
    skill_identity_hash,
    kind,
    attest_path,
    reach=None,
    verdict_ref=None,
    ruling=None,
    at=None,
):
    reach = validate_reach(default_reach(skill_identity_hash) if reach is None else reach, skill_identity_hash)
    _check_authority(sub, kind, reach, verdict_ref, ruling)
    at = at or _now()
    settlement = {
        "kind": kind,
        "verdict_ref": verdict_ref,
        "record_digest": None if ruling is None else ruling.record_digest,
        "file_offset": None if ruling is None else ruling.file_offset,
    }
    sub.add_yank_record(
        yank_id,
        skill_identity_hash,
        reach_json(reach),
        ruling_ref=None if ruling is None else ruling.ruling_ref,
        created_at=at,
        **settlement,
    )
    sub.add_salt(skill_identity_hash, yank_id, **settlement)
    covered, outside = in_reach(sub, reach)
    disowned, released = [], []
    for attempt_id in _attempts(sub, covered):
        if sub.get_attempt(attempt_id)["disowned_at"] is not None:
            continue
        sub.disown(attempt_id, at=at)
        disowned.append(attempt_id)
        if escrow.settle_on_disown(sub, attempt_id, at=at) is not None:
            released.append(attempt_id)
    standing = tuple(a for a in _attempts(sub, outside) if sub.get_attempt(a)["disowned_at"] is None)
    rederived = foundations.rederive_for_attempts(sub, disowned, attest_path)
    outcome = Outcome(yank_id, kind, reach, tuple(disowned), standing, tuple(released), tuple(rederived), yank_id)
    lg.info(
        "record",
        yank_id=yank_id,
        skill_identity_hash=skill_identity_hash,
        kind=kind,
        reach=reach,
        verdict_ref=verdict_ref,
        ruling_ref=None if ruling is None else ruling.ruling_ref,
        disowned=list(disowned),
        standing=list(standing),
        released=list(released),
        rederived=list(rederived),
    )
    return outcome


def current_salt(sub, class_key):
    row = sub.conn.execute(
        f"SELECT salt FROM {SALTS} WHERE class_key = ? ORDER BY seq DESC LIMIT 1", (class_key,)
    ).fetchone()
    return None if row is None else row["salt"]


def records_for(sub, skill_identity_hash):
    rows = sub.conn.execute(
        f"SELECT * FROM {TABLE} WHERE {REVISION} = ? ORDER BY rowid", (skill_identity_hash,)
    ).fetchall()
    return [dict(r) for r in rows]


def offer_as_ticket(sub, attempt_id):
    """The node an attempt produced is a ticket only while the attempt is OK and owned."""
    row = sub.get_attempt(attempt_id)
    if row is None:
        raise UnknownAttempt(f"no attempt {attempt_id}")
    if row["disowned_at"] is not None:
        raise DisownedTicket(f"attempt {attempt_id} was disowned at {row['disowned_at']}; it is no ticket")
    if row["status"] != STATUS_OK:
        raise YankError(f"attempt {attempt_id} is {row['status']}; only an OK attempt is a ticket")
    return row
