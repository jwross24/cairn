import sys
from pathlib import Path

import pytest
from _substrate_helpers import open_writer

from cairn import bundle, challenge, claims, container, lean, log

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

TEST_PRELUDE = b"set_option autoImplicit false\n"
FORMAL = "theorem challenge_hello (n : Nat) : n + 0 = n := by\n  sorry\n"
CURVE_FORMAL = "theorem challenge_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := by\n  sorry\n"
LAKEFILE = 'name = "challenge_probe"\n\n[[lean_lib]]\nname = "Challenge"\nglobs = ["Challenge.+"]\n'
SORRY_WARNING = "declaration uses `sorry`"
MATHLIB = lean.PROJECT_DIR / ".lake" / "packages" / "mathlib"
FAKE_FORMAL_HASH = "f" * 64


def _log(event, result, **fields):
    log.get("grounding.challenge").info(
        event,
        command=" ".join(result.argv),
        cwd=result.cwd,
        rc=result.rc,
        stdout=result.stdout,
        stderr=result.stderr,
        wall_ms=result.wall_ms,
        **fields,
    )


def _probe_project(root, pins):
    root.mkdir()
    (root / "lean-toolchain").write_text(pins["toolchain"] + "\n")
    (root / "lakefile.toml").write_text(LAKEFILE)
    return root


def test_a_rendered_challenge_compiles_under_the_pinned_toolchain(monkeypatch, tmp_path):
    pins = lean.source_pins()
    project = _probe_project(tmp_path / "probe", pins)
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", project / "Challenge")
    stmt = factories.claim_statement(seed=3, formal_source=FORMAL)
    rendered = challenge.write_challenge(stmt, TEST_PRELUDE)
    build = lean.run_argv(lean.command(pins, "build", module=rendered.module), cwd=project)
    _log("challenge_build", build, module=rendered.module, source_hash=rendered.source_hash)
    assert build.rc == 0, build.stderr
    assert SORRY_WARNING in build.stdout + build.stderr
    assert (project / ".lake" / "build" / "lib" / "lean" / "Challenge" / f"C_{stmt.hash[:16]}.olean").is_file()


def test_the_real_prelude_compiles_in_the_gate_project_when_mathlib_is_present(request):
    if not MATHLIB.is_dir():
        pytest.skip(f"mathlib checkout absent at {MATHLIB}; `lake update` in lean/ writes it (7.8 GB)")
    pins = lean.source_pins()
    stmt = factories.claim_statement(seed=4, formal_source=CURVE_FORMAL)
    rendered = challenge.write_challenge(stmt, challenge.prelude_bytes())
    request.addfinalizer(lambda: Path(rendered.path).unlink(missing_ok=True))
    build = lean.run_argv(lean.command(pins, "build", module=rendered.module), cwd=lean.PROJECT_DIR)
    _log("challenge_build_mathlib", build, module=rendered.module, source_hash=rendered.source_hash)
    assert build.rc == 0, build.stderr
    assert SORRY_WARNING in build.stdout + build.stderr


def test_a_challenge_render_gate_run_round_trips_through_the_substrate(pinned_bundle, monkeypatch, tmp_path):
    gate = bundle.GateBundle.open(*pinned_bundle())
    monkeypatch.setattr(challenge, "CHALLENGE_DIR", tmp_path / "Challenge")
    rendered = challenge.write_challenge(
        factories.claim_statement(seed=5, formal_source=FORMAL), gate.challenge_prelude
    )
    unbound = challenge.gate_run(rendered, gate, factories.CREATED_AT, arm=container.DEV_ARM)
    bound = challenge.gate_run(
        rendered, gate, factories.CREATED_AT, arm=container.DEV_ARM, formal_statement_hash=FAKE_FORMAL_HASH
    )
    sub = open_writer(tmp_path)
    try:
        claims.write_gate_run(sub, unbound)
        claims.write_gate_run(sub, bound)
        rows = sub.conn.execute(
            "SELECT run_id, gate, statement_hash, formal_statement_hash, renderer_hash, prelude_hash "
            "FROM gate_runs ORDER BY formal_statement_hash IS NULL"
        ).fetchall()
    finally:
        sub.close()
    assert [tuple(r) for r in rows] == [
        (
            bound.hash,
            "challenge_render",
            rendered.statement_hash,
            FAKE_FORMAL_HASH,
            rendered.renderer_hash,
            rendered.prelude_hash,
        ),
        (
            unbound.hash,
            "challenge_render",
            rendered.statement_hash,
            None,
            rendered.renderer_hash,
            rendered.prelude_hash,
        ),
    ]
    assert challenge.binding(bound)["bundle_hash"] == gate.hash
    with pytest.raises(challenge.BindingAbsent):
        challenge.binding(unbound)
