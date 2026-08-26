#!/usr/bin/env bash
# A closing bead's body carries an ARTIFACTS block: the source and test files with
# line ranges, the commit SHAs, and the commands re-executed at close. This refuses
# a close whose block is absent, malformed, or naming files that are not there.
#
#   scripts/bead-artifact-block.sh <bead-id> [<bead-id> …]
#
# Consumer: the session closing the bead, and the pre-commit hook, which runs it for
# every bead a commit closes, beside scripts/bead-test-plan.sh. It gates the close.
#
# Why the block exists: the compliance audit's deterministic extractor reads a bead
# body with regular expressions, and a body written as prose yields nothing for it to
# check. A prose bead and an empty one score identically, which is what keeps
# audit-policy.yaml's unmeasured_dimensions switch off. The block is the extractable
# form of what a close already writes, and it is the precondition that switch waits on.
#
# Every decision lives in scripts/bead_artifact_block.py, which the suite exercises
# directly: tests/conftest.py refuses a bash subprocess, so logic placed here would be
# logic no test can reach. This file is the shell-shaped entry point and nothing else.
#
# Every invocation appends one line to .check.log: PASS, FAIL, BYPASS, DENY, or
# PARITY-UNKNOWN.
#
# Bypass, named and logged: CAIRN_ARTIFACT_BLOCK_SKIP='<reason>'
exec uv run python "$(dirname "$0")/bead_artifact_block.py" "$@"
