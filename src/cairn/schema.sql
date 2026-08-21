CREATE TABLE IF NOT EXISTS blobs (
    hash TEXT PRIMARY KEY,
    size INTEGER NOT NULL,
    bytes BLOB NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
    hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    canonical BLOB NOT NULL,
    replay_grade TEXT NOT NULL CHECK (replay_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    producer_identity TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS lineage (
    child_hash TEXT NOT NULL,
    parent_hash TEXT NOT NULL,
    edge_kind TEXT NOT NULL,
    PRIMARY KEY (child_hash, parent_hash, edge_kind)
);

CREATE TABLE IF NOT EXISTS roots (
    root_kind TEXT NOT NULL CHECK (root_kind IN ('recipe', 'ledger_row', 'certificate', 'divergence')),
    node_hash TEXT NOT NULL,
    PRIMARY KEY (root_kind, node_hash)
);

CREATE TABLE IF NOT EXISTS recipes (
    recipe_key TEXT PRIMARY KEY,
    skill_identity_hash TEXT NOT NULL,
    inputs_manifest_hash TEXT NOT NULL,
    seed INTEGER NOT NULL,
    tool_versions_hash TEXT NOT NULL,
    container_digest TEXT NOT NULL,
    salt TEXT NOT NULL,
    do_not_cache INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS attempts (
    attempt_id TEXT PRIMARY KEY,
    recipe_key TEXT NOT NULL,
    output_manifest_hash TEXT,
    receipt_hash TEXT,
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'OK', 'FAIL', 'DISAGREE', 'BUDGET_EXCEEDED', 'SKILL_YANKED', 'INTERRUPTED')),
    replay_grade TEXT NOT NULL CHECK (replay_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    verifier_result_hash TEXT,
    certificate_hash TEXT,
    skip_cache_lookup INTEGER NOT NULL DEFAULT 0,
    disowned_at TEXT,
    inadmissible INTEGER NOT NULL DEFAULT 0,
    started_at TEXT NOT NULL,
    ended_at TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    receipt_hash TEXT PRIMARY KEY,
    gate_bundle_hash TEXT NOT NULL,
    start_mono REAL NOT NULL,
    end_mono REAL NOT NULL,
    cpu_user_s REAL NOT NULL,
    cpu_sys_s REAL NOT NULL,
    wall_s REAL NOT NULL,
    peak_rss_bytes INTEGER NOT NULL,
    scratch_bytes_written INTEGER NOT NULL,
    exit_status INTEGER NOT NULL,
    stdout_digest TEXT NOT NULL,
    stderr_digest TEXT NOT NULL,
    tool_digests_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS skill_certificates (
    identity_bundle_hash TEXT PRIMARY KEY REFERENCES nodes(hash),
    cert_hash TEXT NOT NULL UNIQUE,
    transcript_hash TEXT NOT NULL,
    env_manifest_hash TEXT NOT NULL,
    selftest_summary TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS yank_records (
    yank_id TEXT PRIMARY KEY,
    skill_identity_hash TEXT NOT NULL,
    reach_predicate TEXT NOT NULL,
    ruling_ref TEXT,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS salts (
    class_key TEXT PRIMARY KEY,
    salt TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS escrow (
    attempt_id TEXT PRIMARY KEY,
    declared_production_cost REAL NOT NULL,
    declared_verification_cost REAL NOT NULL,
    reserved REAL NOT NULL,
    spent_at TEXT,
    released_at TEXT,
    ceiling_multiplier REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS grade_history (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    node_hash TEXT NOT NULL,
    from_grade TEXT NOT NULL CHECK (from_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    to_grade TEXT NOT NULL CHECK (to_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    reason TEXT,
    at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS attempts_by_recipe ON attempts (recipe_key, status);
CREATE INDEX IF NOT EXISTS lineage_by_parent ON lineage (parent_hash, edge_kind);
CREATE INDEX IF NOT EXISTS grade_history_by_node ON grade_history (node_hash, seq);

CREATE TRIGGER IF NOT EXISTS nodes_no_update BEFORE UPDATE ON nodes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS nodes_no_delete BEFORE DELETE ON nodes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS recipes_no_update BEFORE UPDATE ON recipes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS recipes_no_delete BEFORE DELETE ON recipes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS receipts_no_update BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS receipts_no_delete BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS lineage_no_update BEFORE UPDATE ON lineage BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS lineage_no_delete BEFORE DELETE ON lineage BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS roots_no_update BEFORE UPDATE ON roots BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS roots_no_delete BEFORE DELETE ON roots BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS skill_certificates_no_update BEFORE UPDATE ON skill_certificates BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS skill_certificates_no_delete BEFORE DELETE ON skill_certificates BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS yank_records_no_update BEFORE UPDATE ON yank_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS yank_records_no_delete BEFORE DELETE ON yank_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS salts_no_update BEFORE UPDATE ON salts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS salts_no_delete BEFORE DELETE ON salts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS grade_history_no_update BEFORE UPDATE ON grade_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS grade_history_no_delete BEFORE DELETE ON grade_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS attempts_no_delete BEFORE DELETE ON attempts BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS attempts_append_only BEFORE UPDATE ON attempts
WHEN NOT (
    (
        OLD.status = 'RUNNING' AND OLD.ended_at IS NULL
        AND NEW.status IN ('OK', 'FAIL', 'DISAGREE', 'BUDGET_EXCEEDED', 'SKILL_YANKED', 'INTERRUPTED')
        AND NEW.ended_at IS NOT NULL
        AND NEW.attempt_id IS OLD.attempt_id
        AND NEW.recipe_key IS OLD.recipe_key
        AND NEW.replay_grade IS OLD.replay_grade
        AND NEW.skip_cache_lookup IS OLD.skip_cache_lookup
        AND NEW.disowned_at IS OLD.disowned_at
        AND NEW.inadmissible IS OLD.inadmissible
        AND NEW.started_at IS OLD.started_at
    )
    OR (
        OLD.disowned_at IS NULL AND NEW.disowned_at IS NOT NULL
        AND NEW.attempt_id IS OLD.attempt_id
        AND NEW.recipe_key IS OLD.recipe_key
        AND NEW.output_manifest_hash IS OLD.output_manifest_hash
        AND NEW.receipt_hash IS OLD.receipt_hash
        AND NEW.status IS OLD.status
        AND NEW.replay_grade IS OLD.replay_grade
        AND NEW.verifier_result_hash IS OLD.verifier_result_hash
        AND NEW.certificate_hash IS OLD.certificate_hash
        AND NEW.skip_cache_lookup IS OLD.skip_cache_lookup
        AND NEW.inadmissible IS OLD.inadmissible
        AND NEW.started_at IS OLD.started_at
        AND NEW.ended_at IS OLD.ended_at
    )
    OR (
        OLD.inadmissible = 0 AND NEW.inadmissible = 1
        AND NEW.attempt_id IS OLD.attempt_id
        AND NEW.recipe_key IS OLD.recipe_key
        AND NEW.output_manifest_hash IS OLD.output_manifest_hash
        AND NEW.receipt_hash IS OLD.receipt_hash
        AND NEW.status IS OLD.status
        AND NEW.replay_grade IS OLD.replay_grade
        AND NEW.verifier_result_hash IS OLD.verifier_result_hash
        AND NEW.certificate_hash IS OLD.certificate_hash
        AND NEW.skip_cache_lookup IS OLD.skip_cache_lookup
        AND NEW.disowned_at IS OLD.disowned_at
        AND NEW.started_at IS OLD.started_at
        AND NEW.ended_at IS OLD.ended_at
    )
)
BEGIN SELECT RAISE(ABORT, 'append-only'); END;
