Read this before touching `cairn.pari`, any 60-bit curve fixture, `gp` invocations, or a test that can hit the PARI call bound.

# PARI details

- `cairn.pari` pins libpari to one thread in both processes: `default(nbthreads,1)` at import and `-D nbthreads=1` in `gp_argv`, so every gp spawn through `run_gp` carries it.
- Single-thread values: the 60-bit toy_curve rows, `curve60_seed1.json`, the grounding brief's 60-bit row, `gate_plan.json`'s curve60 fixture and `measure.RHO60_ORDER`. A scratch run at another thread count draws different 60-bit curves; sizes at or below 50 bits are unchanged.
- A gp script run outside `run_gp` inherits the host's core count and will not reproduce those rows.
- `cairn.pari.ellcard`, `ellsea` and `ellorder` are bounded by `cairn.pari.CALL_BOUND_S` (60 s) via cysignals' alarm and raise `PariStall`, a `KeyboardInterrupt` subclass. After the bound fires, libpari is unusable in that process and the suite stops at exit 124.
- A Python `SIGALRM` handler displaces cysignals' alarm. `tests/unit/test_pari_module.py` holds the planted loop proving the chain intact.
