import hashlib
import sqlite3
from pathlib import Path

from _substrate_helpers import IDENTITY_A, certify, recipe

from cairn import migrate_catalog, substrate
from cairn.migrate_fingerprint import store_fingerprint
from cairn.substrate import Substrate

RECEIPT = {name: ("aa" * 32 if name.endswith(("hash", "digest")) else 1) for name in substrate.RECEIPT_FIELDS}
KEY_CHARGES_OBJECTS = (
    ("TRIGGER", "key_charges_bind_reconcile_once"),
    ("TRIGGER", "key_charges_no_delete"),
    ("INDEX", "key_charges_by_key"),
    ("TABLE", "key_charges"),
)
SCHEMA_MIGRATIONS_OBJECTS = (
    ("TRIGGER", "schema_migrations_no_update"),
    ("TRIGGER", "schema_migrations_no_delete"),
    ("TABLE", "schema_migrations"),
)
STAGES = {"v1": KEY_CHARGES_OBJECTS + SCHEMA_MIGRATIONS_OBJECTS, "v2": SCHEMA_MIGRATIONS_OBJECTS}


def shipped():
    return substrate.shipped_objects()


def catalog():
    return migrate_catalog.load_catalog()


def stage_fingerprint(stage):
    return catalog().migrations[{"v1": 0, "v2": 1}[stage]].from_fp


def store_fp(path):
    conn = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        return store_fingerprint(conn, set(shipped()))
    finally:
        conn.close()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def populate(sub):
    key = sub.put_recipe(recipe(1))
    receipt = sub.put_receipt(RECEIPT)
    attempt = sub.start_attempt(key)
    manifest = sub.put_output_manifest({"out": (sub.put_blob(b"x"), 1)}, recipe_key=key)
    sub.close_attempt(attempt, "OK", output_manifest_hash=manifest, receipt_hash=receipt)
    sub.start_attempt(key)
    certify(sub, IDENTITY_A)
    sub.conn.execute(
        "INSERT INTO key_charges (hypothesis_key, ticket_tier, origin, declared_core_s, accrued_at)"
        " VALUES ('h1', 1, 'worker', 2.5, '2026-10-20T00:00:00Z')"
    )


def make_store(directory, stage, name="substrate.sqlite"):
    path = Path(directory) / name
    with Substrate.open(path, role="writer") as sub:
        populate(sub)
    conn = sqlite3.connect(path, autocommit=True)
    try:
        for kind, object_name in STAGES[stage]:
            conn.execute(f"DROP {kind} {object_name}")
    finally:
        conn.close()
    return path
