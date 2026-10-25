#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/breakthrough/n3-joint-search
: > proto2_out.jsonl
for s in 224 216 144 1176 784 1372; do
  nice -n 10 uv run --with mpmath --with gmpy2 python proto2.py $s 3 3 40 >> proto2_out.jsonl 2>&1
done
for s in 11664 18144; do
  nice -n 10 uv run --with mpmath --with gmpy2 python proto2.py $s 4 4 40 >> proto2_out.jsonl 2>&1
done
