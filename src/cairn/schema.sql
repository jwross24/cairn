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
    gate TEXT NOT NULL CHECK (gate IN ('canon_kat', 'verifier', 'tier_gate', 'self_test', 'gate_plan', 'bundle_open')),
    bundle_hash TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    plan_step TEXT,
    instance_hash TEXT,
    statement_hash TEXT,
    result TEXT NOT NULL CHECK (result IN ('pass', 'fail', 'refused', 'blocked', 'admitted')),
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

CREATE INDEX IF NOT EXISTS evidence_by_statement ON evidence_nodes (target_statement_hash);
CREATE INDEX IF NOT EXISTS tag_history_by_statement ON tag_history (statement_hash, seq);
CREATE INDEX IF NOT EXISTS review_verdicts_by_statement ON review_verdicts (statement_hash);
CREATE INDEX IF NOT EXISTS tickets_by_key ON tickets (hypothesis_key, method_identity);
CREATE INDEX IF NOT EXISTS tier_refusals_by_key ON tier_refusals (hypothesis_key);

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

CREATE TRIGGER IF NOT EXISTS claim_statements_born_open BEFORE INSERT ON claim_statements
WHEN NEW.status <> 'open'
BEGIN SELECT RAISE(ABORT, 'claim statement is born open'); END;
