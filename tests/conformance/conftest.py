import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "conformance"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

import skill_contract  # noqa: E402

RESULTS = {}


def pytest_terminal_summary(terminalreporter):
    if not RESULTS:
        return
    terminalreporter.section("skill contract conformance")
    terminalreporter.write_line(skill_contract.matrix(RESULTS))
