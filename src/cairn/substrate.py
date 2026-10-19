import sqlite3
from pathlib import Path

from cairn import log
from cairn.substrate_attempts import SubstrateAttemptWrites
from cairn.substrate_codec import (
    EDGE_CERTIFIES,
    EDGE_INPUT,
    EDGE_MEMBER,
    EDGE_OUTPUT_OF,
    GRADES,
    KIND_TAGS,
    MISSING_BLOB_PREDICATE,
    OUTPUT_MANIFEST,
    RECEIPT,
    RECEIPT_FIELDS,
    RECEIPT_FLOAT_FIELDS,
    RECEIPT_INT_FIELDS,
    ROOT_KINDS,
    SELFTEST_CERT,
    SERVE_SQL,
    STATUSES,
    TERMINAL_STATUSES,
    Served,
    _hex,
    _now,
    attempt_eligible,
    blob_hash,
    certificate_canonical,
    certificate_hash,
    grade_weaker,
    node_hash_for,
    output_manifest_canonical,
    output_manifest_hash,
    receipt_canonical,
    receipt_hash,
    serve_sql,
)
from cairn.substrate_errors import (
    GradeError,
    HashCollision,
    HashMismatch,
    SchemaMismatch,
    SubstrateError,
    UnknownAttempt,
    UnknownNode,
    WriterAlreadyOpen,
)
from cairn.substrate_schema_check import _schema_mismatches, _schema_objects

__all__ = [
    "EDGE_CERTIFIES",
    "EDGE_INPUT",
    "EDGE_MEMBER",
    "EDGE_OUTPUT_OF",
    "GRADES",
    "KIND_TAGS",
    "MISSING_BLOB_PREDICATE",
    "OUTPUT_MANIFEST",
    "RECEIPT",
    "RECEIPT_FIELDS",
    "RECEIPT_FLOAT_FIELDS",
    "RECEIPT_INT_FIELDS",
    "ROOT_KINDS",
    "SELFTEST_CERT",
    "SERVE_SQL",
    "STATUSES",
    "TERMINAL_STATUSES",
    "GradeError",
    "HashCollision",
    "HashMismatch",
    "SchemaMismatch",
    "Served",
    "Substrate",
    "SubstrateError",
    "UnknownAttempt",
    "UnknownNode",
    "WriterAlreadyOpen",
    "_hex",
    "_now",
    "attempt_eligible",
    "blob_hash",
    "certificate_canonical",
    "certificate_hash",
    "grade_weaker",
    "node_hash_for",
    "output_manifest_canonical",
    "output_manifest_hash",
    "receipt_canonical",
    "receipt_hash",
    "schema_mismatches",
    "serve_sql",
]

lg = log.get("substrate")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
BUSY_TIMEOUT_MS = 5000

_WRITER = None
_SHIPPED_SCHEMA = None


def _shipped_schema():
    global _SHIPPED_SCHEMA
    if _SHIPPED_SCHEMA is None:
        conn = sqlite3.connect(":memory:")
        try:
            conn.executescript(SCHEMA_PATH.read_text())
            _SHIPPED_SCHEMA = _schema_objects(conn)
        finally:
            conn.close()
    return _SHIPPED_SCHEMA


def schema_mismatches(conn):
    actual = _schema_objects(conn)
    return ["the store holds no schema at all"] if not actual else _schema_mismatches(_shipped_schema(), actual)


def _require_shipped_schema(conn, path):
    reasons = schema_mismatches(conn)
    if reasons:
        shown = "; ".join(reasons[:8])
        if len(reasons) > 8:
            shown += f"; and {len(reasons) - 8} more"
        raise SchemaMismatch(
            f"{path} was not created by the shipped schema and this project ships no migration: {shown}"
        )


class Substrate(SubstrateAttemptWrites):
    @classmethod
    def open(cls, path, role="writer"):
        global _WRITER
        if role not in ("writer", "reader"):
            raise ValueError(f"role must be 'writer' or 'reader', got {role!r}")
        path = Path(path)
        if role == "writer":
            if _WRITER is not None and not _WRITER.closed:
                raise WriterAlreadyOpen(f"a writer is already open on {_WRITER.path}")
            conn = sqlite3.connect(str(path), timeout=BUSY_TIMEOUT_MS / 1000, autocommit=True)
            conn.row_factory = sqlite3.Row
            try:
                # the refusal reads the store before any pragma writes to it
                fresh = not _schema_objects(conn)
                if not fresh:
                    _require_shipped_schema(conn, path)
                mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
                if mode != "wal":
                    raise SubstrateError(f"journal_mode is {mode!r}, expected 'wal'")
                conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
                conn.execute("PRAGMA synchronous=NORMAL")
                conn.execute("PRAGMA foreign_keys=ON")
                if fresh:
                    conn.executescript(SCHEMA_PATH.read_text())
            except BaseException:
                conn.close()
                raise
            self = cls(conn, path, role)
            _WRITER = self
        else:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000, autocommit=True)
            conn.row_factory = sqlite3.Row
            try:
                _require_shipped_schema(conn, path)
            except BaseException:
                conn.close()
                raise
            self = cls(conn, path, role)
        lg.info("open", path=str(path), role=role, journal_mode=conn.execute("PRAGMA journal_mode").fetchone()[0])
        return self

    def close(self):
        global _WRITER
        if self.closed:
            return
        self.conn.close()
        self.closed = True
        if _WRITER is self:
            _WRITER = None
        lg.info("close", path=str(self.path), role=self.role)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
