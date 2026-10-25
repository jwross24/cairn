#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert
./rt.sh unified.py run --backend cvp --out logs/uprime-cvp-k10.jsonl --utable inputs/utable_uprime.txt --min --verify --mink 10 --maxD 5 > logs/uprime-cvp-k10.stdout 2>&1
./rt.sh unified.py run --backend dual --out logs/uprime-dual-k10.jsonl --utable inputs/utable_uprime.txt --min --minmaxD 3 --verify --mink 10 --maxD 5 > logs/uprime-dual-k10.stdout 2>&1
echo finished > logs/run_validation2.done
