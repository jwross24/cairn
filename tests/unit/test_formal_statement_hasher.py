import json

import pytest

from cairn import bundle, lean

KAT_SOURCE = """import Cairn.StatementHash
open Lean Cairn.StatementHash
#eval IO.println (constantVal { name := `target, levelParams := [], type := .sort .zero })
#eval show IO Unit from do
  let t := Expr.sort .zero
  let a := Expr.forallE `x t (.bvar 0) .default
  let b := Expr.forallE `y t (.bvar 0) .implicit
  if !(a == b) || expr a != expr b then throw (IO.userError "binder-normalization")
  if expr (.mdata {} t) != expr t then throw (IO.userError "export-metadata-normalization")
  if expr (.letE `x t t t true) != expr (.letE `x t t t false) then
    throw (IO.userError "export-nondep-normalization")
"""


def test_lean_canonicalization_known_answer(tmp_path, assert_golden):
    (tmp_path / "Cairn").mkdir()
    (tmp_path / "Cairn" / "StatementHash.lean").write_bytes(lean.STATEMENT_HASHER_PATH.read_bytes())
    (tmp_path / "lakefile.toml").write_text('name = "hasher_kat"\n\n[[lean_lib]]\nname = "Cairn"\n')
    (tmp_path / "lean-toolchain").write_text(lean.source_pins()["toolchain"] + "\n")
    (tmp_path / "Kat.lean").write_text(KAT_SOURCE)
    pins = lean.source_pins()
    lean.assert_pinned(pins)
    lean.require_success(lean.run(pins, "lake", ["build", "Cairn.StatementHash"], cwd=tmp_path))
    result = lean.require_success(lean.run(pins, "lake", ["env", "lean", "Kat.lean"], cwd=tmp_path))
    assert_golden("formal_statement", result.stdout)
    print(result.stdout)


def test_hasher_source_is_a_raw_bundle_object():
    objects = bundle.source_objects(bundle.REPO_ROOT / "bundle")
    raw = objects[lean.STATEMENT_HASHER_KIND]
    assert raw == lean.STATEMENT_HASHER_PATH.read_bytes()
    assert bundle.canonical_bytes(lean.STATEMENT_HASHER_KIND, raw) == raw
    changed = dict(objects, **{lean.STATEMENT_HASHER_KIND: raw + b"\n"})
    assert bundle.bundle_hash(bundle.rows_for(objects)) != bundle.bundle_hash(bundle.rows_for(changed))


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "{}\n",
        '{"canonical_hex":"AA"}\n',
        '{"canonical_hex":"0"}\n',
        '{"canonical_hex":""}\n',
        '{"canonical_hex":"00", "other":1}\n',
        "'target' depends on axioms: [sorryAx]\n",
    ],
)
def test_human_or_malformed_hasher_output_is_refused(stdout):
    with pytest.raises(lean.LeanRejected):
        lean.statement_digest(lean.Run((), None, 0, stdout, "", 0))


def test_failed_hasher_output_is_never_hashed():
    with pytest.raises(lean.LeanRejected, match="rc=1"):
        lean.statement_digest(lean.Run((), None, 1, '{"canonical_hex":"00"}\n', "failed", 0))


def test_statement_digest_uses_its_own_domain():
    result = lean.Run((), None, 0, json.dumps({"canonical_hex": "00"}).replace(" ", "") + "\n", "", 0)
    assert lean.statement_digest(result) == "cac1a18dbdc403c154b630b38af221cf0bc4b3049c042112c486111472f3532d"
