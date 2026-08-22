# Tutorial — build & diff

O coração do tempest-core são duas funções: **`build`** transforma um widget numa
árvore imutável (a IR), e **`diff`** compara duas árvores e devolve a lista mínima
de **patches**. Um renderizador aplica esses patches; o core nunca toca em pixels.

## Construir uma árvore

```python
from tempest_core import Column, Text, build

árvore = build(
    Column(
        children=[
            Text(content="Olá", key="saudacao"),  # (1)!
        ],
    )
)
print(árvore.type)  # "Column"
print(árvore.children[0].props["content"])  # "Olá"
```

1. `key` é a identidade estável do nó — é por ela que o diff casa nós entre
   rebuilds. Dê `key` a tudo que pode mudar de posição ou conteúdo.

`build` devolve um `Node` imutável: `{type, key, props, children}`.

## Diffar duas árvores

```python
from tempest_core import Column, Text, build, diff

a = build(Column(children=[Text(content="Olá", key="s")]))
b = build(Column(children=[Text(content="Tchau", key="s")]))

patches = diff(a, b)
print(patches[0].model_dump(mode="json"))
# {"path": [0], "set_props": {"content": "Tchau"}, "unset_props": []}
```

O diff é **keyed e mínimo**: só o que mudou vira patch. Os cinco tipos são
`Update`, `Insert`, `Remove`, `Reorder` e `Replace`.

!!! info "Por que isso importa"
    O renderizador recebe só o delta — não reconstrói a tela inteira. É o mesmo
    modelo do React, mas a árvore é Python tipado, sem JSX.

## Recapitulando

- `build(widget) -> Node` — a árvore imutável.
- `diff(antiga, nova) -> list[Patch]` — o delta mínimo, keyed.
- Dê `key` aos nós para o diff casar corretamente.
- Próximo: [estado e rebuilds](state.md).
