theorem cairn_dlp_iff {F : Type} [Field F] [DecidableEq F] {W : WeierstrassCurve.Affine F}
    (P Q : W.Point) : (∃ k : ℤ, k • P = Q) ↔ Q ∈ AddSubgroup.zmultiples P :=
  (AddSubgroup.mem_zmultiples_iff).symm
