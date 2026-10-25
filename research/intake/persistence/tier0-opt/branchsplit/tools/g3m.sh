#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
W=/private/tmp/persist-branchsplit
export GATE_PY_OVERLAY=$B/gate-overlay
cd $W/gatev2x
for k in swap37 drop3; do
  nice -n 10 uv run --no-project --with gmpy2 --with sympy python gatev2.py --lvl12 $W/mutpipe_$k/lvl12 --jobs 2 --work $W/gwork --fast --out $B/logs/gate_mut_$k | tail -9 | cut -c1-200
done
echo DONE
