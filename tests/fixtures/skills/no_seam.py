import sys
from pathlib import Path

import blake3

from cairn import canon

from . import _selftest_shim, nonconforming

INTERFACE_VERSION = "no_seam/1"
CROSS_CHECK_AXIS = nonconforming.CROSS_CHECK_AXIS
INDEPENDENT_RANGE = nonconforming.INDEPENDENT_RANGE
COST_PROFILE = nonconforming.COST_PROFILE
CORPUS_PATH = nonconforming.CORPUS_PATH
REPO_ROOT = nonconforming.REPO_ROOT
IDENTITY_SOURCES = (
    "tests/fixtures/skills/no_seam.py",
    "tests/fixtures/skills/nonconforming.py",
    "tests/fixtures/skills/nonconforming_corpus.json",
)
run = nonconforming.run
main = nonconforming.main


def implementation_revision(root=REPO_ROOT):
    hasher = blake3.blake3()
    for rel in sorted(IDENTITY_SOURCES):
        data = (Path(root) / rel).read_bytes()
        hasher.update(canon.length_prefix(rel.encode("utf-8")) + canon.length_prefix(data))
    return hasher.hexdigest()


def identity_bundle(root=REPO_ROOT):
    return {
        **nonconforming.identity_bundle(root),
        "interface_version": INTERFACE_VERSION,
        "implementation_revision": implementation_revision(root),
    }


def certify(sub):
    return _selftest_shim.certify(sys.modules[__name__], sub)


def transcript():
    return _selftest_shim.transcript(sys.modules[__name__])


if __name__ == "__main__":
    sys.exit(main())
