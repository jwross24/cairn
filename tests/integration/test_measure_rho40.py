import json
from pathlib import Path

import pytest

from cairn import cli, exits, measure, verifier

VECTOR = Path(__file__).resolve().parents[1] / "vectors" / "curve60_seed1.json"


@pytest.fixture(scope="module")
def rho40():
    return measure.rho(measure.RHO40_BITS)


def test_rho40_walk_completes_and_recovers_the_drawn_x(rho40):
    assert rho40.stop == "solved"
    assert rho40.x == rho40.secret
    assert 0 < rho40.x < rho40.n
    assert rho40.ops >= measure.RHO_R
    assert rho40.elapsed_s > 0


def test_rho40_walk_pins_the_published_r_theta_and_op_count(rho40):
    assert (measure.RHO_R, measure.RHO_THETA_BITS) == (20, 10)
    assert rho40.ops == 474179
    assert rho40.n == 945003441719
    assert rho40.x == 788702851439


def test_a_key_without_y_mistakes_a_negation_for_a_repeat_and_the_full_key_does_not():
    run = measure.rho(24, seed=6, theta_bits=0)
    assert run.stop == "solved"
    assert run.x == run.secret
    assert run.ops == 1295


def test_rho40_x_passes_the_tier0_verifier(rho40):
    result = verifier.Verifier().run(rho40.instance(), rho40.x)
    assert result.accepted, (result.reason, result.reasons)
    assert result.gate_result == "pass"


def test_planted_off_by_one_x_fails_the_tier0_verifier(rho40):
    result = verifier.Verifier().run(rho40.instance(), (rho40.x + 1) % rho40.n)
    assert not result.accepted
    assert result.reason == "xP-ne-Q"
    assert result.gate_result == "fail"


def test_rho60_default_order_matches_the_checked_in_vector():
    vector = json.loads(VECTOR.read_text())
    assert int(vector["n"]) == measure.RHO60_ORDER
    assert vector["bits"] == measure.RHO60_BITS and vector["seed"] == measure.RHO_INSTANCE_SEED


def test_measure_rho60_under_a_tiny_cap_refuses_the_rate_and_names_cap_ops(capsys):
    code = cli.main(["measure", "rho60", "--cap-ops", "2000", "--json"])
    out, err = capsys.readouterr()
    assert code == exits.USER_INPUT and out == ""
    assert "fewer than 1e6 ops" in err and "--cap-ops" in err


def test_measure_rho60_rejects_a_nonpositive_cap(capsys):
    code = cli.main(["measure", "rho60", "--cap-ops", "0", "--json"])
    out, err = capsys.readouterr()
    assert code == exits.USER_INPUT and out == ""
    assert "--cap-ops must be >= 1" in err


def test_measure_rho60_text_output_is_a_markdown_table_with_both_rungs(capsys):
    code = cli.main(["measure", "rho60", "--cap-ops", str(measure.RHO_MIN_RATE_OPS)])
    out, err = capsys.readouterr()
    assert code == exits.OK, err
    lines = out.splitlines()
    assert lines[0] == measure.RHO_TABLE_HEADER and lines[1] == measure.RHO_TABLE_RULE
    assert lines[2].startswith(f"| {measure.RHO40_BITS} | ") and lines[2].endswith(" | solved | STRONG-EMPIRICAL |")
    assert lines[3].startswith(f"| {measure.RHO60_BITS} | {measure.RHO_MIN_RATE_OPS} | ")
    assert lines[3].endswith(f" | {measure.STOP_CAP_OPS} | {measure.EXTRAPOLATION_TAG} |")
    assert lines[4].startswith("verified_x=") and "accepted=True" in lines[4]


def test_measure_rho60_rejects_a_nonpositive_cap_minutes(capsys):
    code = cli.main(["measure", "rho60", "--cap-minutes", "0", "--json"])
    out, err = capsys.readouterr()
    assert code == exits.USER_INPUT and out == ""
    assert "--cap-minutes must be > 0" in err


def test_measure_rho60_reports_backend_when_cap_minutes_stops_the_40_bit_walk(capsys):
    code = cli.main(["measure", "rho60", "--cap-minutes", "0.0001", "--json"])
    out, err = capsys.readouterr()
    assert code == exits.BACKEND and out == ""
    assert f"the {measure.RHO40_BITS}-bit rho stopped on {measure.STOP_CAP_MINUTES}" in err


def test_measure_rho60_json_payload_carries_the_rate_and_the_conjectural_wall(capsys):
    code = cli.main(["measure", "rho60", "--cap-ops", "1000000", "--json"])
    out, err = capsys.readouterr()
    assert code == exits.OK, err
    payload = json.loads(out)
    assert payload["schema_version"] == 1
    assert payload["target"] == measure.TARGET_RHO60
    assert payload["bits"] == measure.RHO60_BITS == 60
    assert payload["instance_hash"] == "2ab1cdfeed546e0148f808eeb990973a0f369f023054e37e3bc21133100291f6"
    assert payload["ops"] == 1000000
    assert payload["stop"] == measure.STOP_CAP_OPS == "cap-ops"
    assert payload["tag"] == "CONJECTURE"
    assert payload["expected_ops"] == 1166326474
    assert payload["elapsed_s"] > 0
    assert payload["ops_per_s"] == pytest.approx(payload["ops"] / payload["elapsed_s"], rel=2e-3)
    assert payload["extrapolated_wall_s"] == pytest.approx(1166326474 / payload["ops_per_s"], rel=1e-3)
    assert payload["verified_x"] == 788702851439
    assert payload["versions"]["cypari2"] and payload["versions"]["libpari"]
    rho40 = payload["rho40"]
    assert rho40["accepted"] is True
    assert rho40["bits"] == measure.RHO40_BITS == 40
    assert rho40["ops"] == 474179
    assert rho40["stop"] == measure.STOP_SOLVED
    assert rho40["x"] == 788702851439
    assert rho40["verifier_wall_s"] > 0
