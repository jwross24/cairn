import uuid

from cairn import canon, keys, log
from cairn.substrate_codec import (
    EDGE_CERTIFIES,
    GRADES,
    TERMINAL_STATUSES,
    _now,
    certificate_canonical,
    grade_weaker,
)
from cairn.substrate_errors import GradeError, SubstrateError, UnknownAttempt, UnknownNode
from cairn.substrate_nodes import SubstrateNodeWrites

lg = log.get("substrate")


class SubstrateAttemptWrites(SubstrateNodeWrites):
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
        attest_path=None,
    ):
        if status not in TERMINAL_STATUSES:
            raise ValueError(f"status must be one of {TERMINAL_STATUSES}, got {status!r}")
        with self._tx():
            if honor_yank:
                from cairn import yank

                attempt = self.get_attempt(attempt_id)
                if attempt is None:
                    raise UnknownAttempt(f"no attempt {attempt_id}")
                if yank.covers_recipe(self, attempt["recipe_key"], attest_path=attest_path):
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
        selftest_summary = keys.selftest_summary_text(selftest_summary)
        canonical = certificate_canonical(identity_bundle_hash, transcript_hash, env_manifest_hash, selftest_summary)
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
