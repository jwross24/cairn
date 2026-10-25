#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/r1-branch-split/engine
R="nice -n 10 uv run --no-project --with sympy --with gmpy2 python bsrun.py"
BRANCHSPLIT=off $R 14336 ../logs/v14336_off.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w14336off 1e30 2
BRANCHSPLIT=on $R 8192 ../logs/v8192_on.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w8192on 1e30 2
BRANCHSPLIT=on $R 28672 ../logs/v28672_on.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w28672on 1e30 2
