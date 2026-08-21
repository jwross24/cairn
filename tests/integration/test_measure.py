import json
import statistics
import sys

import pytest

from cairn import cli, exits, measure


def _run(argv, capsys):
    code = cli.main(argv)
    out, err = capsys.readouterr()
    return code, out, err


def test_measure_json_table_over_small_seed_count(capsys):
    code, out, err = _run(["measure", "toy-curve-tries", "--sizes", "30,40", "--seeds", "3", "--json"], capsys)
    assert code == exits.OK, err
    doc = json.loads(out)
    assert out.count("\n") == 1
    assert doc["schema_version"] == cli.SCHEMA_VERSION and doc["command"] == "measure"
    assert doc["target"] == "toy-curve-tries" and doc["seeds"] == 3 and doc["sizes"] == [30, 40]
    assert doc["launch_argv"] == [sys.executable, "-m", "cairn.skills.toy_curve"]
    rows = {r["bits"]: r for r in doc["rows"]}
    assert set(rows) == {30, 40}
    r30 = rows[30]
    assert (r30["seeds"], r30["min_tries"], r30["max_tries"]) == (3, 20, 148)
    assert r30["mean_tries"] == round(statistics.fmean([48, 148, 20]), 2)
    assert r30["sd_tries"] == round(statistics.stdev([48, 148, 20]), 2)
    assert rows[40]["mean_tries"] == round(statistics.fmean([40, 52, 57]), 2)
    for r in rows.values():
        assert r["mean_wall_s"] > r["in_process_mean_wall_s"] > 0
        assert r["per_try_ms"] > 0


def test_measure_text_table_is_markdown(capsys):
    code, out, err = _run(["measure", "--sizes", "30", "--seeds", "2"], capsys)
    assert code == exits.OK, err
    lines = out.splitlines()
    assert lines[0] == measure.TABLE_HEADER and lines[1] == measure.TABLE_RULE
    assert lines[2].startswith("| 30 | 2 | 98.00 | 70.71 | 48 | 148 | ")


def test_measure_empty_sizes_exits_zero_with_an_empty_table(capsys):
    code, out, err = _run(["measure", "--sizes", "", "--seeds", "5", "--json"], capsys)
    assert code == exits.OK, err
    assert json.loads(out)["rows"] == []


def test_measure_bad_sizes_exits_user_input(capsys):
    code, out, err = _run(["measure", "--sizes", "30,x", "--json"], capsys)
    assert code == exits.USER_INPUT and out == "" and "cairn measure --help" in err


def test_measure_dead_launch_subprocess_exits_backend(monkeypatch, capsys):
    monkeypatch.setenv("PYTHONHOME", "/nonexistent")
    code, out, err = _run(["measure", "--sizes", "30", "--seeds", "1", "--json"], capsys)
    assert code == exits.BACKEND and out == ""
    assert "exited" in err and "cairn doctor" in err


def test_measure_pari_error_exits_backend(capsys):
    code, out, err = _run(["measure", "--sizes", "1", "--seeds", "1", "--json"], capsys)
    assert code == exits.BACKEND and out == ""
    assert "PariError" in err
