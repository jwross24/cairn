import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import blake3

from cairn import canon, keys, log
from cairn.canon import BLOBREF, INT, STR, Field, Map, Struct

lg = log.get("substrate")

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
BUSY_TIMEOUT_MS = 5000
GRADES = ("Replayable", "Verifiable", "AuditOnly")
STATUSES = ("RUNNING", "OK", "FAIL", "DISAGREE", "BUDGET_EXCEEDED", "BLOCKED", "SKILL_YANKED", "INTERRUPTED")
TERMINAL_STATUSES = STATUSES[1:]
ROOT_KINDS = ("recipe", "ledger_row", "certificate", "divergence")
EDGE_OUTPUT_OF = "output_of"
EDGE_INPUT = "input"
EDGE_MEMBER = "member"
EDGE_CERTIFIES = "certifies"

OUTPUT_MANIFEST = Struct("output_manifest", [Field("artifacts", Map(STR, BLOBREF))])
SELFTEST_CERT = keys.SELFTEST_CERT
RECEIPT_FLOAT_FIELDS = ("start_mono", "end_mono", "cpu_user_s", "cpu_sys_s", "wall_s")
RECEIPT_INT_FIELDS = ("peak_rss_bytes", "scratch_bytes_written", "exit_status")
RECEIPT_FIELDS = (
    "gate_bundle_hash",
    "start_mono",
    "end_mono",
    "cpu_user_s",
    "cpu_sys_s",
    "wall_s",
    "peak_rss_bytes",
    "scratch_bytes_written",
    "exit_status",
    "stdout_digest",
    "stderr_digest",
    "tool_digests_hash",
)
RECEIPT = Struct("receipt", [Field(name, INT if name in RECEIPT_INT_FIELDS else STR) for name in RECEIPT_FIELDS])
KIND_TAGS = {**keys.TAGS_BY_KIND, "skill_certificate": keys.TAG_SELFTEST_CERT}


class SubstrateError(Exception):
    pass


class HashCollision(SubstrateError):
    pass


class HashMismatch(SubstrateError):
    pass


class GradeError(SubstrateError):
    pass


class UnknownNode(SubstrateError):
    pass


class UnknownAttempt(SubstrateError):
    pass


class WriterAlreadyOpen(SubstrateError):
    pass


@dataclass(frozen=True)
class Served:
    attempt_id: str
    output_manifest_hash: str


def _now():
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _hex(digest):
    return digest.hex() if isinstance(digest, (bytes, bytearray)) else str(digest)


def blob_hash(data):
    return blake3.blake3(bytes(data)).hexdigest()


def node_hash_for(kind, canonical):
    tag = KIND_TAGS.get(kind)
    if tag is not None:
        return canon.digest(tag, canonical)
    return keys.node_hash(kind, canonical)


def certificate_canonical(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return canon.encode(
        SELFTEST_CERT,
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        },
    )


def certificate_hash(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return keys.selftest_cert_hash(
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        }
    )


def output_manifest_canonical(artifacts):
    return canon.encode(OUTPUT_MANIFEST, {"artifacts": artifacts})


def output_manifest_hash(artifacts):
    return keys.node_hash("output_manifest", output_manifest_canonical(artifacts))


def receipt_canonical(receipt):
    missing = [f for f in RECEIPT_FIELDS if f not in receipt]
    if missing:
        raise SubstrateError(f"receipt missing field(s) {missing}")
    value = {}
    for name in RECEIPT_FIELDS:
        raw = receipt[name]
        if name in RECEIPT_FLOAT_FIELDS:
            value[name] = repr(float(raw))
        elif name in RECEIPT_INT_FIELDS:
            value[name] = int(raw)
        else:
            value[name] = str(raw)
    return canon.encode(RECEIPT, value)


def receipt_hash(receipt):
    return keys.node_hash("receipt", receipt_canonical(receipt))


def grade_weaker(from_grade, to_grade):
    return GRADES.index(to_grade) > GRADES.index(from_grade)


def attempt_eligible(status, disowned_at, inadmissible, do_not_cache, blobs_present):
    if do_not_cache:
        return "do_not_cache"
    if status != "OK":
        return f"status={status}"
    if disowned_at is not None:
        return "disowned"
    if inadmissible:
        return "inadmissible"
    if not blobs_present:
        return "missing_blob"
    return None


MISSING_BLOB_PREDICATE = (
    "NOT EXISTS (SELECT 1 FROM lineage l WHERE l.parent_hash = a.output_manifest_hash AND l.edge_kind = 'member' "
    "AND NOT EXISTS (SELECT 1 FROM blobs b WHERE b.hash = l.child_hash))"
)


def serve_sql(*, exclude_disowned=True, require_blobs=True, require_ok=True):
    predicates = ["a.recipe_key = ?", "a.inadmissible = 0", "r.do_not_cache = 0", "a.output_manifest_hash IS NOT NULL"]
    if require_ok:
        predicates.append("a.status = 'OK'")
    if exclude_disowned:
        predicates.append("a.disowned_at IS NULL")
    if require_blobs:
        predicates.append(MISSING_BLOB_PREDICATE)
    return (
        "SELECT a.attempt_id, a.output_manifest_hash FROM attempts a JOIN recipes r ON r.recipe_key = a.recipe_key WHERE "
        + " AND ".join(predicates)
        + " ORDER BY a.ended_at DESC, a.rowid DESC LIMIT 1"
    )


SERVE_SQL = serve_sql()

_WRITER = None


class Substrate:
    def __init__(self, conn, path, role):
        self.conn = conn
        self.path = path
        self.role = role
        self.closed = False

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
            mode = conn.execute("PRAGMA journal_mode=WAL").fetchone()[0]
            if mode != "wal":
                conn.close()
                raise SubstrateError(f"journal_mode is {mode!r}, expected 'wal'")
            conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA foreign_keys=ON")
            conn.executescript(SCHEMA_PATH.read_text())
            self = cls(conn, path, role)
            _WRITER = self
        else:
            conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_MS / 1000, autocommit=True)
            conn.row_factory = sqlite3.Row
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

    @contextmanager
    def _tx(self):
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.conn.execute("ROLLBACK")
            raise
        self.conn.execute("COMMIT")

    def journal_mode(self):
        return self.conn.execute("PRAGMA journal_mode").fetchone()[0]

    def get_blob(self, digest):
        row = self.conn.execute("SELECT bytes FROM blobs WHERE hash = ?", (digest,)).fetchone()
        return None if row is None else bytes(row[0])

    def has_blob(self, digest):
        return self.conn.execute("SELECT 1 FROM blobs WHERE hash = ?", (digest,)).fetchone() is not None

    def get_node(self, digest):
        row = self.conn.execute("SELECT * FROM nodes WHERE hash = ?", (digest,)).fetchone()
        return None if row is None else dict(row)

    def get_recipe(self, recipe_key):
        row = self.conn.execute("SELECT * FROM recipes WHERE recipe_key = ?", (recipe_key,)).fetchone()
        return None if row is None else dict(row)

    def get_attempt(self, attempt_id):
        row = self.conn.execute("SELECT * FROM attempts WHERE attempt_id = ?", (attempt_id,)).fetchone()
        return None if row is None else dict(row)

    def attempts_for(self, recipe_key):
        rows = self.conn.execute("SELECT * FROM attempts WHERE recipe_key = ? ORDER BY rowid", (recipe_key,)).fetchall()
        return [dict(r) for r in rows]

    def get_receipt(self, digest):
        row = self.conn.execute("SELECT * FROM receipts WHERE receipt_hash = ?", (digest,)).fetchone()
        return None if row is None else dict(row)

    def get_certificate(self, identity_bundle_hash):
        row = self.conn.execute(
            "SELECT * FROM skill_certificates WHERE identity_bundle_hash = ?", (identity_bundle_hash,)
        ).fetchone()
        return None if row is None else dict(row)

    def lineage_of(self, child_hash):
        rows = self.conn.execute(
            "SELECT * FROM lineage WHERE child_hash = ? ORDER BY parent_hash, edge_kind", (child_hash,)
        ).fetchall()
        return [dict(r) for r in rows]

    def is_root(self, root_kind, node_hash):
        return (
            self.conn.execute(
                "SELECT 1 FROM roots WHERE root_kind = ? AND node_hash = ?", (root_kind, node_hash)
            ).fetchone()
            is not None
        )

    def grade_history(self, node_hash):
        rows = self.conn.execute(
            "SELECT * FROM grade_history WHERE node_hash = ? ORDER BY seq", (node_hash,)
        ).fetchall()
        return [dict(r) for r in rows]

    def effective_grade(self, node_hash):
        row = self.conn.execute(
            "SELECT to_grade FROM grade_history WHERE node_hash = ? ORDER BY seq DESC LIMIT 1", (node_hash,)
        ).fetchone()
        if row is not None:
            return row[0]
        row = self.conn.execute("SELECT replay_grade FROM nodes WHERE hash = ?", (node_hash,)).fetchone()
        if row is None:
            raise UnknownNode(f"no node {node_hash}")
        return row[0]

    def certified(self, identity_bundle_hash):
        row = self.conn.execute(
            "SELECT cert_hash, transcript_hash, env_manifest_hash FROM skill_certificates WHERE identity_bundle_hash = ?",
            (identity_bundle_hash,),
        ).fetchone()
        if row is None:
            return False
        return (
            certificate_hash(identity_bundle_hash, row["transcript_hash"], row["env_manifest_hash"]) == row["cert_hash"]
        )

    def yanked(self, identity_bundle_hash):
        return (
            self.conn.execute(
                "SELECT 1 FROM yank_records WHERE skill_identity_hash = ? LIMIT 1", (identity_bundle_hash,)
            ).fetchone()
            is not None
        )

    def manifest_blobs_present(self, manifest_hash):
        row = self.conn.execute(
            "SELECT count(*) FROM lineage l WHERE l.parent_hash = ? AND l.edge_kind = 'member' AND NOT EXISTS (SELECT 1 FROM blobs b WHERE b.hash = l.child_hash)",
            (manifest_hash,),
        ).fetchone()
        return row[0] == 0

    def serve(self, recipe_key):
        row = self.conn.execute(SERVE_SQL, (recipe_key,)).fetchone()
        if row is not None:
            served = Served(row["attempt_id"], row["output_manifest_hash"])
            lg.info(
                "serve",
                recipe_key=recipe_key,
                served=True,
                attempt_id=served.attempt_id,
                output_manifest_hash=served.output_manifest_hash,
            )
            return served
        lg.info("serve", recipe_key=recipe_key, served=False, why_not=self._why_not_served(recipe_key))
        return None

    def _why_not_served(self, recipe_key):
        recipe = self.get_recipe(recipe_key)
        if recipe is None:
            return "unknown_recipe"
        attempts = self.attempts_for(recipe_key)
        if not attempts:
            return "no_attempts"
        newest = attempts[-1]
        present = newest["output_manifest_hash"] is not None and self.manifest_blobs_present(
            newest["output_manifest_hash"]
        )
        return (
            attempt_eligible(
                newest["status"], newest["disowned_at"], newest["inadmissible"], recipe["do_not_cache"], present
            )
            or "no_eligible_attempt"
        )

    def put_blob(self, data):
        data = bytes(data)
        digest = blob_hash(data)
        with self._tx():
            row = self.conn.execute("SELECT bytes FROM blobs WHERE hash = ?", (digest,)).fetchone()
            if row is not None:
                if bytes(row[0]) != data:
                    raise HashCollision(f"blob {digest} exists with different bytes")
                lg.info("write", table="blobs", hash=digest, status="exists")
                return digest
            self.conn.execute(
                "INSERT INTO blobs (hash, size, bytes, created_at) VALUES (?, ?, ?, ?)",
                (digest, len(data), data, _now()),
            )
        lg.info("write", table="blobs", hash=digest, status="inserted", size=len(data))
        return digest

    def put_node(self, kind, canonical, *, replay_grade="Replayable", producer_identity=None, hash=None):
        canonical = bytes(canonical)
        digest = node_hash_for(kind, canonical)
        if hash is not None and hash != digest:
            raise HashMismatch(f"caller hash {hash} != recomputed {digest} for kind {kind!r}")
        if replay_grade not in GRADES:
            raise ValueError(f"replay_grade must be one of {GRADES}, got {replay_grade!r}")
        with self._tx():
            return self._put_node(kind, canonical, digest, replay_grade, producer_identity)

    def _put_node(self, kind, canonical, digest, replay_grade, producer_identity):
        row = self.conn.execute("SELECT kind, canonical FROM nodes WHERE hash = ?", (digest,)).fetchone()
        if row is not None:
            if bytes(row["canonical"]) != canonical or row["kind"] != kind:
                raise HashCollision(f"node {digest} exists with different bytes or kind")
            lg.info("write", table="nodes", hash=digest, kind=kind, status="exists")
            return digest
        self.conn.execute(
            "INSERT INTO nodes (hash, kind, canonical, replay_grade, producer_identity, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (digest, kind, canonical, replay_grade, producer_identity, _now()),
        )
        lg.info("write", table="nodes", hash=digest, kind=kind, status="inserted")
        return digest

    def add_lineage(self, child_hash, parent_hash, edge_kind):
        with self._tx():
            self._add_lineage(child_hash, parent_hash, edge_kind)

    def _add_lineage(self, child_hash, parent_hash, edge_kind):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO lineage (child_hash, parent_hash, edge_kind) VALUES (?, ?, ?)",
            (child_hash, parent_hash, edge_kind),
        )
        lg.info(
            "write",
            table="lineage",
            hash=child_hash,
            parent=parent_hash,
            edge_kind=edge_kind,
            status="inserted" if cur.rowcount else "exists",
        )

    def add_root(self, root_kind, node_hash):
        if root_kind not in ROOT_KINDS:
            raise ValueError(f"root_kind must be one of {ROOT_KINDS}, got {root_kind!r}")
        with self._tx():
            self._add_root(root_kind, node_hash)

    def _add_root(self, root_kind, node_hash):
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO roots (root_kind, node_hash) VALUES (?, ?)", (root_kind, node_hash)
        )
        lg.info(
            "write", table="roots", hash=node_hash, root_kind=root_kind, status="inserted" if cur.rowcount else "exists"
        )

    def put_recipe(self, recipe, *, do_not_cache=False):
        canonical = canon.encode(keys.RECIPE, recipe)
        recipe_key = node_hash_for("recipe", canonical)
        inputs_manifest_hash = keys.node_hash("inputs_manifest", canon.encode(Map(STR, BLOBREF), recipe["inputs"]))
        tool_versions_hash = keys.node_hash("tool_versions", canon.encode(Map(STR, STR), recipe["tool_versions"]))
        with self._tx():
            self._put_node("recipe", canonical, recipe_key, "Replayable", recipe["skill_identity_hash"])
            row = self.conn.execute("SELECT do_not_cache FROM recipes WHERE recipe_key = ?", (recipe_key,)).fetchone()
            if row is not None:
                if row[0] != int(bool(do_not_cache)):
                    raise SubstrateError(f"recipe {recipe_key} exists with do_not_cache={row[0]}")
                lg.info("write", table="recipes", hash=recipe_key, status="exists")
                return recipe_key
            self.conn.execute(
                "INSERT INTO recipes (recipe_key, skill_identity_hash, inputs_manifest_hash, seed, tool_versions_hash, container_digest, salt, do_not_cache) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    recipe_key,
                    recipe["skill_identity_hash"],
                    inputs_manifest_hash,
                    recipe["seed"],
                    tool_versions_hash,
                    recipe["container_digest"],
                    recipe["salt"],
                    int(bool(do_not_cache)),
                ),
            )
            self._add_root("recipe", recipe_key)
        lg.info("write", table="recipes", hash=recipe_key, status="inserted", do_not_cache=int(bool(do_not_cache)))
        return recipe_key

    def put_identity_bundle(self, bundle):
        canonical = canon.encode(keys.IDENTITY_BUNDLE, bundle)
        return self.put_node("identity_bundle", canonical)

    def put_output_manifest(
        self, artifacts, *, recipe_key=None, input_blobs=(), producer_identity=None, replay_grade="Replayable"
    ):
        canonical = output_manifest_canonical(artifacts)
        digest = keys.node_hash("output_manifest", canonical)
        with self._tx():
            self._put_node("output_manifest", canonical, digest, replay_grade, producer_identity)
            if recipe_key is not None:
                self._add_lineage(digest, recipe_key, EDGE_OUTPUT_OF)
            for blob in input_blobs:
                self._add_lineage(digest, _hex(blob), EDGE_INPUT)
            for blob, _size in artifacts.values():
                self._add_lineage(_hex(blob), digest, EDGE_MEMBER)
        return digest

    def put_receipt(self, receipt):
        canonical = receipt_canonical(receipt)
        digest = keys.node_hash("receipt", canonical)
        with self._tx():
            self._put_node("receipt", canonical, digest, "Replayable", None)
            if self.conn.execute("SELECT 1 FROM receipts WHERE receipt_hash = ?", (digest,)).fetchone() is None:
                columns = ", ".join(RECEIPT_FIELDS)
                marks = ", ".join("?" for _ in RECEIPT_FIELDS)
                self.conn.execute(
                    f"INSERT INTO receipts (receipt_hash, {columns}) VALUES (?, {marks})",
                    (digest, *[receipt[name] for name in RECEIPT_FIELDS]),
                )
                lg.info("write", table="receipts", hash=digest, status="inserted")
            else:
                lg.info("write", table="receipts", hash=digest, status="exists")
        return digest

    def start_attempt(
        self, recipe_key, *, replay_grade="Replayable", skip_cache_lookup=False, attempt_id=None, started_at=None
    ):
        attempt_id = attempt_id or uuid.uuid4().hex
        with self._tx():
            self.conn.execute(
                "INSERT INTO attempts (attempt_id, recipe_key, status, replay_grade, skip_cache_lookup, started_at) VALUES (?, ?, 'RUNNING', ?, ?, ?)",
                (attempt_id, recipe_key, replay_grade, int(bool(skip_cache_lookup)), started_at or _now()),
            )
        lg.info(
            "write",
            table="attempts",
            hash=attempt_id,
            recipe_key=recipe_key,
            status="RUNNING",
            skip_cache_lookup=int(bool(skip_cache_lookup)),
        )
        return attempt_id

    def close_attempt(
        self,
        attempt_id,
        status,
        *,
        output_manifest_hash=None,
        receipt_hash=None,
        verifier_result_hash=None,
        certificate_hash=None,
        ended_at=None,
        honor_yank=False,
    ):
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"status must be one of {TERMINAL_STATUSES}, got {status!r}")
        with self._tx():
            if honor_yank:
                from cairn import yank

                attempt = self.get_attempt(attempt_id)
                if attempt is None:
                    raise UnknownAttempt(f"no attempt {attempt_id}")
                if yank.covers_recipe(self, attempt["recipe_key"]):
                    status = "SKILL_YANKED"
            cur = self.conn.execute(
                "UPDATE attempts SET status = ?, ended_at = ?, output_manifest_hash = ?, receipt_hash = ?, verifier_result_hash = ?, certificate_hash = ? WHERE attempt_id = ?",
                (
                    status,
                    ended_at or _now(),
                    output_manifest_hash,
                    receipt_hash,
                    verifier_result_hash,
                    certificate_hash,
                    attempt_id,
                ),
            )
            if cur.rowcount == 0:
                raise UnknownAttempt(f"no attempt {attempt_id}")
        lg.info(
            "write",
            table="attempts",
            hash=attempt_id,
            status=status,
            output_manifest_hash=output_manifest_hash,
            receipt_hash=receipt_hash,
        )
        return status

    def disown(self, attempt_id, at=None):
        with self._tx():
            cur = self.conn.execute(
                "UPDATE attempts SET disowned_at = ? WHERE attempt_id = ?", (at or _now(), attempt_id)
            )
            if cur.rowcount == 0:
                raise UnknownAttempt(f"no attempt {attempt_id}")
        lg.info("write", table="attempts", hash=attempt_id, status="disowned")

    def mark_inadmissible(self, attempt_id):
        with self._tx():
            cur = self.conn.execute("UPDATE attempts SET inadmissible = 1 WHERE attempt_id = ?", (attempt_id,))
            if cur.rowcount == 0:
                raise UnknownAttempt(f"no attempt {attempt_id}")
        lg.info("write", table="attempts", hash=attempt_id, status="inadmissible")

    def mark_non_reproducible(self, recipe_key):
        with self._tx():
            rows = self.conn.execute(
                "SELECT attempt_id, output_manifest_hash, inadmissible FROM attempts WHERE recipe_key = ? AND status = 'OK' AND disowned_at IS NULL AND replay_grade = 'Replayable' ORDER BY rowid",
                (recipe_key,),
            ).fetchall()
            manifests = sorted({r["output_manifest_hash"] for r in rows if r["output_manifest_hash"] is not None})
            if len(manifests) < 2:
                raise SubstrateError(
                    f"recipe {recipe_key} has {len(manifests)} distinct OK Replayable manifest(s); divergence needs two"
                )
            for manifest in manifests:
                self._add_root("divergence", manifest)
            marked = []
            for row in rows:
                if not row["inadmissible"]:
                    self.conn.execute("UPDATE attempts SET inadmissible = 1 WHERE attempt_id = ?", (row["attempt_id"],))
                    marked.append(row["attempt_id"])
        lg.info(
            "write", table="attempts", hash=recipe_key, status="non_reproducible", attempts=marked, manifests=manifests
        )
        return marked

    def weaken_grade(self, node_hash, to, *, reason=None):
        if to not in GRADES:
            raise ValueError(f"grade must be one of {GRADES}, got {to!r}")
        with self._tx():
            current = self.effective_grade(node_hash)
            if to == current:
                raise GradeError(f"same grade: {node_hash} is already {current}")
            if not grade_weaker(current, to):
                raise GradeError(f"cannot strengthen {node_hash} from {current} to {to}")
            self.conn.execute(
                "INSERT INTO grade_history (node_hash, from_grade, to_grade, reason, at) VALUES (?, ?, ?, ?, ?)",
                (node_hash, current, to, reason, _now()),
            )
        lg.info("write", table="grade_history", hash=node_hash, status=f"{current}->{to}", reason=reason)

    def put_certificate(self, identity_bundle_hash, transcript_hash, env_manifest_hash, selftest_summary, *, at=None):
        if not isinstance(selftest_summary, str):
            selftest_summary = json.dumps(selftest_summary, sort_keys=True, separators=(",", ":"))
        canonical = certificate_canonical(identity_bundle_hash, transcript_hash, env_manifest_hash)
        cert_hash = canon.digest(keys.TAG_SELFTEST_CERT, canonical)
        with self._tx():
            if self.get_node(identity_bundle_hash) is None:
                raise UnknownNode(f"identity bundle {identity_bundle_hash} has no nodes row")
            self._put_node("skill_certificate", canonical, cert_hash, "Replayable", identity_bundle_hash)
            self._add_lineage(cert_hash, identity_bundle_hash, EDGE_CERTIFIES)
            self.conn.execute(
                "INSERT INTO skill_certificates (identity_bundle_hash, cert_hash, transcript_hash, env_manifest_hash, selftest_summary, at) VALUES (?, ?, ?, ?, ?, ?)",
                (identity_bundle_hash, cert_hash, transcript_hash, env_manifest_hash, selftest_summary, at or _now()),
            )
            self._add_root("certificate", cert_hash)
        lg.info(
            "write",
            table="skill_certificates",
            hash=cert_hash,
            identity_bundle_hash=identity_bundle_hash,
            status="inserted",
        )
        return cert_hash

    def add_yank_record(
        self,
        yank_id,
        skill_identity_hash,
        reach_predicate,
        *,
        kind,
        verdict_ref=None,
        record_digest=None,
        file_offset=None,
        ruling_ref=None,
        created_at=None,
    ):
        with self._tx():
            self.conn.execute(
                "INSERT INTO yank_records (yank_id, skill_identity_hash, reach_predicate, kind, verdict_ref, ruling_ref, record_digest, file_offset, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    yank_id,
                    skill_identity_hash,
                    reach_predicate,
                    kind,
                    verdict_ref,
                    ruling_ref,
                    record_digest,
                    file_offset,
                    created_at or _now(),
                ),
            )
        lg.info(
            "write",
            table="yank_records",
            hash=yank_id,
            skill_identity_hash=skill_identity_hash,
            kind=kind,
            status="inserted",
        )

    def add_salt(self, class_key, salt, *, kind, verdict_ref=None, record_digest=None, file_offset=None):
        with self._tx():
            self.conn.execute(
                "INSERT INTO salts (class_key, salt, kind, verdict_ref, record_digest, file_offset) VALUES (?, ?, ?, ?, ?, ?)",
                (class_key, salt, kind, verdict_ref, record_digest, file_offset),
            )
        lg.info("write", table="salts", hash=class_key, salt=salt, kind=kind, status="inserted")

    def add_escrow(
        self,
        attempt_id,
        *,
        declared_production_cost,
        declared_verification_cost,
        reserved,
        ceiling_multiplier,
        spent_at=None,
        spent_by=None,
        released_at=None,
        released_by=None,
    ):
        with self._tx():
            self.conn.execute(
                "INSERT INTO escrow (attempt_id, declared_production_cost, declared_verification_cost, reserved, spent_at, spent_by, released_at, released_by, ceiling_multiplier) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    attempt_id,
                    declared_production_cost,
                    declared_verification_cost,
                    reserved,
                    spent_at,
                    spent_by,
                    released_at,
                    released_by,
                    ceiling_multiplier,
                ),
            )
        lg.info("write", table="escrow", hash=attempt_id, status="inserted")
