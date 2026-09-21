import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from types import SimpleNamespace

import _linux_dependencies as dependencies
import pytest

from cairn import bundle, container


@pytest.fixture
def gate(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


def image(gate):
    return container.Image(gate.container_identity, "unused", "sha256:" + "1" * 64, None)


def test_dependency_key_binds_image_pins_configuration_and_modules(gate, monkeypatch):
    original = image(gate)
    expected = dependencies.cache_key(gate, original)
    assert dependencies.cache_key(gate, replace(original, tag="different")) == expected
    assert dependencies.cache_key(gate, replace(original, image_id="sha256:" + "2" * 64)) != expected
    inputs = dependencies.key_inputs(gate, original)
    assert set(inputs) == {"layout", "image_id", "image_identity", "lean", "files", "modules"}
    for field in ("toolchain", "lean_commit", "mathlib_rev"):
        changed = SimpleNamespace(
            container_identity=gate.container_identity,
            lean={**gate.lean, field: "changed"},
            lake_manifest=gate.lake_manifest,
        )
        assert dependencies.cache_key(changed, original) != expected
    monkeypatch.setattr(dependencies, "MODULES", (*dependencies.MODULES, "Mathlib.Data.Nat.Basic"))
    assert dependencies.cache_key(gate, original) != expected
    with pytest.raises(dependencies.CacheRefused, match="image-mismatch"):
        dependencies.cache_key(gate, replace(original, identity="0" * 64))


@pytest.mark.parametrize("mutation", ["bytes", "extra", "missing", "mode", "link", "directory"])
def test_inventory_covers_ignored_artifacts_and_file_types(tmp_path, mutation):
    root = tmp_path / "project"
    root.mkdir()
    (root / ".gitignore").write_text("*.olean\n")
    artifact = root / "proof.olean"
    artifact.write_bytes(b"compiled")
    expected = dependencies.inventory(root)
    if mutation == "bytes":
        artifact.write_bytes(b"tampered")
    elif mutation == "extra":
        (root / "extra.olean").write_bytes(b"extra")
    elif mutation == "missing":
        artifact.rename(tmp_path / "removed.olean")
    elif mutation == "mode":
        artifact.chmod(0o755)
    elif mutation == "link":
        artifact.rename(root / "other.olean")
        artifact.symlink_to("other.olean")
    else:
        (root / "extra").mkdir()
    assert dependencies.inventory(root) != expected


@pytest.mark.parametrize("target", ["../outside", "/etc/hosts", "absent", "self"])
def test_inventory_refuses_escaping_or_broken_links(tmp_path, target):
    root = tmp_path / "project"
    root.mkdir()
    (tmp_path / "outside").write_bytes(b"external")
    (root / "self").symlink_to(target)
    with pytest.raises(dependencies.CacheRefused, match="link"):
        dependencies.inventory(root)


def test_inventory_refuses_special_files(tmp_path):
    os.mkfifo(tmp_path / "pipe")
    with pytest.raises(dependencies.CacheRefused, match="special-file:pipe"):
        dependencies.inventory(tmp_path)


def test_incomplete_or_corrupt_entries_cannot_restore(gate, tmp_path):
    selected = image(gate)
    cache = tmp_path / "cache"
    cache.mkdir()
    entry = cache / dependencies.cache_key(gate, selected)
    partial = cache / ".partial-unpublished"
    partial.mkdir()
    (partial / "inventory.json").write_text("{}")
    destination = tmp_path / "destination"
    with pytest.raises(dependencies.CacheRefused, match="incomplete"):
        dependencies.restore(gate, selected, cache, destination)
    assert not destination.exists()
    entry.mkdir()
    (entry / "inventory.json").write_text("not-json")
    with pytest.raises(dependencies.CacheRefused, match="incomplete"):
        dependencies.restore(gate, selected, cache, destination)
    (entry / "inventory.json").write_text(json.dumps({"inputs": {}, "inventory": {}}))
    with pytest.raises(dependencies.CacheRefused, match="key-mismatch"):
        dependencies.restore(gate, selected, cache, destination)
    project = entry / "project"
    project.mkdir()
    (project / "ignored.olean").write_bytes(b"unrecorded")
    (entry / "inventory.json").write_text(
        json.dumps({"inputs": dependencies.key_inputs(gate, selected), "inventory": {}})
    )
    with pytest.raises(dependencies.CacheRefused, match="content-mismatch"):
        dependencies.restore(gate, selected, cache, destination)
    assert not destination.exists()


def test_population_lock_refuses_a_second_writer_and_releases_after_failure(tmp_path):
    def acquire():
        with dependencies.population_lock(tmp_path, "key", timeout_s=0):
            return "acquired"

    with ThreadPoolExecutor(max_workers=1) as executor:

        def interrupt():
            with dependencies.population_lock(tmp_path, "key"):
                with pytest.raises(dependencies.CacheRefused, match="lock-timeout"):
                    executor.submit(acquire).result(timeout=5)
                raise ValueError("interrupted")

        with pytest.raises(ValueError, match="interrupted"):
            interrupt()
        assert executor.submit(acquire).result(timeout=5) == "acquired"


@pytest.mark.parametrize("record", [None, {}, {"identity": "wrong"}, {"image_id": "not-an-image"}])
def test_image_record_refuses_missing_or_invalid_identity_before_docker(gate, tmp_path, popen_spy, record):
    if record is not None:
        dependencies.image_record(gate, tmp_path).write_text(json.dumps(record))
    with pytest.raises(dependencies.CacheRefused, match="dependency-cache-image-"):
        dependencies.cached_image(gate, tmp_path)
    assert popen_spy == []
