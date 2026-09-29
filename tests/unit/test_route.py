import json
import os
import subprocess
import sys
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

ROUTE_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "route.py"
route_spec = spec_from_file_location("cairn_route", ROUTE_SCRIPT_PATH)
assert route_spec is not None
assert route_spec.loader is not None
route = module_from_spec(route_spec)
route_spec.loader.exec_module(route)


@pytest.fixture(autouse=True)
def disable_live_judge(monkeypatch):
    monkeypatch.setattr(route.shutil, "which", lambda name: None)


@pytest.fixture
def fake_codex(tmp_path):
    executable = tmp_path / "codex"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import json, os, pathlib, sys, time\n"
        "mode = os.environ.get('ROUTE_FAKE_JUDGE', 'standard')\n"
        "if mode == 'timeout': time.sleep(1)\n"
        "answer = pathlib.Path(sys.argv[sys.argv.index('-o') + 1])\n"
        "if mode == 'garbage': answer.write_text('not-json')\n"
        "elif mode == 'mechanical': answer.write_text(json.dumps({'class': 'Mechanical', 'reason': 'low'}))\n"
        "elif mode == 'class-list': answer.write_text(json.dumps({'class': [], 'reason': 'bad'}))\n"
        "elif mode == 'class-dict': answer.write_text(json.dumps({'class': {}, 'reason': 'bad'}))\n"
        "elif mode == 'empty-reason': answer.write_text(json.dumps({'class': 'Standard', 'reason': ''}))\n"
        "elif mode == 'multiline-reason': answer.write_text(json.dumps({'class': 'Standard', 'reason': 'a\\nb'}))\n"
        "elif mode == 'demanding': answer.write_text(json.dumps({'class': 'Demanding', 'reason': 'broad work'}))\n"
        "else: answer.write_text(json.dumps({'class': 'Standard', 'reason': 'bounded work'}))\n"
    )
    executable.chmod(0o755)
    return [sys.executable, str(executable)]


def _gray_bead(**fields):
    return {
        "id": "gray-test",
        "title": "Handle bounded input",
        "description": "Implement bounded input handling.",
        **fields,
    }


def test_documentation_bead_routes_mechanical_without_judge():
    result = route.route_bead({"id": "docs", "description": "Rewrite README.md."})

    assert result["class"] == "Mechanical"
    assert result["floor"] == "Mechanical"
    assert result["judge"] == {"used": False, "answer": None, "error": None}
    assert set(result) == {"class", "reasons", "floor", "judge"}


def test_critical_body_path_cannot_be_lowered_by_route_label():
    result = route.route_bead(
        {
            "id": "critical",
            "description": "Document the behavior around `bundle/verifier.json`.",
            "labels": ["route:mechanical"],
        }
    )

    assert result["class"] == "Critical"
    assert result["floor"] == "Critical"
    assert result["judge"]["used"] is False


def test_directory_covering_identity_sources_is_critical():
    result = route.route_bead({"id": "bundle", "description": "Touches: bundle/"})

    assert result["class"] == "Critical"


def test_gray_judge_cannot_select_mechanical(fake_codex, monkeypatch):
    monkeypatch.setenv("ROUTE_FAKE_JUDGE", "mechanical")
    result = route.route_bead(_gray_bead(), codex_path=fake_codex)

    assert result["class"] == "Demanding"
    assert result["judge"]["used"] is True
    assert result["judge"]["error"] == "judge returned an answer outside its schema"


@pytest.mark.parametrize("mode", ["timeout", "garbage", "class-list", "class-dict", "empty-reason", "multiline-reason"])
def test_judge_timeout_and_garbage_route_demanding(mode, fake_codex, monkeypatch):
    monkeypatch.setenv("ROUTE_FAKE_JUDGE", mode)
    result = route.route_bead(
        _gray_bead(),
        codex_path=fake_codex,
        judge_timeout_seconds=0.05 if mode == "timeout" else None,
    )

    assert result["class"] == "Demanding"
    assert result["judge"]["error"]


def test_gray_floor_is_standard_and_judge_selects_class(fake_codex):
    result = route.route_bead(_gray_bead(), codex_path=fake_codex)

    assert result["class"] == "Standard"
    assert result["floor"] == "Standard"
    assert result["judge"]["used"] is True


def test_multiple_route_labels_keep_the_highest_class(fake_codex):
    result = route.route_bead(_gray_bead(labels=["route:standard", "route:demanding"]), codex_path=fake_codex)

    assert result["class"] == "Demanding"


def test_unknown_route_label_refuses(fake_codex):
    with pytest.raises(route.RouteError, match="unknown route class label"):
        route.route_bead(_gray_bead(labels=["route:unrated"]), codex_path=fake_codex)


def test_new_skill_identity_source_changes_classification_without_router_edit(tmp_path):
    skills = tmp_path / "src" / "cairn" / "skills"
    skills.mkdir(parents=True)
    identity_path = tmp_path / "docs" / "late-added.txt"
    identity_path.parent.mkdir(parents=True)
    identity_path.write_text("identity source")
    skill_path = skills / "late_added.py"
    skill_path.write_text('IDENTITY_SOURCES = ("src/cairn/skills/late_added.py",)\n')

    initial = route.route_bead(
        {"id": "late-skill", "description": "Touches: docs/late-added.txt"},
        root=tmp_path,
    )
    skill_path.write_text('IDENTITY_SOURCES = ("src/cairn/skills/late_added.py", "docs/late-added.txt")\n')
    extended = route.route_bead(
        {"id": "late-skill", "description": "Touches: docs/late-added.txt"},
        root=tmp_path,
    )

    assert initial["class"] == "Mechanical"
    assert extended["class"] == "Critical"


def test_identity_sources_match_the_test_registry():
    identity_spec = spec_from_file_location(
        "identity_source_contract", Path(__file__).resolve().parent / "test_identity_sources.py"
    )
    assert identity_spec is not None
    assert identity_spec.loader is not None
    identity_contract = module_from_spec(identity_spec)
    identity_spec.loader.exec_module(identity_contract)

    assert set(route._skill_sources(route.ROOT)) == set(identity_contract.REGISTRIES["skill revision"]())
    assert set(route._gate_bundle_sources()) == set(identity_contract.REGISTRIES["gate bundle"]())


def test_empty_skill_identity_registry_refuses(tmp_path):
    (tmp_path / "src" / "cairn" / "skills").mkdir(parents=True)

    with pytest.raises(route.RouteError, match="skill identity registry is empty"):
        route.route_bead({"id": "docs", "description": "Rewrite README.md."}, root=tmp_path)


def test_unknown_paths_remain_gray(fake_codex):
    result = route.route_bead({"id": "unknown", "description": "Touches: mystery.area"}, codex_path=fake_codex)

    assert result["class"] == "Standard"
    assert result["judge"]["used"] is True


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("README.md", "README.md"),
        (".beads/issues.jsonl", ".beads/issues.jsonl"),
        ("./src/cairn/skills/toy_curve.py", "src/cairn/skills/toy_curve.py"),
    ],
)
def test_path_tokens_preserve_dot_paths_and_ignore_dotted_identifiers(text, expected):
    paths = route._paths_from_text(f"pathlib.Path('{text}')")

    assert expected in paths
    assert "pathlib.Path" not in paths


@pytest.mark.parametrize("path", ["docs/probe.json", "research/probe.json", ".beads/issues.jsonl"])
def test_noncode_paths_under_documentation_roots_route_mechanical(path):
    result = route.route_bead({"id": "docs", "description": f"Touches: {path}"})

    assert result["class"] == "Mechanical"
    assert result["judge"]["used"] is False


def test_code_path_under_research_remains_gray(fake_codex):
    result = route.route_bead(
        {"id": "research-code", "description": "Touches: research/probe.py"},
        codex_path=fake_codex,
    )

    assert result["class"] == "Standard"
    assert result["judge"]["used"] is True


def test_judge_invalid_utf8_routes_demanding(tmp_path):
    executable = tmp_path / "codex"
    executable.write_text(
        f"#!{sys.executable}\n"
        "import pathlib, sys\n"
        "pathlib.Path(sys.argv[sys.argv.index('-o') + 1]).write_bytes(b'\\xff')\n"
    )
    executable.chmod(0o755)

    result = route.route_bead(_gray_bead(), codex_path=[sys.executable, str(executable)])

    assert result["class"] == "Demanding"
    assert result["judge"]["error"]


def test_cli_loads_br_json_and_invokes_fake_codex(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    bead = {
        "id": "cli-gray",
        "title": "Handle bounded input",
        "description": "Touches: tests/unit/new_test.py",
    }
    br = bin_dir / "br"
    br.write_text(f"#!{sys.executable}\nimport json\nprint(json.dumps([{json.dumps(bead)}]))\n")
    br.chmod(0o755)
    codex = bin_dir / "codex"
    codex.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        "args = sys.argv[1:]\n"
        "schema = json.loads(pathlib.Path(args[args.index('--output-schema') + 1]).read_text())\n"
        "record = {'model': args[args.index('-m') + 1], 'effort': args[args.index('-c') + 1], 'schema': schema}\n"
        "pathlib.Path(__import__('os').environ['ROUTE_FAKE_RECORD']).write_text(json.dumps(record))\n"
        "pathlib.Path(args[args.index('-o') + 1]).write_text(json.dumps({'class': 'Standard', 'reason': 'bounded work'}))\n"
    )
    codex.chmod(0o755)
    record_path = tmp_path / "judge-record.json"
    env = os.environ.copy()
    env["PATH"] = str(bin_dir)
    env["ROUTE_FAKE_RECORD"] = str(record_path)

    result = subprocess.run(
        [sys.executable, str(ROUTE_SCRIPT_PATH), "cli-gray"],
        cwd=route.ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    record = json.loads(record_path.read_text())
    assert output["class"] == "Standard"
    assert output["floor"] == "Standard"
    assert set(output) == {"class", "reasons", "floor", "judge"}
    assert output["judge"]["used"] is True
    assert record["model"] == route.JUDGE_MODEL
    assert record["effort"] == f"model_reasoning_effort={route.JUDGE_EFFORT}"
    assert record["schema"]["properties"]["class"]["enum"] == ["Standard", "Demanding"]
