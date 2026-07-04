# Instalação

```bash
pip install tempest-core
```

Requer Python `>=3.11`. A única dependência dura é o `pydantic>=2`.

!!! note "Quem usa o tempest-core"
    Você raramente instala o `tempest-core` sozinho — ele vem como dependência do
    **tempestweb** (web) ou do **tempestroid** (nativo). Mas o core é autônomo:
    dá pra construir e diffar árvores sem nenhum renderizador.

## Verificar

```bash
python -c "from tempest_core import App, Column, Text, build, diff; print('OK')"
```

## Desenvolvimento

```bash
uv sync --extra dev
ruff check . && ruff format --check .
mypy tempest_core && pyright tempest_core
pytest -q
```

## Recapitulando

- `pip install tempest-core` — Python 3.11+, só precisa de pydantic.
- Importe tudo do nível de topo: `from tempest_core import …`.
