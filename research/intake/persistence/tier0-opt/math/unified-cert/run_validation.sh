#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert
./rt.sh unified.py run --backend cvp --out logs/u2-cvp-r2.jsonl --min --verify > logs/u2-cvp-r2.stdout 2>&1
./rt.sh unified.py run --backend cvp --out logs/uprime-cvp-r2.jsonl --utable inputs/utable_uprime.txt --min --minmaxD 3 --verify --maxk 9 --maxD 5 > logs/uprime-cvp-r2.stdout 2>&1
./rt.sh unified.py run --backend dual --out logs/uprime-dual.jsonl --utable inputs/utable_uprime.txt --min --minmaxD 3 --verify --maxk 9 --maxD 5 > logs/uprime-dual.stdout 2>&1
echo finished > logs/run_validation.done
