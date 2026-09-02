import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))

import _corpus  # noqa: E402


@pytest.fixture(scope="session")
def planted_registry():
    return _corpus.discover(HERE)


@pytest.fixture(scope="session")
def observations():
    return {}


@pytest.fixture
def observe(observations, tmp_path_factory):
    def run(entry, *, fresh=False):
        if entry.test_id in observations and not fresh:
            return observations[entry.test_id]
        root = tmp_path_factory.mktemp("planted")
        obs = _corpus.observe(entry, db_path=root / "substrate.sqlite", scratch_root=root / "runs")
        if not fresh:
            observations[entry.test_id] = obs
        return obs

    return run


@pytest.fixture
def rollup(planted_registry, observe):
    return _corpus.rollup(planted_registry, {e.test_id: observe(e) for e in planted_registry.entries})
