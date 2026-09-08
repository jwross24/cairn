import os

import pytest


def test_snapshot_tracks_files_without_following_directory_links(tmp_path, isolation_snapshot):
    root = tmp_path / "root"
    nested = root / "deploy" / "nested"
    nested.mkdir(parents=True)
    regular = nested / "regular"
    regular.write_text("payload")
    outside = tmp_path / "outside"
    outside.mkdir()
    external = outside / "external"
    external.write_text("external")
    (root / "deploy" / "file_link").symlink_to(external)
    (root / "deploy" / "directory_link").symlink_to(outside, target_is_directory=True)
    (root / "deploy" / "broken_link").symlink_to(outside / "missing")
    (root / "deploy" / "loop").symlink_to(root / "deploy", target_is_directory=True)
    os.mkfifo(root / "deploy" / "fifo")
    (root / "var").write_text("file root")
    expected = {
        "deploy/nested/regular": (regular.stat().st_size, regular.stat().st_mtime_ns),
        "deploy/file_link": (external.stat().st_size, external.stat().st_mtime_ns),
    }
    assert isolation_snapshot(root) == expected
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    assert isolation_snapshot(alias) == expected
    assert isolation_snapshot(root / ".." / "root") == expected
    regular.write_text("different payload")
    assert isolation_snapshot(root) != expected


@pytest.mark.parametrize("name", [".doctor", "deploy", "var"])
def test_snapshot_follows_a_guarded_root_link(tmp_path, name, isolation_snapshot):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "file"
    target.write_text("content")
    (root / name).symlink_to(outside, target_is_directory=True)
    assert isolation_snapshot(root) == {f"{name}/file": (7, target.stat().st_mtime_ns)}


def test_snapshot_of_missing_roots_is_empty(tmp_path, isolation_snapshot):
    assert isolation_snapshot(tmp_path) == {}
    assert isolation_snapshot(tmp_path / "missing") == {}


def test_snapshot_ignores_unreadable_subdirectories(tmp_path, isolation_snapshot):
    hidden = tmp_path / "deploy" / "hidden"
    hidden.mkdir(parents=True)
    (hidden / "file").write_text("content")
    hidden.chmod(0)
    try:
        with pytest.raises(PermissionError):
            list(hidden.iterdir())
        assert isolation_snapshot(tmp_path) == {}
    finally:
        hidden.chmod(0o700)


def test_snapshot_ignores_inaccessible_and_cyclic_file_links(tmp_path, isolation_snapshot):
    deploy = tmp_path / "deploy"
    deploy.mkdir()
    hidden = tmp_path / "hidden"
    hidden.mkdir()
    (hidden / "file").write_text("content")
    denied = deploy / "denied"
    denied.symlink_to(hidden / "file")
    cycle = deploy / "cycle"
    cycle.symlink_to(cycle)
    hidden.chmod(0)
    try:
        with pytest.raises(PermissionError):
            denied.stat()
        with pytest.raises(OSError, match="Too many levels of symbolic links"):
            cycle.stat()
        assert isolation_snapshot(tmp_path) == {}
    finally:
        hidden.chmod(0o700)
