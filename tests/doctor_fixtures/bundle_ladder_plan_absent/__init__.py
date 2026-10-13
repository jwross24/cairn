import sqlite3

from cairn import bundle, kat

FIXABLE = False
ONLY = "deploy"
FINDINGS = ("D-bundle-plans/invalid",)


def corrupt(shape):
    objects = bundle.source_objects(kat.REPO_ROOT / "bundle")
    rows = bundle.rows_for({kind: value for kind, value in objects.items() if kind != "ladder_plan"})
    shape.bundle = shape.root / "deploy" / "absent-ladder-plan.sqlite"
    shape.pin = shape.root / "deploy" / "absent-ladder-plan.pin"
    with sqlite3.connect(shape.bundle) as conn:
        conn.executescript(bundle.SCHEMA)
        conn.executemany(
            "INSERT INTO objects (kind, canonical) VALUES (?, ?)", [(kind, canonical) for kind, canonical, _ in rows]
        )
    bundle.write_pin(shape.bundle, shape.pin)
