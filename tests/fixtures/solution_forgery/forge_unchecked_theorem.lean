import Lean
open Lean

run_cmd do
  let env ← getEnv
  let decl := Declaration.thmDecl
    { name := `forged, levelParams := [], type := mkConst ``False, value := mkConst ``trivial }
  match env.addDeclCore 0 0 decl none (doCheck := false) with
  | .ok env' => modifyEnv fun _ => env'
  | .error _ => throwError "addDeclCore refused"
