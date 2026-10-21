import Mathlib.Data.Int.ModEq
import Mathlib.Algebra.Ring.Int.Defs
import Mathlib.Algebra.Ring.Divisibility.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.Linarith

namespace PersistenceBlockLift

theorem sq_dvd {s h : ℕ} (hh : s + h ≤ 2 * s) {t : ℤ} (ht : (10 : ℤ) ^ s ∣ t) :
    (10 : ℤ) ^ (s + h) ∣ t ^ 2 := by
  have : (10 : ℤ) ^ (s + h) ∣ (10 : ℤ) ^ (2 * s) := pow_dvd_pow 10 hh
  exact this.trans (by rw [pow_mul']; exact pow_dvd_pow_of_dvd ht 2)

/-- **Nilpotence identity.** If `10^s ∣ t` and `s + h ≤ 2s` then
`(1 + t)^z ≡ 1 + z · t (mod 10^(s+h))` for every natural `z`. -/
theorem pow_one_add_modEq {s h : ℕ} (hh : s + h ≤ 2 * s) {t : ℤ} (ht : (10 : ℤ) ^ s ∣ t)
    (z : ℕ) : (1 + t) ^ z ≡ 1 + z * t [ZMOD 10 ^ (s + h)] := by
  have hsq := sq_dvd hh ht
  induction z with
  | zero => simp [Int.ModEq.refl]
  | succ z ih =>
    rw [Int.modEq_iff_dvd] at ih ⊢
    have h1 := dvd_sub (ih.mul_right (1 + t)) (hsq.mul_left (z : ℤ))
    rw [pow_succ]
    push_cast
    have e : 1 + ((z : ℤ) + 1) * t - (1 + t) ^ z * (1 + t) =
        (1 + (z : ℤ) * t - (1 + t) ^ z) * (1 + t) - z * t ^ 2 := by ring
    rw [e]
    exact h1

/-- The inverse form: a modular inverse `u` of `1 + t` satisfies `u ≡ 1 - t (mod 10^(s+h))`. -/
theorem inverse_modEq {s h : ℕ} (hh : s + h ≤ 2 * s) {t u : ℤ} (ht : (10 : ℤ) ^ s ∣ t)
    (hu : u * (1 + t) ≡ 1 [ZMOD 10 ^ (s + h)]) : u ≡ 1 - t [ZMOD 10 ^ (s + h)] := by
  have hsq := sq_dvd hh ht
  rw [Int.modEq_iff_dvd] at hu ⊢
  have h1 := dvd_sub (hu.mul_right (1 - t)) (hsq.mul_left u)
  have e : 1 - t - u = (1 - u * (1 + t)) * (1 - t) - u * t ^ 2 := by ring
  rw [e]
  exact h1

/-- The inverse form for powers: `u^z ≡ 1 - z · t (mod 10^(s+h))`. -/
theorem inverse_pow_modEq {s h : ℕ} (hh : s + h ≤ 2 * s) {t u : ℤ} (ht : (10 : ℤ) ^ s ∣ t)
    (hu : u * (1 + t) ≡ 1 [ZMOD 10 ^ (s + h)]) (z : ℕ) :
    u ^ z ≡ 1 - z * t [ZMOD 10 ^ (s + h)] := by
  have h2 : u ≡ 1 + -t [ZMOD 10 ^ (s + h)] := by simpa [sub_eq_add_neg] using inverse_modEq hh ht hu
  have h3 := pow_one_add_modEq hh (dvd_neg.2 ht) z
  have := (h2.pow z).trans h3
  simpa [sub_eq_add_neg] using this

/-- The same identity for a natural `t`. -/
theorem pow_one_add_modEq_nat {s h : ℕ} (hh : s + h ≤ 2 * s) {t : ℕ} (ht : 10 ^ s ∣ t) (z : ℕ) :
    (1 + t) ^ z ≡ 1 + z * t [MOD 10 ^ (s + h)] := by
  have := pow_one_add_modEq hh (t := (t : ℤ)) (by exact_mod_cast ht) z
  exact_mod_cast (Int.natCast_modEq_iff (a := (1 + t) ^ z) (b := 1 + z * t) (n := 10 ^ (s + h))).1
    (by exact_mod_cast this)

end PersistenceBlockLift
