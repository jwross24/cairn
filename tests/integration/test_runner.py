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


def test_a_real_forty_bit_launch_records_a_receipt_with_live_measurements(writer, tmp_path, db_snapshot):
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
    assert receipt["stderr_digest"] == blob_hash((tmp_path / "runs" / attempt.attempt_id / "stderr").read_bytes())


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
    edges = {(r["parent_hash"], r["edge_kind"]) for r in writer.lineage_of(attempt.output_manifest_hash)}
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
    second = _fixture_launch(writer, tmp_path, "skills.nondeterministic", skip_cache_lookup=True)
    assert second.output_manifest_hash != first.output_manifest_hash
    assert set(second.diverged) == {first.attempt_id, second.attempt_id}
    for attempt_id in second.diverged:
        assert writer.get_attempt(attempt_id)["inadmissible"] == 1
    for manifest in (first.output_manifest_hash, second.output_manifest_hash):
        assert writer.is_root("divergence", manifest)
    assert writer.serve(first.recipe_key) is None


def test_a_fixture_exiting_three_fails_and_its_receipt_carries_the_real_exit(writer, tmp_path):
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


def test_the_child_sees_no_substrate_path_and_no_inherited_secret(writer, tmp_path, monkeypatch):
    monkeypatch.setenv("CAIRN_DB", str(tmp_path / "substrate.sqlite"))
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "hunter2")
    attempt = _fixture_launch(writer, tmp_path, "skills.print_env")
    assert attempt.status == "OK"
    seen = attempt.parsed.document["environ"]
    assert not any(name.startswith("CAIRN_DB") for name in seen)
    assert "AWS_SECRET_ACCESS_KEY" not in seen
    assert "VIRTUAL_ENV" not in seen and "PWD" not in seen
    assert str(tmp_path / "substrate.sqlite") not in json.dumps(attempt.parsed.document)
    assert attempt.parsed.document["argv"] == [str(tmp_path / "runs" / attempt.attempt_id / "scratch")]


def test_a_megabyte_of_stderr_neither_deadlocks_nor_escapes_its_digest(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.stderr_1mb")
    assert attempt.status == "OK"
    stderr_bytes = (tmp_path / "runs" / attempt.attempt_id / "stderr").read_bytes()
    assert len(stderr_bytes) == 1024 * 1024
    assert writer.get_receipt(attempt.receipt_hash)["stderr_digest"] == blob_hash(stderr_bytes)


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
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree", evaluation=evaluation)
    row = writer.conn.execute("SELECT * FROM escrow WHERE attempt_id = ?", (attempt.attempt_id,)).fetchone()
    assert row["declared_production_cost"] == evaluation.expected_core_s
    assert row["declared_verification_cost"] == evaluation.expected_verification_core_s
    assert row["reserved"] == evaluation.expected_verification_core_s
    assert row["ceiling_multiplier"] == 4.0
    assert row["spent_at"] is None and row["released_at"] is None


def test_a_grant_that_cannot_cover_the_ceiling_refuses_before_spawning(writer, tmp_path, popen_spy):
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
    code, out, err = _run(["startup-scan", "--db", str(db), "--dry-run", "--json"], capsys)
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
    burner_budget = Evaluation(expected_wall_s=30.0, expected_core_s=30.0, expected_verification_core_s=0.0)
    alone = _fixture_launch(
        writer,
        tmp_path,
        "skills.cpu_burner",
        recipe=_recipe(seed=21),
        evaluation=burner_budget,
    )
    with_grandchild = _fixture_launch(
        writer,
        tmp_path,
        "skills.cpu_burner",
        recipe=_recipe(seed=22),
        evaluation=burner_budget,
        env_extra={"PYTHONPATH": FIXTURES, "FIXTURE_GRANDCHILD": "1"},
    )
    assert alone.status == with_grandchild.status == "OK"
    assert with_grandchild.launch.cpu_user_s > alone.launch.cpu_user_s * 2


def test_a_recipe_marked_do_not_cache_is_never_served(writer, tmp_path):
    first = _fixture_launch(writer, tmp_path, "skills.disagree", recipe=_recipe(seed=31), do_not_cache=True)
    assert writer.serve(first.recipe_key) is None
    second = _fixture_launch(writer, tmp_path, "skills.disagree", recipe=_recipe(seed=31), do_not_cache=True)
    assert not second.served_from_cache and second.attempt_id != first.attempt_id


@pytest.mark.parametrize("replay", ["Verifiable", "AuditOnly"])
def test_a_non_replayable_recipe_is_never_marked_non_reproducible(writer, tmp_path, replay):
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


def test_the_child_is_asked_to_terminate_before_it_is_killed(writer, tmp_path):
    attempt = _fixture_launch(
        writer,
        tmp_path,
        "skills.traps_sigterm",
        evaluation=Evaluation(0.125, 0.125, 0.125),
    )
    scratch = tmp_path / "runs" / attempt.attempt_id / "scratch"
    assert (scratch / "sigterm_seen").read_text() == "term"
    assert attempt.launch.exit_status == 0
    assert attempt.status == "BUDGET_EXCEEDED"


def test_a_grandchild_of_a_normally_exiting_child_is_still_swept(writer, tmp_path):
    import os

    attempt = _fixture_launch(writer, tmp_path, "skills.forks_then_exits")
    assert attempt.status == "OK"
    assert not attempt.launch.timed_out
    scratch = tmp_path / "runs" / attempt.attempt_id / "scratch"
    grandchild_pid = int((scratch / "grandchild_pid").read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(grandchild_pid, 0)


def test_an_exception_in_the_wait_loop_still_reaps_the_child(tmp_path, monkeypatch):
    import os
    import subprocess as sp

    spawned = []
    real_popen = sp.Popen

    class Recording(real_popen):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            spawned.append(self.pid)

    monkeypatch.setattr(sp, "Popen", Recording)
    monkeypatch.setattr(runner.subprocess, "Popen", Recording)

    ticks = []
    real_sleep = runner.time.sleep

    def exploding(seconds):
        ticks.append(seconds)
        if len(ticks) == 2:
            raise KeyboardInterrupt("planted")
        return real_sleep(seconds)

    monkeypatch.setattr(runner.time, "sleep", exploding)
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    with pytest.raises(KeyboardInterrupt, match="planted"):
        runner.spawn_and_wait(
            runner.skill_argv("skills.sleep2", scratch),
            tmp_path / "stdout",
            tmp_path / "stderr",
            ceiling_s=None,
            env=runner.child_env({"PYTHONPATH": FIXTURES}),
            stdin_bytes=b"{}",
        )
    assert len(spawned) == 1
    with pytest.raises(ProcessLookupError):
        os.kill(spawned[0], 0)


def test_only_regular_files_under_scratch_become_artifacts(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.scratch_shapes")
    assert attempt.status == "OK"
    members = {
        r["child_hash"]
        for r in writer.conn.execute(
            "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = 'member'",
            (attempt.output_manifest_hash,),
        ).fetchall()
    }
    bodies = {writer.get_blob(h) for h in members}
    assert b"OUTSIDE-THE-SCRATCH-DIR" not in bodies
    assert {b"REAL", b"DEEP"} <= bodies
    assert len(members) == 3


def test_an_attempt_is_never_left_running_when_the_launch_raises(writer, tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "_artifacts", lambda *a: (_ for _ in ()).throw(OSError("planted")))
    with pytest.raises(OSError, match="planted"):
        _fixture_launch(writer, tmp_path, "skills.disagree")
    rows = writer.conn.execute("SELECT status, ended_at FROM attempts").fetchall()
    assert [r["status"] for r in rows] == ["FAIL"]
    assert rows[0]["ended_at"] is not None


def test_a_grant_that_exactly_covers_the_ceiling_is_accepted(writer, tmp_path):
    evaluation = Evaluation(0.2, 0.2, 0.2)
    attempt = _fixture_launch(
        writer,
        tmp_path,
        "skills.disagree",
        evaluation=evaluation,
        budget_remaining=runner.ceiling_for(evaluation.expected_wall_s, 4),
    )
    assert attempt.status == "DISAGREE"


def test_input_blobs_are_linked_to_the_manifest(writer, tmp_path):
    payload = b"an input this recipe names"
    digest = writer.put_blob(payload)
    recipe = {**_recipe(seed=51), "inputs": {"seed.bin": (digest, len(payload))}}
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree", recipe=recipe)
    edges = {(r["parent_hash"], r["edge_kind"]) for r in writer.lineage_of(attempt.output_manifest_hash)}
    assert (digest, substrate.EDGE_INPUT) in edges


def test_the_manifest_records_the_producing_skill_identity(writer, tmp_path):
    attempt = _fixture_launch(writer, tmp_path, "skills.disagree")
    node = writer.get_node(attempt.output_manifest_hash)
    assert node["producer_identity"] == keys.identity_bundle_hash(IDENTITY)


def test_an_unnamed_stdin_document_is_an_empty_object(writer, tmp_path):
    attempt = runner.launch(
        writer,
        "skills.print_env",
        _recipe(seed=61),
        **_kw(tmp_path),
    )
    stdin_bytes = (tmp_path / "runs" / attempt.attempt_id / "stdin").read_bytes()
    assert stdin_bytes == b"{}\n"


def test_the_scratch_measurement_is_a_delta_not_an_absolute(writer, tmp_path):
    attempt_ids = []
    real_spawn = runner.spawn_and_wait

    def preseeded(argv, out_path, err_path, **kwargs):
        scratch = Path(argv[-1])
        (scratch / "preexisting.bin").write_bytes(b"p" * (2 * 1024 * 1024))
        attempt_ids.append(scratch)
        return real_spawn(argv, out_path, err_path, **kwargs)

    attempt = runner.launch(
        writer,
        "skills.disagree",
        _recipe(seed=71),
        stdin_document={"n": 1},
        **_kw(tmp_path),
    )
    quiet = writer.get_receipt(attempt.receipt_hash)["scratch_bytes_written"]
    assert quiet == 0


def test_a_locked_substrate_exits_conflict(tmp_path, capsys):
    db = tmp_path / "substrate.sqlite"
    with substrate.Substrate.open(db):
        code, out, err = _run(["startup-scan", "--db", str(db), "--json"], capsys)
    assert code == exits.CONFLICT
    assert out == ""


def test_a_kill_logs_the_ceiling_and_the_elapsed_wall(writer, tmp_path, json_test_log):
    _fixture_launch(
        writer,
        tmp_path,
        "skills.sleep2",
        evaluation=Evaluation(0.125, 0.125, 0.125),
    )
    records = [
        json.loads(line)
        for line in json_test_log.read_text().splitlines()
        if line.strip() and json.loads(line).get("event") == "kill"
    ]
    assert len(records) == 1
    assert records[0]["ceiling_s"] == pytest.approx(0.5)
    assert records[0]["terminated_at_s"] >= 0.5
    assert records[0]["wall_s"] >= records[0]["terminated_at_s"]


def test_the_launch_log_names_the_cache_decision(writer, tmp_path, json_test_log):
    _fixture_launch(writer, tmp_path, "skills.disagree", recipe=_recipe(seed=81))
    _fixture_launch(writer, tmp_path, "skills.disagree", recipe=_recipe(seed=82))
    records = [
        json.loads(line)
        for line in json_test_log.read_text().splitlines()
        if line.strip() and json.loads(line).get("event") == "launch"
    ]
    assert [r["served"] for r in records] == [False, False]
    assert all("attempt_id" in r for r in records)


def test_signalling_a_reaped_pid_is_swallowed(tmp_path):
    import os
    import signal
    import subprocess

    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    os.wait4(proc.pid, 0)
    proc.returncode = 0
    with pytest.raises(ProcessLookupError):
        os.kill(proc.pid, 0)
    runner._signal_group(proc.pid, proc.pid, signal.SIGKILL)


@pytest.mark.parametrize(
    ("grace", "expected_exit"),
    [(1.5, 0), (0.0, -9)],
    ids=["grace-lets-it-finish", "no-grace-kills-it"],
)
def test_the_grace_window_is_what_lets_a_slow_handler_finish(tmp_path, grace, expected_exit):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    run = runner.spawn_and_wait(
        runner.skill_argv("skills.slow_sigterm", scratch),
        tmp_path / "stdout",
        tmp_path / "stderr",
        ceiling_s=0.2,
        env=runner.child_env({"PYTHONPATH": FIXTURES}),
        stdin_bytes=b"{}",
        grace=grace,
    )
    assert run.timed_out
    assert run.exit_status == expected_exit


def test_a_slower_tick_still_stops_the_child(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    run = runner.spawn_and_wait(
        runner.skill_argv("skills.sleep2", scratch),
        tmp_path / "stdout",
        tmp_path / "stderr",
        ceiling_s=0.2,
        env=runner.child_env({"PYTHONPATH": FIXTURES}),
        stdin_bytes=b"{}",
        tick=0.05,
    )
    assert run.timed_out and run.exit_status < 0
    assert run.wall_s < 1.5


def test_the_default_grace_window_lets_a_prompt_handler_finish(tmp_path):
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    run = runner.spawn_and_wait(
        runner.skill_argv("skills.slow_sigterm", scratch),
        tmp_path / "stdout",
        tmp_path / "stderr",
        ceiling_s=0.2,
        env=runner.child_env({"PYTHONPATH": FIXTURES, "FIXTURE_SIGTERM_DELAY": "0.05"}),
        stdin_bytes=b"{}",
    )
    assert run.timed_out
    assert run.exit_status == 0
    assert runner.GRACE_S > 0.05
