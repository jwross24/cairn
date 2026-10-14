import json

import pytest
from mcp.client import Client

from cairn import bundle, canary, claims, dispatch, exits, skeptic_tools, substrate, worker

SEED = "dispatch-command"


def _deployment(tmp_path, *, grounded=True):
    source = tmp_path / "source"
    source.mkdir()
    role = {
        "template": dispatch.SKEPTIC_HUNT_TEMPLATE,
        "tools": [skeptic_tools.READ_NODE],
        "model": "claude-offline-fixture",
        "max_turns": 1,
        "timeout_s": 1,
    }
    (source / "worker_roles.json").write_text(json.dumps({"skeptic": role}))
    (source / "role_templates.json").write_text(
        json.dumps({dispatch.SKEPTIC_HUNT_TEMPLATE: "1. Offline fixture item\n2. Offline fixture item"})
    )
    (source / "skeptic_scope.json").write_text(json.dumps({"evidence_kinds": []}))
    path, pin, db = tmp_path / "bundle.sqlite", tmp_path / "bundle.pin", tmp_path / "substrate.sqlite"
    pin.write_text(bundle.build(source, path) + "\n")
    with substrate.Substrate.open(db) as sub:
        statement = claims.ClaimStatement(
            "offline-fixture",
            1,
            "Offline fixture statement",
            {"target_family": "fixture", "size_interval": [1, 2], "param_ranges": {}, "assumption_set": []},
            {"units": {}, "cost_model": None},
        )
        claims.write_claim_statement(sub, statement)
        if grounded:
            plantings = tuple({"source": name, "token": canary.token(name, SEED)} for name in canary.SOURCES)
            canary.record(
                sub,
                form=canary.FORM_ECHO,
                plantings=plantings,
                observed="the worker echoed only its handed node " + canary.control_token(SEED),
                control_observed=" ".join(planted["token"] for planted in plantings),
                handed_control_detected=True,
            )
    argv = ["--role", "skeptic", "--statement", statement.hash, "--db", str(db), "--bundle", str(path)]
    return db, [*argv, "--pin", str(pin)], statement.hash


QUERIES = {
    "worker_dispatches": "SELECT * FROM worker_dispatches ORDER BY rowid",
    "worker_results": "SELECT * FROM worker_results ORDER BY rowid",
}


def _rows(db, table):
    with substrate.Substrate.open(db, role="reader") as sub:
        return [dict(row) for row in sub.conn.execute(QUERIES[table])]


def _scripted(text=None):
    async def execute(prepared, cwd):
        statement_hash = prepared.node_ids[0]
        scoped = skeptic_tools.ScopedTools(prepared.skeptic_handle, prepared.tools)
        async with Client(scoped.server["instance"]) as client:
            response = await client.call_tool("read_node", {"node_hash": statement_hash})
            assert not response.is_error
        reply = {
            "statement_hash": statement_hash,
            "verdict": "gap",
            "items": [
                {"id": i, "outcome": "gap", "answer": "Offline fixture only", "cited_node_hashes": [statement_hash]}
                for i in (1, 2)
            ],
        }
        return {
            "status": "success",
            "text": json.dumps(reply) if text is None else text,
            "session_id": "offline-fixture",
            "observed_tools": prepared.tools,
            "observed_skills": (),
            "observed_plugins": (),
            "cost_usd": None,
            "read_node_hashes": tuple(scoped.read_node_hashes),
        }

    return execute


def test_a_recorded_reply_prints_its_typed_record(tmp_path, monkeypatch, capsys):
    db, argv, statement_hash = _deployment(tmp_path)
    monkeypatch.setattr(worker, "_execute", _scripted())
    assert dispatch.main(argv) == exits.OK
    report = json.loads(capsys.readouterr().out)
    assert (report["role"], report["model"], report["status"]) == ("skeptic", "claude-offline-fixture", "success")
    assert report["read_node_count"] == 1
    assert report["typed_record"]["statement_hash"] == statement_hash
    assert report["typed_record"]["verdict"] == "gap"
    assert [item["id"] for item in report["typed_record"]["items"]] == [1, 2]
    assert len(_rows(db, "worker_dispatches")) == len(_rows(db, "worker_results")) == 1


def test_a_fenced_reply_is_recorded_and_refused_as_a_typed_record(tmp_path, monkeypatch, capsys):
    db, argv, _ = _deployment(tmp_path)
    monkeypatch.setattr(worker, "_execute", _scripted(text="```json\n{}\n```"))
    assert dispatch.main(argv) == exits.GATE_REFUSED
    captured = capsys.readouterr()
    assert json.loads(captured.out)["typed_record"] is None
    assert "refused: malformed skeptic_record: expected strict JSON" in captured.err
    assert len(_rows(db, "worker_results")) == 1


def test_a_worker_failure_is_recorded_as_an_error_result(tmp_path, monkeypatch, capsys):
    db, argv, statement_hash = _deployment(tmp_path)

    async def failing(prepared, cwd):
        raise RuntimeError("offline fixture failure")

    monkeypatch.setattr(worker, "_execute", failing)
    assert dispatch.main(argv) == exits.BACKEND
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "failed: RuntimeError: offline fixture failure; dispatch " in captured.err
    assert "holds an error result" in captured.err
    (result,) = _rows(db, "worker_results")
    assert json.loads(result["record_json"])["status"] == "error"
    with substrate.Substrate.open(db, role="reader") as sub:
        assert dispatch.skeptic_record(sub, result["dispatch_id"], statement_hash) is None


def test_an_error_result_names_what_the_worker_said(tmp_path, monkeypatch, capsys):
    db, argv, _ = _deployment(tmp_path)

    async def unauthenticated(prepared, cwd):
        return {
            "status": "error",
            "text": "Not logged in · Please run /login",
            "session_id": "offline-fixture",
            "observed_tools": prepared.tools,
            "observed_skills": (),
            "observed_plugins": (),
            "cost_usd": "0",
        }

    monkeypatch.setattr(worker, "_execute", unauthenticated)
    assert dispatch.main(argv) == exits.BACKEND
    captured = capsys.readouterr()
    assert json.loads(captured.out)["typed_record"] is None
    assert "holds an error result: Not logged in · Please run /login" in captured.err
    assert json.loads(_rows(db, "worker_results")[0]["record_json"])["status"] == "error"


def test_an_ungrounded_substrate_refuses_before_any_record(tmp_path, monkeypatch, capsys):
    db, argv, _ = _deployment(tmp_path, grounded=False)

    async def unreachable(prepared, cwd):
        pytest.fail("the worker ran on an ungrounded dispatch path")

    monkeypatch.setattr(worker, "_execute", unreachable)
    assert dispatch.main(argv) == exits.GATE_REFUSED
    assert "refused: the dispatch path holds no canary record" in capsys.readouterr().err
    assert _rows(db, "worker_dispatches") == []


def test_an_absent_substrate_is_refused_and_not_created(tmp_path, capsys):
    db, argv, _ = _deployment(tmp_path)
    absent = tmp_path / "absent.sqlite"
    argv[argv.index("--db") + 1] = str(absent)
    assert dispatch.main(argv) == exits.ENVIRONMENT
    assert "does not exist; a dispatch never creates one" in capsys.readouterr().err
    assert not absent.exists()


def test_an_unknown_role_and_a_missing_argument_are_refused(tmp_path, capsys):
    _, argv, _ = _deployment(tmp_path)
    argv[argv.index("--role") + 1] = "prover"
    assert dispatch.main(argv) == exits.GATE_REFUSED
    assert "refused: role is absent from the pinned worker_roles object" in capsys.readouterr().err
    assert dispatch.main(["--role", "skeptic"]) == exits.USER_INPUT
    assert "invalid:" in capsys.readouterr().err
