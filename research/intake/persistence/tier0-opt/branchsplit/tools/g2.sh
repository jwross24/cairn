#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
O=$B/logs
W=/private/tmp/persist-branchsplit
for s in "$@"; do
  K=$(cd $W && ./py known.py $s)
  for d in prod cand; do
    ( cd $W && nice -n 10 uv run --no-project --with gmpy2 --with sympy python $B/tools/vrows.py $W/$d $s "$K" 2 $O/rows_${d}_$s.jsonl )
  done
  nice -n 10 uv run --no-project --with gmpy2 --with sympy python $B/tools/vcmp.py $O/rows_prod_$s.jsonl $O/rows_cand_$s.jsonl > $O/vcmp_$s.json
  echo "vertex $s vcmp rc=$?"
done
