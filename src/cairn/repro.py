"""The reproducibility gate's re-run policy by grade and tier (PLAN §3), and the Verifiable owner rule.

Admission re-runs a recipe, or re-checks a witness, and compares bitwise. The policy is fixed by
grade and tier: a Verifiable node's witness is always checked; a Replayable node at Tier 0 or 1 is
always re-run; a Replayable node at Tier 2 or 3 is re-run at the moment justify would derive a
class above CONJECTURE from it, and the derivation carries CONJECTURE until that re-run lands; an
AuditOnly node is inadmissible as evidence. Two successful, non-disowned attempts on one recipe
with different output manifests mark the recipe non-reproducible, both attempts kept and rooted.
Every re-run is a fresh attempt: a second attempt served from the cache is no re-run at all, and
this module refuses to record it as one.

The Verifiable owner rule: a witness is Verifiable only where its verifier is a gate-bundle object
or a certified skill whose identity bundle differs from the witness producer's and whose self-test
carries a must-FAIL witness. A witness whose only verifier ships in its producer's own revision is
AuditOnly. Grades only weaken. A certificate whose summary predates the must-FAIL count is refused
rather than read as carrying none, because a wrong AuditOnly cannot be undone.
"""

import json
from dataclasses import dataclass

from cairn import claims, log
from cairn.substrate import GRADES, SubstrateError, _now

lg = log.get("repro")

REPLAYABLE, VERIFIABLE, AUDIT_ONLY = GRADES
TIERS = claims.TIERS
CHECK_WITNESS = "check_witness"
RERUN_NOW = "rerun_now"
RERUN_ON_DERIVE = "rerun_on_derive"
INADMISSIBLE = "inadmissible"
DECISIONS = (CHECK_WITNESS, RERUN_NOW, RERUN_ON_DERIVE, INADMISSIBLE)
GATE_VERIFIER = "gate"
SKILL_VERIFIER = "skill"
MUST_FAIL_KEY = "must_fail_witnesses"
SECOND_ATTEMPT_AGREE, WITNESS_CHECK = claims.REPRO_KINDS


class ReproError(SubstrateError):
    pass


def policy(grade, tier):
    if grade not in GRADES:
        raise ReproError(f"grade must be one of {GRADES}, got {grade!r}")
    if tier not in TIERS:
        raise ReproError(f"tier must be one of {TIERS}, got {tier!r}")
    if grade == VERIFIABLE:
        return CHECK_WITNESS
    if grade == AUDIT_ONLY:
        return INADMISSIBLE
    return RERUN_NOW if tier <= 1 else RERUN_ON_DERIVE


TABLE = {(grade, tier): policy(grade, tier) for grade in GRADES for tier in TIERS}


def must_fail_witnesses(summary):
    """The must-FAIL witness count a certificate summary carries; None when it carries no such count."""
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except ValueError:
            return None
    if not isinstance(summary, dict):
        return None
    count = summary.get(MUST_FAIL_KEY)
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        return None
    return count


@dataclass(frozen=True)
class Verifier:
    kind: str
    identity_bundle_hash: str | None = None

    def __post_init__(self):
        if self.kind not in (GATE_VERIFIER, SKILL_VERIFIER):
            raise ReproError(f"verifier kind must be {GATE_VERIFIER!r} or {SKILL_VERIFIER!r}, got {self.kind!r}")
        if (self.kind == SKILL_VERIFIER) != (self.identity_bundle_hash is not None):
            raise ReproError("a skill verifier names its identity bundle hash and a gate verifier names none")


def owner_grade(sub, producer_identity, verifier):
    """The grade a witness earns from who verifies it; AuditOnly whenever the rule is not met."""
    if verifier.kind == GATE_VERIFIER:
        return VERIFIABLE, "gate-bundle-verifier"
    if verifier.identity_bundle_hash == producer_identity:
        return AUDIT_ONLY, "verifier-ships-in-producer-revision"
    if not sub.certified(verifier.identity_bundle_hash):
        return AUDIT_ONLY, "verifier-uncertified"
    certificate = sub.get_certificate(verifier.identity_bundle_hash)
    count = must_fail_witnesses(certificate["selftest_summary"])
    if count is None:
        raise ReproError(
            f"the certificate of {verifier.identity_bundle_hash} carries no {MUST_FAIL_KEY} count; "
            "re-certify the verifier before grading a witness against it"
        )
    if count == 0:
        return AUDIT_ONLY, "verifier-selftest-carries-no-must-fail-witness"
    return VERIFIABLE, "certified-independent-verifier-with-must-fail-witness"


def apply_owner_grade(sub, node_hash, producer_identity, verifier):
    grade, reason = owner_grade(sub, producer_identity, verifier)
    current = sub.effective_grade(node_hash)
    if grade != current:
        sub.weaken_grade(node_hash, grade, reason=reason)
    lg.info("owner_grade", node=node_hash, grade=grade, reason=reason, previous=current)
    return grade, reason


def rerun_launch_kwargs():
    return {"skip_cache_lookup": True, "replay": REPLAYABLE}


def _comparable(sub, attempt_id, role):
    row = sub.get_attempt(attempt_id)
    if row is None:
        raise ReproError(f"no attempt {attempt_id}")
    if row["status"] != "OK" or row["output_manifest_hash"] is None:
        raise ReproError(f"the {role} {attempt_id} is {row['status']} with no manifest; nothing to compare")
    if row["disowned_at"] is not None:
        raise ReproError(f"the {role} {attempt_id} is disowned")
    return row


def record_rerun(sub, attempt_id, rerun_attempt_id, *, attest_path, at=None):
    """A second attempt on the first's recipe, never served from cache, compared bitwise."""
    if rerun_attempt_id == attempt_id:
        raise ReproError(f"attempt {attempt_id} cannot be its own re-run")
    first = _comparable(sub, attempt_id, "attempt")
    second = _comparable(sub, rerun_attempt_id, "re-run")
    if second["recipe_key"] != first["recipe_key"]:
        raise ReproError(f"attempt {rerun_attempt_id} is on recipe {second['recipe_key']}, not {first['recipe_key']}")
    if not second["skip_cache_lookup"]:
        raise ReproError(f"attempt {rerun_attempt_id} was launched with the cache open; a re-run is a fresh attempt")
    agree = second["output_manifest_hash"] == first["output_manifest_hash"]
    marked = () if agree else tuple(sub.mark_non_reproducible(first["recipe_key"]))
    record = claims.ReproRecord(attempt_id=attempt_id, kind=SECOND_ATTEMPT_AGREE, passed=agree, at=at or _now())
    claims.write_repro_record(sub, record)
    rederived = () if agree else rederive_recipe(sub, first["recipe_key"], attest_path)
    lg.info(
        "rerun",
        attempt=attempt_id,
        rerun=rerun_attempt_id,
        passed=agree,
        record=record.hash,
        marked=list(marked),
        rederived=list(rederived),
    )
    return record, marked


def rederive_recipe(sub, recipe_key, attest_path):
    """Re-derive every claim resting on the recipe's successful attempts, marked in this call or earlier."""
    from cairn import foundations

    rows = sub.conn.execute(
        "SELECT attempt_id FROM attempts WHERE recipe_key = ? AND status = 'OK' AND disowned_at IS NULL ORDER BY rowid",
        (recipe_key,),
    ).fetchall()
    return foundations.rederive_for_attempts(sub, [r["attempt_id"] for r in rows], attest_path)


def handle_divergence(sub, recipe_key, attest_path):
    marked = tuple(sub.mark_non_reproducible(recipe_key))
    rederived = rederive_recipe(sub, recipe_key, attest_path)
    lg.info("divergence", recipe_key=recipe_key, attempts=list(marked), rederived=list(rederived))
    return marked
