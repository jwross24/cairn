import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "tests"))

from _checks import scan_for_mocks  # noqa: E402


def test_integration_and_e2e_tests_use_no_mocks():
    assert scan_for_mocks(ROOT) == []


def test_planted_mock_import_is_flagged(pytester):
    pytester.syspathinsert(str(ROOT / "tests"))
    pytester.mkpydir("tests")
    (pytester.path / "tests" / "integration").mkdir()
    (pytester.path / "tests" / "integration" / "test_planted.py").write_text("from unittest.mock import MagicMock\n")
    pytester.makepyfile(
        """
        import pathlib
        from _checks import scan_for_mocks
        def test_scan_is_clean():
            assert scan_for_mocks(pathlib.Path(".")) == []
        """
    )
    result = pytester.runpytest("-p", "no:cacheprovider", "-q")
    result.assert_outcomes(failed=1)
    result.stdout.fnmatch_lines(["*MagicMock*"])
