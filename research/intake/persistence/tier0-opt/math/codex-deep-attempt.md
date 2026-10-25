# Deep attempt: symbolic block lifting for W2

**The barrier is not broken.** I obtain an exact polynomial-size block model and a sound certificate that can reject an entire family of copy choices. I cannot prove that such certificates exist for the Tier-C families. I also prove why two natural compression methods lose the required information.

Everything labeled **PROVED ON PAPER** has an ordinary mathematical proof below. Nothing has Cairn’s **PROVEN** status: no Lean check or statement-level review was performed. No conjecture enters an argument.

## Direction and grounding

I chose W2, replacing copy enumeration with a symbolic congruence and a modular separation certificate. I read DEEPCUT.md, SANDWICH.md, BAKER-CHAIN.md, LIT2.md, codex-brainstorm.md, h1-anchoring/REPORT.md, the anchor-first report, and the relevant lattice/descent implementations. I did not access breakthrough/.

The modular certificate idea has related prior art in [the STACS 2026 modular subset-sum paper](https://drops.dagstuhl.de/storage/00lipics/lipics-vol364-stacs2026/html/LIPIcs.STACS.2026.57/LIPIcs.STACS.2026.57.html). Its random-input guarantees do not apply to these structured coefficients. The certificate below is justified independently.

## Theorem 1: an exact symbolic block lift

**PROVED ON PAPER. Confidence HIGH:** an elementary nilpotence identity, checked directly by modular exponentiation.

Fix \(a\ge0\), \(s\ge a+3\), and \(1\le h\le s-a\). Let
\[
C=p+\mathbb Zu+\mathbb Zv
\]
be an exponent coset whose S-units have the same suffix modulo \(10^s\). Work with normalized units modulo \(5^{s+h}\) and \(2^{s+h-a}\). Choose a representative \(Y_0\) of the S-unit at \(p\), and write
\[
g_u=3^{u_1}7^{u_2},\quad g_v=3^{v_1}7^{v_2}.
\]
Negative powers mean modular inverses. Define, modulo \(M=10^h\),
\[
A_u=\frac{Y_0(g_u-1)}{10^s},\qquad
A_v=\frac{Y_0(g_v-1)}{10^s}.
\]
These quotients are integral with compatible modular representatives.

Let \(T\) be the suffix with the next block filled by 1s, including previously fixed digits, and put
\[
\beta=(T-Y_0)/10^s,\qquad w_j=(d_j-1)10^{e_j},
\]
where the optional digit occupies position \(s+e_j\), \(0\le e_j<h\).

Then extending the suffix is exactly
\[
A_u z_1+A_v z_2-\sum_jw_jx_j\equiv\beta\pmod M,
\qquad x_j\in\{0,1\}.
\]
Retain the original multiplicity constraints and at most one selected digit per physical position.

**Proof.** The parent condition gives
\[
v_2(g_i-1)\ge s-a,\qquad v_5(g_i-1)\ge s.
\]
After multiplication by \(Y_0\), every quadratic or higher term vanishes modulo \(10^{s+h}\), because
\[
2s-a\ge s+h,\qquad 2s\ge s+h.
\]
Consequently
\[
Y_0g_u^{z_1}g_v^{z_2}
\equiv Y_0+10^s(A_uz_1+A_vz_2)\pmod{10^{s+h}}.
\]
This holds for negative integer exponents too: inversion of \(1+t\) is \(1-t\) when \(t^2=0\). Comparing with the desired suffix proves equivalence. Construction requires polynomially many bit operations in the precision, number of digit variables, and basis bit length. \(\square\)

**Numerical checks:** 3,528 direct comparisons, using \(a=0,1,2,3\), \(s=a+3,\ldots,a+6\), every permitted \(h\), and \(z_1,z_2=-3,\ldots,3\). All passed. Exceeding the permitted precision was deliberately tested and failed: one example gave actual residue 558860141 versus linear prediction 158860141.

## Theorem 2: a certificate that rejects all choices together

**PROVED ON PAPER. Confidence HIGH:** an interval containment argument; its usefulness is a separate question.

Suppose \(|z_i|\le Z_i\), obtained conservatively by applying the inverse basis matrix to the bounded exponent box. For any integer multiplier \(\mu\), let
\[
r_i=[\mu A_i]_M,\qquad t_j=[\mu w_j]_M
\]
be centered residues. Put
\[
D=Z_1|r_1|+Z_2|r_2|,
\quad L=-D-\sum_j\max(t_j,0),
\quad U=D+\sum_j\max(-t_j,0).
\]
Let \(b=\mu\beta\bmod M\). If
\[
\left\lceil\frac{L-b}{M}\right\rceil>
\left\lfloor\frac{U-b}{M}\right\rfloor,
\]
the entire choice family is impossible.

**Proof.** Every admissible value of
\(r_1z_1+r_2z_2-\sum_jt_jx_j\) lies in \([L,U]\) and must equal \(b\) modulo \(M\). The displayed inequality says this interval contains no such integer. Dropping collision constraints only enlarges the interval, so cannot create a false rejection. \(\square\)

Certificate verification costs polynomial time, without listing copy choices. Finding a successful multiplier has no established subexponential guarantee here.

**Numerical checks:** 510 small instances modulo 20, 50, and 100. There were 180 sound rejections; all 318 feasible instances survived. Twelve infeasible instances remained undecided. These are tests of the certificate, not Tier-C closures.

## Theorem 3: saturation and the cost of explicit output

**PROVED ON PAPER. Confidence HIGH:** exact finite arithmetic plus the elementary order formula for principal units.

Define \(\Lambda\) using the recorded level-96 basis
\[
u=(-5834300434592217394015440000,-5252227908597256497593760000),
\]
\[
v=(24550795595028192589139040000,-26061931100684490688131840000).
\]
Direct modular exponentiation gives
\[
(v_2(g_u-1),v_5(g_u-1))=(9,5),\qquad
(v_2(g_v-1),v_5(g_v-1))=(10,5).
\]
Hence, for \(K-a\ge9\), \(K\ge5\), its normalized image is exactly
\[
(1+2^9\mathbb Z)/2^{K-a}
\times(1+5^5\mathbb Z)/5^K.
\]

**Proof.** Both generators lie in this group. The first has component orders
\(2^{K-a-9}\) and \(5^{K-5}\), by lifting the exponent. These orders are coprime, so its powers alone cover their product. \(\square\)

Consequently, once a suffix of length \(s\ge a+9\) is feasible, every extension preserving that suffix has a nonempty exponent fiber inside the parent. Distinct suffixes have disjoint fibers. For \(r\) independent occupied residue classes with one available digit each, an explicit output list therefore contains \(2^r\) cosets.

For repeated digits the correct one-block count is
\[
\prod_e(1+t_e),
\]
where \(t_e\) counts distinct available digit values in class \(e\). Labeling identical copies separately overcounts.

**Checks:** the basis vectors satisfy the ladder modulus directly; image orders at \(K=9,10,11\), \(a=0\), were 625, 6250, and 62500. All 510 targets from binary families with \(r=1,\ldots,8\) were distinct and compatible.

## Theorem 4: one optional 2 destroys affine-hull compression

**PROVED ON PAPER. Confidence HIGH:** the group generated by a single target ratio determines the hull.

Assume the preceding saturation conditions. Consider suffix targets sharing all positions below \(m\), including two targets differing only by an optional digit 2 at position \(m\). Suppose \(m\ge a+9\).

The smallest affine lattice containing all their unbounded exponent fibers at precision \(K>m\) is exactly the exponent coset determined by the suffix modulo \(10^m\).

**Proof.** The ratio of the two normalized targets has
\[
v_2(\rho-1)=m-a,\qquad v_5(\rho-1)=m.
\]
It generates the full kernel from precision \(K\) to \(m\), with order \(10^{K-m}\). The affine hull contains the precision-\(K\) exponent kernel and a lift of this ratio, so contains the whole precision-\(m\) fiber. All targets already belong to that fiber, proving equality. \(\square\)

**Checks:** 28 pairs \(9\le m<K\le16\) had the predicted order. At \(m=9,K=12\), two target words generated a hull with 1,000 suffixes, including an unwanted digit 3.

## A reachable Tier-C example

**Confidence HIGH in the following exact checks:** the integer identity and all reported fast cuts were verified. This is an anchored pattern for vertex
\[
128421199872=2^{23}3^7 7,
\]
with 31 non-1 digits. Put \(y=3^3 7^{10}=7626831723\), \(\nu=2\). The digit multisets at positions \(0,\ldots,9\) are
\[
(3;\ 2;\ 2,7;\ 2;\ 2,3;\ 2^{[8]};\ 2^{[6]};\
2^{[2]};\ 2^{[2]},3^{[2]};\ 2,3^{[3]}).
\]
Brackets denote multiplicity. Direct integer arithmetic verifies
\[
y=11+\sum_e\sum_{d\text{ at }e}(d-1)10^e.
\]

There are 5,184 distinct depth-1 class choices; six survive. Their depth-2 families contain respectively
\[
576,\ 384,\ 576,\ 576,\ 384,\ 576
\]
distinct cosets, totaling **3,072**, all nonempty.

Every parent has an optional 2 at position 98. Theorem 4 therefore reduces its depth-2 affine hull from precision 192 to precision 98. This is an actual Tier-C pattern, although it establishes no census or closure for its vertex.

The complete enumeration used the read-only blind implementation’s modular logarithms. The original Pohlig–Hellman implementation independently checked the first three parent families, totaling 1,536 children; its redundant remaining run was interrupted.

## Reproducibility and calibration

Scratch directory: /private/tmp/cairn-persistence-deep.Px4WuU.

Run from that directory with:
~~~bash
export UV_CACHE_DIR="$PWD/uv-cache"
export PYTHONDONTWRITEBYTECODE=1
uv run --no-project --offline python probe.py
uv run --no-project --offline python block_probe.py
uv run --no-project --offline python - <<'PY'
from pathlib import Path
source = Path("tierc_survivor.py").read_text().replace(
    "from descent import cut_coset", "from fast_cut import cut_coset"
)
exec(compile(source, "tierc_survivor.py", "exec"))
PY
~~~
Source SHA-256 values for descent.py, lattice.py, and lemma_c_blind.py, respectively:
~~~text
684766b3c1ef6888e93bb328e601f25d6451be55b4e95d6294be25c3c2ba56ed
3d514953dc8f91a55f60ad4b65ef0c44865b4ced028df802e96fcf99d925fd9f
16403c09e3a7ad6f5808b14b4e7185cc615631ea83b684e4ed35713ea1282a44
~~~
Each completed command ended PASS. Scratch sources remain available; they were not installed in the repository. These finite checks supplement the proofs and do not establish asymptotic success.

## HEURISTIC

Seeking modular separating rows for deeper symbolic blocks remains plausible. **Confidence LOW in achieving W2:** I found no successful Tier-C closure certificate, and the following obstruction applies before much branching has occurred.

## Where this breaks

**The certificate has a provable failure regime.** If \(Z_1,Z_2\ge M\) and \(\gcd(A_u,A_v,M)=1\), every multiplier fails to reject: a nonzero centered exponent coefficient makes the interval cover a full residue system; if both coefficients vanish, the multiplier itself is zero modulo \(M\).

All 9,900 small wide-box tests returned undecided. On the reachable Tier-C parent, the test box \(0\le b,c\le10^{600}\) gives coordinate bounds with 528 and 527 decimal digits, versus \(M=10^{96}\); the coefficient gcd is 1. The obstruction applies exactly.

Thus a polynomial-size model and cheap certificate do not supply a subexponential algorithm. Explicit fibers can proliferate, and one enclosing lattice discards almost a whole new block. These results constrain those two representations; other implicit representations remain possible.

The experiments cover one Tier-C multiset, not every vertex. Saturation concerns the specified level-96 lattice and suffix refinements; additional ladder constraints require separate analysis. No accident-density heuristic, absence of observed solutions, or unproved Hasse principle supplies the missing step. The unresolved task is a complete way to minimize exponent height over the symbolic Boolean family without enumerating its fibers.

