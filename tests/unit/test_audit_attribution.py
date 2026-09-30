import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_attribution import (
    ClosingDiff,
    IgnoreConfigError,
    correct,
    correct_pass,
    count_ignore_adds,
    git_closing_diff_reader,
    main,
    passes_after,
    prior_pass,
    pyproject_ignores,
    rederive,
)
from closing_commit import STAGED, UNKNOWN, GitError, history_closings

BEAD = "cairn-m0-e0s.16"
CLOSING_SHA = "04289d27eeb979a1ba3bcdf6f6083c6b5fcde9ce"
MENTIONING_SHA = "dcbe2080d0f7cbb3b8f0b7f1cf0b8a1ba6e5e5c1"
LATER_SHA = "0e560234b1c4a9e0f2d1a7c9b3e8d6f4a2c0b8e6"

MISATTRIBUTED = {
    "id": "anomaly.1",
    "severity": "BLOCKING",
    "category": "anomaly_ignore_list_growth",
    "path": f"(bead {BEAD})",
    "line": 0,
    "snippet": "(see show.json)",
    "description": "Closing commit added 1 line(s) to ignore lists — possible silencing instead of fixing",
}
UNRELATED = {
    "id": "theater.1",
    "severity": "MAJOR",
    "category": "assertion_free_test",
    "path": "tests/unit/test_thing.py",
    "line": 12,
    "snippet": "assert True",
    "description": "a test that asserts nothing",
}


def theater(*findings):
    summary = {"BLOCKING": 0, "MAJOR": 0, "MINOR": 0, "NOTE": 0}
    for finding in findings:
        summary[finding["severity"]] += 1
    return {"bead_id": BEAD, "scanned_files": [], "findings": list(findings), "summary": summary}


def bead_line(bead_id: str, status: str) -> str:
    return f'{{"id":"{bead_id}","title":"t","status":"{status}"}}'


def git_chunk(sha: str, lines: list[str]) -> str:
    return "\x00" + sha + "\n--- a/.beads/issues.jsonl\n+++ b/.beads/issues.jsonl\n" + "\n".join(lines) + "\n"


def closing_chunk(sha: str, bead_id: str) -> str:
    return git_chunk(sha, ["-" + bead_line(bead_id, "open"), "+" + bead_line(bead_id, "closed")])


def mentioning_chunk(sha: str, closes: str, mentions: str) -> str:
    """A later commit that closes some other bead and rewrites this one's row unchanged."""
    return git_chunk(
        sha,
        [
            "-" + bead_line(closes, "open"),
            "+" + bead_line(closes, "closed"),
            "-" + bead_line(mentions, "closed"),
            "+" + bead_line(mentions, "closed"),
        ],
    )


@pytest.mark.parametrize(
    ("diff", "categories"),
    [
        (ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0), []),
        (ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=0), ["anomaly_empty_diff"]),
        (ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=3), ["anomaly_ignore_list_growth"]),
        (
            ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=1),
            ["anomaly_empty_diff", "anomaly_ignore_list_growth"],
        ),
        (None, []),
    ],
)
def test_each_attributed_pattern_is_rederived_from_the_closing_diff_alone(diff, categories):
    assert [f["category"] for f in rederive(diff)] == categories


def test_a_raised_finding_names_the_commit_it_was_judged_against():
    (finding,) = rederive(ClosingDiff(STAGED, files_changed=4, ignore_adds=2))
    assert STAGED in finding["description"]
    assert "2 entry(s)" in finding["description"]


@pytest.mark.parametrize(
    ("diff_text", "count"),
    [
        ("+.beads_hook.log\n", 1),
        ("+++ b/.gitignore\n+one\n+two\n", 2),
        ("+\n", 0),
        ("-removed\n context\n", 0),
        ("", 0),
    ],
)
def test_added_lines_are_counted_the_way_the_scanner_counts_them(diff_text, count):
    assert count_ignore_adds(diff_text) == count


def test_a_finding_raised_against_another_beads_commit_is_dropped():
    corrected, notes = correct(
        theater(MISATTRIBUTED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0)
    )
    assert corrected["findings"] == []
    assert corrected["summary"]["BLOCKING"] == 0
    assert notes == ["dropped 1 finding(s) raised against a commit the bead did not close"]
    assert corrected["commit_attribution"]["closing_commit"] == CLOSING_SHA


def test_a_finding_true_of_the_beads_own_closing_commit_is_reraised():
    corrected, _ = correct(
        theater(MISATTRIBUTED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=1)
    )
    (kept,) = corrected["findings"]
    assert kept["category"] == "anomaly_ignore_list_growth"
    assert kept["severity"] == "BLOCKING"
    assert CLOSING_SHA in kept["description"]
    assert corrected["summary"]["BLOCKING"] == 1


def test_a_pattern_the_scanner_missed_is_raised_against_the_right_commit():
    corrected, notes = correct(
        theater(UNRELATED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=0)
    )
    assert [f["category"] for f in corrected["findings"]] == ["assertion_free_test", "anomaly_empty_diff"]
    assert notes == [f"raised 1 finding(s) against {CLOSING_SHA}"]


def test_findings_the_patterns_do_not_own_survive_the_correction():
    corrected, _ = correct(theater(MISATTRIBUTED, UNRELATED), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, 7, 0))
    assert corrected["findings"] == [UNRELATED]
    assert corrected["summary"] == {"BLOCKING": 0, "MAJOR": 1, "MINOR": 0, "NOTE": 0}


def test_a_bead_no_commit_closed_carries_neither_attributed_pattern():
    corrected, _ = correct(theater(MISATTRIBUTED), BEAD, UNKNOWN, None)
    assert corrected["findings"] == []
    assert corrected["commit_attribution"]["closing_commit"] == UNKNOWN


def test_anomaly_ids_are_renumbered_so_two_findings_never_share_one():
    second = dict(MISATTRIBUTED, id="anomaly.1", category="anomaly_empty_diff", severity="MAJOR")
    corrected, _ = correct(theater(second), BEAD, CLOSING_SHA, ClosingDiff(CLOSING_SHA, 0, 2))
    ids = [f["id"] for f in corrected["findings"]]
    assert ids == ["anomaly.1", "anomaly.2"]


@pytest.mark.parametrize(
    ("after", "expected"),
    [
        (None, ["a", "b", "c"]),
        ("a", ["b", "c"]),
        ("c", []),
    ],
)
def test_only_passes_opened_after_the_marker_are_corrected(after, expected):
    assert passes_after(["c", "a", "b"], after) == expected


def test_the_prior_pass_is_the_newest_one_that_is_not_this_one():
    assert prior_pass(["a", "b", "c"], "c") == "b"
    assert prior_pass(["a"], "a") is None


def test_the_commit_being_made_is_read_from_the_staged_diff_and_not_from_history(monkeypatch):
    import audit_attribution

    seen = []

    def fake_git(_root, args):
        seen.append(args[0])
        return "+one\n" if "--cached" in args and "--" in args else ".gitignore\nsrc/a.py\n"

    monkeypatch.setattr(audit_attribution, "_git", fake_git)
    diff = audit_attribution.git_closing_diff_reader(Path())(STAGED)
    assert seen == ["diff", "diff"]
    assert diff == ClosingDiff(label="(staged)", files_changed=2, ignore_adds=1)


def test_a_commit_already_in_history_is_read_with_show(monkeypatch):
    import audit_attribution

    seen = []

    def fake_git(_root, args):
        seen.append(args[0])
        return "" if "--" in args else "src/a.py\n"

    monkeypatch.setattr(audit_attribution, "_git", fake_git)
    diff = audit_attribution.git_closing_diff_reader(Path())(CLOSING_SHA)
    assert seen == ["show", "show"]
    assert diff == ClosingDiff(label=CLOSING_SHA, files_changed=1, ignore_adds=0)


def test_a_bead_no_commit_closed_asks_git_nothing(monkeypatch):
    import audit_attribution

    monkeypatch.setattr(audit_attribution, "_git", lambda *a: pytest.fail("git was consulted"))
    assert audit_attribution.git_closing_diff_reader(Path())(UNKNOWN) is None


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.fixture
def config_repo(tmp_path, monkeypatch):
    import conftest

    allowed = conftest._allowed_argv0
    monkeypatch.setattr(conftest, "_allowed_argv0", lambda: {*allowed(), "git"})
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-b", "main")
    git(root, "config", "core.hooksPath", "/dev/null")
    git(root, "config", "user.name", "Audit Test")
    git(root, "config", "user.email", "audit@example.test")
    (root / "tracked.txt").write_text("baseline\n")
    git(root, "add", "tracked.txt")
    git(root, "commit", "-m", "baseline")
    return root


def stage_config(root, text):
    (root / "pyproject.toml").write_text(text)
    git(root, "add", "pyproject.toml")


def commit_config(root, text):
    stage_config(root, text)
    git(root, "commit", "-m", "configuration")
    return git(root, "rev-parse", "HEAD")


def test_dependency_move_with_identical_tool_configuration_is_not_ignore_growth(config_repo):
    before = '[project]\ndependencies = []\n[dependency-groups]\ndev = ["gmpy2>=2.3.1"]\n'
    after = '[project]\ndependencies = ["gmpy2>=2.3.1"]\n[dependency-groups]\ndev = []\n'
    settings = '[tool.ruff.lint]\nignore = ["E501"]\n[tool.codespell]\nignore-words-list = "aci,fro"\n'
    commit_config(config_repo, before + settings)
    stage_config(config_repo, after + settings)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff == ClosingDiff("(staged)", 1, 0)
    assert rederive(diff) == []


@pytest.mark.parametrize(
    "setting",
    [
        '[tool.ruff]\nignore = ["F401"]',
        '[tool.ruff]\nextend-ignore = ["F401"]',
        '[tool.ruff.lint]\nignore = ["F401"]',
        '[tool.ruff.lint]\nextend-ignore = ["F401"]',
        '[tool.ruff.per-file-ignores]\n"tests/*" = ["F401"]',
        '[tool.ruff.extend-per-file-ignores]\n"tests/*" = ["F401"]',
        '[tool.ruff.lint.per-file-ignores]\n"tests/*" = ["F401"]',
        '[tool.ruff.lint.extend-per-file-ignores]\n"tests/*" = ["F401"]',
        '[tool.ruff]\nexclude = ["tests/*"]',
        '[tool.ruff]\nextend-exclude = ["tests/*"]',
        '[tool.ruff.lint]\nexclude = ["tests/*"]',
        '[tool.ruff.format]\nexclude = ["tests/*"]',
        '[tool.ty.rules]\ninvalid-argument-type = "ignore"',
        '[[tool.ty.overrides]]\ninclude = ["tests/*"]\n[tool.ty.overrides.rules]\ninvalid-argument-type = "ignore"',
        '[tool.ty.src]\nexclude = ["tests/*"]',
        '[tool.pytest.ini_options]\nfilterwarnings = ["ignore::UserWarning"]',
        '[tool.pytest]\nfilterwarnings = ["ignore::UserWarning"]',
        '[tool.pytest.ini_options]\nfilterwarnings = "ignore::UserWarning"',
        '[tool.pytest.ini_options]\nnorecursedirs = "tests/*"',
        '[tool.pytest]\nnorecursedirs = ["tests/*"]',
        '[tool.pytest.ini_options]\naddopts = "--ignore tests/unit"',
        '[tool.pytest]\naddopts = ["--ignore=tests/unit"]',
        '[tool.pytest]\naddopts = ["--ignore-glob", "tests/*"]',
        '[tool.pytest.ini_options]\naddopts = "-Wignore::UserWarning"',
        '[tool.pytest.ini_options]\naddopts = "-W ignore::UserWarning"',
        '[tool.pytest.ini_options]\naddopts = "--pythonwarnings=ignore::UserWarning"',
        '[tool.pytest.ini_options]\naddopts = "--pythonwarnings ignore::UserWarning"',
        '[tool.pytest]\naddopts = ["-Wi::UserWarning"]',
        '[tool.pytest]\nfilterwarnings = ["i::UserWarning"]',
        '[tool.codespell]\nignore-words-list = "word"',
        '[tool.codespell]\nignore-words-list = ["word"]',
        '[tool.codespell]\nuri-ignore-words-list = "word"',
        '[tool.codespell]\nignore-words = "ignored.txt"',
        '[tool.codespell]\nignore-regex = "word"',
        '[tool.codespell]\nignore-multiline-regex = "word"',
        '[tool.codespell]\nskip = "tests/*"',
        '[tool.codespell]\nexclude-file = "ignored.txt"',
    ],
)
def test_added_suppression_refuses_in_both_index_and_history(config_repo, setting):
    commit_config(config_repo, '[project]\nname = "test"\n')
    stage_config(config_repo, '[project]\nname = "test"\n' + setting + "\n")
    staged = git_closing_diff_reader(config_repo)(STAGED)
    assert staged.ignore_adds == 1
    assert rederive(staged)[0]["severity"] == "BLOCKING"
    git(config_repo, "commit", "-m", "suppression")
    committed = git_closing_diff_reader(config_repo)(git(config_repo, "rev-parse", "HEAD"))
    assert committed.ignore_adds == 1
    assert rederive(committed)[0]["severity"] == "BLOCKING"


def test_index_and_historical_configurations_are_isolated_from_worktree(config_repo):
    commit_config(config_repo, "[tool.ruff.lint]\nignore = []\n")
    sha = commit_config(config_repo, '[tool.ruff.lint]\nignore = ["F401"]\n')
    stage_config(config_repo, '[tool.ruff.lint]\nignore = ["F401", "F841", "E501"]\n')
    (config_repo / "pyproject.toml").write_text("invalid worktree TOML [")
    reader = git_closing_diff_reader(config_repo)
    assert reader(STAGED).ignore_adds == 2
    assert reader(sha).ignore_adds == 1


@pytest.mark.parametrize("path", [".ubsignore", ".eslintignore", ".gitignore", ".flake8"])
def test_dedicated_ignore_files_retain_line_based_detection(config_repo, path):
    (config_repo / path).write_text("one\ntwo\n")
    git(config_repo, "add", path)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 2
    assert rederive(diff)[0]["severity"] == "BLOCKING"


def test_new_config_without_suppressions_and_missing_config_are_clean(config_repo):
    (config_repo / "tracked.txt").write_text("ordinary edit\n")
    git(config_repo, "add", "tracked.txt")
    assert git_closing_diff_reader(config_repo)(STAGED).ignore_adds == 0
    stage_config(config_repo, '[project]\nname = "test"\n')
    assert git_closing_diff_reader(config_repo)(STAGED).ignore_adds == 0


def test_root_commit_counts_new_config_suppressions(config_repo):
    before = git(config_repo, "rev-parse", "HEAD")
    stage_config(config_repo, '[tool.ruff.lint]\nignore = ["F401"]\n')
    tree = git(config_repo, "write-tree")
    sha = git(config_repo, "commit-tree", tree, "-m", "root configuration")
    assert git_closing_diff_reader(config_repo)(sha).ignore_adds == 1
    assert git(config_repo, "rev-parse", "HEAD") == before


def test_removed_config_has_no_added_suppression(config_repo):
    commit_config(config_repo, '[tool.ruff.lint]\nignore = ["F401"]\n')
    (config_repo / "pyproject.toml").rename(config_repo / "retained-config.toml")
    git(config_repo, "add", "--update", "pyproject.toml")
    assert git_closing_diff_reader(config_repo)(STAGED).ignore_adds == 0
    git(config_repo, "commit", "-m", "configuration removal")
    assert git_closing_diff_reader(config_repo)(git(config_repo, "rev-parse", "HEAD")).ignore_adds == 0


@pytest.mark.parametrize(
    "text",
    [
        "[malformed",
        'tool = "not a table"',
        'tool.ruff = "not a table"',
        '[tool.ruff.lint]\nignore = "F401"',
        "[tool.ruff.lint]\nignore = [1]",
        '[tool.ruff.lint]\nper-file-ignores = ["F401"]',
        '[tool.ruff.lint.per-file-ignores]\n"*.py" = "F401"',
        '[tool.ruff]\nextend-exclude = "tests"',
        "[tool.ty]\noverrides = {}",
        "[tool.ty]\noverrides = [1]",
        "[tool.ty.rules]\ninvalid-argument-type = false",
        '[tool.ty.rules]\ninvalid-argument-type = "disabled"',
        '[[tool.ty.overrides]]\ninclude = "tests"',
        '[tool.pytest]\nfilterwarnings = "ignore"',
        "[tool.pytest]\nfilterwarnings = [1]",
        '[tool.pytest]\naddopts = ["--ignore"]',
        '[tool.pytest.ini_options]\naddopts = "\\""',
        '[tool.pytest]\naddopts = ["-W"]',
        '[tool.pytest]\naddopts = ["--pythonwarnings"]',
        '[tool.pytest]\naddopts = ["-Wunknown"]',
        '[tool.pytest]\nfilterwarnings = ["ignore:a:b:c:d:e"]',
        '[tool.pytest]\nfilterwarnings = ["ignore::::bad"]',
        '[tool.pytest]\nfilterwarnings = ["ignore::::-1"]',
        '[tool.pytest]\nfilterwarnings = ["ignore"]\n[tool.pytest.ini_options]\nfilterwarnings = ["error"]',
        "[tool.codespell]\nignore-words-list = 1",
        "[tool.codespell]\nignore-words-list = [1]",
        '[tool.codespell]\nignore-regex = ["word"]',
    ],
)
def test_malformed_configuration_refuses_with_revision_and_path(config_repo, text):
    stage_config(config_repo, text + "\n")
    with pytest.raises(IgnoreConfigError, match=r"pyproject\.toml"):
        git_closing_diff_reader(config_repo)(STAGED)


def test_malformed_parent_configuration_cannot_be_read_as_no_suppressions(config_repo):
    commit_config(config_repo, "[malformed\n")
    stage_config(config_repo, '[project]\nname = "test"\n')
    with pytest.raises(IgnoreConfigError, match=r"HEAD:pyproject\.toml: invalid TOML"):
        git_closing_diff_reader(config_repo)(STAGED)


def test_unreadable_git_blob_refuses(config_repo):
    stage_config(config_repo, '[tool.ruff.lint]\nignore = ["F401"]\n')
    blob = git(config_repo, "rev-parse", ":pyproject.toml")
    path = config_repo / ".git" / "objects" / blob[:2] / blob[2:]
    path.rename(path.with_name(path.name + ".retained"))
    with pytest.raises(GitError, match="cat-file blob"):
        git_closing_diff_reader(config_repo)(STAGED)


def test_configuration_failure_emits_cli_error_and_nonzero_status(config_repo, tmp_path, monkeypatch, capsys):
    import audit_attribution

    stage_config(config_repo, "[malformed\n")
    pass_dir, _ = write_pass(tmp_path, [])
    skill = tmp_path / "skill"
    skill.mkdir()
    rubric = tmp_path / "rubric.md"
    rubric.write_text("rubric\n")
    monkeypatch.setattr(audit_attribution, "resolve", lambda _: {BEAD: STAGED})
    result = main([str(pass_dir), "--root", str(config_repo), "--skill", str(skill), "--rubric", str(rubric)])
    assert result == 3
    assert "IGNORE-CONFIG-FAILED" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ('[tool.ruff]\nignore = ["F401", "F841"]', '[tool.ruff.lint]\nextend-ignore = ["F841", "F401", "F401"]'),
        (
            '[tool.ruff.per-file-ignores]\n"*.py" = ["F401"]',
            '[tool.ruff.lint.extend-per-file-ignores]\n"*.py" = ["F401"]',
        ),
        ('[tool.codespell]\nignore-words-list = "aci,fro"', '[tool.codespell]\nignore-words-list = ["fro", "aci"]'),
        (
            '[tool.pytest.ini_options]\nfilterwarnings = ["error", "ignore::UserWarning"]',
            '[tool.pytest]\nfilterwarnings = [\n "error",\n "ignore::UserWarning",\n]',
        ),
        ('[tool.pytest]\nfilterwarnings = ["i"]', '[tool.pytest]\nfilterwarnings = ["ignore::Warning::0"]'),
        ('[tool.pytest.ini_options]\naddopts = "-Wi"', '[tool.pytest]\naddopts = ["--pythonwarnings=ignore"]'),
        ('[tool.ty.rules]\ninvalid-argument-type = "warn"', '[tool.ty.rules]\ninvalid-argument-type = "error"'),
        ('[tool.pytest]\ntestpaths = ["tests"]', '[tool.pytest]\ntestpaths = ["tests/unit"]'),
    ],
)
def test_semantic_noops_and_ordinary_settings_do_not_add_suppressions(config_repo, before, after):
    commit_config(config_repo, before + "\n")
    stage_config(config_repo, after + "\n")
    assert git_closing_diff_reader(config_repo)(STAGED).ignore_adds == 0


def test_removing_modern_ruff_override_exposes_legacy_suppression(config_repo):
    before = '[tool.ruff]\nignore = ["F401"]\n[tool.ruff.lint]\nignore = []\n'
    after = '[tool.ruff]\nignore = ["F401"]\n'
    commit_config(config_repo, before)
    stage_config(config_repo, after)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 1
    assert rederive(diff)[0]["severity"] == "BLOCKING"


def test_reordering_warning_filters_keeps_order_context_in_suppression_comparison(config_repo):
    before = '[tool.pytest.ini_options]\nfilterwarnings = ["ignore::UserWarning", "error::UserWarning"]\n'
    after = '[tool.pytest.ini_options]\nfilterwarnings = ["error::UserWarning", "ignore::UserWarning"]\n'
    commit_config(config_repo, before)
    stage_config(config_repo, after)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 1
    assert rederive(diff)[0]["severity"] == "BLOCKING"


@pytest.mark.parametrize(
    "option",
    [
        "-Wignore::UserWarning",
        "-W ignore::UserWarning",
        "--pythonwarnings=ignore::UserWarning",
        "--pythonwarnings i::UserWarning",
    ],
)
def test_cli_warning_ignore_broadens_configured_warning_error(config_repo, option):
    before = '[tool.pytest.ini_options]\nfilterwarnings = ["error::UserWarning"]\n'
    commit_config(config_repo, before)
    stage_config(config_repo, before + f'addopts = "{option}"\n')
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 1
    assert rederive(diff)[0]["severity"] == "BLOCKING"


def test_reordering_cli_warning_filters_retains_order_context(config_repo):
    before = '[tool.pytest]\naddopts = ["-Wignore::UserWarning", "-Werror::UserWarning"]\n'
    after = '[tool.pytest]\naddopts = ["-Werror::UserWarning", "-Wignore::UserWarning"]\n'
    commit_config(config_repo, before)
    stage_config(config_repo, after)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 1
    assert rederive(diff)[0]["severity"] == "BLOCKING"


def test_ty_override_scope_growth_is_a_new_suppression_declaration(config_repo):
    before = (
        '[[tool.ty.overrides]]\ninclude = ["tests/unit"]\n[tool.ty.overrides.rules]\ninvalid-argument-type = "ignore"\n'
    )
    after = before.replace('"tests/unit"', '"tests/**"')
    commit_config(config_repo, before)
    stage_config(config_repo, after)
    diff = git_closing_diff_reader(config_repo)(STAGED)
    assert diff.ignore_adds == 1
    assert rederive(diff)[0]["severity"] == "BLOCKING"


def test_ignore_removal_and_duplicates_do_not_count_as_growth():
    before = pyproject_ignores('[tool.ruff.lint]\nignore = ["F401", "F841"]')
    after = pyproject_ignores('[tool.ruff.lint]\nignore = ["F401", "F401"]')
    assert len(after - before) == 0


def write_pass(tmp_path, findings):
    pass_dir = tmp_path / "passes" / "2026-08-26T16-29-01Z"
    bead_dir = pass_dir / "beads" / BEAD
    bead_dir.mkdir(parents=True)
    (bead_dir / "theater.json").write_text(json.dumps(theater(*findings), indent=2) + "\n")
    (bead_dir / "spec.json").write_text(json.dumps({"bead_id": BEAD, "items": []}))
    (bead_dir / "show.json").write_text(json.dumps({"id": BEAD, "status": "closed"}))
    return pass_dir, bead_dir


def anti_theater_score(bead_dir, _synthesis, _prior):
    """Stands in for score-bead.py, whose only input from the corrector is theater.json."""
    summary = json.loads((bead_dir / "theater.json").read_text())["summary"]
    total = 1000 - 350 * summary["BLOCKING"] - 15 * summary["MAJOR"]
    return {"bead_id": bead_dir.name, "score": total, "false_closed": total < 700}


# The two shas a mutated flip-vs-mention rule can pick between: the bead's own
# closing commit is clean, while the later commit that merely rewrites its row is an
# empty diff that grew an ignore list, and scores 635 against a threshold of 700.
DIFF_BY_SHA = {
    CLOSING_SHA: ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0),
    LATER_SHA: ClosingDiff(LATER_SHA, files_changed=0, ignore_adds=5),
}


def run_correction(pass_dir, log_text):
    resolutions = history_closings(log_text)
    return correct_pass(
        pass_dir,
        resolutions=resolutions,
        diff_for=lambda resolution: DIFF_BY_SHA.get(resolution),
        score=anti_theater_score,
        prior=None,
    )


def test_the_corrected_verdict_does_not_move_when_an_unrelated_commit_lands(tmp_path):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    uncorrected = (bead_dir / "theater.json").read_text()
    history = closing_chunk(CLOSING_SHA, BEAD)

    first = run_correction(pass_dir, history)
    theater_after_first = (bead_dir / "theater.json").read_text()

    (bead_dir / "theater.json").write_text(uncorrected)
    grown = (
        mentioning_chunk(LATER_SHA, closes="cairn-cue", mentions=BEAD)
        + mentioning_chunk(MENTIONING_SHA, closes="cairn-us2", mentions=BEAD)
        + history
    )
    second = run_correction(pass_dir, grown)

    assert [verdict.split(" → ")[-1] for _, verdict, _ in first] == ["score 1000"]
    assert [v.split(" → ")[-1] for _, v, _ in second] == ["score 1000"]
    assert (bead_dir / "theater.json").read_text() == theater_after_first


def test_a_bead_no_commit_closed_is_reported_unresolved_and_keeps_no_attributed_finding(tmp_path):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    ((bead_id, verdict, _),) = run_correction(pass_dir, closing_chunk(CLOSING_SHA, "cairn-other"))
    written = json.loads((bead_dir / "theater.json").read_text())
    assert bead_id == BEAD
    assert verdict.startswith("UNRESOLVED")
    assert written["findings"] == []
    assert written["commit_attribution"]["closing_commit"] == UNKNOWN


def test_the_scorers_false_closed_flag_is_what_the_verdict_reports(tmp_path):
    pass_dir, _ = write_pass(tmp_path, [MISATTRIBUTED])
    results = correct_pass(
        pass_dir,
        resolutions={BEAD: CLOSING_SHA},
        diff_for=lambda _r: ClosingDiff(CLOSING_SHA, files_changed=0, ignore_adds=9),
        score=anti_theater_score,
        prior=None,
    )
    assert [failure for _, _, failure in results] == ["false-closed"]


def unverifiable_score(bead_dir, _synthesis, _prior):
    """Stands in for score-bead.py on a pass whose measured weight fell under the floor."""
    return {
        "bead_id": bead_dir.name,
        "score": 0,
        "false_closed": False,
        "unverifiable": True,
        "unmeasured": ["docs_etc", "test_depth", "tests"],
    }


def test_a_closed_bead_the_pass_could_not_verify_still_fails_the_gate(tmp_path):
    pass_dir, _ = write_pass(tmp_path, [MISATTRIBUTED])
    ((_, verdict, failure),) = correct_pass(
        pass_dir,
        resolutions={BEAD: CLOSING_SHA},
        diff_for=lambda _r: ClosingDiff(CLOSING_SHA, files_changed=7, ignore_adds=0),
        score=unverifiable_score,
        prior=None,
    )
    assert failure == "unverifiable"
    assert "the pass could not be verified" in verdict
    assert "docs_etc, test_depth, tests" in verdict
    assert re.search(r"score\s+\d", verdict) is None
    assert re.search(r"threshold\s+\d", verdict) is None


@pytest.mark.parametrize("absent", ["spec.json", "show.json", "theater.json"])
def test_a_bead_dir_the_pass_never_scored_is_left_alone(tmp_path, absent):
    pass_dir, bead_dir = write_pass(tmp_path, [MISATTRIBUTED])
    (bead_dir / absent).rename(bead_dir / f"{absent}.retained")
    assert run_correction(pass_dir, closing_chunk(CLOSING_SHA, BEAD)) == []
