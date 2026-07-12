# Indicadores & listas

Esta categoria reúne dois grupos de widgets de feedback e de dados. Os
**indicadores** — **`ProgressBar`** e **`Spinner`** — são folhas não interativas
(sem eventos) que comunicam progresso ou atividade. As **listas virtualizadas**
— **`LazyColumn`**, **`LazyRow`**, **`LazyGrid`**, **`SectionList`** e o wrapper
**`RefreshControl`** — declaram um `item_count` mais um `item_builder`, e só
materializam a **janela visível** de itens na IR. 🚀

!!! info "O que você aprende aqui"
    - Como um `ProgressBar` alterna entre **determinado** e **indeterminado**, e o que o `Spinner` sempre é.
    - Como o `color_scheme` escolhe a família de cor do acento em cada indicador.
    - Como uma lista **virtualiza**: `item_count` + `item_builder` + a **janela** de tamanho `DEFAULT_WINDOW_SIZE`.
    - Por que o primeiro mount já vem com conteúdo, e como a aplicação **desliza a janela** num scroll.
    - Como funcionam `on_end_reached` / `end_reached_threshold` (paginação), o pull-to-refresh e as seções do `SectionList`.

## Indicadores de progresso

Os indicadores são **widgets folha não interativos**: não têm handlers de evento,
só carregam props que o renderizador pinta contra o tema ativo. Use-os para
sinalizar que algo está acontecendo — uma barra para progresso mensurável, um
spinner para atividade de duração desconhecida.

### `ProgressBar`

Uma barra de progresso horizontal. Ela mostra ou uma **fração determinada** em
`[0.0, 1.0]`, ou uma barra **indeterminada** (em loop) quando a duração é
desconhecida:

```python
from tempest_core import ProgressBar

# Determinada: 42% concluído.
carregando = ProgressBar(value=0.42)

# Indeterminada: trabalho de duração desconhecida (value é ignorado).
processando = ProgressBar(indeterminate=True)
```

O acento (o trecho preenchido da trilha) é pintado pela família de papéis do
`color_scheme`:

```python
from tempest_core import ProgressBar

upload = ProgressBar(value=0.7, color_scheme="secondary")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `float` | `0.0` | A fração concluída em `[0.0, 1.0]` (ignorada quando `indeterminate` está setado). |
| `indeterminate` | `bool` | `False` | Quando `True`, renderiza uma barra em loop sem valor fixo (duração desconhecida). |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que o renderizador pinta o acento da barra. |

!!! note "`value` é validado no range `[0.0, 1.0]`"
    O campo `value` tem `ge=0.0` e `le=1.0` — passar algo fora desse intervalo é
    erro de validação Pydantic na construção, não um clamp silencioso. Quando
    `indeterminate=True`, o `value` é simplesmente ignorado pelo renderizador.

!!! tip "Determinado quando você sabe a fração; indeterminado quando não sabe"
    Prefira `value=` sempre que puder medir o progresso (download com tamanho
    conhecido, passo N de M). Reserve `indeterminate=True` para espera opaca — é o
    que evita uma barra que fica "presa" em 10% porque você não sabe o total.

### `Spinner`

Um indicador de atividade circular — **sempre indeterminado**. Não tem `value`;
existe só para dizer "algo está rodando". O `size` é o diâmetro em pixels
lógicos, ou `None` para o padrão do renderizador:

```python
from tempest_core import Spinner

# Diâmetro padrão do renderizador.
ocupado = Spinner()

# Spinner maior, na cor de erro.
recarregando = Spinner(size=48.0, color_scheme="error")
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `size` | `float \| None` | `None` | O diâmetro do indicador em pixels lógicos, ou `None` para o padrão do renderizador. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que o renderizador pinta o acento do spinner. |

!!! info "O `Spinner` não tem `value` nem `indeterminate`"
    Diferente do `ProgressBar`, o spinner é circular e **sempre** em loop — não
    existe estado "determinado" para ele. Se você precisa mostrar uma fração,
    use o `ProgressBar`.

## Listas virtualizadas

As listas são as primitivas de container **virtual** do framework. Em vez de
declarar uma lista materializada de filhos, elas declaram um `item_count` mais um
`item_builder(index) -> Widget`. Só a **janela visível** de itens chega à IR: o
renderizador reporta o `offset` de scroll via `ScrollEvent`, a aplicação
recalcula a janela `[start, end)` e reconstrói, e o diff por chave (chave do item
= `str(index)`) transforma um deslize de janela numa sequência mínima de
remove/reorder/insert.

O `item_builder` é um callable Python que materializa o widget na **mesma**
thread do `build` — ele nunca cruza a fronteira nativa. O serializador o descarta;
o device recebe `item_count` mais os filhos da janela já materializados e renderiza
nativamente (Compose `LazyColumn`).

### `DEFAULT_WINDOW_SIZE`

A constante que define **quantos itens** entram na janela visível inicial quando
uma lista não declara um `window` explícito:

```python
from tempest_core import DEFAULT_WINDOW_SIZE

print(DEFAULT_WINDOW_SIZE)  # 20
```

`DEFAULT_WINDOW_SIZE` vale **`20`**. É o valor padrão do campo `window_size` de
toda lista (e de cada `SectionHeader`). Ele mantém o primeiro mount barato — o
device renderiza esses 20 itens, não os `item_count` totais — enquanto ainda
mostra conteúdo imediatamente.

!!! info "A janela de virtualização, em uma frase"
    A janela é `window` quando setada (a aplicação a desliza em resposta a um
    `ScrollEvent` via `App.slide_window`), senão o padrão inicial
    `[0, min(window_size, item_count)]`. É isso que faz o **primeiro** mount ser
    não-vazio: `build` materializa `window_size` itens imediatamente, sem esperar
    um evento de scroll. A virtualização é preservada — só a janela é construída,
    nunca todos os `item_count` itens.

### `LazyColumn`

Uma lista virtualizada vertical (Compose `LazyColumn`). Declara um `item_count` e
um `item_builder` em vez de filhos materializados; só a janela visível é
construída na IR:

```python
from tempest_core import LazyColumn, Text

def build_item(index: int) -> Text:
    return Text(content=f"Item {index}")

lista = LazyColumn(item_count=10_000, item_builder=build_item)
```

Esse `LazyColumn` com 10 mil itens materializa só os primeiros `20`
(`DEFAULT_WINDOW_SIZE`) no primeiro mount. Ele emite `ScrollEvent` ao rolar,
`RefreshEvent` no pull-to-refresh e `EndReachedEvent` ao passar de
`end_reached_threshold`:

```python
from tempest_core import LazyColumn, Text

async def carregar_mais(event) -> None:  # (1)!
    ...

lista = LazyColumn(
    item_count=10_000,
    item_builder=lambda i: Text(content=f"Item {i}"),
    end_reached_threshold=0.8,
    on_end_reached=carregar_mais,
)
```

1. O handler pode ser **síncrono ou `async`** — o runtime agenda os awaitables no
   event loop. Ele recebe um `EndReachedEvent` (veja [Referência da API](../reference.md)).

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `item_count` | `int` | *(obrigatório)* | O número total de itens na lista. |
| `item_builder` | `ItemBuilder` | *(obrigatório)* | Factory que constrói o item no índice dado. Vive só no lado Python; nunca serializado. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | Quantos itens entram na janela inicial quando `window` está sem valor. |
| `window` | `tuple[int, int] \| None` | `None` | A janela visível `[start, end)` atual, ou `None` para o padrão inicial. A aplicação a desliza num scroll. |
| `end_reached_threshold` | `float` | `0.8` | A fração `0..1` do scroll total em que `on_end_reached` dispara. |
| `refreshing` | `bool` | `False` | Se o spinner de pull-to-refresh está ativo. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Handler opcional para eventos de scroll. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Handler opcional para pull-to-refresh. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Handler opcional disparado perto do fim da lista. |

!!! warning "Não materialize a lista inteira você mesmo"
    O ponto da virtualização é `item_builder` construir **um** item por índice, sob
    demanda. Passar `item_count` gigantesco é ótimo — só a janela é construída. Mas
    montar toda a lista de widgets antes e devolvê-los pelo builder joga fora a
    virtualização e incha a IR.

!!! note "A aplicação desliza a `window`, o widget não"
    O `LazyColumn` não se move sozinho. Quando o renderizador reporta um
    `ScrollEvent`, a aplicação chama `App.slide_window` para calcular a nova
    `[start, end)` e reconstruir com a `window` atualizada. O widget só descreve
    qual janela materializar; o movimento vem de fora.

### `LazyRow`

O análogo horizontal do `LazyColumn` (Compose `LazyRow`): **contrato idêntico**,
itens dispostos e rolados da esquerda para a direita.

```python
from tempest_core import LazyRow, Text

carrossel = LazyRow(
    item_count=500,
    item_builder=lambda i: Text(content=f"Slide {i}"),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `item_count` | `int` | *(obrigatório)* | O número total de itens na lista. |
| `item_builder` | `ItemBuilder` | *(obrigatório)* | Factory que constrói o item no índice dado. Vive só no lado Python; nunca serializado. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | Quantos itens entram na janela inicial quando `window` está sem valor. |
| `window` | `tuple[int, int] \| None` | `None` | A janela visível `[start, end)` atual, ou `None` para o padrão inicial. |
| `end_reached_threshold` | `float` | `0.8` | A fração `0..1` do scroll total em que `on_end_reached` dispara. |
| `refreshing` | `bool` | `False` | Se o spinner de pull-to-refresh está ativo. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Handler opcional para eventos de scroll. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Handler opcional para pull-to-refresh. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Handler opcional disparado perto do fim da lista. |

!!! tip "Mesma API, eixo diferente"
    Se você já sabe usar `LazyColumn`, já sabe usar `LazyRow` — os campos e
    eventos são exatamente os mesmos. A única diferença é a orientação do scroll.

### `LazyGrid`

Uma grade virtualizada (Compose `LazyVerticalGrid`). Dispõe os itens
virtualizados num número fixo de `columns`, rolando verticalmente. **Não tem
pull-to-refresh** — envolva com um `RefreshControl` se precisar:

```python
from tempest_core import LazyGrid, Text

galeria = LazyGrid(
    item_count=1_000,
    item_builder=lambda i: Text(content=f"Foto {i}"),
    columns=3,
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `item_count` | `int` | *(obrigatório)* | O número total de itens na grade. |
| `item_builder` | `ItemBuilder` | *(obrigatório)* | Factory que constrói o item no índice dado. Vive só no lado Python; nunca serializado. |
| `columns` | `int` | `2` | O número de colunas da grade. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | Quantos itens entram na janela inicial quando `window` está sem valor. |
| `window` | `tuple[int, int] \| None` | `None` | A janela visível `[start, end)` atual, ou `None` para o padrão inicial. |
| `end_reached_threshold` | `float` | `0.8` | A fração `0..1` do scroll total em que `on_end_reached` dispara. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Handler opcional para eventos de scroll. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Handler opcional disparado perto do fim da grade. |

!!! warning "A grade não tem `on_refresh` nem `refreshing`"
    Diferente de `LazyColumn` / `LazyRow`, o `LazyGrid` não expõe pull-to-refresh.
    Para o gesto de puxar-para-atualizar numa grade, envolva-a num `RefreshControl`
    (veja abaixo).

### `SectionHeader`

Uma seção de um `SectionList`: um cabeçalho mais itens virtualizados. **Não é um
widget** — é um value object **congelado** (`frozen=True`) que descreve como
construir o cabeçalho fixo de uma seção e seus itens. Cada seção tem sua própria
janela de virtualização:

```python
from tempest_core import SectionHeader, Text

secao_a = SectionHeader(
    title="A",
    item_count=200,
    item_builder=lambda i: Text(content=f"A-{i}"),
    header_builder=lambda: Text(content="Seção A"),
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | *(obrigatório)* | Um rótulo estável para a seção (usado como chave e no cabeçalho). |
| `item_count` | `int` | *(obrigatório)* | O número de itens nesta seção. |
| `item_builder` | `ItemBuilder` | *(obrigatório)* | Factory que constrói o item num índice local à seção. |
| `header_builder` | `HeaderBuilder` | *(obrigatório)* | Factory que constrói o cabeçalho fixo desta seção. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | Quantos itens entram na janela inicial desta seção quando `window` está sem valor. |
| `window` | `tuple[int, int] \| None` | `None` | A janela visível `[start, end)` atual desta seção, ou `None` para o padrão inicial. |

!!! note "A seção é congelada; a aplicação a substitui via `model_copy`"
    Como `SectionHeader` é `frozen=True`, deslizar sua janela não muta a seção — a
    aplicação **substitui** a seção (frozen) por uma cópia com a nova `window` via
    `model_copy`. Cada item materializado é keyed `"sec:<title>:<index>"` e o
    cabeçalho `"sec:<title>:header"`, então toda child do `SectionList` tem chave
    globalmente única para o diff por chave.

### `SectionList`

Uma lista virtualizada seccionada com cabeçalhos fixos (sticky). Cada
`SectionHeader` declara seu cabeçalho mais seus próprios itens virtualizados. O
renderizador fixa os cabeçalhos (Compose `stickyHeader`; o simulador Qt fixa um
label acima da área de scroll):

```python
from tempest_core import SectionHeader, SectionList, Text

def make_section(letra: str) -> SectionHeader:
    return SectionHeader(
        title=letra,
        item_count=100,
        item_builder=lambda i: Text(content=f"{letra}-{i}"),
        header_builder=lambda: Text(content=f"Seção {letra}"),
    )

contatos = SectionList(
    sections=[make_section("A"), make_section("B"), make_section("C")],
)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `sections` | `list[SectionHeader]` | `[]` | As seções ordenadas a renderizar. |
| `end_reached_threshold` | `float` | `0.8` | A fração `0..1` do scroll total em que `on_end_reached` dispara. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Handler opcional para eventos de scroll. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Handler opcional disparado perto do fim da lista. |

!!! info "Cada seção virtualiza a sua própria janela"
    Um `SectionList` não tem uma janela única — cada `SectionHeader` carrega seu
    próprio `window_size` / `window`. Ao construir, o `SectionList` achata, em
    ordem, o cabeçalho mais os itens da janela de cada seção, tudo keyed para o diff
    por chave do reconciliador.

!!! note "`sections` cai para `[]`, nunca `None`"
    O campo `sections` usa `default_factory` para uma lista vazia — um `SectionList`
    sem seções é um estado válido (lista vazia), não um erro.

### `RefreshControl`

Um wrapper de pull-to-refresh **autônomo** (Compose `PullToRefreshBox`),
desacoplado de uma lista virtualizada. Envolva-o em torno de qualquer conteúdo
rolável — inclusive um `LazyGrid`, que não tem refresh próprio. O conteúdo é
fornecido pelo renderizador; o widget carrega só o contrato de refresh:

```python
from tempest_core import RefreshControl

async def recarregar(event) -> None:
    ...

controle = RefreshControl(refreshing=False, on_refresh=recarregar)
```

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `refreshing` | `bool` | `False` | Se o spinner de pull-to-refresh está ativo. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Handler opcional para pull-to-refresh. |

!!! tip "Você controla o `refreshing`"
    O spinner não some sozinho: no seu `on_refresh`, dispare o recarregamento e,
    quando terminar, reconstrua com `refreshing=False`. Setar `refreshing=True`
    enquanto os dados chegam mantém o indicador girando; voltar para `False` o
    esconde.

## Recapitulando

- **Indicadores** são folhas não interativas: `ProgressBar` alterna
  **determinado** (`value` em `[0.0, 1.0]`) e **indeterminado**; `Spinner` é
  circular e **sempre** indeterminado. O `color_scheme` pinta o acento.
- **Virtualização**: as listas declaram `item_count` + `item_builder` e só
  materializam a **janela visível**; o `item_builder` nunca cruza a fronteira
  nativa.
- **`DEFAULT_WINDOW_SIZE` é `20`** — o `window_size` padrão que dá conteúdo ao
  primeiro mount sem construir todos os `item_count` itens.
- **A aplicação desliza a `window`** num `ScrollEvent` (via `App.slide_window`); o
  widget só descreve qual janela materializar.
- **`LazyColumn` / `LazyRow`** têm pull-to-refresh (`refreshing` / `on_refresh`);
  **`LazyGrid` não** — envolva num `RefreshControl`.
- **Paginação**: `on_end_reached` dispara em `end_reached_threshold` (padrão
  `0.8`) do scroll total.
- **`SectionList`** achata `SectionHeader`s congelados, cada um com sua própria
  janela e cabeçalho fixo; a aplicação substitui a seção via `model_copy` para
  deslizar.
