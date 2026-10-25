# Mutation testing of the engine (2026-10-19, chat session)

Method: plant one defect at a time in a copy of the engine, run eight control vertices through
the C pipeline (`run_vertex_c.py`), and record whether the positive controls (every known child
must survive every level and be recovered under its own pattern) or the verdict table catch it.

| mutant | defect | caught by |
|---|---|---|
| descent-no-exact-case | descent never checks "the number is exactly the tail" | control lost (221184, 41472) |
| descent-wrong-t | t = v₂(9Y − 10^K) + 1 | verdict change on 6; control lost (13122) |
| pinning-K-too-large | K* ignores the basis test | control lost (16, 126) |
| lattice-wrong-sign | sign error in the coset reduction | control lost (111132, 1134) |
| prime-log-off-by-one | R_n table wrong at one residue | control lost (13122, 18144) |
| 2adic-bound-too-small | A reduced by 2 | control lost (16, 1134) |
| tail-allows-zero (Python) | zero digit allowed in the tail | **not caught** — dead code: the live tail test is in lvl12.c (a C mutant of that line is queued) |
| lift-drop-children | drops the n + L residue at each lift | **not caught** on the eight vertices: no control there has ≥ 12 digits |

Score 6/8; the two escapes are a dead-code mutant and a corpus gap, not engine defects.

Corpus fix: the 14-digit element **11519532122112 = 2^14·3^15·7^2** (digit product 10800, not an
even-tree vertex — irrelevant for a control) exercises the n-lift and a position ≥ 12. The real
engine recovers it (vertex 10800: children [11519532122112], 2 open patterns with the 10^27
bound). The lift-drop mutant on this control and the C tail-zero mutant were still running on the
loaded cloud box when this file was written; results will be appended.

Recommendation for Cairn: make the long control part of the standard validation set (the Mac has
the cores), and run this mutation table against `tier0-opt/lvl12.c` before it replaces the
original — mutants of the C tail test and of the CRT representative assembly especially.
