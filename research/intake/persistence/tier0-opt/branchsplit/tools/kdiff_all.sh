#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
for s in "$@"; do
  nice -n 10 uv run --no-project --with gmpy2 --with sympy python $B/tools/kdiff.py /private/tmp/persist-branchsplit/cand /private/tmp/persist-branchsplit/prod $s
  echo "rc=$?"
done
