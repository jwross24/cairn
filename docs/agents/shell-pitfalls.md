Read this before writing a shell one-liner whose exit code is the evidence, or when a command's output comes back empty.

# Shell pitfalls

- zsh does not word-split an unquoted variable. `P="--db X --pin Y"; cmd $P` passes one argument, and the command fails in a way that reads as a defect in the code.
- `cmd | tail -1` reports `tail`'s status. Capture `${PIPESTATUS[1]}` or redirect to a file instead of piping when the exit code is the evidence.
- Nesting `uv run` inside `$(...)` under an outer `uv run` pipeline yields empty output. Capture to a file and parse it in a second command.
- A verdict that must be read goes to a file (`cmd > "$out" 2>&1; tail -1 "$out"`). Byte-equality is settled in Python with lengths and a `hashlib.sha256` digest.
