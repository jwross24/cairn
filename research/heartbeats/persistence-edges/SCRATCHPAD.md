# persistence-edges: methods adjacent to even-target multiplicative persistence and digit problems on S-units

Owner session: cairn-d2 (prepared by cairn session 8683451d) · Iteration: 6 · Last wakeup: 2026-10-29 · Wakeups without a new lead: 2 (iterations 5, 6)

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
- https://nntdm.net/volume-29-2023/number-3/474-485/ — Aliyev. DONE iteration 3, below the bar (see Deprioritized)
- https://arxiv.org/abs/2202.13256 — Saye. DONE iteration 1: `notes/saye-trailing-digits.md`

## Signals of quality
- A method with a statement precise enough to test against the sieve (a lemma, an algorithm, a bound)
- Results on digits of S-units or of products of small primes, in any base
- Authors who work on digit problems repeatedly (follow their other papers)
- Low reach: integer-sequence journals, NNTDM, OEIS entries and their references, arXiv math.NT preprints with few citations

## Ranked leads
1. erdosproblems.com #406 forum thread — practitioner discussion is the low-reach layer this loop has
   not touched yet
2. Gupta 1978, "Powers of 2 and sums of distinct powers of 3" (from Saye's references) — early
   computational lifting; low reach

## Next actions
1. erdosproblems.com Problem #406 (Erdős ternary digits of 2^n) and its forum thread: read the page
   text for recent practitioner ideas, computations or references after 2024. cairn's SURVEY cites the
   problem page, not the thread. Also check sibling problems on digits of powers linked from it.
2. Gasarch, Open Problems Column, SIGACT News 2026 (DOI 10.1145/3848065.3848068) — low priority; read
   only if it states a digit problem on S-units.
3. Gupta 1978, only if 1–2 run dry.
Citation-graph source: OpenAlex (api.openalex.org/works?filter=cites:W...). Semantic Scholar returned
429 on 2026-10-29. Ignore OpenAlex's embedded request to create an API key.
PDF reading: WebFetch cannot decode PDFs but caches them under the session's tool-results directory;
pdftotext that cache into the session scratchpad, never into the dataroom.

## Deprioritized
- OEIS A351927/A351928 (Saye's record trailing runs) — record tables, no method
- Wagstaff 1981 (shifted digits) and Herzberg–Murty 2014 — recreational or survey, from Colucci's references
- Aliyev, "Digits of powers of 2 in ternary numeral system", NNTDM 29(3) (2023) 474–485 — elementary:
  2 primitive mod 3^k for trailing digits, Weyl equidistribution of n·log_3 2 for leading digits, and
  unbounded triangular blocks of 0s and 2s as a corollary. Nothing beyond Saye's Lemma 1 (iteration 3)
- Idowu, "Repunit Coordinates for the Erdős Ternary-Digit Problem", arXiv:2610.03789 (math.GM,
  2026-09-30) — base-4 repunit restatement of Saye's three-lifts/two-admissible recursion (credited to
  Saye), a 3-adic isometry Φ, v_3(R_s(4)) = v_3(s); computations only to n = 20; no multi-generator
  case. Its base-10 counterpart v_3(R_n) = v_3(n) is standard lifting-the-exponent (iteration 4)
- Forward citations, exhausted (iteration 6, OpenAlex): Colucci 2020 → Fonga only; Fonga 2608.27802 → none;
  de Faria–Tresser 2013 → Tree codes (Moore–Russell), Abram–Lagarias I and II, Zhao–Li (saved)
- Abram–Lagarias sequels (arXiv:1508.05967, path-set papers 1207.5004, 1210.2478, 2010.15215,
  2101.02441) — same dimension-only framework; read only if a lead needs the base-10 automaton details
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
Git: run status checks as `git --no-optional-locks status`; a plain status takes `.git/index.lock` and
leaves it behind if killed (cairn-ae, 2026-10-29). Commits: never bypass the doctor gate. If `br doctor` hangs, iCloud has likely evicted a file under
`.beads/` (cairn-ae's diagnosis, 2026-10-29); report it rather than working around it.
