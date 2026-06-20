# 4. Design system (variantes → Material 3)

O `tempest-core` traz um **design system** com **ergonomia de API do Chakra**
(`variant` / `size` / `color_scheme`) ancorado em **Material 3**. Em vez de
escrever cores e espaçamentos à mão, você descreve a *intenção* e um **resolver
puro** produz o `Style` concreto a partir dos tokens do `Theme`. 🚀

## Botões, campos, seleção, slider

Os resolvers interativos vivem em `variants.py` e cada um resolve um `Style`:

```python
from tempest_core import IconButton, Theme
from tempest_core.widgets import Input
from tempest_core.style import FieldVariant

field = Input(value="", field_variant=FieldVariant.FILLED, color_scheme="primary")
button = IconButton(icon="settings", color_scheme="primary", label="Abrir ajustes")
```

!!! info "Estados (hover/press/disabled/focus)"
    Os resolvers interativos têm um irmão `*_states` que devolve a tabela por
    estado, que os renderizadores aplicam em eventos reais de ponteiro/foco.

## Superfícies e layout (H3)

A camada de **superfícies** é não interativa, então **não tem tabela de
estados**: ela só escolhe como a caixa é preenchida e se projeta uma sombra de
elevação.

```python
from tempest_core import CardVariant
from tempest_core.components import Card, HStack, Surface, VStack
from tempest_core.widgets import Spacer, Text

card = Card(                                  # (1)!
    variant=CardVariant.OUTLINED,
    color_scheme="primary",                   # (2)!
    children=[
        HStack(gap="md", children=[           # (3)!
            Text(content="Título"),
            Spacer(),                         # (4)!
            Text(content="42"),
        ]),
    ],
)
```

1. `Card` = `Surface` + padding + `Column`. As três variantes são `ELEVATED`
   (fundo de superfície + sombra), `FILLED` (preenchimento tonal, sem sombra) e
   `OUTLINED` (borda fina, sem sombra).
2. `color_scheme="neutral"` usa os papéis de superfície; um papel (`"primary"`, …)
   tinge com os papéis tonais `*_container` / `on_*_container`.
3. `gap="md"` é um **passo de token** resolvido pela escala de espaçamento do
   tema; um `float` cru também é aceito (compatibilidade).
4. `Spacer()` é um espaçador flexível (`grow=1.0`) que empurra os vizinhos para as
   pontas.

!!! tip "Elevação é uma `Shadow`, não um campo novo"
    A elevação Material 3 é realizada como uma `Shadow` mapeada do nível
    (`elevation=0..5`) — **nenhum campo novo de `Style`** foi adicionado. Por isso
    `len(Style.model_fields)` permanece o mesmo.

## Recapitulando

- `variant` / `size` / `color_scheme` descrevem a intenção; o resolver puro produz
  o `Style`.
- Superfícies (`Card` / `Surface` / `resolve_surface_variant`) são não
  interativas: elevação, preenchimento tonal ou borda.
- `HStack` / `VStack` aceitam `gap` por passo de token; `Spacer` é um flex.
- Um `style=` explícito sempre é mesclado por cima.
