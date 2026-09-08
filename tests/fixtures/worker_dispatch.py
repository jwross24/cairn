import json

import pytest

from cairn import bundle
from cairn.substrate import Substrate

ECHO_TEXT = "CAIRN_DISPATCH_ECHO_738194"
TEMPLATE = "Return exactly the content of the first handed node, with no surrounding text."
ROLE = {
    "template": TEMPLATE,
    "tools": [],
    "model": "claude-haiku-4-5-20251001",
    "max_turns": 1,
    "timeout_s": 120,
}


def make_bundle(directory, role=None):
    source = directory / "source"
    source.mkdir()
    (source / "worker_roles.json").write_text(json.dumps({"echo": ROLE if role is None else role}))
    path, pin = directory / "bundle.sqlite", directory / "bundle.pin"
    bundle.build(source, path)
    pin.write_text(bundle.bundle_hash(bundle.read_rows(path)) + "\n")
    return bundle.GateBundle.open(path, pin)


@pytest.fixture
def arena(tmp_path):
    gate_bundle = make_bundle(tmp_path)
    with Substrate.open(tmp_path / "substrate.sqlite") as sub:
        node = sub.put_node("worker_input", ECHO_TEXT.encode())
        yield sub, gate_bundle, node
