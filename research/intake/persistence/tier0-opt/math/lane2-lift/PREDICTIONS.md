# Lane 2 predictions (registered 2026-10-21 19:50:50 EDT, never edited after this line)

Status at registration: no idea (a)-(e) has been implemented. Existing artifacts: src/join_prof.c (join24 plus counters only),
src/measure.c (tier0/lvlN.c plus read-only fate counters), exact lattice content (scripts/lattice_content.py), the measurement
run over 220 of the 228 equations (the 8 largest still running), the additivity check on 2 equations. The M-series below is
therefore CONFIRMATORY (written after seeing part of the data); the I-series and C-series are PRE-REGISTERED.
Baseline "join24" = join24swap/lvlN.c (md5 54db62e8), reference = tier0/lvlN (md5 20e091fc). CPU seconds are rusage at nice 10
on a machine at load 35-65, so timing ratios carry a +-15% noise band; any ratio inside [0.85, 1.15] is read as "no change".

## M-series (measurement)
M1. The joint 2-part character (73,137,99990001 mod 8,8,16; image 8 of 1024) fails a child with probability in [0.985, 0.996].
    The chat's expectation "the 2-part kills almost nothing" is predicted FALSE; the 2-part is the single largest log-contributor
    (factor 128 of the joint index 259,200 = 128 x 81 x 25 x 1 x 1 x 1).
M2. The 11-part (p3), 17-part (137) and 101-part (p3) characters fail exactly 0 children (image = whole group).
M3. child = parent + (10^12 - 1)*Delta holds exactly (as rationals) on 100% of dumped children; the C residues equal the independent
    big-integer residues on 100%.
M4. Among children passing the single-prime test, Delta mod 73 takes at most 2 distinct values per parent (image order 2), mod 137 at most 34,
    mod 99990001 at most 111100: the only additive (pure congruence) kill is at 73.
M5. The children-weighted all-characters pass rate is in [4e-6, 1.2e-5] (design 1/259200 = 3.86e-6; parents are not random targets).

## I-series (ideas; speedup = CPU(join24) / CPU(variant), byte-identical OPEN/EXACT sets required, both mutants caught)
Heavy set H = the 12 equations with most children. T = all 228.
(a) Small-image cascade, order by kill power per cost: share one cofactor exponentiation z = y^(11*101) for the 3 relevant l-parts and
    test the 5-part first (kills 0.96 at about 26 multiplications). Predicted speedup on H: 1.3 (range 1.1-1.8); on T: 1.2 (1.05-1.5).
    Kill if < 1.10 on H.
(b) Meet-in-the-middle keyed on 73 alone (K = 2): predicted SLOWER than the default key choice by >= 1.5x on H (range 1.5-20x);
    the default cost-model choice is within 15% of the best of the 5 forced key sets on >= 80% of H. Wagner k-tree is not a complete
    enumerator (it keeps one solution per fixed intermediate target), so it cannot give byte-identical sets: recorded as not
    implementable, not as measured.
(c) 10-adic window (K = 4, 25 t-classes) applied before the residue test via window-bit groups: predicted speedup 0.5-1.05 on H
    (no gain); fraction of (parent, window-bit group) pairs with no viable t-class 10-30%. Kill if < 1.15.
(d) Direct 12 -> 48: the level-48 stage is <= 5% of the 24+48 lift CPU on the 214 level-48 equations, so any gain from avoiding it is <= 1.05.
    Lambda_12 images at the level-48 primes (17, 5882353, 9999999900000001): indices 4, 48, 900 individually; joint 24+48 index
    3.94e12 = 88 x (259,200 x 172,800); coset size at 24+48 about 2.3e23, so no key/hash join over the full coset exists.
(e) Counting DP + backtracking over (Z/73 x Z/137) bitsets: predicted speedup on H: 0.5 (range 0.2-1.2) at Tier A children per parent
    (1.4e4-6.1e4); crossover where it beats join24 by 1.5x at children per parent in [2e5, 5e6].
Composite: the best single or combined variant reaches <= 4x on H (range 1.5-8) and <= 3x on T. Probability that any variant reaches
    100x on T: < 1%. Reason (floor): per-parent fixed cost about 3-10 us and the candidate stream (children that pass the cheap
    (73,137) test, 0.35-1.7% of children) each needing a 99990001 character.
Success criterion of the ask (100x with byte-identical sets) is therefore predicted NOT met; the measured statement of why is the deliverable.

## C-series (cost model; MODELED, extrapolation from sweep data at k <= 18)
C1. Level-12 OPEN parents per pattern at k = 24-29 lie in [1e-8, 5e-7]; the chat's sv12 = 5e-3 overstates the lifted population by >= 10^3
    (sv12 counts RESOLVED(descent) survivors, 88-97% of level-12 survivors at k = 12-18, and the measured sv12 rate declines with k beyond 8).
C2. Children per OPEN parent at k = 29 lie in [3e5, 4e6]; 2^(k+1) = 1.07e9 overstates by >= 250.
C3. Tier B lift 12->24 total children in [1e17, 1e19]; at 1.5-3 ns/child (join24) that is 1.5e8-3e10 core-seconds, not 1e15 s.

## Addendum registered 2026-10-21 20:36:23 EDT (earlier predictions above are untouched; scoreboard so far: see RESULT.md)
Trigger: coordinator relay (OWNER RELAY, plan change) asking to compare the Dimitrov-Howe modulus-chain discipline with tier0/LIFT-ADDITIVE.md (md5 072184c2)
on the 228 equations. Read first (evidence, not recall): arXiv:2105.06440 abs + ar5iv text. What I took from it: moduli M_i = m_1..m_i, m_i mostly primes p = 1 mod 2^a 3^b chosen so the order of 2
grows by a factor 1 or 2 per stage; each stage lifts the solutions mod M_{i-1}; a stage is UNBALANCED (enumerate prod #A_j tuples, test with discrete logs mod the new prime) when the number of
lifts of the target chi exceeds prod #A_j, otherwise BALANCED (two sorted lists keyed mod M_i, sqrt cost); the search stops when every power is determinate (p^{i+1} divides M).
Status at registration: ideas (a)-(e), BEST (E0+A+C) are implemented and measured (RESULT.md); nothing below is implemented.
Mapping to the level-24 lift: stages = primes 73, then 137, then 99990001; slots = variables with m+1 lifts; chi = |K_p| (2, 34, 111100) against C0 = children per parent (4e3-6.5e4 on the 228):
balanced at 73 (and the pair 73*137), unbalanced at 99990001 (chi = 111100 > C0). Between stages there are NO new variable lifts (a surviving child has no further freedom), so the chain degenerates to
one join followed by filters; the order-ratio device and the determinate stop have no counterpart (t is determinate once the CRT of the components is formed).
DH variant to be built (LANE2_DH=1 on top of E0+A, tuned weights): balanced join at the cheapest strongest stage, 137 bitmap, discrete-log chain at 99990001, and a per-parent balanced/unbalanced switch (plain enumeration with the
bitmap prefilter when C0 < DH_T instead of a join).
LA variant to be built (LANE2_E=2): LIFT-ADDITIVE's DP over Z/10001 (73*137 by CRT, one bitset of 10001 bits per layer, rotations), backtracking over children, exact test on candidates; allowed set = T*K_pair (68 residues, uncut);
the 10-adic cut would only add candidates' density factor <= 2 and does not change the DP cost, so it is not built (reported as skipped).
P-DH1. DH variant over join24 on the 228 (identical sets): total x1.5 (range 1.2-2.0), heavy-12 x1.5 (1.2-2.0). Kill if < 1.15. Reason: the gain is candidate-stage engineering only.
P-DH2. The DH switch alone (plain when C0 < DH_T) changes total CPU by less than 5% on the 228 (small-C0 equations are a negligible part of the 63 s).
P-LA1. LA bitset DP over join24: x0.9 (range 0.4-2.0) on heavy-12 (DP ~ 12-25 us per parent against 20-100 us for join24 at C0 = 1.4e4-6e4; candidates 0.69% of children). Total on 228: x0.8 (0.3-1.5).
P-LA2. LA with word-per-state arithmetic (the document's 6*10001*(q+1) operation count read literally, about 1 ms per parent) would be x0.02-0.1; the document's projection "3 ms vs 11 ms at q=13" compares against a join24 cost 6.1 us/child / 9, measured here at 1.6-3.4 ns/child, so its x3 advantage at q=13 does not survive the measured baseline (predicted: at q=13, C0 = 4.8e3, join24 about 15 us/parent, LA about 12-25 us).
P-LA3. Crossover (LA beats join24 by >= 1.5x) at C0 >= 3e5 children per parent (range 1e5-3e6); the Tier B mean is 1e5-9e5, so LA and the p3-keyed join matter only there.
P-DH3. Neither variant approaches BEST (x2.4 total); neither reaches x100.
Literature facts supplied by the coordinator (to be recorded, not tested): bitset DP is O~(m)-optimal (Axiotis et al.; Cardinal-Iacono); k-tree/Wagner does not apply because the coset condition is not prefix-linear.
Idea (b)'s registered prediction stands unedited; status KILLED by literature (reason above) plus the forced-key timing in RESULT.md.
