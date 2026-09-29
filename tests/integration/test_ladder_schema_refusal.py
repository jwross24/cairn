import sqlite3

import pytest

from cairn import substrate


def _snapshot(path):
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        master = sorted(connection.execute("SELECT type, name, tbl_name, sql FROM sqlite_master"))
        salts = tuple(connection.execute("SELECT * FROM salts ORDER BY seq"))
    finally:
        connection.close()
    sidecars = tuple(sorted((file.name, file.read_bytes()) for file in path.parent.glob(f"{path.name}-*")))
    return path.read_bytes(), master, salts, sidecars


@pytest.mark.parametrize("role", ["reader", "writer"])
def test_prior_ladder_column_definition_is_refused_without_mutating_the_store(tmp_path, role):
    shipped = substrate.SCHEMA_PATH.read_text()
    prior = shipped.replace("    gate_ops INTEGER,", "    gate_ops INTEGER NOT NULL,")
    assert prior != shipped
    database = tmp_path / "prior-ladder.sqlite"
    connection = sqlite3.connect(str(database), autocommit=True)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.executescript(prior)
    connection.execute(
        "INSERT INTO salts (class_key, salt, kind, verdict_ref) VALUES (?, ?, ?, ?)",
        ("ladder-schema", "sentinel", "gate_verdict", "sentinel-ref"),
    )
    connection.close()
    before = _snapshot(database)

    with pytest.raises(substrate.SchemaMismatch, match="ladder_trials: column definitions differ"):
        substrate.Substrate.open(database, role=role)

    assert _snapshot(database) == before
