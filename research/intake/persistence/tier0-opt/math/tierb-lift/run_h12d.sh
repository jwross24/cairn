#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/tierb-lift
export PYTHONDONTWRITEBYTECODE=1
R="nice -n 10 uv run --no-project --with sympy --with gmpy2 python h12_measure.py"
timeout 2400 $R 9437184 logs/h12_9437184.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 7.7e9 1.6e11 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
timeout 1500 $R 9633792 logs/h12_9633792.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 1e9 2e11 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
timeout 1500 $R 11239424 logs/h12_11239424.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 1e9 1.5e11 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
timeout 1200 $R 3211264 logs/h12_3211264.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 1.1e10 2e11 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
