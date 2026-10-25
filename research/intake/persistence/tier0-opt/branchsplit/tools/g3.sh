#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
W=/private/tmp/persist-branchsplit
export GATE_PY_OVERLAY=$B/gate-overlay
cd $W/gatev2x
mode=$1
shift
nice -n 10 uv run --no-project --with gmpy2 --with sympy python gatev2.py --lvl12 $B/lvl12 --jobs 2 --work $W/gwork --out $B/logs/gate_$mode "$@"
echo "GATE rc=$?"
echo DONE
