# Blind independent comparison

`independent.py` contains the H11 axis-intersection decision and the H2 depth-1 digit automaton. Its inputs are the H11 hypothesis, the branch-split report's soundness argument, and H2's `METHOD.md`. The forbidden implementation directories and H2 Python files are outside the read scope.

`run.py` compares both requested vertices against the current `tier0/lvl12` binary, using a whole-vertex level-12 enumeration with and without `bs` for every digit multiset. It reconstructs each output's coset independently through the permitted level-12 library. EXACT outputs pass through unfiltered and have separate counts. Every decision disagreement and changed output line is written to `disagreements.jsonl`.

H2 samples unique anchored records round-robin across the three requested JSONL files. The default limit is 300 records, with every representation selected by the production `deepcut.py` procedure. Verdicts and surviving-case counts are compared separately. A production case-budget exhaustion is an exclusion, never an agreement. Each comparison records its source file, line, input, representation, verdict, and counts.

Planted points use positive lattice translations of up to eight sampled anchors. The low 96 decimal digits must be zero-free. A plant passes only if the independent automaton has an accepting assignment and the production single-case cut contains the exact planted exponent point. Full enumeration of each dense plant's depth-1 cases is excluded. A million unsuccessful translate candidates per anchor exhausts that anchor's search and is recorded separately.

The supervisor requires effective niceness at least 10, limits numeric library threads to one, and runs one comparison worker with sequential kernel invocations. It stops the worker's process group before 01:45 EDT, with a five-second margin, and refuses the quiet window unless the specified calibration state provides the timestamped exception. Its default total budget is 3,600 seconds. Every long operation checks `date`, using epoch seconds for cutoff comparisons.

Run from a terminal that permits setting niceness:

```bash
cd /Users/jwross/Documents/cairn/research/intake/persistence
PYTHONDONTWRITEBYTECODE=1 UV_CACHE_DIR="$PWD/tier0-opt/math/codex-blind/uv-cache" nice -n 10 uv run --no-sync --offline --project /Users/jwross/Documents/cairn python -B tier0-opt/math/codex-blind/run.py
```

The existing project environment must supply SymPy. No dependency installation or source-tree bytecode write is required. Each invocation creates a distinct result directory underneath `codex-blind/`; existing output files remain intact. Raw kernel outputs, stderr, source hashes, per-pattern comparisons, plants, summaries, and console output live there. An interrupted run retains every completed comparison.

Execution status: the agent sandbox rejects `nice -n 10` with `setpriority: Operation not permitted`. The numerical comparisons and planted-point checks have no execution evidence. Agreement counts are unavailable.
