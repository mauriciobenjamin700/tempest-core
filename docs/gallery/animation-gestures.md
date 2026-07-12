# Animação e gestos

Esta página cobre as duas famílias de widgets que dão **vida e tato** à sua UI no
`tempest-core`: os widgets de **animação** (`Animated`, `AnimatedList`, `Hero`,
`Shimmer`, `Skeleton`) e os widgets de **gesto** (`GestureDetector`,
`PanHandler`, `ScaleHandler`, `DoubleTapHandler`, `Draggable`, `DragTarget`,
`Dismissible`, `ReorderableList`, `InteractiveViewer`).

Todos seguem a mesma filosofia do core: eles descrevem a **intenção** de forma
declarativa (uma duração, uma curva, um handler tipado) e a **interpolação ou a
detecção do ponteiro** roda no engine, não nos renderizadores. Os leaf
renderers (Qt / Compose) só realizam o resultado — o core nunca toca em pixels.
🚀

!!! info "O que você aprende aqui"
    - Como `Animated` monta um filho **já interpolado por frame** por um
      `AnimationController` + `Tween`.
    - Como `AnimatedList` anima entrada/saída com **duração + curva** por direção.
    - Como o `Hero` casa uma geometria entre telas numa **transição de elemento
      compartilhado**.
    - Como `Shimmer` e `Skeleton` viram **placeholder de carregamento** com um
      sweep de gradiente.
    - Quais **gestos reais** cada handler reporta — tap, pan/fling, pinch/rotação,
      drag-and-drop, swipe-to-dismiss, reordenar e pan+zoom — e o evento tipado
      que cada um entrega.

## Animação

Os widgets de animação carregam **só a metadata** que o renderizador precisa para
realizar o movimento. A interpolação em si mora no core: um
`AnimationController` avança um valor normalizado (0.0..1.0) no relógio de frames
do app e um `Tween` interpola entre dois extremos com esse valor. O renderizador
leaf sempre vê o props **final** do frame atual.

### `Animated`

Um wrapper de um filho só, cujo `style` o `view` já interpolou a cada frame. Você
dá um `controller` (que avança o valor) e, opcionalmente, os estilos de começo e
fim; o renderizador apenas monta o filho já no alvo do frame.

```python
from tempest_core.widgets import Animated, Container, Text
from tempest_core.animation import AnimationController
from tempest_core.style import Curve, Style

# O controller avança de 0.0 a 1.0 em 0.3s com uma ease simétrica.
controller = AnimationController(duration_s=0.3, curve=Curve.EASE_IN_OUT)

card = Animated(
    child=Container(child=Text(content="Olá")),
    controller=controller,
    style_begin=Style(opacity=0.0),  # (1)!
    style_end=Style(opacity=1.0),
)
```

1. Quando `style_begin` é `None`, o próprio `style` do filho vira o ponto de
   partida. Só o `style_end` já basta para um fade-in.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget` | *(obrigatório)* | O widget embrulhado, montado com o estilo interpolado do frame. |
| `controller` | `Any` | `None` | O `AnimationController` que dirige a interpolação (tipado `Any` para evitar ciclo de import com o módulo de animação do core). |
| `style_begin` | `Any` | `None` | O `Style` em `value == 0.0`, ou `None` para usar o próprio estilo do filho como início. |
| `style_end` | `Any` | `None` | O `Style` em `value == 1.0`, ou `None`. |

!!! note "A interpolação mora no core, não no renderizador"
    O `view` lê o `value` do `controller`, interpola o `Tween` e dobra o resultado
    no `Style` do filho — então o Qt só monta o filho normalmente. Os campos
    `controller` / `style_begin` / `style_end` ficam no nó para introspecção e
    paridade entre dispositivos, mas **não são consumidos** pelo mount path do
    renderizador Qt (uma divergência Qt-vs-Compose documentada).

!!! tip "Escolha a curva pela sensação, não pelo nome"
    O `AnimationController` aceita qualquer `Curve` — `LINEAR` (velocidade
    constante), `EASE_IN` (acelera), `EASE_OUT` (desacelera), `EASE_IN_OUT`
    (ease simétrica), `EASE` (o default do CSS), `BOUNCE` (quica ao final) e
    `ELASTIC` (oscila como mola). Cada leaf mapeia para sua curva nativa
    (`QEasingCurve` no Qt, `Easing` no Compose); o próprio core aproxima cada uma
    para o relógio de teste/simulador conseguir interpolar sem renderizador.

### `AnimatedList`

Um container flex que anima os filhos **conforme eles entram e saem**. Ele
posiciona os filhos como um `Column`/`Row`, mas numa mudança estrutural (um patch
`Insert`/`Remove`) o filho afetado é animado em vez de aparecer/sumir
instantaneamente.

```python
from tempest_core.widgets import AnimatedList, Container, Text
from tempest_core.style import Curve, FlexDirection

lista = AnimatedList(
    direction=FlexDirection.COLUMN,
    children=[
        Container(child=Text(content="Item 1")),
        Container(child=Text(content="Item 2")),
    ],
    enter_duration_ms=300,
    exit_duration_ms=300,
    enter_curve=Curve.EASE_OUT,  # entra desacelerando
    exit_curve=Curve.EASE_IN,    # sai acelerando
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `direction` | `FlexDirection` | `COLUMN` | A direção do eixo principal (coluna ou linha). |
| `children` | `list[Widget]` | `[]` | Os filhos ordenados. |
| `enter_duration_ms` | `int` | `300` | Duração da animação de entrada, em milissegundos. |
| `exit_duration_ms` | `int` | `300` | Duração da animação de saída, em milissegundos. |
| `enter_curve` | `Curve` | `EASE_OUT` | A curva de easing aplicada à entrada. |
| `exit_curve` | `Curve` | `EASE_IN` | A curva de easing aplicada à saída. |

!!! info "Entrada e saída têm curva e duração próprias"
    Os defaults — `EASE_OUT` para entrar, `EASE_IN` para sair — seguem a
    convenção de Material Motion: elementos que **chegam** desaceleram até o
    repouso, e elementos que **partem** aceleram para fora da tela. O Qt realiza
    isso com um `QPropertyAnimation` na opacidade e altura máxima do filho; o
    renderizador de dispositivo embrulha cada filho num `AnimatedVisibility` (uma
    divergência documentada).

### `Hero`

Marca uma subárvore como **elemento compartilhado** para uma transição de tela.
Quando duas telas de um `Navigator` têm um `Hero` com o mesmo `hero_tag`, o
renderizador interpola a geometria da subárvore marcada ao longo da transição de
rota.

```python
from tempest_core.widgets import Hero, Image

# Na tela de lista: a miniatura.
miniatura = Hero(hero_tag="foto-42", child=Image(src="foto-42-thumb.jpg"))

# Na tela de detalhe: a mesma tag, imagem maior — a geometria interpola entre as duas.
detalhe = Hero(hero_tag="foto-42", child=Image(src="foto-42-full.jpg"))
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `hero_tag` | `str` | *(obrigatório)* | A identidade do elemento compartilhado (precisa casar entre as telas). |
| `child` | `Widget` | *(obrigatório)* | O widget embrulhado que participa da transição. |

!!! warning "A `hero_tag` precisa ser única dentro de cada tela"
    A transição casa **um** `Hero` de origem com **um** de destino pela tag. Duas
    subárvores com a mesma tag na mesma tela deixam o pareamento ambíguo. O Qt
    anima a geometria com um `QPropertyAnimation`; o Compose usa
    `SharedTransitionLayout` + `Modifier.sharedElement` (uma divergência
    documentada).

### `Shimmer`

Um **placeholder de carregamento** que varre um destaque de gradiente sobre um
filho. Embrulha um filho (normalmente um layout de esqueleto) e anima uma faixa
diagonal indo de `base_color` até `highlight_color` e voltando, em loop — o
clássico "conteúdo carregando".

```python
from tempest_core.widgets import Shimmer, Column, Skeleton
from tempest_core.style import Color

carregando = Shimmer(
    child=Column(children=[
        Skeleton(height=16.0),
        Skeleton(height=16.0, width=180.0),
    ]),
    base_color=Color(r=224, g=224, b=224),      # tom de repouso
    highlight_color=Color(r=245, g=245, b=245), # tom do destaque em movimento
    duration_ms=1200,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget` | *(obrigatório)* | O widget que o shimmer pinta por cima. |
| `base_color` | `Color` | `Color(224, 224, 224)` | O tom de repouso do gradiente. |
| `highlight_color` | `Color` | `Color(245, 245, 245)` | O tom do destaque em movimento. |
| `duration_ms` | `int` | `1200` | A duração de uma varredura completa, em milissegundos. |

!!! tip "Shimmer é o wrapper; Skeleton é a folha"
    Use `Shimmer` para pintar o sweep sobre um layout inteiro de placeholders, e
    `Skeleton` para cada retângulo individual (linha de texto, avatar) dentro
    dele. O Qt dirige o gradiente com um loop de repaint via `QTimer`; o
    renderizador de dispositivo usa `InfiniteTransition` +
    `Brush.linearGradient` (uma divergência documentada).

### `Skeleton`

A variante **sem filho** do `Shimmer`: um único retângulo arredondado que varre o
gradiente, usado para ocupar o lugar de uma linha de texto ou avatar enquanto o
conteúdo real carrega.

```python
from tempest_core.widgets import Skeleton

# Uma linha de texto de largura fixa.
linha = Skeleton(width=200.0, height=16.0, radius=4.0)

# Um avatar quadrado, tingido pela família de cor "primary" no tema ativo.
avatar = Skeleton(width=48.0, height=48.0, radius=24.0, color_scheme="primary")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `width` | `float \| None` | `None` | A largura fixa em pixels lógicos, ou `None` para flexar. |
| `height` | `float \| None` | `None` | A altura fixa em pixels lógicos, ou `None` para flexar. |
| `radius` | `float` | `4.0` | O raio de canto em pixels lógicos. |
| `base_color` | `Color` | `Color(224, 224, 224)` | O tom de repouso do gradiente. |
| `highlight_color` | `Color` | `Color(245, 245, 245)` | O tom do destaque em movimento. |
| `duration_ms` | `int` | `1200` | A duração de uma varredura completa, em milissegundos. |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que o renderizador pode tingir os tons do shimmer. |

!!! note "`color_scheme` é resolvido pelo renderizador contra o tema ativo"
    O engine só **carrega** o prop `color_scheme`; o renderizador o resolve contra
    o tema ativo (H4). O padrão `"neutral"` dá o clássico shimmer cinza. Passe
    `"primary"` / `"secondary"` / etc. para um placeholder tingido que combine com
    a superfície onde ele mora.

## Gestos

`GestureDetector` é o primitivo base de gesto do framework: um container de um
filho só que renderiza o filho intacto mas observa o ponteiro sobre ele,
transformando sequências de press/drag/release em **eventos tipados**. Os widgets
de gesto avançados especializam esse contrato para interações mais ricas.

!!! warning "Envolva conteúdo não interativo"
    Gestos funcionam melhor em volta de conteúdo que **não** consome o ponteiro
    (um card, uma imagem, uma linha de texto). Um filho que já trata o ponteiro
    sozinho (por exemplo um `Button`) mantém o próprio tratamento — um limite v1
    documentado. Ambos os leaf renderers realizam o mesmo contrato: Qt via
    filtros de evento de ponteiro / `QGraphicsView` / `QDrag`; Compose via
    `Modifier.pointerInput` / `SwipeToDismissBox` / `graphicsLayer`.

### `GestureDetector`

O detector base: reporta tap, double-tap, long-press e swipe direcional sobre seu
filho. Cada handler é opcional e pode ser síncrono ou `async`.

```python
from tempest_core.widgets import GestureDetector, Container, Text

card = GestureDetector(
    child=Container(child=Text(content="Toque, segure ou deslize")),
    on_tap=lambda e: print("tap"),
    on_double_tap=lambda e: print("double tap"),
    on_long_press=lambda e: print("long press"),
    on_swipe=lambda e: print("swipe", e.direction),  # (1)!
)
```

1. O `SwipeEvent` carrega a direção cardinal dominante e o deslocamento total
   (veja a [Referência da API](../reference.md)).

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget sobre o qual os gestos são detectados. |
| `on_tap` | `TapHandler \| None` | `None` | Handler de um toque único (recebe `TapEvent`). |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler de um toque duplo (recebe `TapEvent`). |
| `on_long_press` | `LongPressHandler \| None` | `None` | Handler de um press mantido além do limiar (recebe `LongPressEvent`). |
| `on_swipe` | `SwipeHandler \| None` | `None` | Handler de um swipe direcional (recebe `SwipeEvent`). |

### `PanHandler`

Reporta um **pan contínuo**: conforme o ponteiro arrasta sobre o filho, o
renderizador entrega deltas por frame e, na soltura, a velocidade do fling, num
`PanEvent`.

```python
from tempest_core.widgets import PanHandler, Container, Text

arrastavel = PanHandler(
    child=Container(child=Text(content="Arraste-me")),
    on_pan=lambda e: app.set_state(x=e.dx, y=e.dy),  # (1)!
)
```

1. O handler é chamado por frame durante o arrasto; use os deltas para mover o
   conteúdo e a velocidade final para um fling.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget sobre o qual o pan é detectado. |
| `on_pan` | `EventHandler \| None` | `None` | Handler do gesto de pan (recebe `PanEvent`). |

!!! danger "`PanHandler` e `ScaleHandler` são *widgets*, não os aliases de handler"
    Os símbolos públicos `PanHandler` e `ScaleHandler` re-exportados de
    `tempest_core.widgets` são os **widgets** desta página. Eles sombreiam de
    propósito os TypeAliases de handler de mesmo nome, que ficam **privados** ao
    módulo `base`. Por isso a coluna *Tipo* do `on_pan` acima diz
    `EventHandler | None`: é um callable (sync ou `async`) que recebe o
    `PanEvent`, não o widget.

### `ScaleHandler`

Reporta **pinch** (escala + rotação) e um double-tap. O `on_scale` recebe um
`ScaleEvent` com a escala acumulada, o ponto focal e a rotação; o double-tap é o
par comum para resetar o zoom.

```python
from tempest_core.widgets import ScaleHandler, Image

foto = ScaleHandler(
    child=Image(src="mapa.png"),
    on_scale=lambda e: app.set_state(scale=e.scale),
    on_double_tap=lambda e: app.set_state(scale=1.0),  # reseta o zoom
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget sobre o qual os gestos são detectados. |
| `on_scale` | `EventHandler \| None` | `None` | Handler do pinch (recebe `ScaleEvent` com escala acumulada, ponto focal e rotação). |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler de um toque duplo (recebe `TapEvent`; par comum para resetar o zoom). |

### `DoubleTapHandler`

O caso mais enxuto: só um **toque duplo**. Útil para "curtir com dois toques" ou
um atalho de zoom sem o custo do pinch.

```python
from tempest_core.widgets import DoubleTapHandler, Image

curtivel = DoubleTapHandler(
    child=Image(src="post.jpg"),
    on_double_tap=lambda e: app.set_state(curtido=True),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget sobre o qual o toque duplo é detectado. |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler de um toque duplo (recebe `TapEvent`). |

### `Draggable`

Um filho que pode ser **pego e arrastado** até um `DragTarget`. O `drag_data` é
um rótulo opaco carregado até o alvo de soltura via `DragEvent.data`, para o alvo
identificar o que caiu nele.

```python
from tempest_core.widgets import Draggable, Container, Text

carta = Draggable(
    child=Container(child=Text(content="Rei de Espadas")),
    drag_data="rei-espadas",  # identifica o item no alvo
    on_drag=lambda e: print("soltei em", e.data),  # (1)!
)
```

1. O `on_drag` dispara quando o arrasto termina, com os dados carregados e a
   posição de soltura.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget que o usuário arrasta. |
| `drag_data` | `str` | `""` | Um rótulo opaco levado ao alvo via `DragEvent.data`, para identificar o que caiu nele. |
| `on_drag` | `DragHandler \| None` | `None` | Handler disparado quando o arrasto termina (recebe `DragEvent` com os dados e a posição de soltura). |

### `DragTarget`

Um filho que **aceita** um `Draggable` solto sobre ele. O `on_drop` dispara
quando um draggable é liberado sobre o alvo, recebendo o `DragEvent` com os dados
do item.

```python
from tempest_core.widgets import DragTarget, Container, Text

pilha = DragTarget(
    child=Container(child=Text(content="Solte cartas aqui")),
    on_drop=lambda e: app.jogar_carta(e.data),  # (1)!
)
```

1. `Draggable` + `DragTarget` formam o par de drag-and-drop: o `drag_data` do
   primeiro chega no `DragEvent.data` do segundo.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget que age como região de soltura. |
| `on_drop` | `DragHandler \| None` | `None` | Handler disparado quando um draggable é solto sobre este alvo (recebe `DragEvent` com os dados do item). |

### `Dismissible`

Um filho que pode ser **deslizado para fora** para dispensá-lo (swipe-to-delete).
O `direction` define a direção de swipe que dispara a dispensa; o `on_dismiss`
dispara quando o swipe passa do limiar.

```python
from tempest_core.widgets import Dismissible, Container, Text, SwipeDirection

item = Dismissible(
    child=Container(child=Text(content="Deslize para apagar")),
    direction=SwipeDirection.LEFT,  # dispensa ao deslizar para a esquerda
    on_dismiss=lambda e: app.remover_item(),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget sobre o qual o gesto de dispensa é detectado. |
| `direction` | `SwipeDirection` | `LEFT` | A direção de swipe que dispara a dispensa (`LEFT` / `RIGHT` / `UP` / `DOWN`). |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler disparado quando o swipe passa do limiar (recebe `DismissEvent`; reusa o tipo de evento de dispensa de overlay). |

!!! note "O `on_dismiss` reusa o `DismissEvent` dos overlays"
    Não há um evento novo para o swipe-to-dismiss: ele reusa o `DismissEvent`
    também usado quando um overlay é fechado. Uma superfície de evento a menos
    para o core carregar.

### `ReorderableList`

Uma lista vertical cujos itens podem ser **arrastados para uma nova ordem**. O
handler tipicamente muta a lista de apoio
(`items.insert(to_index, items.pop(from_index))`) e re-renderiza; uma lista de
filhos com `key` estável então diffa para um patch `Reorder`.

```python
from tempest_core.widgets import ReorderableList, Container, Text

def reordenar(e):
    itens.insert(e.to_index, itens.pop(e.from_index))
    app.rebuild()

lista = ReorderableList(
    children=[
        Container(key="a", child=Text(content="Primeiro")),
        Container(key="b", child=Text(content="Segundo")),
        Container(key="c", child=Text(content="Terceiro")),
    ],
    on_reorder=reordenar,  # (1)!
)
```

1. O `ReorderEvent` carrega o índice de origem e de destino.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os itens ordenados da lista. Prefira `key`s estáveis para o diff emitir um `Reorder`. |
| `on_reorder` | `ReorderHandler \| None` | `None` | Handler disparado quando um item é arrastado para um novo slot (recebe `ReorderEvent` com origem e destino). |

!!! tip "Use `key`s estáveis para diffar como `Reorder`"
    Com `key`s estáveis, o diff por chave reconhece que os itens só trocaram de
    lugar e emite um patch `Reorder` (o mecanismo A2), em vez de atualizações
    posicionais — nenhum tipo de patch novo é necessário.

### `InteractiveViewer`

Um container de um filho só que o usuário pode **arrastar e dar zoom** (pinch +
drag), limitado entre `min_scale` e `max_scale`. O `on_interaction` dispara
conforme a view transforma, com a escala atual, o ponto focal e a rotação.

```python
from tempest_core.widgets import InteractiveViewer, Image

visualizador = InteractiveViewer(
    child=Image(src="planta-baixa.png"),
    min_scale=0.5,
    max_scale=4.0,
    on_interaction=lambda e: app.set_state(scale=e.scale),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | O widget que é arrastado e ampliado. |
| `min_scale` | `float` | `0.5` | O fator de zoom mínimo permitido. |
| `max_scale` | `float` | `4.0` | O fator de zoom máximo permitido. |
| `on_interaction` | `EventHandler \| None` | `None` | Handler disparado enquanto a view transforma (recebe `ScaleEvent` com escala, ponto focal e rotação). |

!!! info "`InteractiveViewer` vs. `ScaleHandler`"
    Os dois entregam um `ScaleEvent`, mas com papéis diferentes: o
    `ScaleHandler` só **reporta** o pinch para você aplicar o efeito, enquanto o
    `InteractiveViewer` já **transforma** o filho (pan + zoom) dentro dos limites
    `min_scale`/`max_scale` e te avisa da transformação. Escolha o viewer quando
    quiser pan+zoom pronto; o handler quando quiser controlar o efeito na mão.

## Recapitulando

- **Animação declara a intenção, o core interpola.** `Animated` monta um filho já
  no alvo do frame (dirigido por um `AnimationController` + `Tween`);
  `AnimatedList` anima entrada/saída com **duração + `Curve`** próprias por
  direção.
- **Curvas** vêm do enum `Curve`: `LINEAR` / `EASE_IN` / `EASE_OUT` /
  `EASE_IN_OUT` / `EASE` / `BOUNCE` / `ELASTIC`, cada uma mapeada para a curva
  nativa do leaf.
- **`Hero`** casa uma geometria entre telas por `hero_tag` numa transição de
  elemento compartilhado — a tag precisa ser única por tela.
- **`Shimmer`** pinta um sweep de gradiente sobre um layout; **`Skeleton`** é a
  folha sem filho, com `color_scheme` resolvido pelo renderizador contra o tema.
- **`GestureDetector`** é o primitivo base (tap / double-tap / long-press /
  swipe); os avançados especializam: `PanHandler` (pan + fling), `ScaleHandler`
  (pinch + rotação + double-tap), `DoubleTapHandler` (só double-tap).
- **`Draggable` + `DragTarget`** formam o drag-and-drop via `drag_data` →
  `DragEvent.data`; **`Dismissible`** faz swipe-to-dismiss; **`ReorderableList`**
  arrasta para reordenar (com `key`s estáveis); **`InteractiveViewer`** dá pan +
  zoom prontos, limitado por `min_scale`/`max_scale`.
- **`PanHandler` e `ScaleHandler` são widgets** re-exportados de
  `tempest_core.widgets` — eles sombreiam de propósito os aliases de handler
  homônimos, que ficam privados ao `base`.
