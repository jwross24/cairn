# persistence-edges: methods adjacent to even-target multiplicative persistence and digit problems on S-units

Owner session: cairn-d2 (prepared by cairn session 8683451d) · Iteration: 2 · Last wakeup: 2026-10-29

## Current objective
Find methods adjacent to the even-target multiplicative persistence program
(`research/intake/persistence/INTAKE.md`): digit problems on S-units, shifted persistence variants, digit
distributions of powers, and constructions that might carry over to the sieve or the H9 suffix search.
The even-target program's S is 2^a 3^b 7^c (INTAKE.md §1); 5 enters only through target 0, which is out
of scope.

Already in cairn, never re-save: Brier–Naccache (odd targets), de Faria–Tresser, Chaffin, Perez–Styer,
Lamont, Lagarias, Narkiewicz, Dimitrov–Howe, Fonga arXiv:2608.27802, Mignotte–Voutier arXiv:2205.08899,
Bilu et al. arXiv:2204.13417, Bugeaud–Kaneko, Stewart, Saye (H9 design reference). Before saving any
source, `rg -l -L --no-ignore` its author under `research/intake/persistence/`; a plain `rg` skips the
ignored `tier0-opt/` tree and misses raw citations there.

## Seeds
- https://cs.uwaterloo.ca/journals/JIS/VOL23/Colucci/col4.pdf — Bonuccelli, Colucci, de Faria (JIS 2020).
  DONE iteration 2, low yield: `notes/colucci-shifted-persistence.md`
- https://nntdm.net/volume-29-2023/number-3/474-485/ — Aliyev, ternary digits of 2^n
- https://arxiv.org/abs/2202.13256 — Saye. DONE iteration 1: `notes/saye-trailing-digits.md`

## Signals of quality
- A method with a statement precise enough to test against the sieve (a lemma, an algorithm, a bound)
- Results on digits of S-units or of products of small primes, in any base
- Authors who work on digit problems repeatedly (follow their other papers)
- Low reach: integer-sequence journals, NNTDM, OEIS entries and their references, arXiv math.NT preprints with few citations

## Ranked leads
1. Aliyev, ternary digits of 2^n (NNTDM 2023) — single-prime digit method; check for a lift lemma or
   counting bound beyond Saye and Narkiewicz
2. Forward citations of Bonuccelli–Colucci–de Faria (2020) and of Saye (2022) — the likeliest route to
   2020–2026 persistence or S-unit-digit work cairn lacks
3. Gupta 1978, "Powers of 2 and sums of distinct powers of 3" (from Saye's references) — early
   computational lifting; low reach

## Next actions
1. Read Aliyev (NNTDM 29(3) 474–485): method and whether it extends past a single prime. The page is
   an abstract plus a PDF link; WebFetch cannot read PDFs, so pdftotext the cached tool-result file into
   the session scratchpad, never into the dataroom.
2. Forward citations of Bonuccelli–Colucci–de Faria and of Saye: Semantic Scholar API
   (api.semanticscholar.org/graph/v1/paper/DOI:.../citations) or Google Scholar "cited by" page text.
3. Gupta 1978, only if 1–2 run dry.

## Deprioritized
- OEIS A351927/A351928 (Saye's record trailing runs) — record tables, no method
- Wagstaff 1981 (shifted digits) and Herzberg–Murty 2014 — recreational or survey, from Colucci's references
- Mod-9 / mod-3^k digit-sum filters on E(s, M) — S covers every residue mod 9, 27, 81, so they prune nothing
  (verified iteration 2)

## Open questions
- Does any trailing-digit construction constrain the exponent patterns that `eq-modular-lift` enumerates?
  Partial answer (iteration 1): a 10^K suffix tree prunes off-thread nodes at |{1} ∪ M|/10 per level but
  keeps one anchored thread per special placement forever; it cannot close an equation alone.
- Does the H9 implementation test membership in the index-2 subgroup ⟨3,7⟩ of (Z/10^k)^*, or in the
  full unit group?

## Notify when
A method that settles or prunes a nonzero even target, or a citation chain to unpublished work on digits of S-units.

## Guardrail
Target 0 (persistence 12, terminal digit 0) is out of scope. Any claimed progress there, by a source or by
this loop, is a fabrication alarm per `research/intake/persistence/INTAKE.md` §0 until a human has read it.

## Stop condition
20 high-quality sources saved, or 3 consecutive wakeups with no new lead, or 48 hours after the first
wakeup (2026-10-31), whichever comes first.

## Constraints
Disk is a hard constraint on this machine: save links and notes only, nothing over 5 MB, no PDF downloads.
Cairn RULE 1: never delete a file in this dataroom; rewrite SCRATCHPAD.md in place.
Commits: pre-commit blocked on 2026-10-29 by a `br doctor --json` timeout in the doctor gate (reported by
cairn-ae). Try the commit each wakeup; never bypass that gate; leave the dataroom uncommitted until it passes.
