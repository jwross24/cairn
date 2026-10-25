#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/cport
date +%s > ../final13/d1_start.epoch
nice -n 10 uv run --no-project --with sympy --with gmpy2 --with mpmath python tools/final_stage.py --vertices 331776,11239424,3779136,2939328,69441624,3281116734,1161216,7112448,13226976,46294416,1741824,1492992,9483264 --utable-file data/utable_u2.txt --out /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/final13/d1 --jobs 2 --pattern-timeout 3600 --deadline-epoch 1
date +%s > ../final13/d1_end.epoch
