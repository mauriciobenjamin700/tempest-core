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

## Componentes de pesquisa (H6) 🔬

A última camada do design system é o kit **pesquisa / ciência de dados**: os
componentes que um pesquisador acadêmico usa para mostrar o resultado de um modelo
ONNX / [`ort-vision-sdk`](https://github.com/mauriciobenjamin700/ort-vision-sdk) de
ponta a ponta. Tudo baixa para primitivas **já existentes** (composição) ou para
uma lista de comandos do `Canvas` (gráficos / overlays) — **sem campo novo de
`Style`, sem resolver novo e sem comando novo de desenho**.

### Cartões de métrica e selo de confiança

```python
from tempest_core import ConfidenceBadge, MetricCard, StatCard

# Card (H3) + Stat (H4) — rótulo, valor e uma tendência tingida (success/error).
acuracia = MetricCard(label="Acurácia", value="92%", delta="+3%", delta_up=True)

# Preset compacto (superfície "filled").
total = StatCard(label="Imagens", value="1.024")

# Badge (H4) colorido pela confiança: ≥80% = success, ≥50% = warning, < = error.
confianca = ConfidenceBadge(confidence=0.92, label="gato")  # pílula "gato 92%"
```

!!! info "`confidence_scheme`"
    O selo escolhe a família de cor com a função pura
    `confidence_scheme(conf, *, high=0.8, mid=0.5)` → `"success"` / `"warning"` /
    `"error"`. Use-a também para colorir suas próprias afordâncias de confiança.

### Gráficos sobre o `Canvas`

```python
from tempest_core import BarChart, ChartSeries, LineChart

linha = LineChart(series=[
    ChartSeries(points=[0.1, 0.4, 0.35, 0.8], label="loss", color_scheme="primary"),
])
barras = BarChart(values=[3.0, 5.0, 2.0], labels=["a", "b", "c"])
```

Os dados de uma série são um `ChartSeries` congelado (`points` + `label` +
`color_scheme` opcional), não uma lista crua, então um gráfico plota várias séries
nomeadas. O `BarChart` também aceita uma `values: list[float]` simples para o caso
de série única. Cada gráfico emite uma lista de comandos do `Canvas`
**determinística** — a suíte de conformância fixa a sequência.

!!! note "Vocabulário de desenho — sem `DrawLine`"
    Uma linha é `MoveTo` + uma sequência de `LineTo` + um `StrokeCmd`; uma barra é
    `DrawRect` + `FillCmd`; os rótulos do eixo Y são `DrawText` (ancorado na
    baseline, sem campo de alinhamento → alinhados à direita estimando a largura do
    texto). Nenhum comando de desenho novo foi introduzido.

### Overlay de detecção

```python
from tempest_core import DetectionBox, DetectionOverlay

overlay = DetectionOverlay(image_src="foto.jpg", boxes=[
    DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="gato", conf=0.93),
])
```

Um `DetectionBox` é `xyxy` **normalizado em `[0, 1]`** — independente de resolução,
multiplicado pelo tamanho do canvas na hora de desenhar. O overlay é um `Stack` de
uma `Image` (`fit=COVER`) sob um `Canvas` que desenha cada caixa
(`DrawRect` + `StrokeCmd`, cor por `confidence_scheme(box.conf)`) com uma legenda
`"{name} {conf:.0%}"`. O motor **não** depende do `ort-vision-sdk` — o adaptador
`Detection` → `DetectionBox` mora no lado do tempestroid.

### Fluxo selecionar imagem → resultado

```python
from tempest_core import ResultView

view = ResultView(
    label="Envie uma foto",
    on_pick=lambda uri: app.set_state(...),  # roda a inferência
    result=overlay,                          # o widget que você montou do resultado
)
```

### `DataTable` com ordenação e paginação

A `DataTable` ganhou cores temáticas e afordâncias **conduzidas pelo app** (o
componente não guarda estado — espelha o padrão das listas do E1): o app mantém
`sort_column` / `sort_ascending` / `page` e passa as linhas já ordenadas.

```python
from tempest_core.components import DataTable

tabela = DataTable(
    columns=["Classe", "Confiança"],
    rows=linhas_ordenadas,            # o app ordena
    sort_column=1, sort_ascending=False, on_sort=lambda col: app.ordenar(col),
    page=0, page_size=10, on_page=lambda p: app.ir_para(p),
)
```

A coluna ativa mostra a seta ▲/▼; com `on_sort` os cabeçalhos viram botões; com
`page_size` a tabela projeta a fatia da página atual e desenha um paginador
prev/next. `Calendar` / `Clock` também migraram para os tokens do tema (o visual
padrão passa da paleta escura antiga para o M3 claro).

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
- Pesquisa (`MetricCard` / `StatCard` / `ConfidenceBadge` / `LineChart` /
  `BarChart` / `DetectionOverlay` / `ResultView`) compõe primitivas e desenha
  gráficos/overlays via lista de comandos do `Canvas` — determinística, sem comando
  de desenho novo; `confidence_scheme` mapeia confiança → status; a `DataTable`
  ganha ordenação/paginação conduzidas pelo app.
- `HStack` / `VStack` aceitam `gap` por passo de token; `Spacer` é um flex.
- Um `style=` explícito sempre é mesclado por cima.
