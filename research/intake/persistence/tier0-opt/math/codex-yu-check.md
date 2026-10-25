# Independent Yu constant check

**HIGH confidence: the 2007 constants agree; three reported 2013 constants require correction.** The smaller 2013 bounds have proofs explicitly omitted in print. This is a source-and-arithmetic audit, not a Lean-certified theorem.

Sources: Yu, *Forum Math.* 19 (2007), 187–280 [Y07], and *Acta Math.* 211 (2013), 315–382 [Y13], owner-supplied PDFs. Page references below use printed pagination. Independent statements and calculations were recorded in `codex-yu/independent-{statements,arithmetic}.txt` before opening `yu-audit/`. No PDFs were copied.

## Setup and hypotheses

Write \(\Xi=\prod_{j=1}^3\alpha_j^{b_j}\), \(H_j=h_0(\alpha_j)\), \(L=\log5\), and \(P=H_1H_2H_3\). All logarithms are natural. Common hypotheses: nonzero algebraic numbers in a number field \(K\), integer exponents, a prime ideal above the rational prime, and \(\Xi\ne1\) [Y07 pp.187–189; Y13 pp.318–320].

For the requested rational units, \(e_{\mathfrak p}=f_{\mathfrak p}=1\), so ideal and rational valuations agree. The defining inequality gives \(\kappa=0\): \(4/5\le2<4\) [Y07 p.188 (1.2); Y13 p.318 (1.2); specialization inferred].

**H07:** \(n\ge2\), multiplicative independence, units, integer exponents not all zero, \(\operatorname{ord}_5b_n\le\operatorname{ord}_5b_j\), and condition (1.5). At \(p=5\), that condition requires \(\zeta_4\in K\), since \(\operatorname{ord}_2(5-1)=2\ne1\). Take \(K=\mathbb Q(i)\), \(d=2\), \(q^u=4\) [Y07 pp.188,190; specialization inferred].

**H13:** the same independence, unit, exponent, and ordering hypotheses, but (1.5) only requires \(\zeta_3\in K\) when \(p=2\). Thus \(K=\mathbb Q\), \(d=1\), \(q^u=2\) is allowed [Y13 pp.319,321].

For application variants put \(B\ge\max_j\{|b_j|,3\}\). Define \(W\) or \(\Omega\) by minimizing, over maximal independent subsets, the product of ordinary heights on the subset and modified heights on its complement [Y07 pp.192–194; Y13 p.323]. For independent triples these equal \(P\).

## Statements, constants, and printed proofs

Here \(A_{07}=C_1\), \(D_{07}=C_2\) from Y07 p.189; \(A_{13}=C_1\), \(D_{13}=C_2\) from Y13 p.320. Numerical exponents are independently computed specializations of those formulas.

| Result | Statement and additional hypotheses | Proof in print | \(\log_{10}C\), independent triple |
|---|---|---|---|
| Y07 Theorem II, p.260 | H07; \(\operatorname{ord}_5(\Xi-1)<D_{07}P h^{(2)}\) | Part II, pp.260–279; final details abbreviated p.279 | 9.302816 |
| Y07 Theorem 1, p.193 | \(n\ge1\), (1.5), units; no independence/order assumption; \(<(n+1)A_{07}W\log B\). Height floor \(L/[k_1(n+4)d]\) | §11, pp.249–253 | 11.268354 |
| Y07 Theorem 3, p.194 | Same hypotheses; \(<(n+1)D_{07}W\log B\). Floor \(1/(k_2 5^\kappa d)\) | Deduction from II by analogy to §11 explicitly omitted, p.279 | 9.904876 |
| Y07 first consequence, pp.190–191 | Common setup; no independence, unit, or (1.5) assumption; \(<nC_0\prod h_j\log B\), \(h_j=\max(H_j,1/(16e^2d^2))\) | Detailed deduction/computation explicitly omitted, p.194 | 13.046886, \(d=1\) |
| Y13 Theorem 1, p.323 | Rank \(r\ge1\), units, (1.5); no independence/order assumption; \(<(n+1)A_{13}\Omega\max(\log B,L)\). Floor \(\max(n,L)/[\kappa_1(n+5)d]\); rank one permits factor \(1/2100\) | Theorem I, §§2–7, pp.325–369; deduction §8, pp.369–373 | 9.922335 |
| Y13 Theorem 2, p.323 | Same hypotheses; replace \(A_{13}\) by \(D_{13}\); floor \(\max(n/L,1)/(\kappa_2 5^\kappa d)\); rank-one factor \(1/4000\) | Explicitly omitted, p.325 | 8.624565 |
| Y13 Main, p.321 | H13; \(<P\min(A_{13}h^{(1)},D_{13}h^{(2)})\) | First branch printed; second branch proof explicitly omitted, p.325 | 9.320275; 8.022505 |
| Y13 Theorem II, p.325 | H13; literally \(<D_{13}P h^{(1)}\) | Explicitly omitted, p.325 | 8.022505 |

Theorem II's printed \(h^{(1)}\) conflicts with the claimed equivalence to the Main Theorem. Treating it as \(h^{(2)}\) is an **inferred typographical correction**, not the literal statement.

## Exact extraction and arithmetic

Y07 case III applies, not case II: the latter requires ramification. For \(n=3\), p.195 gives

\[
(c^{(1)},a^{(1)},k_1)=(1473,32/3,10),\quad
(c^{(2)},a^{(2)},k_2)=(1576/3,8,4e^2),
\]
\[
(a_0^{(1)},a_1^{(1)},a_2^{(1)})=(2+\log8,.32,3.01),\quad
(a_0^{(2)},a_1^{(2)},a_2^{(2)})=(1+\log8,2.4,6.44).
\]

With \(F_2=4+\log8\), equations (1.6)–(1.7), p.189 give exactly

\[
A_{07}=1473(32/3)^3\frac{27\cdot256}{6}\frac54(2/L)^5F_2,
\quad D_{07}=\frac{1576}3 8^3\frac{256}2\frac54\frac{32}{L^3}F_2.
\]

The first consequence uses
\[
nC_0=3(10e)^8 3^{3/2}\log6\log2\frac5{L^2}.
\]
The replacement of \(16e\) by \(10e\) for \(p>2\) is printed on **p.191**; retaining \(16e\) gives exponent 14.679846 [Y07 pp.190–191].

Y13 case III.2 gives \((c^{(1)},a^{(1)},\kappa_1)=(1790,28/3,12)\), \((c^{(2)},a^{(2)},\kappa_2)=(2228/3,7,25)\), \(a_0^{(i)}=2+\log7\), \(a_1^{(1)}=a_2^{(1)}=5.84\), \(a_1^{(2)}=3.32\) [p.324]. The saturated residue subgroup contains the residue of 3, of order four, hence \(\delta=1\) [inferred from pp.319–320 construction]. No Kummer-degree conjecture is needed.

Set \(F_1=4+\log4\), \(M_1=\max(5/L^4,e^3/27)\), \(M_2=\max(5,(e^3/27)L^4)\). Then [Y13 p.320]:
\[
A_{13}=1790(28/3)^3\frac{27\cdot256}{6}\frac{M_1F_1}{2L},\quad
D_{13}=\frac{2228}3 7^3\frac{256}2\frac{M_2F_1}{2L^3}.
\]

For \(b_3=1\), the exact Main-Theorem log factor is
\[
h^{(i)}=\max\left\{\log\!\left(\omega(d)\max_{j<3}(1/H_j+|b_j|/H_3)\right),0,G_i\right\},
\]
also including \(4L\) for Y13. Here \(\omega(2)=1/(2\log^3 6)\), \(\omega(1)=\log2\log3/\log6\); \((G_1,G_2)_{07}=(67.122642,72.317933)\), \((G_1,G_2)_{13}=(82.200145,66.176099)\) [Y07 p.189; Y13 pp.320–321; decimals computed]. These factors cannot silently become \(\log B\).

## Claude comparison

Against `yu-audit/consts_out.txt`:

* **Agree:** Y07 first consequence 13.05, Theorem 1 11.27, Theorem 3 9.90, Theorem II 9.30.
* **Y13 Theorem 1: 10.10 → 9.922335.** `yu_consts.py` uses \(8(p-1)/(p-2)\), but (1.28), p.324 specifies **7**. Its coefficient is too large by \((8/7)^3\).
* **Y13 Theorem 2: 7.97 → 8.624565; Main: 7.37 → 8.022505.** The script uses **8 rather than 7** and reuses \(M_1\) where (1.10), p.320 requires \(M_2=L^4M_1\). Correct/script ratio: \((7/8)^3L^4=4.494911\).
* **BK 15.09:** arithmetic agrees, 15.092300, for the script's expression. **Not verified in print:** neither supplied paper identifies that expression as BK; its attribution is outside this two-paper check.

## Hypothesis fit

**HIGH, conditional on the stated application identities.** Set \(\alpha_3=2^a/T_j\), \((b_1,b_2,b_3)=(b+2,c,1)\). Then \(\Xi=M/T_j\); placing the folded rational last proves the ordering condition. The application identity \(M-T_j=N_j10^{E_j}>0\) proves nonvanishing; excluding digit 5 makes every \(T_j\) a 5-adic unit [application: `NOTE-2026-10-21.md` §4.3–4.4; elementary inference].

Dependence occurs exactly when \(T_j=\pm2^a3^u7^v\), by rational prime valuations. Handle it separately: write \(\Xi=\pm3^{b+2-u}7^{c-v}\). For the minus sign, squaring bounds the valuation using two independent bases; \(\Xi=-1\) has valuation zero. Use an exponent bound covering the resulting doubled exponents. Alternatively use the rank-two application variants with modified heights, never a zero height product. This is an elementary reduction, not a conjecture.

**HIGH:** Y07 requires \(\mathbb Q(i)\); Y13 permits \(\mathbb Q\). **MEDIUM for downstream chain conclusions:** this audit establishes coefficients and hypothesis reductions, not the chain/depth outputs or the omitted 2013 proofs.
