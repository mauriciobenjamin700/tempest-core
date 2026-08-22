# Layout & estrutura

Os widgets de layout são o **esqueleto** de uma tela no `tempest-core`: eles não
pintam conteúdo próprio, mas **posicionam, empilham, recortam e protegem** os
filhos. Todos são nós imutáveis da IR (Pydantic frozen) que o reconciliador
diffa e os renderizadores de folha aplicam — a geometria de flexbox vem do
`Style` do nó (ancorado no modelo de caixa do **Material 3 / CSS flexbox**),
enquanto cada widget aqui só declara *qual* comportamento de container ele tem. 🚀

!!! info "O que você aprende aqui"
    - Os dois **containers de eixo** (`Column`, `Row`) e como `justify` / `align` /
      `gap` moldam a distribuição dos filhos.
    - Os containers de **filho único** (`Container`, `SafeArea`, `AspectRatio`) e
      os de **múltiplos filhos** (`ScrollView`, `Stack`, `Wrap`, `PageView`,
      `KeyboardAvoidingView`).
    - O `Spacer` — o primitivo de espaço flexível — e **como ele abaixa** para
      `style.grow`.
    - Como o `Stack` sobrepõe camadas por z-order e como `SafeAreaEdge` seleciona
      as bordas protegidas.

!!! note "A configuração de layout mora no `style`, não em props por widget"
    `Column`, `Row`, `Stack` e `Wrap` **não** têm props tipo `justify` ou `gap`;
    esses valores vivem no `Style` do nó (herdado de `Widget`). Você compõe o
    layout assim:

    ```python
    from tempest_core import Row
    from tempest_core.style import AlignItems, JustifyContent, Style

    barra = Row(
        style=Style(
            justify=JustifyContent.SPACE_BETWEEN,  # distribui no eixo principal
            align=AlignItems.CENTER,  # centraliza no eixo cruzado
            gap=8.0,  # espaço entre filhos
        ),
        children=[],
    )
    ```

    Os membros reais dos enums de flex estão em `tempest_core.style`
    (`FlexDirection`, `JustifyContent`, `AlignItems`, `FlexWrap`, `Position`,
    `StackAlign`) — veja a [Referência da API](../reference.md).

!!! tip "Alguns widgets só existem em `tempest_core.widgets`"
    `Column`, `Row`, `Container` e `Spacer` são re-exportados no topo
    (`from tempest_core import Column`). Os demais (`ScrollView`, `SafeArea`,
    `SafeAreaEdge`, `Stack`, `Wrap`, `PageView`, `AspectRatio`,
    `KeyboardAvoidingView`) vêm de `from tempest_core.widgets import ...` — é o que
    os exemplos abaixo usam.

## `Column`

Um container **flex vertical**: o eixo principal vai de cima para baixo. Os
filhos são empilhados na ordem em que aparecem em `children`.

```python
from tempest_core import Column, Text

coluna = Column(
    children=[
        Text(content="Primeira linha"),
        Text(content="Segunda linha"),
        Text(content="Terceira linha"),
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, empilhados de cima para baixo. |

!!! tip "`justify` é o eixo principal, `align` é o cruzado"
    Numa `Column`, o eixo principal é **vertical**: `Style(justify=...)` distribui
    os filhos de cima para baixo (`JustifyContent.SPACE_BETWEEN`, `CENTER`, …) e
    `Style(align=...)` os alinha horizontalmente (`AlignItems.START`, `CENTER`,
    `STRETCH`, …). Você não precisa setar `Style(direction=FlexDirection.COLUMN)` —
    a `Column` já é a direção coluna; o campo `direction` é para casos avançados de
    container genérico.

!!! note "Filhos vazios são um estado válido"
    `children` tem `default_factory` de lista vazia — uma `Column()` sem filhos é
    uma coluna vazia legítima, não um erro. Isso segue a convenção de coleções do
    projeto (nunca levantar erro por coleção vazia).

## `Row`

Um container **flex horizontal**: o eixo principal vai da esquerda para a
direita. É o espelho de `Column` no outro eixo.

```python
from tempest_core import Button, Row

barra = Row(
    children=[
        Button(label="Salvar"),
        Button(label="Cancelar", variant="outline"),
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, dispostos da esquerda para a direita. |

!!! tip "Empurre filhos para as pontas com `Spacer` ou `justify`"
    Para separar dois grupos numa `Row`, você pode setar
    `Style(justify=JustifyContent.SPACE_BETWEEN)` **ou** dropar um
    [`Spacer`](#spacer) entre eles. As duas técnicas resolvem o mesmo layout; o
    `Spacer` é útil quando você quer pesos diferentes entre lacunas.

## `Container`

Uma **caixa de filho único** usada para padding, background, bordas e
dimensionamento. Diferente de `Column`/`Row`, ele não distribui um eixo — ele
envolve **um** widget (ou nenhum) e aplica o modelo de caixa do seu `Style`.

```python
from tempest_core import Container, Text
from tempest_core.style import Edge, Style

cartao = Container(
    style=Style(
        padding=Edge.all(16.0),
        background="#FFFFFF",  # str vira Color anywhere a Color is expected
        radius=12.0,
    ),
    child=Text(content="Conteúdo do cartão"),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |

!!! note "`child` é opcional — um `Container` sem filho é uma caixa vazia"
    Com `child=None`, o `Container` vira uma caixa puramente visual (um espaçador
    pintado, um divisor, um bloco de cor). `child_nodes()` devolve `[]` nesse caso,
    então o reconciliador o trata como folha.

## `ScrollView`

Um container **rolável** para uma lista de filhos que transborda a viewport. Por
padrão rola na vertical; ative `horizontal` para rolar na lateral.

```python
from tempest_core import Text
from tempest_core.widgets import ScrollView

lista = ScrollView(children=[Text(content=f"Item {i}") for i in range(200)])

carrossel = ScrollView(horizontal=True, children=[])
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `horizontal` | `bool` | `False` | Quando `True`, os filhos se dispõem e rolam da esquerda para a direita; senão empilham e rolam de cima para baixo. |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados. |

!!! warning "`ScrollView` monta todos os filhos de uma vez"
    Um `ScrollView` constrói a lista inteira em memória — ótimo para dezenas de
    itens, ruim para milhares. Para listas grandes com virtualização (janela
    deslizante), use os widgets `LazyColumn` / `LazyRow` / `LazyGrid` (veja a
    [Referência da API](../reference.md)).

## `SafeArea`

Uma caixa de filho único que **afasta o conteúdo das intrusões do sistema** — a
barra de status, a barra de navegação, ou um recorte/notch de tela. Espelha o
`SafeAreaView` do React Native. No renderizador de dispositivo o inset é o real
`WindowInsets.safeDrawing` reportado pela plataforma; no simulador de desktop
(sem barras de sistema) ele usa insets aproximados fixos.

```python
from tempest_core import Column, Text
from tempest_core.widgets import SafeArea

tela = SafeArea(child=Column(children=[Text(content="Conteúdo protegido")]))
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |
| `edges` | `list[SafeAreaEdge]` | *(todas as quatro)* | As bordas a proteger com inset. |

### O enum `SafeAreaEdge`

`edges` seleciona **quais** bordas recebem inset. O padrão é as quatro; passe um
subconjunto para deixar as outras rentes à borda física.

| Membro | Valor | O que o inset protege |
| --- | --- | --- |
| `SafeAreaEdge.TOP` | `"top"` | Empurra o conteúdo abaixo da barra de status ou de um recorte/notch superior. |
| `SafeAreaEdge.RIGHT` | `"right"` | Mantém o conteúdo livre de intrusões à direita (canto arredondado, notch em paisagem). |
| `SafeAreaEdge.BOTTOM` | `"bottom"` | Levanta o conteúdo acima da barra de navegação ou da área do gesto de home. |
| `SafeAreaEdge.LEFT` | `"left"` | Mantém o conteúdo livre de intrusões à esquerda (canto arredondado, notch em paisagem). |

```python
from tempest_core import Column, Text
from tempest_core.widgets import SafeArea, SafeAreaEdge

# Só protege o topo — o rodapé fica rente à borda (ex.: uma barra que já encosta).
tela = SafeArea(
    edges=[SafeAreaEdge.TOP],
    child=Column(children=[Text(content="Conteúdo")]),
)
```

!!! tip "Proteja só o que precisa"
    Uma barra de navegação inferior full-bleed normalmente quer ficar rente à
    borda de baixo, então você passa
    `edges=[SafeAreaEdge.TOP, SafeAreaEdge.LEFT, SafeAreaEdge.RIGHT]` e deixa o
    `BOTTOM` de fora. Proteger uma borda que não precisa cria um espaço morto
    visível.

## `Spacer`

Uma **caixa vazia flexível** que consome o espaço livre ao longo do eixo
principal do pai. Dropado entre dois filhos de uma `Row`/`Column`, ele se expande
e empurra os irmãos para as pontas. É uma folha invisível — só o `grow` do seu
`Style` importa.

```python
from tempest_core import Button, Row, Spacer

# "Voltar" à esquerda, "Avançar" à direita — o Spacer empurra tudo pras pontas.
rodape = Row(
    children=[
        Button(label="Voltar", variant="ghost"),
        Spacer(),
        Button(label="Avançar"),
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `flex` | `float` | `1.0` | O peso de flex pelo qual o spacer cresce (deve ser `> 0`); assado em `style.grow`. |

!!! note "Como o `Spacer` abaixa: `flex` vira `style.grow`"
    Na construção, um `model_validator(mode="after")` assa `flex` em `style.grow`
    **quando o `grow` está unset**. Assim o `Style` que os renderizadores consomem
    sempre carrega um `grow`, e um `Spacer()` estica mesmo sem `style` explícito. Um
    `style.grow` explícito **vence** — então um spacer com peso duplo é
    `Spacer(style=Style(grow=2.0))` (ou o próprio `flex`). Os renderizadores o
    realizam como caixa esticável (Qt `addStretch` / `QWidget` crescente; Compose
    `Modifier.weight`), reusando só o campo `grow` existente — nenhum campo novo.

!!! tip "Pesos assimétricos com dois `Spacer`"
    Dois spacers com `flex` diferentes dividem o espaço livre nessa proporção:
    `Spacer(flex=1.0)` + `Spacer(flex=2.0)` deixam o segundo com o dobro da lacuna
    — útil para centralizar um filho fora do meio geométrico.

## `Stack`

Um container de **sobreposição**: os filhos compartilham uma caixa e são pintados
em camadas por z-order. Diferente de `Column`/`Row` (que dispõem ao longo de um
eixo), o `Stack` pinta os filhos **um sobre o outro** na ordem de declaração — o
primeiro é a camada de baixo, o último fica por cima. É o primitivo de overlay do
framework: um scrim, um card modal, um toast ou um FAB é só um filho posterior de
um `Stack` que envolve o conteúdo da página.

```python
from tempest_core import Container, Text
from tempest_core.style import Position, Style
from tempest_core.widgets import Stack

tela = Stack(
    children=[
        Container(child=Text(content="Conteúdo da página")),  # camada de baixo
        Container(  # scrim full-bleed por cima
            style=Style(
                position=Position.ABSOLUTE,
                top=0.0,
                right=0.0,
                bottom=0.0,
                left=0.0,
                background="#000000",
                opacity=0.5,
            ),
        ),
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, camada de baixo primeiro. |

!!! note "Filhos posicionados vs não posicionados"
    Um filho **sem** posição é alinhado dentro da caixa pelo `Style.stack_align` do
    `Stack`. Um filho cujo `Style` seta `position = ABSOLUTE` sai do fluxo e é
    ancorado pelos insets `top`/`right`/`bottom`/`left` (como o `Positioned` do
    Flutter / `position: absolute` do CSS). Setar `left` **e** `right` (ou `top` e
    `bottom`) estica o filho naquele eixo — um scrim full-bleed é `ABSOLUTE` com os
    quatro insets em `0`.

!!! info "`stack_align` usa o enum `StackAlign`, não `justify`/`align`"
    O alinhamento dos filhos não posicionados do `Stack` é de **dois eixos** e usa
    `Style(stack_align=...)`. Os membros reais são: `TOP_START`, `TOP_CENTER`,
    `TOP_END`, `CENTER_START`, `CENTER`, `CENTER_END`, `BOTTOM_START`,
    `BOTTOM_CENTER`, `BOTTOM_END` — cada um cruza uma banda vertical (topo/centro/
    baixo) com uma horizontal (início/centro/fim). Containers de flex comuns
    continuam usando `JustifyContent`/`AlignItems` de eixo único.

## `Wrap`

Um container de **flow-layout**: os filhos fluem da esquerda para a direita e
quebram para a próxima linha quando a atual enche. É o primitivo natural para
chips, tags ou qualquer conjunto de pílulas de fluxo livre — diferente da `Row`,
que mantém todo filho numa única linha.

```python
from tempest_core import Button
from tempest_core.widgets import Wrap

chips = Wrap(
    children=[
        Button(label=tag, variant="outline") for tag in ["Python", "Rust", "Go", "Zig"]
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados, fluídos e quebrados na ordem. |

!!! note "O `Wrap` quebra por padrão — e como ele abaixa"
    O wrapping é controlado por `Style.flex_wrap`, mas um `Wrap` **quebra mesmo com
    o campo unset**, já que quebrar é o propósito do widget. Os membros reais de
    `FlexWrap` são `NOWRAP`, `WRAP` e `WRAP_REVERSE` (esse último empilha as novas
    linhas na ordem cruzada reversa). O renderizador Compose abaixa o `Wrap` para
    `FlowRow`/`FlowColumn`; o Qt realiza o fluxo imperativamente.

## `PageView`

Um **carrossel horizontal paginado**: uma página de largura total visível por
vez. Cada filho é uma página; o usuário desliza (dispositivo) ou usa controles
prev/next (simulador) para navegar. O índice ativo mora na **state da aplicação**
— o app passa a `page` atual e a atualiza a partir do handler `on_page_change`.

```python
from tempest_core import Container, Text
from tempest_core.widgets import PageView

onboarding = PageView(
    page=0,
    on_page_change=lambda e: print("nova página:", e.page),  # (1)!
    children=[
        Container(child=Text(content="Bem-vindo")),
        Container(child=Text(content="Recursos")),
        Container(child=Text(content="Pronto!")),
    ],
)
```

1. O handler recebe um `PageChangeEvent` com o novo índice em `.page` (veja a
   [Referência da API](../reference.md)).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | As páginas ordenadas. |
| `page` | `int` | `0` | O índice da página ativa (base 0), dirigido pela state da aplicação. |
| `on_page_change` | `PageChangeHandler \| None` | `None` | Handler invocado com um `PageChangeEvent` quando a página ativa muda. |

!!! warning "Ignore o evento cujo `page` já bate com a state"
    Para evitar um loop de feedback, o handler deve **ignorar** um
    `PageChangeEvent` cujo `page` já é igual ao índice na state. O `PageView` é
    controlado: a fonte da verdade é a state da app, não o widget. O renderizador
    Compose o abaixa para um `HorizontalPager`; o Qt usa um `QStackedWidget` com
    navegação prev/next.

## `AspectRatio`

Uma caixa de filho único que **restringe o filho a uma razão largura/altura
fixa**. O `ratio` é `largura / altura`: `1.0` é quadrado, `16/9` é widescreen. O
renderizador deriva a dimensão faltante a partir da que o pai limita.

```python
from tempest_core.widgets import AspectRatio, Image

# Um vídeo/thumb sempre 16:9, não importa a largura disponível.
thumb = AspectRatio(ratio=16 / 9, child=Image(src="capa.jpg"))
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `ratio` | `float` | *(obrigatório)* | A razão `largura / altura` a impor (deve ser `> 0`). |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |

!!! note "É o par explícito de `Style.aspect_ratio` — e como abaixa"
    Existe também o campo `Style.aspect_ratio`; use o **widget** quando fixar a
    razão é o único propósito da caixa, e o campo de `Style` quando a razão é só uma
    entre várias regras de estilo. Os dois coexistem. O renderizador Compose abaixa
    o widget para `Modifier.aspectRatio`; o Qt deriva a dimensão fixa
    imperativamente.

## `KeyboardAvoidingView`

Um container **vertical que recua o conteúdo quando o teclado aparece**. Envolve
os filhos e, com o teclado on-screen aberto, os inseta para o input focado ficar
visível acima dele.

```python
from tempest_core import Button, Column
from tempest_core.widgets import Input, KeyboardAvoidingView

form = KeyboardAvoidingView(
    children=[
        Column(
            children=[
                Input(placeholder="E-mail"),
                Input(placeholder="Senha"),
                Button(label="Entrar"),
            ]
        ),
    ]
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados que a view inseta. |

!!! info "Sem contrato de evento — o inset é 100% do renderizador"
    O `KeyboardAvoidingView` **não** declara nenhum evento; o inset do teclado é
    tratado pelo renderizador, não exposto a handlers da aplicação. No dispositivo,
    o Compose o abaixa para uma `Column` com `Modifier.imePadding()` (dirigido por
    `WindowInsets.ime`); o simulador Qt escuta
    `QApplication.inputMethod().keyboardRectangleChanged` e ajusta as margens,
    comportando-se como uma `Column` comum no desktop (sem teclado virtual).

## Recapitulando

- **Containers de eixo**: `Column` (vertical) e `Row` (horizontal) dispõem os
  filhos ao longo do eixo principal; `justify`/`align`/`gap` moram no `Style`.
- **Filho único**: `Container` (modelo de caixa que você define), `SafeArea`
  (insets que o sistema reporta, por `SafeAreaEdge`), `AspectRatio` (razão
  `largura/altura` fixa).
- **Múltiplos filhos**: `ScrollView` (rola, monta tudo), `Stack` (sobreposição por
  z-order + `position`/`stack_align`), `Wrap` (flow-layout que quebra por padrão),
  `PageView` (carrossel controlado pela state), `KeyboardAvoidingView` (recua sob
  o teclado).
- **`Spacer`** é a folha invisível que estica: `flex` abaixa para `style.grow`, e
  um `style.grow` explícito vence.
- **A geometria de flexbox mora no `Style`** — os widgets só declaram *qual*
  comportamento de container têm; os renderizadores abaixam cada um para as
  primitivas nativas (Compose `FlowRow`/`HorizontalPager`/`Modifier.*`; Qt
  imperativo).
