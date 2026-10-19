CREATE TABLE IF NOT EXISTS acknowledgments (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL,
    issued_by TEXT NOT NULL,
    at TEXT NOT NULL,
    note TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS ledger_entries_by_key ON ledger_entries (hypothesis_key);
CREATE INDEX IF NOT EXISTS human_queue_closures_by_item ON human_queue_closures (item_id, seq);
CREATE INDEX IF NOT EXISTS acknowledgments_by_item ON acknowledgments (item_id);

CREATE TRIGGER IF NOT EXISTS ledger_entries_no_update BEFORE UPDATE ON ledger_entries BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ledger_entries_no_delete BEFORE DELETE ON ledger_entries BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS human_queue_items_no_update BEFORE UPDATE ON human_queue_items BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS human_queue_items_no_delete BEFORE DELETE ON human_queue_items BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS human_queue_closures_no_update BEFORE UPDATE ON human_queue_closures BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS human_queue_closures_no_delete BEFORE DELETE ON human_queue_closures BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS acknowledgments_no_update BEFORE UPDATE ON acknowledgments BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS acknowledgments_no_delete BEFORE DELETE ON acknowledgments BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS human_queue_closing_rule BEFORE INSERT ON human_queue_closures
WHEN (NEW.path = 'blocker_cleared' AND (SELECT blocker FROM human_queue_items WHERE item_id = NEW.item_id) IS NULL)
  OR (NEW.path IN ('terminal_status', 'acknowledgment') AND (SELECT blocker FROM human_queue_items WHERE item_id = NEW.item_id) IS NOT NULL)
  OR (NEW.path = 'terminal_status'
      AND (SELECT target_kind FROM human_queue_items WHERE item_id = NEW.item_id) = 'statement'
      AND COALESCE((SELECT status FROM claim_statements WHERE hash = (SELECT target FROM human_queue_items WHERE item_id = NEW.item_id)), 'open') = 'open')
BEGIN SELECT RAISE(ABORT, 'closing rule'); END;

CREATE TRIGGER IF NOT EXISTS human_queue_blocker_clearing_rule BEFORE INSERT ON human_queue_closures
WHEN NEW.path = 'blocker_cleared'
  AND (SELECT blocker FROM human_queue_items WHERE item_id = NEW.item_id) IS NOT NULL
  AND (((SELECT blocker FROM human_queue_items WHERE item_id = NEW.item_id) IN ('null_control_pending', 'already_settled'))
       IS NOT (NEW.record_digest IS NULL))
BEGIN SELECT RAISE(ABORT, 'blocker clearing rule'); END;

CREATE TABLE IF NOT EXISTS nogo_declarations (
    hypothesis_key TEXT NOT NULL,
    declaration_hash TEXT NOT NULL,
    declared_by TEXT NOT NULL,
    at TEXT NOT NULL,
    PRIMARY KEY (hypothesis_key, declaration_hash)
);

CREATE TABLE IF NOT EXISTS nogo_reviews (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_key TEXT NOT NULL,
    declaration_hash TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('accept_for_tiering', 'reject', 'needs_revision')),
    gate_bundle_hash TEXT NOT NULL,
    at TEXT NOT NULL,
    supersedes TEXT,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS nogo_declarations_by_key ON nogo_declarations (hypothesis_key);
CREATE INDEX IF NOT EXISTS nogo_reviews_by_key ON nogo_reviews (hypothesis_key);

CREATE TRIGGER IF NOT EXISTS nogo_declarations_no_update BEFORE UPDATE ON nogo_declarations BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS nogo_declarations_no_delete BEFORE DELETE ON nogo_declarations BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS nogo_reviews_no_update BEFORE UPDATE ON nogo_reviews BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS nogo_reviews_no_delete BEFORE DELETE ON nogo_reviews BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS escrow_settle_once BEFORE UPDATE ON escrow
WHEN NOT (
    OLD.spent_at IS NULL AND OLD.released_at IS NULL
    AND NEW.attempt_id IS OLD.attempt_id
    AND NEW.declared_production_cost IS OLD.declared_production_cost
    AND NEW.declared_verification_cost IS OLD.declared_verification_cost
    AND NEW.reserved IS OLD.reserved
    AND NEW.ceiling_multiplier IS OLD.ceiling_multiplier
    AND (
        (NEW.spent_at IS NOT NULL AND NEW.spent_by IS NOT NULL AND NEW.released_at IS NULL AND NEW.released_by IS NULL)
        OR (NEW.released_at IS NOT NULL AND NEW.released_by IS NOT NULL AND NEW.spent_at IS NULL AND NEW.spent_by IS NULL)
    )
)
BEGIN SELECT RAISE(ABORT, 'escrow settles once: spent or released, never both, never twice'); END;
CREATE TRIGGER IF NOT EXISTS escrow_no_delete BEFORE DELETE ON escrow BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS expert_signoffs (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_hash TEXT NOT NULL,
    expert TEXT NOT NULL,
    gate_bundle_hash TEXT NOT NULL,
    at TEXT NOT NULL,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS scrutiny_requests (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_key TEXT NOT NULL,
    requested_class TEXT NOT NULL CHECK (requested_class IN ('routine', 'elevated', 'top')),
    assigned_class TEXT NOT NULL CHECK (assigned_class IN ('routine', 'elevated', 'top')),
    requested_by TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS expert_signoffs_by_statement ON expert_signoffs (statement_hash);
CREATE INDEX IF NOT EXISTS scrutiny_requests_by_key ON scrutiny_requests (hypothesis_key);

CREATE TRIGGER IF NOT EXISTS expert_signoffs_no_update BEFORE UPDATE ON expert_signoffs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS expert_signoffs_no_delete BEFORE DELETE ON expert_signoffs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS scrutiny_requests_no_update BEFORE UPDATE ON scrutiny_requests BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS scrutiny_requests_no_delete BEFORE DELETE ON scrutiny_requests BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS worker_dispatches (
    dispatch_id TEXT PRIMARY KEY,
    record_hash TEXT NOT NULL UNIQUE REFERENCES nodes(hash),
    record_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS worker_results (
    dispatch_id TEXT PRIMARY KEY REFERENCES worker_dispatches(dispatch_id),
    record_hash TEXT NOT NULL UNIQUE REFERENCES nodes(hash),
    record_json TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS worker_dispatches_no_update BEFORE UPDATE ON worker_dispatches BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS worker_dispatches_no_delete BEFORE DELETE ON worker_dispatches BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS worker_results_no_update BEFORE UPDATE ON worker_results BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS worker_results_no_delete BEFORE DELETE ON worker_results BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS dispatch_canaries (
    canary_id TEXT PRIMARY KEY,
    record_hash TEXT NOT NULL UNIQUE REFERENCES nodes(hash),
    sdk_version TEXT NOT NULL,
    cli_version TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('pass', 'fail')),
    record_json TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS dispatch_canaries_no_update BEFORE UPDATE ON dispatch_canaries BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS dispatch_canaries_no_delete BEFORE DELETE ON dispatch_canaries BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS ladder_tables (
    hash TEXT PRIMARY KEY,
    run_id TEXT NOT NULL UNIQUE,
    nonce TEXT NOT NULL,
    hypothesis_hash TEXT NOT NULL,
    method_identity TEXT NOT NULL,
    implementation_revision TEXT NOT NULL,
    gate_bundle_hash TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    uncounted_backend TEXT,
    attempt_id TEXT,
    verdict TEXT NOT NULL CHECK (verdict IN ('KEEP', 'KEEP_IN_SAMPLE', 'REJECT', 'INCONCLUSIVE')),
    verdict_predicate TEXT NOT NULL,
    refutation_kind TEXT CHECK (refutation_kind IS NULL OR refutation_kind IN ('measured', 'implementation')),
    verdict_rung INTEGER,
    replay_grade TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ladder_rungs (
    table_hash TEXT NOT NULL REFERENCES ladder_tables (hash),
    bits INTEGER NOT NULL,
    role TEXT NOT NULL,
    trials INTEGER NOT NULL,
    ops_kind TEXT NOT NULL CHECK (ops_kind IN ('exact', 'lower_bound', 'unknown')),
    mean_ops TEXT,
    sd_ops TEXT,
    cpu_seconds TEXT NOT NULL,
    reference_rate TEXT NOT NULL,
    memory_bytes INTEGER NOT NULL,
    success_rate TEXT NOT NULL,
    radius TEXT NOT NULL,
    claim_ci_low TEXT,
    claim_ci_high TEXT,
    model_prediction TEXT NOT NULL,
    model_band TEXT NOT NULL,
    shape_statistic TEXT,
    declared_shape TEXT NOT NULL,
    PRIMARY KEY (table_hash, bits)
);

CREATE TABLE IF NOT EXISTS ladder_trials (
    table_hash TEXT NOT NULL REFERENCES ladder_tables (hash),
    arm TEXT NOT NULL,
    bits INTEGER NOT NULL,
    trial INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    instance_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    output_complete INTEGER NOT NULL,
    recovered INTEGER NOT NULL,
    gate_ops_kind TEXT NOT NULL CHECK (gate_ops_kind IN ('exact', 'lower_bound', 'unknown')),
    gate_ops INTEGER,
    reported_ops INTEGER,
    cpu_seconds TEXT NOT NULL,
    wall_seconds TEXT NOT NULL,
    peak_rss_bytes INTEGER NOT NULL,
    scratch_bytes INTEGER NOT NULL,
    reported_memory_bytes INTEGER NOT NULL,
    replay_grade TEXT NOT NULL,
    measurement_scope TEXT NOT NULL,
    witness_hash TEXT,
    PRIMARY KEY (table_hash, arm, bits, trial)
);

CREATE INDEX IF NOT EXISTS ladder_tables_by_hypothesis ON ladder_tables (hypothesis_hash);

CREATE TRIGGER IF NOT EXISTS ladder_tables_no_update BEFORE UPDATE ON ladder_tables BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_tables_no_delete BEFORE DELETE ON ladder_tables BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_rungs_no_update BEFORE UPDATE ON ladder_rungs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_rungs_no_delete BEFORE DELETE ON ladder_rungs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_trials_no_update BEFORE UPDATE ON ladder_trials BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_trials_no_delete BEFORE DELETE ON ladder_trials BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS disagreements (
    disagreement_id TEXT PRIMARY KEY,
    statement_hash TEXT NOT NULL,
    left_hash TEXT NOT NULL,
    right_hash TEXT NOT NULL,
    classification TEXT NOT NULL,
    owner TEXT NOT NULL,
    frozen_tag TEXT NOT NULL,
    item_id TEXT NOT NULL,
    raised_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS disagreements_by_statement ON disagreements (statement_hash, raised_at);
CREATE TRIGGER IF NOT EXISTS disagreements_no_update BEFORE UPDATE ON disagreements BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS disagreements_no_delete BEFORE DELETE ON disagreements BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS ladder_dispatches (
    dispatch_id TEXT PRIMARY KEY,
    record_hash TEXT NOT NULL UNIQUE REFERENCES nodes(hash),
    run_id TEXT NOT NULL,
    arm TEXT NOT NULL,
    nonce TEXT NOT NULL,
    hypothesis_hash TEXT NOT NULL,
    implementation_revision TEXT NOT NULL,
    allow_list_hash TEXT NOT NULL,
    gate_bundle_hash TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    record_json TEXT NOT NULL,
    UNIQUE (run_id, arm)
);
CREATE TRIGGER IF NOT EXISTS ladder_dispatches_no_update BEFORE UPDATE ON ladder_dispatches BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS ladder_dispatches_no_delete BEFORE DELETE ON ladder_dispatches BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TABLE IF NOT EXISTS human_authority_records (
    kind TEXT NOT NULL CHECK (kind IN ('operator_session', 'statement_ratification', 'yank_ruling', 'salt_issuance')),
    canonical BLOB NOT NULL,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL CHECK (file_offset >= 0),
    producer_identity TEXT NOT NULL,
    PRIMARY KEY (record_digest, file_offset)
);

CREATE TRIGGER IF NOT EXISTS human_authority_records_no_update BEFORE UPDATE ON human_authority_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS human_authority_records_no_delete BEFORE DELETE ON human_authority_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
