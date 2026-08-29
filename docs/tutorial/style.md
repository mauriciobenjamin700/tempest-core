# 2. Estilo

O estilo é **inline e tipado** — sem folhas de estilo, sem cascata, sem
especificidade. Um `Style` é um objeto Pydantic que cada renderizador traduz para
o seu alvo (CSS no web, propriedades Qt/Compose no nativo).

```python
from tempest_core import Container, Style, Text, Widget
from tempest_core import Color, Edge


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

## Todo número é finito

Um campo numérico de `Style` — e de qualquer widget — recusa `nan`, `inf` e
`-inf`:

```python
from tempest_core import Style

Style(width=float("nan"))
# ValidationError: width — Input should be a finite number
```

Parece severo para um valor que ninguém digita de propósito. Mas ninguém digita:
ele **chega**, de dado de fora.

```python
metricas = await backend.get("/metrics")  # {"carga_pct": "NaN"}
Style(width=float(metricas["carga_pct"]))  # float("NaN") == nan
```

Uma divisão por zero, um sensor sem leitura, um campo que o backend serializou
como a string `"NaN"` — e o `nan` entra na árvore sem nenhum sinal.

!!! danger "Por que isso não pode passar"
    `nan` e `inf` **não têm token em JSON**, e todo renderizador que este core
    alimenta é alcançado por JSON. O encoder do Python escreve as palavras cruas
    `NaN`/`Infinity`, e nenhum `JSON.parse` de browser aceita.

    O estrago não é a propriedade errada: é o **lote inteiro** que a carrega. Um
    `nan` num `width` derruba o batch de patches que ia junto — inclusive as
    mudanças de widgets que não têm nada a ver com ele.

    Foi medido na issue #160 do tempestweb: uma métrica que chegou como `"NaN"`
    matou o lote dentro da decodificação do cliente — antes do transporte, antes
    do renderizador, antes de qualquer diagnóstico —, e o erro visível apareceu
    **um rebuild depois**, como `patch path out of range`, num app bar cuja
    segunda ação simplesmente nunca tinha sido entregue. Em 3 de 7 reproduções
    não houve **nenhuma** linha de console.

!!! tip "Limite não substitui finitude"
    `Style.opacity` (`ge=0.0, le=1.0`) já recusava `inf` — mas só porque
    `inf <= 1.0` é falso. Um limite de um lado só não segura: `text_scale` e
    `aspect_ratio` têm `gt=0.0`, e `inf > 0.0` é verdadeiro. Por isso a guarda é
    de **finitude**, não de faixa.

Recusar na construção é o ponto: o `ValidationError` nomeia o campo na linha que
montou o widget. Valide onde o número entra:

```python
import math

from tempest_core import Style


def largura_da_barra(bruto: str) -> Style:
    """Converte o número do backend, caindo para 0 quando não é finito."""
    carga = float(bruto)
    return Style(width=carga if math.isfinite(carga) else 0.0)


print(largura_da_barra("42.5").width)  # 42.5
print(largura_da_barra("NaN").width)  # 0.0
```

## Animação implícita

Declare uma `Transition` e a mudança de propriedades é animada em vez de saltar:

```python
from tempest_core import Curve, Transition

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
- Todo número é finito: `nan`/`inf` são recusados na construção, porque JSON
  não os representa e um só deles derruba o lote de patches inteiro.
- Veja a [referência da API](../reference.md) para tudo.
