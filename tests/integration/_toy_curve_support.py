import json
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest

from cairn import bundle, cli

PLATFORM_SKIP = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="pinned_bundle pins through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

TRANSCRIPT_GOLDEN = "toy_curve_selftest_transcript"
FLOOR_GOLDEN = "toy_curve_floor"
CERTIFICATE_GOLDEN = "toy_curve_certificate"
GOLDENS = Path(__file__).resolve().parent.parent / "goldens"


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _paths(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    return (
        (
            "--bundle",
            str(bundle_path),
            "--pin",
            str(pin_path),
            "--db",
            str(tmp_path / "substrate.sqlite"),
        ),
        bundle_path,
        pin_path,
    )


def _config(bundle_path, pin_path):
    return bundle.GateBundle.open(bundle_path, pin_path).verifier_config()


def _writable_copy(source, destination):
    shutil.copy(source, destination)
    Path(destination).chmod(0o644)
    return destination


def _edit_one_row(path, kind="tiers"):
    conn = sqlite3.connect(str(path))
    conn.execute("UPDATE objects SET canonical = ? WHERE kind = ?", (b"tampered", kind))
    conn.commit()
    conn.close()


def _certificate_rows(db_path):
    if not Path(db_path).exists():
        return []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return conn.execute("SELECT * FROM skill_certificates").fetchall()
    finally:
        conn.close()


def _records(log_path, event):
    return [
        json.loads(line)
        for line in log_path.read_text().splitlines()
        if line.strip() and json.loads(line).get("event") == event
    ]
