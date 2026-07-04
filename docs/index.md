# tempest-core

**O core de UI agnóstico de renderizador** — o motor por trás do
[tempestroid](https://github.com/mauriciobenjamin700/tempestroid) (renderizadores
nativos: Qt / Compose / Android) e do tempestweb (DOM, modos WASM + servidor). 🌩️

Uma árvore, muitos renderizadores. Você descreve a UI como **Python tipado** e o
core produz uma árvore imutável (a IR) e calcula o **diff** entre duas árvores —
os renderizadores só aplicam os patches.

```python
from tempest_core import Column, Text, build, diff

antiga = build(Column(children=[Text(content="Contagem: 0", key="label")]))
nova = build(Column(children=[Text(content="Contagem: 1", key="label")]))

diff(antiga, nova)
# -> [Update(set_props={"content": "Contagem: 1"})]
```

## O que tem dentro

| Camada | O que faz |
|---|---|
| **IR + reconciliador** | `build` / `diff` (e `build_scene` / `diff_scene` para overlays), o modelo `Node` / `Patch`, e o `App` com loop de rebuild coalescido |
| **Estilo tipado** | `Style`, `Color`, `Edge`, gradientes, sombras, bordas, transições — sem cascata CSS, inline e tipado |
| **Widgets & componentes** | layout (Column/Row/Container/Stack), texto, botão, inputs, checkbox, listas (LazyColumn/Row/Grid), overlays, gestos, mídia, + componentes compostos (cards, forms, campos, tabelas, inputs BR…) |
| **Design system** | ergonomia Chakra (`variant`/`size`/`color_scheme`) → `Style` Material 3 via resolvers puros (`variants.py`): botões/campos/seleção, superfícies, feedback (`success`/`warning`/`info`), navegação e kit de pesquisa/ciência de dados |
| **Transversais** | animação, i18n, navegação (`Route`/`NavStack`), tema, validadores (CPF/CNPJ/email/telefone), ícones |

!!! tip "Sem código acoplado a plataforma"
    Nada de Qt, JNI, Android ou DOM aqui — o core importa limpo sob CPython,
    Pyodide e um servidor headless. Única dependência dura: `pydantic>=2`.

## Próximos passos

- [Instalação](installation.md) — `pip install tempest-core`.
- [Tutorial](tutorial/index.md) — construa e diffe sua primeira árvore.
- [Referência da API](reference.md) — os símbolos públicos.
