import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import _doctor_fixtures as doctor_fixtures
import pytest

from cairn import attest, bundle, cli, exits, pari
from cairn.doctor import artifacts, detectors, fixers, mutate

ROOT = Path(__file__).resolve().parents[2]
UV_INDEX = '[[tool.uv.index]]\nname = "pypi"\nurl = "https://pypi.org/simple"\ndefault = true\n'
GITIGNORE = ".doctor/\nvar/\n"


@dataclass
class Shape:
    root: Path
    db: Path
    bundle: Path
    pin: Path
    attest: Path

    def argv(self, *rest, only=None):
        head = [
            "doctor",
            "--root",
            str(self.root),
            "--db",
            str(self.db),
            "--bundle",
            str(self.bundle),
            "--pin",
            str(self.pin),
            "--attest",
            str(self.attest),
        ]
        if only:
            head += [f"--only={only}"]
        return head + list(rest)


def _clear_flags(root):
    for path in Path(root).rglob("*"):
        if os.path.lexists(path) and not path.is_symlink() and os.stat(path).st_flags:
            os.chflags(path, 0)


def _build_shape(root):
    root = Path(root)
    (root / "deploy").mkdir(parents=True)
    (root / "var").mkdir(parents=True)
    bundle_path, pin_path = root / "deploy" / "gate-bundle.sqlite", root / "deploy" / "gate-bundle.pin"
    attest_path, db_path = root / "deploy" / "attestations.log", root / "var" / "substrate.sqlite"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    attest.init(attest_path, bundle.GateBundle.open(bundle_path, pin_path).waiver_target())
    assert (
        cli.main(["selftest", "toy-curve", "--db", str(db_path), "--bundle", str(bundle_path), "--pin", str(pin_path)])
        == exits.OK
    )
    (root / "pyproject.toml").write_text(UV_INDEX)
    (root / ".gitignore").write_text(GITIGNORE)
    return Shape(root, db_path, bundle_path, pin_path, attest_path)


@pytest.fixture(scope="session")
def master_shape(tmp_path_factory):
    root = tmp_path_factory.mktemp("doctor-master") / "checkout"
    _build_shape(root)
    yield root
    _clear_flags(root)


@pytest.fixture
def shape(master_shape, tmp_path):
    root = tmp_path / "checkout"
    shutil.copytree(master_shape, root)
    made = Shape(
        root,
        root / "var" / "substrate.sqlite",
        root / "deploy" / "gate-bundle.sqlite",
        root / "deploy" / "gate-bundle.pin",
        root / "deploy" / "attestations.log",
    )
    yield made
    _clear_flags(root)


def run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


SQLITE_SIDECARS = ("-wal", "-shm")


def tree_hashes(root, *, skip=(".doctor",), sidecars=False):
    seen = {}
    for path in sorted(Path(root).rglob("*")):
        rel = path.relative_to(root)
        if rel.parts and rel.parts[0] in skip:
            continue
        if not sidecars and path.name.endswith(SQLITE_SIDECARS):
            continue
        if path.is_symlink():
            continue
        st = os.stat(path)
        digest = None
        if path.is_file():
            try:
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
            except PermissionError:
                digest = "unreadable"
        seen[str(rel)] = (digest, stat.S_IMODE(st.st_mode), st.st_flags)
    return seen


def stat_line(path):
    st = os.stat(path)
    return f"{stat.S_IMODE(st.st_mode):04o} flags={st.st_flags:#x}"


def latest_run_dir(root):
    return artifacts.resolve_run_dir(root, "latest")


# ---------------------------------------------------------------- healthy shape


def test_the_built_deploy_shape_is_healthy_and_prints_one_json_document(shape, capsys):
    code, out, err = run(shape.argv("--json"), capsys)
    assert code == exits.DOCTOR_HEALTHY, out + err
    document = json.loads(out)
    assert out.count("\n") == 1
    assert document["schema_version"] == cli.SCHEMA_VERSION and document["command"] == "doctor"
    assert document["findings"] == [] and document["exit_code"] == exits.DOCTOR_HEALTHY
    assert document["run_id"] and (Path(document["run_dir"]) / "report.json").is_file()


def test_a_detect_run_writes_nothing_outside_the_doctor_directory(shape, capsys):
    before = tree_hashes(shape.root, skip=(), sidecars=True)
    run(shape.argv(), capsys)
    after = tree_hashes(shape.root, skip=(), sidecars=True)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    stray = {k for k in changed if k.split("/")[0] != ".doctor" and not k.endswith(SQLITE_SIDECARS)}
    assert changed and stray == set(), stray


def test_every_detector_leaves_the_examined_tree_byte_identical(shape):
    ctx = detectors.Context(shape.root, shape.db, shape.bundle, shape.pin, shape.attest)
    before = tree_hashes(shape.root, sidecars=True)
    detectors.detect(ctx)
    after = tree_hashes(shape.root, sidecars=True)
    stray = {k for k in set(before) | set(after) if before.get(k) != after.get(k) and not k.endswith(SQLITE_SIDECARS)}
    assert stray == set(), stray


def test_a_planted_mutating_detector_is_caught_by_the_purity_check(shape, monkeypatch):
    def dirty(ctx):
        (ctx.root / "planted-by-a-detector").write_text("x")
        return []

    monkeypatch.setattr(
        detectors,
        "DETECTORS",
        (*detectors.DETECTORS, detectors.Detector("D-planted", "dirs", dirty, "writes")),
    )
    ctx = detectors.Context(shape.root, shape.db, shape.bundle, shape.pin, shape.attest)
    before = tree_hashes(shape.root)
    detectors.detect(ctx)
    assert (shape.root / "planted-by-a-detector").is_file()
    assert tree_hashes(shape.root) != before


# ---------------------------------------------------------------- surface


def test_capabilities_lists_every_detector_and_fixer_id_and_both_exit_dictionaries(shape, capsys):
    code, out, err = run(shape.argv("capabilities", "--json"), capsys)
    assert code == exits.DOCTOR_HEALTHY, err
    doc = json.loads(out)
    assert {d["id"] for d in doc["detectors"]} == {d.id for d in detectors.DETECTORS}
    assert [f["id"] for f in doc["fixers"]] == [name for name, _ in fixers.FIXERS]
    assert doc["exit_codes"]["doctor"] == {str(k): v for k, v in exits.DOCTOR.items()}
    assert doc["exit_codes"]["cli"] == {str(k): v for k, v in exits.CLI.items()}


def test_every_declared_detector_id_resolves_to_a_callable_in_code(shape, capsys):
    doc = json.loads(run(shape.argv("capabilities", "--json"), capsys)[1])
    by_id = {d.id: d for d in detectors.DETECTORS}
    for declared in doc["detectors"]:
        assert callable(by_id[declared["id"]].fn)
        assert declared["subsystem"] == by_id[declared["id"]].subsystem


def test_robot_docs_prints_the_handbook(shape, capsys):
    code, out, err = run(shape.argv("robot-docs"), capsys)
    assert code == exits.DOCTOR_HEALTHY
    for needle in ("cairn doctor --robot-triage", "## Detectors", "## Exit codes (doctor)", "D-pin-mode", "F-modes"):
        assert needle in out


def test_health_is_one_line_and_an_exit_code(shape, capsys):
    code, out, err = run(shape.argv("health"), capsys)
    assert code == exits.DOCTOR_HEALTHY
    assert out.count("\n") == 1 and out.startswith("cairn doctor:")


def test_robot_triage_carries_the_exact_next_command(shape, capsys):
    doctor_fixtures.load("pin_flag").corrupt(shape)
    code, out, err = run(shape.argv("--robot-triage"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    doc = json.loads(out)
    assert set(doc) >= {"summary", "findings", "actions_planned", "recommended_command", "capabilities_command"}
    assert doc["recommended_command"] == "cairn doctor --fix"
    assert doc["capabilities_command"] == "cairn doctor capabilities --json"
    assert run(shape.argv(*doc["recommended_command"].split()[2:]), capsys)[0] == exits.DOCTOR_HEALTHY


def test_explain_expands_one_finding_with_its_evidence(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    code, out, err = run(shape.argv("--explain", "D-pin-mode/mode", "--json"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    finding = json.loads(out)["finding"]
    assert finding["id"] == "D-pin-mode/mode" and "mode=0644" in finding["evidence"]


def test_explain_of_an_unknown_finding_is_a_doctor_usage_error(shape, capsys):
    code, out, err = run(shape.argv("--explain", "D-no-such/thing"), capsys)
    assert code == exits.DOCTOR_USAGE and out == "" and "D-no-such/thing" in err


def test_an_unknown_subsystem_is_a_doctor_usage_error_not_a_cli_one(shape, capsys):
    code, out, err = run(shape.argv("--only=nosuch"), capsys)
    assert code == exits.DOCTOR_USAGE and code != exits.USER_INPUT and out == ""


def test_a_missing_undo_argument_is_a_doctor_usage_error(shape, capsys):
    code, out, err = run(shape.argv("undo"), capsys)
    assert code == exits.DOCTOR_USAGE and out == ""


def test_online_is_refused_at_m0(shape, capsys):
    before = tree_hashes(shape.root, skip=())
    code, out, err = run(shape.argv("--online"), capsys)
    assert code == exits.DOCTOR_REFUSED and out == "" and "--online" in err
    assert tree_hashes(shape.root, skip=()) == before
    assert not (shape.root / ".doctor").exists()


def test_quick_spawns_no_subprocess_and_skips_the_kat(shape, capsys, popen_spy):
    code, out, err = run(shape.argv("--quick", "--json"), capsys)
    assert code == exits.DOCTOR_HEALTHY
    assert popen_spy == []


def test_only_scopes_the_run_to_one_subsystem(shape, capsys):
    doctor_fixtures.load("pin_flag").corrupt(shape)
    assert run(shape.argv("--json", only="gp"), capsys)[0] == exits.DOCTOR_HEALTHY
    assert run(shape.argv("--json", only="deploy"), capsys)[0] == exits.DOCTOR_FINDINGS


def test_ls_lists_the_runs_the_index_recorded(shape, capsys):
    run(shape.argv(), capsys)
    run(shape.argv(), capsys)
    code, out, err = run(shape.argv("ls", "--json"), capsys)
    assert code == exits.DOCTOR_HEALTHY
    rows = json.loads(out)["runs"]
    assert len(rows) == 2 and all(row["mode"] == "detect" for row in rows)


def test_json_output_is_one_document_with_logs_on_stderr_only(shape, capsys):
    code, out, err = run(shape.argv("--json", "--log", "DEBUG"), capsys)
    json.loads(out)
    assert out.count("\n") == 1
    assert err.strip() and all(json.loads(line)["step"] for line in err.splitlines() if line.strip())


# ---------------------------------------------------------------- round trips

FIXABLE_FIXTURES = [n for n in doctor_fixtures.names() if doctor_fixtures.load(n).FIXABLE]
UNFIXABLE_FIXTURES = [n for n in doctor_fixtures.names() if not doctor_fixtures.load(n).FIXABLE]


@pytest.mark.parametrize("name", FIXABLE_FIXTURES)
def test_a_fixable_failure_mode_round_trips_through_fix_and_undo(name, shape, capsys):
    fixture = doctor_fixtures.load(name)
    fixture.corrupt(shape)
    only = fixture.ONLY
    corrupted = tree_hashes(shape.root)

    code, out, err = run(shape.argv("--json", only=only), capsys)
    assert code == exits.DOCTOR_FINDINGS
    document = json.loads(out)
    found = {f["id"] for f in document["findings"]}
    assert set(fixture.FINDINGS) <= found, found
    assert all(f["recommended_command"] for f in document["findings"])

    code, out, err = run(shape.argv("--dry-run", "--fix", "--json", only=only), capsys)
    assert code == exits.DOCTOR_FINDINGS
    plan = json.loads(out)
    assert plan["actions"] == [] and plan["actions_planned"]
    assert tree_hashes(shape.root) == corrupted

    code, out, err = run(shape.argv("--fix", "--json", only=only), capsys)
    assert code == exits.DOCTOR_HEALTHY, out + err
    fixed = json.loads(out)
    assert fixed["actions"] and all(a["backup"] is not None or a["before_hash"] is None for a in fixed["actions"])
    assert tree_hashes(shape.root) != corrupted

    assert run(shape.argv(only=only), capsys)[0] == exits.DOCTOR_HEALTHY

    code, out, err = run(shape.argv("undo", "latest"), capsys)
    assert code == exits.DOCTOR_HEALTHY, err
    restored = tree_hashes(shape.root)
    quarantined = {k for k in restored if mutate.QUARANTINE_SUFFIX in k}
    assert bool(quarantined) == getattr(fixture, "QUARANTINES_ON_UNDO", False)
    assert {k: v for k, v in restored.items() if k not in quarantined} == corrupted


@pytest.mark.parametrize("name", UNFIXABLE_FIXTURES)
def test_an_unfixable_failure_mode_is_named_with_its_next_command_and_never_mutated(name, shape, capsys):
    fixture = doctor_fixtures.load(name)
    fixture.corrupt(shape)
    corrupted = tree_hashes(shape.root)

    code, out, err = run(shape.argv("--json"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    findings = {f["id"]: f for f in json.loads(out)["findings"]}
    assert set(fixture.FINDINGS) <= set(findings), sorted(findings)
    for wanted in fixture.FINDINGS:
        assert findings[wanted]["fixable"] is False
        assert findings[wanted]["recommended_command"].strip()

    code, out, err = run(shape.argv("--fix", "--json"), capsys)
    assert code == exits.DOCTOR_PARTIAL
    assert set(fixture.FINDINGS) <= {f["id"] for f in json.loads(out)["findings"]}
    assert tree_hashes(shape.root) == corrupted


def test_a_missing_gp_binary_names_the_brew_line(shape, capsys, monkeypatch, tmp_path):
    monkeypatch.setattr(pari, "GP_BIN", str(tmp_path / "no-such-gp"))
    code, out, err = run(shape.argv("--json", only="gp"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    finding = json.loads(out)["findings"][0]
    assert finding["id"] == "D-gp-binary/absent"
    assert finding["recommended_command"] == detectors.BREW_LINE == "brew install pari"


def test_a_bundle_that_no_longer_matches_its_pin_names_the_repin_sequence(shape, capsys):
    doctor_fixtures.load("bundle_pin_mismatch").corrupt(shape)
    code, out, err = run(shape.argv("--json", only="deploy"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    finding = next(f for f in json.loads(out)["findings"] if f["id"] == "D-bundle/pin-mismatch")
    assert finding["recommended_command"] == bundle.repin_sequence(shape.bundle, shape.pin)
    assert "chflags nouappnd" in finding["recommended_command"] and "--force" in finding["recommended_command"]


def test_running_attempts_name_the_startup_scan(shape, capsys):
    doctor_fixtures.load("running_attempts").corrupt(shape)
    code, out, err = run(shape.argv("--json", only="substrate"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    finding = next(f for f in json.loads(out)["findings"] if f["id"] == "D-substrate/running-attempts")
    assert finding["recommended_command"] == f"cairn startup-scan --db {shape.db}"


def test_an_uncertified_skill_names_the_selftest(shape, capsys):
    doctor_fixtures.load("uncertified_skill").corrupt(shape)
    code, out, err = run(shape.argv("--json", only="gates"), capsys)
    assert code == exits.DOCTOR_FINDINGS
    finding = next(f for f in json.loads(out)["findings"] if f["id"] == "D-certificate/uncertified")
    assert finding["recommended_command"] == (
        f"cairn selftest toy-curve --db {shape.db} --bundle {shape.bundle} --pin {shape.pin}"
    )


# ---------------------------------------------------------------- safety harness


def test_fix_is_idempotent(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    first = json.loads(run(shape.argv("--fix", "--json"), capsys)[1])
    assert len(first["actions"]) == 1
    code, out, err = run(shape.argv("--fix", "--json"), capsys)
    assert code == exits.DOCTOR_HEALTHY
    assert json.loads(out)["actions"] == []


def test_undo_fails_closed_when_a_backup_is_gone_and_changes_nothing(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    assert run(shape.argv("--fix"), capsys)[0] == exits.DOCTOR_HEALTHY
    run_dir = latest_run_dir(shape.root)
    backup = next((run_dir / "backups").rglob("*.pin"))
    os.chflags(backup, 0)
    os.rename(backup, backup.with_suffix(".moved"))
    fixed = tree_hashes(shape.root)
    code, out, err = run(shape.argv("undo", "latest"), capsys)
    assert code == exits.DOCTOR_ROLLED_BACK and "missing" in err
    assert tree_hashes(shape.root) == fixed


def test_undo_of_an_unknown_run_is_a_usage_error(shape, capsys):
    code, out, err = run(shape.argv("undo", "2026-01-01T00-00-00Z__abcdef"), capsys)
    assert code == exits.DOCTOR_USAGE and "cairn doctor ls" in err


def test_a_second_fix_while_the_lock_is_held_refuses_with_concurrency_lost(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    with mutate.acquire(shape.root):
        code, out, err = run(shape.argv("--fix"), capsys)
    assert code == exits.DOCTOR_CONCURRENCY and str(os.getpid()) in err
    assert run(shape.argv("--fix"), capsys)[0] == exits.DOCTOR_HEALTHY


def _child(shape, *args, env=None):
    environ = dict(os.environ)
    environ["PYTHONPATH"] = str(ROOT / "src")
    environ.update(env or {})
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; from cairn import cli; sys.exit(cli.main(sys.argv[1:]))",
            *shape.argv(*args),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=environ,
    )


def test_two_concurrent_fixes_leave_one_winner_and_one_concurrency_loss(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    first, second = _child(shape, "--fix"), _child(shape, "--fix")
    first.communicate()
    second.communicate()
    codes = sorted([first.returncode, second.returncode])
    assert exits.DOCTOR_CONCURRENCY in codes, codes
    assert {c for c in codes if c != exits.DOCTOR_CONCURRENCY} <= {exits.DOCTOR_HEALTHY, exits.DOCTOR_PARTIAL}, codes


def test_a_sigkill_between_backup_and_apply_leaves_no_tmp_file_and_no_stale_lock(shape, capsys):
    doctor_fixtures.load("pin_mode").corrupt(shape)
    corrupted = tree_hashes(shape.root)
    child = _child(shape, "--fix", env={mutate.CRASH_ENV: "1"})
    child.communicate()
    assert child.returncode == -9, child.returncode
    assert tree_hashes(shape.root) == corrupted
    assert [p.name for p in shape.root.rglob(".tmp.*")] == []
    crashed = max(artifacts.runs_dir(shape.root).iterdir())
    assert list((crashed / "staging").rglob("*")) == []
    assert (crashed / "backups" / "deploy" / "gate-bundle.pin").is_file()
    with mutate.acquire(shape.root):
        pass
    assert run(shape.argv("--fix"), capsys)[0] == exits.DOCTOR_HEALTHY


def test_mutate_refuses_to_create_a_pin_that_is_not_there(shape, tmp_path):
    run_obj = artifacts.start(shape.root)
    try:
        with mutate.acquire(shape.root) as lock:
            run_obj.lock = lock
            with pytest.raises(mutate.Refused, match="operator act"):
                mutate.mutate(
                    run_obj, shape.root / "deploy" / "absent.pin", mutate.Op(mutate.MODES, mode=0o444, flags=0)
                )
    finally:
        artifacts.close(run_obj)


def test_mutate_without_the_lock_refuses(shape):
    run_obj = artifacts.start(shape.root)
    try:
        with pytest.raises(mutate.Refused, match="lock"):
            mutate.mutate(run_obj, shape.pin, mutate.Op(mutate.MODES, mode=0o444, flags=stat.UF_APPEND))
    finally:
        artifacts.close(run_obj)


def test_f_modes_refuses_a_planned_action_whose_file_vanished(shape):
    run_obj = artifacts.start(shape.root)
    try:
        action = fixers.Action(
            detectors.F_MODES,
            str(shape.root / "deploy" / "gone.pin"),
            mutate.Op(mutate.MODES, mode=0o444, flags=stat.UF_APPEND),
            "chmod",
            ("D-pin-mode/mode",),
        )
        with pytest.raises(mutate.Refused, match="operator act"):
            fixers.apply(run_obj, [action])
    finally:
        artifacts.close(run_obj)


# ---------------------------------------------------------------- artifacts


def test_the_run_artifact_holds_every_declared_file_and_lives_under_the_doctor_directory(shape, capsys):
    run(shape.argv(), capsys)
    run_dir = latest_run_dir(shape.root)
    assert run_dir.parent == artifacts.runs_dir(shape.root)
    for name in ("report.json", "report.md", "actions.jsonl", "stderr.log", "undo.sh"):
        assert (run_dir / name).is_file(), name
    assert (run_dir / "backups").is_dir()
    assert (run_dir / "undo.sh").read_text().splitlines()[-1] == f"cairn doctor undo {run_dir.name}"
    assert json.loads((run_dir / "report.json").read_text())["run_id"] == run_dir.name


def test_the_run_id_uses_the_wall_clock_even_under_source_date_epoch(shape, monkeypatch, capsys):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    run(shape.argv(), capsys)
    run_dir = latest_run_dir(shape.root)
    report = json.loads((run_dir / "report.json").read_text())
    assert report["ts"] == "1970-01-01T00:00:00Z"
    assert not run_dir.name.startswith("1970-")


def test_git_head_is_read_textually_and_is_nogit_without_a_checkout(shape):
    assert artifacts.git_head(shape.root) == "nogit"
    head = artifacts.git_head(ROOT)
    assert len(head) == 40 and all(c in "0123456789abcdef" for c in head)


def test_the_index_line_carries_the_run_and_its_verdict(shape, capsys):
    doctor_fixtures.load("pin_flag").corrupt(shape)
    run(shape.argv("--fix"), capsys)
    row = artifacts.history(shape.root)[-1]
    assert row["mode"] == "fix" and row["exit_code"] == exits.DOCTOR_HEALTHY and row["actions"] == 1
