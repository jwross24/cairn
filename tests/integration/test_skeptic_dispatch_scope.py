import asyncio
import json
import shutil
import sys
from dataclasses import asdict
from pathlib import Path

import pytest
from mcp.client import Client

from cairn import bundle, dispatch, skeptic, skeptic_tools, substrate

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _skeptic_isolation_seed import _make_skeptic_bundle, _seed


@pytest.mark.parametrize("kinds", [None, "all", ["prover_transcript"], ["ladder_table", "ladder_table"], [7]])
def test_invalid_pinned_scope_is_refused(tmp_path, clear_flags, kinds):
    gate = bundle.GateBundle.open(*_make_skeptic_bundle(tmp_path, clear_flags, "invalid", kinds))
    with substrate.Substrate.open(tmp_path / "invalid-substrate.sqlite") as writer:
        seeded = _seed(writer, gate, include_lean=False)
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(writer, gate, seeded["statement"].hash)


def test_missing_pinned_scope_does_not_grant_the_maximum(tmp_path, pinned_bundle):
    source = tmp_path / "unscoped-source"
    shutil.copytree(bundle.REPO_ROOT / "bundle", source, ignore=shutil.ignore_patterns("skeptic_scope.json"))
    gate = bundle.GateBundle.open(*pinned_bundle(src=source))
    with substrate.Substrate.open(tmp_path / "missing.sqlite") as writer:
        seeded = _seed(writer, gate, include_lean=False)
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(writer, gate, seeded["statement"].hash)


def test_in_memory_scope_mutation_cannot_widen_access(tmp_path, clear_flags):
    gate = bundle.GateBundle.open(*_make_skeptic_bundle(tmp_path, clear_flags, "narrow", ["lean_artifact"]))
    with substrate.Substrate.open(tmp_path / "narrow-memory.sqlite") as writer:
        seeded = _seed(writer, gate)
        gate.object("skeptic_scope")["evidence_kinds"].append("ladder_table")
        handle = skeptic.snapshot(writer, gate, seeded["statement"].hash)
        assert handle.read(seeded["evidence"]["lean_artifact"].hash)["verdict"] == "pass"
        with pytest.raises(skeptic.ScopedReadRefused):
            handle.read(seeded["evidence"]["ladder_table"].hash)


def test_dispatch_prepares_a_scoped_handle_and_records_rerun_artifacts(tmp_path, clear_flags):
    tools = [skeptic_tools.READ_NODE, skeptic_tools.REQUEST_RERUN]
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(tmp_path, clear_flags, "dispatch", sorted(skeptic.MAX_EVIDENCE_KINDS), tools=tools)
    )
    with substrate.Substrate.open(tmp_path / "dispatch-substrate.sqlite") as sub:
        seeded = _seed(sub, gate)
        prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(seeded["statement"].hash,))
        assert isinstance(prepared.skeptic_handle, skeptic.Handle)
        assert prepared.skeptic_handle.read(seeded["statement"].hash)["claim_id"] == seeded["statement"].claim_id
        with pytest.raises(skeptic.ScopedReadRefused):
            prepared.skeptic_handle.read(seeded["transcript_node"])
        record = dispatch._record(sub, prepared)
        assert dispatch.read(sub, record.dispatch_id).tool_allow_list == tuple(tools)
        request = asdict(prepared.skeptic_handle.request_rerun(seeded["evidence"]["ladder_table"].hash))
        scoped = skeptic_tools.ScopedTools(prepared.skeptic_handle, prepared.tools)
        read_hashes = (seeded["statement"].hash, seeded["evidence"]["ladder_table"].hash)

        async def read_scoped():
            async with Client(scoped.server["instance"]) as client:
                for digest in read_hashes:
                    response = await client.call_tool("read_node", {"node_hash": digest})
                    assert not response.is_error

        asyncio.run(read_scoped())
        assert tuple(scoped.read_node_hashes) == read_hashes
        finished = dispatch.DispatchResult(
            dispatch_id=record.dispatch_id,
            status="success",
            text="",
            session_id="record-fixture",
            observed_tools=tuple(tools),
            observed_skills=(),
            observed_plugins=(),
            cost_usd=None,
            at=record.at,
            rerun_requests=(request,),
            read_node_hashes=tuple(scoped.read_node_hashes),
        )
        dispatch._write(sub, dispatch.RESULT, finished, (record.hash,))
        assert dispatch.result(sub, record.dispatch_id) == finished
        stored = sub.conn.execute(
            "SELECT record_json FROM worker_results WHERE dispatch_id = ?", (record.dispatch_id,)
        ).fetchone()
        assert json.loads(stored["record_json"])["rerun_requests"] == [request]
        assert json.loads(stored["record_json"])["read_node_hashes"] == list(read_hashes)


@pytest.mark.parametrize("handed", ["empty", "transcript", "statement_and_transcript", "two_statements"])
def test_scoped_dispatch_refuses_unfiltered_handed_nodes(tmp_path, clear_flags, handed):
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(
            tmp_path, clear_flags, "handed", sorted(skeptic.MAX_EVIDENCE_KINDS), tools=[skeptic_tools.READ_NODE]
        )
    )
    with substrate.Substrate.open(tmp_path / "handed-substrate.sqlite") as sub:
        seeded = _seed(sub, gate)
        choices = {
            "empty": (),
            "transcript": (seeded["transcript_node"],),
            "statement_and_transcript": (seeded["statement"].hash, seeded["transcript_node"]),
            "two_statements": (seeded["statement"].hash, seeded["other_statement"].hash),
        }
        with pytest.raises(dispatch.DispatchRefused, match="exactly one handed claim statement"):
            dispatch._prepare(sub, gate, role="skeptic", node_ids=choices[handed])
        assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_dispatch_distinguishes_a_supported_tool_from_its_duplicate(tmp_path, clear_flags):
    gate = bundle.GateBundle.open(
        *_make_skeptic_bundle(tmp_path, clear_flags, "valid-tool", ["ladder_table"], tools=[skeptic_tools.READ_NODE])
    )
    duplicate = bundle.GateBundle.open(
        *_make_skeptic_bundle(
            tmp_path,
            clear_flags,
            "duplicate-tool",
            ["ladder_table"],
            tools=[skeptic_tools.READ_NODE, skeptic_tools.READ_NODE],
        )
    )
    with substrate.Substrate.open(tmp_path / "duplicate-substrate.sqlite") as sub:
        seeded = _seed(sub, gate, include_lean=False)
        prepared = dispatch._prepare(sub, gate, role="skeptic", node_ids=(seeded["statement"].hash,))
        assert prepared.tools == (skeptic_tools.READ_NODE,)
        with pytest.raises(dispatch.DispatchRefused, match="duplicate worker tool"):
            dispatch._prepare(sub, duplicate, role="skeptic", node_ids=(seeded["statement"].hash,))


def test_empty_rerun_artifacts_preserve_record_bytes():
    fields = {
        "dispatch_id": "record-fixture",
        "status": "success",
        "text": "",
        "session_id": "session-fixture",
        "observed_tools": (),
        "observed_skills": (),
        "observed_plugins": (),
        "cost_usd": None,
        "at": "2026-09-08T00:00:00+00:00",
    }
    result = dispatch.DispatchResult(
        "record-fixture", "success", "", "session-fixture", (), (), (), None, "2026-09-08T00:00:00+00:00"
    )
    assert result.rerun_requests == ()
    assert result.as_dict() == fields
    assert result.hash == substrate.node_hash_for("worker_result", bundle.canonical_bytes("worker_result", fields))


def test_a_handed_bundle_that_is_not_the_pinned_bundle_is_refused(tmp_path, clear_flags):
    bundle_path, pin_path = _make_skeptic_bundle(tmp_path, clear_flags, "pinned-narrow", ["lean_artifact"])
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    widened = json.dumps({"evidence_kinds": sorted(skeptic.MAX_EVIDENCE_KINDS)}).encode()
    forged_rows = [
        bundle._row(kind, bundle.canonical_bytes(kind, json.loads(widened)))
        if kind == "skeptic_scope"
        else (kind, canonical, digest)
        for kind, canonical, digest in gate.rows
    ]
    forged_hash = bundle.bundle_hash(forged_rows)
    forged = bundle.GateBundle(bundle_path, pin_path, forged_rows, forged_hash, forged_hash)
    assert forged.object("skeptic_scope")["evidence_kinds"] == sorted(skeptic.MAX_EVIDENCE_KINDS)
    with substrate.Substrate.open(tmp_path / "forged.sqlite") as writer:
        seeded = _seed(writer, gate)
        assert (
            skeptic.snapshot(writer, gate, seeded["statement"].hash).read(seeded["evidence"]["lean_artifact"].hash)[
                "verdict"
            ]
            == "pass"
        )
        with pytest.raises(skeptic.ScopedReadRefused, match="supplied gate bundle is not the pinned bundle"):
            skeptic.snapshot(writer, forged, seeded["statement"].hash)
