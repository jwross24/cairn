import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _substrate_helpers as helpers
import factories
from _corpus import MUST_FAIL, Entry

from cairn import bundle, claims, escrow, justify, repro, tiergate, yank
from cairn.profile import CostProfile, Evaluation, Production, SizeCost, Verification
from cairn.substrate import Substrate

OWNER = "cairn-m1-cqt.3.6"
REJECT = "REJECT"
ACCEPT = "ACCEPT"
AT = "2026-09-05T00:00:00.000000+00:00"
LATER = "2026-09-05T00:00:01.000000+00:00"
METHOD_IDENTITY = {"interface_version": "toy_curve/1", "params": {"r": "20"}}
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
LAUNCH_EVALUATION = Evaluation(1.0, 1.0, 1.0)
BUDGET_ID = "escrow/budget-refused"
SETTLEMENT_ID = "escrow/second-settlement-refused"
DEFERRED_ID = "escrow/deferred-release-refused"
YANK_ID = "yank/yanked-evidence-refused"


def _launch(cold, seed, *, module="skills.scratch_1mb", revision="aa" * 32):
    return cold.launch(
        module,
        helpers.recipe(seed=seed, skill_identity_hash=revision),
        stdin_document={"seed": seed},
        evaluation=LAUNCH_EVALUATION,
        ceiling_multiplier=4,
        tool_digests={"gp": "2.17.4"},
        env_extra={"PYTHONPATH": str(FIXTURES)},
        skip_cache_lookup=True,
    )


def _refused(operation, exception):
    try:
        operation()
    except exception:
        return True
    return False


def _certify(cold):
    revision = cold.sub.put_identity_bundle(helpers.IDENTITY_A)
    cold.sub.put_certificate(revision, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return revision


def _gate_bundle(cold):
    path = cold.scratch_root / "gate-bundle.sqlite"
    pin = cold.scratch_root / "gate-bundle.pin"
    bundle.build(bundle.REPO_ROOT / "bundle", path)
    bundle.write_pin(path, pin)
    if hasattr(os, "chflags"):
        os.chflags(pin, 0)
    return bundle.GateBundle.open(path, pin)


def _budget_profile():
    return CostProfile(
        tier=0,
        production=Production(
            model="synthetic",
            per_size={40: SizeCost(mean_tries=1.0, sd_tries=0.0, per_try_s=0.4, mean_wall_s=0.4)},
        ),
        verification=Verification(grade="Verifiable", cost_model="same_as_production"),
        source="tests/planted/family_escrow_yank.py",
    )


def budget_refused(cold):
    revision = _certify(cold)
    evaluation = _budget_profile().evaluate(40)
    if evaluation.expected_core_s > 0.5:
        raise AssertionError(evaluation)
    if evaluation.expected_core_s + evaluation.expected_verification_core_s <= 0.5:
        raise AssertionError(evaluation)
    decision = tiergate.TierGate(cold.sub, _gate_bundle(cold)).admit(
        tiergate.Launch(
            cost_profile=_budget_profile(),
            inputs=40,
            budget_remaining=0.5,
            hypothesis_key="f" * 64,
            method_identity=METHOD_IDENTITY,
            skill_identity_hash=revision,
            declared_tier=0,
        )
    )
    run = claims.get_gate_run(cold.sub, decision.gate_run_hash)
    if not isinstance(decision, tiergate.TierRefused):
        return ACCEPT
    if tiergate.BUDGET not in decision.reasons:
        raise AssertionError(decision.reasons)
    if run is None or run["result"] != "refused" or tiergate.BUDGET not in json.loads(run["reasons"]):
        raise AssertionError(run)
    return REJECT


def second_settlement_refused(cold):
    first = _launch(cold, 1)
    first_record = repro.record_witness_check(cold.sub, first.attempt_id, True, at=AT)
    spent = escrow.reservation(cold.sub, first.attempt_id)
    if (
        spent["spent_at"] != AT
        or spent["spent_by"] != f"witness_check:{first_record.hash}"
        or spent["released_at"] is not None
        or spent["released_by"] is not None
    ):
        raise AssertionError(spent)
    second_record = repro.record_witness_check(cold.sub, first.attempt_id, True, at=LATER)
    if second_record.hash == first_record.hash or escrow.reservation(cold.sub, first.attempt_id) != spent:
        raise AssertionError("a later witness check changed the first settlement")
    repeated_spend = _refused(
        lambda: escrow.spend(cold.sub, first.attempt_id, check_event="repeat"), escrow.AlreadySettled
    )

    failed = _launch(cold, 2, module="skills.disagree")
    failed_row = escrow.reservation(cold.sub, failed.attempt_id)
    if (
        failed.status != "DISAGREE"
        or failed_row["released_by"] != "status:DISAGREE"
        or failed_row["spent_at"] is not None
        or failed_row["spent_by"] is not None
    ):
        raise AssertionError(failed_row)
    if escrow.settle_on_close(cold.sub, failed.attempt_id, failed.status) is not None:
        raise AssertionError("a non-OK attempt settled twice")
    failed_release = _refused(lambda: escrow.release(cold.sub, failed.attempt_id), escrow.AlreadySettled)

    disowned = _launch(cold, 3)
    cold.sub.disown(disowned.attempt_id, at=AT)
    disowned_row = escrow.settle_on_disown(cold.sub, disowned.attempt_id, at=LATER)
    if (
        disowned_row["released_at"] != LATER
        or disowned_row["released_by"] != escrow.RELEASE_DISOWNED
        or disowned_row["spent_at"] is not None
        or disowned_row["spent_by"] is not None
    ):
        raise AssertionError(disowned_row)
    if escrow.settle_on_disown(cold.sub, disowned.attempt_id) is not None:
        raise AssertionError("a disowned attempt settled twice")
    disowned_release = _refused(lambda: escrow.release(cold.sub, disowned.attempt_id), escrow.AlreadySettled)
    return REJECT if repeated_spend and failed_release and disowned_release else ACCEPT


def _deferred_evidence(cold, attempt_id, statement):
    node = factories.evidence_node(
        "ladder_table",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        verdict="KEEP",
        attempt_id=attempt_id,
        in_sample_sizes=tuple(statement.scope["size_interval"]),
        seed=22,
    )
    claims.write_evidence_node(cold.sub, node)
    return node


def deferred_release_refused(cold):
    first = _launch(cold, 11)
    if first.status != "OK":
        raise AssertionError(first.status)
    statement = factories.claim_statement(seed=21)
    claims.write_claim_statement(cold.sub, statement)
    ticket = factories.ticket(hypothesis_key="h" * 64, tier=2, statement_hash=statement.hash, seed=21)
    claims.write_ticket(cold.sub, ticket)
    node = _deferred_evidence(cold, first.attempt_id, statement)
    before = escrow.reservation(cold.sub, first.attempt_id)
    waiting = justify.derive_tag(cold.sub, statement.hash, "unused-attestation-file")
    if waiting.tag != justify.CONJECTURE or waiting.deferred != (node.hash,):
        raise AssertionError(waiting)

    branch = _launch(cold, 11, module="skills.disagree")
    if branch.status != "DISAGREE" or branch.recipe_key != first.recipe_key:
        raise AssertionError((branch.status, branch.recipe_key, first.recipe_key))
    after = escrow.reservation(cold.sub, first.attempt_id)
    if (
        after != before
        or not escrow.standing(cold.sub, first.attempt_id)
        or claims.get_evidence_node(cold.sub, node.hash) is None
        or justify.derive_tag(cold.sub, statement.hash, "unused-attestation-file").deferred != (node.hash,)
    ):
        raise AssertionError(after)
    premature_release = _refused(lambda: escrow.release(cold.sub, first.attempt_id), escrow.ReleaseRefused)
    return REJECT if premature_release else ACCEPT


def _yank_attempts(cold, revision):
    attempts = {}
    for seed in (1, 2, 3):
        attempts[seed] = _launch(cold, seed, revision=revision)
    return attempts


def _yank_evidence(cold, attempt_id, seed):
    statement = factories.claim_statement(seed=seed)
    claims.write_claim_statement(cold.sub, statement)
    node = factories.evidence_node(
        "ladder_table",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        verdict="KEEP",
        attempt_id=attempt_id,
        in_sample_sizes=tuple(statement.scope["size_interval"]),
        seed=seed,
    )
    claims.write_evidence_node(cold.sub, node)
    return statement, node


def yanked_evidence_refused(cold):
    revision = cold.sub.put_identity_bundle(helpers.IDENTITY_A)
    attempts = _yank_attempts(cold, revision)
    first_statement, first_node = _yank_evidence(cold, attempts[1].attempt_id, 31)
    second_statement, second_node = _yank_evidence(cold, attempts[2].attempt_id, 32)
    yank_outcome = yank.record(
        cold.sub,
        yank_id="family-yank",
        skill_identity_hash=revision,
        kind=yank.HUMAN_PATH,
        attest_path="unused-attestation-file",
        reach={"skill_identity_hash": revision, "seed": [1, 2]},
        ruling=yank.Ruling("ruling-family-yank", "ab" * 32, 128),
        at=AT,
    )
    inside = (attempts[1].attempt_id, attempts[2].attempt_id)
    outside = attempts[3].attempt_id
    if set(yank_outcome.disowned) != set(inside) or yank_outcome.standing != (outside,):
        raise AssertionError(yank_outcome)
    if set(yank_outcome.released) != set(inside) or yank.current_salt(cold.sub, revision) != "family-yank":
        raise AssertionError(yank_outcome)

    ticket_refused = all(
        _refused(lambda attempt_id=attempt_id: yank.offer_as_ticket(cold.sub, attempt_id), yank.DisownedTicket)
        for attempt_id in inside
    )
    outside_ticket = yank.offer_as_ticket(cold.sub, outside)
    derived = justify.derive_tag(cold.sub, first_statement.hash, "unused-attestation-file")
    second_derived = justify.derive_tag(cold.sub, second_statement.hash, "unused-attestation-file")
    justify_refused = all(
        result.tag == justify.SPECULATION
        and result.results[0][0]["hash"] == node.hash
        and isinstance(result.results[0][1], justify.Absent)
        and result.results[0][1].reason == "disowned"
        for result, node in ((derived, first_node), (second_derived, second_node))
    )
    with Substrate.open(cold.sub.path, role="reader") as reader:
        inside_served = [reader.serve(cold.sub.get_attempt(attempt_id)["recipe_key"]) for attempt_id in inside]
        outside_served = reader.serve(cold.sub.get_attempt(outside)["recipe_key"])
    cache_refused = inside_served == [None, None] and outside_served is not None
    outside_control = (
        escrow.standing(cold.sub, outside)
        and outside_ticket["attempt_id"] == outside
        and not yank.covers_recipe(cold.sub, cold.sub.get_attempt(outside)["recipe_key"])
    )
    return REJECT if ticket_refused and justify_refused and cache_refused and outside_control else ACCEPT


ENTRIES = (
    Entry(BUDGET_ID, "escrow", MUST_FAIL, REJECT, OWNER, budget_refused, launches=False),
    Entry(SETTLEMENT_ID, "escrow", MUST_FAIL, REJECT, OWNER, second_settlement_refused),
    Entry(DEFERRED_ID, "escrow", MUST_FAIL, REJECT, OWNER, deferred_release_refused),
    Entry(YANK_ID, "yank", MUST_FAIL, REJECT, OWNER, yanked_evidence_refused),
)
