import asyncio
import os
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from claude_agent_sdk import CLIConnectionError

from cairn import canary, dispatch, worker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tests.fixtures.worker_dispatch import arena

__all__ = ["arena"]

SEED = "canary-seed-1"


def _plantings():
    return tuple({"source": source, "token": canary.token(source, SEED)} for source in canary.SOURCES)


def _pass_record(sub, **overrides):
    plantings = _plantings()
    fields = {
        "form": canary.FORM_ECHO,
        "plantings": plantings,
        "observed": "the worker echoed only its handed node " + canary.control_token(SEED),
        "control_observed": " ".join(p["token"] for p in plantings),
        "handed_control_detected": True,
    }
    return canary.record(sub, **{**fields, **overrides})


def test_planting_writes_one_distinct_token_into_each_settings_source(tmp_path):
    plantings = canary.plant(tmp_path, seed=SEED)
    assert tuple(p["source"] for p in plantings) == canary.SOURCES
    assert len({p["token"] for p in plantings}) == len(canary.SOURCES)
    for planted in plantings:
        path = canary.path_for(tmp_path, planted["source"], planted["token"])
        assert path.is_file()
        assert planted["token"] in path.read_text() or planted["token"] in path.name
    assert (tmp_path / "CLAUDE.md").is_file()
    assert (tmp_path / ".claude" / "CLAUDE.md").is_file()
    skill_token = canary.token(canary.SKILL_FILE, SEED)
    assert (tmp_path / ".claude" / "skills" / f"canary-{skill_token}" / "SKILL.md").is_file()
    status_token = canary.token(canary.WORKING_TREE_STATUS, SEED)
    assert [p.name for p in tmp_path.glob("uncommitted-*.md")] == [f"uncommitted-{status_token}.md"]


def test_the_detector_sees_a_token_that_is_present_and_only_that_token():
    plantings = _plantings()
    assert canary.found("nothing planted here", plantings) == ()
    leaked = plantings[2]["token"]
    assert canary.found(f"role prompt {leaked} tail", plantings) == (canary.SKILL_FILE,)
    assert canary.found(" ".join(p["token"] for p in plantings), plantings) == canary.SOURCES


@pytest.mark.parametrize(
    ("reachable", "leaked", "handed", "verdict"),
    [
        (canary.SOURCES, (), True, canary.PASS),
        (canary.SOURCES, (canary.PROJECT_INSTRUCTIONS,), True, canary.FAIL),
        (canary.SOURCES, (), False, canary.FAIL),
        (canary.SOURCES[:3], (), True, canary.PASS),
        ((), (), True, canary.FAIL),
    ],
)
def test_a_canary_passes_only_when_every_planting_is_reachable_and_none_leaks(reachable, leaked, handed, verdict):
    assert (
        canary.verdict_for(_plantings(), reachable=reachable, leaked=leaked, handed_control_detected=handed) == verdict
    )


def test_a_record_names_the_sources_the_control_run_could_not_reach(arena):
    sub, _, _ = arena
    plantings = _plantings()
    written = _pass_record(sub, control_observed=plantings[2]["token"])
    assert written.verdict == canary.PASS
    assert written.reachable == (canary.SKILL_FILE,)
    assert set(canary.SOURCES) - set(written.reachable) == {
        canary.PROJECT_INSTRUCTIONS,
        canary.USER_INSTRUCTIONS,
        canary.WORKING_TREE_STATUS,
    }


def test_an_incomplete_planting_set_cannot_pass():
    assert (
        canary.verdict_for(_plantings()[:3], reachable=canary.SOURCES, leaked=(), handed_control_detected=True)
        == canary.FAIL
    )


def test_a_recorded_canary_is_content_addressed_append_only_and_read_back(arena):
    sub, _, _ = arena
    written = _pass_record(sub)
    assert written.verdict == canary.PASS
    assert written.form == canary.FORM_ECHO
    assert written.reachable == canary.SOURCES and written.leaked == ()
    assert written.sdk_version == worker.SDK_VERSION and written.cli_version == worker.CLI_VERSION
    assert canary.newest(sub) == written
    node = sub.get_node(written.hash)
    assert node["kind"] == canary.KIND and node["replay_grade"] == "AuditOnly"
    assert sub.is_root("ledger_row", written.hash)
    for statement in (
        f"UPDATE {canary.TABLE} SET verdict = 'pass'",
        f"DELETE FROM {canary.TABLE}",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            sub.conn.execute(statement)


def test_an_ungrounded_path_refuses_and_a_passing_canary_grounds_it(arena):
    sub, _, _ = arena
    with pytest.raises(canary.CanaryRefused, match="holds no canary record"):
        canary.require_grounded(sub)
    written = _pass_record(sub)
    assert canary.require_grounded(sub) == written


def test_a_canary_grounded_on_another_toolchain_is_stale(arena):
    sub, _, _ = arena
    _pass_record(sub, sdk_version="0.0.0-older")
    with pytest.raises(canary.CanaryRefused, match=re.escape("grounded SDK 0.0.0-older")):
        canary.require_grounded(sub)
    with pytest.raises(canary.CanaryRefused, match=re.escape("CLI 9.9.9-newer")):
        canary.require_grounded(sub, cli_version="9.9.9-newer")


def test_a_failed_canary_yanks_the_path_until_a_fresh_one_passes(arena):
    sub, _, _ = arena
    _pass_record(sub)
    assert canary.require_grounded(sub).verdict == canary.PASS
    leaking = " ".join(p["token"] for p in _plantings())
    failed = _pass_record(sub, observed=leaking)
    assert failed.verdict == canary.FAIL and failed.leaked == canary.SOURCES
    with pytest.raises(canary.CanaryRefused, match="refuse until a fresh canary passes"):
        canary.require_grounded(sub)
    assert _pass_record(sub).verdict == canary.PASS
    assert canary.require_grounded(sub).verdict == canary.PASS


def test_dispatch_refuses_while_the_canary_is_stale_and_writes_no_record(arena):
    sub, gate_bundle, node = arena
    _pass_record(sub, sdk_version="0.0.0-older")
    with pytest.raises(dispatch.DispatchRefused, match=re.escape("grounded SDK 0.0.0-older")):
        asyncio.run(dispatch.run(sub, gate_bundle, role="echo", node_ids=(node,)))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 0


def test_a_grounded_canary_lets_the_dispatch_reach_the_sdk(arena):
    sub, gate_bundle, node = arena
    _pass_record(sub)
    with pytest.raises(CLIConnectionError, match="subprocess outside the allow-list"):
        asyncio.run(dispatch.run(sub, gate_bundle, role="echo", node_ids=(node,)))
    assert sub.conn.execute("SELECT COUNT(*) FROM worker_dispatches").fetchone()[0] == 1


def test_the_control_run_options_enable_the_settings_sources_the_dispatch_suppresses(arena, tmp_path):
    sub, gate_bundle, node = arena
    prepared = dispatch._prepare(sub, gate_bundle, role="echo", node_ids=(node,))
    assert canary.options_for(prepared, tmp_path, settings_enabled=False).setting_sources == []
    assert canary.options_for(prepared, tmp_path, settings_enabled=True).setting_sources == ["project", "local"]


def test_the_settings_home_the_canary_plants_into_is_scoped_and_restored(tmp_path, monkeypatch):
    monkeypatch.setenv(canary.CONFIG_DIR_ENV, "/outer")
    monkeypatch.setenv(canary.HOME_ENV, "/outer-home")
    with canary.config_dir(tmp_path) as directory:
        assert directory == str(tmp_path / ".claude")
        assert os.environ[canary.HOME_ENV] == str(tmp_path)
    assert os.environ[canary.CONFIG_DIR_ENV] == "/outer"
    assert os.environ[canary.HOME_ENV] == "/outer-home"
    monkeypatch.delenv(canary.CONFIG_DIR_ENV)
    with canary.config_dir(tmp_path):
        pass
    assert canary.CONFIG_DIR_ENV not in os.environ
