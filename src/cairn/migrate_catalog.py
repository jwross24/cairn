import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from cairn.migrate_fingerprint import fingerprint, store_fingerprint
from cairn.migrate_lint import lint, split_statements
from cairn.substrate_schema_check import _schema_objects

MIGRATIONS_DIR = Path(__file__).with_name("migrations")
MANIFEST = "manifest.json"
HISTORY = "history.json"


class MigrationRefused(Exception):
    pass


@dataclass(frozen=True)
class Migration:
    id: str
    file: str
    from_fp: str
    to_fp: str
    sql_sha256: str
    trigger_review_required: bool
    directory: Path

    def sql_bytes(self):
        return (self.directory / self.file).read_bytes()

    def statements(self):
        return split_statements(self.sql_bytes().decode())

    def verify(self):
        actual = hashlib.sha256(self.sql_bytes()).hexdigest()
        if actual != self.sql_sha256:
            raise MigrationRefused(
                f"migration {self.id} ({self.file}) changed after it was recorded: "
                f"manifest sha256 {self.sql_sha256}, file sha256 {actual}"
            )
        problems, has_trigger = lint(self.sql_bytes().decode())
        if has_trigger and not self.trigger_review_required:
            problems.append("the migration creates a trigger and its manifest entry lacks trigger_review_required")
        if problems:
            raise MigrationRefused(f"migration {self.id} ({self.file}) is not additive: " + "; ".join(problems))


@dataclass(frozen=True)
class Catalog:
    migrations: tuple

    def by_id(self, step_id):
        return next((m for m in self.migrations if m.id == step_id), None)

    def from_fingerprints(self):
        return {m.from_fp for m in self.migrations}

    def newest(self):
        return self.migrations[-1] if self.migrations else None

    def path(self, start, target):
        steps, seen, current = [], {start}, start
        while current != target:
            step = next((m for m in self.migrations if m.from_fp == current), None)
            if step is None or step.to_fp in seen:
                return None
            steps.append(step)
            seen.add(step.to_fp)
            current = step.to_fp
        return steps

    def verify(self):
        for migration in self.migrations:
            migration.verify()


def load_catalog(directory=MIGRATIONS_DIR):
    directory = Path(directory)
    entries = json.loads((directory / MANIFEST).read_text())["migrations"]
    migrations = tuple(
        Migration(
            id=e["id"],
            file=e["file"],
            from_fp=e["from"],
            to_fp=e["to"],
            sql_sha256=e["sql_sha256"],
            trigger_review_required=bool(e.get("trigger_review_required", False)),
            directory=directory,
        )
        for e in entries
    )
    ids = [m.id for m in migrations]
    if ids != sorted(set(ids)):
        raise MigrationRefused(f"manifest ids are not unique and ascending: {ids}")
    return Catalog(migrations)


def load_history(directory=MIGRATIONS_DIR):
    return {e["fingerprint"]: e["commit"] for e in json.loads((Path(directory) / HISTORY).read_text())["schemas"]}


@dataclass(frozen=True)
class Classification:
    kind: str
    fingerprint: str | None
    steps: tuple = ()


def classify(conn, shipped_objects, catalog=None, history=None):
    actual = _schema_objects(conn)
    if not actual:
        return Classification("empty", None)
    universe = set(shipped_objects)
    current = store_fingerprint(conn, universe)
    target = fingerprint(shipped_objects)
    if current == target:
        return Classification("current", current)
    catalog = load_catalog() if catalog is None else catalog
    steps = catalog.path(current, target)
    if steps:
        return Classification("migratable", current, tuple(steps))
    history = load_history() if history is None else history
    return Classification("historical" if current in history else "unknown", current)


def enforcement_problems(shipped_objects, catalog):
    target = fingerprint(shipped_objects)
    newest = catalog.newest()
    if newest is None:
        return ["the catalog holds no migration"]
    problems = []
    if newest.to_fp != target:
        problems.append(
            f"newest migration {newest.id} ends at {newest.to_fp[:12]} but the shipped schema is {target[:12]}: "
            "a schema file changed without a migration"
        )
    problems.extend(
        f"migration {migration.id} does not lead to the shipped schema"
        for migration in catalog.migrations
        if catalog.path(migration.from_fp, target) is None
    )
    return problems
