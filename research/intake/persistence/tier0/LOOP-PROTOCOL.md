# The loop: how chat, Cairn and Codex run computation and theory together

*2026-10-21 21:00 EDT. Owner's instruction: "try to do this sort of experimentation with computation and theory in a
loop, and get Cairn and Codex to do that as well; they need to coordinate effectively." This file is the protocol.
It binds all three sessions from the next ledger line on. AGENTS.md remains law (RULE 1/2, gates, owner commits).*

## 1. The loop (one item = one pass; every pass is a ledger line)

1. **Measure** — an exact computation on real project data (sweep records, gated equations, the corpus, a lattice),
   never on a model. State the sample. Example: the image indices of the words' lattice at 193/769 (HSHADOW §2).
2. **Regularity** — one sentence, falsifiable, with a number: "every word has exactly one level-192 child (256/256)".
3. **Prediction** — written BEFORE the next run, in the ledger or PREDICTIONS.md: what the regularity implies on
   data not yet looked at, with a kill condition ("if any word has 0 or ≥ 2 children, dead").
4. **Mechanism** — the reason, in algebra: "the image is trivial because 768 | content". Must name the object that
   carries the effect (a lattice, a subgroup, a congruence), not a metaphor.
5. **Certificate** — the mechanism turned into an exact finite check that replaces enumeration (shadowcert.py),
   validated verdict-for-verdict against the older method on the same inputs, plus a planted positive and one
   mutant that the check must catch.
6. **Lemma** — the general statement (EXPERIMENTS-X §X5: content = first invariant factor; p − 1 | d₁ ⇒ additive
   kill), with the numbers it explains and the numbers it predicts; Lean if it is two lines, Codex retype if not.
7. **Where it fails** — the negative result is a deliverable (X3: saturation at the first window). A pass that ends
   in "no" closes a door for everyone and is logged with the same care.

A pass that stops at step 2 is a measurement, at step 4 an explanation, at step 5 a tool, at step 6 mathematics.
The ledger line names the step reached. Nothing is "progress" until step 5; nothing is "new mathematics" until 6.

## 2. Who does what (by capability, not seniority)

- **Chat**: steps 1–6 on data it has (corpus, trees_mac snapshots, lattices); Python prototypes with built-in
  self-tests (brute force vs the new method on real inputs); literature checks; the theory write-ups; PAPER.md.
- **Cairn**: steps 1–2 on data only the Mac has (sweep files, gated equations, C port internals); step 5 in C with
  the gate (identical survivor sets vs production, two mutants, timing); cost models with measured unit costs;
  Lean. Cairn DIRECTS Codex and relays its output with the exact prompt used.
- **Codex** (via Cairn, always blind): the independent re-implementation of any certificate (step 5) from the
  written statement only; the retype of any lemma's constants (step 6); the adversary — plant a genuine child or a
  synthetic 10-adic point and try to get it closed; attack the hypothesis chain. Codex never sees chat's or
  Cairn's code for the thing it is checking, and never sees the expected numbers.

## 3. Coordination rules

- **One queue**: HYPOTHESES.md holds every open item as (id, owner, step reached, prediction, kill condition,
  data needed). A new idea is a queue line before it is work. Claim by writing your name; two sessions on the
  same item is a ledger bug.
- **Ledger line format**: `HH:MM <who> → <who>: <ID> step <n>: <one-sentence result>; <numbers>; <md5 of the
  landed file>; NEXT: <what the other session must do, with the exact file/sample>`.
- **Data before models**: no cost projection without the measured unit cost it rests on, named.
- **Every rate carries an interval**; every verdict names the algorithm that produced it and the second method
  that agreed with it.
- **Negative results travel**: a falsified prediction gets the same line as a confirmed one and a "do not retry
  without new data" note.
- **Clock**: Mac time only (chat stamps ledger lines from the Mac's `date`, after the 19:33 drift incident).
- **Tempo**: chat and Cairn each post at least one loop line per working hour while both are active; Codex
  results are posted the moment Cairn has them, with the prompt.

## 4. The queue as of 21:00 EDT (owner may re-rank)

| id | item | owner | step reached | next |
|---|---|---|---|---|
| L1 | Corpus to 10^6884 two ways; RST[1] theorem for all four even roots | chat sieve (c ≈ 950/8146, reboots) + Cairn gate | 1 | Cairn: zfsieve gate; Codex: blind N(k), Lemma 1.1, 2.1 |
| L2 | Additive lift 12→24 (and 24→48, 48→96) | chat prototype 120/120 | 5 (Python) | Cairn: C port + gate on 228 equations; cost model with measured unit costs |
| L3 | Shadow certificate at 96→192→384 | chat 43/43 ≡ two older methods | 5 | Cairn: C port, re-run 1335; Codex: blind re-implementation |
| X2 | Level-24 descent survivors: shadow vs accident | — | 0 | Cairn: classify on the 228 gated equations; prediction ≥ 99 % shadows at k ≥ 13 |
| X4 | 96→480 certificate (seven trivial-image primes) | chat, exact indices | 4 | chat: prototype + self-test; Cairn: compare cost vs 192/384 on the 1335 |
| X5 | Content lemma (d₁ of ⟨3,7⟩) | chat | 6 (paper proof) | Cairn: Lean; Codex: retype d₁(Λ_96) from the prime list |
| X6 | Ideal final-stage primes: all PH-feasible p with (p−1) \| d₁ | chat | 0 | chat tonight |
| A1 | Adversary: planted child through the full pipeline | — | 0 | Cairn runs Codex blind |
| Z | Root 0 | nobody | — | no action; REDUCTION.md §3′ is the record |
