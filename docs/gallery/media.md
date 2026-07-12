# Mídia & Canvas

Depois das folhas simples de texto e botão, esta é a superfície **rica** do
`tempest-core`: bitmaps e ícones, um **`Canvas` de modo retido** (uma lista
serializável de comandos de desenho), embutidos de vídeo/web/SVG, câmera ao vivo
e leitura de QR, um mapa embutido e os *wrappers* de efeito visual
(`Blur` / `BackdropFilter` / `ClipPath`). 🎨

Tudo aqui segue a mesma regra do resto da IR: **só valores JSON-serializáveis**.
As cores nos comandos de `Canvas` são listas `[r, g, b, a]` de floats em `[0, 1]`
— nunca tuplas nem objetos `Color` — então a mesma lista chega aos dois
renderizadores de folha (Qt via `QPainter`; Compose via `drawIntoCanvas`) sem
tradução.

!!! info "O que você aprende aqui"
    - As folhas de **imagem e ícone** (`Image`, `Icon`, `Svg`) e o enum `ImageFit`
      que decide como algo escala dentro da caixa.
    - Como o **`Canvas` é um modelo de desenho declarativo**: uma *lista de
      comandos* (`MoveTo`, `LineTo`, `FillCmd`, …) que os renderizadores repetem a
      cada pintura.
    - As **superfícies avançadas e de mídia do device**: vídeo, web view, câmera,
      scanner de QR, mapa — e os *wrappers* de efeito (`Blur`, `BackdropFilter`,
      `ClipPath`).

## Imagem & ícones

A base visual: trazer um pixel ou um vetor para a tela e dizer **como ele escala**
dentro da caixa. Três folhas (`Image`, `Icon`, `Svg`) e um enum compartilhado
(`ImageFit`).

### `ImageFit`

O vocabulário de escala, emprestado do `object-fit` do CSS. Ele aparece em
`Image.fit` e em `Svg.fit`, e decide o que acontece quando a razão de aspecto do
conteúdo não bate com a da caixa.

| Membro | Valor | O que faz |
| --- | --- | --- |
| `CONTAIN` | `"contain"` | Escala preservando a razão de aspecto até caber **inteiro** na caixa. A imagem toda fica visível; pode sobrar espaço vazio (letterbox) no eixo não preenchido. |
| `COVER` | `"cover"` | Escala preservando a razão de aspecto até **cobrir** a caixa toda. Sem espaço vazio; o que sobra no eixo mais longo é cortado. |
| `FILL` | `"fill"` | Estica para a largura e altura exatas da caixa, **ignorando** a razão de aspecto. Nada é cortado, mas a imagem pode distorcer. |
| `NONE` | `"none"` | Não escala; renderiza no tamanho intrínseco em pixels. Maior que a caixa → recortado; menor → centralizado com espaço em volta. |

```python
from tempest_core import ImageFit

ImageFit.CONTAIN  # cabe inteiro, pode sobrar espaço
ImageFit.COVER    # cobre tudo, pode cortar
```

!!! tip "`CONTAIN` vs. `COVER`"
    A escolha quase sempre é entre esses dois: `CONTAIN` quando **nenhum pixel
    pode sumir** (um logo, um diagrama) e `COVER` quando a caixa **não pode ter
    buraco** (um banner, um avatar de fundo). `FILL` distorce e `NONE` ignora a
    caixa — use-os só quando é exatamente isso que você quer.

### `Image`

Um bitmap carregado de uma URL ou de um asset empacotado. No mínimo, só `src`:

```python
from tempest_core import Image, ImageFit

capa = Image(
    src="https://picsum.photos/800/600",
    fit=ImageFit.COVER,
    alt="Foto de capa do artigo",
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `src` | `str` | *(obrigatório)* | A fonte da imagem — uma URL `http(s)` ou um caminho de asset empacotado. |
| `fit` | `ImageFit` | `CONTAIN` | Como a imagem escala dentro da caixa. |
| `alt` | `str` | `""` | Texto alternativo mostrado se a imagem não puder carregar. |

!!! note "`alt` é acessibilidade, não decoração"
    O `alt` vira o texto alternativo (equivalente ao `alt` do HTML): ele aparece
    se a imagem falhar e é o que os leitores de tela anunciam. Preencha-o sempre
    que a imagem carregar informação.

### `Icon`

Um ícone vetorial. O `name` pode ser um dos nomes **curados** do framework (ex.
`"search"`, `"home"`) — nesse caso o renderizador traça a geometria de path única
embutida — ou um identificador de ícone de plataforma qualquer; se nada resolver,
o renderizador cai para mostrar o próprio nome.

```python
from tempest_core import Icon

lupa = Icon(name="search", size=20.0)
casa = Icon(name="home")  # tamanho padrão do renderizador
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `name` | `str` | *(obrigatório)* | O identificador do ícone — um valor curado (ou sua string) ou um nome de plataforma. |
| `size` | `float \| None` | `None` | O lado do ícone em pixels lógicos, ou `None` para o padrão do renderizador. |

### `Svg`

Um gráfico vetorial escalável carregado de uma URL ou asset. Diferente do `Icon`
(uma geometria de path única), o `Svg` renderiza um documento SVG inteiro, e reusa
o mesmo `ImageFit` da `Image` para escalar:

```python
from tempest_core import Svg, ImageFit

logo = Svg(src="assets/logo.svg", fit=ImageFit.CONTAIN)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `src` | `str` | *(obrigatório)* | A fonte do SVG — uma URL `http(s)` ou um caminho de asset. |
| `fit` | `ImageFit` | `CONTAIN` | Como o vetor escala dentro da caixa. |

## Canvas & vocabulário de desenho

O `Canvas` não desenha via chamadas imperativas — ele **interpreta uma lista de
comandos**. Essa lista *é* a IR do desenho: uma sequência serializável e
diffável por valor de `DrawCommand` que os dois renderizadores de folha repetem a
cada pintura. Você monta a cena como dados; o reconciler faz o diff da lista por
valor e emite um único `Update` com a nova lista quando algo muda.

Um `DrawCommand` é uma **união discriminada** (pelo campo `kind`) de nove modelos
de valor congelados. Pense neles como um mini vocabulário de desenho, com dois
grupos:

- **Construção de path** — acumulam geometria no path ativo: `MoveTo`, `LineTo`,
  `ArcTo`, `Close`, `DrawRect`, `DrawOval`.
- **Pintura** — consomem o path ativo (e o resetam): `FillCmd`, `StrokeCmd`. Mais
  o `DrawText`, que pinta texto direto num ponto.

A ideia central: **uma forma = geometria + pintura**. Uma linha é
`MoveTo` + `LineTo` + `StrokeCmd`. Uma barra preenchida é `DrawRect` + `FillCmd`.
Você primeiro descreve *onde*, depois diz *como pintar*.

### `Canvas`

A superfície de modo retido que interpreta a lista.

```python
from tempest_core import (
    Canvas,
    MoveTo,
    LineTo,
    StrokeCmd,
    DrawRect,
    FillCmd,
)

grafico = Canvas(
    width=200.0,
    height=120.0,
    commands=[
        # Uma linha: mova o ponto, trace até o próximo, então pincele.
        MoveTo(x=0.0, y=100.0),
        LineTo(x=200.0, y=20.0),
        StrokeCmd(color=[0.1, 0.5, 0.9, 1.0], width=2.0),
        # Uma barra: descreva o retângulo, então preencha.
        DrawRect(x=20.0, y=60.0, width=40.0, height=60.0),
        FillCmd(color=[0.9, 0.3, 0.2, 1.0]),
    ],
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `commands` | `list[DrawCommand]` | `[]` | Os comandos ordenados repetidos a cada pintura. |
| `width` | `float \| None` | `None` | Largura fixa opcional do canvas, em pixels lógicos. |
| `height` | `float \| None` | `None` | Altura fixa opcional do canvas, em pixels lógicos. |

!!! info "A ordem é a semântica"
    Os comandos rodam **em ordem**, como camadas de tinta: um comando de pintura
    (`FillCmd` / `StrokeCmd`) consome tudo que foi acumulado no path *até ali* e
    **reseta** o path. Então cada forma pintada é um bloco
    `geometria… → pintura`, e a próxima forma começa do zero.

### Comandos de construção de path

| Comando | `kind` | Campos (padrão) | O que faz |
| --- | --- | --- | --- |
| `MoveTo` | `"move_to"` | `x`, `y` | Move o ponto atual do path **sem desenhar**. |
| `LineTo` | `"line_to"` | `x`, `y` | Adiciona uma linha reta do ponto atual até `(x, y)`. |
| `ArcTo` | `"arc_to"` | `x`, `y`, `width`, `height`, `start_angle`, `sweep_angle` | Adiciona um arco elíptico na caixa `(x, y, width, height)`; ângulos em **graus**. |
| `Close` | `"close"` | — | Fecha o subpath ativo de volta ao ponto inicial. |
| `DrawRect` | `"draw_rect"` | `x`, `y`, `width`, `height` | Adiciona um retângulo ao path ativo. |
| `DrawOval` | `"draw_oval"` | `x`, `y`, `width`, `height` | Adiciona uma elipse (oval) à caixa `(x, y, width, height)`. |

```python
from tempest_core import MoveTo, LineTo, ArcTo, Close, DrawRect, DrawOval

MoveTo(x=10.0, y=10.0)
LineTo(x=90.0, y=10.0)
ArcTo(x=0.0, y=0.0, width=100.0, height=100.0, start_angle=0.0, sweep_angle=90.0)
Close()
DrawRect(x=0.0, y=0.0, width=50.0, height=30.0)
DrawOval(x=0.0, y=0.0, width=50.0, height=50.0)
```

!!! note "`DrawRect` / `DrawOval` acumulam geometria, não pintam"
    Apesar do prefixo `Draw`, esses dois só **adicionam a forma ao path ativo** —
    nada aparece até um `FillCmd` ou `StrokeCmd` depois. `DrawText` é a exceção:
    ele pinta na hora.

### Comandos de pintura

| Comando | `kind` | Campos (padrão) | O que faz |
| --- | --- | --- | --- |
| `FillCmd` | `"fill"` | `color` | Preenche o path ativo com uma cor sólida e reseta o path. |
| `StrokeCmd` | `"stroke"` | `color`, `width` (`1.0`) | Pincela o contorno do path ativo e reseta o path. |
| `DrawText` | `"draw_text"` | `text`, `x`, `y`, `size` (`14.0`), `color` (`[0,0,0,1]`) | Desenha um texto na *baseline* em `(x, y)`. |

```python
from tempest_core import FillCmd, StrokeCmd, DrawText

FillCmd(color=[0.2, 0.7, 0.4, 1.0])
StrokeCmd(color=[0.0, 0.0, 0.0, 1.0], width=3.0)
DrawText(text="42", x=12.0, y=24.0, size=16.0, color=[0.1, 0.1, 0.1, 1.0])
```

!!! warning "Cor é sempre uma lista `[r, g, b, a]` de floats em `[0, 1]`"
    Todos os comandos com cor (`FillCmd`, `StrokeCmd`, `DrawText`) usam uma
    **lista** de quatro floats normalizados — nunca tupla, nunca `0–255`, nunca um
    objeto `Color`. É o que mantém o comando JSON-serializável direto por
    `model_dump()`. Vermelho puro opaco é `[1.0, 0.0, 0.0, 1.0]`.

## Superfícies avançadas & mídia do device

Aqui a folha delega a uma capacidade real da plataforma: um decodificador de
vídeo, um motor web, a câmera, o mapa. O core continua sem tocar em pixels — ele
só descreve *o que* embutir e *como* reagir aos eventos que a plataforma emite.

### `VideoPlayer`

Um player de vídeo embutido.

```python
from tempest_core import VideoPlayer

clipe = VideoPlayer(
    src="https://cdn.exemplo.com/intro.mp4",
    autoplay=True,
    loop=True,
    muted=True,      # autoplay silencioso — política comum de mobile/web
    controls=False,
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `src` | `str` | *(obrigatório)* | A fonte do vídeo — uma URL `http(s)` ou um caminho de asset. |
| `autoplay` | `bool` | `False` | Se a reprodução começa sozinha ao montar. |
| `loop` | `bool` | `False` | Se a reprodução reinicia ao chegar ao fim. |
| `controls` | `bool` | `True` | Se os controles de transporte da plataforma aparecem. |
| `muted` | `bool` | `False` | Se a trilha de áudio começa muda. |

### `WebView`

Uma web view embutida renderizando uma página remota.

```python
from tempest_core import WebView

docs = WebView(url="https://exemplo.com/ajuda", javascript_enabled=True)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `url` | `str` | *(obrigatório)* | A URL da página a carregar. |
| `javascript_enabled` | `bool` | `True` | Se a execução de JavaScript é permitida. |

### `CameraPreview`

Uma superfície de preview de câmera ao vivo, que **opcionalmente transmite
frames** para o app. Sem `on_frame` é só um preview. Com `on_frame`, o device
anexa um estágio `ImageAnalysis` (mantendo só o frame mais recente) e chama o
handler com um `CameraFrameEvent` no máximo a cada `frame_interval_ms`.

```python
from tempest_core import CameraPreview

async def on_frame(event):
    # reconstrua o array com tempestroid.vision.frame_array e rode a inferência
    ...

camera = CameraPreview(
    facing="back",
    on_frame=on_frame,
    frame_interval_ms=300,
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `facing` | `str` | `"back"` | Qual câmera usar (`"front"` ou `"back"`). |
| `on_frame` | `EventHandler \| None` | `None` | Handler chamado com um `CameraFrameEvent` por frame (limitado); sync ou `async`. |
| `frame_interval_ms` | `int` | `300` | Gap mínimo entre frames emitidos, em ms (ignorado sem `on_frame`). |

!!! tip "A limitação existe porque a inferência é mais lenta que a câmera"
    A câmera entrega dezenas de frames por segundo; um modelo on-device leva bem
    mais que isso por frame. O `frame_interval_ms` desacopla os dois — mantendo só
    o frame mais recente — para você não empilhar trabalho que nunca alcança o
    feed.

### `QrScanner`

Uma superfície de câmera ao vivo que lê QR/códigos de barras e reporta cada
resultado.

```python
from tempest_core import QrScanner

def on_scan(event):
    print("código lido:", event)

scanner = QrScanner(on_scan=on_scan)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `on_scan` | `EventHandler \| None` | `None` | Handler chamado com um `QrScanEvent` para cada código decodificado; sync ou `async`. |

### `MapView`

Um mapa embutido centralizado numa coordenada, com marcadores opcionais.

```python
from tempest_core import MapView

mapa = MapView(
    latitude=-23.5505,
    longitude=-46.6333,
    zoom=14.0,
    markers=[
        {"lat": -23.5505, "lng": -46.6333, "title": "São Paulo"},
    ],
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `latitude` | `float` | `0.0` | A latitude do centro do mapa, em graus. |
| `longitude` | `float` | `0.0` | A longitude do centro do mapa, em graus. |
| `zoom` | `float` | `12.0` | O nível de zoom do mapa. |
| `markers` | `list[dict[str, Any]]` | `[]` | Descritores de marcador JSON-serializáveis (cada um um dict, ex. `{"lat": …, "lng": …, "title": …}`); a lista cruza a ponte como está. |

!!! note "Marcadores são dicts simples, não widgets"
    Cada marcador é um `dict` JSON-serializável que o renderizador nativo
    interpreta — o formato exato (`lat` / `lng` / `title` …) é um contrato de
    dados, não uma sub-árvore de widgets.

### Efeitos: `Blur`, `BackdropFilter`

Dois *wrappers* que borram — a diferença é **o quê**. O `Blur` borra o próprio
filho; o `BackdropFilter` borra as **camadas atrás** do filho (um alias semântico,
para vidro fosco sobre conteúdo). Os dois têm os mesmos campos.

```python
from tempest_core import Blur, BackdropFilter, Image, Text

fosco = Blur(radius=12.0, child=Image(src="assets/foto.jpg"))
vidro = BackdropFilter(radius=16.0, child=Text(value="Sobreposto"))
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `radius` | `float` | `8.0` | O raio do blur, em pixels lógicos. |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |

!!! info "`Blur` vs. `BackdropFilter`"
    Mesma mecânica, alvos diferentes: use `Blur` para desfocar **o conteúdo do
    filho** (uma foto censurada, um placeholder) e `BackdropFilter` para desfocar
    **o que está atrás** do filho (uma barra translúcida sobre a página).

### Recorte: `ClipShape`, `ClipPath`

O `ClipPath` recorta seu filho a uma forma predefinida, escolhida pelo enum
`ClipShape`.

| `ClipShape` | Valor | O que faz |
| --- | --- | --- |
| `CIRCLE` | `"circle"` | Recorta a um **círculo** inscrito na caixa (usa o lado menor como diâmetro numa caixa não quadrada). Ótimo para avatares. |
| `ROUNDED_RECT` | `"rounded_rect"` | Recorta a um retângulo de cantos arredondados, usando `radius` como raio do canto. Raio `0` ≈ retângulo comum. |
| `OVAL` | `"oval"` | Recorta a uma **elipse** que preenche a largura e altura totais da caixa (estica; numa caixa não quadrada vira um oval, não um círculo). |

```python
from tempest_core import ClipPath, ClipShape, Image

avatar = ClipPath(
    shape=ClipShape.CIRCLE,
    child=Image(src="assets/perfil.jpg"),
)

cartao = ClipPath(
    shape=ClipShape.ROUNDED_RECT,
    radius=16.0,
    child=Image(src="assets/banner.jpg"),
)
```

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `shape` | `ClipShape` | `ROUNDED_RECT` | A forma de recorte. |
| `radius` | `float` | `8.0` | O raio do canto para `ROUNDED_RECT`, em pixels lógicos. |
| `child` | `Widget \| None` | `None` | O widget envolvido (opcional). |

!!! warning "`CIRCLE` vs. `OVAL` numa caixa não quadrada"
    Os dois viram círculo quando a caixa é quadrada. Numa caixa retangular, o
    `CIRCLE` usa o **lado menor** (fica redondo, centralizado) e o `OVAL`
    **estica** para preencher os dois eixos (fica ovalado). O `radius` só tem
    efeito em `ROUNDED_RECT`.

## Recapitulando

- **Imagem & ícones**: `Image` (bitmap), `Icon` (path vetorial) e `Svg`
  (documento vetorial) trazem conteúdo para a tela; `ImageFit`
  (`CONTAIN` / `COVER` / `FILL` / `NONE`) decide como ele escala na caixa.
- **`Canvas` é um modelo de desenho declarativo**: uma `list[DrawCommand]` que os
  renderizadores repetem. A ordem é a semântica e cada forma é
  `geometria → pintura`.
- **Vocabulário de comandos**: construção de path (`MoveTo`, `LineTo`, `ArcTo`,
  `Close`, `DrawRect`, `DrawOval`) + pintura (`FillCmd`, `StrokeCmd`, `DrawText`).
  Uma linha = `MoveTo` + `LineTo` + `StrokeCmd`; uma barra = `DrawRect` +
  `FillCmd`. Cores são listas `[r, g, b, a]` em `[0, 1]`.
- **Superfícies do device**: `VideoPlayer`, `WebView`, `CameraPreview` (com
  `on_frame` limitado por `frame_interval_ms`), `QrScanner`, `MapView`.
- **Efeitos e recorte**: `Blur` (o filho) vs. `BackdropFilter` (atrás do filho);
  `ClipPath` recorta a `ClipShape.CIRCLE` / `ROUNDED_RECT` / `OVAL`.

Todos os campos e formas são apenas dados JSON-serializáveis — veja os tipos
completos na [Referência da API](../reference.md).
