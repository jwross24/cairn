CREATE TABLE IF NOT EXISTS schema_migrations (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    from_fingerprint TEXT NOT NULL,
    to_fingerprint TEXT NOT NULL,
    sql_sha256 TEXT NOT NULL,
    cairn_git_sha TEXT NOT NULL,
    applied_at TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS schema_migrations_no_update BEFORE UPDATE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS schema_migrations_no_delete BEFORE DELETE ON schema_migrations BEGIN SELECT RAISE(ABORT, 'append-only'); END;
