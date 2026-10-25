#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert
./rt.sh tests/mutants.py > logs/mutants.out 2>&1
./rt.sh tests/test_ucert.py > logs/tests.out 2>&1
./rt.sh unified.py planted --out logs/planted-genuine.jsonl --seed 21 --genuine 10 > logs/planted-genuine.stdout 2>&1
echo finished > logs/run_validation3.done
