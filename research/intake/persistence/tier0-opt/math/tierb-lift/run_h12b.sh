#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/tierb-lift
export PYTHONDONTWRITEBYTECODE=1
R="nice -n 10 uv run --no-project --with sympy --with gmpy2 python h12_measure.py"
for v in 124416 14336 28672; do
  timeout 400 $R $v logs/h12_$v.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 4e8 5e11 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
done
