# ADR-017: CI reports the check gate

## Status

Accepted by owner decision, 2026-11-23: option (a) of `cairn-5auq`.

## Context

`.beads/policy.yaml` requires a passing `check` gate for `in_progress -> closed`. Its only reporter was `scripts/check.sh --bead <id>`, which refuses unless the run is the complete unscoped all-lane gate. That run needs Docker and took about 27 minutes on 2026-09-19 (`.check.log`, 15:48 to 16:15). AGENTS.md says a full local run is not an automatic prerequisite to a close, so an agent closing a bead either made a run the docs call non-routine or could not close. Four gate reports exist in `.check.log`; the nightly retro of 2026-11-21 found a session rerunning the full gate for two beads.

CI already runs every lane on each pushed commit: one `check (<lane>)` job per lane in `tests/_ci_lanes.py` `CI_LANES`.

## Decision

The `check` gate for a bead is recorded from CI's run on the pushed commit that closes it. `scripts/check.sh --from-ci --bead <id>` dispatches to `scripts/ci_gate.py`, which records a pass with provider `ci` only when all of these hold:

- the bead is `in_progress`;
- HEAD is on a remote branch;
- a completed push run of `ci.yml` for that exact commit concluded `success`;
- every lane the `lane:` matrix in `.github/workflows/ci.yml` declares as of that commit has a `check (<lane>)` job that concluded `success`. The matrix is read as data, never executed; `tests/unit/test_ci_gate.py` holds it equal to `tests/_ci_lanes.py` `CI_LANES`, and that test runs in the run being read.

Anything less records nothing and logs a `DENY gate-report` line with its reason to `.check.log`. A failure of git, gh or br is its own exit code, never a pass.

The full local `scripts/check.sh --bead <id>` stays a valid reporter for a commit CI cannot run.

Rejected: (b) accepting the scoped lanes a change touches, because a change can break a lane it did not touch and still report pass; (c) keeping the full local run as the only reporter, because it keeps a 27-minute Docker run on every close.

## Consequences

The close follows CI: commit, push, wait for the run to go green, record the gate, then `br close`. The close record in `.beads/issues.jsonl` therefore lands in the next commit rather than the implementation commit.

Lanes are read from the verified commit, so a lane added after that commit does not apply to it, and a commit whose registry and workflow matrix disagree fails its own CI run and so never reports.
