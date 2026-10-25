# Independent brainstorm, ranked by expected value

**The strongest lead is to meet the archimedean and 5-adic gap chains in the middle.** This substantially reduces the height bound without removing its exponential dependence on digit count.

Grounding: I read the ten requested documents in order, then relevant engine code. Neither excluded file was read. Probes used temporary scratch space and standard-library Python. Unrun tests below are proposals with advance predictions. No idea assumes abc. None has Cairn’s PROVEN status.

## 1. Meet the two gap chains

**Claim, derived:** Set \(M=9y\), \(T_j=\sum_{i>j}9(d_i-1)10^{E_i}-1\). For the permitted digits, every \(T_j\) is a 5-adic unit, including when \(E_k=0\), since digit 5 is excluded. Also \(M/T_j-1\ne0\). A bottom-up Yu chain can therefore meet the existing top-down Matveev chain:
\[
n=(n-E_j)+E_j\le X_j+Z_j,
\quad Z_k=Y,\quad Z_j=Y(Z_{j+1}\log10+\log80).
\]
Here \(X_j\) follows the existing prefix recursion,
\[
Y=D_4\log3\log7(1+\log B),\quad B=3.4n+2,
\quad D_4=(16e)^{10}4^{5/2}(\log8)^2\,5/(\log5)^2.
\]
The height factor for 2 is rounded up to 1. Optimize the meeting index \(j\).

**Removal:** hundreds of orders from the height bound, potentially several sandwich depths and their branching factors. Initial pattern enumeration remains.

**Literature:** Bugeaud–Kaneko, [*On the digital representation of smooth numbers*](https://arxiv.org/html/1704.00432v1), Theorem 2.1, inequality (2.2), and Lemma 3.1 actually read. Meeting the chains is my deduction.

**Kill test, run:** prediction was substantially smaller depths. Conservative rational logarithm bounds and \(e<3\) give \(n<10^{237},10^{332},10^{465}\) for \(k=22,31,44\), \(a>0\), at splits \(j=13,18,25\). Upper-bound/N ratios: .489, .167, .363. Smaller integer endpoints were refused; three genuine anchors passed unit/nonvanishing checks. Under one CPU-second. Forecast depths: 5, 7, 10. These certify arithmetic for the proposed recursions, not their theorem application.

**Confidence MEDIUM:** explicit published inequality; application and monotonicity need independent review.

## 2. Intersect anchor carry DP with Lemma C before emitting patterns

**Claim, algorithmic:** For fixed anchor, wrap, and \(\nu\), augment the representation DP with which local digit occupies copy zero, or none. Enforce Lemma C’s exact finite quotient condition during the DP; existentially eliminate higher columns. Retain digit-product budgets and distinct physical positions.

**Removal:** potentially \(10^6\)–\(10^9\) representations per anchor. For \(a+9<96\), the documented quotient sees only positions below \(a+9\); high-column multiplicity can disappear.

**Literature:** Bryant, [*Graph-Based Algorithms for Boolean Function Manipulation*](https://www.cs.cmu.edu/~bryant/pubdir/ieeetc86.pdf), representation/reduction sections actually read; this carry construction extends the read anchor-DP description.

**Kill test:** unrun, 90 CPU-minutes on twenty heavy anchor fibers; predict 100× fewer states than representations. A preliminary probe predicted sharp compression but obtained only 1.32× on 27 positioned records; three constructed, non-frontier examples gave 2.6×, 7.8×, 32.7×. That weakens the scaling prediction.

**Confidence MEDIUM:** exact elimination is sound; useful compression remains unestablished.

## 3. Join additive lift sums against the multiplicative image

**Claim, algorithmic:** At a lift, let \(B\) count digit-copy assignments and \(H\) count distinct S-unit residues attainable from the parent coset modulo selected new primes. Enumerate that image. Balance two additive partial-sum lists, placing the target-image variable on one side, and join equal residues.

**Removal:** when \(H\ll B\), work can approach \(\sqrt{BH}+Z\), where \(Z\) counts outputs, replacing \(B\). This attacks lifting, rather than the dense level-12 count. Preserve multiset symmetry.

**Literature:** Dimitrov–Howe, [*Powers of 3 with few nonzero bits and a conjecture of Erdős*](https://arxiv.org/html/2105.06440v2), balanced/unbalanced lifting sections actually read. Their target has rank one; ours requires measuring rank-two \(H\).

**Kill test, unrun:** 60 CPU-minutes, ten large recorded parents, initially primes 73 and 137. Predict 100× fewer generated tuples on the largest parents. Reject if image size, outputs, or exact survivor comparison defeat the gain.

**Confidence MEDIUM:** established join mechanism; target-image size could erase savings.

## 4. Share deeper-cut states across histories

**Claim, algorithmic:** At fixed depth, histories with the same canonical exponent coset and remaining multiset of \((d,e\bmod96)\) have identical future extensions. The coset determines the fixed tail. Merge them in a decision DAG; compute nearest-point bounds once per state. Across anchor representations, retain additional carry state needed by the identity.

**Removal:** repeated copy histories and lattice work through sandwich depths; hoped-for 100×–10,000× savings.

**Literature:** Bryant’s paper above, actually read. Equal future languages, rather than similar numerical bounds, justify merging.

**Kill test, unrun:** 90 CPU-minutes on recorded sandwich survivors through depth six. Predict 100× history/state compression for one heavy fiber; require identical survivor unions and bounds. Otherwise demote.

**Confidence LOW:** distinct tails may generate distinct cosets almost every time.

## 5. Put valuation-aware suffix constraints before the ladder

**Claim, algorithmic:** Search admissible suffixes using the digit-product budget while retaining congruences in all three exponents. A suffix \(t\bmod10^K\) fixes \(a=v_2(t)\) only when \(v_2(t)<K\); if \(t\equiv0\bmod2^K\), retain the whole branch \(a\ge K\). Interleave these constraints with prime refinement. Check shorter numbers separately.

**Removal:** avoids configuring exhaustive global \(A(M)\), and rejects suffix families before enormous lifts. The target is orders of magnitude through earlier constraint intersection.

**Literature:** Dimitrov–Howe, same paper, extraneous-solution and prime-power sections actually read; the three-exponent integration is proposed.

**Kill test, unrun:** 90 CPU-minutes on a 2-heavy multiset from RESULT-dpcount.md. Predict 100× fewer expanded lift nodes. Plant genuine S-units with \(a\ge K\); every one must survive.

**Confidence MEDIUM:** exact cover is elementary; the unresolved high-valuation branch may dominate.

## 6. Seek a finite certificate of anchoredness

**Claim to test:** For fixed \(M,a\), every level-96 survivor has an integer anchor representation. Encode digit-position multiplicities, modular subgroup membership, and exclusion of every anchor in an explicitly bounded envelope. An independently checked unsatisfiability certificate establishes this only for the encoded slice.

**Removal:** would justify bypassing \(10^{19}\)–\(10^{22}\) patterns. This is a completeness obligation, not an available theorem.

**Literature:** Bertók–Hajdu, *A Hasse-type principle for exponential Diophantine equations and its applications*, known here through LIT2 and Dimitrov–Howe; original not read. No Hasse conjecture is assumed.

**Kill test, partly run:** prediction was that the full level-96 domain undermines the rare-accident argument. Exact multiset counts reproduce all six level-12 totals and give level-96 domains \(2.61\times10^{40}\)–\(2.09\times10^{48}\). Uniform-residue heuristics using the documented lattice index predict \(1.4\times10^3\)–\(1.1\times10^{11}\) accidental memberships per fixed \(a\), **before descent**. These are not observed survivors. Unrun: 120 CPU-minute certificate pilot; predict small-slice success, uncertain Tier-B scaling.

**Confidence LOW:** arithmetic may defeat proof compression; accidental survivors may exist.

## why the strongest of these might fail

The two-ended chain needs every hypothesis checked, including negative \(T_k=-1\), heights at least 1, and the self-referential inequality. Exact endpoint arithmetic cannot validate a misapplied theorem. Even if correct, it leaves initial enumeration intact.

Anchor compression can fail through exponentially many distinguishable states or incomplete coverage. A census of anchors cannot detect unanchored survivors. The full-domain heuristic makes this consequential, although descent could remove those accidents. Also, the census’s \(a\le60\) cutoff is empirical, while documented searches reach valuations above 100. Neither a cutoff nor timeout earns completeness.

“No better theorem found” also does not establish that a problem-specific improvement implies abc.

**Constant-factor work:** cached local logarithms, packed quotient tables, batched lattice intersections, memory-local joins.

**Next action:** independently audit idea 1’s theorem application, then run idea 2’s joint-DP pilot.
