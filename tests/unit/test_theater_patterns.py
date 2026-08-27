import copy
import shutil
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from theater_patterns import (
    EXPIRY_BEAD,
    SECTION,
    PolicyError,
    evaluate,
    load_patterns,
    main,
    matches,
    targets,
)

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "theater_patterns.py"
POLICY = ROOT / "audit-policy.yaml"
CHILD_TIMEOUT_S = 60

# The fixture text is assembled rather than written out: a literal platform skip in
# this file is a match, and exempting the gate's own tests would widen the one list
# whose narrowness is the property under test.
MARK = "skip" + "if"

SKIP_BLOCK = """import sys

import pytest

pytestmark = pytest.mark.{mark}(
    sys.platform != "darwin",
    reason="{reason}",
)


def test_x():
    assert True
"""

SECOND_SKIP = """

@pytest.mark.{mark}(
    sys.platform != "linux",
    reason="a second, different skip in the same file",
)
def test_y():
    assert True
"""

ONE_LINE_SKIP = 'pytestmark = pytest.mark.{mark}(sys.platform != "darwin", reason="r")\n'


def entry(**overrides):
    base = {
        "id": "P-platform-skip-hides-a-gate",
        "signature": r"skipif\(\s*sys\.platform",
        "file_glob": ["tests/**/*.py"],
        "in_test_files": True,
        "severity": "MAJOR",
        "rationale": "a platform skip must be paired with an assertion naming the degraded behavior",
    }
    base.update(overrides)
    return base


def document(**overrides):
    return {SECTION: [entry(**overrides)]}


def tree(root: Path, files: Mapping[str, str]) -> Path:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


def open_bead(_bead_id):
    return "open"


def closed_bead(_bead_id):
    return "closed"


def real_policy() -> dict:
    return yaml.safe_load(POLICY.read_text())


def real_pattern() -> dict:
    return copy.deepcopy(real_policy()[SECTION][0])


def exempt_paths() -> list[str]:
    return [str(e["path"]) for e in real_pattern()["exempt_paths"]]


def exempt_counts() -> dict[str, int]:
    return {str(e["path"]): int(e["matches"]) for e in real_pattern()["exempt_paths"]}


def exempt(*paths: str, matches: int = 1) -> list[dict]:
    return [{"path": path, "matches": matches} for path in paths]


# --- the section is the switch -------------------------------------------------


def test_a_document_without_the_section_turns_the_gate_off(tmp_path):
    assert evaluate(tmp_path, {"threshold": 700}).kind == "OFF"


def test_an_empty_document_turns_the_gate_off(tmp_path):
    assert evaluate(tmp_path, None).kind == "OFF"


def test_an_empty_section_is_refused_rather_than_read_as_off(tmp_path):
    outcome = evaluate(tmp_path, {SECTION: []})
    assert outcome.kind == "DENY"
    assert "delete the key" in outcome.problems[0]


def test_the_gate_off_scans_nothing_even_with_a_matching_file(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    assert evaluate(tmp_path, {"threshold": 700}).findings == []


# --- the signature spans lines -------------------------------------------------


def test_the_declared_signature_matches_every_real_platform_skip():
    pattern = load_patterns(document(**{k: v for k, v in real_pattern().items() if k != "exempt_paths"}))[0]
    found = sorted(rel for rel in targets(ROOT, pattern) if matches((ROOT / rel).read_text(), pattern))
    assert found == [
        "tests/conformance/test_skill_contract.py",
        "tests/integration/test_gate_bundle.py",
        "tests/integration/test_grounding_fs.py",
        "tests/integration/test_toy_curve_selftest.py",
    ]


def test_the_line_oriented_signature_matches_none_of_them():
    pattern = load_patterns(document(signature=r"skipif\(sys\.platform"))[0]
    assert [rel for rel in targets(ROOT, pattern) if matches((ROOT / rel).read_text(), pattern)] == []


def test_the_reported_line_is_the_skipif_call_not_the_argument(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    outcome = evaluate(tmp_path, document())
    assert [(f.path, f.line) for f in outcome.findings] == [("tests/unit/test_a.py", 5)]


def test_a_single_line_skipif_still_matches(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": ONE_LINE_SKIP.format(mark=MARK)})
    assert len(evaluate(tmp_path, document()).findings) == 1


# --- the exemption, both directions --------------------------------------------


def test_the_real_policy_exempts_exactly_the_four_known_modules():
    assert exempt_paths() == [
        "tests/conformance/test_skill_contract.py",
        "tests/integration/test_gate_bundle.py",
        "tests/integration/test_grounding_fs.py",
        "tests/integration/test_toy_curve_selftest.py",
    ]


def test_the_real_policy_names_the_bead_that_removes_the_exemption():
    assert real_pattern()["exempt_until_bead"] == "cairn-hcl"


def test_the_real_tree_under_the_real_policy_is_clean():
    outcome = evaluate(ROOT, real_policy(), bead_status=open_bead)
    assert (outcome.kind, outcome.findings, outcome.problems) == ("PASS", [], [])


def test_a_fifth_module_outside_the_exemption_fires_major(tmp_path):
    files = {rel: SKIP_BLOCK.format(mark=MARK, reason="known") for rel in exempt_paths()}
    files["tests/unit/test_new.py"] = SKIP_BLOCK.format(mark=MARK, reason="new")
    tree(tmp_path, files)
    outcome = evaluate(tmp_path, {SECTION: [real_pattern()]}, bead_status=open_bead)
    assert outcome.kind == "FAIL"
    assert [(f.severity, f.path) for f in outcome.findings] == [("MAJOR", "tests/unit/test_new.py")]


def test_the_exemption_is_by_name_not_by_directory(tmp_path):
    files = {rel: SKIP_BLOCK.format(mark=MARK, reason="known") for rel in exempt_paths()}
    files["tests/integration/test_sibling.py"] = SKIP_BLOCK.format(mark=MARK, reason="sibling")
    tree(tmp_path, files)
    outcome = evaluate(tmp_path, {SECTION: [real_pattern()]}, bead_status=open_bead)
    assert [f.path for f in outcome.findings] == ["tests/integration/test_sibling.py"]


# --- an exemption covers a count, not a file -----------------------------------


def test_the_real_policy_records_the_count_each_exempt_module_actually_carries():
    pattern = load_patterns({SECTION: [real_pattern()]})[0]
    measured = {e.path: len(matches((ROOT / e.path).read_text(), pattern)) for e in pattern.exempt_paths}
    assert measured == exempt_counts()


def test_a_second_skip_in_an_already_exempt_file_fires_major(tmp_path):
    files = {rel: SKIP_BLOCK.format(mark=MARK, reason="known") for rel in exempt_paths()}
    grown = "tests/integration/test_grounding_fs.py"
    files[grown] += SECOND_SKIP.format(mark=MARK)
    tree(tmp_path, files)
    outcome = evaluate(tmp_path, {SECTION: [real_pattern()]}, bead_status=open_bead)
    assert outcome.kind == "FAIL"
    assert [(f.severity, f.path) for f in outcome.findings] == [("MAJOR", grown)]
    assert "covers 1 match(es) in this file; it carries 2" in outcome.findings[0].note


def test_the_finding_points_at_the_first_match_beyond_the_allowance(tmp_path):
    body = SKIP_BLOCK.format(mark=MARK, reason="known") + SECOND_SKIP.format(mark=MARK)
    tree(tmp_path, {"tests/unit/test_a.py": body})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead)
    pattern = load_patterns(doc)[0]
    assert outcome.findings[0].line == matches(body, pattern)[1][0]


def test_a_count_at_its_allowance_stays_silent(tmp_path):
    body = SKIP_BLOCK.format(mark=MARK, reason="known") + SECOND_SKIP.format(mark=MARK)
    tree(tmp_path, {"tests/unit/test_a.py": body})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py", matches=2), exempt_until_bead="cairn-hcl")
    assert evaluate(tmp_path, doc, bead_status=open_bead).kind == "PASS"


def test_a_count_that_drops_denies_rather_than_widening_the_allowance(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="known")})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py", matches=2), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead)
    assert outcome.kind == "DENY"
    assert "exempt for 2 match(es) but carries 1" in " ".join(outcome.problems)


def test_a_bare_path_carrying_no_count_is_refused():
    with pytest.raises(PolicyError, match="is a bare path"):
        load_patterns(document(exempt_paths=["tests/unit/test_a.py"], exempt_until_bead="cairn-hcl"))


def test_a_path_named_twice_is_refused():
    entries = exempt("tests/unit/test_a.py") + exempt("tests/unit/test_a.py", matches=2)
    with pytest.raises(PolicyError, match="more than once"):
        load_patterns(document(exempt_paths=entries, exempt_until_bead="cairn-hcl"))


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"path": "tests/unit/test_a.py"}, "matches must be an integer"),
        ({"path": "tests/unit/test_a.py", "matches": "1"}, "matches must be an integer"),
        ({"path": "tests/unit/test_a.py", "matches": True}, "matches must be an integer"),
        ({"path": "tests/unit/test_a.py", "matches": 0}, "drop the entry rather than exempting no match"),
        ({"matches": 1}, "has no path"),
        ({"path": "tests/unit/test_a.py", "matches": 1, "until": "x"}, "unknown exempt_paths key"),
    ],
)
def test_a_malformed_exemption_entry_is_refused(entry, message):
    with pytest.raises(PolicyError, match=message):
        load_patterns(document(exempt_paths=[entry], exempt_until_bead="cairn-hcl"))


# --- the exemption cannot widen or outlive its bead ----------------------------


def test_an_exemption_naming_no_removing_bead_is_refused():
    with pytest.raises(PolicyError, match="never expires"):
        load_patterns(document(exempt_paths=exempt("tests/unit/test_a.py")))


def test_a_closed_removing_bead_denies(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=closed_bead)
    assert outcome.kind == "DENY"
    assert "is closed" in " ".join(outcome.problems)


def test_an_open_removing_bead_passes(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    assert evaluate(tmp_path, doc, bead_status=open_bead).kind == "PASS"


def test_no_resolver_warns_rather_than_denying(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=None)
    assert outcome.kind == "PASS"
    assert outcome.problems == []
    assert "was not checked" in " ".join(outcome.warnings)


def test_no_resolver_still_scans_and_still_fires(tmp_path):
    """A warn that quietly stopped scanning would be the fail-open this gate exists against."""
    files = {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="known")}
    files["tests/unit/test_new.py"] = SKIP_BLOCK.format(mark=MARK, reason="new")
    tree(tmp_path, files)
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=None)
    assert outcome.kind == "FAIL"
    assert [f.path for f in outcome.findings] == ["tests/unit/test_new.py"]
    assert outcome.warnings != []


def test_no_resolver_still_enforces_the_per_file_count(tmp_path):
    body = SKIP_BLOCK.format(mark=MARK, reason="known") + SECOND_SKIP.format(mark=MARK)
    tree(tmp_path, {"tests/unit/test_a.py": body})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=None)
    assert outcome.kind == "FAIL"
    assert "carries 2" in outcome.findings[0].note


def test_a_resolver_that_is_present_and_cannot_find_the_bead_still_denies(tmp_path):
    def missing(bead_id):
        raise LookupError("br show exited 1")

    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-nope")
    outcome = evaluate(tmp_path, doc, bead_status=missing)
    assert outcome.kind == "DENY"
    assert "br show exited 1" in " ".join(outcome.problems)


def test_an_exempt_path_absent_from_the_tree_denies(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    doc = document(exempt_paths=exempt("tests/unit/test_gone.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead)
    assert outcome.kind == "DENY"
    assert "absent from the tree" in " ".join(outcome.problems)


def test_an_exempt_path_that_no_longer_matches_denies(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": "def test_x():\n    assert True\n"})
    doc = document(exempt_paths=exempt("tests/unit/test_a.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead)
    assert outcome.kind == "DENY"
    assert "no longer matches the signature" in " ".join(outcome.problems)


def test_an_exempt_path_no_glob_reaches_denies(tmp_path):
    tree(
        tmp_path,
        {
            "tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r"),
            "src/x.py": SKIP_BLOCK.format(mark=MARK, reason="r"),
        },
    )
    doc = document(exempt_paths=exempt("src/x.py"), exempt_until_bead="cairn-hcl")
    outcome = evaluate(tmp_path, doc, bead_status=open_bead)
    assert outcome.kind == "DENY"
    assert "no file_glob of this pattern reaches it" in " ".join(outcome.problems)


# --- a section that cannot be applied refuses rather than scanning less --------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"signature": "skipif("}, "does not compile"),
        ({"signature": ""}, "signature must be a non-empty string"),
        ({"severity": "CRITICAL"}, "is not one of"),
        ({"file_glob": []}, "file_glob must be a non-empty list"),
        ({"rationale": ""}, "rationale must be a non-empty string"),
        ({"in_test_files": "yes"}, "in_test_files must be a boolean"),
        ({"exempt_until_bead": 7}, "exempt_until_bead must be a bead id"),
    ],
)
def test_a_malformed_entry_is_refused(overrides, message):
    with pytest.raises(PolicyError, match=message):
        load_patterns(document(**overrides))


def test_a_non_mapping_entry_is_refused():
    with pytest.raises(PolicyError, match="is not a mapping"):
        load_patterns({SECTION: ["skipif"]})


def test_in_test_files_false_leaves_test_files_alone(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    assert evaluate(tmp_path, document(in_test_files=False)).kind == "PASS"


# --- the shell-facing contract ------------------------------------------------


def run_cli(*args, **kwargs):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        timeout=CHILD_TIMEOUT_S,
        **kwargs,
    )


def policy_file(tmp_path: Path, doc: dict) -> Path:
    path = tmp_path / "policy.yaml"
    path.write_text(yaml.safe_dump(doc))
    return path


def test_cli_refuses_a_finding_and_logs_fail(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(tmp_path), "--policy", str(policy_file(tmp_path, document())), "--log", str(log))
    assert proc.returncode == 2
    assert "MAJOR P-platform-skip-hides-a-gate  tests/unit/test_a.py:5" in proc.stderr
    assert log.read_text().split()[1:4] == ["FAIL", "theater-patterns:", "1"]


def test_cli_passes_the_real_tree_under_the_real_policy(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(ROOT), "--policy", str(POLICY), "--log", str(log))
    assert proc.returncode == 0, proc.stderr
    assert "PASS theater-patterns" in log.read_text()


def without_br(tmp_path: Path) -> dict[str, str]:
    """The CI runner's PATH: uv and git, no br."""
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    for tool in ("uv", "git", "python3"):
        found = shutil.which(tool)
        if found:
            (stub / tool).symlink_to(found)
    return {"PATH": f"{stub}:/usr/bin:/bin"}


def test_cli_passes_the_real_tree_with_br_off_path(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(ROOT), "--policy", str(POLICY), "--log", str(log), env=without_br(tmp_path))
    assert proc.returncode == 0, proc.stderr
    text = log.read_text()
    assert "EXPIRY-UNKNOWN theater-patterns" in text
    assert "PASS theater-patterns" in text
    assert EXPIRY_BEAD in proc.stderr


def test_cli_with_br_off_path_still_refuses_a_planted_skip(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    policy = policy_file(tmp_path, document(exempt_paths=exempt("tests/unit/test_b.py"), exempt_until_bead="cairn-hcl"))
    tree(tmp_path, {"tests/unit/test_b.py": SKIP_BLOCK.format(mark=MARK, reason="known")})
    proc = run_cli("--root", str(tmp_path), "--policy", str(policy), "--log", str(log), env=without_br(tmp_path))
    assert proc.returncode == 2
    assert "tests/unit/test_a.py:5" in proc.stderr
    assert "EXPIRY-UNKNOWN theater-patterns" in log.read_text()


def test_cli_logs_off_when_the_section_is_deleted(tmp_path):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    proc = run_cli(
        "--root", str(tmp_path), "--policy", str(policy_file(tmp_path, {"threshold": 700})), "--log", str(log)
    )
    assert proc.returncode == 0
    assert "OFF theater-patterns" in log.read_text()


def test_cli_denies_a_missing_policy_rather_than_reporting_clean(tmp_path):
    log = tmp_path / "gate.log"
    proc = run_cli("--root", str(tmp_path), "--policy", str(tmp_path / "absent.yaml"), "--log", str(log))
    assert proc.returncode == 3
    assert "refusing to report a clean tree unscanned" in proc.stderr
    assert "DENY theater-patterns infra" in log.read_text()


def test_cli_denies_an_unparsable_policy(tmp_path):
    log = tmp_path / "gate.log"
    bad = tmp_path / "policy.yaml"
    bad.write_text("project_theater_patterns: [\n")
    proc = run_cli("--root", str(tmp_path), "--policy", str(bad), "--log", str(log))
    assert proc.returncode == 3
    assert "does not parse as YAML" in proc.stderr


def test_cli_bypass_is_named_and_logged(tmp_path, monkeypatch):
    tree(tmp_path, {"tests/unit/test_a.py": SKIP_BLOCK.format(mark=MARK, reason="r")})
    log = tmp_path / "gate.log"
    monkeypatch.setenv("CAIRN_THEATER_PATTERNS_SKIP", "probing the bypass")
    assert main(["--root", str(tmp_path), "--policy", str(policy_file(tmp_path, document())), "--log", str(log)]) == 0
    assert "BYPASS theater-patterns: probing the bypass" in log.read_text()


def test_check_sh_runs_the_gate():
    assert "theater-patterns.sh" in (ROOT / "scripts" / "check.sh").read_text()


def test_a_br_that_never_answers_denies_the_scan_rather_than_skipping_the_expiry(monkeypatch):
    import theater_patterns

    def expire(argv, **kwargs):
        assert kwargs.get("timeout") == theater_patterns.BR_TIMEOUT_SECONDS, argv
        raise subprocess.TimeoutExpired(argv, theater_patterns.BR_TIMEOUT_SECONDS)

    monkeypatch.setattr(theater_patterns.subprocess, "run", expire)
    with pytest.raises(LookupError) as raised:
        theater_patterns.bead_status_resolver()("cairn-fur")
    assert "did not answer within" in str(raised.value)
    assert "cairn-fur" in str(raised.value)
