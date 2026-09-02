import hashlib
import json
from pathlib import Path

import blake3
import pytest

from cairn import ec, instances, selftest, selftest_skills
from cairn.skills import instance_maker, toy_curve

SKILLS = Path(selftest_skills.SKILLS_DIR)
RHO_CORPUS = selftest.load_corpus(SKILLS / "rho_dp_corpus.json")
BSGS_CORPUS = selftest.load_corpus(SKILLS / "bsgs_corpus.json")
MAKER_CORPUS = selftest_skills.load_maker_corpus()
VECTORS = json.loads((Path(__file__).resolve().parent.parent / "vectors" / "dlp_instances.json").read_text())


def _values(case):
    return {name: field["value"] for name, field in case["fields"].items()}


def _generated(corpus):
    return [c for c in corpus["cases"] if c["source"].startswith("cairn.skills.toy_curve.run(")]


def _rederive(bits):
    curve = toy_curve.run(bits, 1)
    x = int.from_bytes(blake3.blake3(f"x/{bits}/1/1".encode()).digest(), "big") % (curve.n - 1) + 1
    Q = ec.mul(curve.p, curve.a, tuple(curve.P), x)
    return {"p": curve.p, "a": curve.a, "b": curve.b, "n": curve.n, "P": list(curve.P), "Q": list(Q), "x": x}


@pytest.mark.parametrize("case", _generated(RHO_CORPUS), ids=lambda c: c["id"])
def test_every_generated_dlp_row_rederives_from_its_stated_source(case):
    values = _values(case)
    bits = values["p"].bit_length()
    assert case["id"] == f"bits{bits}_seed1"
    assert _rederive(bits) == values


def test_the_two_dlp_corpora_vendor_the_same_cases():
    rho = (SKILLS / "rho_dp_corpus.json").read_bytes()
    bsgs = (SKILLS / "bsgs_corpus.json").read_bytes()
    assert (len(rho), hashlib.sha256(rho).hexdigest()) == (len(bsgs), hashlib.sha256(bsgs).hexdigest())
    assert RHO_CORPUS["pass_floor"] == sum(1 for c in RHO_CORPUS["cases"] if c["ledger"] == "pass") == 5
    assert [c["ledger"] for c in RHO_CORPUS["cases"]].count("intentional_non_goal") == 1


@pytest.mark.parametrize("name", sorted(VECTORS["instances"]))
def test_the_conformance_instances_rederive_and_match_the_corpus_where_shared(name):
    row = VECTORS["instances"][name]
    assert _rederive(row["bits"]) == {k: row[k] for k in ("p", "a", "b", "n", "P", "Q", "x")}
    shared = next((c for c in RHO_CORPUS["cases"] if c["id"] == name), None)
    if shared is not None:
        assert _values(shared) == {k: row[k] for k in ("p", "a", "b", "n", "P", "Q", "x")}


@pytest.mark.parametrize("case", MAKER_CORPUS["cases"], ids=lambda c: c["id"])
def test_every_maker_row_rederives_from_the_derivation_and_the_maker(case):
    values = _values(case)
    assert values["seed"] == instances.trial_seed(
        values["nonce"], values["hypothesis_key"], values["bits"], values["trial"]
    )
    if "p" in values:
        out = instance_maker.run(values["bits"], values["seed"])
        assert {
            k: (list(getattr(out, k)) if k in ("P", "Q") else getattr(out, k))
            for k in ("p", "a", "b", "n", "P", "Q", "x")
        } == {k: values[k] for k in ("p", "a", "b", "n", "P", "Q", "x")}
