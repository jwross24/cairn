#!/bin/zsh
# usage: build_and_test.sh <label>
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt
PY=/Users/jwross/Documents/cairn/research/intake/persistence/tier0/.venv/bin/python3
cc -O3 -march=native -o lvl12 lvl12.c > /private/tmp/persist-opt-scratch/cc.log 2>&1 || { echo "COMPILE FAILED"; grep error /private/tmp/persist-opt-scratch/cc.log; exit 1; }
nice -n 10 $PY c_oracle.py ./lvl12 chk_o/$1.jsonl || { echo "ORACLE RUN FAILED"; exit 1; }
cmp golden/c_oracle.jsonl chk_o/$1.jsonl && echo ORACLE_SAME || { echo ORACLE_DIFF; exit 1; }
uptime
nice -n 10 $PY bench.py ./lvl12 5 $1
