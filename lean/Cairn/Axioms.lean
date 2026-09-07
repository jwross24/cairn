import Lean

open Lean

namespace Cairn.Axioms

def report (module : Name) (targets : Array Name) : CoreM Json := do
  if targets.isEmpty then throwError "empty-theorem-names"
  if targets.toList.eraseDups.length != targets.size then throwError "duplicate-theorem-name"
  let env ← getEnv
  let mut rows := []
  let mut reachable : Std.HashSet Name := {}
  let mut pending := targets
  for target in targets.qsort Name.lt do
    let some c := env.find? target | throwError "missing-theorem:{target}"
    let .thmInfo _ := c | throwError "target-not-theorem:{target}"
    let axioms ← collectAxioms target
    rows := rows ++ [(target.toString, toJson ((axioms.map Name.toString).qsort (· < ·)))]
  while !pending.isEmpty do
    let n := pending.back!
    pending := pending.pop
    if reachable.contains n then continue
    reachable := reachable.insert n
    let some c := env.find? n | throwError "missing-constant:{n}"
    pending := pending ++ c.type.getUsedConstants
    if let some value := c.value? (allowOpaque := true) then
      pending := pending ++ value.getUsedConstants
    if let .inductInfo v := c then pending := pending ++ v.ctors.toArray
  let mut unused : Array String := #[]
  for (n, _) in env.constants.toList do
    if reachable.contains n then continue
    let some idx := env.getModuleIdxFor? n | continue
    if env.header.moduleNames[idx.toNat]! != module then continue
    if (← collectAxioms n).contains `sorryAx then unused := unused.push n.toString
  return Json.mkObj [("theorems", Json.mkObj rows),
    ("unused_admissions", toJson (unused.qsort (· < ·)))]

end Cairn.Axioms

unsafe def main (args : List String) : IO UInt32 := do
  try
    let module :: targets := args | throw (IO.userError "expected-module-and-theorem-names")
    initSearchPath (← findSysroot)
    let env ← importModules #[{ module := module.toName }] {} 0
    let result ← (Cairn.Axioms.report module.toName (targets.map String.toName).toArray).toIO'
      { fileName := "<cairn-axioms>", fileMap := default } { env }
    (← IO.getStdout).putStrLn result.compress
    return 0
  catch e =>
    (← IO.getStderr).putStrLn e.toString
    return 1
