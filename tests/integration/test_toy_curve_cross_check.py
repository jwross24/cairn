import json
from pathlib import Path

import gmpy2
import pytest

from cairn import bundle, canon, claims, justify, keys, m0, pari, runner, selftest, substrate, tiergate
from cairn.skills import instance_maker, order_bsgs_gmpy2, toy_curve

FIXTURES = str(Path(__file__).resolve().parents[1] / "fixtures")


def test_sixty_bit_run_has_independent_implementation_agreement():
    out = toy_curve.run(60, 1)
    assert out.status == "OK"
    assert out.cross_check == [
        {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "untested"},
        {"axis": "implementation", "independent_range": {"bits": [30, 60]}, "result": "agree"},
    ]
    assert int(order_bsgs_gmpy2.group_order(out.p, out.a, out.b, [out.P])) == out.n


def test_real_certificate_attributes_sixty_bit_coverage_to_implementation(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        certificate = selftest.certify(sub, gate.verifier_config())
        summary = json.loads(sub.get_certificate(certificate["identity_bundle_hash"])["selftest_summary"])
        assert summary["cross_check"] == [
            {"axis": "algorithm", "independent_range": {"bits": [0, 50]}},
            {"axis": "implementation", "independent_range": {"bits": [30, 60]}},
        ]
        assert justify.cross_check_covers(summary["cross_check"][:1], {"bits": 60}).covered is False
        assert justify.cross_check_covers(summary["cross_check"], {"bits": 60}).record() == {
            "covered": True,
            "dimensions": {"bits": True},
            "contributions": {"bits": {"implementation": [60, 60]}},
        }
        assert summary["randomized_arm"] is True
        assert justify.producer_capped(summary, {"bits": 60}) is False


def test_seventy_bit_profile_refuses_a_tier_zero_launch(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        certificate = selftest.certify(sub, gate.verifier_config())
        hypothesis = claims.HypothesisObject(**m0._hypothesis(70))
        claims.write_hypothesis_object(sub, hypothesis)
        decision = tiergate.TierGate(sub, gate).admit(
            tiergate.Launch(
                cost_profile=toy_curve.COST_PROFILE,
                inputs=70,
                budget_remaining=100,
                hypothesis_key=hypothesis.hash,
                method_identity=hypothesis.method_identity,
                skill_identity_hash=certificate["identity_bundle_hash"],
                declared_tier=0,
            )
        )
        assert isinstance(decision, tiergate.TierRefused)
        assert decision.reasons == ("boundary-table",)
        recorded = claims.get_gate_run(sub, decision.gate_run_hash)
        assert recorded["result"] == "refused" and json.loads(recorded["reasons"]) == ["boundary-table"]


def test_real_gmp_order_plus_one_is_disagree_and_persisted(tmp_path, load_vector):
    identity = toy_curve.identity_bundle()
    recipe = {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {},
        "seed": 1,
        "tool_versions": identity["tool_digests"],
        "container_digest": identity["container_digest"],
        "salt": "implementation-order-plus-one",
    }
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        attempt = runner.launch(
            sub,
            "skills.toy_curve_order_offset",
            recipe,
            stdin_document={"bits": 60, "seed": 1},
            bundle_hash="ab" * 32,
            evaluation=toy_curve.COST_PROFILE.evaluate(60),
            ceiling_multiplier=10,
            tool_digests=identity["tool_digests"],
            scratch_root=tmp_path / "runs",
            env_extra={"PYTHONPATH": FIXTURES},
            skip_cache_lookup=True,
        )
        assert attempt.status == "DISAGREE"
        assert sub.get_node(attempt.output_manifest_hash) is not None
        assert sub.manifest_blobs_present(attempt.output_manifest_hash)
        row = sub.conn.execute(
            "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = 'member'",
            (attempt.output_manifest_hash,),
        ).fetchone()
        assert row is not None
        out = toy_curve.ToyCurveOutput.from_json(sub.get_blob(row["child_hash"]).decode())
        vector = load_vector("curve60_seed1.json")
        assert out.status == "DISAGREE"
        assert all(out.to_wire()[name] == vector[name] for name in ("p", "a", "b", "n", "P", "tries"))
        assert out.cross_check == [
            {"axis": "algorithm", "independent_range": {"bits": [0, 50]}, "result": "untested"},
            {"axis": "implementation", "independent_range": {"bits": [30, 60]}, "result": "disagree"},
        ]
        first, second = out.transcripts
        assert [first["call"], second["call"]] == ["ellsea_early_abort", "gmpy2_bsgs"]
        assert first["result"] == out.n and second["result"] == out.n + 1
        for transcript in out.transcripts:
            body = {name: transcript[name] for name in toy_curve.TRANSCRIPT_BODY.names}
            assert transcript["curve"] == [out.a, out.b, out.p]
            assert transcript["digest"] == keys.node_hash(
                toy_curve.TRANSCRIPT_BODY.name, canon.encode(toy_curve.TRANSCRIPT_BODY, body)
            )
        assert first["digest"] != second["digest"]
        print(json.dumps({"manifest": attempt.output_manifest_hash, "stdout_blob": row["child_hash"], **out.to_wire()}))


@pytest.mark.parametrize(("bits", "seed"), [(3, 2), (28, 1), (70, 1)])
def test_implementation_does_not_run_outside_its_declared_range(monkeypatch, bits, seed):
    def forbidden(*args, **kwargs):
        raise AssertionError("implementation oracle outside declared range")

    monkeypatch.setattr(order_bsgs_gmpy2, "group_order", forbidden)
    out = toy_curve.run(bits, seed)
    assert out.status == "OK" and out.cross_check[1]["result"] == "untested"
    if bits == 3:
        assert (out.p, out.a, out.b, out.n, out.P) == (5, 3, 3, 5, (4, 2))


@pytest.mark.parametrize("module", [toy_curve, instance_maker])
@pytest.mark.parametrize(("name", "accessor"), [("gmpy2", "version"), ("gmp", "mp_version")])
def test_independent_dependency_versions_move_skill_identity(monkeypatch, module, name, accessor):
    before = module.skill_identity_hash()
    assert module.identity_bundle()["tool_digests"][name] == getattr(gmpy2, accessor)()
    monkeypatch.setattr(gmpy2, accessor, lambda: "planted-version")
    assert module.skill_identity_hash() != before


def test_maker_identity_tracks_the_independent_order_source(tmp_path):
    for rel in instance_maker.IDENTITY_SOURCES:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((instance_maker.REPO_ROOT / rel).read_bytes())
    before = instance_maker.implementation_revision(tmp_path)
    source = tmp_path / "src/cairn/skills/order_bsgs_gmpy2.py"
    assert source.is_file()
    source.write_bytes(source.read_bytes() + b"\n")
    assert instance_maker.implementation_revision(tmp_path) != before


def test_maker_preserves_both_axis_disagreement_transcripts(monkeypatch):
    real_sea, real_gmp = pari.ellsea, order_bsgs_gmpy2.group_order
    monkeypatch.setattr(pari, "ellsea", lambda *args, **kwargs: real_sea(*args, **kwargs) + 2)
    monkeypatch.setattr(order_bsgs_gmpy2, "group_order", lambda *args, **kwargs: real_gmp(*args, **kwargs) + 1)
    out = instance_maker.run(40, 1)
    assert out.status == "DISAGREE"
    assert [transcript["call"] for transcript in out.transcripts] == ["ellcard", "ellsea", "gmpy2_bsgs"]
    assert [transcript["result"] for transcript in out.transcripts] == [out.n, out.n + 2, out.n + 1]
    assert len({transcript["digest"] for transcript in out.transcripts}) == 3
