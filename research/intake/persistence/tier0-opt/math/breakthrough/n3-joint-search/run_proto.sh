#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/breakthrough/n3-joint-search
: > proto_out.jsonl
for s in 224 216 144 1176 784 1372 2744; do
  nice -n 10 uv run --with mpmath --with gmpy2 python proto.py $s 4 4 40 >> proto_out.jsonl 2>&1
done
NEG=1 nice -n 10 uv run --with mpmath --with gmpy2 python proto.py 224 4 4 40 > proto_neg.jsonl 2>&1
