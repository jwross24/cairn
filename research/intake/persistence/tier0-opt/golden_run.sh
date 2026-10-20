#!/bin/zsh
# usage: golden_run.sh <outdir> [ncores]
out=$1; nc=${2:-4}
PY=/Users/jwross/Documents/cairn/research/intake/persistence/tier0/.venv/bin/python3
mkdir -p $out
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt
for spec in "4:14" "14:27,72" "27:" "98:" "189:" "294:" "72:98,189,294,1161216"; do
  s=${spec%%:*}; k=${spec#*:}
  nice -n 10 $PY run_vertex_c.py $s "$k" $nc > $out/v$s.jsonl 2> $out/v$s.log
  echo "v$s rc=$? $(uptime | sed 's/.*load/load/')" >> $out/progress.txt
done
