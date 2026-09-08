import re

import pytest

from cairn import bundle, claims, cli

MAP = bundle.REPO_ROOT / "MAP.md"
REGISTRIES = {
    "command": lambda: cli.registered(),
    "evidence_kind": lambda: claims.EVIDENCE_KINDS,
    "repro_kind": lambda: claims.REPRO_KINDS,
    "gate": lambda: claims.GATES,
    "tag": lambda: claims.TAGS,
    "bundle_object": lambda: tuple(sorted(bundle.source_objects(bundle.REPO_ROOT / bundle.DEFAULT_SRC))),
}


def code_spans(text):
    return set(re.findall(r"`([^`]+)`", text))


def absent(text, names):
    spans = code_spans(text)
    return tuple(n for n in names if n not in spans and f"cairn {n}" not in spans)


def report(label, missing):
    return f"MAP.md names no {label} for: {', '.join(missing)}"


@pytest.mark.parametrize("label", sorted(REGISTRIES))
def test_the_map_names_every_registered_entry(label):
    names = REGISTRIES[label]()
    assert names
    missing = absent(MAP.read_text(), names)
    assert not missing, report(label, missing)


@pytest.mark.parametrize(("label", "dropped"), [(a, n) for a in sorted(REGISTRIES) for n in REGISTRIES[a]()])
def test_a_scratch_map_missing_one_entry_goes_red(label, dropped):
    names = REGISTRIES[label]()
    text = MAP.read_text()
    scratch = text.replace(f"`{dropped}`", "`[removed]`").replace(f"`cairn {dropped}`", "`[removed]`")
    assert scratch != text
    missing = absent(scratch, names)
    assert missing == (dropped,)
    assert dropped in report(label, missing)


def test_a_name_appearing_only_inside_a_longer_code_span_does_not_count():
    assert absent("the module `justify.py` holds it", ("justify",)) == ("justify",)
    assert absent("the verb `justify` drives it", ("justify",)) == ()
