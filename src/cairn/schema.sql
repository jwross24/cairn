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
    status TEXT NOT NULL CHECK (status IN ('RUNNING', 'OK', 'FAIL', 'DISAGREE', 'BUDGET_EXCEEDED', 'BLOCKED', 'SKILL_YANKED', 'INTERRUPTED')),
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
    kind TEXT NOT NULL CHECK (kind IN ('gate_verdict', 'human_path')),
    verdict_ref TEXT,
    ruling_ref TEXT,
    record_digest TEXT,
    file_offset INTEGER,
    created_at TEXT NOT NULL,
    CHECK ((kind = 'gate_verdict') = (verdict_ref IS NOT NULL AND ruling_ref IS NULL AND record_digest IS NULL AND file_offset IS NULL)),
    CHECK ((kind = 'human_path') = (verdict_ref IS NULL AND ruling_ref IS NOT NULL AND record_digest IS NOT NULL AND file_offset IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS salts (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    class_key TEXT NOT NULL,
    salt TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('gate_verdict', 'human_path')),
    verdict_ref TEXT,
    record_digest TEXT,
    file_offset INTEGER,
    UNIQUE (class_key, salt),
    CHECK ((kind = 'gate_verdict') = (verdict_ref IS NOT NULL AND record_digest IS NULL AND file_offset IS NULL)),
    CHECK ((kind = 'human_path') = (verdict_ref IS NULL AND record_digest IS NOT NULL AND file_offset IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS escrow (
    attempt_id TEXT PRIMARY KEY,
    declared_production_cost REAL NOT NULL,
    declared_verification_cost REAL NOT NULL,
    reserved REAL NOT NULL,
    spent_at TEXT,
    spent_by TEXT,
    released_at TEXT,
    released_by TEXT,
    ceiling_multiplier REAL NOT NULL,
    CHECK ((spent_at IS NULL) = (spent_by IS NULL)),
    CHECK ((released_at IS NULL) = (released_by IS NULL)),
    CHECK (spent_at IS NULL OR released_at IS NULL)
);

CREATE TABLE IF NOT EXISTS grade_history (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    node_hash TEXT NOT NULL,
    from_grade TEXT NOT NULL CHECK (from_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    to_grade TEXT NOT NULL CHECK (to_grade IN ('Replayable', 'Verifiable', 'AuditOnly')),
    reason TEXT,
    at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gc_runs (
    run_id TEXT PRIMARY KEY,
    dry_run INTEGER NOT NULL,
    roots INTEGER NOT NULL,
    reachable INTEGER NOT NULL,
    candidates INTEGER NOT NULL,
    count INTEGER NOT NULL,
    bytes INTEGER NOT NULL,
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
CREATE TRIGGER IF NOT EXISTS gc_runs_no_update BEFORE UPDATE ON gc_runs BEGIN SELECT RAISE(ABORT, 'append-only'); END;
CREATE TRIGGER IF NOT EXISTS gc_runs_no_delete BEFORE DELETE ON gc_runs BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS attempts_no_delete BEFORE DELETE ON attempts BEGIN SELECT RAISE(ABORT, 'append-only'); END;

CREATE TRIGGER IF NOT EXISTS attempts_append_only BEFORE UPDATE ON attempts
WHEN NOT (
    (
        OLD.status = 'RUNNING' AND OLD.ended_at IS NULL
        AND NEW.status IN ('OK', 'FAIL', 'DISAGREE', 'BUDGET_EXCEEDED', 'BLOCKED', 'SKILL_YANKED', 'INTERRUPTED')
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
    gate TEXT NOT NULL CHECK (gate IN ('canon_kat', 'verifier', 'tier_gate', 'self_test', 'gate_plan', 'bundle_open', 'ladder_plan', 'challenge_render')),
    bundle_hash TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    plan_step TEXT,
    instance_hash TEXT,
    statement_hash TEXT,
    formal_statement_hash TEXT,
    renderer_hash TEXT,
    prelude_hash TEXT,
    arm TEXT CHECK (arm IS NULL OR arm IN ('dev-macos-fake-landrun', 'gold-linux-container')),
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
    CHECK ((path IN ('attestation', 'acknowledgment')) = (record_digest IS NOT NULL AND file_offset IS NOT NULL))
);

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
    mean_ops TEXT NOT NULL,
    sd_ops TEXT NOT NULL,
    cpu_seconds TEXT NOT NULL,
    reference_rate TEXT NOT NULL,
    memory_bytes INTEGER NOT NULL,
    success_rate TEXT NOT NULL,
    radius TEXT NOT NULL,
    claim_ci_low TEXT,
    claim_ci_high TEXT,
    model_prediction TEXT NOT NULL,
    model_band TEXT NOT NULL,
    shape_statistic TEXT NOT NULL,
    declared_shape TEXT NOT NULL,
    PRIMARY KEY (table_hash, bits)
);

CREATE TABLE IF NOT EXISTS ladder_trials (
    table_hash TEXT NOT NULL REFERENCES ladder_tables (hash),
    bits INTEGER NOT NULL,
    trial INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    instance_hash TEXT NOT NULL,
    recovered INTEGER NOT NULL,
    completed INTEGER NOT NULL,
    gate_ops INTEGER NOT NULL,
    reported_ops INTEGER NOT NULL,
    cpu_seconds TEXT NOT NULL,
    wall_seconds TEXT NOT NULL,
    peak_rss_bytes INTEGER NOT NULL,
    scratch_bytes INTEGER NOT NULL,
    reported_memory_bytes INTEGER NOT NULL,
    replay_grade TEXT NOT NULL,
    witness_hash TEXT,
    PRIMARY KEY (table_hash, bits, trial)
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
