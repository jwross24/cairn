import Mathlib.Data.Int.ModEq
import Mathlib.Algebra.Ring.Int.Defs
import Mathlib.Algebra.Ring.Divisibility.Basic
import Mathlib.Tactic.Ring
import Mathlib.Tactic.LinearCombination
import Mathlib.Data.ZMod.Basic
import Mathlib.Algebra.Group.Int.Units
import Mathlib.RingTheory.Coprime.Lemmas
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

theorem unit_zpow_lift {R : Type*} [CommRing R] {y x : R} (hyx : y * x * x = 0) (G : Rˣ)
    (hG : (G : R) = 1 + x) (z : ℤ) : y * ((G ^ z : Rˣ) : R) = y + z * (y * x) := by
  have key : ∀ (w : R) (c : ℤ), y * w = y + c * (y * x) → y * x * w = y * x →
      ∀ n : ℕ, y * w ^ n = y + (n * c) * (y * x) := by
    intro w c h1 h2 n
    induction n with
    | zero => simp
    | succ n ih =>
      have : y * w ^ (n + 1) = (y * w ^ n) * w := by ring
      rw [this, ih]
      have e : (y + ((n : ℤ) * c) * (y * x)) * w = y * w + ((n : ℤ) * c) * (y * x * w) := by ring
      push_cast at e ⊢
      rw [e, h1, h2]
      ring
  have hxG : y * x * (G : R) = y * x := by rw [hG]; linear_combination hyx
  have hyG : y * (G : R) = y + ((1 : ℤ) : R) * (y * x) := by rw [hG]; push_cast; ring
  have hxGi : y * x * ((G⁻¹ : Rˣ) : R) = y * x := by
    have := congrArg (fun r => r * ((G⁻¹ : Rˣ) : R)) hxG
    simpa [mul_assoc] using this.symm
  have hyGi : y * ((G⁻¹ : Rˣ) : R) = y + (-1 : ℤ) * (y * x) := by
    have h3 : y * ((G⁻¹ : Rˣ) : R) - (y - y * x) = ((G⁻¹ : Rˣ) : R) * (y * x * x) := by
      have hinv : (G : R) * ((G⁻¹ : Rˣ) : R) = 1 := by simp
      have hx : x = (G : R) - 1 := by rw [hG]; ring
      calc y * ((G⁻¹ : Rˣ) : R) - (y - y * x)
          = y * ((G⁻¹ : Rˣ) : R) - (y - y * x) * ((G : R) * ((G⁻¹ : Rˣ) : R)) := by rw [hinv, mul_one]
        _ = ((G⁻¹ : Rˣ) : R) * (y * x * x) := by rw [hx]; ring
    rw [hyx, mul_zero] at h3
    push_cast
    linear_combination h3
  rcases z with n | n
  · rw [Int.ofNat_eq_natCast, zpow_natCast, Units.val_pow_eq_pow_val]
    simpa using key _ 1 hyG hxG n
  · rw [zpow_negSucc, ← inv_pow, Units.val_pow_eq_pow_val]
    have := key _ (-1) hyGi hxGi (n + 1)
    push_cast at this ⊢
    linear_combination this

theorem dvd_ten_pow {m : ℕ} {x : ℤ} (h2 : (2 : ℤ) ^ m ∣ x) (h5 : (5 : ℤ) ^ m ∣ x) :
    (10 : ℤ) ^ m ∣ x := by
  have hc : IsCoprime ((2 : ℤ) ^ m) ((5 : ℤ) ^ m) :=
    IsCoprime.pow (Int.isCoprime_iff_gcd_eq_one.2 (by decide))
  rw [show (10 : ℤ) ^ m = 2 ^ m * 5 ^ m by rw [← mul_pow]; norm_num]
  exact hc.mul_dvd h2 h5

theorem prod_dvd {Y g₁ g₂ : ℤ} {a s h : ℕ} (has : a ≤ s) (hh : h ≤ s - a) (hY : (2 : ℤ) ^ a ∣ Y)
    (h₁2 : (2 : ℤ) ^ (s - a) ∣ g₁ - 1) (h₁5 : (5 : ℤ) ^ s ∣ g₁ - 1)
    (h₂2 : (2 : ℤ) ^ (s - a) ∣ g₂ - 1) (h₂5 : (5 : ℤ) ^ s ∣ g₂ - 1) :
    (10 : ℤ) ^ (s + h) ∣ Y * (g₁ - 1) * (g₂ - 1) := by
  apply dvd_ten_pow
  · have : (2 : ℤ) ^ (a + (s - a) + (s - a)) ∣ Y * (g₁ - 1) * (g₂ - 1) := by
      rw [pow_add, pow_add]; exact mul_dvd_mul (mul_dvd_mul hY h₁2) h₂2
    exact (pow_dvd_pow 2 (by omega)).trans this
  · have : (5 : ℤ) ^ (s + s) ∣ Y * (g₁ - 1) * (g₂ - 1) := by
      have h3 := (mul_dvd_mul h₁5 h₂5).mul_left Y
      rw [← pow_add, ← mul_assoc] at h3
      exact h3
    exact (pow_dvd_pow 5 (by omega)).trans this

/-- **Two-generator block lift.** With `N = 10^(s+h)`, `2^a ∣ Y₀`, `v₂(g_i − 1) ≥ s − a`,
`v₅(g_i − 1) ≥ s` and `h ≤ s − a`, and `Y₀ (g_i − 1) = 10^s A_i`, then for all integers `z₁ z₂`
the unit powers satisfy `Y₀ g_u^z₁ g_v^z₂ ≡ Y₀ + 10^s (A_u z₁ + A_v z₂) (mod N)`. -/
theorem two_generator_lift {Y gu gv Au Av : ℤ} {a s h : ℕ} (has : a ≤ s) (hh : h ≤ s - a)
    (hY : (2 : ℤ) ^ a ∣ Y)
    (hu2 : (2 : ℤ) ^ (s - a) ∣ gu - 1) (hu5 : (5 : ℤ) ^ s ∣ gu - 1)
    (hv2 : (2 : ℤ) ^ (s - a) ∣ gv - 1) (hv5 : (5 : ℤ) ^ s ∣ gv - 1)
    (hYu : Y * (gu - 1) = 10 ^ s * Au) (hYv : Y * (gv - 1) = 10 ^ s * Av)
    (Gu Gv : (ZMod (10 ^ (s + h)))ˣ) (hGu : (Gu : ZMod (10 ^ (s + h))) = gu)
    (hGv : (Gv : ZMod (10 ^ (s + h))) = gv) (z₁ z₂ : ℤ) :
    (Y : ZMod (10 ^ (s + h))) * ((Gu ^ z₁ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h))) *
        ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h))) =
      Y + 10 ^ s * (Au * z₁ + Av * z₂) := by
  have z0 : ∀ x : ℤ, (10 : ℤ) ^ (s + h) ∣ x → ((x : ℤ) : ZMod (10 ^ (s + h))) = 0 := fun x hx => by
    have := (ZMod.intCast_zmod_eq_zero_iff_dvd x (10 ^ (s + h))).2 (by exact_mod_cast hx)
    exact this
  have huu := z0 _ (prod_dvd has hh hY hu2 hu5 hu2 hu5)
  have huv := z0 _ (prod_dvd has hh hY hu2 hu5 hv2 hv5)
  have hvv := z0 _ (prod_dvd has hh hY hv2 hv5 hv2 hv5)
  push_cast at huu huv hvv
  have hGu' : (Gu : ZMod (10 ^ (s + h))) = 1 + ((gu : ZMod (10 ^ (s + h))) - 1) := by rw [hGu]; ring
  have hGv' : (Gv : ZMod (10 ^ (s + h))) = 1 + ((gv : ZMod (10 ^ (s + h))) - 1) := by rw [hGv]; ring
  have e1 := unit_zpow_lift (y := (Y : ZMod (10 ^ (s + h)))) (x := (gu : ZMod (10 ^ (s + h))) - 1) (by linear_combination huu) Gu hGu' z₁
  have hyx1 : (Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1) * ((gv : ZMod (10 ^ (s + h))) - 1) = 0 := huv
  have e2 := unit_zpow_lift (y := (Y : ZMod (10 ^ (s + h)))) (x := (gv : ZMod (10 ^ (s + h))) - 1) (by linear_combination hvv) Gv hGv' z₂
  have e3 := unit_zpow_lift (y := (Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1)) (x := (gv : ZMod (10 ^ (s + h))) - 1)
    (by rw [hyx1, zero_mul]) Gv hGv' z₂
  have hA1 : (Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1) = 10 ^ s * Au := by exact_mod_cast congrArg (Int.cast : ℤ → ZMod (10 ^ (s + h))) hYu
  have hA2 : (Y : ZMod (10 ^ (s + h))) * ((gv : ZMod (10 ^ (s + h))) - 1) = 10 ^ s * Av := by exact_mod_cast congrArg (Int.cast : ℤ → ZMod (10 ^ (s + h))) hYv
  have : (Y : ZMod (10 ^ (s + h))) * ((Gu ^ z₁ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h))) * ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h))) =
      ((Y : ZMod (10 ^ (s + h))) + z₁ * ((Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1))) * ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h))) := by
    rw [e1]
  rw [this]
  have e4 : ((Y : ZMod (10 ^ (s + h))) + z₁ * ((Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1))) * ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h)))
      = ((Y : ZMod (10 ^ (s + h))) * ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h)))) +
        z₁ * (((Y : ZMod (10 ^ (s + h))) * ((gu : ZMod (10 ^ (s + h))) - 1)) * ((Gv ^ z₂ : (ZMod (10 ^ (s + h)))ˣ) : ZMod (10 ^ (s + h)))) := by ring
  rw [e4, e2, e3, hyx1]
  rw [hA1, hA2]
  ring

end PersistenceBlockLift
