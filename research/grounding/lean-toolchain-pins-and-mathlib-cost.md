# Grounding brief: the Lean toolchain, its pins, and what mathlib costs on this machine

Bead `cairn-m1-cqt.5.1`. Probe date 2026-09-02, macOS 26.6 / Darwin 25.6.0 arm64, 10 cores,
24 GB, APFS; load average 5–9 throughout because two sibling sessions ran suites, so every wall
time below is an upper bound for an idle machine. The rows tagged PROVEN-by-probe are asserted
by `tests/integration/test_lean_toolchain.py` and `tests/unit/test_lean_pins.py` on every run;
the timings are context (not asserted). The 2026-08-21 record, when `~/.elan` was absent, is
`lean-checker-protocol.md`.

Tags: **PROVEN-by-probe** = the exact command ran here and a test asserts the observed output
on every run; **STRONG-EMPIRICAL** = observed here, on one input or one timing window;
**CONJECTURE** = stated, not executed here; **OPEN** = not probed, with the bead that grounds
it; **context (not asserted)** = a hand-run command or a logged field no test asserts.

## 1. Resolution arm

The arm taken: the resolver's absolute path comes from `ELAN_HOME` (default `~/.elan`), every
invocation names the toolchain with `+leanprover/lean4:v4.34.0-rc1`, no default toolchain is
set, and `~/.elan/bin` stays off every PATH. The bundle (`bundle/lean.json`) pins the toolchain
name and the lean commit, not the host path; `cairn.lean.assert_pinned` refuses when the
resolved toolchain's version or commit differs from the pin, before any compile.

| Item | Value | Tag |
|---|---|---|
| `~/.elan/bin/elan --version` | `elan 4.2.3 (b6cec7e10 2026-06-08)` | context (not asserted) on this machine; CI greps `elan $ELAN_VERSION ` from the same command |
| `~/.elan/bin/elan toolchain list` | `leanprover/lean4:v4.34.0-rc1`, stdout only, rc 0 | PROVEN-by-probe (`test_the_pinned_toolchain_resolves_and_reports_the_pinned_commit` runs it through `assert_installed` and asserts the pin is listed) |
| `ELAN_HOME` | read by `cairn.lean.elan_home` on every call and passed to every child, so the resolver, the proxies and the test allow-list (`tests/conftest.py`) all follow it; a test that sets it may spawn whatever sits at `$ELAN_HOME/bin/{elan,lean,lake,leanchecker}`, which is how the absent-toolchain and hung-tool tests plant their fixtures | STRONG-EMPIRICAL (`test_the_child_sees_the_resolved_elan_home_and_a_hung_tool_is_killed`) |
| `~/.elan/bin/lean +leanprover/lean4:v4.34.0-rc1 --version` | `Lean (version 4.34.0-rc1, arm64-apple-darwin24.6.0, commit 3447a668783dbce1a8fdb97101dd067687b2b418, Release)`; 0.59 s wall by `time -p`, 371 ms in-process | PROVEN-by-probe for version, commit and build; the timing is context |
| `~/.elan/settings.toml` | `telemetry = false`, `version = "12"`, no default toolchain; `elan show` → `no active toolchain` | context (not asserted) |
| bare `~/.elan/bin/lean --version` | prints `error: no default toolchain configured` and exits **0** | STRONG-EMPIRICAL — rc is not a signal for this failure; the version regex in `cairn.lean.VERSION_RE` is |
| `+leanprover/lean4:v4.34.0-rc1` from an `ELAN_HOME` with no toolchains | elan starts downloading `https://releases.lean-lang.org/lean4/v4.34.0-rc1/lean-4.34.0-rc1-darwin_aarch64.tar.zst` (561 MB); killed at 15 s | STRONG-EMPIRICAL — the reason `assert_installed` runs `elan toolchain list` first |
| `elan toolchain list` on an empty `ELAN_HOME` | stdout `no installed toolchains`, rc 0 | PROVEN-by-probe (`test_an_absent_toolchain_is_refused_before_the_proxy_can_download_it` symlinks the real `elan` into an empty home and asserts `LeanMissing` with no `toolchains/` created) |
| `+leanprover/lean4:v4.34.0-rc1-wrong` | `error: no such release: 'v4.34.0-rc1-wrong'` after a network round trip | STRONG-EMPIRICAL; the installed check refuses before that round trip |
| elan-init from the v4.2.3 release archive (`elan-aarch64-apple-darwin.tar.gz`, 2 167 269 bytes) with `-y --no-modify-path --default-toolchain none` into a scratch `ELAN_HOME` | rc 0; 31 MB; no toolchain; no rc-file edits | STRONG-EMPIRICAL — the CI recipe in `.github/workflows/ci.yml` |
| toolchain on disk | `~/.elan/toolchains/leanprover--lean4---v4.34.0-rc1` = 2.7 GB; release archive `lean-4.34.0-rc1-darwin_aarch64.tar.zst` = 561 265 981 bytes | context (not asserted) |

## 2. leanchecker

| Item | Value | Tag |
|---|---|---|
| presence | `~/.elan/toolchains/leanprover--lean4---v4.34.0-rc1/bin/leanchecker`, proxied by `~/.elan/bin/leanchecker` | PROVEN-by-probe (the fresh replay below runs it) |
| `lake build Hello` on a mathlib-free `lakefile.toml` project (`theorem hello (n : Nat) : n + 0 = n := Nat.add_zero n`) | rc 0; 4.77 s wall first run (manifest created); oleans at `.lake/build/lib/lean/Hello.olean` | PROVEN-by-probe (`test_hello_theorem_builds_and_leanchecker_replays_it_from_empty`) |
| `lake env leanchecker -v Hello` | `replaying Hello`, rc 0, 1.09 s | PROVEN-by-probe (same test, the `replay` bundle command) |
| `lake env leanchecker --fresh -v Hello` | `replaying Hello with --fresh`, rc 0; 50.6 s wall on `Grounding.Hello` at load 7.4, 57.1 s inside the test; the 2026-08-21 figure was 32.3 s on an idle machine | PROVEN-by-probe for rc and output (the `replay_fresh` bundle command); timing is context |
| `leanchecker` direct with `LEAN_PATH=<project>/.lake/build/lib/lean:<toolchain>/lib/lean` | same output, 0.92 s | context — `lake env` is the bundle's command because it needs no knowledge of the `.lake` layout |
| `#print axioms hello` | `'hello' does not depend on any axioms` | context (not asserted) |

## 3. The mathlib pin and its cost

The pin: mathlib `1f29011071772620f612bf5a06433775f06067b8`, on `master`, committed
2026-08-21T02:09:10Z, whose `lean-toolchain` is `leanprover/lean4:v4.34.0-rc1`; master moved to
`v4.34.0-rc2` at `85e3a25e006c` (2026-08-21T15:44Z). GitHub's commit endpoint returns 422 for
the seven-character prefix `1f29011`; the full SHA resolves (the 2026-08-21 brief cites the
prefix). `lean/lakefile.toml` requires mathlib at the full SHA; `lean/lake-manifest.json` is
the record `lake update` wrote and is ingested into the gate bundle as the `lake_manifest`
object; `bundle/lean.json` names the same revision, and `tests/unit/test_lean_pins.py` asserts
the three agree.

| Item | Value | Tag |
|---|---|---|
| `lake +leanprover/lean4:v4.34.0-rc1 update` in `lean/` | rc 0, 207 s wall; clones mathlib plus batteries, Qq, aesop, proofwidgets, importGraph, LeanSearchClient, plausible, Cli (revisions in the manifest); mathlib's `post_update` hook runs `cache get` inside the same command | STRONG-EMPIRICAL |
| cache coverage of the pin | `~/.cache/mathlib` held 8691 `.ltar` files dated 2026-08-21 04:32–04:34; `cache get` for this pin attempted and downloaded **8747 of 8747** files (zero local hits); the cache holds 17 438 files, 883 MB afterward. The 2026-08-21 files do not serve this pin; whether they belong to another revision or to another key scheme is not established | STRONG-EMPIRICAL for the counts; the reason is OPEN (bead F2 records which revision a container's cache covers) |
| second `lake exe cache get` | `No files to download`, `Already decompressed 8747 file(s)`, rc 0, 20 s | STRONG-EMPIRICAL |
| disk | `lean/.lake/packages/mathlib` 7.1 GB; `lean/.lake/packages` 7.8 GB; `lean/.lake/build` 1.3 MB; 70 GB free after | context (not asserted) |
| `lake build Grounding.Hello` (mathlib-free module inside the mathlib-requiring project) | rc 0, 8.5 s wall (789 ms build) | STRONG-EMPIRICAL |
| `lake build Grounding.Curve` (`import Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point`; `theorem hello_curve {R : Type} [CommRing R] (W : WeierstrassCurve R) : W.Δ = W.Δ := rfl`) | rc 0, 21.2 s wall, 1994 jobs served from the cache, the module itself 12 s | STRONG-EMPIRICAL — the mathlib-importing build the bead asks for; a minimal Challenge with a curve import costs about twenty seconds here once the cache is in place |
| `lake env leanchecker -v Grounding.Curve` (not fresh) | `replaying Grounding.Curve`, rc 0, 18.5 s | STRONG-EMPIRICAL |
| `#print axioms hello_curve` | `'hello_curve' depends on axioms: [propext]` | context (not asserted); inside the permitted set |
| `leanchecker --fresh` on `Challenge.FormalHasherCost`, importing the affine-point mathlib module | rc 0; `replaying Challenge.FormalHasherCost with --fresh`; `time -p`: real 465.52, user 287.06, sys 32.72 seconds; process wall 465794.034 ms, bound 600 s | STRONG-EMPIRICAL, 2026-09-07 dev-macos-fake-landrun; build real 36.73 s, hasher `lake exe` real 36.58 s. Fixture and commands: `formal-statement-hasher.md`. |
| `lake build Challenge.C_<hash>` of a rendered Challenge (bead F3): mathlib-free test prelude in a tmp lake project | rc 0, 2.8 s wall; `warning: … declaration uses \`sorry\`` on stdout with rc 0 | PROVEN-by-probe (`tests/integration/test_challenge_compile.py::test_a_rendered_challenge_compiles_under_the_pinned_toolchain` asserts rc 0 and the warning) |
| the same with the bundle prelude (`import Mathlib.AlgebraicGeometry.EllipticCurve.Affine.Point`) and a Weierstrass statement, in `lean/` | rc 0, 22.0 s wall, 1994 jobs from the cache | STRONG-EMPIRICAL (`test_the_real_prelude_compiles_in_the_gate_project_when_mathlib_is_present` runs it where the checkout exists and skips with a printed reason elsewhere) |

## 4. CI

`.github/workflows/ci.yml` restores `~/.elan` from a cache keyed on the elan release, the
toolchain file and the runner OS and architecture, installs elan 4.2.3 from its release
archive and the toolchain by name on a miss, and proves the resolution with
`lean +<toolchain> --version` before the gates. The in-suite Lean tests cost one lake build
plus one fresh replay (about one minute at this machine's load); mathlib is not cloned in CI.
The job ceiling is 20 minutes. Runner-side timings are OPEN until the first run of the F1
close lands; `tests/goldens/PROVENANCE.md` and the close comment carry them when they do.

## 5. Bundle fields

`bundle/lean.json`: `toolchain`, `lean_commit`, `mathlib_rev`, `permitted_axioms`, and
`checker` command templates (`version`, `build`, `replay`, `replay_fresh`) whose argv[0] is a
pinned tool name that `cairn.lean.command` resolves under `ELAN_HOME` with the `+toolchain`
override. `cairn.bundle.source_objects` ingests `lean/lake-manifest.json` as `lake_manifest`,
so the gate-bundle hash moves with the manifest; `tests/goldens/gate_bundle_hash.golden` is
regenerated in the same commit. `cairn.lean.assert_pinned(gate.lean)` is the fail-closed check
beads F5 and F6 call before compilation.
