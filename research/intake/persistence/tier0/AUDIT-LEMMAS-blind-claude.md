# Re-proofs of the two lemmas behind Method steps 5 and 6

Notation. y = R_n + Σ_j (d_j − 1)·10^{e_j}, R_n = (10^n − 1)/9, digits d_j ∈ M ⊂ {2..9}, positions
e_j distinct, 0 ≤ e_j < n. y = 2^a 3^b 7^c with a fixed by the pattern. "Coset" means
C = v + Λ ⊂ Z², Λ a rank-2 lattice with basis β⁽¹⁾, β⁽²⁾, and the true (b, c) lies in C.

## Lemma A (10-adic pinning, step 5)

**Statement.** For K ≥ 1 say (★_K) holds if for both basis vectors β = (β₁, β₂):
3^{β₁}7^{β₂} ≡ 1 (mod 5^K), and, when K > a, also 3^{β₁}7^{β₂} ≡ 1 (mod 2^{K−a}).
If (★_K) holds then (b, c) ↦ 2^a 3^b 7^c mod 10^K is constant on C. Moreover (★_K) ⇒ (★_{K−1}),
so K* := max{K : (★_K)} is well defined, and K* < ∞.

**Proof.** The maps ψ₅ : Z² → (Z/5^K)^×, (x, y) ↦ 3^x 7^y and (for K > a) ψ₂ : Z² → (Z/2^{K−a})^×
are group homomorphisms (3 and 7 are units mod 5 and mod 2), so they vanish on Λ iff they vanish on a
basis of Λ; (★_K) says exactly that. For two points (b, c), (b', c') of C the difference lies in Λ,
hence 3^b 7^c ≡ 3^{b'} 7^{c'} mod 5^K and (K > a) mod 2^{K−a}. Multiplying by 2^a gives congruence of
2^a3^b7^c and 2^a3^{b'}7^{c'} mod 5^K and mod 2^K (for K ≤ a both are ≡ 0 mod 2^K). CRT gives
mod 10^K. Monotonicity is clear (reduce the congruences). Finiteness: if (★_K) held for all K then
3^{β₁}7^{β₂} = 1 in Z₅ for a nonzero integer vector, i.e. 3^{β₁} = 7^{−β₂} in Q, impossible. ∎

Negative coordinates are harmless (the homomorphisms are defined on all of Z²); the value for the
true, nonnegative (b, c) equals the value at any representative.

**Hypotheses the description leaves implicit (none of them false, all needed):**
1. a is part of the pattern (it is: the residue congruences already depend on a).
2. The true (b, c) lies in C. True because C is the exact solution set of necessary congruences
   — this is why the lattice step must be exact and the discrete logs verified.
3. The 2-adic condition is mod 2^{K−a}, not mod 2^K, and is void when K ≤ a. The description says this.
4. "The last K* digits of y are known" is only meaningful when n ≥ K*; when n < K* the whole of y
   equals Y. The description handles this ("if n ≤ K*, y is known exactly").

Verdict: **correct as stated.**

## Lemma B (2-adic descent, step 6)

**Statement.** Suppose the last K digits of y are known, Y := y mod 10^K, and n ≥ K. Let
H = {j : e_j ≥ K} and m := min({n} ∪ {e_j : j ∈ H}) (so m ≥ K). Put t := v₂(9Y − 10^K).
Then 9y = 10^n − 10^K + Σ_{j∈H} 9(d_j − 1)10^{e_j} + 9Y, and: if m > t then a = t.
Equivalently: a ≠ t ⇒ K ≤ m ≤ t.

**Proof.** y − Y is y with its low K digits removed: y − Y = Σ_{i=K}^{n−1} 10^i + Σ_{j∈H} (d_j − 1)10^{e_j}
(positions ≥ K carry a 1 except the e_j with j ∈ H, which carry d_j). Multiply by 9 and use
9·Σ_{i=K}^{n−1}10^i = 10^n − 10^K. In the identity, v₂(10^n) = n ≥ m and
v₂(9(d_j − 1)10^{e_j}) ≥ e_j ≥ m, so the sum of those terms has v₂ ≥ m. If m > t the remaining term
9Y − 10^K has the strictly smallest valuation, so v₂(9y) = t, and v₂(9y) = v₂(y) = a. Note
9Y − 10^K ≠ 0 since 9 ∤ 10^K. ∎

So when a ≠ t, the "next event" (the smallest position ≥ K that is either the end of the number or
a non-1 digit) lies in [K, t]: finitely many cases. In the case e_high = m with digit d, the digits
at K..m−1 are 1 and the digit at m is d, so y mod 10^{m+1} = Y + (10^m − 10^K)/9 + **d**·10^m
(not (d−1)·10^m — the (d−1) form belongs to the R_n decomposition, which already has a 1 at m;
I made exactly this mistake in my first implementation and the positive control caught it).
In the case n = m, y = Y + (10^m − 10^K)/9 exactly and no digit of M may remain unplaced.

**Facts the description omits that matter for understanding what the lemma can do:**
1. *The lemma is vacuous when a < K.* Since y ≡ Y (mod 2^K), a < K gives v₂(Y) = a < K =
   v₂(10^K), so t = v₂(9Y − 10^K) = a automatically. The descent can only act when a ≥ K, i.e. when
   2^K | Y. This is the mechanism behind the addendum's "silent because v₂(9Y − 10^K) = a".
2. *The recursion necessarily ends in silence or exactness.* Each active step raises the known
   length from K to m + 1 > K and the step is active only while a ≥ K. Hence after at most a − K + 1
   steps the known length exceeds a and the lemma is silent. Therefore step 6 alone cannot "resolve
   every pattern"; a pattern is closed only if, along every branch, the tail test (step 5), an empty
   coset cut, or the exact candidate test fires. For the seven Tier-0 vertices this does happen
   (verified below); the addendum's 27 open patterns show it is not guaranteed in general.
3. Hypothesis n ≥ K is required (the identity is false otherwise); the n ≤ K* case must be handled
   separately by exactness, which the description does.
4. The case n = m ("the number is exactly the extended tail") must be enumerated: it is a genuine
   case of the lemma, not an edge case. The authors report having missed it once (child 93312 of 162).
   My implementation includes it; it is the branch that recovers e.g. 1161216 (m = n = 7, t = 7).
5. The cut "2^a3^b7^c ≡ Y' (mod 10^{K'})" splits as: mod 5^{K'} one congruence mod 4·5^{K'−1}
   (3 generates (Z/5^K)^×, fine); mod 2^{K'}: if K' ≤ a only the condition 2^{K'} | Y' (no
   congruence on (b, c)); if K' > a then v₂(Y') must equal a and 3^b7^c ≡ Y'/2^a (mod 2^{K'−a}),
   which gives a parity congruence b + c ≡ ε (mod 2) plus one congruence mod 2^{K'−a−2}
   (from (Z/2^e)^× = ⟨−1⟩×⟨5⟩). "Two linear congruences" undercounts and "(Z/2^K)^×" must be read
   as (Z/2^{K−a})^× applied to Y'/2^a; this is an imprecision, not an error.
6. Which digit may sit at m is restricted by the pattern (its residue class must be ≡ m mod L);
   using that restriction is sound and strictly stronger than "a high digit".

Verdict: **correct as stated, under the hypotheses n ≥ K (implicit) and that the coset is exact.**
It is weaker than the prose suggests: it only acts on patterns with a ≥ K*, and it never closes a
pattern by itself — closure always comes from the tail test, an empty coset, or an exact candidate.
