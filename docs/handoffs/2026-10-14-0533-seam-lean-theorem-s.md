# Lane SEAM: Lean check of Theorem S (two-grumpy-giants seam), handoff

## Goal

Lane SEAM (agent-mail name **BrownRaven**) was run overnight by the orchestrating session **MagentaSparrow** at the
owner's request. Its job was to prove the seam of the two-grumpy-giants law, a uniform O(l) edge bound
`|W(l,n) - Q(l,n)| <= C l`. `W` is the chain-free weight; `Q` is `scaled_prediction` in
`~/brennerbot_sessions/cairn-giants-20261013/codex/g_phase.py`. The proof was then to be machine-checked in Lean, with no
`sorry`, no axiom, no `native_decide`, and no `decide` standing in for a general statement.

Orders: `~/.local/share/cairn-agent-mail/orders/CAIRN-SEAM-2026-10-14.md` and `CAIRN-SEAM-LEAN-0230.md`, plus
MagentaSparrow's messages of 03:45, 04:12 and 04:32 EDT. The hard stop was 05:50 EDT 2026-10-14, with nothing new after
05:30.

## Status

**All ordered items are finished, stop mail sent (agent-mail message id 1343, 04:42 EDT).** Nothing is in flight, and no
background process is running.

- **Finished, argued on paper:** `law/seam/PROOF.md`, Theorem S `|W - Q| <= 5l + 92.1n^2 + 110.4n < 41l`. Also finished:
  `READ-COROLLARY-C.md` and `ATTAINABILITY.md`.
- **Finished, Lean on the dev arm:** the headline is `theoremS_codex`: `|W - scaled_prediction(l,n)| <= 39 l` for prime `l`,
  `n >= 9`, `3n^2 < l < 4n^2`. Its components:
  - Lemma L, Lemma Z, BETA (`|beta - sigma| <= 6n + 20`), and the discrete form `theoremS_discrete`.
  - Lemmas I and R: non-strip by explicit antiderivative, strip by monotonicity. Error `18.75 n^2`.
  - Simpson exactness on the cut set (`strip_simpson_cuts`), and codex's `_strip_integral` transcribed and proved equal to
    `int sigma` (`codexStrip_eq`).
- **Not done:**
  - BETA at PROOF.md's constant `5.1n + 18.4`. Lean has `6n + 20`, because it bounds the overlap of the three bands by
    `3 mu_+` and does not prove the bands disjoint.
  - No second model family has audited the Lean statements against PROOF.md. Calibration stays AuditOnly; nothing is PROVEN
    (cairn RULE 2).

## Decisions

- **BETA constant raised to `6n + 20`.** Bounding by `3 mu_+` avoided a band-disjointness proof. Theorem S still closes
  (39 l).
- **No Mathlib integrals for BETA.** It telescopes `H c v` in `Huber.lean` instead.
- **Lemmas I and R are split in two.**
  - The non-strip part uses an explicit antiderivative over `ℚ` (`PhiA`, `PhiB`), with unit-step bounds in place of
    derivatives, as MagentaSparrow asked.
  - The strip part uses monotonicity of `sigma` with Mathlib's `MonotoneOn.sum_le_integral` and `integral_le_sum`. This
    was much shorter than a piecewise-cubic antiderivative.
- **Simpson exactness is shown via cut-free pieces.** On a closed piece with no cut strictly inside, each clip keeps one
  branch (`band_quad`, seven leaves), so the band term is quadratic there. No continuity argument is needed.
- **Codex's Python was transcribed into Lean** (`codexSlice`, `codexStrip`). Faithfulness is by reading, because Lean
  cannot read Python.
- **Evidence placement.** Every evidence file is new and lives outside the cairn repo. PROOF.md, ATTAINABILITY.md, ORDER.md
  and READ-COROLLARY-C.md were never edited, by order.

## Dead ends

- `dcg` refuses some shell forms, so use its safe alternatives and never work around it:
  - a heredoc fed to `uv run python -` (use the Write tool, or `python -c`);
  - a redirect to a variable path such as `> /tmp/seam_$f.out` (write literal paths);
  - a heredoc that quotes a delete command (edit with the Edit tool).
- Lean pitfalls hit in these files:
  - `rw [max_eq_right ...]` fails when an earlier rewrite has already changed that term.
  - `rw [← node_zero]` rewrites inside the arguments of `node` itself, causing a motive error; rewrite `at key` instead.
  - A hypothesis named `hi` shadows the variable `hi`.
  - Reals need a `noncomputable section`.
  - Mathlib names in this pin: `div_le_div_iff₀`, `le_div_iff₀`, `Finset.pairwise_sort`, `List.pairwise_iff_getElem`,
    `intervalIntegral.sum_integral_adjacent_intervals`, `integral_eq_sub_of_hasDerivAt`, `Int.lt_ceil`, `Int.floor_lt`,
    `Int.le_ceil_iff`, `Int.floor_le_iff`.
- **RULE 1 incident.** At 02:59 a `rm -f law/seam/lean/axioms-lemmaL.out` was run. The file was restored verbatim and the
  deletion disclosed. Never delete files.

## Files

The evidence root is `~/brennerbot_sessions/cairn-giants-20261013/law/seam/`.

- `HANDOFF.md`: the lane's full handoff. Its bottom line and sections cover Lean items 02:30, 03:45, 04:12 and 04:32.
- `PROOF.md`: the paper proof of Theorem S (audited; do not edit).
- `NOTES.md`: the append-only journal.
- `strip_identity_check.py` / `.out`: my Simpson strip against codex `_strip_integral`. 258 rows, 0 mismatches in exact
  rationals.
- `lean/`: byte-identical copy of the scratch build (35 files), with `README.md` holding the reproduction commands. The
  outputs `build.out`, `scan.out`, `axioms*.out`, `check-*.out` and `plant-*.out` live here too.
- The scratch Lean project is `/private/tmp/seam-lean`, with its own Mathlib cache of about 7.8 GB. Mathlib is pinned at
  rev `1f290110…` and the toolchain is `v4.34.0-rc1`. Its root `SeamLean.lean` imports `Assembly`, `Strip`, `CutSet` and
  `Codex`.
- The Lean files under `SeamLean/` that carry the key results:
  - `Assembly.lean`: `theoremS_discrete`, `Wsum_stable`.
  - `Integral.lean`: `lemmaI_nonstrip`, `lemmaR_nonstrip`.
  - `Strip.lean`: `theoremS_39`.
  - `Simpson.lean`: `band_quad`, `simpson_exact`.
  - `CutSet.lean`: `strip_simpson_cuts`.
  - `Codex.lean`: `codexStrip_eq`, `theoremS_codex`.
- `~/.local/share/cairn-agent-mail/orders/measure-2026-10-13.jsonl`: stop lines for lane SEAM, appended with Python
  `open(path, "a")`.

## Verification

Run every build under the heavy lock and memory cap, from `/private/tmp/seam-lean`:

```bash
lockf -k /tmp/cairn-heavy.lock uv run --no-project python ~/.local/share/cairn-agent-mail/orders/memcap.py 6 lake build
lockf -k /tmp/cairn-heavy.lock uv run --no-project python ~/.local/share/cairn-agent-mail/orders/memcap.py 6 lake env lean SeamLean/AxiomsSimpson.lean
lockf -k /tmp/cairn-heavy.lock uv run --no-project python ~/.local/share/cairn-agent-mail/orders/memcap.py 6 lake env lean SeamLean/CheckSimpson.lean
lockf -k /tmp/cairn-heavy.lock uv run --no-project python ~/.local/share/cairn-agent-mail/orders/memcap.py 6 lake env lean SeamLean/PlantCodex.lean
```

Last results, 04:41 EDT:

- The build completes, 8,785 jobs, exit 0.
- `AxiomsSimpson.lean` and `CheckSimpson.lean` exit 0. All 15 theorems print `[propext, Classical.choice, Quot.sound]`.
- The planted-negative files `PlantIR.lean`, `PlantSimpson.lean` and `PlantCodex.lean` exit 1, as intended.
- `scan.out` reports 0 matches.
- The strip check exits 0:
  `cd law/seam && uv run --no-project python strip_identity_check.py` gives `rows 258 mismatches 0`.

## Next steps

1. Have a second model family (Codex) read `lean/SeamLean/Codex.lean` and `AxiomsSimpson.lean`'s printed definitions
   against `codex/g_phase.py` lines 16-46. It should also read `theoremS_codex`'s statement against PROOF.md's Theorem S.
   That is the remaining audit before any calibration upgrade.
2. Optionally restore BETA's `5.1n + 18.4` in Lean by proving the three live bands disjoint (`5n + 19.1`).
3. Wait for MagentaSparrow's reply on topic `cairn-m1-cqt.10`. Never wait on a human; the stop is 05:50 EDT.

## Open questions

- Should the Lean development move from scratch into the cairn repo (for example `lean/Grounding/`)? Moving it would be a
  repo change, which this lane was forbidden to make. Only the owner can decide.
- `git status` shows `main` one commit ahead of `origin/main`, plus untracked `lean/Grounding/HalfWeight101.lean` and
  `KColumnBound.lean`. Neither came from this lane, which made no commits; they belong to another session.

Standing instructions for any continuation:

- New files only, and no edits to the audited files.
- No cairn commits.
- Never delete a file (RULE 1).
- Use `uv`, never `pip` or bare `python`.
- Keep the agent-mail registration token private.
- American English.
