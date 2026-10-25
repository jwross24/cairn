#!/bin/sh
# libpydesc.dylib: GMP linked statically from Homebrew. -DCHECK builds the self-verifying variant used by the tests.
set -e
cd "$(dirname "$0")"
OUT=${1:-libpydesc.dylib}
EXTRA=${2:-}
cc -O3 $EXTRA -Wall -Wextra -Wno-unused -Wno-unused-parameter -dynamiclib -I/opt/homebrew/include -o "$OUT" pydesc.c /opt/homebrew/lib/libgmp.a
