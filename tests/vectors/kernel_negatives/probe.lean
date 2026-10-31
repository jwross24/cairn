import Export.Parse
import Lean

deriving instance BEq for Lean.QuotKind
deriving instance BEq for Lean.QuotVal
deriving instance BEq for Lean.InductiveVal
deriving instance BEq for Lean.ConstantInfo

def runBuiltinKernel (solution : Export.ExportedEnv) : IO (Option String) := do
  let env ← Lean.mkEmptyEnvironment
  let mut kernelEnv := env.toKernelEnv
  let origConstMap := solution.constMap
  let quotTargets := [`Quot.mk, `Quot.lift, `Quot.ind]
  let kernelConstMap := quotTargets.foldl (init := origConstMap) (·.erase ·)
  try
    kernelEnv ← kernelEnv.replay kernelConstMap
  catch e =>
    return some s!"kernel: {e}"
  try
    let verifyTargets := `Quot :: quotTargets
    for quotTarget in verifyTargets do
      if let some info := origConstMap[quotTarget]? then
        let some info' := kernelEnv.find? quotTarget |
          throw <| .userError s!"Could not find quotient constant in final kernel env: {quotTarget}"
        if info != info' then
          throw <| .userError s!"Quotient constant mismatch on: {quotTarget}"
    return none
  catch e =>
    return some s!"quot-postcheck: {e}"

def main (args : List String) : IO UInt32 := do
  let [inputPath] := args | do
    IO.println "USAGE"
    return 3
  let handle ← IO.FS.Handle.mk inputPath .read
  match ← (Export.parseStream (.ofHandle handle)).toBaseIO with
  | .error e =>
    IO.println s!"PARSE-FAIL {e}"
    return 2
  | .ok env =>
    match ← runBuiltinKernel env with
    | none =>
      IO.println s!"ACCEPT {env.constMap.size}"
      return 0
    | some msg =>
      IO.println s!"REJECT {msg}"
      return 1
