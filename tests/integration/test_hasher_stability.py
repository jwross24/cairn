import difflib
import json

import factories
import pytest
from _substrate_helpers import open_writer

from cairn import bundle, challenge, claims, container, lean

SOURCE = "def bound : Nat := 3\ntheorem target (n : Nat) (h : n < bound) : n < bound := by sorry\n"
LAKEFILE = 'name = "hash_probe"\n\n[[lean_lib]]\nname = "Challenge"\n'


def build_hash(root, gate, source):
    root.mkdir()
    (root / "lakefile.toml").write_text(LAKEFILE)
    (root / "lean-toolchain").write_text(gate.lean["toolchain"] + "\n")
    (root / "Challenge.lean").write_text(source)
    digest = lean.formal_statement_hash(gate, "Challenge", ["target"], project_dir=root, work_dir=root / "tool")
    print(json.dumps({"project": str(root), "source": source, "formal_statement_hash": digest}, sort_keys=True))
    return digest


@pytest.mark.parametrize(
    ("label", "source", "equal"),
    [
        ("fresh", SOURCE, True),
        ("comment", "-- one comment\n" + SOURCE, True),
        ("unused", SOURCE + "def unused : Nat := 17\n", True),
        ("hypothesis", SOURCE.replace("h : n < bound", "h : n ≤ bound"), False),
        ("definition", SOURCE.replace("bound : Nat := 3", "bound : Nat := 4"), False),
    ],
    ids=["fresh", "comment", "unused", "hypothesis", "definition"],
)
def test_fresh_builds_and_single_edit_pairs(pinned_bundle, tmp_path, label, source, equal):
    gate = bundle.GateBundle.open(*pinned_bundle())
    base = build_hash(tmp_path / "base", gate, SOURCE)
    digest = build_hash(tmp_path / label, gate, source)
    print(
        "".join(difflib.unified_diff(SOURCE.splitlines(True), source.splitlines(True), fromfile="base", tofile=label))
    )
    assert (base == digest) is equal, label


def test_real_formal_hash_is_bound_in_the_substrate(pinned_bundle, tmp_path, monkeypatch):
    prelude = tmp_path / "prelude.lean"
    prelude.write_text("set_option autoImplicit false\n")
    monkeypatch.setattr(challenge, "PRELUDE_PATH", prelude)
    gate = bundle.GateBundle.open(*pinned_bundle())
    project = tmp_path / "compiled"
    project.mkdir()
    (project / "lakefile.toml").write_text(LAKEFILE + 'globs = ["Challenge.+"]\n')
    (project / "lean-toolchain").write_text(gate.lean["toolchain"] + "\n")
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", project / "Challenge")
    rendered = challenge.write_challenge(
        factories.claim_statement(seed=11, formal_source=SOURCE), gate.challenge_prelude
    )
    digest = lean.formal_statement_hash(
        gate, rendered.module, ["target"], project_dir=project, work_dir=tmp_path / "tool"
    )
    run = challenge.gate_run(rendered, gate, factories.CREATED_AT, arm=container.DEV_ARM, formal_statement_hash=digest)
    sub = open_writer(tmp_path)
    try:
        claims.write_gate_run(sub, run)
        row = sub.conn.execute(
            "SELECT statement_hash, formal_statement_hash FROM gate_runs WHERE run_id=?", (run.hash,)
        ).fetchone()
    finally:
        sub.close()
    assert tuple(row) == (rendered.statement_hash, digest)
    assert challenge.binding(run)["formal_statement_hash"] == digest
    print(json.dumps(challenge.binding(run), sort_keys=True))
    unbound = challenge.gate_run(rendered, gate, factories.CREATED_AT, arm=container.DEV_ARM)
    with pytest.raises(challenge.BindingAbsent, match="formal_statement_hash is empty") as rejected:
        challenge.binding(unbound)
    print(str(rejected.value))
