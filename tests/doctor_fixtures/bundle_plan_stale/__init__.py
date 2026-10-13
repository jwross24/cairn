import sqlite3

from cairn import bundle, kat

FIXABLE = False
ONLY = "deploy"
FINDINGS = ("D-bundle-plans/invalid",)


def corrupt(shape):
    objects = bundle.source_objects(kat.REPO_ROOT / "bundle")
    objects["gate_plan"]["steps"] = [
        step for step in objects["gate_plan"]["steps"] if step["step"] != "ladder_selftest_method_identity"
    ]
    rows = bundle.rows_for(objects)
    shape.bundle = shape.root / "deploy" / "stale-plan.sqlite"
    shape.pin = shape.root / "deploy" / "stale-plan.pin"
    with sqlite3.connect(shape.bundle) as conn:
        conn.executescript(bundle.SCHEMA)
        conn.executemany(
            "INSERT INTO objects (kind, canonical) VALUES (?, ?)", [(kind, canonical) for kind, canonical, _ in rows]
        )
    bundle.write_pin(shape.bundle, shape.pin)
