#!/bin/sh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/r1-branch-split/engine
for s in 14336 8192 10800; do
BRANCHSPLIT_AUDIT=$PWD/../logs/auditfull_$s.jsonl BRANCHSPLIT_AUDIT_STRIDE=1 BRANCHSPLIT_AUDIT_CAP=2000000 BRANCHSPLIT=on nice -n 10 uv run --no-project --with sympy --with gmpy2 python bsrun.py $s ../logs/v${s}_auditfull.jsonl /private/tmp/claude-501/-Users-jwross-Documents-cairn/ec9f8f52-ce29-4a5c-9caf-2ecbd434509f/scratchpad/wauditfull_$s 1e30 2 > /dev/null 2>&1
nice -n 10 uv run --no-project --with sympy --with gmpy2 python bsaudit.py ../logs/auditfull_$s.jsonl > ../logs/auditfull_$s.result 2>&1
done
