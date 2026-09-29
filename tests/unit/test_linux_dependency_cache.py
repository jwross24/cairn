import hashlib
import json
import os
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import _linux_dependencies as dependencies
import pytest

from cairn import bundle, container, lean, solutionbuild


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


def _write_dependency_entry(gate, selected, cache, monkeypatch):
    monkeypatch.setattr(solutionbuild, "_dependency_packages", lambda *args: ())
    cache.mkdir(parents=True, exist_ok=True)
    entry = cache / dependencies.cache_key(gate, selected)
    project = entry / "project"
    project.mkdir(parents=True)
    for name, content in dependencies.project_files(gate).items():
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    record = {"inputs": dependencies.key_inputs(gate, selected), "inventory": dependencies.inventory(project)}
    (entry / "inventory.json").write_text(json.dumps(record, sort_keys=True) + "\n")
    return entry


def _exported_cache(gate, tmp_path, monkeypatch):
    selected = image(gate)
    cache = tmp_path / "cache"
    entry = _write_dependency_entry(gate, selected, cache, monkeypatch)
    monkeypatch.setattr(container, "image_id", lambda ctx, reference: selected.image_id)
    monkeypatch.setattr(container, "assert_pinned", lambda *args, **kwargs: None)
    dependencies.remember_image(gate, selected, cache)
    docker_calls = []

    def run_docker(ctx, *args, timeout_s=container.RUN_TIMEOUT_S):
        docker_calls.append((ctx, args))
        if args[:2] == ("image", "save"):
            (tmp_path / "last-save-id").write_text(args[-1])
            (Path(args[3])).write_bytes(b"docker-image-archive")
        return SimpleNamespace(rc=0, stdout="", stderr="")

    monkeypatch.setattr(container, "run_docker", run_docker)
    archive = tmp_path / "image.tar"
    dependencies.export_archive(gate, selected, cache, archive)
    return selected, cache, entry, archive, docker_calls


def _copy_cache_hit(gate, source, destination):
    destination.mkdir()
    key = next(path.name for path in source.iterdir() if path.is_dir() and path.name != "")
    shutil.copytree(source / key, destination / key, symlinks=True)
    shutil.copy2(dependencies.image_record(gate, source), dependencies.image_record(gate, destination))


def test_image_archive_round_trip_preserves_exact_id_and_dependency_inventory(gate, tmp_path, monkeypatch):
    selected, cache, entry, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    assert (tmp_path / "last-save-id").read_text() == selected.image_id
    assert docker_calls[0][1][-1] == selected.image_id
    metadata = json.loads(dependencies.archive_metadata_path(archive).read_text())
    assert metadata == {
        "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "archive_size": archive.stat().st_size,
        "container_identity": gate.container_identity,
        "image_id": selected.image_id,
        "layout": dependencies.ARCHIVE_LAYOUT,
        "schema": 1,
    }
    staged = list(tmp_path.glob("cairn-linux-dependency-archive-*"))
    assert len(staged) == 1
    assert not staged[0].is_relative_to(cache)
    assert (staged[0] / "image.tar").stat().st_ino == archive.stat().st_ino
    assert (staged[0] / "metadata.json").stat().st_ino == dependencies.archive_metadata_path(archive).stat().st_ino
    restored_cache = tmp_path / "restored-cache"
    _copy_cache_hit(gate, cache, restored_cache)
    restored_archive = tmp_path / "restored-image.tar"
    shutil.copy2(archive, restored_archive)
    shutil.copy2(dependencies.archive_metadata_path(archive), dependencies.archive_metadata_path(restored_archive))
    inspect_ids = []

    def image_id(ctx, reference):
        inspect_ids.append(reference)
        return selected.image_id

    monkeypatch.setattr(container, "image_id", image_id)
    imported = dependencies.import_archive(gate, restored_cache, restored_archive)
    assert imported.image_id == selected.image_id
    assert inspect_ids == [selected.image_id]
    assert docker_calls[-1][1] == ("load", "--input", str(restored_archive))
    destination = tmp_path / "private-project"
    dependencies.restore(gate, imported, restored_cache, destination)
    assert destination != restored_cache / dependencies.cache_key(gate, imported) / "project"
    assert dependencies.inventory(destination) == dependencies.inventory(entry / "project")


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("missing-archive", "archive-unavailable"),
        ("missing-metadata", "archive-metadata-unavailable"),
        ("digest", "archive-digest-mismatch"),
        ("image-id", "archive-identity-mismatch"),
        ("missing-image-id", "archive-metadata-invalid"),
    ],
)
def test_image_archive_import_rejects_invalid_hit_before_docker_load(gate, tmp_path, monkeypatch, mutation, message):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    restored_cache = tmp_path / "restored-cache"
    _copy_cache_hit(gate, cache, restored_cache)
    if mutation == "missing-archive":
        archive.rename(tmp_path / "missing-image.tar")
    elif mutation == "missing-metadata":
        dependencies.archive_metadata_path(archive).rename(tmp_path / "missing-image-metadata.json")
    elif mutation == "digest":
        archive.write_bytes(b"Xocker-image-archive")
    elif mutation == "image-id":
        metadata_path = dependencies.archive_metadata_path(archive)
        metadata = json.loads(metadata_path.read_text())
        metadata["image_id"] = "sha256:" + "2" * 64
        metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n")
    else:
        metadata_path = dependencies.archive_metadata_path(archive)
        metadata = json.loads(metadata_path.read_text())
        del metadata["image_id"]
        metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n")
    docker_calls.clear()
    with pytest.raises(dependencies.CacheRefused, match=message):
        dependencies.import_archive(gate, restored_cache, archive)
    assert docker_calls == []
    assert selected.image_id == "sha256:" + "1" * 64


def test_image_archive_import_refuses_loaded_wrong_id_and_pins(gate, tmp_path, monkeypatch):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    restored_cache = tmp_path / "restored-cache"
    _copy_cache_hit(gate, cache, restored_cache)
    monkeypatch.setattr(container, "image_id", lambda ctx, reference: "sha256:" + "2" * 64)
    with pytest.raises(dependencies.CacheRefused, match="import-image-validation-failed"):
        dependencies.import_archive(gate, restored_cache, archive)
    assert docker_calls[-1][1][:2] == ("load", "--input")
    monkeypatch.setattr(container, "image_id", lambda ctx, reference: selected.image_id)
    monkeypatch.setattr(
        container,
        "assert_pinned",
        lambda *args, **kwargs: (_ for _ in ()).throw(lean.LeanPinMismatch({}, {})),
    )
    with pytest.raises(dependencies.CacheRefused, match="import-image-validation-failed"):
        dependencies.import_archive(gate, restored_cache, archive)


def test_image_archive_import_requires_an_existing_image_record(gate, tmp_path, monkeypatch):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    restored_cache = tmp_path / "restored-cache"
    restored_cache.mkdir()
    shutil.copytree(
        cache / dependencies.cache_key(gate, selected), restored_cache / dependencies.cache_key(gate, selected)
    )
    docker_calls.clear()
    with pytest.raises(dependencies.CacheRefused, match="image-unavailable"):
        dependencies.import_archive(gate, restored_cache, archive)
    assert docker_calls == []


def test_image_archive_import_refuses_symlinked_image_record(gate, tmp_path, monkeypatch):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    restored_cache = tmp_path / "restored-cache"
    _copy_cache_hit(gate, cache, restored_cache)
    record = dependencies.image_record(gate, restored_cache)
    replacement = tmp_path / "record-copy.json"
    record.rename(replacement)
    record.symlink_to(replacement)
    docker_calls.clear()
    with pytest.raises(dependencies.CacheRefused, match="image-unavailable"):
        dependencies.import_archive(gate, restored_cache, archive)
    assert docker_calls == []


def test_image_archive_import_refuses_corrupt_dependencies_and_failed_load(gate, tmp_path, monkeypatch):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    restored_cache = tmp_path / "restored-cache"
    _copy_cache_hit(gate, cache, restored_cache)
    entry = restored_cache / dependencies.cache_key(gate, selected)
    project_file = entry / "project" / "lean-toolchain"
    project_file.write_text("tampered\n")
    with pytest.raises(dependencies.CacheRefused, match="import-entry-invalid"):
        dependencies.import_archive(gate, restored_cache, archive)
    assert docker_calls[-1][1][:2] == ("load", "--input")
    project_file.write_text(dependencies.project_files(gate)["lean-toolchain"])

    def failed_load(ctx, *args, timeout_s=container.RUN_TIMEOUT_S):
        docker_calls.append((ctx, args))
        return SimpleNamespace(rc=1, stdout="", stderr="load rejected")

    monkeypatch.setattr(container, "run_docker", failed_load)
    with pytest.raises(dependencies.CacheRefused, match="archive-load-failed:rc=1"):
        dependencies.import_archive(gate, restored_cache, archive)
    assert project_file.read_text() == dependencies.project_files(gate)["lean-toolchain"]


@pytest.mark.parametrize("target", ["archive", "metadata"])
def test_image_archive_export_refuses_conflict_without_overwriting(gate, tmp_path, monkeypatch, target):
    selected, cache, _, archive, docker_calls = _exported_cache(gate, tmp_path, monkeypatch)
    metadata_path = dependencies.archive_metadata_path(archive)
    if target == "archive":
        archive.write_bytes(b"unrelated archive")
    else:
        metadata = json.loads(metadata_path.read_text())
        metadata["layout"] = "other"
        metadata_path.write_text(json.dumps(metadata, sort_keys=True) + "\n")
    archive_before = archive.read_bytes()
    metadata_before = metadata_path.read_bytes()
    with pytest.raises(dependencies.CacheRefused, match=r"archive-(size|digest|layout)-mismatch"):
        dependencies.export_archive(gate, selected, cache, archive)
    assert len(docker_calls) == 1
    assert archive.read_bytes() == archive_before
    assert metadata_path.read_bytes() == metadata_before


def test_main_import_does_not_rebuild_a_malformed_declared_hit(gate, tmp_path, monkeypatch):
    _, cache, _, archive, _ = _exported_cache(gate, tmp_path, monkeypatch)
    archive.rename(tmp_path / "missing.tar")
    monkeypatch.setattr(bundle, "build", lambda *args: None)
    monkeypatch.setattr(bundle, "write_pin", lambda *args: None)
    monkeypatch.setattr(bundle.GateBundle, "open", lambda *args: gate)
    builds = []
    docker_calls = []
    monkeypatch.setattr(container, "build", lambda *args, **kwargs: builds.append(args))
    monkeypatch.setattr(container, "run_docker", lambda *args, **kwargs: docker_calls.append(args))
    monkeypatch.setattr(
        sys,
        "argv",
        ["linux-dependencies", "--cache", str(cache), "--import-archive", str(archive)],
    )
    with pytest.raises(dependencies.CacheRefused, match="archive-unavailable"):
        dependencies.main()
    assert builds == []
    assert docker_calls == []


def test_main_exports_only_after_preparation_and_image_record_publication(gate, tmp_path, monkeypatch, capsys):
    selected = image(gate)
    cache = tmp_path / "cache"
    _write_dependency_entry(gate, selected, cache, monkeypatch)
    events = []
    monkeypatch.setattr(bundle, "build", lambda *args: None)
    monkeypatch.setattr(bundle, "write_pin", lambda *args: None)
    monkeypatch.setattr(bundle.GateBundle, "open", lambda *args: gate)
    monkeypatch.setattr(container, "build", lambda *args, **kwargs: (events.append("build"), selected)[1])
    monkeypatch.setattr(container, "image_id", lambda ctx, reference: selected.image_id)
    monkeypatch.setattr(container, "assert_pinned", lambda *args, **kwargs: events.append("pins"))
    original_prepare = dependencies.prepare
    original_remember = dependencies.remember_image

    def prepare(*args):
        events.append("prepare")
        return original_prepare(*args)

    def remember(*args):
        events.append("remember")
        return original_remember(*args)

    def run_docker(ctx, *args, timeout_s=container.RUN_TIMEOUT_S):
        if args[0:2] == ("image", "save"):
            events.append("save")
            Path(args[3]).write_bytes(b"docker-image-archive")
        else:
            events.append("tag")
        return SimpleNamespace(rc=0, stdout="", stderr="")

    monkeypatch.setattr(dependencies, "prepare", prepare)
    monkeypatch.setattr(dependencies, "remember_image", remember)
    monkeypatch.setattr(container, "run_docker", run_docker)
    monkeypatch.setattr(
        sys,
        "argv",
        ["linux-dependencies", "--cache", str(cache), "--export-archive", str(tmp_path / "image.tar")],
    )
    dependencies.main()
    capsys.readouterr()
    assert events.index("prepare") < events.index("remember") < events.index("save")
    assert dependencies.image_record(gate, cache).is_file()
    assert (tmp_path / "image.tar").is_file()


def test_main_cache_mode_keeps_its_existing_prepare_path(gate, tmp_path, monkeypatch, capsys):
    selected = image(gate)
    cache = tmp_path / "cache"
    _write_dependency_entry(gate, selected, cache, monkeypatch)
    monkeypatch.setattr(bundle, "build", lambda *args: None)
    monkeypatch.setattr(bundle, "write_pin", lambda *args: None)
    monkeypatch.setattr(bundle.GateBundle, "open", lambda *args: gate)
    monkeypatch.setattr(container, "build", lambda *args, **kwargs: selected)
    monkeypatch.setattr(container, "assert_pinned", lambda *args, **kwargs: None)
    docker_calls = []

    def run_docker(ctx, *args, timeout_s=container.RUN_TIMEOUT_S):
        docker_calls.append(args)
        return SimpleNamespace(rc=0, stdout="", stderr="")

    monkeypatch.setattr(container, "run_docker", run_docker)
    monkeypatch.setattr(
        sys,
        "argv",
        ["linux-dependencies", "--cache", str(cache)],
    )
    dependencies.main()
    capsys.readouterr()
    assert dependencies.image_record(gate, cache).is_file()
    assert docker_calls == [
        ("tag", selected.image_id, f"cairn-linux-dependencies:{dependencies.cache_key(gate, selected)}")
    ]
    assert not (tmp_path / "image.tar").exists()


def test_main_rejects_simultaneous_archive_modes(gate, tmp_path, monkeypatch):
    monkeypatch.setattr(bundle, "build", lambda *args: None)
    monkeypatch.setattr(bundle, "write_pin", lambda *args: None)
    monkeypatch.setattr(bundle.GateBundle, "open", lambda *args: gate)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "linux-dependencies",
            "--cache",
            str(tmp_path / "cache"),
            "--export-archive",
            str(tmp_path / "one.tar"),
            "--import-archive",
            str(tmp_path / "two.tar"),
        ],
    )
    with pytest.raises(SystemExit, match="2"):
        dependencies.main()
