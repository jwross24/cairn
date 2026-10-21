import copy

import pytest
from _toy_curve_support import (
    PLATFORM_SKIP,
    _certificate_rows,
    _config,
    _edit_one_row,
    _paths,
    _run,
    _writable_copy,
)

from cairn import env, exits, keys, pari, selftest, substrate, verifier
from cairn.skills import toy_curve

pytestmark = PLATFORM_SKIP


def test_the_verifier_arm_refuses_every_wrong_draw(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    body = selftest.verifier_arm(out, config, seed)
    assert body["reasons"] == {"xP-ne-Q": selftest.DRAW_COUNT}


def test_a_field_without_an_origin_is_refused_before_any_case_runs(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    calls = []
    for name in ("ellcard", "ellsea", "ellorder"):
        real = getattr(pari, name)
        monkeypatch.setattr(
            pari,
            name,
            lambda *a, _n=name, _r=real, **k: (calls.append(_n), _r(*a, **k))[1],
        )
    reached = []
    monkeypatch.setattr(
        selftest,
        "run_case",
        lambda case: reached.append(case["id"]) or (None, True, {}),
    )
    doc = copy.deepcopy(selftest.load_corpus())
    del doc["cases"][1]["fields"]["P"]["origin"]
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.CorpusSchemaError, match=r"\$\.cases\[1\]\.fields\.P"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
    assert calls == [] and reached == []
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_pin_that_does_not_match_aborts_before_any_case_runs(tmp_path, pinned_bundle, capsys, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    tampered = _writable_copy(bundle_path, tmp_path / "tampered.sqlite")
    _edit_one_row(tampered)
    calls = []
    monkeypatch.setattr(selftest, "run_case", lambda case: calls.append(case["id"]) or (None, True, {}))
    db = tmp_path / "substrate.sqlite"
    code, out, err = _run(
        [
            "selftest",
            "toy-curve",
            "--bundle",
            str(tampered),
            "--pin",
            str(pin_path),
            "--db",
            str(db),
            "--json",
        ],
        capsys,
    )
    assert code == exits.GATE_REFUSED
    assert out == "" and "chflags nouappnd" in err
    assert calls == []
    assert _certificate_rows(db) == []


def test_a_missing_bundle_exits_environment(tmp_path, capsys):
    code, out, err = _run(
        [
            "selftest",
            "toy-curve",
            "--bundle",
            str(tmp_path / "absent.sqlite"),
            "--pin",
            str(tmp_path / "absent.pin"),
            "--db",
            str(tmp_path / "substrate.sqlite"),
        ],
        capsys,
    )
    assert code == exits.ENVIRONMENT
    assert out == "" and "absent.sqlite" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_the_double_run_is_byte_equal(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    first = selftest.run_once(config)
    second = selftest.run_once(config)
    assert first["transcript"] == second["transcript"]
    assert first["transcript_hash"] == second["transcript_hash"]
    assert len(first["records"]) == 6


LEDGER_CASES = [
    ("F5", "pass", "ellmul"),
    ("GF101", "pass", "ellorder"),
    ("bits150", "pass", "order_kills"),
    ("negative_control", "pass", "order_does_not_kill"),
]


@pytest.mark.parametrize(
    ("case_id", "expected_ledger", "postcondition"),
    LEDGER_CASES,
    ids=["F5", "GF101", "bits150", "negative_control"],
)
def test_the_ledger_entry_and_postcondition_of_every_case(case_id, expected_ledger, postcondition):
    case = next(c for c in selftest.load_corpus()["cases"] if c["id"] == case_id)
    assert case["ledger"] == expected_ledger
    assert postcondition in case["postconditions"]
    observed, held, per_check = selftest.run_case(case)
    assert held and per_check[postcondition]
    assert set(observed) == set(case["postconditions"])


def _result(accepted, reason):
    return verifier.VerifierResult(
        instance_hash="00" * 32,
        x=1,
        accepted=accepted,
        reason=reason,
        reasons=() if reason is None else (reason,),
        stdout_digest="00" * 32,
        stderr_digest="00" * 32,
        rc=0 if accepted else 1,
        wall_s=0.0,
        spawned=True,
    )


@pytest.mark.parametrize(
    ("behavior", "match"),
    [
        ("accept_everything", "was accepted"),
        ("refuse_everything", "was refused"),
        ("wrong_reason", "unexpected refusal reasons"),
    ],
)
def test_the_verifier_arm_refuses_a_driver_that_misbehaves(tmp_path, pinned_bundle, monkeypatch, behavior, match):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    real = verifier.Verifier.run
    if behavior == "accept_everything":
        replacement = lambda self, instance, x: _result(True, None)  # noqa: E731
    elif behavior == "refuse_everything":
        replacement = lambda self, instance, x: _result(False, "xP-ne-Q")  # noqa: E731
    else:

        def replacement(self, instance, x):
            result = real(self, instance, x)
            return result if result.accepted else _result(False, "nQ-not-O")

    monkeypatch.setattr(verifier.Verifier, "run", replacement)
    with pytest.raises(selftest.SelftestFailed, match=match):
        selftest.verifier_arm(out, config, seed)


def test_the_verifier_arm_drives_the_real_verifier_once_per_draw(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    config = _config(bundle_path, pin_path)
    seed = selftest.arm_seed(toy_curve.implementation_revision()) or 1
    out, _ = selftest.postcondition_arm(seed)
    submitted = []
    real = verifier.Verifier.run

    def spy(self, instance, x):
        submitted.append(x)
        return real(self, instance, x)

    monkeypatch.setattr(verifier.Verifier, "run", spy)
    body = selftest.verifier_arm(out, config, seed)
    assert body["ok"] == body["fail"] == selftest.DRAW_COUNT
    assert len(submitted) == 2 * selftest.DRAW_COUNT
    assert submitted[0::2] == selftest._draws(seed, out.n, selftest.DRAW_COUNT, b"verifier-x")
    assert all(a != b for a, b in zip(submitted[0::2], submitted[1::2], strict=True))


def test_a_case_below_the_floor_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    doc = copy.deepcopy(selftest.load_corpus())
    doc["cases"][2]["ledger"] = "known_gap"
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="below the floor 4"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path), doc=doc)
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_diverging_double_run_refuses(tmp_path, pinned_bundle, monkeypatch):
    bundle_path, pin_path = pinned_bundle()
    real = selftest.run_once
    seen = []

    def drifting(config, *, doc=None, root=None):
        result = real(config, doc=doc, root=root)
        seen.append(1)
        if len(seen) == 2:
            result = {**result, "transcript": result["transcript"] + b"drift"}
        return result

    monkeypatch.setattr(selftest, "run_once", drifting)
    with (
        substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub,
        pytest.raises(selftest.SelftestFailed, match="double-run"),
    ):
        selftest.certify(sub, _config(bundle_path, pin_path))
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_a_recorded_certificate_that_differs_from_the_minted_one_refuses(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    identity = toy_curve.identity_bundle()
    identity_hash = keys.identity_bundle_hash(identity)
    env_hash = keys.env_manifest_digest(env.manifest())
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        sub.put_identity_bundle(identity)
        planted = sub.put_certificate(identity_hash, "ab" * 32, env_hash, {"planted": 1})
        with pytest.raises(selftest.SelftestFailed, match="differs from the minted"):
            selftest.certify(sub, _config(bundle_path, pin_path))
        assert sub.get_certificate(identity_hash)["cert_hash"] == planted
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1


def test_a_malformed_corpus_exits_user_input(tmp_path, pinned_bundle, capsys, monkeypatch):
    argv, _, _ = _paths(tmp_path, pinned_bundle)

    def raiser(*a, **k):
        raise selftest.CorpusSchemaError("$.cases[0].fields.P", "field is missing origin")

    monkeypatch.setattr(selftest, "certify", raiser)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.USER_INPUT
    assert out == "" and "$.cases[0].fields.P" in err and "--log DEBUG" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


@pytest.mark.parametrize(
    "error",
    [
        selftest.SelftestFailed("floor", "3 passing cases is below the floor 4"),
        toy_curve.PostconditionFailed("isprime", "n is not prime"),
    ],
    ids=["selftest-failed", "postcondition-failed"],
)
def test_a_failing_selftest_exits_gate_refused(tmp_path, pinned_bundle, capsys, monkeypatch, error):
    argv, _, _ = _paths(tmp_path, pinned_bundle)

    def raiser(*a, **k):
        raise error

    monkeypatch.setattr(selftest, "certify", raiser)
    code, out, err = _run(["selftest", "toy-curve", *argv, "--json"], capsys)
    assert code == exits.GATE_REFUSED
    assert out == "" and "--log DEBUG" in err
    assert _certificate_rows(tmp_path / "substrate.sqlite") == []


def test_without_json_the_command_prints_the_certificate_hash(tmp_path, pinned_bundle, capsys):
    argv, _, _ = _paths(tmp_path, pinned_bundle)
    code, out, err = _run(["selftest", "toy-curve", *argv], capsys)
    assert code == exits.OK, err
    with substrate.Substrate.open(tmp_path / "substrate.sqlite", role="reader") as sub:
        row = sub.get_certificate(toy_curve.skill_identity_hash())
    assert out.strip() == row["cert_hash"]


def test_an_identity_node_already_present_is_not_written_twice(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    identity = toy_curve.identity_bundle()
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        sub.put_identity_bundle(identity)
        result = selftest.certify(sub, _config(bundle_path, pin_path))
        assert result["recorded"] == "inserted"
        assert sub.certified(result["identity_bundle_hash"])
    assert len(_certificate_rows(tmp_path / "substrate.sqlite")) == 1
