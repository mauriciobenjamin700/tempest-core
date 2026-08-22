# Navegação

A navegação no `tempest-core` se divide em **duas famílias**. Os **componentes**
são peças de página que **abaixam para primitivas** (`Row`/`Column`/`Container`) e
resolvem seu visual pelos tokens do `Theme` — barras, abas, trilhas e campos de
barra. Os **widgets de roteamento** são os nós de IR que hospedam a *pilha de
rotas* na árvore: `Navigator`, `TabView`, `TabBar` e `RouteDrawer`. As duas
famílias se importam do topo (`from tempest_core import ...`); a diferença é o que
cada uma faz, não de onde vem. 🚀

!!! info "O que você aprende aqui"
    - As **barras** de topo/rodapé (`AppBar`, `CollapsingAppBar`, `Header`,
      `Footer`) e como elas resolvem a **superfície** pelos tokens do tema.
    - A navegação **tab/rail** (`NavBar`, `Tabs`, `Breadcrumb`): item ativo como
      **pílula de destaque**, aba ativa com **sublinhado**, seleção **controlada
      pelo app**.
    - O **menu lateral** (`Burger`, `Drawer`): o `Burger` abaixa para um
      `IconButton`; o `Drawer` é um painel **controlado**.
    - Os **widgets de roteamento** (`Navigator`, `TabView`, `TabBar`,
      `RouteDrawer`) — os nós de IR que hospedam a pilha de rotas.
    - Os **campos de barra** (`SearchBar`, `Stepper`) montados sobre primitivas.

!!! note "Um lugar para importar"
    Tudo que é público sai do topo: `from tempest_core import AppBar, NavBar,
    Navigator, TabView, TabBar, RouteDrawer`. Os submódulos continuam existindo,
    mas você não precisa saber em qual deles cada símbolo mora.

## Barras

As barras são `Component`s de estrutura de página. `AppBar`, `Footer` e
`CollapsingAppBar` resolvem sua **superfície** (fundo + sombra de elevação +
container tingido) via `resolve_surface_variant`, exatamente como um card; a cor
do título/conteúdo é o conteúdo legível dessa superfície. `Header` lê cores e
espaçamento direto dos tokens do `Theme`.

### `AppBar`

Uma barra de aplicação de topo: `leading` opcional, `title` e `actions` no fim.
No caso mínimo você só passa o `title`:

```python
from tempest_core import AppBar
from tempest_core import Button, IconButton

barra = AppBar(
    title="Caixa de entrada",
    leading=IconButton(icon="arrow_back", label="Voltar"),
    actions=[
        IconButton(icon="search", label="Buscar"),
        Button(label="Novo"),
    ],
    variant="elevated",
    color_scheme="primary",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | O texto do título da barra. |
| `leading` | `Widget \| None` | `None` | Widget antes do título (menu/voltar); omitido quando `None`. |
| `actions` | `list[Widget]` | `[]` | Widgets de ação alinhados ao fim da barra. |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que tingir. |
| `elevation` | `int \| None` | `None` | Nível de elevação M3 (0-5) sobrescrevendo o padrão. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (paridade; encaminhado). |

!!! tip "Superfície via resolver, título por cima"
    A barra é montada com `merge_styles(surface, ...)`: o `resolve_surface_variant`
    entrega fundo + elevação + a **cor de conteúdo legível**, e o título herda essa
    cor. Um `style` explícito é mesclado **por cima** da superfície resolvida (os
    campos setados vencem). `AppBar(title=…)` sozinho já é uma barra elevada neutra.

### `CollapsingAppBar`

Uma barra estilo *sliver* que encolhe conforme o usuário rola o conteúdo. Ela não
escuta scroll sozinha: o app lê o offset do `ScrollEvent` da lista, guarda no
estado e devolve em `scroll_offset` — a altura (e a fonte do título) é derivada
disso em Python puro, então o reconciliador só faz diff de `Style.height`:

```python
from tempest_core import CollapsingAppBar

barra = CollapsingAppBar(
    title="Galeria",
    expanded_height=200.0,
    collapsed_height=56.0,
    scroll_offset=app.state.scroll,  # (1)!
    color_scheme="primary",
)
```

1. Você alimenta o `scroll_offset` a partir do `on_scroll` da sua lista rolável;
   a barra deriva a altura e a fonte do título entre expandida e colapsada.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | O texto do título da barra. |
| `expanded_height` | `float` | `200.0` | A altura no topo da rolagem (offset `0`). |
| `collapsed_height` | `float` | `56.0` | A altura mínima quando totalmente colapsada. |
| `scroll_offset` | `float` | `0.0` | O offset atual (px lógicos) dirigido pelo app via `on_scroll`. |
| `background` | `Color \| None` | `None` | Fundo que sobrescreve a superfície resolvida (escotilha legada). |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que tingir. |
| `elevation` | `int \| None` | `None` | Nível de elevação M3 (0-5) sobrescrevendo o padrão. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (paridade; encaminhado). |
| `style` | `Style \| None` | `None` | Estilo sobreposto ao default derivado da barra. |

!!! note "Colapso sem IR nova"
    A altura eases de `expanded_height` (offset `0`) até `collapsed_height` (uma
    vez passada a distância de colapso), e a fonte do título vai de 28 a 20 em
    passo. Tudo é `Style.height`/`font_size` comum — nenhum evento novo, nenhuma
    mudança de renderizador. O `background` legado ainda vence quando setado.

### `Header`

Uma faixa de cabeçalho de página: um título com subtítulo opcional. Diferente das
outras barras, **não tem `variant`** — um header é uma faixa plana, não uma
superfície elevada. As cores saem direto dos tokens (`SURFACE_VARIANT` no fundo,
`ON_SURFACE` no título, `ON_SURFACE_VARIANT` no subtítulo):

```python
from tempest_core import Header

cabecalho = Header(
    title="Configurações",
    subtitle="Gerencie sua conta e preferências",
    color_scheme="primary",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | A linha primária do cabeçalho. |
| `subtitle` | `str \| None` | `None` | Linha secundária opcional, mostrada abafada sob o título. |
| `color_scheme` | `str \| None` | `None` | Papel M3 opcional tingindo o título; `None` mantém o `ON_SURFACE` neutro. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem cores e espaçamento. |

!!! info "Só tokens, sem superfície resolvida"
    O `Header` não passa por `resolve_surface_variant`: ele lê `SURFACE_VARIANT`,
    `ON_SURFACE` e `ON_SURFACE_VARIANT` diretamente, e a tipografia vem de
    `theme.typography("headline_small")`/`("body_medium")`. Um `color_scheme`
    (diferente de `"neutral"`) tinge só o título com a cor do papel.

### `Footer`

Uma barra inferior que segura conteúdo arbitrário, centralizado. Espelha a
`AppBar` na resolução de superfície:

```python
from tempest_core import Footer
from tempest_core import Text

rodape = Footer(
    children=[Text(content="© 2026 Tempest")],
    variant="filled",
    color_scheme="neutral",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os widgets dispostos no rodapé (links, labels). |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que tingir. |
| `elevation` | `int \| None` | `None` | Nível de elevação M3 (0-5) sobrescrevendo o padrão. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (paridade; encaminhado). |

## Navegação tab/rail

Estes componentes são de **seleção presencial**: o índice ativo mora no estado do
app e é alternado a partir do `on_select`. Cada item abaixa para um `Button` cujo
handler fecha sobre o índice — nada de estado interno próprio.

### `NavBar`

Uma barra de navegação horizontal com um item destacado. O item ativo vira uma
**pílula de destaque** (`resolve_badge_variant`, SOLID, no `color_scheme`); os
inativos ficam num tratamento GHOST discreto (neutro). A barra em si é uma
superfície resolvida:

```python
from tempest_core import NavBar

barra = NavBar(
    items=["Início", "Buscar", "Perfil"],
    active=app.state.tab,  # (1)!
    on_select=lambda i: app.set_state(tab=i),
    color_scheme="primary",
)
```

1. Seleção **controlada pelo app**: o `NavBar` não guarda o índice — você passa o
   `active` do seu estado e reage no `on_select`.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `items` | `list[str]` | `[]` | Os labels dos itens visíveis, em ordem. |
| `active` | `int` | `0` | O índice do item atualmente selecionado. |
| `on_select` | `Callable[[int], Any]` | *(obrigatório)* | Chamado com o índice do item tocado. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que a pílula ativa pinta. |
| `size` | `ResponsiveSize` | `Size.MD` | A densidade — um `Size` só ou mapa por breakpoint. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a barra e os itens. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! tip "Item ativo = pílula de destaque"
    O item selecionado usa `resolve_badge_variant(SOLID)` — a mesma pílula de
    destaque do sistema de badges — enquanto os outros usam `resolve_variant(GHOST)`
    neutro. Cada item recebe `grow=1.0`, então preenchem a barra por igual.

### `Tabs`

Uma faixa de abas cuja aba ativa carrega um **sublinhado**. Cada aba é um botão
GHOST; a ativa toma a cor do papel `color_scheme` mais uma `SideBorder` inferior
fina (2px) como indicador — usando só campos de `Style` existentes, **sem** campo
novo:

```python
from tempest_core import Tabs

abas = Tabs(
    tabs=["Visão geral", "Atividade", "Ajustes"],
    active=app.state.tab,
    on_select=lambda i: app.set_state(tab=i),
    color_scheme="primary",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | `[]` | Os labels das abas visíveis, em ordem. |
| `active` | `int` | `0` | O índice da aba atualmente selecionada. |
| `on_select` | `Callable[[int], Any]` | *(obrigatório)* | Chamado com o índice da aba tocada. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 da aba ativa + sublinhado. |
| `size` | `ResponsiveSize` | `Size.MD` | A densidade — um `Size` só ou mapa por breakpoint. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a faixa e as abas. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! note "Aba ativa = sublinhado, não pílula"
    Onde o `NavBar` destaca com uma pílula preenchida, o `Tabs` destaca com o
    **indicador de sublinhado**: a aba ativa recebe a cor do papel mais uma
    `Border(width=2.0, color=accent)` na base. Como o `NavBar`, a seleção é
    controlada pelo app via `active`/`on_select`.

### `Breadcrumb`

Uma trilha de migalhas unidas por um separador. As cores saem dos tokens: a
migalha atual (última) usa `ON_SURFACE`, as demais `ON_SURFACE_VARIANT`, e os
separadores `ON_SURFACE_VARIANT`. Se você passar `on_select`, as migalhas
navegáveis viram links (`resolve_variant` LINK) — **a última nunca é tapável**:

```python
from tempest_core import Breadcrumb

trilha = Breadcrumb(
    items=["Início", "Projetos", "tempest-core"],
    separator="/",
    on_select=lambda i: app.navigate_to(i),
    color_scheme="primary",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `items` | `list[str]` | `[]` | Os labels das migalhas, da raiz à atual, em ordem. |
| `separator` | `str` | `"/"` | O texto desenhado entre as migalhas. |
| `on_select` | `Callable[[int], Any] \| None` | `None` | Handler opcional com o índice da migalha; `None` deixa tudo presentacional. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que a migalha-link pinta. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem cores e o link. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (paridade; encaminhado). |

!!! info "A última migalha é sempre presentacional"
    Mesmo com `on_select` setado, a migalha atual (`index == len(items) - 1`) é um
    `Text`, nunca um `Button` — você não navega para onde já está. Sem `on_select`,
    todas as migalhas são `Text`.

## Menu lateral

### `Burger`

Um botão de menu hambúrguer. Ele **abaixa para um `IconButton`** mostrando o glifo
curado `Icons.MENU` na variante GHOST — então reusa o resolver de variante H1 e o
sistema de ícones (um ícone de linha de verdade, não um caractere literal). O uso
típico é alternar um `Drawer`:

```python
from tempest_core import Burger

botao = Burger(
    on_click=lambda: app.set_state(menu_open=not app.state.menu_open),
    color_scheme="neutral",
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `on_click` | `Callable[[], Any]` | *(obrigatório)* | Invocado no toque (ex.: alternar um `Drawer`). |
| `variant` | `Variant` | `GHOST` | O tratamento visual (solid/outline/ghost/link). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que pintar. |
| `size` | `ResponsiveSize` | `Size.MD` | A densidade — um `Size` só ou mapa por breakpoint. |
| `glyph` | `str` | `"☰"` | **Depreciado**. Fallback de compat; o botão sempre mostra o ícone `menu`. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a variante. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! warning "`glyph` é legado — o ícone é sempre o `menu`"
    Versões antigas renderizavam o caractere de `glyph`. Hoje o `Burger` sempre
    abaixa para o `IconButton` com `Icons.MENU`; um `glyph` não-padrão é carregado
    só como label acessível. Para customizar a aparência, passe `style`.

### `Drawer`

Um painel lateral **controlado**: mostra seus `children` quando `open` é `True`, e
colapsa para uma caixa vazia quando `False`. O flag `open` mora no estado do app
(alterne-o pelo `on_click` de um `Burger`). Quando aberto, o painel resolve sua
superfície via `resolve_surface_variant`, espelhando um card:

```python
from tempest_core import Drawer
from tempest_core import Text

painel = Drawer(
    open=app.state.menu_open,  # (1)!
    children=[
        Text(content="Início"),
        Text(content="Ajustes"),
    ],
    width=260.0,
    variant="elevated",
)
```

1. Estado **controlado pelo app**: o `Drawer` não guarda `open` — você o alimenta
   e o alterna a partir do `Burger`.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `open` | `bool` | `False` | Se o drawer está expandido; `False` colapsa para caixa vazia. |
| `children` | `list[Widget]` | `[]` | Os widgets empilhados dentro do drawer aberto. |
| `width` | `float` | `260.0` | A largura do painel em px lógicos quando aberto. |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento de superfície (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que tingir. |
| `elevation` | `int \| None` | `None` | Nível de elevação M3 (0-5) sobrescrevendo o padrão. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície do painel. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (paridade; encaminhado). |

!!! note "Painel lateral, não overlay flutuante"
    O modelo de layout é flex-only (sem empilhamento/overlay), então um drawer
    aberto renderiza como **painel lateral**, não como overlay flutuante com scrim.
    Overlay verdadeiro é um follow-up de renderizador.

## Roteamento (widgets)

Estes quatro são **widgets de IR**, não componentes — importe-os de `tempest_core`
direto. Eles são a superfície de navegação *na árvore*: a `NavStack` (dona da
`App`) decide *qual* rota está no topo, e estes widgets abaixam isso para uma
subárvore renderizável que o reconciliador faz diff numa troca de rota. Os nomes
de nó e props são **congelados** para que os dois renderizadores (Qt / Compose)
concordem por valor.

### `Navigator`

Um host de pilha de navegação que renderiza a tela do topo. A `view` monta o
`child` a partir de `app.nav.top` e o embrulha num `Navigator`; empilhar/desempilhar
reconstrói com um `child` diferente, e o `depth` deixa o renderizador distinguir um
push (mais fundo) de um pop (mais raso) para escolher a direção do slide:

```python
from tempest_core import Navigator, Column, Text

nav = Navigator(
    child=Column(children=[Text(content="Tela do topo")]),
    transition="slide",
    depth=app.nav.depth,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget` | *(obrigatório)* | A tela atualmente no topo da pilha. |
| `transition` | `str` | `"slide"` | Dica de animação para a troca de tela (`"slide"` / `"fade"` / `"none"`). |
| `depth` | `int` | `0` | A profundidade atual da pilha; o renderizador compara com a anterior para escolher a direção. |

### `TabView`

Um host com abas: uma faixa de abas mais o conteúdo da aba ativa. A `view` monta o
`child` da aba ativa; tocar uma aba dispara `on_change` com um `RouteChangeEvent`
carregando `params["index"]`, então o handler troca a aba ativa e reconstrói:

```python
from tempest_core import TabView, Column, Text

view = TabView(
    tabs=["Feed", "Buscar", "Perfil"],
    active=app.state.tab,
    child=Column(children=[Text(content="Conteúdo da aba ativa")]),
    on_change=lambda e: app.set_state(tab=e.params["index"]),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | *(obrigatório)* | Os labels das abas, em ordem. |
| `active` | `int` | `0` | O índice da aba atualmente selecionada. |
| `child` | `Widget` | *(obrigatório)* | O widget de conteúdo da aba ativa. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Handler invocado com um `RouteChangeEvent` no toque. |

### `TabBar`

Uma faixa de abas autônoma: um label selecionável por aba, sem conteúdo próprio.
Emite um `RouteChangeEvent` tipado no toque, com o índice em `params["index"]`.
Use-a solta para dirigir navegação, ou deixe o `TabView` ter uma implicitamente:

```python
from tempest_core import TabBar

strip = TabBar(
    tabs=["Dia", "Semana", "Mês"],
    active=app.state.range,
    on_change=lambda e: app.set_state(range=e.params["index"]),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | *(obrigatório)* | Os labels das abas, pareados por índice entre Qt/Compose. |
| `active` | `int` | `0` | O índice da aba atualmente selecionada. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Handler opcional invocado com um `RouteChangeEvent` no toque. |

!!! tip "`TabBar` é a faixa; `TabView` é faixa + conteúdo"
    Se você só precisa das abas para dirigir estado (e renderiza o conteúdo você
    mesmo), use `TabBar`. Se quer que o host gerencie a faixa **e** a tela da aba
    ativa junto, use `TabView`.

### `RouteDrawer`

Um host de drawer-como-rota: conteúdo principal com um painel lateral que desliza
por cima. Quando `open` é `True`, o renderizador desliza o `drawer` sobre o
`child`; alternar dispara `on_change`. Modelar o drawer como widget (em vez de
overlay transiente) mantém o estado aberto/fechado na árvore declarativa, então ele
sobrevive a rebuilds e diffs como qualquer prop:

```python
from tempest_core import RouteDrawer, Column, Text

host = RouteDrawer(
    child=Column(children=[Text(content="Conteúdo principal")]),
    drawer=Column(children=[Text(content="Painel de rotas")]),
    open=app.state.drawer_open,
    on_change=lambda e: app.set_state(drawer_open=not app.state.drawer_open),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget` | *(obrigatório)* | O conteúdo principal mostrado sob o drawer. |
| `drawer` | `Widget` | *(obrigatório)* | O painel que desliza sobre o conteúdo quando aberto. |
| `open` | `bool` | `False` | Se o painel do drawer está mostrado no momento. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Handler invocado com um `RouteChangeEvent` quando o drawer alterna. |

!!! note "`Drawer` (componente) vs `RouteDrawer` (widget)"
    O `Drawer` de **Menu lateral** é um `Component` de UI que abaixa para um
    `Column`; o `RouteDrawer` é um **widget de IR** que coordena conteúdo + painel
    numa troca de rota com o `NavStack`. Escolha pela camada: peça de página vs. host
    de roteamento.

## Campos de barra

### `SearchBar`

Um campo de busca: um `Input` de texto **controlado** com botão de limpar opcional.
O `Input` interno resolve seu estilo via `resolve_field_variant`; a pílula externa
carrega uma superfície de `resolve_surface_variant`; e o botão de limpar abaixa para
um `IconButton` (glifo curado `Icons.X`, GHOST) — mostrado só quando `on_clear` está
setado **e** o campo não está vazio:

```python
from tempest_core import SearchBar

busca = SearchBar(
    value=app.state.query,  # (1)!
    placeholder="Buscar produtos",
    on_change=lambda e: app.set_state(query=e.value),
    on_clear=lambda: app.set_state(query=""),
    field_variant="filled",
    color_scheme="neutral",
)
```

1. O `on_change` recebe um `TextChangeEvent` validado a cada edição; o `value` é
   controlado pelo app.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O texto atual da consulta (controlado). |
| `placeholder` | `str` | `"Search"` | A dica de campo vazio. |
| `on_change` | `Callable[[TextChangeEvent], Any]` | *(obrigatório)* | Chamado com o `TextChangeEvent` validado a cada edição. |
| `on_clear` | `Callable[[], Any] \| None` | `None` | Handler do botão limpar; mostra só quando setado e o campo não-vazio. |
| `field_variant` | `FieldVariant` | `FILLED` | O tratamento do input interno (outline / filled / flushed). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que o foco pinta. |
| `size` | `ResponsiveSize` | `Size.MD` | A densidade — um `Size` só ou mapa por breakpoint. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem o campo e a pílula. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! tip "O botão de limpar é condicional"
    Ele só aparece quando você passa `on_clear` **e** `value` é não-vazio — nada de
    um X mudo num campo já vazio. Sem `on_clear`, a barra é só o input.

### `Stepper`

Um contador numérico: `-` decrementa, o valor atual, `+` incrementa. Ele **clampa**
o resultado aos limites opcionais antes de reportar, então o handler nunca recebe um
valor fora de faixa:

```python
from tempest_core import Stepper

qtd = Stepper(
    value=app.state.qty,
    step=1,
    min_value=0,
    max_value=10,
    on_change=lambda v: app.set_state(qty=v),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `int` | `0` | O valor atual. |
| `step` | `int` | `1` | O quanto é somado/removido por toque. |
| `min_value` | `int \| None` | `None` | O limite inferior, ou `None` para ilimitado. |
| `max_value` | `int \| None` | `None` | O limite superior, ou `None` para ilimitado. |
| `on_change` | `Callable[[int], Any]` | *(obrigatório)* | Chamado com o novo valor (já clampado) no toque. |

!!! note "O clamp acontece antes do `on_change`"
    Tocar `+` além de `max_value` (ou `-` abaixo de `min_value`) reporta o limite,
    não o valor estourado. Com ambos `None`, o stepper é ilimitado. Como todo
    componente, `value` é controlado — você reflete o valor reportado no estado.

## Recapitulando

- **Duas famílias**: componentes, que abaixam para primitivas, e widgets de
  roteamento, que hospedam a pilha de rotas na IR — as duas importadas do topo
  (`from tempest_core import ...`).
- **Barras**: `AppBar` / `Footer` / `CollapsingAppBar` resolvem a **superfície**
  via `resolve_surface_variant`; `Header` lê tokens direto (faixa plana, sem
  `variant`).
- **Tab/rail**: `NavBar` destaca o ativo com uma **pílula** (badge SOLID); `Tabs`
  com um **sublinhado** (SideBorder 2px); `Breadcrumb` é uma trilha de tokens com a
  última migalha sempre presentacional. Seleção **controlada pelo app** via
  `active` / `on_select`.
- **Menu lateral**: `Burger` abaixa para um `IconButton` (`Icons.MENU`, GHOST);
  `Drawer` é um painel **controlado** por `open`, painel lateral (não overlay).
- **Roteamento**: `Navigator` (pilha), `TabView` (faixa + conteúdo), `TabBar`
  (só faixa), `RouteDrawer` (conteúdo + painel de rota) — nós de IR com props
  congeladas, dirigidos por `RouteChangeEvent`.
- **Campos de barra**: `SearchBar` (input controlado + limpar condicional) e
  `Stepper` (contador que clampa antes de reportar).

Todos esses símbolos aparecem na [Referência da API](../reference.md); para o
modelo de estado controlado veja o [tutorial de estado](../tutorial/state.md) e o
[sistema de design](../tutorial/design-system.md).
