import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
SOLUTION_PLAN_EXACT_JOB_TIMEOUT = "timeout-minutes: ${{ matrix.lane == 'solution-plan-exact' && 45 || 20 }}"
SOLUTION_PLAN_EXACT_SESSION_DEADLINE = (
    "CAIRN_SESSION_DEADLINE: ${{ matrix.lane == 'solution-plan-exact' && '1962' || '1080' }}"
)
MATHLIB_CACHE = "Restore the pinned mathlib cache"
MATHLIB_SETUP = "Provision the pinned mathlib prerequisite"
LEAN_CACHE = "Restore the Lean toolchain"
LEAN_INSTALL = "Install the Lean toolchain"
LEAN_RESOLVE = "The Lean toolchain the gate resolves"
COMPARATOR_CACHE = "Restore the pinned comparator build"
COMPARATOR_BUILD = "Build pinned comparator and exporter"
GATES = "Gates"
LINUX_CACHE_KEY = "Identify Linux prerequisite cache"
LINUX_CACHE_RESTORE = "Restore Linux prerequisite cache"
LINUX_CACHE_IMPORT = "Import cached Linux prerequisites"
LINUX_CACHE_PREPARE = "Prepare Linux prerequisites"
LINUX_CACHE_EXPORT = "Export Linux prerequisites"
LINUX_CACHE_SAVE = "Save Linux prerequisite cache"
LINUX_CACHE_ACTION = "55cc8345863c7cc4c66a329aec7e433d2d1c52a9"
LINUX_CACHE_PATHS = (
    "${{ runner.temp }}/cairn-linux-prerequisites/dependencies",
    "${{ runner.temp }}/cairn-linux-prerequisites/image.tar",
    "${{ runner.temp }}/cairn-linux-prerequisites/image.tar.metadata.json",
)
LINUX_CACHE_INPUTS = (
    "bundle/Containerfile",
    "bundle/container.json",
    "bundle/lean.json",
    "lean/lake-manifest.json",
    "lean/lean-toolchain",
    "tests/_linux_dependencies.py",
    "src/cairn/container.py",
    "src/cairn/lean.py",
    "src/cairn/solutionbuild.py",
)
CONTAINER_LANES = (
    "lane: [container, container-image, container-replay-exact, container-replay-refusals, "
    "container-plan-exact, container-plan-proven, container-plan-refusals]"
)
MODULE = "Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point"
LEAN_SETUP_CONDITION = (
    "matrix.lane != 'python'"
    " && matrix.lane != 'python-integration'"
    " && matrix.lane != 'm0-lineage'"
    " && matrix.lane != 'm0-replay'"
    " && matrix.lane != 'm0-transcript'"
    " && matrix.lane != 'm0-boundaries'"
    " && matrix.lane != 'gateplan'"
)
LEAN_SETUP_STEPS = (
    LEAN_CACHE,
    LEAN_INSTALL,
    LEAN_RESOLVE,
    MATHLIB_CACHE,
    MATHLIB_SETUP,
    "Read comparator pins",
    "Provision comparator source",
    "Provision exporter source",
    COMPARATOR_CACHE,
    COMPARATOR_BUILD,
)
MACOS_LANES = (
    "lane: [python, python-integration, m0-lineage, m0-replay, m0-transcript, m0-boundaries, gateplan, lean-core, lean-replay, "
    "solution, solution-library-dlp, solution-library-finite-point, solution-library-binding, "
    "solution-plan-exact, solution-plan-refusals]"
)


def _steps(text: str) -> dict[str, int]:
    return {match.group(1): match.start() for match in re.finditer(r"^      - name: (.+)$", text, re.MULTILINE)}


def _step(text: str, name: str) -> str:
    marker = f"- name: {name}"
    assert marker in text, f"CI has no {name.lower()} step"
    return text.split(marker, 1)[1].split("\n      - ", 1)[0]


def _step_body(text: str, name: str) -> str:
    return _step(text, name).split("run: |\n", 1)[1]


def _assert_ci_lanes(text):
    assert CONTAINER_LANES in text
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in _step(text, "Linux container gates")
    assert MACOS_LANES in text
    assert "fail-fast: false" in text
    assert "continue-on-error:" not in text
    assert 'CAIRN_SESSION_DEADLINE: "1080"' in text
    macos_job = text.split("  check:\n", 1)[1]
    assert SOLUTION_PLAN_EXACT_JOB_TIMEOUT in macos_job
    assert SOLUTION_PLAN_EXACT_SESSION_DEADLINE in macos_job
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in _step(text, GATES)
    assert "name: cairn-failure-diagnostics-${{ matrix.lane }}" in text
    for name in (
        "Read comparator pins",
        "Provision comparator source",
        "Provision exporter source",
        "Build pinned comparator and exporter",
    ):
        assert f"if: {LEAN_SETUP_CONDITION}" in _step(text, name)
        assert _steps(text)[name] < _steps(text)[GATES]


def _assert_container_lane(text):
    job = text.split("  container:\n", 1)[1].split("  check:\n", 1)[0]
    assert "runs-on: ubuntu-24.04-arm" in job
    assert "timeout-minutes: 41" in {line.strip() for line in job.splitlines()}
    assert 'CAIRN_SESSION_DEADLINE: "1080"' in job
    assert "continue-on-error:" not in job
    assert "uv sync --locked --all-groups" in job
    assert "pari-gp libpari-dev" in job
    assert "br sync --import-only" in job
    assert CONTAINER_LANES in job
    assert "fail-fast: false" in job
    assert "name: cairn-failure-diagnostics-${{ matrix.lane }}" in job
    step = _step(job, "Linux container gates")
    assert 'run: scripts/check.sh --ci-lane "${{ matrix.lane }}"' in step
    assert "if:" not in step
    types = _step(job, "Linux adapter types")
    assert "ty check --python-platform linux" in types
    for path in (
        "src/cairn/container.py",
        "src/cairn/lean.py",
        "src/cairn/solutionbuild.py",
        "src/cairn/solutionchecks.py",
        "tests/_linux_dependencies.py",
        "tests/integration/test_container_statement_hash.py",
        "tests/integration/test_lean_container.py",
    ):
        assert path in types
    assert "if:" not in types
