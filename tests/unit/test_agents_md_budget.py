import re

from cairn import bundle

ROOT = bundle.REPO_ROOT
AGENTS = ROOT / "AGENTS.md"
AGENT_DOCS = ROOT / "docs" / "agents"
MAX_BYTES = 19_000


def _mentioned():
    return set(re.findall(r"docs/agents/[A-Za-z0-9_.-]+\.md", AGENTS.read_text()))


def test_agents_md_fits_the_byte_budget():
    assert len(AGENTS.read_bytes()) <= MAX_BYTES


def test_every_agent_doc_agents_md_mentions_exists():
    mentioned = _mentioned()
    assert mentioned
    missing = sorted(p for p in mentioned if not (ROOT / p).is_file())
    assert not missing, f"AGENTS.md points at missing files: {missing}"


def test_every_agent_doc_is_mentioned_in_agents_md():
    on_disk = {f"docs/agents/{p.name}" for p in AGENT_DOCS.glob("*.md")}
    assert on_disk
    orphans = sorted(on_disk - _mentioned())
    assert not orphans, f"docs/agents files AGENTS.md never names: {orphans}"
