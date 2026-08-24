import json
import sys
from pathlib import Path

import pytest

from cairn import cli, exits, keys, runner, substrate
from cairn.profile import Evaluation
from cairn.skills import toy_curve
from cairn.substrate import blob_hash

FIXTURES = str(Path(__file__).resolve().parent.parent / "fixtures")
BUNDLE_HASH = "ab" * 32
IDENTITY = toy_curve.identity_bundle()
TOOL_DIGESTS = IDENTITY["tool_digests"]


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def _recipe(seed=1, salt=""):
    return {
        "skill_identity_hash": keys.identity_bundle_hash(IDENTITY),
        "inputs": {},
        "seed": seed,
        "tool_versions": {"cypari2": TOOL_DIGESTS["cypari2"]},
        "container_digest": IDENTITY["container_digest"],
        "salt": salt,
    }


def _kw(tmp_path, evaluation=None, **overrides):
    base = {
        "bundle_hash": BUNDLE_HASH,
        "evaluation": evaluation or toy_curve.COST_PROFILE.evaluate(40),
        "ceiling_multiplier": 4,
        "tool_digests": TOOL_DIGESTS,
        "scratch_root": tmp_path / "runs",
        "env_extra": {"PYTHONPATH": FIXTURES},
    }
    base.update(overrides)
    return base


@pytest.fixture
def writer(tmp_path):
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        yield sub


def _fixture_launch(sub, tmp_path, module, **overrides):
    return runner.launch(
        sub,
        module,
        overrides.pop("recipe", _recipe(seed=7)),
        stdin_document={"n": 1},
        **_kw(tmp_path, **overrides),
    )


def test_a_real_forty_bit_launch_records_a_receipt_with_live_measurements(
    writer, tmp_path, db_snapshot
):
    before = db_snapshot(writer.conn, "before")
    attempt = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        **_kw(tmp_path),
    )
    after = db_snapshot(writer.conn, "after")
    assert attempt.status == "OK" and not attempt.served_from_cache
    assert after["attempts"] - before["attempts"] == 1
    assert after["receipts"] - before["receipts"] == 1

    receipt = writer.get_receipt(attempt.receipt_hash)
    assert receipt["cpu_user_s"] > 0
    assert receipt["wall_s"] > 0
    assert receipt["peak_rss_bytes"] > 0
    assert receipt["exit_status"] == 0
    assert receipt["gate_bundle_hash"] == BUNDLE_HASH
    assert receipt["end_mono"] > receipt["start_mono"]

    stdout_path = tmp_path / "runs" / attempt.attempt_id / "stdout"
    assert receipt["stdout_digest"] == blob_hash(stdout_path.read_bytes())
    assert receipt["stderr_digest"] == blob_hash(
        (tmp_path / "runs" / attempt.attempt_id / "stderr").read_bytes()
    )


def test_the_manifest_carries_the_skill_s_own_output_bytes(writer, tmp_path):
    attempt = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        **_kw(tmp_path),
    )
    stdout_bytes = (tmp_path / "runs" / attempt.attempt_id / "stdout").read_bytes()
    members = writer.conn.execute(
        "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = 'member'",
        (attempt.output_manifest_hash,),
    ).fetchall()
    assert [r["child_hash"] for r in members] == [blob_hash(stdout_bytes)]
    assert writer.get_blob(blob_hash(stdout_bytes)) == stdout_bytes
    assert toy_curve.ToyCurveOutput.from_json(stdout_bytes.decode()).bits == 40
    assert writer.manifest_blobs_present(attempt.output_manifest_hash)


def test_the_manifest_is_linked_to_its_recipe(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree")
    edges = {
        (r["parent_hash"], r["edge_kind"])
        for r in writer.lineage_of(attempt.output_manifest_hash)
    }
    assert (attempt.recipe_key, substrate.EDGE_OUTPUT_OF) in edges


def test_a_second_identical_launch_is_served_from_cache(writer, tmp_path, db_snapshot):
    first = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        **_kw(tmp_path),
    )
    before = db_snapshot(writer.conn, "before-second")
    second = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        **_kw(tmp_path),
    )
    after = db_snapshot(writer.conn, "after-second")
    assert second.served_from_cache and second.attempt_id == first.attempt_id
    assert after["attempts"] == before["attempts"]
    assert after["receipts"] == before["receipts"]


def test_skip_cache_lookup_records_a_fresh_attempt_that_agrees(writer, tmp_path):
    first = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        **_kw(tmp_path),
    )
    second = runner.launch(
        writer,
        "cairn.skills.toy_curve",
        _recipe(seed=1),
        stdin_document={"bits": 40, "seed": 1},
        skip_cache_lookup=True,
        **_kw(tmp_path),
    )
    assert not second.served_from_cache
    assert second.attempt_id != first.attempt_id
    assert second.output_manifest_hash == first.output_manifest_hash
    assert second.diverged == ()
    assert writer.get_attempt(second.attempt_id)["skip_cache_lookup"] == 1


def test_two_disagreeing_attempts_mark_the_recipe_non_reproducible(writer, tmp_path):
    first = _fixture_launch(writer, tmp_path, "skills.nondeterministic")
    second = _fixture_launch(
        writer, tmp_path, "skills.nondeterministic", skip_cache_lookup=True
    )
    assert second.output_manifest_hash != first.output_manifest_hash
    assert set(second.diverged) == {first.attempt_id, second.attempt_id}
    for attempt_id in second.diverged:
        assert writer.get_attempt(attempt_id)["inadmissible"] == 1
    for manifest in (first.output_manifest_hash, second.output_manifest_hash):
        assert writer.is_root("divergence", manifest)
    assert writer.serve(first.recipe_key) is None


def test_a_fixture_exiting_three_fails_and_its_receipt_carries_the_real_exit(
    writer, tmp_path
):
    attempt = _fixture_launch(writer, tmp_path, "skills.exit3")
    assert attempt.status == "FAIL"
    assert writer.get_receipt(attempt.receipt_hash)["exit_status"] == 3
    assert writer.serve(attempt.recipe_key) is None


def test_a_fixture_past_its_ceiling_is_killed_and_never_served(writer, tmp_path):
    attempt = _fixture_launch(
        writer,
        tmp_path,
        "skills.sleep2",
        evaluation=Evaluation(0.2, 0.2, 0.2),
    )
    assert attempt.status == "BUDGET_EXCEEDED"
    assert attempt.launch.timed_out
    assert 0.8 <= attempt.launch.wall_s < 2.0
    assert writer.get_receipt(attempt.receipt_hash)["exit_status"] < 0
    assert writer.serve(attempt.recipe_key) is None


def test_a_self_written_receipt_is_ignored(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.fake_receipt")
    assert attempt.status == "OK"
    assert "receipt" not in attempt.parsed.document
    receipt = writer.get_receipt(attempt.receipt_hash)
    assert receipt["cpu_user_s"] < 9999.0
    assert receipt["wall_s"] < 9999.0
    assert receipt["peak_rss_bytes"] > 1


def test_the_child_sees_no_substrate_path_and_no_inherited_secret(
    writer, tmp_path, monkeypatch
):
    monkeypatch.setenv("CAIRN_DB", str(tmp_path / "substrate.sqlite"))
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "hunter2")
    attempt = _fixture_launch(writer, tmp_path, "skills.print_env")
    assert attempt.status == "OK"
    seen = attempt.parsed.document["environ"]
    assert not any(name.startswith("CAIRN_DB") for name in seen)
    assert "AWS_SECRET_ACCESS_KEY" not in seen
    assert "VIRTUAL_ENV" not in seen and "PWD" not in seen
    assert str(tmp_path / "substrate.sqlite") not in json.dumps(attempt.parsed.document)
    assert attempt.parsed.document["argv"] == [
        str(tmp_path / "runs" / attempt.attempt_id / "scratch")
    ]


def test_a_megabyte_of_stderr_neither_deadlocks_nor_escapes_its_digest(
    writer, tmp_path
):
    attempt = _fixture_launch(writer, tmp_path, "skills.stderr_1mb")
    assert attempt.status == "OK"
    stderr_bytes = (tmp_path / "runs" / attempt.attempt_id / "stderr").read_bytes()
    assert len(stderr_bytes) == 1024 * 1024
    assert writer.get_receipt(attempt.receipt_hash)["stderr_digest"] == blob_hash(
        stderr_bytes
    )


def test_bytes_written_under_scratch_are_measured(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.scratch_1mb")
    assert attempt.status == "OK"
    receipt = writer.get_receipt(attempt.receipt_hash)
    assert receipt["scratch_bytes_written"] >= 1024 * 1024
    quiet = _fixture_launch(writer, tmp_path, "skills.disagree", recipe=_recipe(seed=8))
    assert writer.get_receipt(quiet.receipt_hash)["scratch_bytes_written"] == 0


def test_a_disagreeing_skill_keeps_its_document_as_an_artifact(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree")
    assert attempt.status == "DISAGREE"
    assert attempt.output_manifest_hash is not None
    assert writer.serve(attempt.recipe_key) is None
    assert attempt.parsed.document["status"] == "DISAGREE"


def test_a_malformed_document_fails_and_writes_no_manifest(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.malformed")
    assert attempt.status == "FAIL"
    assert attempt.output_manifest_hash is None
    assert not attempt.parsed.well_formed
    assert writer.get_attempt(attempt.attempt_id)["output_manifest_hash"] is None


def test_escrow_is_reserved_at_launch_and_left_unsettled(writer, tmp_path):
    evaluation = toy_curve.COST_PROFILE.evaluate(40)
    attempt = _fixture_launch(
        writer, tmp_path, "skills.disagree", evaluation=evaluation
    )
    row = writer.conn.execute(
        "SELECT * FROM escrow WHERE attempt_id = ?", (attempt.attempt_id,)
    ).fetchone()
    assert row["declared_production_cost"] == evaluation.expected_core_s
    assert row["declared_verification_cost"] == evaluation.expected_verification_core_s
    assert row["reserved"] == evaluation.expected_verification_core_s
    assert row["ceiling_multiplier"] == 4.0
    assert row["spent_at"] is None and row["released_at"] is None


def test_a_grant_that_cannot_cover_the_ceiling_refuses_before_spawning(
    writer, tmp_path, popen_spy
):
    evaluation = Evaluation(0.2, 0.2, 0.2)
    with pytest.raises(runner.BudgetRefused, match="cannot cover the ceiling"):
        _fixture_launch(
            writer,
            tmp_path,
            "skills.disagree",
            evaluation=evaluation,
            budget_remaining=0.5,
        )
    assert popen_spy == []
    assert writer.conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0


def test_the_argv_is_the_interpreter_and_the_named_module(writer, tmp_path, popen_spy):
    _fixture_launch(writer, tmp_path, "skills.disagree")
    assert len(popen_spy) == 1
    assert popen_spy[0][:3] == [sys.executable, "-m", "skills.disagree"]


def test_startup_scan_interrupts_an_orphaned_running_attempt(writer, tmp_path):
    key = writer.put_recipe(_recipe(seed=99))
    orphan = writer.start_attempt(key)
    assert runner.startup_scan(writer) == [orphan]
    assert writer.get_attempt(orphan)["status"] == "INTERRUPTED"
    assert writer.get_attempt(orphan)["ended_at"] is not None
    assert writer.serve(key) is None
    assert runner.startup_scan(writer) == []


def test_a_launch_scans_before_it_spawns(writer, tmp_path):
    key = writer.put_recipe(_recipe(seed=99))
    orphan = writer.start_attempt(key)
    _fixture_launch(writer, tmp_path, "skills.disagree")
    assert writer.get_attempt(orphan)["status"] == "INTERRUPTED"


def test_the_dry_run_reports_without_changing_anything(writer, tmp_path):
    key = writer.put_recipe(_recipe(seed=99))
    orphan = writer.start_attempt(key)
    assert runner.startup_scan(writer, dry_run=True) == [orphan]
    assert writer.get_attempt(orphan)["status"] == "RUNNING"
    assert writer.get_attempt(orphan)["ended_at"] is None
    assert runner.startup_scan(writer) == [orphan]
    assert writer.get_attempt(orphan)["status"] == "INTERRUPTED"


def test_the_startup_scan_command_reports_then_reports_nothing(tmp_path, capsys):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(_recipe(seed=99))
        orphan = sub.start_attempt(key)
    code, out, err = _run(["startup-scan", "--db", str(db), "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert document["interrupted"] == [orphan] and document["count"] == 1
    assert document["dry_run"] is False
    assert out.count("\n") == 1

    code, out, err = _run(["startup-scan", "--db", str(db), "--json"], capsys)
    assert code == exits.OK
    assert json.loads(out) == {
        "schema_version": cli.SCHEMA_VERSION,
        "command": "startup-scan",
        "interrupted": [],
        "count": 0,
        "dry_run": False,
    }


def test_the_startup_scan_command_honors_dry_run(tmp_path, capsys):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(_recipe(seed=99))
        orphan = sub.start_attempt(key)
    code, out, err = _run(
        ["startup-scan", "--db", str(db), "--dry-run", "--json"], capsys
    )
    assert code == exits.OK, err
    assert json.loads(out)["dry_run"] is True
    with substrate.Substrate.open(db, role="reader") as sub:
        assert sub.get_attempt(orphan)["status"] == "RUNNING"


def test_the_startup_scan_command_prints_bare_ids_without_json(tmp_path, capsys):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db) as sub:
        key = sub.put_recipe(_recipe(seed=99))
        orphan = sub.start_attempt(key)
    code, out, err = _run(["startup-scan", "--db", str(db)], capsys)
    assert code == exits.OK, err
    assert out == f"{orphan}\n"


def test_a_missing_substrate_names_a_command_that_exists(tmp_path, capsys):
    absent = tmp_path / "absent.sqlite"
    code, out, err = _run(["startup-scan", "--db", str(absent)], capsys)
    assert code == exits.ENVIRONMENT
    assert out == ""
    named = err.rsplit("run: ", 1)[1].strip().split()[1]
    assert named in {c.name for c in cli.commands()}


def test_a_sigterm_immune_child_is_escalated_to_sigkill(writer, tmp_path):
    attempt = _fixture_launch(
        writer,
        tmp_path,
        "skills.sigterm_immune",
        evaluation=Evaluation(0.125, 0.125, 0.125),
    )
    assert attempt.status == "BUDGET_EXCEEDED"
    assert attempt.launch.exit_status == -9
    assert attempt.launch.wall_s < 5.0
    assert writer.get_receipt(attempt.receipt_hash)["exit_status"] == -9


def test_the_group_sweep_leaves_no_stray_grandchild(writer, tmp_path):
    import os

    attempt = _fixture_launch(
        writer,
        tmp_path,
        "skills.forks_a_grandchild",
        evaluation=Evaluation(0.125, 0.125, 0.125),
    )
    assert attempt.status == "BUDGET_EXCEEDED"
    scratch = tmp_path / "runs" / attempt.attempt_id / "scratch"
    assert (scratch / "grandchild").exists()
    grandchild_pid = int((scratch / "grandchild_pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(grandchild_pid, 0)


def test_rusage_covers_the_child_and_what_the_child_reaped(writer, tmp_path):
    alone = _fixture_launch(
        writer, tmp_path, "skills.cpu_burner", recipe=_recipe(seed=21)
    )
    with_grandchild = _fixture_launch(
        writer,
        tmp_path,
        "skills.cpu_burner",
        recipe=_recipe(seed=22),
        env_extra={"PYTHONPATH": FIXTURES, "FIXTURE_GRANDCHILD": "1"},
    )
    assert alone.status == with_grandchild.status == "OK"
    assert with_grandchild.launch.cpu_user_s > alone.launch.cpu_user_s * 2


def test_a_recipe_marked_do_not_cache_is_never_served(writer, tmp_path):
    first = _fixture_launch(
        writer, tmp_path, "skills.disagree", recipe=_recipe(seed=31), do_not_cache=True
    )
    assert writer.serve(first.recipe_key) is None
    second = _fixture_launch(
        writer, tmp_path, "skills.disagree", recipe=_recipe(seed=31), do_not_cache=True
    )
    assert not second.served_from_cache and second.attempt_id != first.attempt_id


@pytest.mark.parametrize("replay", ["Verifiable", "AuditOnly"])
def test_a_non_replayable_recipe_is_never_marked_non_reproducible(
    writer, tmp_path, replay
):
    first = _fixture_launch(
        writer,
        tmp_path,
        "skills.nondeterministic",
        recipe=_recipe(seed=41),
        replay=replay,
    )
    second = _fixture_launch(
        writer,
        tmp_path,
        "skills.nondeterministic",
        recipe=_recipe(seed=41),
        replay=replay,
        skip_cache_lookup=True,
    )
    assert second.output_manifest_hash != first.output_manifest_hash
    assert second.diverged == ()
    assert writer.get_attempt(second.attempt_id)["inadmissible"] == 0
    assert writer.get_attempt(first.attempt_id)["replay_grade"] == replay


def test_an_attempt_carries_the_replay_grade_it_was_given(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree", replay="Verifiable")
    assert writer.get_attempt(attempt.attempt_id)["replay_grade"] == "Verifiable"
    assert writer.effective_grade(attempt.output_manifest_hash) == "Verifiable"
