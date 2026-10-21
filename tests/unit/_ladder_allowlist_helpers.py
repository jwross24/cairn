import json
import os
import sys

import pytest

from cairn import allowlist, bundle

BACKEND = os.path.realpath(sys.executable)
BACKEND_REEXEC = allowlist.reexec_target(BACKEND)
BACKEND_EXECS = tuple(sorted({BACKEND} | ({BACKEND_REEXEC} if BACKEND_REEXEC else set())))


def _hypothesis(**claimed):
    return {
        "target_family": "toy_curve",
        "claimed": {"model": "c_ln_p_tries", **claimed},
        "method_identity": {"interface_version": "toy_curve/1", "params": {}},
        "declared_parameter_ranges": {"bits": [40, 40]},
        "sampling_distribution": None,
    }


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def scratch(tmp_path):
    path = tmp_path / "scratch"
    path.mkdir()
    return path


@pytest.fixture
def instance(shipped, scratch):
    return allowlist.instantiate(shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch)


def _planted(pinned_bundle, tmp_path, obj, name="planted"):
    source = tmp_path / name
    source.mkdir()
    for path in (bundle.REPO_ROOT / "bundle").glob("*.json"):
        (source / path.name).write_text(path.read_text())
    (source / "allow_lists.json").write_text(json.dumps(obj))
    return bundle.GateBundle.open(*pinned_bundle(name=name, src=source))
