import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cairn import log
from cairn.substrate import HashMismatch, node_hash_for

lg = log.get("records")


def as_json(value):
    return json.dumps(value.as_dict(), sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RecordKind:
    kind: str
    table: str
    unique_by: str
    canonical: Callable[[Any], bytes]
    index_row: Callable[[Any], dict]
    decode: Callable[[dict], Any]
    grade: str = "Replayable"
    root: str | None = None
    producer: Callable[[Any], str | None] | None = None
    generated: tuple[tuple[str, Callable[[], Any]], ...] = ()
    hash_column: str = "record_hash"


def put(sub, record_kind, value, parents=()):
    canonical = record_kind.canonical(value)
    digest = node_hash_for(record_kind.kind, canonical)
    if digest != value.hash:
        raise HashMismatch(f"{record_kind.kind} value names {value.hash}, its canonical bytes hash to {digest}")
    row = {
        record_kind.hash_column: digest,
        **record_kind.index_row(value),
        **{column: make() for column, make in record_kind.generated},
    }
    with sub.transaction():
        sub.put_node(
            record_kind.kind,
            canonical,
            replay_grade=record_kind.grade,
            producer_identity=None if record_kind.producer is None else record_kind.producer(value),
            hash=digest,
        )
        columns = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        sub.conn.execute(f"INSERT INTO {record_kind.table} ({columns}) VALUES ({marks})", tuple(row.values()))
        lg.info("write", table=record_kind.table, hash=digest, status="inserted")
        if record_kind.root is not None:
            sub.add_root(record_kind.root, digest)
        for parent in parents:
            sub.add_lineage(digest, parent, "input")
    return digest


def find(sub, record_kind, **where):
    if not all(column.isidentifier() for column in where):
        raise ValueError(f"{record_kind.table} lookup names a column that is no identifier: {sorted(where)}")
    clause = " AND ".join(f"{column} = ?" for column in where) or "1"
    rows = sub.conn.execute(
        f"SELECT * FROM {record_kind.table} WHERE {clause} ORDER BY rowid", tuple(where.values())
    ).fetchall()
    return [_verified(sub, record_kind, row) for row in rows]


def find_one(sub, record_kind, **where):
    values = find(sub, record_kind, **where)
    if len(values) > 1:
        raise LookupError(f"{record_kind.table} holds {len(values)} records for {where}")
    return values[0] if values else None


def newest(sub, record_kind):
    row = sub.conn.execute(f"SELECT * FROM {record_kind.table} ORDER BY rowid DESC LIMIT 1").fetchone()
    return None if row is None else _verified(sub, record_kind, row)


def _verified(sub, record_kind, row):
    value = record_kind.decode(row)
    digest = row[record_kind.hash_column]
    node = sub.get_node(digest)
    if (
        value.hash != digest
        or node is None
        or node["kind"] != record_kind.kind
        or bytes(node["canonical"]) != record_kind.canonical(value)
        or any(row[column] != v for column, v in record_kind.index_row(value).items())
    ):
        raise HashMismatch(
            f"{record_kind.table} record {row[record_kind.unique_by]} does not match its content address"
        )
    return value
