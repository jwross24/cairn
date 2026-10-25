#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport
T=/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/t2-final
date +%s > $T/d1_start.epoch
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py --sources /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/t2-cap/trees_t2cap.jsonl --vertices 9633792,116169984 --utable-file data/utable_u2.txt --out $T/d1 --jobs 2 --pattern-timeout 3600 --deadline-epoch 1
date +%s > $T/d1_end.epoch
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py --vertices 2667168,1843968,368947264 --utable-file data/utable_u2.txt --out $T/control --jobs 1 --pattern-timeout 3600
date +%s > $T/control_end.epoch
