"""The bead store the two gates read: how a failed lookup is named, and where CI gets one.

`br` itself is outside conftest's subprocess allow-list, so the lookups that have to
run it are exercised through the gates in test_bead_artifact_block.py and
test_theater_patterns.py; what is unit-testable here is the part that decides before
`br` is reached, and the wiring that gives a runner a store at all.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

import br_lookup  # noqa: E402
from _bead_store import bead_store, no_database  # noqa: E402

WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

# The order br 0.2.22 requires: it refuses `init`, `sync` and `show` alike while a
# `.beads` directory holding no database is in place, so the tracked files can only
# be laid back down after the store exists.
REBUILD_SEQUENCE = (
    "mv .beads",
    "br init",
    "issues.jsonl",
    "br sync --import-only",
    "br show",
)


def test_a_workspace_with_no_database_is_unavailable_before_br_is_run():
    blocked = br_lookup.unavailable(no_database())
    assert blocked is not None
    assert blocked.condition == br_lookup.NO_DATABASE
    assert "br sync --import-only" in blocked.remediation


def test_a_workspace_with_a_database_is_available():
    assert br_lookup.unavailable(bead_store()) is None


def test_a_directory_with_no_beads_workspace_above_it_is_not_a_bead_that_is_missing(tmp_path):
    blocked = br_lookup.unavailable(tmp_path)
    assert blocked is not None
    assert blocked.condition == br_lookup.NO_DATABASE


@pytest.mark.parametrize(
    ("condition", "expected"),
    [
        (br_lookup.BR_ABSENT, "br is not installed"),
        (br_lookup.NO_DATABASE, "no bead database to resolve it against"),
        (br_lookup.UNKNOWN_BEAD, "cairn-abc is not in the bead store"),
        (br_lookup.UNREADABLE, "the bead store would not answer for cairn-abc"),
    ],
)
def test_each_condition_gets_its_own_sentence(condition, expected):
    assert br_lookup.BeadLookupError(condition, "measured").headline("cairn-abc") == expected


def test_each_condition_gets_its_own_remediation():
    fixes = {c: br_lookup.REMEDIATION[c] for c in br_lookup.REMEDIATION}
    assert len(set(fixes.values())) == len(fixes)


def test_a_plain_lookup_error_is_named_rather_than_forwarded():
    named = br_lookup.as_lookup_error(LookupError("br show exited 1"))
    assert named.condition == br_lookup.UNREADABLE
    assert "br show exited 1" in named.detail


def _rebuild_step_body() -> str:
    text = WORKFLOW.read_text()
    marker = "- name: The bead store the gates resolve ids against"
    assert marker in text, "the workflow builds no bead store"
    after = text.split(marker, 1)[1].split("\n      - ", 1)[0]
    script = after.split("run: |\n", 1)[1]
    return "\n".join(line for line in script.splitlines() if not line.strip().startswith("#"))


def _step_offsets() -> dict[str, int]:
    text = WORKFLOW.read_text()
    return {m.group(1): m.start() for m in re.finditer(r"^      - name: (.+)$", text, re.MULTILINE)}


def test_ci_builds_a_bead_store_after_installing_br_and_before_the_gates():
    steps = _step_offsets()
    store = "The bead store the gates resolve ids against"
    assert store in steps, sorted(steps)
    assert steps["The br the gates read"] < steps[store]
    assert steps[store] < steps["Gates"]


def test_the_ci_rebuild_runs_the_only_order_br_accepts():
    body = _rebuild_step_body()
    positions = [body.find(token) for token in REBUILD_SEQUENCE]
    assert all(p >= 0 for p in positions), dict(zip(REBUILD_SEQUENCE, positions, strict=True))
    assert positions == sorted(positions), dict(zip(REBUILD_SEQUENCE, positions, strict=True))


def test_the_ci_rebuild_fails_its_own_step_rather_than_a_later_one():
    body = _rebuild_step_body()
    assert "set -euo pipefail" in body
