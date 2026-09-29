import os
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run_fixture_suite(pytester, source):
    pytester.makeconftest(
        f"import runpy\nclear_flags = runpy.run_path({str(ROOT / 'tests' / 'conftest.py')!r})['clear_flags']\n"
    )
    pytester.makepyfile(test_clear_flags=source)
    return pytester.runpytest_subprocess("-q", "-p", "no:cacheprovider", "--disable-warnings")


def test_clear_flags_restores_readonly_file_without_chflags_and_ignores_missing_paths(pytester):
    result = _run_fixture_suite(
        pytester,
        """
import os
from pathlib import Path

def test_clear_flags(clear_flags):
    root = Path(__file__).parent
    path = root / "readonly"
    path.write_bytes(b"payload")
    path.chmod(0o444)
    clear_flags(path)
    clear_flags(root / "missing")
    if hasattr(os, "chflags"):
        del os.chflags
""",
    )
    path = pytester.path / "readonly"
    try:
        assert result.ret == 0, result.stdout.str()
        result.assert_outcomes(passed=1)
        assert stat.S_IMODE(path.stat().st_mode) == 0o644
    finally:
        if path.exists():
            path.chmod(0o644)


def test_clear_flags_restores_platform_protection(pytester):
    result = _run_fixture_suite(
        pytester,
        """
import os
import stat
from pathlib import Path

def test_clear_flags(clear_flags):
    path = Path(__file__).parent / "protected"
    path.write_bytes(b"payload")
    path.chmod(0o444)
    if hasattr(os, "chflags") and hasattr(stat, "UF_APPEND"):
        os.chflags(path, stat.UF_APPEND)
    clear_flags(path)
""",
    )
    path = pytester.path / "protected"
    try:
        assert result.ret == 0, result.stdout.str()
        result.assert_outcomes(passed=1)
        assert stat.S_IMODE(path.stat().st_mode) == 0o644
        if hasattr(os, "chflags") and hasattr(stat, "UF_APPEND"):
            assert path.stat().st_flags & stat.UF_APPEND == 0
    finally:
        if path.exists():
            if hasattr(os, "chflags"):
                os.chflags(path, 0)
            path.chmod(0o644)
