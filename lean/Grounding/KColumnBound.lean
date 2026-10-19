import Mathlib.Algebra.Order.Chebyshev
import Mathlib.Algebra.Order.BigOperators.Group.Finset
import Mathlib.Algebra.Field.Basic
import Mathlib.Data.Finset.Prod
import Mathlib.Tactic.Linarith

open Finset

/-- **k-column slope bound.** If a finite set `s` of points of the plane over a field `F` has
at most `k` distinct first coordinates, then the number of distinct finite slopes
`(q.2 - p.2) / (q.1 - p.1)` over pairs `p, q ∈ s` with `p.1 ≠ q.1` satisfies
`2 * k * #slopes ≤ (k - 1) * #s ^ 2`. -/
theorem k_column_slope_bound {F : Type*} [Field F] [DecidableEq F]
    (s : Finset (F × F)) (k : ℕ) (hk : (s.image Prod.fst).card ≤ k) :
    2 * k * (((s ×ˢ s).filter (fun pq : (F × F) × (F × F) => pq.1.1 ≠ pq.2.1)).image
        (fun pq : (F × F) × (F × F) => (pq.2.2 - pq.1.2) / (pq.2.1 - pq.1.1))).card
      ≤ (k - 1) * s.card ^ 2 := by
  set C := (s ×ˢ s).filter (fun pq : (F × F) × (F × F) => pq.1.1 ≠ pq.2.1) with hC
  set D := (s ×ˢ s).filter (fun pq : (F × F) × (F × F) => pq.1.1 = pq.2.1) with hD
  set f : (F × F) × (F × F) → F := fun pq => (pq.2.2 - pq.1.2) / (pq.2.1 - pq.1.1) with hf
  have hCD : C.card + D.card = s.card ^ 2 := by
    have h := card_filter_add_card_filter_not (s := s ×ˢ s)
      (fun pq : (F × F) × (F × F) => pq.1.1 ≠ pq.2.1)
    simp only [not_not] at h
    rw [card_product] at h
    rw [sq]
    exact h
  have hS : 2 * (C.image f).card ≤ C.card := by
    apply mul_card_image_le_card
    intro b hb
    obtain ⟨⟨p, q⟩, hpq, rfl⟩ := mem_image.mp hb
    have hmem := mem_filter.mp hpq
    obtain ⟨hps, hqs⟩ := mem_product.mp hmem.1
    have hne : p.1 ≠ q.1 := hmem.2
    have hsw : f (q, p) = f (p, q) := by
      show (p.2 - q.2) / (p.1 - q.1) = (q.2 - p.2) / (q.1 - p.1)
      rw [← neg_sub q.2 p.2, ← neg_sub q.1 p.1, neg_div_neg_eq]
    have hsub : ({(p, q), (q, p)} : Finset _) ⊆ {a ∈ C | f a = f (p, q)} := by
      intro x hx
      rcases mem_insert.mp hx with rfl | hx
      · exact mem_filter.mpr ⟨hpq, rfl⟩
      · rw [mem_singleton] at hx
        subst hx
        refine mem_filter.mpr ⟨?_, hsw⟩
        exact mem_filter.mpr ⟨mem_product.mpr ⟨hqs, hps⟩, fun h => hne h.symm⟩
    have hpair : ({(p, q), (q, p)} : Finset _).card = 2 := by
      apply card_pair
      intro h
      exact hne (by rw [(Prod.mk.inj h).1])
    calc 2 = ({(p, q), (q, p)} : Finset _).card := hpair.symm
      _ ≤ _ := card_le_card hsub
  have hm : s.card = ∑ c ∈ s.image Prod.fst, #{a ∈ s | a.1 = c} :=
    card_eq_sum_card_image Prod.fst s
  have hN : D.card = ∑ c ∈ s.image Prod.fst, #{a ∈ s | a.1 = c} ^ 2 := by
    rw [card_eq_sum_card_fiberwise (f := fun x : (F × F) × (F × F) => x.1.1)
      (t := s.image Prod.fst) ?_]
    · apply sum_congr rfl
      intro c _
      have : {a ∈ D | a.1.1 = c} = {a ∈ s | a.1 = c} ×ˢ {a ∈ s | a.1 = c} := by
        ext ⟨p, q⟩
        simp only [hD, mem_filter, mem_product]
        grind
      rw [this, card_product, sq]
    · intro x hx
      have := mem_filter.mp (mem_coe.mp hx)
      exact mem_coe.mpr (mem_image_of_mem _ (mem_product.mp this.1).1)
  have hcs : s.card ^ 2 ≤ k * D.card := by
    calc s.card ^ 2 = (∑ c ∈ s.image Prod.fst, #{a ∈ s | a.1 = c}) ^ 2 := by rw [← hm]
      _ ≤ (s.image Prod.fst).card * ∑ c ∈ s.image Prod.fst, #{a ∈ s | a.1 = c} ^ 2 :=
        sq_sum_le_card_mul_sum_sq
      _ = (s.image Prod.fst).card * D.card := by rw [hN]
      _ ≤ k * D.card := Nat.mul_le_mul_right _ hk
  rcases k with _ | j
  · have : s.card ^ 2 ≤ 0 := by simpa using hcs
    simp
  · simp only [Nat.add_sub_cancel]
    nlinarith [Nat.mul_le_mul_left (j + 1) hS, hcs, congrArg (fun x => (j + 1) * x) hCD]

/-- The set of finite slopes `(q.2 - p.2) / (q.1 - p.1)` over pairs of distinct-column points
among the first `i + 1` points `p 0, ..., p i` of a chain. -/
def slopes {F : Type*} [Field F] [DecidableEq F] (p : ℕ → F × F) (i : ℕ) : Finset F :=
  ((((range (i + 1)).image p) ×ˢ ((range (i + 1)).image p)).filter
      (fun pq : (F × F) × (F × F) => pq.1.1 ≠ pq.2.1)).image
    (fun pq : (F × F) × (F × F) => (pq.2.2 - pq.1.2) / (pq.2.1 - pq.1.1))

/-- The number of distinct finite slopes among the first `i + 1` points of the chain `p`. -/
def d {F : Type*} [Field F] [DecidableEq F] (p : ℕ → F × F) (i : ℕ) : ℕ :=
  (slopes p i).card

/-- **k-column bound on `d`.** If every prefix `p 0, ..., p i` of the chain occupies at most `k`
distinct first coordinates, then `2 * k * d p i ≤ (k - 1) * (i + 1) ^ 2`. -/
theorem k_column_d_bound {F : Type*} [Field F] [DecidableEq F]
    (p : ℕ → F × F) (k : ℕ)
    (hk : ∀ i, ((Finset.range (i + 1)).image (fun j => (p j).1)).card ≤ k) (i : ℕ) :
    2 * k * d p i ≤ (k - 1) * (i + 1) ^ 2 := by
  have h1 : (((range (i + 1)).image p).image Prod.fst).card ≤ k := by
    rw [Finset.image_image]
    exact hk i
  have h2 := k_column_slope_bound ((range (i + 1)).image p) k h1
  have h3 : ((range (i + 1)).image p).card ≤ i + 1 := by
    simpa using (card_image_le (s := range (i + 1)) (f := p))
  have h4 : ((range (i + 1)).image p).card ^ 2 ≤ (i + 1) ^ 2 := Nat.pow_le_pow_left h3 2
  exact le_trans h2 (Nat.mul_le_mul_left _ h4)

/-- **k-column weight bound.** For a chain whose every prefix occupies at most `k` distinct first
coordinates, the weight `∑ i < N, (l - d p i)` is at least
`∑ i < N, (l - ⌊(i + 1) ^ 2 * (k - 1) / (2 * k)⌋)`, with truncated natural subtraction and natural
division. -/
theorem k_column_weight_bound {F : Type*} [Field F] [DecidableEq F]
    (p : ℕ → F × F) (k l N : ℕ)
    (hk : ∀ i, ((Finset.range (i + 1)).image (fun j => (p j).1)).card ≤ k) :
    ∑ i ∈ Finset.range N, (l - (i + 1) ^ 2 * (k - 1) / (2 * k))
      ≤ ∑ i ∈ Finset.range N, (l - d p i) := by
  have hkpos : 0 < k := by
    have h0 := hk 0
    have : ((Finset.range (0 + 1)).image (fun j => (p j).1)).card = 1 := by simp
    omega
  apply Finset.sum_le_sum
  intro i _
  apply Nat.sub_le_sub_left
  have h := k_column_d_bound p k hk i
  rw [Nat.le_div_iff_mul_le (by omega)]
  calc d p i * (2 * k) = 2 * k * d p i := Nat.mul_comm _ _
    _ ≤ (k - 1) * (i + 1) ^ 2 := h
    _ = (i + 1) ^ 2 * (k - 1) := Nat.mul_comm _ _
