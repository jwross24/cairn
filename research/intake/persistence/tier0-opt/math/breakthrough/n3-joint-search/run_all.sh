#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/breakthrough/n3-joint-search
: > proto_out.jsonl
: > proto2_out.jsonl
run() { nice -n 10 uv run --with mpmath --with gmpy2 python "$@" ; }
run proto2.py 1372 3 3 30 >> proto2_out.jsonl 2>&1
run proto2.py 784 3 3 30 >> proto2_out.jsonl 2>&1
run proto2.py 224 3 3 30 >> proto2_out.jsonl 2>&1
NEG=1 run proto.py 224 3 3 30 > proto_neg.jsonl 2>&1
run proto.py 1372 4 4 30 >> proto_out.jsonl 2>&1
run proto.py 784 4 4 30 >> proto_out.jsonl 2>&1
run proto.py 224 4 4 30 >> proto_out.jsonl 2>&1
run proto2.py 1176 3 3 30 >> proto2_out.jsonl 2>&1
run proto2.py 216 3 3 30 >> proto2_out.jsonl 2>&1
run proto2.py 144 3 3 30 >> proto2_out.jsonl 2>&1
