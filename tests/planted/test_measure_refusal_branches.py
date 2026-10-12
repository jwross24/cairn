from dataclasses import replace
from pathlib import Path

import pytest

from cairn import exits, measure, pari, verifier
from cairn.errors import CliError

REFUSING_SCRIPT = Path(__file__).resolve().parents[1] / "fixtures" / "measure" / "refuse_correct_x.gp"


class OrderSubject:
    def __init__(self, rho, *, disagree=True):
        self.rho = rho
        self.disagree = disagree
        self.runs = []

    def __call__(self, bits, **kwargs):
        run = self.rho(bits, **kwargs)
        self.runs.append(run)
        return replace(run, n=run.n + 2) if bits == measure.RHO60_BITS and self.disagree else run


def test_correct_recovered_rho40_x_is_refused_by_the_planted_verifier(monkeypatch):
    original_verifier = verifier.Verifier
    subject = OrderSubject(measure.rho, disagree=False)
    results = []

    class RefusingVerifier(original_verifier):
        def __init__(self):
            super().__init__(verifier.VerifierConfig(script=REFUSING_SCRIPT.read_bytes()))

        def run(self, instance, x):
            result = super().run(instance, x)
            results.append(result)
            return result

    with monkeypatch.context() as planted:
        planted.setattr(measure, "rho", subject)
        planted.setattr(verifier, "Verifier", RefusingVerifier)
        with pytest.raises(CliError) as refused:
            measure.rho60_report(1, measure.DEFAULT_CAP_MINUTES)

    assert refused.value.code == exits.BACKEND
    assert refused.value.what == "the 40-bit rho's x was refused by the Tier-0 verifier: xP-ne-Q"
    assert refused.value.next_command == "cairn doctor"
    assert len(subject.runs) == 1
    recovered = subject.runs[0]
    assert recovered.bits == 40 and recovered.stop == measure.STOP_SOLVED
    assert recovered.x == recovered.secret == 788702851439
    assert recovered.ops == 474179
    assert len(results) == 1
    assert results[0].spawned and results[0].rc == 1
    assert not results[0].accepted and results[0].reason == "xP-ne-Q"
    control = original_verifier().run(recovered.instance(), recovered.x)
    assert control.spawned and control.accepted and control.rc == 0


def test_planted_rho60_order_disagreement_reaches_backend(monkeypatch):
    subject = OrderSubject(measure.rho)
    with monkeypatch.context() as planted:
        planted.setattr(measure, "rho", subject)
        with pytest.raises(CliError) as refused:
            measure.rho60_report(1, measure.DEFAULT_CAP_MINUTES)

    assert refused.value.code == exits.BACKEND
    assert refused.value.what == (
        f"toy_curve(60, 1) has order {measure.RHO60_ORDER + 2}, not the recorded {measure.RHO60_ORDER}"
    )
    assert refused.value.next_command == "cairn doctor"
    assert [run.bits for run in subject.runs] == [40, 60]
    recovered, real60 = subject.runs
    assert recovered.x == recovered.secret and recovered.stop == measure.STOP_SOLVED
    assert real60.n == measure.RHO60_ORDER and real60.ops == 1 and real60.stop == measure.STOP_CAP_OPS
    curve = pari.pari.ellinit([real60.a, real60.b], real60.p)
    assert int(pari.ellcard(curve)) == real60.n
    assert int(pari.pari.ellisoncurve(curve, list(real60.P))) == 1


def test_removing_the_planted_order_disagreement_leaves_backend_branch_unreached(monkeypatch):
    subject = OrderSubject(measure.rho, disagree=False)
    with monkeypatch.context() as planted:
        planted.setattr(measure, "rho", subject)
        with pytest.raises(measure.RefusedTooFewOps, match="fewer than 1e6 ops"):
            measure.rho60_report(1, measure.DEFAULT_CAP_MINUTES)

    assert [run.bits for run in subject.runs] == [40, 60]
    assert subject.runs[1].n == measure.RHO60_ORDER
    assert subject.runs[1].ops == 1
