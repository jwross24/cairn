import json
import re
from datetime import UTC, datetime

from cairn import canon, keys, log
from cairn.bundle import BundleError
from cairn.canon import NON_EMPTY_STR, Field, Struct
from cairn.substrate import blob_hash

lg = log.get("human_authority")

OPERATOR_SESSION = "operator_session"
STATEMENT_RATIFICATION = "statement_ratification"
YANK_RULING = "yank_ruling"
SALT_ISSUANCE = "salt_issuance"
KINDS = (OPERATOR_SESSION, STATEMENT_RATIFICATION, YANK_RULING, SALT_ISSUANCE)
TABLE = "human_authority_records"
DEFAULT_SESSION_MAX_DURATION_S = 3600
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")

RECORDS = {
    OPERATOR_SESSION: Struct(
        OPERATOR_SESSION,
        [
            Field("kind", NON_EMPTY_STR),
            Field("gate_bundle_hash", NON_EMPTY_STR),
            Field("session_id", NON_EMPTY_STR),
            Field("issued_by", NON_EMPTY_STR),
            Field("opened_at", NON_EMPTY_STR),
            Field("expires_at", NON_EMPTY_STR),
        ],
    ),
    STATEMENT_RATIFICATION: Struct(
        STATEMENT_RATIFICATION,
        [
            Field("kind", NON_EMPTY_STR),
            Field("gate_bundle_hash", NON_EMPTY_STR),
            Field("statement_hash", NON_EMPTY_STR),
            Field("issued_by", NON_EMPTY_STR),
            Field("at", NON_EMPTY_STR),
        ],
    ),
    YANK_RULING: Struct(
        YANK_RULING,
        [
            Field("kind", NON_EMPTY_STR),
            Field("gate_bundle_hash", NON_EMPTY_STR),
            Field("ruling_ref", NON_EMPTY_STR),
            Field("yank_id", NON_EMPTY_STR),
            Field("skill_identity_hash", NON_EMPTY_STR),
            Field("reach_predicate", NON_EMPTY_STR),
            Field("issued_by", NON_EMPTY_STR),
            Field("at", NON_EMPTY_STR),
        ],
    ),
    SALT_ISSUANCE: Struct(
        SALT_ISSUANCE,
        [
            Field("kind", NON_EMPTY_STR),
            Field("gate_bundle_hash", NON_EMPTY_STR),
            Field("class_key", NON_EMPTY_STR),
            Field("salt", NON_EMPTY_STR),
            Field("issued_by", NON_EMPTY_STR),
            Field("at", NON_EMPTY_STR),
        ],
    ),
}
FIELD_NAMES = {
    kind: tuple(name for name in schema.names if name not in ("kind", "gate_bundle_hash"))
    for kind, schema in RECORDS.items()
}


class HumanAuthorityError(ValueError):
    pass


def _hash(value, name):
    if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
        raise HumanAuthorityError(f"{name} must be a lowercase 64-character hex hash")


def _timestamp(value, name):
    if not isinstance(value, str) or not value:
        raise HumanAuthorityError(f"{name} must be a timezone-aware ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise HumanAuthorityError(f"{name} must be a timezone-aware ISO timestamp") from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise HumanAuthorityError(f"{name} must include a timezone offset")
    try:
        return parsed.astimezone(UTC)
    except OverflowError:
        raise HumanAuthorityError(f"{name} is outside the supported UTC timestamp range") from None


def _reach_json(value):
    if not isinstance(value, str):
        raise HumanAuthorityError("reach_predicate must be canonical JSON text")

    def reject_constant(constant):
        raise ValueError(f"invalid JSON constant {constant}")

    try:
        parsed = json.loads(value, parse_constant=reject_constant)
    except TypeError, ValueError:
        raise HumanAuthorityError("reach_predicate must be canonical JSON text") from None
    if not isinstance(parsed, dict):
        raise HumanAuthorityError("reach_predicate must be a JSON object")
    canonical = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
    if canonical != value:
        raise HumanAuthorityError("reach_predicate must be sorted compact JSON")
    return canonical


def _validate(kind, payload):
    if kind not in RECORDS:
        raise HumanAuthorityError(f"unknown human authority kind {kind!r}")
    if not isinstance(payload, dict):
        raise HumanAuthorityError("human authority fields must be an object")
    if payload.get("kind") != kind:
        raise HumanAuthorityError(f"record kind must be {kind!r}")
    for name in ("kind", "gate_bundle_hash", *FIELD_NAMES[kind]):
        value = payload.get(name)
        if isinstance(value, str) and not value.strip():
            raise HumanAuthorityError(f"{name} must not be blank")
    _hash(payload.get("gate_bundle_hash"), "gate_bundle_hash")
    if kind == OPERATOR_SESSION:
        opened = _timestamp(payload["opened_at"], "opened_at")
        expires = _timestamp(payload["expires_at"], "expires_at")
        duration = (expires - opened).total_seconds()
        if duration <= 0 or duration > DEFAULT_SESSION_MAX_DURATION_S:
            raise HumanAuthorityError("session expiry must be after opening and within 3600 seconds")
    elif kind == STATEMENT_RATIFICATION:
        _hash(payload["statement_hash"], "statement_hash")
        _timestamp(payload["at"], "at")
    elif kind == YANK_RULING:
        _hash(payload["skill_identity_hash"], "skill_identity_hash")
        _reach_json(payload["reach_predicate"])
        _timestamp(payload["at"], "at")
    else:
        _timestamp(payload["at"], "at")
    return payload


def canonical(kind, fields, *, gate_bundle_hash):
    if not isinstance(kind, str) or kind not in RECORDS:
        raise HumanAuthorityError(f"unknown human authority kind {kind!r}")
    if not isinstance(fields, dict):
        raise HumanAuthorityError("human authority fields must be an object")
    unknown = sorted(map(repr, set(fields) - set(FIELD_NAMES[kind])))
    missing = sorted(set(FIELD_NAMES.get(kind, ())) - set(fields))
    if unknown:
        raise HumanAuthorityError(f"{kind} carries unknown fields: {', '.join(unknown)}")
    if missing:
        raise HumanAuthorityError(f"{kind} is missing fields: {', '.join(missing)}")
    payload = {"kind": kind, "gate_bundle_hash": gate_bundle_hash, **fields}
    _validate(kind, payload)
    try:
        return canon.encode(RECORDS[kind], payload)
    except canon.CanonError as exc:
        raise HumanAuthorityError(str(exc)) from None


def _decode(kind, data):
    payload = canon.decode(RECORDS[kind], data)
    _validate(kind, payload)
    if canonical(
        kind, {name: payload[name] for name in FIELD_NAMES[kind]}, gate_bundle_hash=payload["gate_bundle_hash"]
    ) != bytes(data):
        raise HumanAuthorityError("record bytes are not canonical")
    return payload


def _result(payload, record_digest, file_offset):
    return {**payload, "record_digest": record_digest, "file_offset": file_offset}


def write(sub, kind, fields, *, gate_bundle_hash, file_offset):
    if isinstance(file_offset, bool) or not isinstance(file_offset, int) or file_offset < 0:
        raise HumanAuthorityError("file_offset must be a non-negative int")
    record = canonical(kind, fields, gate_bundle_hash=gate_bundle_hash)
    payload = _decode(kind, record)
    digest = blob_hash(record)
    producer = payload["issued_by"]
    with sub._tx():
        existing = sub.conn.execute(
            f"SELECT kind, canonical, producer_identity FROM {TABLE} WHERE record_digest = ? AND file_offset = ?",
            (digest, file_offset),
        ).fetchone()
        if existing is not None:
            if (
                existing["kind"] != kind
                or bytes(existing["canonical"]) != record
                or existing["producer_identity"] != producer
            ):
                raise HumanAuthorityError("an authority mirror already occupies this digest and offset")
        else:
            sub.conn.execute(
                f"INSERT INTO {TABLE} (kind, canonical, record_digest, file_offset, producer_identity) VALUES (?, ?, ?, ?, ?)",
                (kind, record, digest, file_offset, producer),
            )
        sub.put_node(kind, record, producer_identity=producer)
    lg.info("write", table=TABLE, kind=kind, digest=digest, offset=file_offset, status="inserted")
    return _result(payload, digest, file_offset)


def append(sub, attest_path, kind, fields, *, gate_bundle_hash):
    record = canonical(kind, fields, gate_bundle_hash=gate_bundle_hash)
    from cairn import attest

    offset = attest.append_record(attest_path, record)
    return write(sub, kind, fields, gate_bundle_hash=gate_bundle_hash, file_offset=offset)


def visible_records(sub, kind, attest_path):
    if not isinstance(kind, str) or kind not in RECORDS:
        raise HumanAuthorityError(f"unknown human authority kind {kind!r}")
    from cairn import attest

    rows = sub.conn.execute(
        f"SELECT kind, canonical, record_digest, file_offset, producer_identity FROM {TABLE} WHERE kind = ? ORDER BY file_offset, record_digest",
        (kind,),
    ).fetchall()
    visible = []
    for row in rows:
        try:
            record = bytes(row["canonical"])
            payload = _decode(kind, record)
            digest = blob_hash(record)
            offset = row["file_offset"]
            if (
                row["kind"] != kind
                or row["record_digest"] != digest
                or row["producer_identity"] != payload["issued_by"]
                or isinstance(offset, bool)
                or not isinstance(offset, int)
                or offset < 0
            ):
                continue
            body = attest.read_record(attest_path, offset)
            if body != record:
                continue
            node = sub.get_node(keys.node_hash(kind, record))
            if (
                node is None
                or node["kind"] != kind
                or bytes(node["canonical"]) != record
                or node["producer_identity"] != payload["issued_by"]
            ):
                continue
        except canon.CanonError, HumanAuthorityError, attest.AttestationError, OSError, TypeError, ValueError:
            continue
        visible.append(_result(payload, digest, offset))
    return visible


def _valid_now(at, name="at"):
    try:
        return _timestamp(at, name)
    except HumanAuthorityError:
        return None


def operator_session_open(sub, gate, attest_path, *, at):
    now = _valid_now(at)
    if now is None:
        return False
    try:
        gate_hash = gate.hash
        _hash(gate_hash, "gate_bundle_hash")
        policy = gate.tiers["operator_session"]
        if not isinstance(policy, dict) or not isinstance(policy.get("required"), bool):
            return False
        if set(policy) != {"required", "max_duration_s"}:
            return False
        cap = policy["max_duration_s"]
        if isinstance(cap, bool) or not isinstance(cap, int) or not 1 <= cap <= DEFAULT_SESSION_MAX_DURATION_S:
            return False
    except AttributeError, BundleError, KeyError, TypeError, ValueError:
        return False
    if not policy["required"]:
        return True
    for record in visible_records(sub, OPERATOR_SESSION, attest_path):
        if record["gate_bundle_hash"] != gate_hash:
            continue
        opened = _valid_now(record["opened_at"], "opened_at")
        expires = _valid_now(record["expires_at"], "expires_at")
        if opened is None or expires is None or not opened <= now < expires:
            continue
        if (expires - opened).total_seconds() <= cap:
            return True
    return False


def statement_ratified(sub, statement_hash, gate_bundle_hash, attest_path):
    try:
        _hash(statement_hash, "statement_hash")
        _hash(gate_bundle_hash, "gate_bundle_hash")
    except HumanAuthorityError:
        return False
    now = datetime.now(UTC)
    return any(
        record["statement_hash"] == statement_hash
        and record["gate_bundle_hash"] == gate_bundle_hash
        and (at := _valid_now(record["at"])) is not None
        and at <= now
        for record in visible_records(sub, STATEMENT_RATIFICATION, attest_path)
    )


def yank_ruling_matches(
    sub,
    *,
    yank_id,
    skill_identity_hash,
    reach,
    ruling_ref,
    record_digest,
    file_offset,
    attest_path,
):
    try:
        _hash(skill_identity_hash, "skill_identity_hash")
        _hash(record_digest, "record_digest")
        wanted_reach = json.dumps(reach, sort_keys=True, separators=(",", ":"))
    except HumanAuthorityError, TypeError, ValueError:
        return False
    if isinstance(file_offset, bool) or not isinstance(file_offset, int) or file_offset < 0:
        return False
    now = datetime.now(UTC)
    return any(
        record["yank_id"] == yank_id
        and record["skill_identity_hash"] == skill_identity_hash
        and record["reach_predicate"] == wanted_reach
        and record["ruling_ref"] == ruling_ref
        and record["record_digest"] == record_digest
        and record["file_offset"] == file_offset
        and (at := _valid_now(record["at"])) is not None
        and at <= now
        for record in visible_records(sub, YANK_RULING, attest_path)
    )


def salt_issuance_matches(sub, *, class_key, salt, record_digest, file_offset, attest_path):
    try:
        _hash(record_digest, "record_digest")
    except HumanAuthorityError:
        return False
    if isinstance(file_offset, bool) or not isinstance(file_offset, int) or file_offset < 0:
        return False
    now = datetime.now(UTC)
    return any(
        record["class_key"] == class_key
        and record["salt"] == salt
        and record["record_digest"] == record_digest
        and record["file_offset"] == file_offset
        and (at := _valid_now(record["at"])) is not None
        and at <= now
        for record in visible_records(sub, SALT_ISSUANCE, attest_path)
    )
