import json
import shutil

from cairn import bundle, kat

FIXABLE = False
ONLY = None
FINDINGS = ("D-bundle/pin-mismatch",)


def corrupt(shape):
    src = shape.root / "bundle-src"
    shutil.copytree(kat.REPO_ROOT / "bundle", src)
    auditor = src / "auditor.json"
    body = json.loads(auditor.read_text())
    body["doctor_fixture"] = True
    auditor.write_text(json.dumps(body))
    bundle.build(src, shape.bundle)
