import ast
import re
from pathlib import Path

import pytest

from cairn import bundle, challenge, container, lean, statement_prefilters, verifier

ROOT = bundle.REPO_ROOT
AGENTS = ROOT / "AGENTS.md"


def _skill_sources():
    found = set()
    for path in sorted((ROOT / "src" / "cairn" / "skills").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "IDENTITY_SOURCES" for t in node.targets
            ):
                found |= set(ast.literal_eval(node.value))
    return tuple(sorted(found))


def _relative(path):
    return str(Path(path).resolve().relative_to(ROOT.resolve()))


def _gate_bundle_sources():
    found = {_relative(p) for p in (ROOT / bundle.DEFAULT_SRC).glob("*.json")}
    found |= {
        _relative(lean.MANIFEST_PATH),
        _relative(lean.STATEMENT_HASHER_PATH),
        _relative(lean.AXIOM_PATH),
        _relative(container.CONTAINERFILE_PATH),
    }
    for module in (challenge, verifier, statement_prefilters):
        for name in dir(module):
            if name.endswith("_PATH"):
                value = getattr(module, name)
                if isinstance(value, (str, Path)):
                    found.add(_relative(value))
    found |= {
        _relative(statement_prefilters.VENDOR_DIR / relative)
        for relative in statement_prefilters.LINTER_SOURCES.values()
    }
    return tuple(sorted(found))


REGISTRIES = {
    "skill revision": _skill_sources,
    "gate bundle": _gate_bundle_sources,
}


def _code_spans(text):
    return set(re.findall(r"`([^`]+)`", text))


def _absent(text, paths):
    spans = _code_spans(text)
    return tuple(p for p in paths if p not in spans)


@pytest.mark.parametrize("label", sorted(REGISTRIES))
def test_agents_md_names_every_identity_bearing_file(label):
    paths = REGISTRIES[label]()
    assert paths
    missing = _absent(AGENTS.read_text(), paths)
    assert not missing, f"AGENTS.md names no {label} identity-bearing file for: {', '.join(missing)}"


@pytest.mark.parametrize(
    ("label", "dropped"),
    [(label, path) for label in sorted(REGISTRIES) for path in REGISTRIES[label]()],
)
def test_a_scratch_agents_md_missing_one_path_goes_red(label, dropped):
    text = AGENTS.read_text()
    scratch = text.replace(f"`{dropped}`", "`[removed]`")
    assert scratch != text
    assert dropped in _absent(scratch, REGISTRIES[label]())


@pytest.mark.parametrize("label", sorted(REGISTRIES))
def test_every_path_the_code_names_is_a_file_on_disk(label):
    for path in REGISTRIES[label]():
        assert (ROOT / path).is_file(), f"{label} names {path}, which is not a file"


def test_the_two_registries_name_no_file_in_common():
    overlap = set(REGISTRIES["skill revision"]()) & set(REGISTRIES["gate bundle"]())
    assert not overlap, f"a file cannot be both: {sorted(overlap)}"
