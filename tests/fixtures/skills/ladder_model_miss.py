import hashlib
import sys
from dataclasses import replace
from pathlib import Path

from cairn.profile import CostProfile, Production
from cairn.skills import bsgs

INTERFACE_VERSION = bsgs.INTERFACE_VERSION
INPUTS = bsgs.INPUTS
COST_PROFILE = CostProfile(
    tier=bsgs.COST_PROFILE.tier,
    production=Production(
        model=bsgs.COST_PROFILE.production.model,
        per_size={bits: replace(bsgs.COST_PROFILE.production.per_size[bits], mean_tries=1.0) for bits in (28, 30)},
    ),
    verification=bsgs.COST_PROFILE.verification,
    source="fixture: intentionally low predictions for ladder model-miss settlement",
    memory=bsgs.COST_PROFILE.memory,
)
REPLAY_GRADE = bsgs.REPLAY_GRADE


def implementation_revision():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def identity_bundle():
    return {**bsgs.identity_bundle(), "implementation_revision": implementation_revision()}


def main():
    document = bsgs.parse_inputs(sys.stdin.read())
    result = bsgs.run(*(document[name] for name in ("bits", "seed", "p", "a", "b", "n", "P", "Q")))
    print(result.to_json())


if __name__ == "__main__":
    main()
