# Superfícies & cards

As **superfícies** são as caixas temáticas sobre as quais todo o resto do
`tempest-core` se apoia. No fundo há uma única primitiva — a **`Surface`** — e
tudo mais (`Card`, `Sidebar`, painéis) é ela mais um pouco de padding e um
arranjo de filhos. Todas resolvem seu `Style` da API de variantes **Chakra**
(`variant` / `color_scheme` / `elevation`) ancorada em **Material 3**: você
descreve a *intenção* de superfície e o **resolver puro**
`resolve_surface_variant` assa o `Style` concreto a partir dos tokens do
`Theme`. 🚀

!!! info "O que você aprende aqui"
    - A **primitiva `Surface`** (sem padding) e como o `Card` é só ela + padding + `Column`.
    - As três **variantes** `CardVariant` (`ELEVATED` / `FILLED` / `OUTLINED`) e para qual tratamento M3 cada uma abaixa.
    - Por que a **elevação é uma `Shadow`** mapeada do nível M3, nunca um campo de `Style` novo.
    - Os **itens de conteúdo** (`ListTile`, `Avatar`, `Divider`) e como eles leem cor e espaçamento do tema.
    - Os componentes de **layout** (`Grid`, `HStack`, `VStack`, `Scaffold`, `Sidebar`) e o `gap` por **passo de token**.
    - Os **helpers de composição**: `merge_style` e os tokens de paleta padrão.

## Superfícies

A superfície é a caixa temática crua. `Surface` não tem padding próprio;
`StyledContainer` adiciona um padding por passo de token sobre a `Container`
primitiva.

### `Surface`

A primitiva de superfície **sem padding**: uma caixa de um filho só que carrega o
`Style` resolvido da variante, sem padding ou gap interno. É o que toda
superfície de nível mais alto (`Card`, cabeçalho de `Accordion`, …) constrói por
cima.

```python
from tempest_core.components import Surface
from tempest_core.widgets import Text

superficie = Surface(child=Text(content="Olá"))
```

Esse `Surface(child=…)` já é uma superfície **elevada, neutra** — pronta para os
renderizadores. Escolha a variante e a família de cor pela *intenção*:

```python
from tempest_core.components import Surface
from tempest_core.style import CardVariant
from tempest_core.widgets import Text

painel = Surface(
    variant=CardVariant.OUTLINED,   # (1)!
    color_scheme="primary",         # tonal *_container
    elevation=0,                    # nível M3 explícito
    child=Text(content="Painel"),
)
```

1. `variant` também aceita a string equivalente (`"outlined"`); o enum
   `CardVariant` deixa a intenção explícita.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 (`"neutral"` usa as roles de superfície planas; uma família usa as roles tonais `*_container`). |
| `elevation` | `int \| None` | `None` | Nível M3 explícito (0-5) que sobrepõe o padrão da variante. |
| `radius_step` | `str` | `"md"` | O passo da escala de forma para o raio dos cantos. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (aceito por paridade; não usado aqui). |

!!! note "`Surface` é a base sem padding; `Card` é `Surface` + padding + `Column`"
    Diferente do `Card`, a `Surface` **não adiciona padding nem gap interno** — ela
    é a superfície nua, deixando o layout do conteúdo para o que ela envolve. Ela
    resolve o `Style` da variante, mescla o `style` explícito do chamador por cima
    (os campos setados vencem) e abaixa para uma `Container` de um filho só.

### `StyledContainer`

Uma caixa de um filho só com **padding por passo de token** sobre a `Container`
primitiva. Dá ergonomia de design-system à primitiva sem mutá-la: o `padding`
aceita um nome de passo (`"md"` / `"lg"`) resolvido contra a escala de
espaçamento do tema, ou um `float` cru para retrocompatibilidade.

```python
from tempest_core.components import StyledContainer
from tempest_core.widgets import Text

caixa = StyledContainer(padding="lg", child=Text(content="Conteúdo folgado"))
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |
| `padding` | `float \| str` | `"md"` | O padding interno — um nome de passo de token (`"md"`) ou um `float` em pixels lógicos. |
| `theme` | `Theme` | `Theme()` | O tema cuja escala de espaçamento resolve o nome do passo. |

!!! tip "Passo de token ou float — os dois valem"
    Uma string (`"md"`) resolve via `Theme.space(...)`; um `float` cru
    (`padding=24.0`) passa direto. Um `style` explícito é mesclado por cima do
    padding resolvido.

## Cards & itens

Blocos de apresentação clássicos que abaixam para primitivas. Com os tokens do
design-system, cada um lê cor e espaçamento do `Theme` em vez de hexadecimais
fixos.

### `Card`

Uma superfície temática que agrupa uma pilha de filhos (card do Material 3). É
exatamente **`Surface` + padding + `Column`**: resolve o tratamento de
superfície de `variant` / `color_scheme` / `elevation`, adiciona seu próprio
padding e empilha os filhos numa `Column`.

```python
from tempest_core.components import Card
from tempest_core.widgets import Text

cartao = Card(children=[
    Text(content="Título"),
    Text(content="Corpo do card."),
])
```

Um `Card(children=…)` sem argumentos produz um card **elevado, neutro**. Escolha
a variante e ajuste os passos de espaçamento:

```python
from tempest_core.components import Card
from tempest_core.style import CardVariant
from tempest_core.widgets import Text

destaque = Card(
    variant=CardVariant.FILLED,
    color_scheme="primary",
    padding_step="lg",   # padding interno
    gap_step="md",       # espaço entre os filhos
    children=[Text(content="Plano Pro")],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os widgets empilhados verticalmente dentro do card. |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que o card se tinge. |
| `elevation` | `int \| None` | `None` | Nível M3 explícito (0-5) sobrepondo o padrão. |
| `padding_step` | `str` | `"md"` | O passo de espaçamento para o padding interno. |
| `radius_step` | `str` | `"md"` | O passo da escala de forma para o raio dos cantos. |
| `gap_step` | `str` | `"sm"` | O passo de espaçamento para o gap entre os filhos. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (aceito por paridade; não usado). |

!!! info "As três variantes de `CardVariant`"
    | `CardVariant` | Tratamento M3 | Fundo | Sombra | Borda |
    | --- | --- | --- | --- | --- |
    | `ELEVATED` | *elevated card* | `surface` | elevação nível 1 | — |
    | `FILLED` | *filled card* | `surface_variant` (tonal) | — | — |
    | `OUTLINED` | *outlined card* | `surface` | — | `outline` (1px) |

    O `color_scheme` decide *qual* família de cor pinta o tratamento: `"neutral"`
    usa as roles de superfície planas; uma família (`"primary"`, `"error"`, …) usa
    as roles tonais `*_container`.

!!! warning "Elevação é uma `Shadow`, não um campo de `Style` novo"
    Um nível de elevação M3 (0-5) é **mapeado para uma `Shadow`** (blur + deslocamento
    para baixo) via `_elevation_shadow` — nunca um campo `elevation` no `Style`. Por
    padrão `ELEVATED` sobe para o nível 1 e `FILLED`/`OUTLINED` ficam rentes (nível
    0); passar `elevation=` sobrepõe esse padrão. O renderizador traduz a `Shadow`
    resolvida para a elevação nativa (Compose `Modifier.shadow` / Qt
    `QGraphicsDropShadowEffect`).

### `ListTile`

Uma linha de lista: widgets `leading`/`trailing` opcionais em volta de um bloco
de título. O título usa `ON_SURFACE`, o subtítulo usa `ON_SURFACE_VARIANT`, e os
gaps/padding vêm da escala de espaçamento do tema.

```python
from tempest_core.components import Avatar, ListTile
from tempest_core import IconButton

linha = ListTile(
    title="Mauricio Benjamin",
    subtitle="mauricio@exemplo.com",
    leading=Avatar(initials="MB"),
    trailing=IconButton(icon="chevron_right", label="Abrir"),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | O texto primário da linha. |
| `subtitle` | `str \| None` | `None` | Uma segunda linha opcional, mostrada apagada sob o título. |
| `leading` | `Widget \| None` | `None` | Widget opcional antes do texto (ex.: um `Avatar`). |
| `trailing` | `Widget \| None` | `None` | Widget opcional depois do texto (ex.: um `Button`). |
| `color_scheme` | `str \| None` | `None` | Família M3 opcional que tinge o título; `None` mantém o `ON_SURFACE` neutro. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem cores e espaçamento. |

!!! note "`ListTile` é apresentacional — sem `on_click` de linha"
    Como o handling de toque só existe no `Button` no conjunto de primitivas, a
    linha não tem `on_click`. Coloque um `Button` (ou `IconButton`) no slot
    `trailing` para ações. O bloco de título cresce (`grow=1.0`) e empurra o
    `trailing` para a borda; a superfície de acessibilidade (`semantics`) é
    preservada na linha.

### `Avatar`

Um badge redondo mostrando iniciais curtas, tingido pelas roles de container. O
círculo se preenche com a role tonal `*_container` do `color_scheme` e as iniciais
usam a role `on_*_container` legível (segura para WCAG-AA por construção).

```python
from tempest_core.components import Avatar

avatar = Avatar(initials="MB", size=48.0, color_scheme="secondary")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `initials` | `str` | `""` | O texto curto dentro do círculo (ex.: `"MB"`). |
| `size` | `float` | `40.0` | O diâmetro do círculo em pixels lógicos. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que o círculo se tinge. |
| `theme` | `Theme` | `Theme()` | O tema que resolve as cores do círculo. |

!!! tip "O raio segue o tamanho"
    O `radius` é fixado em `size / 2.0` — sempre um círculo perfeito, seja qual for
    o `size`. As cores saem do par `(*_container, on_*_container)` do esquema; um
    esquema desconhecido cai no container primário.

### `Divider`

Uma régua horizontal fina, tingida com a cor `OUTLINE_VARIANT` do Material 3. O
`thickness` aceita um nome de passo de token (resolvido contra a escala de forma)
ou um `float` cru.

```python
from tempest_core.components import Divider

linha = Divider()                        # régua de 1px, outline-variant
grossa = Divider(thickness=2.0, color_scheme="primary")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `thickness` | `float \| str` | `1.0` | A altura da linha — um nome de passo de token (`"xs"`) ou um `float`. |
| `color_scheme` | `str \| None` | `None` | Família M3 opcional para a cor da régua; `None` usa o `OUTLINE_VARIANT` neutro. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem a cor e o passo. |

## Layout de componentes

Componentes de estrutura de página. Todos abaixam para árvores de `Column` /
`Row` / `Container` primitivas.

### `Grid`

Uma grade de colunas fixas dispondo os filhos em células de largura igual,
preenchidas da esquerda para a direita e de cima para baixo.

```python
from tempest_core.components import Card, Grid
from tempest_core.widgets import Text

grade = Grid(
    columns=3,
    gap="md",   # passo de token ou float
    children=[Card(children=[Text(content=f"Item {i}")]) for i in range(6)],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | As células, preenchidas esquerda→direita, depois cima→baixo. |
| `columns` | `int` | `2` | O número de colunas por linha (limitado a no mínimo 1). |
| `gap` | `float \| str` | `8.0` | O espaço entre células — um nome de passo de token (`"md"`) ou um `float`. |
| `theme` | `Theme` | `Theme()` | O tema cuja escala de espaçamento resolve o nome do passo. |

!!! note "Células crescem para dividir a largura; a última linha é preenchida"
    Cada filho é envolvido numa `Container` que cresce (`grow=1.0`), então as
    colunas dividem a largura igualmente (o *flex*). Linhas finais curtas são
    completadas com células vazias para manter o alinhamento das colunas.

### `HStack`

Uma pilha horizontal: filhos da esquerda para a direita com um `gap` por passo de
token. Um wrapper ergonômico estilo SwiftUI sobre a `Row` primitiva, com `align`
(eixo cruzado) e `justify` (eixo principal) na superfície.

```python
from tempest_core.components import HStack
from tempest_core.style import JustifyContent
from tempest_core.widgets import Text

barra = HStack(
    gap="sm",
    justify=JustifyContent.SPACE_BETWEEN,
    children=[Text(content="Esquerda"), Text(content="Direita")],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, dispostos da esquerda para a direita. |
| `gap` | `float \| str` | `"md"` | O espaço entre os filhos — um nome de passo de token ou um `float`. |
| `align` | `AlignItems \| None` | `CENTER` | O alinhamento no eixo cruzado (vertical) dos filhos. |
| `justify` | `JustifyContent \| None` | `None` | A distribuição no eixo principal (horizontal) dos filhos. |
| `theme` | `Theme` | `Theme()` | O tema cuja escala de espaçamento resolve o gap. |

### `VStack`

O irmão vertical do `HStack`, sobre a `Column` primitiva: filhos de cima para
baixo com um `gap` por passo de token. Aqui `align` é o eixo cruzado (horizontal)
e `justify` é o eixo principal (vertical).

```python
from tempest_core.components import VStack
from tempest_core.widgets import Text

coluna = VStack(
    gap="lg",
    children=[Text(content="Um"), Text(content="Dois"), Text(content="Três")],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, dispostos de cima para baixo. |
| `gap` | `float \| str` | `"md"` | O espaço entre os filhos — um nome de passo de token ou um `float`. |
| `align` | `AlignItems \| None` | `None` | O alinhamento no eixo cruzado (horizontal) dos filhos. |
| `justify` | `JustifyContent \| None` | `None` | A distribuição no eixo principal (vertical) dos filhos. |
| `theme` | `Theme` | `Theme()` | O tema cuja escala de espaçamento resolve o gap. |

!!! tip "`gap` por passo de token, sempre coerente"
    Nos dois stacks (e no `Grid`), um `gap` string (`"md"`) resolve contra a escala
    de espaçamento do tema via `Theme.space(...)`; um `float` cru passa direto.
    Preferir os passos mantém o ritmo vertical/horizontal consistente com o resto
    do design-system.

### `Scaffold`

O frame de página: uma app bar no topo, um corpo que cresce e uma bottom bar
opcional. O `BACKGROUND` do tema preenche o frame.

```python
from tempest_core.components import Scaffold
from tempest_core import AppBar
from tempest_core.widgets import Text

pagina = Scaffold(
    app_bar=AppBar(title="Início"),
    body=Text(content="Conteúdo da página"),
    scroll=True,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `app_bar` | `Widget \| None` | `None` | A barra do topo (comumente um `AppBar`); omitida quando `None`. |
| `body` | `Widget \| None` | `None` | O conteúdo principal; vira uma coluna vazia quando `None`. |
| `bottom_bar` | `Widget \| None` | `None` | A barra de baixo (ex.: `NavBar` ou `Footer`); omitida quando `None`. |
| `scroll` | `bool` | `False` | Quando `True`, envolve o corpo numa `ScrollView` (conveniência do Qt). |
| `theme` | `Theme` | `Theme()` | O tema cuja role `BACKGROUND` preenche o frame. |

!!! note "O corpo cresce; as barras ficam nas pontas"
    O `Scaffold` abaixa para uma `Column` que empilha, em ordem, a app bar, o corpo
    (envolvido num container que cresce, `grow=1.0`, ou numa `ScrollView` quando
    `scroll=True`) e a bottom bar. O corpo *flex* empurra as barras para o topo e a
    base do frame.

### `Sidebar`

Uma coluna lateral de largura fixa com widgets de navegação/conteúdo. A superfície
do painel é resolvida de `variant` / `color_scheme` / `elevation`, espelhando um
card; a largura e o padding fixos ficam inalterados.

```python
from tempest_core.components import Sidebar
from tempest_core import Button

lateral = Sidebar(
    width=280.0,
    children=[
        Button(label="Início", variant="ghost"),
        Button(label="Ajustes", variant="ghost"),
    ],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os widgets empilhados de cima para baixo na sidebar. |
| `width` | `float` | `240.0` | A largura fixa da sidebar em pixels lógicos. |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que a sidebar se tinge. |
| `elevation` | `int \| None` | `None` | Nível M3 explícito (0-5) sobrepondo o padrão. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície do painel. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (aceito por paridade; encaminhado). |

## Helpers de composição

Para construir componentes customizados no mesmo idioma, o pacote re-exporta o
helper de mesclagem de estilo e uma pequena paleta escura padrão.

### `merge_style`

Sobrepõe os campos **setados** de um `override` sobre um `Style` base. Só os
campos explicitamente não-`None` do override vencem; todo o resto mantém o padrão
do componente. Como `Style` é congelado, retorna uma cópia nova mesclada.

```python
from tempest_core.components import merge_style
from tempest_core.style import Style

base = Style(padding=None, radius=8.0, gap=4.0)
final = merge_style(base, Style(radius=16.0))   # radius vence; gap e padding do base
```

Esse é exatamente o mecanismo que todo componente usa para deixar você
sobrescrever só os campos com que se importa: cada `render` monta um `Style`
default e chama `merge_style(default, self.style)`. Passar `override=None`
devolve o `base` intocado.

!!! info "Override sempre por cima, sem perder o default"
    É o mesmo idioma dos botões (o override vence nos campos que seta) aplicado às
    superfícies e itens. Você nunca perde o estilo default do componente ao setar
    um campo pontual pelo `style`.

### Tokens de paleta padrão

Seis constantes `Color` — uma paleta escura contida que combina com os exemplos.
Servem como valores prontos ao montar componentes fora de um `Theme` completo.

```python
from tempest_core.components import (
    BACKGROUND,
    SURFACE,
    ACCENT,
    MUTED,
    ON_SURFACE,
    ON_MUTED,
)
from tempest_core.style import Style
from tempest_core.widgets import Container, Text

caixa = Container(
    style=Style(background=SURFACE),
    child=Text(content="Rótulo", style=Style(color=ON_SURFACE)),
)
```

| Token | Hex | Papel |
| --- | --- | --- |
| `BACKGROUND` | `#0b0f14` | Fundo da página / frame. |
| `SURFACE` | `#1f2937` | Superfície elevada (cards, painéis). |
| `ACCENT` | `#2563eb` | Cor de destaque / ação. |
| `MUTED` | `#374151` | Superfície apagada / secundária. |
| `ON_SURFACE` | `#f9fafb` | Conteúdo legível sobre `SURFACE`. |
| `ON_MUTED` | `#9ca3af` | Conteúdo apagado sobre `MUTED`. |

!!! tip "Tokens são valores prontos, não um substituto do `Theme`"
    Eles dão a um `AppBar` ou `Scaffold` uma aparência intencional na largada. Para
    temas completos e resolução por role (as roles M3 `*_container`, elevação, etc.),
    passe um `Theme` — veja o [tutorial do design-system](../tutorial/design-system.md).

## Recapitulando

- **`Surface`** é a primitiva sem padding; **`Card` é `Surface` + padding +
  `Column`**. As duas resolvem via `resolve_surface_variant` de `variant` /
  `color_scheme` / `elevation`.
- **`CardVariant`**: `ELEVATED` (elevated card, sombra nível 1) → `FILLED` (tonal
  `surface_variant`, sem sombra) → `OUTLINED` (borda `outline`, sem sombra).
- **Elevação é uma `Shadow`** mapeada do nível M3 (0-5), nunca um campo de `Style`
  novo; o renderizador a traduz para a elevação nativa.
- **`StyledContainer`** dá padding por passo de token à `Container` primitiva sem
  mutá-la.
- **Itens de conteúdo** — `ListTile` (apresentacional, ação vai no `trailing`),
  `Avatar` (círculo tonal, raio = `size / 2`), `Divider` (régua `OUTLINE_VARIANT`)
  — leem cor e espaçamento do tema.
- **Layout** — `Grid` (células que crescem para dividir a largura), `HStack` /
  `VStack` (stacks com `gap` por passo de token), `Scaffold` (corpo que cresce
  entre as barras), `Sidebar` (painel de largura fixa com superfície resolvida).
- **Helpers** — `merge_style` sobrepõe os campos setados do override; os tokens
  `BACKGROUND` / `SURFACE` / `ACCENT` / `MUTED` / `ON_SURFACE` / `ON_MUTED` são
  valores prontos de paleta.
