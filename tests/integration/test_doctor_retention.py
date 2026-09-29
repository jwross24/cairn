import json
import os
import stat
from datetime import datetime

from cairn import cli, exits
from cairn.doctor import artifacts, detectors, mutate


def _argv(root, *rest):
    return [
        "doctor",
        "--root",
        str(root),
        "--db",
        str(root / "external.sqlite"),
        "--bundle",
        str(root / "bundle.sqlite"),
        "--pin",
        str(root / "bundle.pin"),
        "--attest",
        str(root / "attest.log"),
        *rest,
    ]


def _run(root, *args, capsys):
    code = cli.main(_argv(root, *args))
    out, err = capsys.readouterr()
    return code, out, err


def _at(value):
    return datetime.fromisoformat(value).timestamp()


def _make_run(root, at, *, findings=(), actions=(), planned=None):
    run = artifacts.start(root, at=_at(at))
    code = exits.DOCTOR_FINDINGS if findings else exits.DOCTOR_HEALTHY
    finding_rows = []
    for finding in findings:
        row = finding.as_dict() if hasattr(finding, "as_dict") else finding
        finding_rows.append(
            {
                "severity": detectors.ERROR,
                "subsystem": "test",
                "message": row.get("id", "test finding"),
                "evidence": "test finding",
                "fixable": False,
                "recommended_command": "cairn doctor",
                **row,
            }
        )
    action_rows = [
        {
            "before_hash": None,
            "after_hash": None,
            "before_mode": None,
            "after_mode": None,
            "before_flags": None,
            "after_flags": None,
            "backup": None,
            "ts": "2026-01-01T00:00:00Z",
            **action,
        }
        for action in actions
    ]
    report = {
        "mode": "fix" if actions else "detect",
        "run_id": run.run_id,
        "run_dir": str(run.run_dir),
        "root": str(root),
        "exit_code": code,
        "exit_meaning": exits.DOCTOR[code],
        "summary": "test report",
        "findings": finding_rows,
        "actions_planned": planned or [],
        "actions": action_rows,
        "recommended_command": "cairn doctor",
        "capabilities_command": "cairn doctor capabilities --json",
        "ts": "2026-01-01T00:00:00Z",
    }
    run.actions_path.write_text("".join(json.dumps(action, sort_keys=True) + "\n" for action in action_rows))
    artifacts.finish(run, report)
    artifacts.close(run)
    return run.run_id


def _tree(root):
    entries = {}
    if not root.exists():
        return entries
    for path in sorted(root.rglob("*")):
        relative = str(path.relative_to(root))
        if path.is_symlink():
            entries[relative] = ("symlink", str(path.readlink()))
        elif path.is_file():
            entries[relative] = ("file", path.read_bytes(), stat.S_IMODE(path.stat().st_mode), path.stat().st_flags)
        elif path.is_dir():
            entries[relative] = ("directory", stat.S_IMODE(path.stat().st_mode), path.stat().st_flags)
    return entries


def _lock(root):
    lock = root / mutate.LOCK_RELPATH
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()


def test_gc_previews_without_writes_then_removes_only_strictly_older_runs(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    old = _make_run(root, "2020-12-31T23:59:59+00:00")
    boundary = _make_run(root, "2021-01-01T00:00:00+00:00")
    latest = _make_run(root, "2021-01-02T00:00:00+00:00")
    _lock(root)
    before = _tree(root)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--json", capsys=capsys)

    assert code == exits.DOCTOR_HEALTHY, err
    document = json.loads(out)
    assert [candidate["run_id"] for candidate in document["candidates"]] == [old]
    assert document["dry_run"] and document["removed"] == []
    assert _tree(root) == before

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", "--json", capsys=capsys)

    assert code == exits.DOCTOR_HEALTHY, err
    document = json.loads(out)
    assert document["removed"] == [old]
    assert not (artifacts.runs_dir(root) / old).exists()
    assert (artifacts.runs_dir(root) / boundary).is_dir()
    assert (artifacts.runs_dir(root) / latest).is_dir()
    rows = artifacts.history(root)
    assert [row["run_id"] for row in rows] == [old, boundary, latest]
    code, out, err = _run(root, "ls", "--json", capsys=capsys)
    listed = json.loads(out)["runs"]
    assert [row["artifact_state"] for row in listed] == ["unavailable", "available", "available"]


def test_gc_clears_uappnd_from_a_backup_without_following_links(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    old = _make_run(root, "2020-01-01T00:00:00+00:00")
    backup = artifacts.runs_dir(root) / old / "backups" / "deploy" / "bundle.pin"
    backup.parent.mkdir(parents=True)
    backup.write_text("pin\n")
    os.chflags(backup, stat.UF_APPEND)
    _make_run(root, "2022-01-01T00:00:00+00:00")

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", "--json", capsys=capsys)

    assert code == exits.DOCTOR_HEALTHY, out + err
    assert not (artifacts.runs_dir(root) / old).exists()
    document = json.loads(out)
    assert any(item["path"] == str(backup) and item["flags"] & stat.UF_APPEND for item in document["cleared_flags"])


def test_gc_reports_completed_removal_when_later_run_cannot_be_removed(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    first = _make_run(root, "2020-01-01T00:00:00+00:00")
    second = _make_run(root, "2020-02-01T00:00:00+00:00")
    _make_run(root, "2022-01-01T00:00:00+00:00")
    second_path = artifacts.runs_dir(root) / second
    second_path.chmod(0o500)

    try:
        code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", "--json", capsys=capsys)
    finally:
        if second_path.exists():
            second_path.chmod(0o700)

    document = json.loads(out)
    assert code == exits.DOCTOR_REFUSED
    assert document["removed"] == [first]
    assert document["cleared_flags"] == []
    assert document["partial_state_possible"] is True
    assert document["failure_path"] == str(second_path)
    assert "completed removals=1" in err
    assert not (artifacts.runs_dir(root) / first).exists()
    assert second_path.is_dir()


def test_gc_refuses_the_entire_batch_when_latest_is_selected(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    older = _make_run(root, "2020-01-01T00:00:00+00:00")
    latest = _make_run(root, "2020-01-02T00:00:00+00:00")

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED
    assert latest in err and ".doctor/latest" in err
    assert (artifacts.runs_dir(root) / older).is_dir()
    assert (artifacts.runs_dir(root) / latest).is_dir()


def test_gc_refuses_latest_in_a_dry_run_without_writes(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    _make_run(root, "2020-01-01T00:00:00+00:00")
    latest = _make_run(root, "2020-01-02T00:00:00+00:00")
    _lock(root)
    before = _tree(root)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and latest in err
    assert _tree(root) == before


def test_gc_refuses_a_symlink_inside_any_selected_run_before_removing_the_batch(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    first = _make_run(root, "2020-01-01T00:00:00+00:00")
    second = _make_run(root, "2020-01-02T00:00:00+00:00")
    outside = tmp_path / "outside"
    outside.write_text("preserved\n")
    link = artifacts.runs_dir(root) / second / "escape"
    link.symlink_to(outside)
    _make_run(root, "2022-01-01T00:00:00+00:00")

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and str(link) in err
    assert (artifacts.runs_dir(root) / first).is_dir()
    assert (artifacts.runs_dir(root) / second).is_dir()
    assert outside.read_text() == "preserved\n"


def test_gc_rejects_a_symlinked_runs_root(tmp_path, capsys):
    root = tmp_path / "checkout"
    outside = tmp_path / "outside-runs"
    root.mkdir()
    outside.mkdir()
    target = outside / "2020-01-01T00-00-00Z__abcdef"
    target.mkdir()
    (root / ".doctor").mkdir()
    (root / ".doctor" / "runs").symlink_to(outside, target_is_directory=True)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and ".doctor/runs" in err
    assert target.is_dir()


def test_gc_checks_a_symlinked_doctor_ancestor_before_opening_a_lock(tmp_path, capsys):
    root = tmp_path / "checkout"
    outside = tmp_path / "outside-doctor"
    root.mkdir()
    outside.mkdir()
    run = outside / "runs" / "2020-01-01T00-00-00Z__abcdef"
    run.mkdir(parents=True)
    (root / ".doctor").symlink_to(outside, target_is_directory=True)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and ".doctor" in err
    assert run.is_dir()
    assert not (outside / "lock").exists()


def test_gc_rejects_a_traversing_latest_target_without_touching_its_destination(tmp_path, capsys):
    root = tmp_path / "checkout"
    outside = tmp_path / "outside"
    root.mkdir()
    outside.mkdir()
    (outside / "sentinel").write_text("preserved\n")
    runs = root / ".doctor" / "runs"
    runs.mkdir(parents=True)
    (root / ".doctor" / "latest").symlink_to("runs/../../outside", target_is_directory=True)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and "unsafe latest target" in err
    assert (outside / "sentinel").read_text() == "preserved\n"
    assert not (outside / "lock").exists()


def test_gc_refuses_a_symlinked_lock_without_changing_its_target(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    old = _make_run(root, "2020-01-01T00:00:00+00:00")
    _make_run(root, "2022-01-01T00:00:00+00:00")
    outside = tmp_path / "outside-lock"
    outside.write_text("preserve this lock target\n")
    (root / mutate.LOCK_RELPATH).symlink_to(outside)

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)

    assert code == exits.DOCTOR_REFUSED and "unsafe doctor lock" in err
    assert outside.read_text() == "preserve this lock target\n"
    assert (artifacts.runs_dir(root) / old).is_dir()


def test_gc_requires_an_explicit_cutoff_and_rejects_naive_instants(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()

    code, out, err = _run(root, "gc", capsys=capsys)

    assert code == exits.DOCTOR_USAGE and "--before" in err
    code, out, err = _run(root, "gc", "--before", "2021-01-01T00:00:00", capsys=capsys)
    assert code == exits.DOCTOR_USAGE and "timezone-aware" in err


def test_gc_timezone_offset_matches_the_equivalent_utc_date_cutoff(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    old = _make_run(root, "2020-12-31T23:59:59+00:00")
    _make_run(root, "2021-01-01T00:00:00+00:00")
    _make_run(root, "2022-01-01T00:00:00+00:00")

    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--json", capsys=capsys)
    assert code == exits.DOCTOR_HEALTHY, err
    date_candidates = [candidate["run_id"] for candidate in json.loads(out)["candidates"]]

    code, out, err = _run(root, "gc", "--before", "2020-12-31T19:00:00-05:00", "--json", capsys=capsys)
    assert code == exits.DOCTOR_HEALTHY, err
    offset_candidates = [candidate["run_id"] for candidate in json.loads(out)["candidates"]]

    assert date_candidates == offset_candidates == [old]


def test_since_is_refused_with_every_subcommand(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    commands = (
        ("undo", "latest"),
        ("capabilities",),
        ("health",),
        ("robot-docs",),
        ("ls",),
        ("gc", "--before", "2021-01-01"),
        ("diff",),
    )

    for command in commands:
        code, out, err = _run(root, "--since=not-a-run", *command, capsys=capsys)
        assert code == exits.DOCTOR_USAGE
        assert "--since is available only on the default doctor run" in err


def _dirs_reference_run(root, capsys):
    code, out, err = _run(root, "--only=dirs", "--json", capsys=capsys)
    assert code == exits.DOCTOR_FINDINGS, out + err
    reference = json.loads(out)
    assert {finding["id"] for finding in reference["findings"]} == {
        "D-dirs/deploy-absent",
        "D-dirs/var-absent",
        "D-dirs/gitignore",
    }
    return reference


def _repair_dirs_shape(root):
    (root / "deploy").mkdir()
    (root / "var").mkdir()
    (root / ".gitignore").write_text(".doctor/\nvar/\n")


def test_diff_compares_planned_actions_from_real_directory_detectors_without_writes(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    reference = _dirs_reference_run(root, capsys)
    _repair_dirs_shape(root)
    before = _tree(root)

    code, out, err = _run(root, "--only=dirs", "diff", reference["run_id"], "--json", capsys=capsys)

    assert code == exits.DOCTOR_HEALTHY, err
    document = json.loads(out)
    assert document["reference"] == reference["run_id"]
    assert document["added"] == []
    assert {finding_id for action in document["removed"] for finding_id in action["because"]} == {
        "D-dirs/deploy-absent",
        "D-dirs/var-absent",
        "D-dirs/gitignore",
    }
    assert _tree(root) == before


def test_since_compares_findings_from_real_directory_detectors_with_a_retained_report(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    reference = _dirs_reference_run(root, capsys)
    _repair_dirs_shape(root)

    code, out, err = _run(root, f"--since={reference['run_id']}", "--only=dirs", "--json", capsys=capsys)

    assert code == exits.DOCTOR_HEALTHY, err
    delta = json.loads(out)["since"]
    assert delta["run_id"] == reference["run_id"] and delta["added"] == []
    assert {finding["id"] for finding in delta["resolved"]} == {finding["id"] for finding in reference["findings"]}


def test_diff_refuses_a_collected_report_and_undo_latest_skips_collected_actions(tmp_path, capsys):
    root = tmp_path / "checkout"
    root.mkdir()
    old_target = root / "old-created-directory"
    old_target.mkdir()
    old_action = {"path": old_target.name, "op": mutate.MKDIR}
    retained_target = root / "retained-created-directory"
    retained_target.mkdir()
    retained_action = {"path": retained_target.name, "op": mutate.MKDIR}
    retained = _make_run(root, "2021-01-01T00:00:00+00:00", actions=[retained_action])
    collected = _make_run(root, "2020-01-01T00:00:00+00:00", actions=[old_action])
    _make_run(root, "2022-01-01T00:00:00+00:00")
    code, out, err = _run(root, "gc", "--before", "2021-01-01", "--yes", capsys=capsys)
    assert code == exits.DOCTOR_HEALTHY, out + err

    code, out, err = _run(root, "diff", collected, capsys=capsys)
    assert code == exits.DOCTOR_REFUSED and "unavailable or collected" in err
    code, out, err = _run(root, f"--since={collected}", capsys=capsys)
    assert code == exits.DOCTOR_REFUSED and "unavailable or collected" in err

    code, out, err = _run(root, "undo", "latest", capsys=capsys)
    assert code == exits.DOCTOR_HEALTHY, out + err
    assert not retained_target.exists()
    assert retained in out
    assert old_target.exists()
