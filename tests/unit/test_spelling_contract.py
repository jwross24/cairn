import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GITHUB_PREDICATE = "cancelled()"


def test_github_api_spelling_is_exempt_but_british_prose_is_refused(tmp_path):
    api = tmp_path / "api.md"
    api.write_text(f"failure() || {GITHUB_PREDICATE}\n")
    prose = tmp_path / "prose.md"
    prose.write_text(f"The run is {GITHUB_PREDICATE[:-2]}.\n")
    accepted = subprocess.run(
        [sys.executable, "-m", "codespell_lib", str(api)], cwd=ROOT, capture_output=True, text=True
    )
    refused = subprocess.run(
        [sys.executable, "-m", "codespell_lib", str(prose)], cwd=ROOT, capture_output=True, text=True
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert refused.returncode == 65, refused.stdout + refused.stderr
    assert f"{GITHUB_PREDICATE[:-2]} ==> canceled" in refused.stdout
