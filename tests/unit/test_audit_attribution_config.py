import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from _audit_attribution_helpers import BEAD, write_pass

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from audit_attribution import (
    ClosingDiff,
    IgnoreConfigError,
    git_closing_diff_reader,
    main,
    pyproject_ignores,
    rederive,
)
from closing_commit import STAGED, GitError


def git(root, *args):
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _root_conftest(pytestconfig):
    # several conftest.py files share the bare module name "conftest"; the isolation guard reads the root one's globals
    path = Path(__file__).resolve().parents[1] / "conftest.py"
    return next(
        plugin
        for plugin in pytestconfig.pluginmanager.get_plugins()
        if getattr(plugin, "__file__", None) and Path(plugin.__file__).resolve() == path
    )


@pytest.fixture(scope="module")
def config_repo_template(tmp_path_factory, pytestconfig):
    conftest = _root_conftest(pytestconfig)
    allowed = conftest._allowed_argv0
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(conftest, "_allowed_argv0", lambda: {*allowed(), "git"})
        root = tmp_path_factory.mktemp("config-repo-template") / "repo"
        root.mkdir()
        git(root, "init", "-b", "main")
        git(root, "config", "core.hooksPath", "/dev/null")
        git(root, "config", "user.name", "Audit Test")
        git(root, "config", "user.email", "audit@example.test")
        (root / "tracked.txt").write_text("baseline\n")
        git(root, "add", "tracked.txt")
        git(root, "commit", "-m", "baseline")
    return root


@pytest.fixture
def config_repo(config_repo_template, tmp_path, monkeypatch, pytestconfig):
    conftest = _root_conftest(pytestconfig)
    allowed = conftest._allowed_argv0
    monkeypatch.setattr(conftest, "_allowed_argv0", lambda: {*allowed(), "git"})
    root = tmp_path / "repo"
    shutil.copytree(config_repo_template, root, symlinks=True)
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
