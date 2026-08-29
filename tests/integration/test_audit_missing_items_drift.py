import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

SKILL_LEAF = "skills/beads-compliance-and-completion-verification"
CANDIDATES = (
    Path.cwd() / ".claude" / SKILL_LEAF,
    Path.home() / ".claude" / SKILL_LEAF,
    Path.home() / ".codex" / SKILL_LEAF,
)
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "compliance_skill"
EXCERPT = FIXTURES / "gather-evidence-loops.sh"
META = json.loads((FIXTURES / "gather-evidence-loops.json").read_text())
SKILL = next((c for c in CANDIDATES if (c / "scripts/gather-evidence.sh").is_file()), None)

pytestmark = pytest.mark.skipif(
    SKILL is None,
    reason="the vendored compliance skill lives outside the repo; the frozen excerpt carries its structure for CI",
)


def skill_file(leaf):
    assert SKILL is not None
    return (SKILL / leaf).read_text()


def test_the_live_gatherer_still_matches_the_frozen_excerpt():
    live = skill_file("scripts/gather-evidence.sh")
    start = live.index(META["excerpt_first_line"])
    end = live.index(META["excerpt_stops_before"])
    cut = live[start:end].rstrip() + "\n"
    assert hashlib.sha256(cut.encode()).hexdigest() == META["excerpt_sha256"], (
        f"{META['source']} has drifted from tests/fixtures/compliance_skill/gather-evidence-loops.sh; "
        "re-read the three loops, update the excerpt and the GATHERER_* constants together"
    )


def test_the_live_renderer_still_emits_the_frozen_heading_line():
    renderer = skill_file("scripts/score-bead.py")
    assert META["heading_render_line"] in renderer, (
        f"{META['heading_renderer']} no longer emits the frozen heading line; "
        "the corrector splits on it, so update HEADING and the fixture together"
    )
