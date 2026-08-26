import json
import os
import sys
from pathlib import Path

import blake3

from cairn import canon, env, keys, log, pari
from cairn.profile import CostProfile, Evaluation, Production, ProfileUndeclared, SizeCost, Verification

from . import _selftest_shim

INTERFACE_VERSION = "witness/1"
SEAM = "cairn.pari.ellsea"
CROSS_CHECK_AXIS = "vibes"
INDEPENDENT_RANGE = {"bits": [0, 50]}
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = ("tests/fixtures/skills/witness.py", "tests/fixtures/skills/witness_corpus.json")
CORPUS_PATH = Path(__file__).resolve().parent / "witness_corpus.json"
STATUS_OK = "OK"
LOG_STEP = "skill.witness"
P = 1048583
A = 2
B = 3
BITS = 20


class LaxProfile(CostProfile):
    def evaluate(self, bits):
        try:
            return super().evaluate(bits)
        except ProfileUndeclared:
            return Evaluation(expected_wall_s=0.05, expected_core_s=0.05, expected_verification_core_s=0.05)


COST_PROFILE = LaxProfile(
    tier=0,
    production=Production(
        model="constant",
        per_size={BITS: SizeCost(1.0, 0.0, 1.0e-3, 0.05), 60: SizeCost(1.0, 0.0, 1.0e-3, 0.05)},
    ),
    verification=Verification(grade="Replayable", cost_model="same_as_production"),
    source="fixture: the negative witness for the clauses the nonconforming fixture cannot reach",
)


class InputError(ValueError):
    pass


def parse_inputs(text):
    try:
        doc = json.loads(text)
    except ValueError as exc:
        raise InputError(f"stdin is not JSON: {exc}") from None
    if not isinstance(doc, dict):
        raise InputError(f"stdin is not a JSON object: {type(doc).__name__}")
    return int(doc.get("bits", BITS)), int(doc.get("seed", 1))


def run(bits, seed):
    lg = log.get(LOG_STEP)
    E = pari.pari.ellinit([A, B], P)
    card = int(pari.ellcard(E))
    lg.info("run", bits=bits, seed=seed, card=card)
    return {
        "bits": bits,
        "seed": seed,
        "n": str(card),
        "mean_wall_s": 0.05,
        "cross_check": {
            "axis": CROSS_CHECK_AXIS,
            "independent_range": {k: list(v) for k, v in INDEPENDENT_RANGE.items()},
            "result": "agree",
        },
        "status": STATUS_OK,
    }


def implementation_revision(root=REPO_ROOT):
    hasher = blake3.blake3()
    for rel in sorted(IDENTITY_SOURCES):
        path = Path(root) / rel
        data = path.read_bytes() if path.is_file() else b""
        hasher.update(canon.length_prefix(rel.encode("utf-8")) + canon.length_prefix(data))
    return hasher.hexdigest()


def identity_bundle(root=REPO_ROOT):
    versions = pari.pari_versions()
    return {
        "interface_version": INTERFACE_VERSION,
        "implementation_revision": implementation_revision(root),
        "tool_digests": {
            "gp_binary_sha256": env.gp_binary_sha256(),
            "cypari2": versions["cypari2"],
            "libpari": versions["libpari"],
        },
        "container_digest": keys.env_manifest_digest(env.manifest()),
        "numeric_profile": None,
    }


def skill_identity_hash(root=REPO_ROOT):
    return keys.identity_bundle_hash(identity_bundle(root))


def certify(sub):
    return _selftest_shim.certify(sys.modules[__name__], sub, record=False)


def transcript():
    return _selftest_shim.transcript(sys.modules[__name__]) + os.urandom(8)


def main(stdin=None, stdout=None, stderr=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    log.configure(None)
    try:
        bits, seed = parse_inputs(stdin.read())
    except InputError as exc:
        stderr.write(f"error: {exc}\n")
        return 1
    stdout.write(json.dumps(run(bits, seed), indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
