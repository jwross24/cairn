#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/r1-branch-split/engine
R="nice -n 10 uv run --no-project --with sympy --with gmpy2 python bsrun.py"
BRANCHSPLIT=off $R 72 ../logs/v72_off.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w72off 1e30 2
BRANCHSPLIT=off $R 224 ../logs/v224_off.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w224off 1e30 2
BRANCHSPLIT=on $R 224 ../logs/v224_on.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w224on 1e30 2
BRANCHSPLIT=on $R 14336 ../logs/v14336_on.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w14336on 1e30 2
BRANCHSPLIT=on $R 10800 ../logs/v10800_on.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w10800on 1e30 2
BRANCHSPLIT=off $R 10800 ../logs/v10800_off.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/w10800off 1e30 2
