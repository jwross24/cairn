import Mathlib.Algebra.Order.Group.Nat
import Mathlib.Data.Nat.ModEq
import Mathlib.Algebra.Group.Nat.Even
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.NormNum.GCD
import Mathlib.Tactic.Positivity

namespace DeepCutCongruence

theorem ten_pow (K : ℕ) : 10 ^ K = 2 ^ K * 5 ^ K := by
  rw [← mul_pow]
  norm_num

theorem unit_modEq_five {K a w ℓ : ℕ} (h : 2 ^ a * w ≡ 2 ^ a * ℓ [MOD 10 ^ K]) :
    w ≡ ℓ [MOD 5 ^ K] := by
  rw [ten_pow] at h
  exact Nat.ModEq.cancel_left_of_coprime (Nat.Coprime.pow K a (by norm_num))
    (Nat.ModEq.of_mul_left (2 ^ K) h)

theorem unit_modEq_two {K a w ℓ : ℕ} (ha : a ≤ K) (h : 2 ^ a * w ≡ 2 ^ a * ℓ [MOD 10 ^ K]) :
    w ≡ ℓ [MOD 2 ^ (K - a)] := by
  rw [ten_pow] at h
  have h2 := Nat.ModEq.of_mul_right (5 ^ K) h
  rw [show 2 ^ K = 2 ^ a * 2 ^ (K - a) by rw [← pow_add, Nat.add_sub_cancel' ha]] at h2
  exact Nat.ModEq.mul_left_cancel' (by positivity) h2

theorem pow_succ_dvd_iff (n w : ℕ) : 2 ^ (n + 1) ∣ 2 ^ n * w ↔ 2 ∣ w := by
  rw [pow_succ, Nat.mul_dvd_mul_iff_left (by positivity)]

theorem pow_succ_dvd_of_lt {n m : ℕ} (h : n < m) (w : ℕ) : 2 ^ (n + 1) ∣ 2 ^ m * w :=
  Dvd.dvd.mul_right (Nat.pow_dvd_pow 2 h) w

theorem pow_succ_dvd_iff_of_modEq {n K x y : ℕ} (hn : n < K) (h : x ≡ y [MOD 10 ^ K]) :
    2 ^ (n + 1) ∣ x ↔ 2 ^ (n + 1) ∣ y :=
  Nat.ModEq.dvd_iff h (by rw [ten_pow]; exact Dvd.dvd.mul_right (Nat.pow_dvd_pow 2 hn) _)

theorem two_adic_eq {K a a' w ℓ : ℕ} (haK : a < K) (hw : ¬ 2 ∣ w) (hℓ : ¬ 2 ∣ ℓ)
    (h : 2 ^ a' * w ≡ 2 ^ a * ℓ [MOD 10 ^ K]) : a' = a := by
  rcases lt_trichotomy a' a with hlt | heq | hgt
  · exact absurd ((pow_succ_dvd_iff a' w).1
      ((pow_succ_dvd_iff_of_modEq (hlt.trans haK) h).2 (pow_succ_dvd_of_lt hlt ℓ))) hw
  · exact heq
  · exact absurd ((pow_succ_dvd_iff a ℓ).1
      ((pow_succ_dvd_iff_of_modEq haK h).1 (pow_succ_dvd_of_lt hgt w))) hℓ

/-- **Deep-cut arithmetic core (Lemma C).** If `y' = 2^a' · 3^b · 7^c` agrees with
`L = 2^a · ℓ` (`ℓ` odd, `a < K`) modulo `10^K`, then `v₂(y') = v₂(L)`, i.e. `a' = a`, and the unit
part satisfies `3^b · 7^c ≡ ℓ (mod 5^K)` and `3^b · 7^c ≡ ℓ (mod 2^(K - a))`. -/
theorem deep_cut_core {K a a' b c ℓ : ℕ} (haK : a < K) (hℓ : Odd ℓ)
    (h : 2 ^ a' * (3 ^ b * 7 ^ c) ≡ 2 ^ a * ℓ [MOD 10 ^ K]) :
    a' = a ∧ 3 ^ b * 7 ^ c ≡ ℓ [MOD 5 ^ K] ∧ 3 ^ b * 7 ^ c ≡ ℓ [MOD 2 ^ (K - a)] := by
  have hw : ¬ 2 ∣ 3 ^ b * 7 ^ c :=
    Nat.two_dvd_ne_zero.mpr (Nat.odd_iff.mp ((Odd.pow ⟨1, rfl⟩).mul (Odd.pow ⟨3, rfl⟩)))
  obtain rfl := two_adic_eq haK hw (Nat.two_dvd_ne_zero.mpr (Nat.odd_iff.mp hℓ)) h
  exact ⟨rfl, unit_modEq_five h, unit_modEq_two haK.le h⟩

end DeepCutCongruence
