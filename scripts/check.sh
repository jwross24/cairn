#!/usr/bin/env bash
# The one place that says what "green" means. The pre-commit hook and CI both
# call this, so a gate can never be enforced in one and absent from the other.
#
#   scripts/check.sh --fast   format + lint + spelling   (seconds; the hook)
#   scripts/check.sh          the above plus the suite   (minutes; CI)
#
# Every run appends one line per gate to .check.log with pass/fail/skip, so a
# reader can tail it and see what actually fired. A gate whose tool is missing
# DENIES; it never passes quietly.
#
# Bypass, named and logged: CAIRN_CHECK_SKIP='<reason>' scripts/check.sh
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 3
LOG="$ROOT/.check.log"
STAMP() { date -u +%Y-%m-%dT%H:%M:%SZ; }
say() { printf '%s %s\n' "$(STAMP)" "$*" >> "$LOG"; }

if [ -n "${CAIRN_CHECK_SKIP:-}" ]; then
  say "BYPASS all gates: $CAIRN_CHECK_SKIP"
  echo "[check] BYPASSED: $CAIRN_CHECK_SKIP (logged to .check.log)" >&2
  exit 0
fi

FAST=0
[ "${1:-}" = "--fast" ] && FAST=1

if ! command -v uv >/dev/null 2>&1; then
  say "DENY infra: uv not on PATH"
  echo "[check] uv is not installed; every gate runs through it." >&2
  echo "        install: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 3
fi

FAILED=()

# Output streams rather than being captured. A captured gate that hangs prints
# nothing at all, which is how a 45-minute CI hang produced no diagnostic beyond
# the step before it.
gate() {
  local name="$1"; shift
  say "RUN $name"
  printf '[check] run %s\n' "$name"
  if ! "$@"; then
    say "FAIL $name"
    printf '[check] FAIL %s\n' "$name" >&2
    FAILED+=("$name")
    return 1
  fi
  say "PASS $name"
  printf '[check] pass %s\n' "$name"
}

gate format   uv run ruff format --check src tests scripts
gate lint     uv run ruff check src tests scripts
gate spelling uv run codespell
gate types    uv run ty check src tests
gate theater  ./scripts/theater-patterns.sh
if [ "$FAST" = "1" ]; then
  say "SKIP tests (--fast)"
  printf '[check] skip tests (--fast; CI runs them)\n'
else
  if [ -n "${CAIRN_SESSION_DEADLINE_SKIP:-}" ]; then
    say "DEADLINE bypassed: $CAIRN_SESSION_DEADLINE_SKIP"
  else
    say "DEADLINE ${CAIRN_SESSION_DEADLINE:-3000}s session (dumps every thread; a kill prints 'Timeout (' on stderr, and the watchdog exits 124, its faulthandler backstop 15s later exits 1; an in-process libpari call past cairn.pari.CALL_BOUND_S prints 'libpari stall in <test>' and also exits 124)"
  fi
  gate tests uv run pytest -q --durations=25
fi

if [ ${#FAILED[@]} -ne 0 ]; then
  say "RESULT fail: ${FAILED[*]}"
  printf '\n[check] FAILED: %s\n' "${FAILED[*]}" >&2
  printf '        fix formatting: uv run ruff format src tests scripts\n' >&2
  printf '        fix lint:       uv run ruff check --fix src tests scripts\n' >&2
  printf '        bypass (logged): CAIRN_CHECK_SKIP=%s scripts/check.sh\n' "'<reason>'" >&2
  exit 1
fi

say "RESULT pass (fast=$FAST)"
printf '[check] all gates pass\n'
