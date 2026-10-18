namespace HalfWeight

structure State where
  pts : List (Nat × Nat)
  det : List Bool
  idx : Nat
  total : Nat
  found : Nat

def invDiff (l : Nat) (px x : Nat) : Nat :=
  if px = x + 1 then 1
  else if x = px + 1 then l - 1
  else if px = x + 2 then (l + 1) / 2
  else l - (l + 1) / 2

def pairStep (l : Nat) (p : Nat × Nat) (st : State) (q : Nat × Nat) : State :=
  if q.1 = p.1 then st
  else
    let r := ((q.2 + l - p.2) % l * invDiff l q.1 p.1) % l
    if st.det.getD r false then st
    else
      { st with det := st.det.set r true, total := st.total + st.idx, found := st.found + 1 }

def addPoint (l : Nat) (st : State) (p : Nat × Nat) : State :=
  if st.found = l then st
  else if st.pts.contains p then st
  else
    let st' := st.pts.foldl (pairStep l p) st
    { st' with pts := st'.pts ++ [p], idx := st'.idx + 1 }

def roundStep (l n : Nat) (st : State) (t : Nat) : State :=
  let st1 := addPoint l st (0, t % l)
  let st2 := addPoint l st1 (1, (t * n) % l)
  addPoint l st2 (2, (l - (t * (n + 1)) % l) % l)

def initialState (l : Nat) : State :=
  { pts := [], det := List.replicate l false, idx := 0, total := 0, found := 0 }

def chainFreeWeight (l n : Nat) : Nat :=
  let st0 := [(0, 0), (0, 1 % l), (1, 0), (2, 0)].foldl (addPoint l) (initialState l)
  ((List.range l).foldl (fun st i => roundStep l n st (i + 1)) st0).total

def polyS (n : Nat) : Int :=
  let m : Int := n
  let a : Int × Int × Int × Int :=
    match n % 4 with
    | 0 => (0, -28, -7, 47)
    | 1 => (3, -43, -7, 47)
    | 2 => (-4, -28, -7, 47)
    | _ => (-5, -43, -7, 47)
  (a.1 + a.2.1 * m + a.2.2.1 * m ^ 2 + a.2.2.2 * m ^ 3) / 16

def polyR (n : Nat) : Int :=
  let m : Int := n
  let b : Int × Int × Int × Int :=
    match n % 4 with
    | 0 => (-48, 32, -11, 2)
    | 1 => (-35, 28, -11, 2)
    | 2 => (-36, 32, -11, 2)
    | _ => (-39, 28, -11, 2)
  (b.1 + b.2.1 * m + b.2.2.1 * m ^ 2 + b.2.2.2 * m ^ 3) / 16

def deltaTerm (n : Nat) (e : Int) : Int :=
  if e ≤ -2 * (n : Int) - 3 ∧ ¬ (n % 2 = 1 ∧ e = -3 * (n : Int) - 2) then 1 else 0

def diagLimit (n : Nat) (g : Int) (j : Nat) : Int :=
  (n : Int) - j + (g - j) / (n : Int)

def innerSum (j : Nat) (d : Int) : Nat :=
  if d < 0 then 0
  else (List.range (d.toNat + 1)).foldl (fun a k => a + min (3 * k + 1) (3 * j + 2)) 0

def gTerm (n : Nat) (g : Int) : Nat :=
  (List.range n).foldl (fun acc j => acc + innerSum j (diagLimit n g j)) 0

def roundLevel (n l T : Nat) : Int :=
  ((l - 1) / 2 : Nat) - (T * n : Nat) - ((T * (n + 2) + 1) / 2 : Nat)

def hTerm (n l : Nat) : Int :=
  let c : Int := ((n + 1) / 2 : Nat)
  (List.range (l + 1)).foldl
    (fun acc T =>
      if T < n then acc
      else
        let L := roundLevel n l T
        acc + max 0 (L + c + n) + max 0 (L + c) + max 0 L)
    0

def formulaWeight (l n : Nat) : Int :=
  let e : Int := (l : Int) - 4 * (n : Int) ^ 2
  let g : Int := (e - 1) / 2
  3 * (n : Int) * l - 2 - polyS n + polyR n + deltaTerm n e + (gTerm n g : Int) + hTerm n l

end HalfWeight

open HalfWeight

set_option maxRecDepth 100000
set_option maxHeartbeats 0

/-- At the prime 101 with n = 5, the chain-free weight value is 1260. -/
theorem half_weight_101_value : chainFreeWeight 101 5 = 1260 := by decide

/-- At the prime 101 with n = 5, the closed formula of Theorem A evaluates to 1260. -/
theorem half_formula_101_value : formulaWeight 101 5 = 1260 := by decide

/-- At the prime 101 with n = 5, the chain-free weight equals the closed formula of Theorem A. -/
theorem half_weight_101 : (chainFreeWeight 101 5 : Int) = formulaWeight 101 5 := by decide

