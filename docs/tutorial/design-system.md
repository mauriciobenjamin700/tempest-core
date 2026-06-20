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

## Exibição de dados e feedback (H4)

A camada de **feedback** adiciona três famílias de cor de status do Material 3 —
`success` / `warning` / `info` — e dois novos resolvers: `resolve_badge_variant`
(badge / tag / chip) e `resolve_alert_variant` (alert / banner). Alertas, como
superfícies, são **não interativos** (sem tabela de estados).

```python
from tempest_core import Alert, Badge, Stat
from tempest_core.style import AlertVariant, BadgeVariant

ok = Badge(label="LIVE", variant=BadgeVariant.SUBTLE, color_scheme="success")  # (1)!
note = Alert(                                  # (2)!
    title="Salvo",
    body="Suas alterações estão no ar.",
    variant=AlertVariant.LEFT_ACCENT,
    color_scheme="success",
)
metric = Stat(label="Usuários ativos", value="1.2k", delta="+12%", delta_up=True)  # (3)!
```

1. Badge: `SOLID` (papel + on-papel), `SUBTLE` (par `*_container` / `on_*_container`,
   seguro para AA) ou `OUTLINE` (transparente + borda no papel).
2. Alert: `SUBTLE` (padrão), `SOLID`, `LEFT_ACCENT` / `TOP_ACCENT` (preenchimento
   sutil + uma borda direcional grossa no papel saturado; os renderizadores
   espelham o lado físico sob RTL).
3. `Stat` tinge o delta com o papel `success` (alta) ou `error` (baixa).

!!! warning "Contraste: por que `SUBTLE` usa o par `*_container`"
    Um papel de status saturado sobre branco pode **falhar no WCAG-AA** (medido:
    `success` sólido = 3.02). Por isso as superfícies de status sutis usam o par
    tonal `*_container` / `on_*_container` (≈13.7 de contraste), que passa no AA.
    As famílias de status são geradas de sementes semânticas fixas (verde / âmbar /
    azul) e continuam **aditivas + retrocompatíveis** — nenhum campo novo de
    `Style`.

`Alert` / `Stat` / `ProgressStepper` são novos componentes; `Tag` é um preset
estático (não selecionável) de `Chip`. `Badge` / `Banner` / `Avatar` /
`EmptyState` / `SegmentedControl` / `Rating` / `Chip` foram re-tematizados sobre os
tokens, e os call sites antigos continuam funcionando (o `tone` legado mapeia para
`color_scheme`).

## Navegação (H5)

Barras, painéis e abas também são **temáticos** — e sem nenhum resolver, enum ou
campo de `Style` novo: a fase H5 é um **skin pass** que reaproveita os resolvers
que você já conhece. As barras (`AppBar` / `Footer` / `Sidebar` / `Drawer`) usam o
resolver de superfície do H3; o item ativo da `NavBar` é uma pílula de destaque
(resolver de badge do H4) e os inativos são *ghost* (resolver de variante do H1).

```python
from tempest_core import Tabs
from tempest_core.components import AppBar, NavBar, SearchBar

bar = AppBar(title="Caixa de entrada", color_scheme="primary")  # (1)!
busca = SearchBar(value="", on_change=lambda e: None, color_scheme="primary")  # (2)!
nav = NavBar(items=["Início", "Busca", "Você"], active=0, on_select=lambda i: None)  # (3)!
abas = Tabs(tabs=["Resumo", "Atividade"], active=0, on_select=lambda i: None)  # (4)!
```

1. `AppBar` / `Footer` / `CollapsingAppBar` resolvem a superfície (fundo + sombra
   de elevação + container tingido) via `resolve_surface_variant`; a cor do título
   é o conteúdo legível da superfície. O `variant` (`ELEVATED` / `FILLED` /
   `OUTLINED`) e o `color_scheme` valem aqui também.
2. `SearchBar` resolve o `Input` interno com `resolve_field_variant` (campo
   conduzido pelo foco), a pílula externa com `resolve_surface_variant` e o botão
   de limpar vira um `IconButton` (o ícone `x`).
3. `NavBar`: o item ativo é uma **pílula de destaque** (`resolve_badge_variant`
   `SOLID`) no papel do `color_scheme`; os inativos são `resolve_variant` `GHOST`
   (neutro). `on_select` recebe o índice tocado.
4. `Tabs` (componente novo): cada aba é um texto `GHOST`; a aba ativa toma a cor do
   papel **mais um indicador de sublinhado** — uma fina `SideBorder` inferior no
   papel de destaque (apenas campos existentes de `Border` / `SideBorder`).

!!! tip "Ergonomia idêntica à dos botões"
    Todo componente de navegação aceita `color_scheme` / `size` / `theme` / `media`
    e um `style=` explícito por cima — a mesma API do `Button`. Os call sites
    antigos (`AppBar(title=…)`, `NavBar(items=…, …)`, `Burger(on_click=…)`)
    continuam funcionando sem mudança: os props do H5 são aditivos.

!!! note "`Burger` agora é um `IconButton`"
    `Burger` baixa para um `IconButton` com o ícone `menu` (`GHOST`), reaproveitando
    o sistema de ícones. O antigo prop `glyph` permanece como **fallback
    descontinuado** (retrocompatível), mas o botão sempre mostra o ícone real.

## Recapitulando

- `variant` / `size` / `color_scheme` descrevem a intenção; o resolver puro produz
  o `Style`.
- Superfícies (`Card` / `Surface` / `resolve_surface_variant`) são não
  interativas: elevação, preenchimento tonal ou borda.
- Feedback (`Badge` / `Alert` / `Stat` / `resolve_badge_variant` /
  `resolve_alert_variant`) traz as famílias de status `success` / `warning` /
  `info` — subtle usa o par `*_container` para AA.
- Navegação (`AppBar` / `NavBar` / `Tabs` / `SearchBar`) é um skin pass: barras via
  resolver de superfície, item ativo via pílula de destaque, abas com sublinhado —
  sem resolver/enum/campo novo.
- `HStack` / `VStack` aceitam `gap` por passo de token; `Spacer` é um flex.
- Um `style=` explícito sempre é mesclado por cima.
