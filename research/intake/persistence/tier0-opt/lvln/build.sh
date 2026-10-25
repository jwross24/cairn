#!/bin/bash
# PGO build of lvlN.c. Training inputs: train/ (level 24, 48, 96 lifts). Profile: lvlN.profdata.
# "build.sh retrain" regenerates the profile first.
set -e
H=$(cd "$(dirname "$0")" && pwd)
L=/opt/homebrew/opt/llvm/bin
cd "$H"
if [ "$1" = "retrain" ]; then
  $L/clang -O3 -march=native -fprofile-instr-generate -o /private/tmp/lvlN_gen lvlN.c
  P=$(mktemp -d /private/tmp/lvlN_prof.XXXX)
  LLVM_PROFILE_FILE=$P/a%p.profraw /private/tmp/lvlN_gen train/cfgL24.txt train/parents24_400.txt > /dev/null 2>&1
  LLVM_PROFILE_FILE=$P/b%p.profraw /private/tmp/lvlN_gen train/cfgL48.txt train/parents48.txt > /dev/null 2>&1
  LLVM_PROFILE_FILE=$P/c%p.profraw /private/tmp/lvlN_gen train/cfgL96.txt train/parents96.txt > /dev/null 2>&1
  $L/llvm-profdata merge -o lvlN.profdata $P/*.profraw
fi
$L/clang -O3 -march=native -fprofile-instr-use=lvlN.profdata -o lvlN lvlN.c
