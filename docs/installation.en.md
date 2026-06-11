# Installation

```bash
pip install tempest-core
```

Requires Python `>=3.11`. The only hard dependency is `pydantic>=2`.

!!! note "Who uses tempest-core"
    You rarely install `tempest-core` on its own — it comes as a dependency of
    **tempestweb** (web) or **tempestroid** (native). But the core is standalone:
    you can build and diff trees with no renderer at all.

## Verify

```bash
python -c "from tempest_core import App, Column, Text, build, diff; print('OK')"
```

## Develop

```bash
uv sync --extra dev
ruff check . && ruff format --check .
pyright tempest_core
pytest -q
```

## Recap

- `pip install tempest-core` — Python 3.11+, only needs pydantic.
- Import everything from the top level: `from tempest_core import …`.
