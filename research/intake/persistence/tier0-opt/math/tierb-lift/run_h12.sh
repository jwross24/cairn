#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/tierb-lift
export PYTHONDONTWRITEBYTECODE=1
R="nice -n 10 uv run --no-project --with sympy --with gmpy2 python h12_measure.py"
timeout 1380 sh -c '
$0 14336 logs/h12_14336.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 0 4e8 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
$0 28672 logs/h12_28672.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 0 4e8 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
$0 124416 logs/h12_124416.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12 0 4e8 2 /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/h12/dump
' "$R"
