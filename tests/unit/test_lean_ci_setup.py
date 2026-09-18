import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MATHLIB_CACHE = "Restore the pinned mathlib cache"
MATHLIB_SETUP = "Provision the pinned mathlib prerequisite"
GATES = "Gates"
MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"


def _steps(text: str) -> dict[str, int]:
    return {match.group(1): match.start() for match in re.finditer(r"^      - name: (.+)$", text, re.MULTILINE)}


def _step(text: str, name: str) -> str:
    marker = f"- name: {name}"
    assert marker in text, f"CI has no {name.lower()} step"
    return text.split(marker, 1)[1].split("\n      - ", 1)[0]


def _step_body(text: str, name: str) -> str:
    return _step(text, name).split("run: |\n", 1)[1]


def _assert_mathlib_prerequisite(text: str) -> None:
    steps = _steps(text)
    assert MATHLIB_CACHE in steps, "CI has no mathlib cache step"
    assert MATHLIB_SETUP in steps, "CI has no mathlib prerequisite step"
    assert GATES in steps, "CI has no Gates step"
    assert steps[MATHLIB_CACHE] < steps[MATHLIB_SETUP] < steps[GATES]

    cache = _step(text, MATHLIB_CACHE)
    assert "actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9" in cache
    assert "lean/.lake" in cache
    assert "~/.cache/mathlib" in cache
    assert "runner.os" in cache
    assert "runner.arch" in cache
    for path in ("lean/lean-toolchain", "lean/lake-manifest.json", "lean/lakefile.toml"):
        assert path in cache

    setup_step = _step(text, MATHLIB_SETUP)
    setup = _step_body(text, MATHLIB_SETUP)
    assert "working-directory: lean" in setup_step
    assert "\n        if:" not in setup_step
    assert "set -euo pipefail" in setup
    assert 'toolchain="$(cat lean-toolchain)"' in setup
    assert f'"$HOME/.elan/bin/lake" "+$toolchain" exe cache get {MODULE}' in setup
    assert "git diff --exit-code -- lake-manifest.json" in setup


def test_ci_provisions_pinned_mathlib_before_the_gates():
    _assert_mathlib_prerequisite(WORKFLOW.read_text())


def test_ci_contract_refuses_a_missing_mathlib_prerequisite():
    broken = WORKFLOW.read_text().replace(f"- name: {MATHLIB_SETUP}", "- name: mathlib prerequisite absent", 1)
    with pytest.raises(AssertionError, match="no mathlib prerequisite step"):
        _assert_mathlib_prerequisite(broken)
