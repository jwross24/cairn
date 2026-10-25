# Brief for the Cairn session: the frontier program (chat, 2026-10-20 15:10 EDT)

Context: FRONTIER.md (ranked 72 remaining base-10 vertices, three tiers, registered forecast),
SANDWICH.md, DEEPCUT.md. Everything enumerated so far is CLOSED; the only thing left in base 10 is
enumeration cost. Owner prioritizes against M1; each item is independent.

## 1. Swap tier0-opt's lvl12 into the sweep (8× on Tier A) — needs the gate
The sweep runs the gated lvl12.c at 66 ns/pattern; tier0-opt measures 8–9 ns. Tier A (53 vertices,
3.9e14 patterns) is 30 days at 66 ns and 4 days at 8 ns on 10 cores. Gate before swapping (RULE: never
into a running sweep): `difftest.py` on 72 and 10800 with the opt binary IDENTICAL, plus the survivor
list of one mid-size vertex (14336, 1.8e9 patterns) byte-identical between the two binaries. Then stop,
swap, relaunch the identical resumable command.

## 2. GPU level-12 kernel (Metal on Apple Silicon) — the only route to Tier B
Spec = lvl12.c's contract exactly: input the exported config (`export_cfg.py` → primes, pow10, R tables,
ℓ-component tables H, CRT constants, g, u, U2, K per a), enumerate the same pattern space (n mod 12,
digit positions mod 12 as multisets) and emit the same survivor records "a nu eps..." in the same
order or in any order with a canonical sort. Acceptance: survivor sets bit-identical to lvl12.c on 72,
10800 and 14336. Target ≥ 10^10 patterns/s (the kernel is integer-only: Gray-code residue updates
mod five primes ≤ 9901 and table lookups — fit the 9901 table in threadgroup memory). Keep it a
separate binary (`lvl12_gpu`), never replace lvl12.c; the gate decides when it may feed the sweep.
The lift 12→24 (lvlN.c) becomes the next bottleneck for Tier B; measure its share before optimizing.

## 3. Lemma C + sandwich in C for Tier-A scale
Tier-A vertices will leave 10^4–10^5 open patterns each at level 96; Python Lemma C/sandwich is ~1 s
per pattern-depth. A C port of `cut_coset` (5-adic/2-adic logs by lifting, 2-D coset intersection,
exact nearest point) with the same inputs as deepcut.py (anchor y, a, ν, positions) and the same
verdicts on DEEPCUT-run-0545.txt (636/679 closed at depth 1) and SANDWICH-run.txt (43/43) is the
acceptance test. Gate it like the rest.

## 4. Base 8 on the Mac (replication of the complete theorem) — commands in the ledger (19:40).

## 5. Already armed: deepcut.py + sandwich.py when the base-10 sweep ends; Lean `lower_digits_of_candidate`.

Nothing here touches the running jobs without the gate; nothing changes calibration tags.
