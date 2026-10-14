import ast
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from math import isqrt
from pathlib import Path

import pytest

from cairn.slopemodel import slopemodel_a, slopemodel_b, slopemodel_sweep_a, slopemodel_sweep_b

ROOT = Path(__file__).resolve().parents[2]
PRIMES_PATH = ROOT / "tests" / "vectors" / "slope_validation_primes.json"
PRIMES = json.loads(PRIMES_PATH.read_text())
CI_PRIMES = [ell for ell in PRIMES if ell < 2**18]
SWEEPS = (slopemodel_sweep_a, slopemodel_sweep_b)


def chain_free_reference(ell, n):
    initial = [(0, 0), (0, 1), (1, 0), (2, 0)]
    initial.extend((x, y % ell) for t in range(1, ell + 1) for x, y in ((0, t), (1, t * n), (2, -t * (n + 1))))
    points = []
    seen = set()
    first = {}
    for point in initial:
        if point in seen:
            continue
        x, y = point
        index = len(points)
        for previous_x, previous_y in points:
            if previous_x != x:
                residue = (y - previous_y) * pow(x - previous_x, -1, ell) % ell
                first.setdefault(residue, index)
        seen.add(point)
        points.append(point)
        if len(first) == ell:
            return sum(first.values()), max(first.values())
    raise AssertionError("chain-free reference did not cover every residue")


def test_validation_primes_are_the_frozen_distinct_domain():
    assert hashlib.sha256(PRIMES_PATH.read_bytes()).hexdigest() == (
        "f902d3acd2d6e009e747907c145a76b6ef8fd553c21460a93a91fdd5cbf1c7db"
    )
    assert len(PRIMES) == len(set(PRIMES)) == 396
    assert sorted(PRIMES) == PRIMES
    assert (PRIMES[0], PRIMES[-1]) == (5, 4194007)
    assert all(slopemodel_b.is_prime(ell) for ell in PRIMES)


def assert_agreement(ell, reference_a=slopemodel_a, sweep_a=slopemodel_sweep_a):
    n = (564 * isqrt(ell) + 500) // 1000
    first = reference_a.weight(ell, n)
    second = slopemodel_b.weight(ell, n)
    assert first == second, ("point references", ell, first, second)
    actual_a = sweep_a.weight(ell, n)
    actual_b = slopemodel_sweep_b.weight(ell, n)
    assert actual_a == first, ("sweep-a", ell, actual_a, first)
    assert actual_b == second, ("sweep-b", ell, actual_b, second)


@pytest.mark.parametrize("ell", CI_PRIMES)
def test_sweeps_agree_with_both_point_sequence_references(ell):
    assert_agreement(ell)


@pytest.mark.slow
@pytest.mark.parametrize("ell", PRIMES)
def test_all_validation_primes_agree(ell):
    assert_agreement(ell)


@pytest.mark.parametrize(
    ("engine", "original", "replacement", "label", "argument"),
    [
        (
            slopemodel_sweep_a,
            "add(top - t, top, 3 * t + 1, 0)",
            "add(top - t, top, 3 * t, 0)",
            "sweep-a",
            "sweep_a",
        ),
        (
            slopemodel_a,
            "for x, y in ((0, t), (1, t * n), (2, -t * (n + 1))):",
            "for x, y in ((2, -t * (n + 1)), (1, t * n), (0, t)):",
            "point references",
            "reference_a",
        ),
    ],
    ids=("giant-one-arrives-early", "round-point-order-reversed"),
)
def test_agreement_refuses_planted_point_order_faults(tmp_path, engine, original, replacement, label, argument):
    assert_agreement(11)
    source = Path(engine.__file__).read_text()
    assert source.count(original) == 1
    path = tmp_path / "planted_slopemodel.py"
    path.write_text(source.replace(original, replacement))
    spec = importlib.util.spec_from_file_location("planted_slopemodel", path)
    assert spec is not None
    assert spec.loader is not None
    mutant = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mutant)
    with pytest.raises(AssertionError, match=label):
        assert_agreement(11, **{argument: mutant})


@pytest.mark.parametrize("ell", [3, 5, 7, 11, 17, 31])
def test_all_small_steps_and_chain_free_indices(ell):
    for n in range(1, ell - 1):
        expected = slopemodel_a.weight(ell, n)
        assert expected == slopemodel_b.weight(ell, n)
        chain_free = chain_free_reference(ell, n)
        for engine in SWEEPS:
            assert engine.weight(ell, n) == expected
            assert engine.weight_chain_free(ell, n) == chain_free


@pytest.mark.parametrize("engine", SWEEPS, ids=("sweep-a", "sweep-b"))
@pytest.mark.parametrize("interface", ["weight", "weight_chain_free"])
@pytest.mark.parametrize(("ell", "n"), [(2, 1), (9, 1), (True, 1), (7, 0), (7, 6), (7, True)])
def test_sweep_interfaces_refuse_invalid_parameters(engine, interface, ell, n):
    with pytest.raises(ValueError, match="must be"):
        getattr(engine, interface)(ell, n)


@pytest.mark.parametrize("engine", SWEEPS, ids=("sweep-a", "sweep-b"))
def test_sweep_refuses_values_above_its_own_domain(engine):
    with pytest.raises(ValueError, match="must be an integer"):
        engine.weight(engine.MAX_L + 1, 1)


def test_second_sweep_refuses_excessive_horizon():
    with pytest.raises(ValueError, match=r"horizon .* exceeds resource limit"):
        slopemodel_sweep_b.weight(4294967311, 1)


def test_second_sweep_refuses_excessive_correction_streams():
    with pytest.raises(ValueError, match=r"correction streams .* exceed resource limit"):
        slopemodel_sweep_b.weight(65537, 65535)


@pytest.mark.parametrize("engine", SWEEPS, ids=("sweep-a", "sweep-b"))
def test_sweep_cli_computes_from_checkout_json(engine):
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    result = subprocess.run(
        [sys.executable, "-m", engine.__name__],
        input=json.dumps({"l": 971153, "n": 556}),
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=environment,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    expected = slopemodel_a.weight(971153, 556)
    assert json.loads(result.stdout) == {"W": expected[0], "last": expected[1]}
    assert result.stderr == ""


@pytest.mark.parametrize("engine", SWEEPS, ids=("sweep-a", "sweep-b"))
def test_sweep_imports_are_standard_library_only(engine):
    tree = ast.parse(Path(engine.__file__).read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imports.append((node.module or "").split(".")[0])
    assert set(imports) <= sys.stdlib_module_names
