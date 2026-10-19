from cairn import canon, keys, log
from cairn.canon import BLOBREF, STR, Map
from cairn.substrate_codec import (
    EDGE_INPUT,
    EDGE_MEMBER,
    EDGE_OUTPUT_OF,
    GRADES,
    RECEIPT_FIELDS,
    ROOT_KINDS,
    _hex,
    _now,
    blob_hash,
    node_hash_for,
    output_manifest_canonical,
    receipt_canonical,
)
from cairn.substrate_errors import HashCollision, HashMismatch, SubstrateError
from cairn.substrate_reads import SubstrateReads

lg = log.get("substrate")


class SubstrateNodeWrites(SubstrateReads):
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
