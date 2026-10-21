import json
import os
import signal
import sqlite3
import subprocess
import sys
import time

import pytest

from cairn import cli, exits, keys, runner
from cairn.skills import toy_curve
from cairn.substrate import Substrate, WriterAlreadyOpen

IDENTITY = toy_curve.identity_bundle()

HOLDER = (
    "import sys, time\n"
    "from pathlib import Path\n"
    "from cairn import substrate\n"
    "sub = substrate.Substrate.open(sys.argv[1])\n"
    "Path(sys.argv[2]).write_text('ready')\n"
    "time.sleep(120)\n"
)


@pytest.fixture
def holder(tmp_path):
    procs = []

    def start(db):
        flag = tmp_path / f"ready-{len(procs)}"
        proc = subprocess.Popen([sys.executable, "-c", HOLDER, str(db), str(flag)])
        procs.append(proc)
        deadline = time.monotonic() + 60
        while not flag.exists():
            assert proc.poll() is None and time.monotonic() < deadline
            time.sleep(0.05)
        return proc

    yield start
    for proc in procs:
        proc.kill()
        proc.wait()


def _recipe():
    return {
        "skill_identity_hash": keys.identity_bundle_hash(IDENTITY),
        "inputs": {},
        "seed": 99,
        "tool_versions": {"cypari2": IDENTITY["tool_digests"]["cypari2"]},
        "container_digest": IDENTITY["container_digest"],
        "salt": "",
    }


def _seed_running_attempt(db):
    with Substrate.open(db) as sub:
        return sub.start_attempt(sub.put_recipe(_recipe()))


def test_a_second_process_cannot_open_a_writer_or_interrupt_the_live_attempt(tmp_path, holder):
    db = tmp_path / "substrate.sqlite"
    attempt = _seed_running_attempt(db)
    holder(db)
    with pytest.raises(WriterAlreadyOpen, match="another process"):
        Substrate.open(db)
    with Substrate.open(db, role="reader") as reader:
        assert reader.get_attempt(attempt)["status"] == "RUNNING"
        assert runner.startup_scan(reader, dry_run=True) == [attempt]


def test_a_symlinked_path_is_the_same_ownership_domain(tmp_path, holder):
    db = tmp_path / "substrate.sqlite"
    _seed_running_attempt(db)
    alias = tmp_path / "alias.sqlite"
    alias.symlink_to(db)
    holder(db)
    with pytest.raises(WriterAlreadyOpen, match="another process"):
        Substrate.open(alias)


def test_a_killed_owner_releases_ownership_and_the_orphan_is_recovered_once(tmp_path, holder):
    db = tmp_path / "substrate.sqlite"
    attempt = _seed_running_attempt(db)
    proc = holder(db)
    with pytest.raises(WriterAlreadyOpen):
        Substrate.open(db)
    os.kill(proc.pid, signal.SIGKILL)
    proc.wait()
    with Substrate.open(db) as sub:
        assert runner.startup_scan(sub) == [attempt]
        assert runner.startup_scan(sub) == []
        assert sub.get_attempt(attempt)["status"] == "INTERRUPTED"


def test_close_releases_ownership_to_a_later_writer(tmp_path):
    db = tmp_path / "substrate.sqlite"
    Substrate.open(db).close()
    Substrate.open(db).close()


def test_an_initialization_failure_releases_ownership(tmp_path):
    db = tmp_path / "substrate.sqlite"
    db.write_bytes(b"not a database file, but long enough to be refused as one" * 4)
    for _ in range(2):
        with pytest.raises(sqlite3.DatabaseError, match="not a database"):
            Substrate.open(db)


def test_the_startup_scan_command_refuses_a_live_owner_and_dry_run_still_reports(tmp_path, holder, capsys):
    db = tmp_path / "substrate.sqlite"
    attempt = _seed_running_attempt(db)
    holder(db)
    code = cli.main(["startup-scan", "--db", str(db), "--json"])
    assert code == exits.CONFLICT
    capsys.readouterr()
    code = cli.main(["startup-scan", "--db", str(db), "--dry-run", "--json"])
    out = capsys.readouterr().out
    assert code == exits.OK
    assert json.loads(out)["interrupted"] == [attempt]
    with Substrate.open(db, role="reader") as reader:
        assert reader.get_attempt(attempt)["status"] == "RUNNING"
