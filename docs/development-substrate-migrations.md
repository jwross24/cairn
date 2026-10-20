# Substrate migrations

Operator procedure for moving an existing substrate to the schema this checkout ships. `docs/development.md` carries the other development procedures; this page is separate because that file is at the staged-file size limit.

## What a schema is and how it is recognized

A schema fingerprint is a sha256 over the normalized object list (`substrate_schema_check._schema_objects`): every table, index, trigger and view, with each table's columns. A store's fingerprint covers only the objects the shipped schema names, so an observer table a session attached to the store does not change it.

`src/cairn/migrations/manifest.json` lists the migrations in order, each with its from-fingerprint, to-fingerprint and the sha256 of its SQL file. `history.json` lists the fingerprint of every shipped schema, rebuilt from the git history of the three schema files. A migration's SQL never changes after it is recorded; a changed file is a hard refusal.

## What a migration may contain

`CREATE TABLE`, `CREATE INDEX`, `CREATE VIEW`, `CREATE TRIGGER` whose body is only `SELECT RAISE(...)`, and `ALTER TABLE ... ADD COLUMN` with a constant default. The lint (`migrate_lint.py`) refuses `UPDATE`, `DELETE`, `DROP`, `INSERT`, renames, rebuilds and non-constant defaults. A migration that creates a trigger carries `"trigger_review_required": true` in the manifest and needs a cross-family review of the commit that adds it. A change that cannot be additive is a new store.

## Opening an older store

`Substrate.open` never migrates. A store at a known older fingerprint is refused with exit code 6 (`NEEDS_MIGRATION`) and the message names `cairn substrate migrate plan --db <path>`. A store at an unknown or newer fingerprint is refused and left unmodified. `cairn doctor` reports a store that needs migration under `D-substrate/schema`.

## Procedure

Stop every process that has the store open; `apply` takes an exclusive lock and fails with exit code 5 while another connection holds it.

```bash
uv run cairn substrate migrate plan --db PATH
uv run cairn substrate migrate apply --db PATH --plan-token TOKEN
uv run cairn substrate migrate undo --db PATH --run RUN-ID
```

`plan` is read-only. It prints the steps, the backup path and a token. The token is a sha256 over the resolved path, the from and to fingerprints, the steps, a digest of every table's rows in rowid order and the `integrity_check` result, so a store that changes after the plan, or a token that is edited, is refused.

`apply` takes the exclusive lock, recomputes the token and compares it in constant time, checkpoints the WAL with `TRUNCATE`, writes `PATH.pre-migrate-<from8>-<to8>-<utc>.sqlite` through the SQLite online backup API and verifies that copy (integrity, fingerprint, row digests), then runs every step in one `BEGIN IMMEDIATE`. It checks the fingerprint after each step, proves every pre-existing table's original columns hash the same, appends one `schema_migrations` row per step and commits. A fresh connection must then pass `integrity_check`, the schema fingerprint, the row digests, a reader open and the doctor's substrate detector before `apply` reports success. A failure before the commit rolls back and leaves the backup. A failure after the commit exits 2 and prints the `undo` command.

`undo` verifies the backup against the sha256 in `PATH.pre-migrate-<run>.sqlite.json`, renames the current file to `PATH.quarantine-<run>-<utc>.sqlite` (any `-wal` and `-shm` beside it move too), and copies the backup into place. Nothing is deleted. Writes made after the migration are in the quarantined file.

## CI enforcement

`tests/unit/test_migrate_catalog.py` requires the newest migration's to-fingerprint to equal the shipped schema's fingerprint. A schema file edit without a migration fails it; adding the migration is the fix.
