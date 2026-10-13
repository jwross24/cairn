import json
import sys
from pathlib import Path

from cairn import canon, env, keys, pari
from cairn.slopemodel import slopemodel_a

INTERFACE_VERSION = "slope_weight_a/1"
REPLAY_GRADE = "Replayable"
DO_NOT_CACHE = True
CROSS_CHECK_AXIS = "algorithm"
INDEPENDENT_RANGE = {"l": [3, slopemodel_a.MAX_L]}
REPO_ROOT = Path(__file__).resolve().parents[3]
HUNT_MODULE = "cairn.slopemodel.slope_hunt_executor"
IDENTITY_SOURCES = (
    "src/cairn/skills/slope_weight_a.py",
    "src/cairn/skills/slope_weight_a_corpus.json",
    "src/cairn/slopemodel/slopemodel_a.py",
    "src/cairn/slopemodel/slope_predicates.py",
    "src/cairn/slopemodel/slope_hunt_executor.py",
)


class InputError(ValueError):
    pass


class PostconditionFailed(ValueError):
    pass


def run(ell, n):
    try:
        weight, last = slopemodel_a.weight(ell, n)
    except ValueError as exc:
        raise InputError(str(exc)) from None
    return {"l": ell, "n": n, "weight": weight, "last_index": last, "status": "OK"}


def check_weight(ell, n, claimed):
    if type(claimed) is not int or claimed < 0:
        raise InputError("claimed weight must be a nonnegative integer")
    out = run(ell, n)
    if out["weight"] != claimed:
        raise PostconditionFailed(f"claimed weight {claimed} differs from {out['weight']}")
    return out


def implementation_revision(root=REPO_ROOT):
    material = b"".join(
        canon.length_prefix(relative.encode()) + canon.length_prefix((Path(root) / relative).read_bytes())
        for relative in sorted(IDENTITY_SOURCES)
    )
    return canon.digest("cairn/slope-weight-implementation/v1", material)


def identity_bundle(root=REPO_ROOT):
    return {
        "interface_version": INTERFACE_VERSION,
        "implementation_revision": implementation_revision(root),
        "tool_digests": {"gp_binary_sha256": env.gp_binary_sha256(), **pari.pari_versions()},
        "container_digest": keys.env_manifest_digest(env.manifest()),
        "numeric_profile": pari.NUMERIC_PROFILE,
    }


def skill_identity_hash(root=REPO_ROOT):
    return keys.identity_bundle_hash(identity_bundle(root))


def main(stdin=None, stdout=None, stderr=None):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        document = json.load(stdin)
        if not isinstance(document, dict) or set(document) != {"l", "n"}:
            raise InputError("input must hold exactly l and n")
        output = run(document["l"], document["n"])
    except (ValueError, TypeError) as exc:
        stderr.write(f"error: {exc}\n")
        return 1
    stdout.write(json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
