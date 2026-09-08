import FormalConjecturesUtil.Linters.ExistsImplicationLinter
set_option linter.style.existsImplication true

-- CASE literal_bounded_binder  the grounding's exact surface form
theorem litBounded : (∃ n : Nat, n > 0 ∧ (n ≠ 1 → False)) → True := fun _ => trivial
set_option pp.all false in
#check (∃ n : Nat, n > 0 ∧ (n ≠ 1 → False))
example : True := trivial
theorem litSugar : (∃ n > 0, (n : Nat) ≠ 1 → False) → True := fun _ => trivial
