# research/intake/persistence — multiplicative persistence, even-target program

Intake material written 2026-10-19 in a chat session, before any bead exists. AuditOnly.
Nothing here is a Cairn skill, claim statement or evidence node yet; these files are the
reading a lane needs to write them. Nothing here is PROVEN under RULE 2.

- `INTAKE.md` — the problem, the load-bearing invariant (target 0 stands), tagged claims,
  the 1062 equations for A_4 by tier, proposed skills with self-tests, the negative-results
  map, and the first three beads.
- `ANALYSIS.md` — proofs (Thm 1–8), the 10^4000 computation, every attack route on
  Conjecture Z and where each dies, the heuristic.
- `zfsieve.c`, `zfcheck.py` — the sieve and exact verifier used for the computation.
  Self-test: `./zfsieve 370 0 100000 | python3 zfcheck.py` must report 8807 zero-free,
  largest 140 digits at (25,227,28), max persistence 10 at (4,20,5). The 10^4000 run is
  87,932,095,342 triples, 17,961 survivors, 8807 zero-free, ~70 CPU-min on two cores.

Under the repo's rules these would become: a `persistence_oracle` skill (Tier-0 verifier),
a `zf_sieve` skill with the self-test above and a measured cost profile, claim statements
C1–C8 from INTAKE.md with their tags, and the negative-results map entries, before any
worker touches an equation.
