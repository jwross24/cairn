import dataclasses
import fnmatch
import hashlib
import sys
import tomllib
from pathlib import Path

import pytest

from cairn import bundle, challenge, lean
from cairn.substrate import blob_hash

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

FORMAL = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  sorry\n"
PRELUDE = b"set_option autoImplicit false\n"
FAKE_FORMAL_HASH = "f" * 64


def _statement(formal=FORMAL, seed=1):
    return factories.claim_statement(seed=seed, formal_source=formal)


def _fingerprint(data):
    return len(data), hashlib.sha256(data).hexdigest()


def test_double_render_is_byte_identical():
    stmt = _statement()
    first = challenge.render(stmt, PRELUDE)
    second = challenge.render(stmt, PRELUDE)
    assert _fingerprint(first) == _fingerprint(second)
    assert first == PRELUDE + b"\n" + FORMAL.encode()


def test_render_normalizes_line_endings_and_trailing_whitespace():
    messy = _statement(formal="theorem t : True := by  \r\n  trivial   \r\n\r\n")
    assert challenge.render(messy, b"  \r\n") == b"\n\ntheorem t : True := by\n  trivial\n"


@pytest.mark.parametrize("formal", [None, "", "   \n\n"], ids=["none", "empty", "whitespace"])
def test_a_statement_without_formal_source_is_refused(formal):
    with pytest.raises(challenge.NoFormalSource, match="carries no formal source"):
        challenge.render(_statement(formal=formal), PRELUDE)


def test_the_gate_project_declares_the_challenge_library_and_ignores_rendered_modules():
    lakefile = tomllib.loads((lean.PROJECT_DIR / "lakefile.toml").read_text())
    libs = {entry["name"]: entry for entry in lakefile["lean_lib"]}
    assert libs["Challenge"]["globs"] == ["Challenge.+"]
    assert challenge.CHALLENGE_DIR == lean.PROJECT_DIR / "Challenge"
    ignored = (lean.PROJECT_DIR / ".gitignore").read_text().splitlines()
    assert "Challenge/C_*.lean" in ignored
    assert fnmatch.fnmatch(Path(challenge.module_path(_statement(), "Challenge")).as_posix(), "Challenge/C_*.lean")


def test_module_name_and_path_derive_from_the_statement_hash():
    stmt = _statement()
    assert challenge.module_name(stmt) == "Challenge.C_" + stmt.hash[:16]
    assert challenge.module_path(stmt, "/x") == Path("/x") / f"C_{stmt.hash[:16]}.lean"
    assert challenge.module_name(_statement(seed=2)) != challenge.module_name(stmt)


def test_a_worker_writable_root_is_refused_by_the_render_step(tmp_path):
    with pytest.raises(challenge.PathNotGateOwned, match="not the gate-owned Challenge directory"):
        challenge.write_challenge(_statement(), PRELUDE, root=tmp_path)
    assert list(tmp_path.rglob("*.lean")) == []


def test_write_challenge_lands_in_the_gate_owned_directory_only(monkeypatch, tmp_path):
    owned = tmp_path / "Challenge"
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", owned)
    stmt = _statement()
    rendered = challenge.write_challenge(stmt, PRELUDE)
    path = Path(rendered.path)
    assert path.parent == owned
    assert path.read_bytes() == challenge.render(stmt, PRELUDE)
    assert rendered.source_hash == blob_hash(path.read_bytes())
    assert rendered.prelude_hash == blob_hash(PRELUDE)
    assert rendered.renderer_hash == challenge.renderer_hash()
    assert challenge.write_challenge(stmt, PRELUDE) == rendered
    assert sorted(p.name for p in owned.iterdir()) == [f"C_{stmt.hash[:16]}.lean"]


def test_the_bundle_carries_prelude_and_renderer_as_raw_objects(pinned_bundle):
    gate = bundle.GateBundle.open(*pinned_bundle())
    assert gate.challenge_prelude == challenge.prelude_bytes()
    assert gate.challenge_renderer == challenge.renderer_bytes()
    assert gate.digest_of(challenge.PRELUDE_KIND) == challenge.prelude_hash()
    assert gate.digest_of(challenge.RENDERER_KIND) == challenge.renderer_hash()
    assert challenge.prelude_bytes().startswith(b"import Mathlib.")


def test_an_edited_prelude_fails_the_bundle_pin_check(pinned_bundle, monkeypatch, tmp_path):
    _, pin_path = pinned_bundle()
    edited = tmp_path / "challenge_prelude.lean"
    edited.write_bytes(challenge.prelude_bytes() + b"\nopen Nat\n")
    monkeypatch.setattr(challenge, "PRELUDE_PATH", edited)
    rebuilt = tmp_path / "rebuilt.sqlite"
    assert bundle.build(bundle.REPO_ROOT / "bundle", rebuilt) != bundle.read_pin(pin_path)
    with pytest.raises(bundle.BundlePinMismatch):
        bundle.GateBundle.open(rebuilt, pin_path)


def test_a_render_under_another_prelude_or_renderer_is_refused_a_gate_run(pinned_bundle, monkeypatch, tmp_path):
    gate = bundle.GateBundle.open(*pinned_bundle())
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", tmp_path / "Challenge")
    foreign = challenge.write_challenge(_statement(), PRELUDE)
    with pytest.raises(challenge.RenderNotFromBundle, match="challenge_prelude") as caught:
        challenge.gate_run(foreign, gate, factories.CREATED_AT)
    assert (caught.value.rendered_hash, caught.value.bundle_hash) == (blob_hash(PRELUDE), challenge.prelude_hash())
    pinned = challenge.write_challenge(_statement(), gate.challenge_prelude)
    stale_renderer = dataclasses.replace(pinned, renderer_hash="0" * 64)
    with pytest.raises(challenge.RenderNotFromBundle, match="challenge_renderer"):
        challenge.gate_run(stale_renderer, gate, factories.CREATED_AT)
    assert challenge.gate_run(pinned, gate, factories.CREATED_AT).prelude_hash == gate.digest_of(challenge.PRELUDE_KIND)


def test_the_gate_run_carries_the_binding_field_and_refuses_it_absent(pinned_bundle, monkeypatch, tmp_path):
    gate = bundle.GateBundle.open(*pinned_bundle())
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", tmp_path / "Challenge")
    rendered = challenge.write_challenge(_statement(), gate.challenge_prelude)
    unbound = challenge.gate_run(rendered, gate, factories.CREATED_AT)
    assert (unbound.gate, unbound.result, unbound.formal_statement_hash) == ("challenge_render", "pass", None)
    assert (unbound.bundle_hash, unbound.pin_hash) == (gate.hash, gate.pin_hash)
    assert (unbound.statement_hash, unbound.renderer_hash, unbound.prelude_hash) == (
        rendered.statement_hash,
        rendered.renderer_hash,
        rendered.prelude_hash,
    )
    with pytest.raises(challenge.BindingAbsent, match="formal_statement_hash is empty"):
        challenge.binding(unbound)
    bound = challenge.gate_run(rendered, gate, factories.CREATED_AT, formal_statement_hash=FAKE_FORMAL_HASH)
    assert bound.hash != unbound.hash
    assert challenge.binding(bound) == {
        "claim_statement_hash": rendered.statement_hash,
        "formal_statement_hash": FAKE_FORMAL_HASH,
        "bundle_hash": gate.hash,
        "renderer_hash": rendered.renderer_hash,
        "prelude_hash": rendered.prelude_hash,
    }


def test_a_binding_is_refused_from_any_other_gate():
    other = factories.gate_run(
        statement_hash="s" * 64, formal_statement_hash=FAKE_FORMAL_HASH, renderer_hash="r" * 64, prelude_hash="p" * 64
    )
    with pytest.raises(challenge.BindingAbsent, match="gate is 'tier_gate'"):
        challenge.binding(other)


def test_a_submission_carries_only_a_solution_module_and_the_hash_it_names():
    assert {f.name for f in dataclasses.fields(challenge.Submission)} == {"solution_module", "formal_statement_hash"}
    smuggled = {"solution_module": b"theorem x : True := trivial\n", "formal_statement_hash": FAKE_FORMAL_HASH}
    smuggled["challenge_module"] = b"edited"
    with pytest.raises(TypeError, match="challenge_module"):
        challenge.Submission(**smuggled)
