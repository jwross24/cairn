#!/bin/zsh
B=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/branchsplit
for s in "$@"; do
  nice -n 10 uv run --no-project python $B/tools/vcmp.py $B/logs/rows_prod_$s.jsonl $B/logs/rows_cand_$s.jsonl > $B/logs/vcmp_$s.json
  echo "vertex $s vcmp rc=$?"
done
