import difflib
import hashlib
import json

import factories
import pytest
from _substrate_helpers import open_writer

from cairn import bundle, challenge, claims, container, lean

SOURCE = "def bound : Nat := 3\ntheorem target (n : Nat) (h : n < bound) : n < bound := by sorry\n"
LAKEFILE = 'name = "hash_probe"\n\n[[lean_lib]]\nname = "Challenge"\n'


def build_canonical_and_hash(root, gate, source, monkeypatch):
    root.mkdir()
    (root / "lakefile.toml").write_text(LAKEFILE)
    (root / "lean-toolchain").write_text(gate.lean["toolchain"] + "\n")
    (root / "Challenge.lean").write_text(source)
    captured = []
    statement_digest = lean.statement_digest

    def capture(result):
        digest = statement_digest(result)
        canonical_hex = lean.canonical_result(result)["canonical_hex"]
        captured.append(bytes.fromhex(canonical_hex))
        return digest

    with monkeypatch.context() as patch:
        patch.setattr(lean, "statement_digest", capture)
        digest = lean.formal_statement_hash(gate, "Challenge", ["target"], project_dir=root, work_dir=root / "tool")
    assert len(captured) == 1
    canonical = captured[0]
    print(
        json.dumps(
            {
                "project": str(root),
                "canonical_bytes": len(canonical),
                "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
                "formal_statement_hash": digest,
            },
            sort_keys=True,
        )
    )
    return canonical, digest


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
def test_fresh_builds_and_single_edit_pairs(pinned_bundle, tmp_path, label, source, equal, monkeypatch):
    gate = bundle.GateBundle.open(*pinned_bundle())
    base_bytes, base_hash = build_canonical_and_hash(tmp_path / "base", gate, SOURCE, monkeypatch)
    changed_bytes, changed_hash = build_canonical_and_hash(tmp_path / label, gate, source, monkeypatch)
    print(
        "".join(difflib.unified_diff(SOURCE.splitlines(True), source.splitlines(True), fromfile="base", tofile=label))
    )
    assert (base_bytes == changed_bytes) is equal, label
    assert (base_hash == changed_hash) is equal, label


@pytest.mark.parametrize(
    ("base_source", "changed_source", "equal"),
    [
        (
            "def leaf : Nat := 3\ndef middle : Nat := leaf\ntheorem target : middle = middle := rfl\n",
            "def leaf : Nat := 4\ndef middle : Nat := leaf\ntheorem target : middle = middle := rfl\n",
            False,
        ),
        (
            "opaque sealed : Nat := 3\ntheorem target : sealed = sealed := rfl\n",
            "opaque sealed : Nat := 4\ntheorem target : sealed = sealed := rfl\n",
            False,
        ),
        (
            "def proposition : Prop := True\ntheorem support : proposition := True.intro\ndef wrapper : proposition := support\ntheorem target : wrapper = wrapper := rfl\n",
            "def proposition : Prop := True\ntheorem support : True := True.intro\ndef wrapper : proposition := support\ntheorem target : wrapper = wrapper := rfl\n",
            False,
        ),
        (
            "theorem proofOnlyA : True := True.intro\ntheorem proofOnlyB : True := by trivial\ntheorem support : True := proofOnlyA\ntheorem target : support = support := rfl\n",
            "theorem proofOnlyA : True := True.intro\ntheorem proofOnlyB : True := by trivial\ntheorem support : True := proofOnlyB\ntheorem target : support = support := rfl\n",
            True,
        ),
    ],
    ids=["nested-definition-value", "opaque-value", "closure-theorem-type", "closure-proof-only-dependencies"],
)
def test_canonical_closure_bytes_track_types_and_values_but_exclude_theorem_proofs(
    pinned_bundle, tmp_path, monkeypatch, base_source, changed_source, equal
):
    gate = bundle.GateBundle.open(*pinned_bundle())
    base_bytes, base_hash = build_canonical_and_hash(tmp_path / "base", gate, base_source, monkeypatch)
    changed_bytes, changed_hash = build_canonical_and_hash(tmp_path / "changed", gate, changed_source, monkeypatch)
    assert (base_bytes == changed_bytes) is equal
    assert (base_hash == changed_hash) is equal


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
