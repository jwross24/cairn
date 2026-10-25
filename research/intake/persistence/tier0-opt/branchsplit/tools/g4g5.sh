#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
W=/private/tmp/persist-branchsplit
PY=(nice -n 10 uv run --no-project --with gmpy2 --with sympy python)
CAP=232906752
echo "== G4 plants candidate"
${PY[@]} $B/tools/plants.py $W/cand $CAP $W/plwork_cand $B/logs/plants_cand.jsonl
for k in swap37 drop3; do
  echo "== G5 $k vertex 224 (expect refusal)"
  K=$(cd $W && ./py known.py 224)
  (cd $W/mutpipe_$k && ${PY[@]} run_vertex_c.py 224 "$K" 2 > /dev/null 2> $B/logs/mut_${k}_224.err; echo "rc=$?"; grep -m1 "POSITIVE CONTROL" $B/logs/mut_${k}_224.err)
  echo "== G5 $k kernel differential 72 224 (expect mismatch)"
  for s in 72 224; do
    ${PY[@]} $B/tools/kdiff.py $W/cand $W/prod $s $W/mutpipe_$k/lvl12 $W/kdiff_$k | tail -3
    echo "rc=$?"
  done
  echo "== G5 $k plants"
  ${PY[@]} $B/tools/plants.py $W/mutpipe_$k $CAP $W/plwork_$k $B/logs/plants_mut_$k.jsonl
done
echo DONE
