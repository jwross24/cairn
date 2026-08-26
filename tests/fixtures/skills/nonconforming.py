import json
import os
import sys
from pathlib import Path

import blake3

from cairn import canon, env, keys, log, pari
from cairn.profile import CostProfile, Production, SizeCost, Verification

INTERFACE_VERSION = "bad"
SEAM = "cairn.pari.ellsea"
CROSS_CHECK_AXIS = "algorithm"
INDEPENDENT_RANGE = {"bits": [0, 50]}
REPO_ROOT = Path(__file__).resolve().parents[3]
IDENTITY_SOURCES = (
    "tests/fixtures/skills/nonconforming.py",
    "tests/fixtures/skills/nonconforming_corpus.json",
)
CORPUS_PATH = Path(__file__).resolve().parent / "nonconforming_corpus.json"
SUBSTRATE_ENV = "CAIRN_DB"
STATUS_OK = "OK"
LOG_STEP = "skill.nonconforming"
P = 1048583
A = 2
B = 3
BITS = 20

COST_PROFILE = CostProfile(
    tier=0,
    production=Production(
        model="constant",
        per_size={BITS: SizeCost(1.0, 0.0, 1.0e-3, 0.05), 60: SizeCost(1.0, 0.0, 1.0e-3, 0.05)},
    ),
    verification=Verification(grade="Replayable", cost_model="same_as_production"),
    source="fixture: a fixed curve, no measurement behind the numbers",
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
    sea = int(pari.ellsea(E))
    lg.info("run", bits=bits, seed=seed, card=card, sea=sea)
    return {
        "bits": bits,
        "seed": seed,
        "p": str(P),
        "a": str(A),
        "b": str(B),
        "n": str(card),
        "sea": str(sea),
        "cross_check": {
            "axis": CROSS_CHECK_AXIS,
            "independent_range": {k: list(v) for k, v in INDEPENDENT_RANGE.items()},
            "result": "agree" if bits <= INDEPENDENT_RANGE["bits"][1] else "untested",
        },
        "substrate": os.environ.get(SUBSTRATE_ENV) or "",
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
    document = run(bits, seed)
    stdout.write(json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
