# Pesquisa

O kit de **pesquisa / ciência de dados** é a camada que um pesquisador acadêmico
usa para mostrar o resultado de um modelo ONNX /
[`ort-vision-sdk`](https://github.com/mauriciobenjamin700/ort-vision-sdk) de ponta
a ponta: cartões de métrica num dashboard, gráficos simples (linha / barra),
caixas de detecção sobre uma imagem e o fluxo *escolher imagem → mostrar
resultado*. Tudo aqui **abaixa para primitivas que já existem** (composição) ou
para uma **lista de comandos do `Canvas`** (gráficos / overlays) — nenhum campo
novo de `Style`, nenhum resolver novo e **nenhum comando de desenho novo** é
introduzido. 🔬

!!! info "O que você aprende aqui"
    - Como `MetricCard` / `StatCard` compõem o **`Card` (H3) + `Stat` (H4)** sem
      inventar primitiva.
    - Como a função pura `confidence_scheme` mapeia confiança → status e alimenta
      tanto o `ConfidenceBadge` quanto o `DetectionOverlay`.
    - Como `LineChart` / `BarChart` emitem uma **lista de comandos determinística**
      do `Canvas` usando só o vocabulário de desenho existente.
    - Por que um `DetectionBox` é **`xyxy` normalizado em `[0, 1]`** e como ele vira
      caixas sobre uma `Image`.
    - Como o `ResultView` arranja o fluxo picker → resultado sem guardar estado.

## Cartões de métrica

O bloco de topo de um dashboard: um número grande com um rótulo e uma tendência.
Nada aqui é uma primitiva nova — os cartões **compõem** o `Card` e o `Stat`, e o
selo de confiança compõe o `Badge`. A cor de status sai toda de uma única função
pura, `confidence_scheme`.

### `MetricCard`

Uma métrica de dashboard dentro de um cartão temático: rótulo, valor e uma
tendência opcional tingida (`success` para cima, `error` para baixo). No caso
mínimo você passa só `label` e `value`:

```python
from tempest_core import MetricCard

acuracia = MetricCard(label="Acurácia", value="92%", delta="+3%", delta_up=True)
```

Precisa de um mini-gráfico ao lado do número? O slot `trailing` aceita qualquer
widget — por exemplo um `LineChart` fazendo as vezes de *sparkline*:

```python
from tempest_core import ChartSeries, LineChart, MetricCard

spark = LineChart(
    series=[ChartSeries(points=[0.80, 0.86, 0.89, 0.92])],
    width=96.0,
    height=40.0,
)
acuracia = MetricCard(
    label="Acurácia",
    value="92%",
    delta="+3%",
    delta_up=True,
    color_scheme="success",
    trailing=spark,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | A legenda da métrica (mostrada apagada/muted). |
| `value` | `str` | `""` | O valor da métrica (grande e proeminente). |
| `delta` | `str \| None` | `None` | A linha de tendência (ex.: `"+12%"`); `None` esconde. |
| `delta_up` | `bool` | `True` | Se o delta é positivo (tingido de `success`) ou negativo (`error`). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que a superfície do cartão tinge. |
| `variant` | `CardVariant` | `ELEVATED` | O tratamento da superfície (elevated / filled / outlined). |
| `trailing` | `Widget \| None` | `None` | Um widget opcional à direita do bloco de stat (sparkline, ícone…). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície e o stat. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport (aceito por paridade; **não usado** aqui). |

!!! note "É `Card` + `Stat`, não uma primitiva nova"
    O `render` do `MetricCard` monta um `Stat` (o bloco rótulo/valor/delta da H4) e
    o embrulha num `Card` (a superfície da H3). Quando `trailing` está setado, o
    stat e o widget extra entram num `Row` centralizado; senão o stat é o corpo
    direto. Nada além dessas duas primitivas compostas — o cartão herda de graça
    todo o comportamento de superfície e de tokens delas.

### `StatCard`

Um **preset compacto** do `MetricCard`: exatamente o mesmo componente, só que com a
superfície mais densa por padrão (`filled` em vez de `elevated`). Serve para uma
grade apertada de números:

```python
from tempest_core import StatCard

total = StatCard(label="Imagens", value="1.024")
```

#### Props

O `StatCard` **herda todos os props do `MetricCard`** — a única diferença é o
padrão de `variant`.

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `variant` | `CardVariant` | `FILLED` | A superfície densa do preset (sobreponha para retunar). |
| *(demais)* | — | *(iguais ao `MetricCard`)* | `label`, `value`, `delta`, `delta_up`, `color_scheme`, `trailing`, `theme`, `media`. |

!!! tip "Quando cada um"
    Use `MetricCard` (elevado) para os KPIs de destaque de uma tela; use `StatCard`
    (preenchido, mais apertado) para uma fileira/grade de números secundários que
    não devem competir por atenção. Como `StatCard` **é** um `MetricCard`, todo
    prop continua valendo — inclusive dá para sobrepor `variant` de volta para
    `ELEVATED` se quiser.

### `ConfidenceBadge`

Uma pílula de status que mostra a confiança de um modelo, colorida por limiar.
Compõe o `Badge` (H4), escolhe o `color_scheme` via `confidence_scheme` e rotula
como uma porcentagem arredondada. Um `label` opcional vira prefixo:

```python
from tempest_core import ConfidenceBadge

# Pílula verde "gato 92%" (>= 80% => success).
confianca = ConfidenceBadge(confidence=0.92, label="gato")

# Sem rótulo, só a porcentagem — e com limiares próprios.
bruta = ConfidenceBadge(confidence=0.63, high=0.9, mid=0.6)  # "63%", amber
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `confidence` | `float` | *(obrigatório)* | A confiança do modelo em `[0, 1]`. |
| `label` | `str` | `""` | Um prefixo opcional (ex.: a classe prevista) antes da porcentagem. |
| `high` | `float` | `0.8` | O limiar de `success` passado ao `confidence_scheme`. |
| `mid` | `float` | `0.5` | O limiar de `warning` passado ao `confidence_scheme`. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a pílula. **Não entra na IR.** |

!!! note "Variante `SUBTLE` por acessibilidade"
    O selo pinta com `BadgeVariant.SUBTLE` (o par tonal *container*, seguro para
    WCAG-AA), **não** com `SOLID`. Um `SOLID` pintaria branco sobre o papel de
    status saturado — `success` (~3.02) e `warning` (~4.0) **falham** o contraste
    AA. A escolha espelha a decisão da H4 e mantém o selo legível em qualquer
    família de status.

### `confidence_scheme`

A função pura por trás de toda cor de confiança do kit. É o clássico semáforo:
`>= high` é verde (`"success"`), `>= mid` é âmbar (`"warning"`), abaixo é vermelho
(`"error"`). Como é pura e determinística, todo componente conduzido por confiança
(selo, caixa de detecção) colore de forma consistente:

```python
from tempest_core import confidence_scheme

confidence_scheme(0.92)  # "success"
confidence_scheme(0.63)  # "warning"
confidence_scheme(0.31)  # "error"
confidence_scheme(0.63, high=0.9, mid=0.6)  # "warning" (limiares próprios)
```

#### Assinatura

`confidence_scheme(conf: float, *, high: float = 0.8, mid: float = 0.5) -> str`

| Parâmetro | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `conf` | `float` | *(obrigatório)* | O score de confiança, tipicamente em `[0, 1]`. |
| `high` | `float` | `0.8` | Limiar **inclusivo** a partir do qual o score lê como alto (`"success"`). |
| `mid` | `float` | `0.5` | Limiar **inclusivo** a partir do qual lê como médio (`"warning"`); abaixo, baixo (`"error"`). |

!!! info "Limiares inclusivos, comparação em cascata"
    A comparação é `conf >= high` primeiro, depois `conf >= mid`, senão `error` —
    logo os limiares são **inclusivos** (exatamente `0.8` com o padrão já é
    `success`). Passe seus próprios `high` / `mid` para recalibrar sem trocar de
    função: o `ConfidenceBadge` e o `DetectionOverlay` repassam esses dois nomes
    direto para cá.

## Gráficos sobre o Canvas

Os gráficos não são widgets novos: cada um **abaixa para um `Canvas`** carregando
uma lista de comandos de desenho. A lista é **determinística** para uma entrada
fixa — a suíte de conformância fixa a sequência exata — e usa só o vocabulário de
desenho que já existe. Os dados chegam num `ChartSeries` congelado, então um mesmo
gráfico plota várias séries nomeadas e coloridas.

### `ChartSeries`

Uma única série de dados nomeada e (opcionalmente) colorida. Um gráfico recebe uma
**lista** desses em vez de um `list[float]` cru, para plotar várias séries de uma
vez, cada uma com seu rótulo e — se quiser — seu próprio `color_scheme`. É um
modelo **congelado** (`frozen`):

```python
from tempest_core import ChartSeries

loss = ChartSeries(points=[0.90, 0.42, 0.31, 0.18], label="loss", color_scheme="error")
acc = ChartSeries(points=[0.55, 0.71, 0.84, 0.92], label="acc", color_scheme="success")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `points` | `list[float]` | `[]` | Os valores-y da série, na ordem de plotagem (um por posição x). |
| `label` | `str` | `""` | Um rótulo opcional (ex.: para legenda; carregado, não desenhado pelos gráficos mínimos). |
| `color_scheme` | `str \| None` | `None` | A família de papéis M3 da série; `None` cai na paleta rotativa do gráfico. |

!!! note "Paleta rotativa quando `color_scheme` é `None`"
    Quando uma série não nomeia sua cor, o gráfico escolhe da paleta rotativa
    (`primary` → `secondary` → `tertiary` → `error` → `success` → `warning` →
    `info`) pelo **índice** da série. Assim duas séries sem cor nunca saem iguais, e
    você só precisa setar `color_scheme` quando a cor importa semanticamente.

### `LineChart`

Um gráfico de linhas multi-série desenhado sobre um `Canvas`. Cada `ChartSeries`
vira uma polilinha conectada sobre um plot emoldurado, com gridlines no eixo Y e
rótulos de tick alinhados à direita:

```python
from tempest_core import ChartSeries, LineChart

curva = LineChart(
    series=[
        ChartSeries(
            points=[0.90, 0.42, 0.31, 0.18], label="loss", color_scheme="error"
        ),
        ChartSeries(
            points=[0.55, 0.71, 0.84, 0.92], label="acc", color_scheme="success"
        ),
    ],
    width=320.0,
    height=200.0,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `series` | `list[ChartSeries]` | `[]` | As séries a plotar (cada uma sua polilinha + cor). |
| `width` | `float` | `320.0` | A largura do canvas, em pixels lógicos. |
| `height` | `float` | `200.0` | A altura do canvas, em pixels lógicos. |
| `color_scheme` | `str` | `"primary"` | A família M3 padrão de uma série sem cor própria. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens viram as cores concretas. **Não entra na IR.** |

!!! note "Vocabulário de desenho — não existe `DrawLine`"
    Uma linha é `MoveTo` + uma sequência de `LineTo` + um único `StrokeCmd`; os
    eixos e as gridlines saem do mesmo trio. Os rótulos do eixo Y são `DrawText`
    (ancorado na baseline, **sem** campo de alinhamento) — para alinhá-los à direita
    o engine desloca a âncora para a esquerda estimando a largura do texto. Nenhum
    comando de desenho novo foi criado, e a lista final é determinística para
    entrada fixa.

### `BarChart`

Um gráfico de barras sobre um `Canvas`. Aceita ou uma lista de `ChartSeries` (a
**primeira** série vira as barras) ou, para o caso trivial de série única, uma
`values: list[float]` simples com `labels` opcionais:

```python
from tempest_core import BarChart

# Caminho simples: uma lista de valores (+ rótulos).
barras = BarChart(values=[3.0, 5.0, 2.0], labels=["a", "b", "c"])
```

```python
from tempest_core import BarChart, ChartSeries

# Caminho tipado: a primeira série vira as barras, com cor explícita.
barras = BarChart(
    series=[ChartSeries(points=[3.0, 5.0, 2.0], color_scheme="tertiary")],
    labels=["a", "b", "c"],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `series` | `list[ChartSeries]` | `[]` | As séries (a **primeira** é plotada como barras). Opcional se `values` for dado. |
| `values` | `list[float]` | `[]` | Uma lista de valores de série única (usada quando `series` está vazio). |
| `labels` | `list[str]` | `[]` | Rótulos opcionais do eixo X para as barras. |
| `width` | `float` | `320.0` | A largura do canvas, em pixels lógicos. |
| `height` | `float` | `200.0` | A altura do canvas, em pixels lógicos. |
| `color_scheme` | `str` | `"primary"` | A família M3 padrão das barras (se a série não nomear a sua). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens viram as cores concretas. **Não entra na IR.** |

!!! note "Barra é `DrawRect` + `FillCmd`; `series` vence `values`"
    Cada barra é um `DrawRect` seguido de um `FillCmd` sobre o mesmo plot
    emoldurado dos eixos. Quando **os dois** `series` e `values` são passados, o
    `series` ganha (usa-se o `points` e o `color_scheme` da primeira série);
    `values` só entra quando `series` está vazio. A baseline sempre inclui o `0`,
    então as barras têm um chão com significado. A sequência de comandos é
    determinística — a suíte de conformância a fixa.

## Overlay de detecção

Um resultado de detecção de objetos é uma imagem com caixas por cima. O engine
**não** depende do `ort-vision-sdk`: as caixas chegam normalizadas em `[0, 1]`, o
que as deixa independentes de resolução, e o adaptador de um resultado `Detection`
real para `DetectionBox` mora do lado do tempestroid, não aqui.

### `DetectionBox`

Uma caixa de detecção **`xyxy` normalizada em `[0, 1]`** — as coordenadas são
frações da largura/altura do canvas (`0` = esquerda/topo, `1` = direita/baixo),
multiplicadas pelo tamanho em pixels só na hora de desenhar. É um modelo
**congelado** (`frozen`):

```python
from tempest_core import DetectionBox

gato = DetectionBox(x1=0.10, y1=0.20, x2=0.50, y2=0.60, name="gato", conf=0.93)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `x1` | `float` | *(obrigatório)* | A borda esquerda como fração da largura (`[0, 1]`). |
| `y1` | `float` | *(obrigatório)* | A borda de topo como fração da altura (`[0, 1]`). |
| `x2` | `float` | *(obrigatório)* | A borda direita como fração da largura (`[0, 1]`). |
| `y2` | `float` | *(obrigatório)* | A borda de baixo como fração da altura (`[0, 1]`). |
| `name` | `str` | `""` | Um rótulo de classe opcional desenhado ao lado da caixa. |
| `conf` | `float` | `1.0` | A confiança em `[0, 1]` (dita a cor da caixa e a porcentagem do rótulo). |

!!! tip "Normalizado = resolução-independente"
    Como as coordenadas são frações, a **mesma** caixa desenha certo em qualquer
    tamanho de canvas — troque o `width`/`height` do overlay e as caixas
    acompanham. É a convenção `xyxy` normalizada comum, mas sem acoplar o engine a
    nenhuma SDK de visão. Escreva um adaptador `det.box.xyxy` → `DetectionBox` no
    seu app.

### `DetectionOverlay`

Uma imagem com caixas de detecção por cima. Abaixa para um `Stack` de uma `Image`
base (`fit=COVER`) sob um `Canvas` de overlay; cada `DetectionBox` é multiplicada
pelo tamanho do canvas e desenhada como um retângulo traçado, colorido por
`confidence_scheme`, com uma legenda `"{name} {conf:.0%}"`:

```python
from tempest_core import DetectionBox, DetectionOverlay

overlay = DetectionOverlay(
    image_src="foto.jpg",
    boxes=[
        DetectionBox(x1=0.10, y1=0.20, x2=0.50, y2=0.60, name="gato", conf=0.93),
        DetectionBox(x1=0.55, y1=0.30, x2=0.90, y2=0.80, name="cão", conf=0.61),
    ],
    width=320.0,
    height=320.0,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `image_src` | `str` | *(obrigatório)* | A fonte da imagem (URL ou caminho de asset) a emoldurar. |
| `boxes` | `list[DetectionBox]` | `[]` | As caixas normalizadas a desenhar. |
| `width` | `float` | `320.0` | A largura do canvas/imagem, em pixels lógicos. |
| `height` | `float` | `320.0` | A altura do canvas/imagem, em pixels lógicos. |
| `high` | `float` | `0.8` | O limiar de `success` passado ao `confidence_scheme`. |
| `mid` | `float` | `0.5` | O limiar de `warning` passado ao `confidence_scheme`. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens dão a cor do rótulo. **Não entra na IR.** |

!!! note "`Stack(Image + Canvas)` — cada caixa é traço + rótulo, sem comando novo"
    O overlay é um `Stack` da `Image` (`COVER`) sob um `Canvas`. Cada caixa vira um
    `DrawRect` + `StrokeCmd` (na cor de `confidence_scheme(box.conf, high=..., mid=...)`)
    e, quando há legenda, um pequeno fundo (`DrawRect` + `FillCmd`) mais o texto
    `DrawText` no par `on_<scheme>` para contraste. Cada caixa colore consistente
    com o `ConfidenceBadge` porque as duas passam pela **mesma** função. Nenhum
    comando de desenho novo é introduzido.

## Fluxo selecionar → resultado

O último elo: escolher uma imagem, rodar a inferência e mostrar o resultado. O
componente **não guarda estado** — o app é dono da inferência e monta o widget de
resultado; o `ResultView` só arranja o picker e o resultado numa coluna.

### `ResultView`

Empilha um `ImagePicker` sobre um slot `result` opcional — o widget que o app
constrói a partir da saída do modelo (um `DetectionOverlay`, um `MetricCard`, um
`ConfidenceBadge` ou um gráfico):

```python
from tempest_core import DetectionBox, DetectionOverlay, ResultView


def ao_escolher(uri: str) -> None:
    """Roda a inferência e guarda o resultado no estado do app."""
    ...  # o app roda o modelo e faz set_state com o widget montado


view = ResultView(
    label="Envie uma foto",
    on_pick=ao_escolher,
    result=DetectionOverlay(
        image_src="foto.jpg",
        boxes=[DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="gato", conf=0.93)],
    ),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O URI da imagem escolhida (repassado ao picker; `""` até escolher). |
| `label` | `str` | `""` | Um título opcional acima do picker. |
| `on_pick` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com o URI da imagem escolhida na seleção. |
| `result` | `Widget \| None` | `None` | O widget de resultado abaixo do picker; `None` mostra só o picker. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens dão o espaçamento. **Não entra na IR.** |

!!! note "O app é dono da inferência"
    O `render` monta um `Column` de um `ImagePicker` e, quando setado, o `result`.
    O componente não roda modelo nenhum: você trata o `on_pick`, roda a inferência,
    monta o widget de resultado (overlay, cartão, gráfico…) e o passa de volta em
    `result` num rebuild. Isso mantém o `ResultView` sem estado e reusável para
    **qualquer** tarefa de visão — classificação, detecção ou segmentação.

## Recapitulando

- **Tudo compõe ou desenha** — nenhum componente de pesquisa inventa primitiva,
  campo de `Style`, resolver ou comando de desenho novo.
- **Cartões**: `MetricCard` = `Card` (H3) + `Stat` (H4); `StatCard` é o mesmo,
  preset `filled` compacto; `ConfidenceBadge` = `Badge` (H4) `SUBTLE`, colorido por
  `confidence_scheme`.
- **`confidence_scheme(conf, *, high=0.8, mid=0.5)`** é a função pura e
  determinística por trás de toda cor de confiança: `>= high` → `success`,
  `>= mid` → `warning`, senão `error`.
- **Gráficos**: `LineChart` / `BarChart` abaixam para uma lista de comandos
  **determinística** do `Canvas` — linha = `MoveTo` + `LineTo` + `StrokeCmd`, barra
  = `DrawRect` + `FillCmd`, sem `DrawLine`. Os dados vêm num `ChartSeries`
  congelado; no `BarChart`, `series` vence `values`.
- **Detecção**: `DetectionBox` é `xyxy` normalizado em `[0, 1]`; o
  `DetectionOverlay` é um `Stack(Image COVER + Canvas)` que colore cada caixa pela
  mesma `confidence_scheme`, sem depender do `ort-vision-sdk`.
- **`ResultView`** arranja `ImagePicker` + slot `result` sem estado — o app roda a
  inferência e monta o resultado.
