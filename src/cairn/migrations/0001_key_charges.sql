CREATE TABLE IF NOT EXISTS key_charges (
    charge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    hypothesis_key TEXT NOT NULL,
    ticket_tier INTEGER,
    origin TEXT NOT NULL CHECK (origin IN ('worker', 'gate-owned', 'recorded-rerun')),
    declared_core_s REAL NOT NULL CHECK (declared_core_s >= 0),
    attempt_id TEXT UNIQUE,
    measured_core_s REAL CHECK (measured_core_s IS NULL OR measured_core_s >= 0),
    accrued_at TEXT NOT NULL,
    reconciled_at TEXT,
    CHECK ((measured_core_s IS NULL) = (reconciled_at IS NULL))
);
CREATE INDEX IF NOT EXISTS key_charges_by_key ON key_charges (hypothesis_key, ticket_tier, origin);
CREATE TRIGGER IF NOT EXISTS key_charges_bind_reconcile_once BEFORE UPDATE ON key_charges
WHEN NOT (
    NEW.charge_id IS OLD.charge_id
    AND NEW.hypothesis_key IS OLD.hypothesis_key
    AND NEW.ticket_tier IS OLD.ticket_tier
    AND NEW.origin IS OLD.origin
    AND NEW.declared_core_s IS OLD.declared_core_s
    AND NEW.accrued_at IS OLD.accrued_at
    AND (
        (OLD.attempt_id IS NULL AND NEW.attempt_id IS NOT NULL
            AND NEW.measured_core_s IS OLD.measured_core_s AND NEW.reconciled_at IS OLD.reconciled_at)
        OR (OLD.measured_core_s IS NULL AND NEW.measured_core_s IS NOT NULL
            AND NEW.attempt_id IS OLD.attempt_id)
    )
)
BEGIN SELECT RAISE(ABORT, 'a charge binds to one attempt once and reconciles once'); END;
CREATE TRIGGER IF NOT EXISTS key_charges_no_delete BEFORE DELETE ON key_charges BEGIN SELECT RAISE(ABORT, 'append-only'); END;
