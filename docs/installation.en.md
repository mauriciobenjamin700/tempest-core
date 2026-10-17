# Installation

```bash
pip install tempest-core
```

Requires Python `>=3.11`. The only hard dependency is `pydantic>=2`.

!!! note "Who uses tempest-core"
    You rarely install `tempest-core` on its own — it comes as a dependency of
    **tempestweb** (web) or **tempestroid** (native). But the core is standalone:
    you can build and diff trees with no renderer at all.

??? info "Technical details: importing is cheap because models are built on demand"
    Every widget is a Pydantic model, and building a model's validator and
    serializer costs time. The core has about 260 models and most apps use a
    fraction of them — so the shared base declares `defer_build=True`: each class
    is built on **first use** (construction, `model_validate`, `model_dump`,
    `model_json_schema`), once, rather than at `import`.

    Measured on the tempest-webtunnel dashboard: `import tempest_core` dropped
    about 37% in CPU time on CPython and about 25% under Pyodide, which is where a
    web app's boot spends most of its Python side. The cost does not vanish, it
    moves: the first render pays for building the classes it actually uses.

    Nothing observable changes — validation, serialization, JSON schema,
    `frozen`, `extra="forbid"` and the `nan`/`inf` refusal behave as before.

## Verify

```bash
python -c "from tempest_core import App, Column, Text, build, diff; print('OK')"
```

## Develop

```bash
uv sync --extra dev
ruff check . && ruff format --check .
mypy tempest_core && pyright tempest_core
pytest -q
```

## Recap

- `pip install tempest-core` — Python 3.11+, only needs pydantic.
- Import everything from the top level: `from tempest_core import …`.
