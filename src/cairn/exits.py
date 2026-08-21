OK = 0
USER_INPUT = 1
GATE_REFUSED = 2
ENVIRONMENT = 3
BACKEND = 4
CONFLICT = 5

CLI = {
    OK: "OK",
    USER_INPUT: "USER_INPUT: bad arguments, malformed input, unknown id; the error names the exact command to run",
    GATE_REFUSED: "GATE_REFUSED: a gate or safety gate refused, or a self-test failed (fail closed): KAT mismatch, bundle hash differs from the pin, TierRefused, a verifier FAIL inside a gate run, a dangerous operation invoked without its --yes/--force; state untouched",
    ENVIRONMENT: "ENVIRONMENT: a required binary, stack, file or database is missing or wrongly shaped (gp absent, PARI stack, bundle/pin/attestation file, substrate, EPERM on a flagged file)",
    BACKEND: "BACKEND: a subprocess the command needed died, timed out or returned malformed output outside any gate's classification, or an unexpected exception",
    CONFLICT: "CONFLICT: a second writer holds the substrate (database is locked after the busy timeout)",
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
