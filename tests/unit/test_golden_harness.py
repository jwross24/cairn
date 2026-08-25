from pathlib import Path

import pytest

CONFTEST_SRC = (Path(__file__).resolve().parent.parent / "conftest.py").read_text()


def test_differing_golden_fails_with_a_diff_and_writes_actual(assert_golden, tmp_path, monkeypatch):
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    golden = tmp_path / "x.golden"
    golden.write_text("old\n")
    with pytest.raises(AssertionError) as info:
        assert_golden(golden, "new\n")
    assert "-old" in str(info.value) and "+new" in str(info.value)
    assert (tmp_path / "x.golden.actual").read_text() == "new\n"


def test_update_goldens_rewrites_the_file(assert_golden, tmp_path, monkeypatch):
    monkeypatch.setenv("UPDATE_GOLDENS", "1")
    golden = tmp_path / "y.golden"
    golden.write_text("old\n")
    assert_golden(golden, "new\n")
    assert golden.read_text() == "new\n"


def test_isolation_guard_fails_a_test_that_writes_under_deploy(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import pathlib
        def test_writes_deploy():
            pathlib.Path("deploy").mkdir(exist_ok=True)
            pathlib.Path("deploy/leak").write_text("x")
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(passed=1, errors=1)
    assert result.ret != 0
    result.stdout.fnmatch_lines(["*IsolationViolation*deploy/leak*"])


def test_isolation_guard_fails_a_test_that_spawns_outside_the_allow_list(pytester, monkeypatch):
    monkeypatch.setenv("CAIRN_REPO_ROOT", str(pytester.path))
    pytester.makeconftest(CONFTEST_SRC)
    pytester.makepyfile(
        """
        import subprocess
        def test_spawns_echo():
            subprocess.run(["/bin/echo", "hi"], check=True)
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*IsolationViolation*/bin/echo*"])
