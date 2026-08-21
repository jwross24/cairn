OK = 0
USER_INPUT = 1
GATE_REFUSED = 2
ENVIRONMENT = 3
BACKEND = 4
CONFLICT = 5

CLI = {
    OK: "OK",
    USER_INPUT: "USER_INPUT: bad arguments, malformed input, unknown id; the error names the exact command to run",
    GATE_REFUSED: "GATE_REFUSED: a gate refused or a self-test failed (fail closed): KAT mismatch, bundle hash differs from the pin, TierRefused, verifier FAIL inside a gate run",
    ENVIRONMENT: "ENVIRONMENT: a required binary, stack, file or database is missing or wrongly shaped (gp absent, PARI stack, bundle/pin/attestation file, substrate)",
    BACKEND: "BACKEND: gp or a skill subprocess crashed, timed out, or returned malformed output",
    CONFLICT: "CONFLICT: the single-writer lock is held by another process",
}

DOCTOR_HEALTHY = 0
DOCTOR_FINDINGS = 1
DOCTOR_PARTIAL = 2
DOCTOR_ROLLED_BACK = 3
DOCTOR_REFUSED = 4
DOCTOR_CONCURRENCY = 5
DOCTOR_USAGE = 64

DOCTOR = {
    DOCTOR_HEALTHY: "healthy",
    DOCTOR_FINDINGS: "findings present, no --fix requested",
    DOCTOR_PARTIAL: "fix attempted, partial",
    DOCTOR_ROLLED_BACK: "fix failed and rolled back",
    DOCTOR_REFUSED: "refused unsafe",
    DOCTOR_CONCURRENCY: "concurrency lost (lock held)",
    DOCTOR_USAGE: "usage error",
}
