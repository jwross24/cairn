import Grounding.RepunitCongruence
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Data.Nat.ModEq
import Mathlib.Tactic.NormNum
import Mathlib.Tactic.NormNum.Prime

open Finset RepunitCongruence

namespace PersistenceBranchSplit

theorem sum_modEq {ι : Type*} {n : ℕ} (s : Finset ι) {f g : ι → ℕ}
    (h : ∀ i ∈ s, f i ≡ g i [MOD n]) : ∑ i ∈ s, f i ≡ ∑ i ∈ s, g i [MOD n] := by
  classical
  induction s using Finset.induction_on with
  | empty => simp [Nat.ModEq.refl]
  | insert a s ha ih =>
    rw [sum_insert ha, sum_insert ha]
    exact (h a (mem_insert_self a s)).add (ih fun i hi => h i (mem_insert_of_mem hi))

theorem R_three_mul_modEq (r q : ℕ) : R (r + 3 * q) ≡ R r [MOD 3] :=
  (R_add_mul_modEq 3 r q).of_dvd (by decide : 3 ∣ R 3)

theorem R_six_mul_modEq (r q : ℕ) : R (r + 6 * q) ≡ R r [MOD 7] :=
  (R_add_mul_modEq 6 r q).of_dvd (by decide : 7 ∣ R 6)

theorem R_modEq_three {m n : ℕ} (h : m ≡ n [MOD 3]) : R m ≡ R n [MOD 3] := by
  have hm := R_three_mul_modEq (m % 3) (m / 3)
  have hn := R_three_mul_modEq (n % 3) (n / 3)
  rw [Nat.mod_add_div] at hm hn
  rw [show n % 3 = m % 3 from h.symm] at hn
  exact hm.trans hn.symm

theorem R_modEq_seven {m n : ℕ} (h : m ≡ n [MOD 6]) : R m ≡ R n [MOD 7] := by
  have hm := R_six_mul_modEq (m % 6) (m / 6)
  have hn := R_six_mul_modEq (n % 6) (n / 6)
  rw [Nat.mod_add_div] at hm hn
  rw [show n % 6 = m % 6 from h.symm] at hn
  exact hm.trans hn.symm

theorem pow_ten_modEq_three (e : ℕ) : 10 ^ e ≡ 1 [MOD 3] := by
  simpa using (show 10 ≡ 1 [MOD 3] by decide).pow e

theorem pow_ten_modEq_seven {m n : ℕ} (h : m ≡ n [MOD 6]) : 10 ^ m ≡ 10 ^ n [MOD 7] := by
  have key : ∀ r q : ℕ, 10 ^ (r + 6 * q) ≡ 10 ^ r [MOD 7] := fun r q => by
    have : (10 ^ 6) ^ q ≡ 1 [MOD 7] := by
      simpa using (show 10 ^ 6 ≡ 1 [MOD 7] by decide).pow q
    calc 10 ^ (r + 6 * q) = 10 ^ r * (10 ^ 6) ^ q := by rw [pow_add, pow_mul]
      _ ≡ 10 ^ r * 1 [MOD 7] := this.mul_left _
      _ = 10 ^ r := mul_one _
  have hm := key (m % 6) (m / 6)
  have hn := key (n % 6) (n / 6)
  rw [Nat.mod_add_div] at hm hn
  rw [show n % 6 = m % 6 from h.symm] at hn
  exact hm.trans hn.symm

/-- Pattern values modulo `3` are given by `ν + Σ (d_j - 1)`. -/
theorem value_modEq_three {q : ℕ} (d : Fin q → ℕ) (ν : ℕ) (e : Fin q → ℕ) :
    R ν + ∑ j, (d j - 1) * 10 ^ e j ≡ ν + ∑ j, (d j - 1) [MOD 3] := by
  have hR : R ν ≡ ν [MOD 3] := by
    simpa [R] using (sum_modEq (range ν) (f := fun i => 10 ^ i) (g := fun _ => 1)
      fun i _ => pow_ten_modEq_three i)
  refine hR.add (sum_modEq _ fun j _ => ?_)
  simpa using (pow_ten_modEq_three (e j)).mul_left (d j - 1)

/-- **Residue determination.** The value `R_ν + Σ (d_j - 1) · 10^(e_j)` modulo `3` and modulo `7`
depends only on `ν` and the `e_j` modulo `12`. -/
theorem value_modEq_of_modEq_twelve {q : ℕ} (d : Fin q → ℕ) {ν ν' : ℕ} {e e' : Fin q → ℕ}
    (hν : ν ≡ ν' [MOD 12]) (he : ∀ j, e j ≡ e' j [MOD 12]) :
    (R ν + ∑ j, (d j - 1) * 10 ^ e j ≡ R ν' + ∑ j, (d j - 1) * 10 ^ e' j [MOD 3]) ∧
    (R ν + ∑ j, (d j - 1) * 10 ^ e j ≡ R ν' + ∑ j, (d j - 1) * 10 ^ e' j [MOD 7]) := by
  constructor
  · exact (R_modEq_three (hν.of_dvd (by norm_num))).add
      (sum_modEq _ fun j _ => by
        exact ((pow_ten_modEq_three (e j)).trans (pow_ten_modEq_three (e' j)).symm).mul_left _)
  · exact (R_modEq_seven (hν.of_dvd (by norm_num))).add
      (sum_modEq _ fun j _ => (pow_ten_modEq_seven ((he j).of_dvd (by norm_num))).mul_left _)

theorem exponent_zero_of_not_dvd_three {a b c : ℕ} (h : ¬ 3 ∣ 2 ^ a * 3 ^ b * 7 ^ c) : b = 0 := by
  by_contra hb
  exact h (Dvd.dvd.mul_right (Dvd.dvd.mul_left (dvd_pow_self 3 hb) _) _)

theorem exponent_zero_of_not_dvd_seven {a b c : ℕ} (h : ¬ 7 ∣ 2 ^ a * 3 ^ b * 7 ^ c) : c = 0 := by
  by_contra hc
  exact h (Dvd.dvd.mul_left (dvd_pow_self 7 hc) _)

end PersistenceBranchSplit
