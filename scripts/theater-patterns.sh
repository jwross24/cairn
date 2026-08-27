#!/usr/bin/env bash
# audit-policy.yaml's project_theater_patterns section, applied to the working tree.
#
#   scripts/theater-patterns.sh [--root DIR] [--policy FILE] [--log FILE]
#
# Consumer: scripts/check.sh, which the pre-commit hook and CI both call, so the
# gate cannot be enforced in one and absent from the other.
#
# Why it is cairn-owned rather than a sixth fork of the vendored skill: the skill
# reads project_theater_patterns only from subagents/theater-detector.md, and the
# pre-commit path runs no subagents; scripts/theater-scan.sh carries a fixed
# catalog and opens no policy file. A fork there would bind the section to one
# bead's cited files and would be reverted by the next upstream update. The cost
# is that findings here gate the commit and score nothing on the audit's
# anti_theater dimension.
#
# Every decision lives in scripts/theater_patterns.py, which the suite exercises
# directly: tests/conftest.py refuses a bash subprocess, so logic placed here
# would be logic no test can reach.
#
# Every invocation appends one line to .check.log: PASS, FAIL, OFF, DENY or BYPASS.
#
# Bypass, named and logged: CAIRN_THEATER_PATTERNS_SKIP='<reason>'
exec uv run python "$(dirname "$0")/theater_patterns.py" "$@"
