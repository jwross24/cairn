import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import attest, bundle, substrate

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "bundle"


def command(directory, src=SRC):
    return [sys.executable, "-m", "cairn.deployment", "--src", str(src), "--directory", str(directory)]


def state(path):
    metadata = path.lstat()
    content = str(path.readlink()) if path.is_symlink() else path.read_bytes() if path.is_file() else None
    return metadata.st_mode, getattr(metadata, "st_flags", None), content


def test_one_command_prepares_a_readable_fixture_deployment(tmp_path, clear_flags):
    directory = tmp_path / "deployment"
    pin = directory / "gate-bundle.pin"
    attestation = directory / "attestations.log"
    clear_flags(pin)
    clear_flags(attestation)
    completed = subprocess.run(command(directory), capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stderr
    document = json.loads(completed.stdout)
    assert document["bundle"] == str(directory / "gate-bundle.sqlite")
    assert document["pin"] == str(pin)
    assert document["attest"] == str(attestation)
    gate = bundle.GateBundle.open(document["bundle"], document["pin"])
    expected = bundle.bundle_hash(bundle.rows_for(bundle.source_objects(SRC)))
    assert document["bundle_hash"] == gate.hash == gate.pin_hash == expected
    canonical = attest.waiver_canonical(attest.fixture_waiver(gate.waiver_target()))
    assert document["waiver_offset"] == 0
    assert document["waiver_digest"] == substrate.blob_hash(canonical)
    assert attest.read_record(attestation, 0) == canonical
    assert attestation.read_bytes() == attest.frame(canonical)
    assert sorted(path.name for path in directory.iterdir()) == [
        "attestations.log",
        "gate-bundle.pin",
        "gate-bundle.sqlite",
    ]
    assert stat.S_IMODE(directory.stat().st_mode) == 0o700
    for path in (Path(document["bundle"]), pin):
        assert stat.S_IMODE(path.stat().st_mode) == 0o444
    if hasattr(os, "chflags"):
        assert pin.stat().st_flags & stat.UF_APPEND
        assert attestation.stat().st_flags & stat.UF_APPEND


@pytest.mark.parametrize("kind", ["directory", "file", "symlink", "dangling_symlink"])
def test_existing_destination_is_preserved(tmp_path, kind):
    directory = tmp_path / "deployment"
    target = tmp_path / "target"
    sentinel = tmp_path / "sentinel"
    sentinel.write_bytes(b"preserve these bytes")
    if kind == "directory":
        directory.mkdir(mode=0o700)
        (directory / "gate-bundle.sqlite").write_bytes(b"existing bundle")
    elif kind == "file":
        directory.write_bytes(b"existing destination")
    elif kind == "symlink":
        target.mkdir(mode=0o750)
        (target / "gate-bundle.pin").write_bytes(b"existing pin")
        directory.symlink_to(target, target_is_directory=True)
    else:
        directory.symlink_to(target, target_is_directory=True)
    paths = [directory, sentinel]
    if directory.is_dir():
        paths.extend(directory.iterdir())
    if target.exists():
        paths.append(target)
    before = {path: state(path) for path in paths}
    completed = subprocess.run(command(directory), capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert completed.stdout == ""
    refusal = json.loads(completed.stderr.splitlines()[-1])
    assert refusal["stage"] == "destination"
    assert refusal["retained"] == []
    assert {path: state(path) for path in paths} == before
    assert not (directory / "attestations.log").exists()


def test_concurrent_creators_cannot_replace_the_winner(tmp_path, clear_flags):
    directory = tmp_path / "deployment"
    clear_flags(directory / "gate-bundle.pin")
    clear_flags(directory / "attestations.log")
    processes = [subprocess.Popen(command(directory), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)]
    try:
        processes.append(
            subprocess.Popen(command(directory), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        )
        results = [(process, *process.communicate(timeout=30)) for process in processes]
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
    assert sorted(process.returncode for process, _, _ in results) == [0, 2]
    winner = next(json.loads(stdout) for process, stdout, _ in results if process.returncode == 0)
    loser = next(json.loads(stderr.splitlines()[-1]) for process, _, stderr in results if process.returncode == 2)
    assert loser["stage"] in ("destination", "create")
    assert loser["retained"] == []
    gate = bundle.GateBundle.open(winner["bundle"], winner["pin"])
    assert gate.hash == winner["bundle_hash"]
    assert (directory / "attestations.log").read_bytes() == attest.frame(
        attest.waiver_canonical(attest.fixture_waiver(gate.waiver_target()))
    )
    before = {path: state(path) for path in directory.iterdir()}
    completed = subprocess.run(command(directory), capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert {path: state(path) for path in directory.iterdir()} == before


@pytest.mark.parametrize("invalid", ["malformed_json", "missing_fixture", "invalid_fixture"])
def test_invalid_source_refuses_before_directory_creation(tmp_path, invalid):
    src = tmp_path / "source"
    src.mkdir()
    if invalid == "malformed_json":
        (src / "gate_plan.json").write_text("{")
    else:
        value = {"fixtures": {}} if invalid == "missing_fixture" else {"fixtures": {"waiver_hypothesis": {}}}
        (src / "gate_plan.json").write_text(json.dumps(value))
    directory = tmp_path / "deployment"
    completed = subprocess.run(command(directory, src), capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert completed.stdout == ""
    refusal = json.loads(completed.stderr.splitlines()[-1])
    assert refusal["stage"] == "preflight"
    assert refusal["retained"] == []
    assert not directory.exists()


def test_missing_parent_refuses_without_creating_paths(tmp_path):
    directory = tmp_path / "missing" / "deployment"
    completed = subprocess.run(command(directory), capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    assert json.loads(completed.stderr.splitlines()[-1])["stage"] == "create"
    assert not directory.parent.exists()
