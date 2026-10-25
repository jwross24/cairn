#!/bin/zsh
W=/private/tmp/persist-branchsplit
cd $W/cand
for sk in "72 98,189,294,1161216" "224 784,2744,41472,71442,122472" "10800 11519532122112"; do
  set -- ${=sk}
  nice -n 10 uv run --no-project --with gmpy2 --with sympy python difftest.py $1 $2
  echo "difftest $1 rc=$?"
done
