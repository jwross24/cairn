import hashlib
import json
import sys
from pathlib import Path

from cairn.skills import bsgs

INTERFACE_VERSION = bsgs.INTERFACE_VERSION
INPUTS = bsgs.INPUTS
COST_PROFILE = bsgs.COST_PROFILE
REPLAY_GRADE = bsgs.REPLAY_GRADE


def implementation_revision():
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def identity_bundle():
    return {**bsgs.identity_bundle(), "implementation_revision": implementation_revision()}


def main():
    document = bsgs.parse_inputs(sys.stdin.read())
    result = bsgs.run(*(document[name] for name in ("bits", "seed", "p", "a", "b", "n", "P", "Q")))
    output = json.loads(result.to_json())
    output["x"] = str((int(output["x"]) + 1) % document["n"])
    print(json.dumps(output))


if __name__ == "__main__":
    main()
