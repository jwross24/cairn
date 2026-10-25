#!/bin/zsh
# usage: runq.sh s M sv
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/kt-audit
tag="$1_${2//,/}"
PYTHONDONTWRITEBYTECODE=1 uv run --no-project --with sympy --with gmpy2 python -I run_audit.py $1 $2 1 > audit_${tag}.log 2>&1
