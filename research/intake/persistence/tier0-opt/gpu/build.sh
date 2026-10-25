#!/bin/zsh
set -e
cd "$(dirname "$0")"
{ echo 'static const char SHADER_SRC[] ='; sed 's/\\/\\\\/g; s/"/\\"/g; s/^/"/; s/$/\\n"/' lvl12_gpu.metal; echo ';'; } > shader_src.h
clang -O2 -fobjc-arc -Wall -Wno-unused-function -framework Foundation -framework Metal -o "${OUT:-lvl12_gpu}" lvl12_gpu.m
