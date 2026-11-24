import dataclasses
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from cairn import records
from cairn.substrate import HashMismatch, node_hash_for

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

KIND = "worker_dispatch"


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@dataclass(frozen=True)
class Named:
    dispatch_id: str
    named_hash: str

    def as_dict(self):
        return {"dispatch_id": self.dispatch_id}

    @property
    def hash(self):
        return self.named_hash


RECORD = records.RecordKind(
    kind=KIND,
    table="worker_dispatches",
    unique_by="dispatch_id",
    canonical=lambda value: records.as_json(value).encode(),
    index_row=lambda value: {"dispatch_id": value.dispatch_id, "record_json": records.as_json(value)},
    decode=lambda row: Named(row["dispatch_id"], row["record_hash"]),
    grade="AuditOnly",
    root="ledger_row",
)


def _true_hash(dispatch_id):
    return node_hash_for(KIND, records.as_json(Named(dispatch_id, "")).encode())


def test_a_put_record_reads_back_verified_with_its_node_and_root(writer):
    value = Named("d-1", _true_hash("d-1"))
    assert records.put(writer, RECORD, value) == value.hash
    assert records.find_one(writer, RECORD, dispatch_id="d-1") == value
    assert records.find_one(writer, RECORD, dispatch_id="d-2") is None
    roots = writer.conn.execute("SELECT root_kind FROM roots WHERE node_hash = ?", (value.hash,)).fetchall()
    assert [r["root_kind"] for r in roots] == ["ledger_row"]


def test_a_lookup_column_that_is_no_identifier_is_refused_before_any_query(writer):
    with pytest.raises(ValueError, match="no identifier"):
        records.find(writer, RECORD, **{"dispatch_id = dispatch_id OR 1": "x"})


def test_a_value_naming_another_content_address_writes_nothing(writer):
    nodes = writer.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
    with pytest.raises(HashMismatch, match="its canonical bytes hash to"):
        records.put(writer, RECORD, Named("d-1", "ab" * 32))
    assert writer.conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0] == nodes
    assert writer.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_a_row_inserted_around_the_writer_that_does_not_decode_is_a_content_address_refusal(writer):
    from_json = dataclasses.replace(
        RECORD, decode=lambda row: Named(json.loads(row["record_json"])["dispatch_id"], row["record_hash"])
    )
    digest = writer.put_node(KIND, b"{}")
    writer.conn.execute(
        "INSERT INTO worker_dispatches (dispatch_id, record_hash, record_json) VALUES ('f', ?, '{}')", (digest,)
    )
    writer.conn.commit()
    with pytest.raises(HashMismatch, match="worker_dispatches record f does not decode: KeyError"):
        records.find(writer, from_json, dispatch_id="f")
