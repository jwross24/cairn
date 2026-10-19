from cairn import log
from cairn.substrate_base import SubstrateBase
from cairn.substrate_codec import SERVE_SQL, Served, attempt_eligible, certificate_hash
from cairn.substrate_errors import UnknownNode

lg = log.get("substrate")


class SubstrateReads(SubstrateBase):
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

    def yanked(self, identity_bundle_hash, *, attest_path=None):
        from cairn import yank

        return bool(yank.records_for(self, identity_bundle_hash, attest_path=attest_path))

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
