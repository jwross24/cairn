import asyncio
import json
from pathlib import Path

import pytest

from cairn import bundle, dispatch, roles
from cairn.substrate import Substrate, blob_hash

ROLE = {
    "template": roles.SKEPTIC,
    "tools": [],
    "model": "claude-haiku-4-5-20251001",
    "max_turns": 1,
    "timeout_s": 120,
}


def _source(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    for path in (bundle.REPO_ROOT / "bundle").glob("*.json"):
        (source / path.name).write_text(path.read_text())
    (source / "worker_roles.json").write_text(json.dumps({"skeptic": ROLE}))
    return source


def _build(source, directory):
    directory.mkdir(parents=True, exist_ok=True)
    path, pin = directory / "gate-bundle.sqlite", directory / "gate-bundle.pin"
    bundle.build(source, path)
    pin.write_text(bundle.bundle_hash(bundle.read_rows(path)) + "\n")
    return bundle.GateBundle.open(path, pin)


@pytest.fixture
def arena(tmp_path):
    source = _source(tmp_path)
    gate_bundle = _build(source, tmp_path / "pinned")
    with Substrate.open(tmp_path / "substrate.sqlite") as sub:
        node = sub.put_node("worker_input", b"a handed problem")
        yield sub, source, gate_bundle, node


def test_the_dispatch_record_names_the_template_hash_it_ran(arena):
    sub, _, gate_bundle, node = arena
    text, digest = roles.load(gate_bundle, roles.SKEPTIC)
    record = dispatch._record(sub, dispatch._prepare(sub, gate_bundle, role="skeptic", node_ids=(node,)))
    assert record.role_template_hash == digest == blob_hash(text.encode())
    assert sub.get_blob(record.role_template_hash) == text.encode()
    assert record.bundle_hash == gate_bundle.hash
    row = sub.conn.execute(
        "SELECT record_json FROM worker_dispatches WHERE dispatch_id = ?", (record.dispatch_id,)
    ).fetchone()
    assert json.loads(row["record_json"])["role_template_hash"] == digest


def test_a_template_edited_after_pinning_fails_closed_at_dispatch(arena):
    sub, source, gate_bundle, node = arena
    edited = dict(gate_bundle.object(roles.BUNDLE_KIND))
    edited[roles.SKEPTIC] = edited[roles.SKEPTIC] + "\n11. An item nobody pinned.\n"
    (source / "role_templates.json").write_text(json.dumps(edited))
    digest = bundle.build(source, gate_bundle.path)
    assert digest != gate_bundle.hash
    with pytest.raises(bundle.BundlePinMismatch):
        asyncio.run(dispatch.run(sub, gate_bundle, role="skeptic", node_ids=(node,)))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_a_repinned_template_edit_is_refused_against_the_handed_bundle(arena):
    sub, source, gate_bundle, node = arena
    edited = dict(gate_bundle.object(roles.BUNDLE_KIND))
    edited[roles.SKEPTIC] = "A checklist nobody reviewed."
    (source / "role_templates.json").write_text(json.dumps(edited))
    digest = bundle.build(source, gate_bundle.path)
    Path(gate_bundle.pin_path).write_text(digest + "\n")
    with pytest.raises(dispatch.DispatchRefused, match="dispatch bundle differs from the supplied gate bundle"):
        asyncio.run(dispatch.run(sub, gate_bundle, role="skeptic", node_ids=(node,)))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_a_role_naming_an_absent_template_is_refused_before_any_record(arena, tmp_path):
    sub, source, _, node = arena
    (source / "worker_roles.json").write_text(json.dumps({"skeptic": {**ROLE, "template": "absent_brief"}}))
    gate_bundle = _build(source, tmp_path / "absent")
    with pytest.raises(dispatch.DispatchRefused, match="carries no role_templates entry 'absent_brief'"):
        dispatch._prepare(sub, gate_bundle, role="skeptic", node_ids=(node,))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_a_planted_claim_reference_is_refused_before_any_record(arena, tmp_path):
    sub, source, _, node = arena
    statement = "cd" * 32
    edited = json.loads((source / "role_templates.json").read_text())
    edited[roles.SKEPTIC] = f"Audit statement {statement}."
    (source / "role_templates.json").write_text(json.dumps(edited))
    gate_bundle = _build(source, tmp_path / "planted")
    with pytest.raises(dispatch.DispatchRefused, match=f"names claim digest {statement}"):
        dispatch._prepare(sub, gate_bundle, role="skeptic", node_ids=(node,))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0
