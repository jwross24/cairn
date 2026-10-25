#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/breakthrough/n3-joint-search
: > proto_neg2.jsonl
NEG=1 NEGD=2 nice -n 10 uv run --with mpmath --with gmpy2 python proto2.py 224 3 3 30 >> proto_neg2.jsonl 2>&1
NEG=1 NEGD=2 nice -n 10 uv run --with mpmath --with gmpy2 python proto2.py 784 3 3 30 >> proto_neg2.jsonl 2>&1
