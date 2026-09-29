theorem cairn_finite_point {F : Type} [Field F] [Finite F] (W : WeierstrassCurve.Affine F) :
    Finite W.Point := by
  classical
  let f : W.Point → Option (F × F) := fun
    | .zero => none
    | .some x y _ => some (x, y)
  refine Finite.of_injective f ?_
  rintro (_ | ⟨x₁, y₁, h₁⟩) (_ | ⟨x₂, y₂, h₂⟩) h
  · rfl
  · cases h
  · cases h
  · simp only [f, Option.some.injEq, Prod.mk.injEq] at h
    obtain ⟨rfl, rfl⟩ := h
    rfl
