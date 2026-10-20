Read this before adding or changing a dependency, the Python pin or the package index in `pyproject.toml`.

# Toolchain detail

- `requires-python = ">=3.14"` in `pyproject.toml`, mirrored in `[tool.ty.environment]`; change the pin there, nowhere else.
- The same file pins the PyPI index (`[[tool.uv.index]]`, `default = true`) because `~/.config/uv/uv.toml` points at a corporate Artifactory that times out off-network.
- Runtime dependencies: `blake3` (content addressing), `claude-agent-sdk` (agent execution), `cypari2` (PARI arithmetic), `gmpy2` (independent integer arithmetic).
- Dev group: `pytest`, `pytest-timeout`, `hypothesis`, `ruff`, `ty`, `codespell`.
