import Mathlib.Data.Nat.Totient
import Mathlib.GroupTheory.OrderOfElement
import Mathlib.Tactic.NormNum.Prime
import Mathlib.Tactic.NormNum.DivMod
import Mathlib.Tactic.NormNum.GCD

namespace X5

theorem kill_one (p : ℕ) [Fact p.Prime] (u : (ZMod p)ˣ) (b : ℤ)
    (hb : ((p - 1 : ℕ) : ℤ) ∣ b) : u ^ b = 1 := by
  have hu : u ^ (p - 1) = 1 := by
    rw [← Nat.totient_prime (Fact.out : p.Prime), ← ZMod.card_units_eq_totient]
    exact pow_card_eq_one
  obtain ⟨k, rfl⟩ := hb
  rw [zpow_mul, zpow_natCast, hu, one_zpow]

theorem additive_kill (p : ℕ) [Fact p.Prime] (d : ℤ) (hd : ((p - 1 : ℕ) : ℤ) ∣ d)
    (u v : (ZMod p)ˣ) (b c : ℤ) (hb : d ∣ b) (hc : d ∣ c) : u ^ b * v ^ c = 1 := by
  rw [kill_one p u b (hd.trans hb), kill_one p v c (hd.trans hc), one_mul]

instance : Fact (Nat.Prime 769) := ⟨by norm_num⟩

def d₁ : ℤ := 13545045360000

theorem kill_769_planted (b c : ℤ) (hb : d₁ ∣ b) (hc : d₁ ∣ c) :
    (ZMod.unitOfCoprime 3 (by norm_num : Nat.Coprime 3 769)) ^ b *
      (ZMod.unitOfCoprime 7 (by norm_num : Nat.Coprime 7 769)) ^ c = 1 :=
  additive_kill 769 d₁ (by unfold d₁; norm_num) _ _ b c hb hc

end X5
