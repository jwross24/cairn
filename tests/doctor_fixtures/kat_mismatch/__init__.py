import json

from cairn import kat

CONTEXT_ONLY = True
FIXABLE = False
ONLY = "gates"
FINDINGS = ("D-kat/mismatch",)


def corrupt(shape):
    vectors = json.loads(shape.vectors.read_text())
    vectors["vectors"][0]["expected"] = "corrupt"
    shape.vectors.write_text(json.dumps(vectors))


def write_clean(shape):
    shape.vectors.write_bytes(kat.DEFAULT_VECTORS.read_bytes())
