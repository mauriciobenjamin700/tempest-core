# 2. Estilo

O estilo é **inline e tipado** — sem folhas de estilo, sem cascata, sem
especificidade. Um `Style` é um objeto Pydantic que cada renderizador traduz para
o seu alvo (CSS no web, propriedades Qt/Compose no nativo).

```python
from tempest_core import Container, Style, Text, Widget
from tempest_core.style import Color, Edge


def cartao() -> Widget:
    return Container(
        key="cartao",
        style=Style(
            padding=Edge.all(16),  # (1)!
            gap=8.0,
            background=Color.from_hex("#f5f5f5"),  # (2)!
            radius=12.0,
        ),
        children=[Text(content="Num cartão", key="t")],
    )
```

1. `Edge.all(16)` = 16px nos quatro lados. Há também `Edge.symmetric(vertical=…,
   horizontal=…)` e `Edge(top=…, right=…, …)`.
2. `Color.from_hex("#f5f5f5")` → `Color(r, g, b, a)`. No web isso vira
   `rgba(...)`; o valor cruza a fronteira como `{r, g, b, a}`.

## Animação implícita

Declare uma `Transition` e a mudança de propriedades é animada em vez de saltar:

```python
from tempest_core.style import Curve, Transition

Style(transition=Transition(duration_ms=300, curve=Curve.EASE_IN_OUT))
```

!!! tip "Tema = valores de Style"
    Não há motor de tema mágico: um tema é só um conjunto de `Color`/`Style` que a
    sua `view` aplica. Trocar de tema é a view produzindo Styles diferentes.

## Escape hatch de HTML (`tag` / `attrs`)

Todo `Widget` carrega dois campos opcionais de "dica de renderizador" — `tag` e
`attrs` — para o renderizador HTML/SSR (`tempestweb`). Eles são ignorados pelos
renderizadores nativos (Qt/Compose), assim como `semantics`/`focusable` já são.

```python
from tempest_core import Container, Text, Widget


def barra_de_navegacao() -> Widget:
    return Container(
        key="nav",
        tag="nav",  # (1)!
        attrs={"id": "topo", "aria-label": "Principal"},  # (2)!
        children=[
            Text(
                content="Início",
                tag="a",
                attrs={"href": "/", "hx-get": "/", "hx-target": "#main"},  # (3)!
            ),
        ],
    )
```

1. `tag` sobrescreve o elemento HTML semântico emitido (`<nav>` em vez do
   `<div>` padrão); `None` deixa o renderizador escolher o elemento natural.
2. `attrs` é um `dict[str, str]` de atributos HTML arbitrários (`id`, `class`,
   `data-*`, `aria-*`).
3. É por aqui que atributos HTMX (`hx-*`) entram na saída SSR sem precisar de um
   campo dedicado no core.

!!! info "Por que um escape hatch tipado"
    O core é agnóstico de renderizador; ele não modela toda tag/atributo HTML.
    `tag`/`attrs` fluem pelo `build()` para as `props` do nó (como qualquer outro
    campo), então o renderizador HTML os consome e os demais os ignoram — sem
    caso especial.

## Recapitulando

- `Style` é tipado e inline; sem cascata CSS.
- `Color.from_hex`, `Edge.all/symmetric`, `Transition` cobrem o dia a dia.
- Cada renderizador traduz o mesmo `Style` para o seu alvo.
- Veja a [referência da API](../reference.md) para tudo.
