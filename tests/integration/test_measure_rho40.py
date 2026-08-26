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
