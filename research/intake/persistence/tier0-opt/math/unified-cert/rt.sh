#!/bin/zsh
cd /Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/unified-cert
export PYTHONDONTWRITEBYTECODE=1
exec nice -n 10 uv run --no-project --with gmpy2 --with fpylll --with cysignals --with sympy python -I -u "$@"
