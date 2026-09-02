import argparse

import pytest

from cairn import exits, measure
from cairn.errors import CliError


def test_a_dlp_row_reports_ops_wall_table_and_verification_columns():
    row = measure._dlp_row("bsgs", 30, [100, 300], [0.1, 0.3], [40, 40], [640, 640], [0.1, 0.3])
    assert row["mean_ops"] == 200.0 and row["sd_ops"] == pytest.approx(141.42, abs=0.01)
    assert row["min_ops"] == 100 and row["max_ops"] == 300
    assert row["per_op_us"] == pytest.approx(1000.0)
    assert row["mean_wall_s"] == 0.2 and row["sd_wall_s"] == pytest.approx(0.1414, abs=0.001)
    assert row["table_entries"] == 40.0 and row["table_bytes"] == 640.0 and row["bytes_per_entry"] == 16.0
    assert row["mean_verify_s"] == 0.2 and row["maxrss_bytes"] > 0


def test_a_single_seed_row_has_zero_spread_and_a_rho_row_has_no_table_columns():
    row = measure._dlp_row("rho-dp", 40, [5], [2.0], [None], [None], [0.001])
    assert row["sd_ops"] == 0.0 and row["sd_wall_s"] == 0.0
    assert row["table_entries"] is None and row["table_bytes"] is None and row["bytes_per_entry"] is None
    lines = measure.dlp_table_lines([row])
    assert lines[0] == measure.DLP_TABLE_HEADER and lines[1] == measure.DLP_TABLE_RULE
    assert lines[2].startswith("| rho-dp | 40 | 1 | 5.00 | 0.00 | 5 | 5 |") and "| - | - | - |" in lines[2]


def test_the_dlp_target_refuses_zero_seeds_and_sizes_default_per_target():
    ns = argparse.Namespace(target="dlp", sizes=None, seeds=0, skill="bsgs", negation_map=False, json=False)
    with pytest.raises(CliError) as info:
        measure._dlp(ns)
    assert info.value.code == exits.USER_INPUT and "--seeds must be >= 1" in info.value.what
    assert measure.parse_sizes(measure.DLP_DEFAULT_SIZES) == [28, 30, 40, 50]
    assert measure.TARGET_DLP in measure.TARGETS and measure.DLP_SKILLS == ("rho-dp", "bsgs", "instance-maker")


def test_one_measured_seed_per_skill_agrees_with_the_skills_own_output():
    ops, wall, entries, table_bytes, verify = measure._dlp_one("bsgs", 20, 1, False)
    assert (
        ops > entries > 0
        and table_bytes == entries * 8 + (1 << max(1, (2 * (entries + 1) - 1).bit_length())) * 4
        and wall > 0
        and verify == wall
    )
    ops, wall, entries, table_bytes, verify = measure._dlp_one("rho-dp", 20, 1, False)
    assert ops > 0 and entries is None and table_bytes is None and 0 < verify < wall + 1
    tries, wall, entries, table_bytes, verify = measure._dlp_one("instance-maker", 20, 1, False)
    assert tries >= 1 and entries is None and verify == wall
