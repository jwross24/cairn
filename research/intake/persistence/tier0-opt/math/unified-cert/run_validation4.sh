#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert
./rt.sh tests/mutants.py > logs/mutants2.out 2>&1
nice -n 10 uv run --no-project --with mpmath --with sympy python -I -u ../../cport/tools/mk_utable_u2.py --probe 31,0 > logs/u2-probe-31.out 2>&1
./rt.sh unified.py run --backend dual --out logs/u2-dual-r2.jsonl --min --verify > logs/u2-dual-r2.stdout 2>&1
./rt.sh unified.py run --backend dual --out logs/uprime-dual-v2.jsonl --utable inputs/utable_uprime.txt --verify --maxk 9 --maxD 3 > logs/uprime-dual-v2.stdout 2>&1
echo finished > logs/run_validation4.done
