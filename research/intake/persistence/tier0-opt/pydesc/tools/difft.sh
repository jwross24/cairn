#!/bin/zsh
# difft.sh <srcdir> <vertex> <known> <logfile>
cd "$1" || exit 9
S=$(date +%s)
PATH=/private/tmp/persist-pydesc/shim:$PATH nice -n 10 python3 difftest.py "$2" "$3" > "$4" 2>&1
echo "rc=$? secs=$(( $(date +%s) - S ))" >> "$4"
