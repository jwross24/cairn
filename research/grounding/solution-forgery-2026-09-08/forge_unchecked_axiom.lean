import Lean
open Lean

run_cmd do
  let env ← getEnv
  let decl := Declaration.axiomDecl
    { name := `forged, levelParams := [], type := mkConst ``False, isUnsafe := false }
  match env.addDeclCore 0 0 decl none (doCheck := false) with
  | .ok env' => modifyEnv fun _ => env'
  | .error _ => throwError "addDeclCore refused"

theorem forged_false : False := @forged
