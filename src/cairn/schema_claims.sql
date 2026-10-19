CREATE TABLE IF NOT EXISTS hypothesis_objects (
    hash TEXT PRIMARY KEY,
    canonical BLOB NOT NULL,
    claim_statement_hash TEXT,
    supersedes TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_statements (
    hash TEXT PRIMARY KEY,
    claim_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    informal TEXT NOT NULL,
    formal_source TEXT,
    scope TEXT NOT NULL,
    quantities TEXT NOT NULL,
    source_claim_hash TEXT,
    supersedes TEXT,
    status TEXT NOT NULL CHECK (status IN ('open', 'refuted', 'promoted', 'withdrawn')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_nodes (
    hash TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('lean_artifact', 'ladder_table', 'repro_node', 'counterexample_hunt_record', 'statistical', 'model_proof')),
    target_statement_hash TEXT NOT NULL,
    population TEXT NOT NULL,
    assumptions TEXT NOT NULL,
    producer_identity TEXT NOT NULL,
    producer_tag TEXT NOT NULL,
    verdict TEXT CHECK (verdict IS NULL OR verdict IN ('KEEP', 'KEEP_IN_SAMPLE', 'REJECT', 'INCONCLUSIVE', 'SURVIVED', 'KILLED', 'INCOMPLETE')),
    in_sample_sizes TEXT,
    attempt_id TEXT,
    repro_record_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS repro_records (
    hash TEXT PRIMARY KEY,
    attempt_id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('second_attempt_agree', 'witness_check')),
    passed INTEGER NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tag_history (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_hash TEXT NOT NULL,
    from_tag TEXT CHECK (from_tag IS NULL OR from_tag IN ('SPECULATION', 'CONJECTURE', 'STRONG-EMPIRICAL', 'PROVEN')),
    to_tag TEXT NOT NULL CHECK (to_tag IN ('SPECULATION', 'CONJECTURE', 'STRONG-EMPIRICAL', 'PROVEN')),
    evidence_hash TEXT,
    justification TEXT NOT NULL,
    actor TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS review_verdicts (
    row_id INTEGER PRIMARY KEY AUTOINCREMENT,
    statement_hash TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('approve', 'reject', 'needs_revision')),
    checklist_template_hash TEXT NOT NULL,
    gate_bundle_hash TEXT NOT NULL,
    at TEXT NOT NULL,
    supersedes TEXT,
    record_digest TEXT NOT NULL,
    file_offset INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS gate_runs (
    run_id TEXT PRIMARY KEY,
    gate TEXT NOT NULL CHECK (gate IN ('canon_kat', 'verifier', 'tier_gate', 'self_test', 'gate_plan', 'bundle_open', 'ladder_plan', 'challenge_render', 'solution_plan_step')),
    bundle_hash TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    plan_step TEXT,
    instance_hash TEXT,
    statement_hash TEXT,
    formal_statement_hash TEXT,
    renderer_hash TEXT,
    prelude_hash TEXT,
    arm TEXT CHECK (arm IS NULL OR arm IN ('dev-macos-fake-landrun', 'gold-linux-container')),
    result TEXT NOT NULL CHECK (result IN ('pass', 'fail', 'refused', 'blocked', 'admitted', 'timeout')),
    reasons TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tickets (
    ticket_hash TEXT PRIMARY KEY,
    hypothesis_key TEXT NOT NULL,
    method_identity TEXT NOT NULL,
    statement_hash TEXT,
    tier INTEGER NOT NULL,
    kind TEXT NOT NULL,
    node_hash TEXT NOT NULL,
    bundle_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tier_refusals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_key TEXT NOT NULL,
    declared_tier INTEGER NOT NULL,
    ticket_tier INTEGER,
    reason TEXT NOT NULL,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS instance_nonces (
    nonce TEXT PRIMARY KEY,
    hypothesis_key TEXT NOT NULL,
    run_id TEXT NOT NULL UNIQUE,
    drawn_at TEXT NOT NULL,
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS instance_trials (
    nonce TEXT NOT NULL REFERENCES instance_nonces (nonce),
    bits INTEGER NOT NULL,
    trial INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    instance_hash TEXT NOT NULL,
    x TEXT NOT NULL,
    attempt_id TEXT,
    PRIMARY KEY (nonce, bits, trial)
);

CREATE INDEX IF NOT EXISTS evidence_by_statement ON evidence_nodes (target_statement_hash);
CREATE INDEX IF NOT EXISTS tag_history_by_statement ON tag_history (statement_hash, seq);
CREATE INDEX IF NOT EXISTS review_verdicts_by_statement ON review_verdicts (statement_hash);
CREATE INDEX IF NOT EXISTS tickets_by_key ON tickets (hypothesis_key, method_identity);
CREATE INDEX IF NOT EXISTS tier_refusals_by_key ON tier_refusals (hypothesis_key);
CREATE INDEX IF NOT EXISTS instance_nonces_by_key ON instance_nonces (hypothesis_key);

CREATE TRIGGER IF NOT EXISTS hypothesis_objects_no_update BEFORE UPDATE ON hypothesis_objects BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS hypothesis_objects_no_delete BEFORE DELETE ON hypothesis_objects BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_nodes_no_update BEFORE UPDATE ON evidence_nodes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS evidence_nodes_no_delete BEFORE DELETE ON evidence_nodes BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS repro_records_no_update BEFORE UPDATE ON repro_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS repro_records_no_delete BEFORE DELETE ON repro_records BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tag_history_no_update BEFORE UPDATE ON tag_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tag_history_no_delete BEFORE DELETE ON tag_history BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_verdicts_no_update BEFORE UPDATE ON review_verdicts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS review_verdicts_no_delete BEFORE DELETE ON review_verdicts BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS gate_runs_no_update BEFORE UPDATE ON gate_runs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS gate_runs_no_delete BEFORE DELETE ON gate_runs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tickets_no_update BEFORE UPDATE ON tickets BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tickets_no_delete BEFORE DELETE ON tickets BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tier_refusals_no_update BEFORE UPDATE ON tier_refusals BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS tier_refusals_no_delete BEFORE DELETE ON tier_refusals BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS claim_statements_no_delete BEFORE DELETE ON claim_statements BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS claim_statements_one_transition BEFORE UPDATE ON claim_statements
WHEN NOT (
    OLD.status = 'open' AND NEW.status IN ('refuted', 'promoted', 'withdrawn')
    AND NEW.hash IS OLD.hash
    AND NEW.claim_id IS OLD.claim_id
    AND NEW.version IS OLD.version
    AND NEW.informal IS OLD.informal
    AND NEW.formal_source IS OLD.formal_source
    AND NEW.scope IS OLD.scope
    AND NEW.quantities IS OLD.quantities
    AND NEW.source_claim_hash IS OLD.source_claim_hash
    AND NEW.supersedes IS OLD.supersedes
    AND NEW.created_at IS OLD.created_at
)
BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS tag_history_downgrade_needs_evidence BEFORE INSERT ON tag_history
WHEN NEW.from_tag IS NOT NULL AND NEW.evidence_hash IS NULL
AND (CASE NEW.to_tag WHEN 'SPECULATION' THEN 0 WHEN 'CONJECTURE' THEN 1 WHEN 'STRONG-EMPIRICAL' THEN 2 WHEN 'PROVEN' THEN 3 END)
  < (CASE NEW.from_tag WHEN 'SPECULATION' THEN 0 WHEN 'CONJECTURE' THEN 1 WHEN 'STRONG-EMPIRICAL' THEN 2 WHEN 'PROVEN' THEN 3 END)
BEGIN SELECT RAISE(ABORT, 'downgrade requires evidence'); END;

CREATE TRIGGER IF NOT EXISTS instance_nonces_no_delete BEFORE DELETE ON instance_nonces BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS instance_trials_no_delete BEFORE DELETE ON instance_trials BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS instance_trials_no_update BEFORE UPDATE ON instance_trials BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS instance_nonces_one_publication BEFORE UPDATE ON instance_nonces
WHEN NOT (
    OLD.published_at IS NULL AND NEW.published_at IS NOT NULL
    AND NEW.nonce IS OLD.nonce
    AND NEW.hypothesis_key IS OLD.hypothesis_key
    AND NEW.run_id IS OLD.run_id
    AND NEW.drawn_at IS OLD.drawn_at
)
BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS claim_statements_born_open BEFORE INSERT ON claim_statements
WHEN NEW.status <> 'open'
BEGIN SELECT RAISE(ABORT, 'claim statement is born open'); END;

CREATE TABLE IF NOT EXISTS ledger_entries (
    hash TEXT PRIMARY KEY,
    hypothesis_key TEXT NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('REFUTED', 'PARKED')),
    refutation_kind TEXT CHECK (refutation_kind IS NULL OR refutation_kind IN ('formal', 'measured', 'implementation')),
    evidence_node TEXT NOT NULL,
    method TEXT NOT NULL,
    measured_points TEXT NOT NULL,
    result TEXT,
    retry_predicate TEXT,
    caught_by TEXT NOT NULL,
    blocker TEXT,
    faulting_revision TEXT,
    created_at TEXT NOT NULL,
    CHECK ((decision = 'REFUTED') = (refutation_kind IS NOT NULL)),
    CHECK ((decision = 'PARKED') = (blocker IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS human_queue_items (
    item_id TEXT PRIMARY KEY,
    class TEXT NOT NULL CHECK (class IN ('statement_review', 'nogo_review', 'waiver_request', 'yank_ruling', 'revision_admission', 'expert_signoff', 'disagreement', 'near_dup_review', 'supersedes_refuted_review', 'null_control_pending', 'clock_inconclusive', 'shape_departure', 'leaked', 'cost_drift', 'audit_shortfall')),
    target_kind TEXT NOT NULL CHECK (target_kind IN ('statement', 'branch', 'rung', 'audit_cycle')),
    target TEXT NOT NULL,
    blocker TEXT,
    enqueued_at TEXT NOT NULL,
    CHECK ((class IN ('leaked', 'clock_inconclusive', 'shape_departure', 'cost_drift', 'audit_shortfall')) = (blocker IS NULL))
);

CREATE TABLE IF NOT EXISTS human_queue_closures (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL REFERENCES human_queue_items (item_id),
    path TEXT NOT NULL CHECK (path IN ('attestation', 'blocker_cleared', 'terminal_status', 'acknowledgment')),
    ref TEXT NOT NULL,
    record_digest TEXT,
    file_offset INTEGER,
    closed_at TEXT NOT NULL,
    CHECK (CASE
        WHEN path IN ('attestation', 'acknowledgment') THEN record_digest IS NOT NULL AND file_offset IS NOT NULL
        WHEN path = 'terminal_status' THEN record_digest IS NULL AND file_offset IS NULL
        ELSE (record_digest IS NULL) = (file_offset IS NULL)
    END)
);

