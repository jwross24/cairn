#!/bin/zsh
tag=$1
PY=/Users/jwross/Documents/cairn/research/intake/persistence/tier0/.venv/bin/python3
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt
./golden_run.sh chk_$tag 4
nice -n 10 $PY eq_golden.py chk_$tag/eq6.jsonl 4 2> chk_$tag/eq6.log
$PY normalize.py chk_$tag chk_${tag}_n
rc=0
for f in golden/*.jsonl; do b=$(basename $f); if [ $b = c_oracle.jsonl ]; then continue; fi; if cmp -s $f chk_${tag}_n/$b; then echo "SAME $b"; else echo "DIFF $b"; rc=1; fi; done
nice -n 10 $PY c_oracle.py ./lvl12 chk_${tag}_n/c_oracle.jsonl
if cmp -s golden/c_oracle.jsonl chk_${tag}_n/c_oracle.jsonl; then echo "SAME c_oracle.jsonl"; else echo "DIFF c_oracle.jsonl"; rc=1; fi
echo "rc=$rc"
