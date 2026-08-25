import json

import pytest

from cairn import cli, exits, kat, pari
from cairn.errors import CliError

DISCOVERY = ("--json", "capabilities", "robot-docs")
BOUNDED_ARGV = {"measure": ("toy-curve-tries", "--sizes", "30", "--seeds", "2")}
DEPLOY_ARGV = (
    "bundle",
    "attest",
    "selftest",
    "startup-scan",
    "gate",
    "m0-run",
    "justify",
)
ESC = "\x1b"


def _scrub(text):
    import importlib.metadata
    import platform

    return text.replace(importlib.metadata.version("cairn"), "[VERSION]").replace(platform.python_version(), "[PYTHON]")


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


@pytest.fixture
def fixture_command():
    registered = []

    def add(name, run, **kw):
        kw.setdefault("summary", f"test fixture {name}")
        kw.setdefault("read_only", True)
        kw.setdefault("json", True)
        cli.register(name, lambda p: None, run, **kw)
        registered.append(name)

    yield add
    for name in registered:
        cli.unregister(name)


def test_capabilities_golden(assert_golden, capsys):
    code, out, err = _run(["capabilities", "--json"], capsys)
    assert code == exits.OK
    assert_golden("capabilities", _scrub(out))


def test_top_help_golden(assert_golden, capsys):
    with pytest.raises(SystemExit) as info:
        cli.main(["--help"])
    assert info.value.code == 0
    assert_golden("help_top", capsys.readouterr().out)


@pytest.mark.parametrize("name", cli.registered())
def test_subcommand_help_exits_zero_and_names_discovery_surfaces(name, capsys, assert_golden):
    with pytest.raises(SystemExit) as info:
        cli.main([name, "--help"])
    out = capsys.readouterr().out
    assert info.value.code == 0
    assert all(word in out for word in DISCOVERY)
    assert_golden(f"help_{name}", out)


@pytest.mark.parametrize("name", cli.registered())
def test_registration_is_the_capabilities_row(name):
    cmd = cli.resolve_command(name)
    row = next(c for c in cli.capabilities_document()["commands"] if c["name"] == name)
    assert (row["read_only"], row["json"], row["dangerous"], row["gating"]) == (
        cmd.read_only,
        cmd.json,
        cmd.dangerous,
        cmd.gating,
    )


def _deploy_argv(name, tmp_path, pinned_bundle, clear_flags, capsys):
    if name == "startup-scan":
        from cairn import substrate

        db = tmp_path / "substrate.sqlite"
        with substrate.Substrate.open(db):
            pass
        return ("--db", str(db))
    bundle_path, pin_path = pinned_bundle()
    paths = ("--bundle", str(bundle_path), "--pin", str(pin_path))
    if name == "justify":
        from cairn import attest, claims, substrate

        db = tmp_path / "substrate.sqlite"
        statement = claims.ClaimStatement(
            claim_id="cli-contract",
            version=1,
            informal="a statement with no evidence derives SPECULATION",
            scope={
                "target_family": "toy_curve",
                "size_interval": [40, 40],
                "param_ranges": {},
                "assumption_set": set(),
            },
            quantities={"units": {}, "cost_model": None},
        )
        with substrate.Substrate.open(db) as sub:
            claims.write_claim_statement(sub, statement)
        log_path = tmp_path / "attestations.log"
        clear_flags(log_path)
        attest.init(log_path, "f" * 64)
        return (
            "--statement",
            statement.hash,
            "--db",
            str(db),
            "--attest",
            str(log_path),
        )
    if name == "bundle":
        return ("show", *paths)
    if name == "selftest":
        return ("toy-curve", *paths, "--db", str(tmp_path / "substrate.sqlite"))
    attest_path = tmp_path / "attestations.log"
    clear_flags(attest_path)
    if name in ("gate", "m0-run"):
        from cairn import attest
        from cairn import bundle as bundle_mod

        gate_bundle = bundle_mod.GateBundle.open(bundle_path, pin_path)
        attest.init(attest_path, gate_bundle.waiver_target())
        db = tmp_path / "substrate.sqlite"
        tail = (*paths, "--attest", str(attest_path), "--db", str(db))
        if name == "gate":
            return ("selftest", *tail)
        _run(["selftest", "toy-curve", *paths, "--db", str(db)], capsys)
        return ("--bits", "40", "--seed", "1", *tail)
    return ("init", *paths, "--attest", str(attest_path))


@pytest.mark.parametrize("name", [c.name for c in cli.commands() if c.json])
def test_json_commands_emit_exactly_one_document_on_stdout(name, capsys, tmp_path, pinned_bundle, clear_flags):
    argv = (
        _deploy_argv(name, tmp_path, pinned_bundle, clear_flags, capsys)
        if name in DEPLOY_ARGV
        else BOUNDED_ARGV.get(name, ())
    )
    code, out, err = _run([name, *argv, "--json"], capsys)
    assert code == exits.OK, err
    document = json.loads(out)
    assert document["schema_version"] == cli.SCHEMA_VERSION and document["command"] == name
    assert out.count("\n") == 1
    assert ESC not in out and ESC not in err


def test_capabilities_lists_contract_sections(capsys):
    code, out, err = _run(["capabilities", "--json"], capsys)
    doc = json.loads(out)
    assert set(doc) >= {
        "commands",
        "exit_codes",
        "env_vars",
        "default_paths",
        "global_options",
        "schema_version",
        "contract_version",
    }
    assert set(doc["exit_codes"]) == {"cli", "doctor"}
    assert doc["exit_codes"]["cli"] == {str(k): v for k, v in exits.CLI.items()}


def test_capabilities_is_deterministic(capsys):
    first = _run(["capabilities", "--json"], capsys)[1]
    second = _run(["capabilities", "--json"], capsys)[1]
    assert first == second


def test_robot_docs_prints_the_handbook(capsys):
    code, out, err = _run(["robot-docs"], capsys)
    assert code == exits.OK
    for step in (
        "bundle build",
        "bundle pin",
        "attest init",
        "selftest toy-curve",
        "gate selftest",
        "m0-run",
    ):
        assert step in out
    assert "## Exit codes (cli)" in out and "## Never" in out
    flag = _run(["--robot-help"], capsys)[1]
    assert flag == out


def test_bare_invocation_prints_usage_and_hints_and_exits_user_input(capsys):
    code, out, err = _run([], capsys)
    assert code == exits.USER_INPUT
    assert out == ""
    assert "usage:" in err and all(word in err for word in DISCOVERY)


@pytest.mark.parametrize(
    ("argv", "needle"),
    [
        (["--jsno", "capabilities"], "--json"),
        (["capabilities", "--jsno"], "--json"),
        (["kta"], "kat"),
        (["kat", "cannon"], "canon"),
    ],
    ids=["flag-typo-before", "flag-typo-after", "subcommand-typo", "choice-typo"],
)
def test_typo_hints_name_the_intended_spelling(argv, needle, capsys):
    code, out, err = _run(argv, capsys)
    assert code == exits.USER_INPUT
    assert out == ""
    assert needle in err and ("did you mean" in err or "maybe you meant" in err)
    assert "run: cairn" in err


def test_exit_codes_one_named_failure_each(tmp_path, capsys, monkeypatch, fixture_command):
    code, out, err = _run(["kat", "--no-such"], capsys)
    assert code == exits.USER_INPUT and "next_command" in err
    copy = tmp_path / "canon_kat.json"
    data = json.loads(kat.DEFAULT_VECTORS.read_text())
    data["vectors"][1]["relation"] = {"differs": "recipe_a"}
    copy.write_text(json.dumps(data))
    code, out, err = _run(["kat", "canon", "--vectors", str(copy)], capsys)
    assert code == exits.GATE_REFUSED
    monkeypatch.setattr(pari, "GP_BIN", "/nonexistent/gp")
    fixture_command("probe-gp", lambda ns: (pari.run_gp([], "print(1)"), exits.OK)[1])
    code, out, err = _run(["probe-gp"], capsys)
    assert code == exits.ENVIRONMENT and "cairn doctor" in err
    monkeypatch.undo()
    fixture_command("probe-backend", lambda ns: (_ for _ in ()).throw(pari.GpTimeout(0, 0.0)))
    code, out, err = _run(["probe-backend"], capsys)
    assert code == exits.BACKEND and "GpTimeout" in err
    import sqlite3

    fixture_command(
        "probe-lock",
        lambda ns: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked")),
    )
    code, out, err = _run(["probe-lock"], capsys)
    assert code == exits.CONFLICT and "cairn doctor" in err


def test_cli_error_record_and_human_line_carry_next_command(capsys):
    err = CliError(
        exits.GATE_REFUSED,
        "bundle hash differs from pin",
        where="deploy/gate-bundle.pin",
        next_command="cairn bundle pin --bundle B --pin P",
    )
    assert err.record()["next_command"] == "cairn bundle pin --bundle B --pin P"
    assert (
        err.human()
        == "error: bundle hash differs from pin (deploy/gate-bundle.pin); run: cairn bundle pin --bundle B --pin P"
    )


def test_dangerous_fixture_is_refused_pre_run_without_its_gating_flag(fixture_command, capsys):
    calls = []
    fixture_command(
        "danger",
        lambda ns: (calls.append(ns), exits.OK)[1],
        dangerous=True,
        gating="--yes",
        read_only=False,
        json=False,
    )
    code, out, err = _run(["danger"], capsys)
    assert code == exits.GATE_REFUSED and calls == [] and "cairn danger --yes" in err and out == ""
    code, out, err = _run(["danger", "--yes"], capsys)
    assert code == exits.OK and len(calls) == 1
    fixture_command(
        "dry",
        lambda ns: (calls.append(ns), exits.OK)[1],
        dangerous=True,
        gating="--yes",
        read_only=False,
        json=False,
        dry_run_default=True,
    )
    assert _run(["dry"], capsys)[0] == exits.OK and len(calls) == 2
    with pytest.raises(ValueError, match="gating"):
        cli.register(
            "ungated",
            lambda p: None,
            lambda ns: 0,
            summary="x",
            read_only=False,
            json=False,
            dangerous=True,
        )


def test_refuse_overwrite_and_require_yes_gate_dangerous_ops(tmp_path):
    target = tmp_path / "pin"
    target.write_text("x")
    cli.refuse_overwrite(tmp_path / "absent", flag="--force", command="cairn bundle pin", force=False)
    with pytest.raises(CliError) as info:
        cli.refuse_overwrite(target, flag="--force", command="cairn bundle pin", force=False)
    assert info.value.code == exits.GATE_REFUSED and info.value.next_command == "cairn bundle pin --force"
    cli.refuse_overwrite(target, flag="--force", command="cairn bundle pin", force=True)
    with pytest.raises(CliError) as info:
        cli.require_yes(False, plan="delete 3 blobs", command="cairn gc")
    assert (
        info.value.code == exits.GATE_REFUSED
        and info.value.next_command == "cairn gc --yes"
        and "delete 3 blobs" in info.value.what
    )
    cli.require_yes(True, plan="delete 3 blobs", command="cairn gc")


def test_fixture_command_leaking_text_under_json_is_caught(fixture_command, capsys):
    def leaky(ns):
        print("progress: 50%")
        cli.emit_json("leaky", {"ok": True})
        return exits.OK

    fixture_command("leaky", leaky)
    code, out, err = _run(["leaky", "--json"], capsys)
    with pytest.raises(json.JSONDecodeError):
        json.loads(out)
    assert out.count("\n") == 2


def test_fixture_command_emitting_ansi_is_caught(fixture_command, capsys):
    def colorful(ns):
        print(f"{ESC}[31mred{ESC}[0m")
        return exits.OK

    fixture_command("colorful", colorful, json=False)
    code, out, err = _run(["colorful"], capsys)
    assert ESC in out


def test_fixture_help_without_discovery_hint_is_caught():
    parser = cli.build_parser()
    help_text = parser.format_help()
    assert all(word in help_text for word in DISCOVERY)
    bare = cli.argparse.ArgumentParser(prog="cairn fixture")
    assert not all(word in bare.format_help() for word in DISCOVERY)


def test_source_date_epoch_drives_now_iso(monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    assert cli.now_iso() == "1970-01-01T00:00:00Z"


def test_unexpected_exception_is_never_silent(fixture_command, capsys):
    fixture_command("boom", lambda ns: (_ for _ in ()).throw(RuntimeError("kaboom")))
    code, out, err = _run(["boom"], capsys)
    assert code == exits.BACKEND
    assert "kaboom" in err and out == ""
