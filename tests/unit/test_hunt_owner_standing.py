from types import SimpleNamespace

import _substrate_helpers as helpers
import pytest

from cairn import hunt, repro


@pytest.fixture
def writer(tmp_path):
    with helpers.open_writer(tmp_path) as sub:
        yield sub


@pytest.mark.parametrize(
    ("grade", "reason", "standing"),
    [
        (repro.VERIFIABLE, "gate-bundle-verifier", True),
        (repro.AUDIT_ONLY, "verifier-ships-in-producer-revision", False),
        (repro.AUDIT_ONLY, "verifier-uncertified", False),
        (repro.AUDIT_ONLY, "verifier-selftest-carries-no-must-fail-witness", False),
        (repro.VERIFIABLE, "certified-independent-verifier-with-must-fail-witness", True),
    ],
)
def test_standing_uses_owner_grade_and_passes_a_skill_verifier(monkeypatch, grade, reason, standing):
    sub = object()
    plan = SimpleNamespace(executor_identity="executor", verifier_identity="verifier")
    calls = []

    def owner_grade(store, producer, verifier):
        calls.append((store, producer, verifier))
        return grade, reason

    monkeypatch.setattr(repro, "owner_grade", owner_grade)
    assert hunt._verifier_standing(sub, plan) == (standing, reason)
    assert calls == [(sub, "executor", repro.Verifier(repro.SKILL_VERIFIER, "verifier"))]


@pytest.mark.parametrize("count", [None, -1, True, "1"])
def test_malformed_must_fail_summary_refuses_standing(writer, count):
    producer = writer.put_identity_bundle(helpers.IDENTITY_A)
    verifier = writer.put_identity_bundle(helpers.IDENTITY_B)
    summary = dict(helpers.SELFTEST_SUMMARY)
    if count is not None:
        summary[repro.MUST_FAIL_KEY] = count
    writer.put_certificate(verifier, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, summary)
    plan = SimpleNamespace(executor_identity=producer, verifier_identity=verifier)
    with pytest.raises(repro.ReproError, match="carries no must_fail_witnesses count"):
        hunt._verifier_standing(writer, plan)
