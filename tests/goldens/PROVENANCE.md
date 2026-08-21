# Golden provenance

Every golden or vector under `tests/goldens/` and `tests/vectors/` lists its generator, the tool versions it depends on, and a volatility grade (1 = deterministic everywhere; 5 = expected to drift). Regeneration is `UPDATE_GOLDENS=1 uv run pytest <test> -k <name>` followed by a commit whose message names the tool version that moved it.

| File | Generator | Tool versions | Volatility | Note |
|---|---|---|---|---|
| `tests/vectors/curve60_seed1.json` | `/opt/homebrew/bin/gp -q -f -s 64M tests/vectors/gen60.gp` (smoke test `test_curve60_vector_matches_live_gp`) | PARI/GP 2.17.4, libpari 2.17.2 (cypari2 2.2.4 reproduces it in-process) | 3 | Deterministic under the pinned call sequence; depends on libpari's PRNG, so a libpari bump may legitimately move it. `tries` must stay 45 while the sequence is the one `toy_curve` pins for bits > 50. |
