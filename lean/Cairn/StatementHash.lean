import Lean

open Lean

namespace Cairn.StatementHash

def frame (s : String) : String := s!"{s.utf8ByteSize}:{s}"

def node (tag : String) (fields : List String := []) : String :=
  frame tag ++ frame (String.join (fields.map frame))

def names (ns : List Name) : String :=
  node "names" (ns.map encodeName)
where
  encodeName : Name → String
    | .anonymous => node "anonymous"
    | .str p s => node "str" [encodeName p, s]
    | .num p n => node "num" [encodeName p, toString n]

def name (n : Name) : String := names.encodeName n

def level : Level → String
  | .zero => node "zero"
  | .succ l => node "succ" [level l]
  | .max a b => node "max" [level a, level b]
  | .imax a b => node "imax" [level a, level b]
  | .param n => node "param" [name n]
  | .mvar n => node "mvar" [name n.name]

partial def expr : Expr → String
  | .bvar n => node "bvar" [toString n]
  | .fvar n => node "fvar" [name n.name]
  | .mvar n => node "mvar" [name n.name]
  | .sort l => node "sort" [level l]
  | .const n ls => node "const" [name n, node "levels" (ls.map level)]
  | .app f a => node "app" [expr f, expr a]
  | .lam _ t b _ => node "lam" [expr t, expr b]
  | .forallE _ t b _ => node "forall" [expr t, expr b]
  | .letE _ t v b _ => node "let" [expr t, expr v, expr b]
  | .lit (.natVal n) => node "nat" [toString n]
  | .lit (.strVal s) => node "string" [s]
  | .mdata _ e => expr e
  | .proj n i e => node "proj" [name n, toString i, expr e]

def constantVal (v : ConstantVal) : String :=
  node "constant" [name v.name, names v.levelParams, expr v.type]

def hints : ReducibilityHints → String
  | .opaque => node "opaque"
  | .abbrev => node "abbrev"
  | .regular n => node "regular" [toString n]

def safety : DefinitionSafety → String
  | .safe => "safe"
  | .unsafe => "unsafe"
  | .partial => "partial"

def info (c : ConstantInfo) : String :=
  let base := constantVal c.toConstantVal
  match c with
  | .axiomInfo v => node "axiom" [base, toString v.isUnsafe]
  | .defnInfo v => node "definition" [base, expr v.value, hints v.hints, safety v.safety, names v.all]
  | .thmInfo v => node "theorem" [base, expr v.value, names v.all]
  | .opaqueInfo v => node "opaque" [base, expr v.value, toString v.isUnsafe, names v.all]
  | .inductInfo v => node "inductive" [base, toString v.numParams, toString v.numIndices,
      names v.all, names v.ctors, toString v.numNested, toString v.isRec,
      toString v.isUnsafe, toString v.isReflexive]
  | .ctorInfo v => node "constructor" [base, name v.induct, toString v.cidx,
      toString v.numParams, toString v.numFields, toString v.isUnsafe]
  | .recInfo v => node "recursor" [base, names v.all, toString v.numParams,
      toString v.numIndices, toString v.numMotives, toString v.numMinors,
      node "rules" (v.rules.map fun r => node "rule" [name r.ctor, toString r.nfields, expr r.rhs]),
      toString v.k, toString v.isUnsafe]
  | .quotInfo v => node "quotient" [base, match v.kind with
      | .type => "type" | .ctor => "ctor" | .lift => "lift" | .ind => "ind"]

def dependencies (c : ConstantInfo) : Array Name := Id.run do
  let mut result := c.type.getUsedConstants
  if let some v := c.value? (allowOpaque := true) then
    result := result ++ v.getUsedConstants
  match c with
  | .inductInfo v => result := result ++ v.ctors.toArray ++ v.all.toArray
  | .ctorInfo v => result := result.push v.induct
  | .recInfo v =>
    for r in v.rules do
      result := result.push r.ctor ++ r.rhs.getUsedConstants
  | _ => pure ()
  return result

def canonical (env : Environment) (targets : Array Name) : Except String String := do
  if targets.isEmpty then throw "empty-theorem-names"
  let sorted := targets.qsort Name.lt
  if sorted.toList.eraseDups.length != sorted.size then throw "duplicate-theorem-name"
  let mut pending := #[]
  let mut roots := []
  for target in sorted do
    let some c := env.find? target | throw s!"missing-theorem:{target}"
    let .thmInfo v := c | throw s!"target-not-theorem:{target}"
    roots := roots ++ [constantVal v.toConstantVal]
    pending := pending ++ v.type.getUsedConstants
  let mut seen : Std.HashSet Name := {}
  let mut closure : Array Name := #[]
  while !pending.isEmpty do
    let n := pending.back!
    pending := pending.pop
    if seen.contains n then continue
    seen := seen.insert n
    let some c := env.find? n | throw s!"missing-constant:{n}"
    if targets.contains n then
      pending := pending ++ c.type.getUsedConstants
    else
      closure := closure.push n
      pending := pending ++ dependencies c
  let mut records := []
  for n in closure.qsort Name.lt do
    let some c := env.find? n | throw s!"missing-constant:{n}"
    records := records ++ [info c]
  return node "cairn.formal-statement.v1" [node "targets" roots, node "closure" records]

def hex (bytes : ByteArray) : String := Id.run do
  let alphabet := "0123456789abcdef".toList.toArray
  let mut result := ""
  for b in bytes do
    result := result.push alphabet[b.toNat / 16]!
    result := result.push alphabet[b.toNat % 16]!
  return result

end Cairn.StatementHash

unsafe def main (args : List String) : IO UInt32 := do
  try
    let module :: targets := args | throw (IO.userError "expected-module-and-theorem-names")
    initSearchPath (← findSysroot)
    let env ← importModules #[{ module := module.toName }] {} 0
    match Cairn.StatementHash.canonical env (targets.map String.toName).toArray with
    | .error reason =>
      (← IO.getStderr).putStrLn reason
      return 1
    | .ok bytes =>
      (← IO.getStdout).putStrLn (Json.mkObj [("canonical_hex", toJson (Cairn.StatementHash.hex bytes.toUTF8))]).compress
      return 0
  catch e =>
    (← IO.getStderr).putStrLn e.toString
    return 1
