#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport
date +%s > ../final13/control_start.epoch
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py --vertices 2667168,1843968,368947264 --utable-file data/utable_u2.txt --out /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/control --jobs 1 --pattern-timeout 3600
date +%s > ../final13/control_end.epoch
