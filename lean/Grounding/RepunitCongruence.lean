import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Data.Nat.ModEq
import Mathlib.Tactic.Ring

open Finset

namespace RepunitCongruence

/-- The repunit `R n = 1 + 10 + ⋯ + 10^(n-1)`. -/
def R (n : ℕ) : ℕ := ∑ i ∈ range n, 10 ^ i

theorem nine_mul_R_add_one (n : ℕ) : 9 * R n + 1 = 10 ^ n := by
  induction n with
  | zero => simp [R]
  | succ n ih =>
    simp only [R, sum_range_succ] at ih ⊢
    rw [pow_succ]
    omega

theorem R_add (a b : ℕ) : R (a + b) = R a + 10 ^ a * R b := by
  simp only [R, sum_range_add, pow_add, mul_sum]

theorem pow_modEq_one (L : ℕ) : 10 ^ L ≡ 1 [MOD R L] := by
  rw [← nine_mul_R_add_one L]
  have h := (Nat.modEq_zero_iff_dvd.2 (dvd_mul_left (R L) 9)).add_right 1
  rwa [Nat.zero_add] at h

theorem R_add_mul_modEq (L r q : ℕ) : R (r + L * q) ≡ R r [MOD R L] := by
  induction q with
  | zero =>
    simp only [Nat.mul_zero, Nat.add_zero]
    exact Nat.ModEq.refl _
  | succ q ih =>
    rw [show r + L * (q + 1) = (r + L * q) + L by ring, R_add]
    refine Nat.ModEq.trans ?_ ih
    have h := (Nat.modEq_zero_iff_dvd.2 (dvd_mul_left (R L) (10 ^ (r + L * q)))).add_left
      (R (r + L * q))
    rwa [Nat.add_zero] at h

theorem pow_add_mul_modEq (L r q : ℕ) : 10 ^ (r + L * q) ≡ 10 ^ r [MOD R L] := by
  rw [pow_add, pow_mul]
  simpa using ((pow_modEq_one L).pow q).mul_left (10 ^ r)

theorem R_modEq {L n ν : ℕ} (h : n ≡ ν [MOD L]) : R n ≡ R ν [MOD R L] := by
  have hn := R_add_mul_modEq L (n % L) (n / L)
  have hν := R_add_mul_modEq L (ν % L) (ν / L)
  rw [Nat.mod_add_div] at hn hν
  rw [show n % L = ν % L from h] at hn
  exact hn.trans hν.symm

theorem pow_modEq {L n ν : ℕ} (h : n ≡ ν [MOD L]) : 10 ^ n ≡ 10 ^ ν [MOD R L] := by
  have hn := pow_add_mul_modEq L (n % L) (n / L)
  have hν := pow_add_mul_modEq L (ν % L) (ν / L)
  rw [Nat.mod_add_div] at hn hν
  rw [show n % L = ν % L from h] at hn
  exact hn.trans hν.symm

/-- **Open-pattern congruence.** If `y = R ν + Σ (d j - 1) 10^(e j)`, then every
`y' = R n + Σ (d j - 1) 10^(E j)` with `n ≡ ν` and `E j ≡ e j (mod L)` satisfies
`y' ≡ y (mod R L)`. The bounds `ν < L`, `e j < L` of the pattern reading are not needed. -/
theorem candidate_modEq {L k : ℕ} (d : Fin k → ℕ) {ν n y y' : ℕ} {e E : Fin k → ℕ}
    (hy : y = R ν + ∑ j, (d j - 1) * 10 ^ e j)
    (hy' : y' = R n + ∑ j, (d j - 1) * 10 ^ E j)
    (hn : n ≡ ν [MOD L]) (hE : ∀ j, E j ≡ e j [MOD L]) :
    y' ≡ y [MOD R L] := by
  subst hy hy'
  refine (R_modEq hn).add ?_
  unfold Nat.ModEq
  rw [sum_nat_mod, sum_nat_mod (s := univ) (f := fun j => (d j - 1) * 10 ^ e j)]
  congr 1
  exact sum_congr rfl fun j _ => ((pow_modEq (hE j)).mul_left (d j - 1))

end RepunitCongruence
