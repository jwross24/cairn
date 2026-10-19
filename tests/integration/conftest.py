import json
from pathlib import Path

import pytest
from _substrate_helpers import open_writer

from cairn import attest, ladderplan


@pytest.fixture
def writer(tmp_path):
    sub = open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def attest_path(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "f" * 64)
    return path


@pytest.fixture
def plan():
    return ladderplan.LadderPlan.load(
        json.loads((Path(__file__).resolve().parents[2] / "bundle" / "ladder_plan.json").read_text())
    )
