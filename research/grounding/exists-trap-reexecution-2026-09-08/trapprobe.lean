import FormalConjecturesUtil.Linters.ExistsImplicationLinter
import FormalConjecturesUtil.Linters.StubLinter

set_option linter.style.existsImplication true
set_option linter.style.stubs true

-- CASE plain_exists_implication  expect WARN
theorem plain : (∃ n : Nat, n ≠ 0 → False) → True := fun _ => trivial

-- CASE binder_predicate  expect SILENT (documented blind spot)
theorem binder : (∃ n : Nat, n > 0 ∧ (n ≠ 1 → False)) → True := fun _ => trivial

-- CASE conjunction_nested  expect SILENT (documented blind spot)
theorem nested : (∃ n : Nat, (n ≠ 0 → False) ∧ True) → True := fun _ => trivial

-- CASE clean_disjunction  expect SILENT
theorem clean : (∃ n : Nat, n ≠ 0 ∨ False) → True := fun _ => trivial

-- CASE axiom_decl  expect WARN
axiom myAx : (1 : Nat) = 2

-- CASE opaque_decl  expect WARN
opaque myOpaque : Nat

-- CASE def_sorry  expect WARN
def myDef : Nat := sorry

-- CASE theorem_sorry  expect SILENT (deliberate)
theorem thmSorry : (1 : Nat) = 1 := by sorry
