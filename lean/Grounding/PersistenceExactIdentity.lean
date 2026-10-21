import Grounding.RepunitCongruence
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.BigOperators.Fin
import Mathlib.Tactic.Linarith

open Finset RepunitCongruence

namespace PersistenceExactIdentity

/-- **Exact identity from a congruence.** For `y ≤ V`, `y ≡ V (mod R_L)` holds exactly when
`V = y + k · R_L` for some natural `k`. -/
theorem exact_identity_iff {L y V : ℕ} (hyV : y ≤ V) :
    y ≡ V [MOD R L] ↔ ∃ k, V = y + k * R L := by
  rw [Nat.modEq_iff_dvd' hyV]
  constructor
  · rintro ⟨k, hk⟩
    exact ⟨k, by rw [mul_comm, ← hk]; omega⟩
  · rintro ⟨k, hk⟩
    exact ⟨k, by rw [mul_comm, hk]; omega⟩

theorem R_mono {m n : ℕ} (h : m ≤ n) : R m ≤ R n :=
  sum_le_sum_of_subset (range_mono h)

theorem pow_le_R {e L : ℕ} (h : e < L) : 10 ^ e ≤ R L :=
  single_le_sum (f := fun i => 10 ^ i) (fun _ _ => Nat.zero_le _) (mem_range.2 h)

/-- **Quotient bound.** For `ν < L`, digits at most `9` and positions below `L`, the pattern value
`R_ν + Σ (d_j - 1) · 10^(e_j)` over `q` entries has quotient at most `1 + 8q` by `R_L`. -/
theorem k_bound {L q : ℕ} (d : Fin q → ℕ) (hd : ∀ j, d j ≤ 9) {ν : ℕ} {e : Fin q → ℕ}
    (hν : ν < L) (he : ∀ j, e j < L) :
    (R ν + ∑ j, (d j - 1) * 10 ^ e j) / R L ≤ 1 + 8 * q := by
  apply Nat.div_le_of_le_mul
  have hterm : ∀ j, (d j - 1) * 10 ^ e j ≤ 8 * R L := fun j =>
    Nat.mul_le_mul (by have := hd j; omega) (pow_le_R (he j))
  have hsum : ∑ j, (d j - 1) * 10 ^ e j ≤ ∑ _j : Fin q, 8 * R L := sum_le_sum fun j _ => hterm j
  rw [sum_const, card_univ, Fintype.card_fin, smul_eq_mul] at hsum
  have := R_mono hν.le
  nlinarith

end PersistenceExactIdentity
