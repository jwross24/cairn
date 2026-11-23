import hashlib
import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_missing_items import (
    GATHERER_CATEGORIES,
    GATHERER_SEARCHED_CATEGORIES,
    HEADING,
    HINT_DRIVEN_CATEGORIES,
    TESTS_GUARD_EXCLUDED_NAME,
    classify,
    spec_categories,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
EXCERPT = FIXTURES / "compliance_skill" / "gather-evidence-loops.sh"
META = json.loads((FIXTURES / "compliance_skill" / "gather-evidence-loops.json").read_text())
BEAD = FIXTURES / "compliance_pass" / "cairn-m0-e0s.12"

# The excerpt and the metadata beside it are cut from the vendored gatherer in one step, so a
# digest recorded in that metadata agrees with whatever was cut last and cannot witness the cut
# itself. These literals sit in source a reviewer reads, which is the one place a regeneration
# does not reach: a laundered edit to the gatherer has to be typed in here to pass.
EXCERPT_SHA256 = "1da867c4719e9da037633cb8ae192a686deb7bf51b360ef264866b223f10a90e"
EXCERPT_BYTES = 3972
SOURCE_SHA256 = "3fdd679e5aad522e6f866d2aa94f1a1d3fc5071ab3d9d27498af08fac8bce498"
SOURCE_BYTES = 7874
TESTS_MARKER = "# Walk tests (each type)"
DOC_MARKER = "# Walk documentation / migrations / feature_flags / telemetry / ci_workflows"
TEST_TYPES = ("unit", "integration", "e2e", "fuzz", "property", "metamorphic", "golden", "conformance")


@pytest.fixture(scope="module")
def gatherer():
    return EXCERPT.read_text()


def loop(gatherer, marker):
    after = gatherer.split(marker, 1)[1]
    for later in (TESTS_MARKER, DOC_MARKER):
        if later in after:
            after = after.split(later, 1)[0]
    return after


def test_the_tests_loop_declines_to_search_for_an_item_named_primary(gatherer):
    assert f'[ "$NAME" != "{TESTS_GUARD_EXCLUDED_NAME}" ]' in loop(gatherer, TESTS_MARKER)


def test_the_tests_loop_iterates_the_eight_types(gatherer):
    header = re.search(r"^for ttype in ([^;]+); do$", loop(gatherer, TESTS_MARKER), re.MULTILINE)
    assert header is not None
    assert tuple(header.group(1).split()) == TEST_TYPES


def test_the_doc_loop_iterates_the_categories_this_module_names(gatherer):
    header = re.search(r"^for cat in ([^;]+); do$", loop(gatherer, DOC_MARKER), re.MULTILINE)
    assert header is not None
    assert set(header.group(1).split()) == set(GATHERER_CATEGORIES)


def test_the_doc_loop_case_carries_arms_for_only_the_searched_categories(gatherer):
    body = loop(gatherer, DOC_MARKER).split('case "$cat" in', 1)[1].split("esac", 1)[0]
    assert set(re.findall(r"^\s*(\w+)\)$", body, re.MULTILINE)) == set(GATHERER_SEARCHED_CATEGORIES)


def test_the_two_searched_categories_resolve_by_existence_not_by_hint(gatherer):
    body = loop(gatherer, DOC_MARKER)
    assert 'if [ -f "$PROJECT/README.md" ]' in body
    assert 'if [ -d "$PROJECT/.github/workflows" ]' in body
    assert "expected_path_hints" not in body


def test_expected_path_hints_reaches_the_code_and_tests_loops_and_the_tests_hints_precede_the_guard(gatherer):
    lines = gatherer.splitlines()
    readers = [i for i, line in enumerate(lines) if ".expected_path_hints[" in line]
    walks = [[line for line in lines[:i] if line.startswith("# Walk ")][-1] for i in readers]
    assert walks == ["# Walk code_artifacts", TESTS_MARKER]
    assert HINT_DRIVEN_CATEGORIES == ("code_artifacts",)
    tests_loop = loop(gatherer, TESTS_MARKER)
    assert tests_loop.index(".expected_path_hints[") < tests_loop.index(f'[ "$NAME" != "{TESTS_GUARD_EXCLUDED_NAME}" ]')


def test_every_item_the_recorded_pass_reported_missing_was_never_searched_for():
    spec = json.loads((BEAD / "spec.json").read_text())
    items = classify((BEAD / "scorecard.md").read_text(), spec)
    assert len(items) == 5
    assert all(item.unresolvable for item in items)
    assert {item.spec_item_id for item in items} <= set(spec_categories(spec))


def test_the_heading_this_tool_splits_on_is_the_one_the_renderer_emits():
    assert HEADING in META["heading_render_line"]
    assert META["heading_render_line"] == f'md.append("{HEADING}\\n")'


def test_the_frozen_excerpt_is_the_bytes_this_file_pins():
    raw = EXCERPT.read_bytes()
    assert len(raw) == EXCERPT_BYTES, f"{EXCERPT} is {len(raw)} bytes against the pinned {EXCERPT_BYTES}"
    assert hashlib.sha256(raw).hexdigest() == EXCERPT_SHA256, (
        f"{EXCERPT} does not hash to the digest pinned in {Path(__file__).name}. "
        "Re-cutting the excerpt from the vendored gatherer rewrites the fixture and its metadata "
        "together, so this literal is the only record of which cut the classifier was read against: "
        "re-read the three loops, confirm the GATHERER_* constants still describe them, and update "
        "EXCERPT_SHA256 and EXCERPT_BYTES in the same review."
    )


def test_the_fixture_metadata_agrees_with_the_digests_this_file_pins():
    assert META["excerpt_sha256"] == EXCERPT_SHA256
    assert META["source_sha256"] == SOURCE_SHA256, (
        f"{META['source']} was cut at a digest other than the one pinned in {Path(__file__).name}; "
        "a regeneration that rewrites the metadata alone leaves this literal behind"
    )
    assert META["source_bytes"] == SOURCE_BYTES
