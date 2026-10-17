# Instalação

```bash
pip install tempest-core
```

Requer Python `>=3.11`. A única dependência dura é o `pydantic>=2`.

!!! note "Quem usa o tempest-core"
    Você raramente instala o `tempest-core` sozinho — ele vem como dependência do
    **tempestweb** (web) ou do **tempestroid** (nativo). Mas o core é autônomo:
    dá pra construir e diffar árvores sem nenhum renderizador.

??? info "Detalhes técnicos: o import é barato porque os modelos são construídos sob demanda"
    Todo widget é um modelo Pydantic, e construir o validador e o serializador de
    um modelo custa. O core tem perto de 260 modelos, e a maioria dos apps usa uma
    fração deles — por isso a base comum declara `defer_build=True`: cada classe é
    construída no **primeiro uso** (construção, `model_validate`, `model_dump`,
    `model_json_schema`), uma vez só, e não no `import`.

    Medido no painel do tempest-webtunnel: `import tempest_core` caiu cerca de
    37% em tempo de CPU no CPython e cerca de 25% no Pyodide, que é onde o boot de
    um app web passa a maior parte do lado Python. O custo não some, muda de lugar:
    a primeira renderização paga a construção das classes que ela de fato usa.

    Nada observável muda — validação, serialização, JSON schema, `frozen`,
    `extra="forbid"` e a recusa de `nan`/`inf` se comportam como antes.

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
