import importlib
from pathlib import Path

from cairn import canon, selftest, verifier
from cairn.selftest import SelftestFailed

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = Path(__file__).resolve().parent / "skills"
RHO_DP = "rho-dp"
BSGS = "bsgs"
INSTANCE_MAKER = "instance-maker"
SLOPE_WEIGHT_A = "slope-weight-a"
SLOPE_WEIGHT_B = "slope-weight-b"
NAMES = (RHO_DP, BSGS, INSTANCE_MAKER, SLOPE_WEIGHT_A, SLOPE_WEIGHT_B)
MODULES = {
    RHO_DP: "cairn.skills.rho_dp",
    BSGS: "cairn.skills.bsgs",
    INSTANCE_MAKER: "cairn.skills.instance_maker",
    SLOPE_WEIGHT_A: "cairn.skills.slope_weight_a",
    SLOPE_WEIGHT_B: "cairn.skills.slope_weight_b",
}
CORPUS_PATHS = {
    RHO_DP: SKILLS_DIR / "rho_dp_corpus.json",
    BSGS: SKILLS_DIR / "bsgs_corpus.json",
    INSTANCE_MAKER: SKILLS_DIR / "instance_maker_corpus.json",
    SLOPE_WEIGHT_A: SKILLS_DIR / "slope_weight_a_corpus.json",
    SLOPE_WEIGHT_B: SKILLS_DIR / "slope_weight_b_corpus.json",
}
LOG_STEP = "selftest"
CASE_SEED = 1
ARM_BITS = 30
OUTCOME_PASS = "pass"
OUTCOME_REFUSED = "refused"
OUTCOME_WRONG = "wrong"
LABEL_X = {RHO_DP: b"rho-dp-x", BSGS: b"bsgs-x"}
LABEL_X_PRIME = {RHO_DP: b"rho-dp-x-prime", BSGS: b"bsgs-x-prime"}
LABEL_NONCE = b"instance-maker-nonce"
LABEL_HYPOTHESIS = b"instance-maker-hypothesis"
MAKER_VECTOR_FIELDS = ("nonce", "hypothesis_key", "bits", "trial", "seed")
MAKER_INSTANCE_FIELDS = ("p", "a", "b", "n", "P", "Q", "x")
MAKER_CASE_KEYS = ("id", "ledger", "source", "fields")
HEX_DIGITS = frozenset("0123456789abcdef")


def module_for(which):
    if which not in MODULES:
        raise KeyError(f"no self-test for {which!r}; one of {NAMES}")
    return importlib.import_module(MODULES[which])


def _values(case):
    return {name: field["value"] for name, field in case["fields"].items()}


def _instance_seed(revision):
    return selftest.arm_seed(revision) or 1


def _revision(module, root):
    return module.implementation_revision() if root is None else module.implementation_revision(root)


def _identity(module, root):
    return module.identity_bundle() if root is None else module.identity_bundle(root)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX_DIGITS


def _nonce_from(seed, label):
    material = canon.length_prefix(str(seed).encode("utf-8")) + canon.length_prefix(label)
    return canon.digest("cairn/selftest-nonce/v1", material)


def _other_scalar(seed, n, x, label):
    other = selftest._draws(seed, n, 1, label)[0]
    if other == x:
        other = x % (n - 1) + 1
    return other


def _verifier_arm(config, instance, x, other):
    driver = verifier.Verifier(config)
    accepted = driver.run(instance, x)
    if not accepted.accepted:
        raise SelftestFailed("verifier-arm", f"the skill's x = {x} was refused: {accepted.reason}")
    refused = driver.run(instance, other)
    if refused.accepted:
        raise SelftestFailed("verifier-arm", f"x' = {other} != x was accepted")
    if refused.reason != "xP-ne-Q":
        raise SelftestFailed("verifier-arm", f"unexpected refusal reason {refused.reason!r}")
    return {"ok": 1, "fail": 1, "reasons": {refused.reason: 1}, "outcome": OUTCOME_PASS}


def _result(records, ledger, passes, floor, arms, seed, doc):
    transcript = selftest.transcript_bytes(records)
    return {
        "records": records,
        "transcript": transcript,
        "transcript_hash": selftest.transcript_digest(transcript),
        "ledger": ledger,
        "passes": passes,
        "floor": floor,
        "arms": arms,
        "seed": seed,
        "origins": selftest.field_origins(doc),
    }
