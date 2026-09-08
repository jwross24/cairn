import inspect
import json
from dataclasses import FrozenInstanceError, fields

import pytest

from cairn.skeptic import Handle, RerunRequest, ScopedReadRefused, snapshot


def _handle():
    return Handle(
        statement_hash="s" * 64,
        _records=(
            (
                "e" * 64,
                json.dumps(
                    {
                        "kind": "ladder_table",
                        "recipe_hash": "r" * 64,
                        "certificate_hash": "c" * 64,
                        "repro_record_hash": "p" * 64,
                        "attempt_id": "a" * 64,
                    }
                ),
            ),
            ("s" * 64, json.dumps({"claim_id": "claim"})),
        ),
    )


def test_handle_reads_fresh_json_and_lists_only_serialized_scope():
    handle = _handle()
    assert handle.node_hashes == ("e" * 64, "s" * 64)
    first = handle.read("s" * 64)
    first["claim_id"] = "changed"
    assert handle.read("s" * 64) == {"claim_id": "claim"}
    assert not hasattr(handle, "conn")
    assert not hasattr(handle, "put_blob")


def test_handle_refuses_unknown_reads_and_builds_minimal_rerun_request():
    handle = _handle()
    with pytest.raises(ScopedReadRefused):
        handle.read("x" * 64)
    assert handle.request_rerun("e" * 64) == RerunRequest(
        statement_hash="s" * 64,
        evidence_hash="e" * 64,
        attempt_id="a" * 64,
        recipe_key="r" * 64,
    )


def test_handle_rerun_rejects_lean_or_incomplete_projection():
    with pytest.raises(ScopedReadRefused, match="Lean"):
        Handle(
            statement_hash="s" * 64,
            _records=(("e" * 64, json.dumps({"formal_statement_hash": "f" * 64, "verdict": "pass"})),),
        ).request_rerun("e" * 64)
    with pytest.raises(ScopedReadRefused, match="rerunnable"):
        Handle(
            statement_hash="s" * 64,
            _records=(
                (
                    "e" * 64,
                    json.dumps(
                        {
                            "kind": "ladder_table",
                            "recipe_hash": None,
                            "certificate_hash": None,
                            "repro_record_hash": None,
                            "attempt_id": None,
                        }
                    ),
                ),
            ),
        ).request_rerun("e" * 64)


def test_snapshot_has_no_scope_override_and_handle_carries_no_live_authority():
    assert tuple(inspect.signature(snapshot).parameters) == ("sub", "gate_bundle", "statement_hash")
    handle = _handle()
    assert {field.name for field in fields(handle)} == {"statement_hash", "_records"}
    assert all(isinstance(digest, str) and isinstance(payload, str) for digest, payload in handle._records)


@pytest.mark.parametrize("attribute", ["statement_hash", "_records"])
def test_handle_cannot_be_retargeted(attribute):
    with pytest.raises(FrozenInstanceError):
        setattr(_handle(), attribute, "forbidden")


@pytest.mark.parametrize("method", ["put_blob", "put_node", "start_attempt", "close_attempt"])
def test_handle_refuses_write_methods(method):
    with pytest.raises(AttributeError):
        getattr(_handle(), method)
