# Tabelas

As tabelas exibem dados em **linhas por colunas**. Há duas, e elas resolvem
problemas opostos: **`Table`** é uma grade **estática** que você monta à mão a
partir de valores tipados (`TableRow` / `TableCell`); **`DataTable`** é uma
tabela **temática** de strings, com **ordenação** e **paginação conduzidas pelo
app**. Como todo componente do `tempest-core`, as duas abaixam para uma `Column`
de `Row`s de `Container`/`Text`, então renderizam idênticas no simulador Qt e no
device Compose, sem mudança de renderizador. 🚀

!!! info "O que você aprende aqui"
    - Como montar uma **grade estática** com `Table` a partir de `TableRow` e `TableCell`.
    - O que `colspan` / `rowspan` fazem hoje (e o que ainda não fazem).
    - O padrão **"conduzido pelo app"** da `DataTable`: o componente **não guarda estado**.
    - Como **ordenação** vira cabeçalhos tapáveis com seta `▲`/`▼`, e como **paginar** com `page_size`.

## `Table`

Uma tabela de dados **estática**, disposta como linhas de células de largura
igual. Você a monta a partir de `TableRow`s tipadas, cada uma com uma lista de
`TableCell`s. No caso mínimo, só `rows`:

```python
from tempest_core import Table, TableRow, TableCell

tabela = Table(
    headers=["Nome", "Papel"],
    rows=[
        TableRow(cells=[TableCell(content="Ana"), TableCell(content="Admin")]),
        TableRow(cells=[TableCell(content="Bruno"), TableCell(content="Editor")]),
    ],
)
```

Os `headers` viram uma **primeira linha enfatizada** (fundo `SURFACE`, texto
`ON_SURFACE` em negrito); cada linha do corpo ganha um divisor inferior e cada
célula **cresce** (`grow=1.0`) para dividir a largura da linha por igual. Sem
`headers`, você tem só o corpo.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `rows` | `list[TableRow]` | `[]` | As linhas do corpo, cada uma uma `TableRow` de `TableCell`s. |
| `headers` | `list[str]` | `[]` | Rótulos de cabeçalho renderizados como primeira linha enfatizada. Vazio = sem cabeçalho. |
| `style` | `Style \| None` | `None` | Um `Style` sobreposto ao fundo `SURFACE` padrão da tabela. |

!!! note "Colunas por posição, largura por igual"
    Não há modelo de coluna: a *n*-ésima `TableCell` de cada linha ocupa a *n*-ésima
    coluna, e todas as células crescem igualmente. Alinhe suas linhas você mesmo —
    uma linha com menos células simplesmente tem menos colunas naquela linha.

## `TableCell`

Uma única célula de uma `Table`. É um modelo de **valor imutável** (`frozen`):
carrega o texto e, opcionalmente, `colspan` / `rowspan` e um `style` próprio.

```python
from tempest_core import TableCell
from tempest_core import Style

destaque = TableCell(content="Total", style=Style(grow=1.0))
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `content` | `str` | *(obrigatório)* | O texto da célula. |
| `colspan` | `int` | `1` | Quantas colunas a célula ocupa. |
| `rowspan` | `int` | `1` | Quantas linhas a célula ocupa. |
| `style` | `Style \| None` | `None` | Um `Style` sobreposto ao padding/texto padrão da célula. |

!!! warning "`colspan` e `rowspan` são informativos por enquanto"
    Os dois campos existem e são validados, mas a **abaixação para primitivas
    renderiza uma célula por entrada** — não há mesclagem de células ainda. Trate-os
    como metadado que os renderizadores podem honrar no futuro, não como um efeito
    de layout garantido hoje.

## `TableRow`

Uma única linha de uma `Table` — as células ordenadas mais um `style` opcional
sobreposto ao layout padrão da linha. Também é `frozen`.

```python
from tempest_core import TableRow, TableCell
from tempest_core import Style

linha = TableRow(
    cells=[TableCell(content="Ana"), TableCell(content="Admin")],
    style=Style(grow=1.0),  # sobreposto ao divisor inferior padrão da linha
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `cells` | `list[TableCell]` | `[]` | As células ordenadas da linha. |
| `style` | `Style \| None` | `None` | Um `Style` sobreposto ao layout padrão da linha (que já traz um divisor inferior). |

!!! tip "O `style` da linha é mesclado, não substituído"
    A `Table` monta cada linha com um divisor inferior padrão e então **mescla o
    seu `style` por cima** (via `merge_style`). Você ajusta um campo pontual sem
    perder o divisor — mesma regra de override que os botões usam para o `Style`.

## `DataTable`

Uma tabela de **matriz de strings temática**, com **ordenação e paginação
conduzidas pelo app**. É a conveniência estilizada para o caso comum
"cabeçalhos + matriz de strings": ela lê todas as cores dos tokens do `Theme`
(cabeçalho `SURFACE_VARIANT` / `ON_SURFACE`, corpo `SURFACE` com uma zebra sutil,
divisor `OUTLINE_VARIANT`) — nenhum hexadecimal fixo. No caso mínimo, só
`columns` e `rows`:

```python
from tempest_core import DataTable

tabela = DataTable(
    columns=["Nome", "Idade"],
    rows=[["Ana", "42"], ["Bruno", "17"], ["Carla", "88"]],
)
```

Isso já é uma tabela temática, pronta para os renderizadores. As props de
ordenação e paginação abaixo são **aditivas**: cada chamada
`DataTable(columns=…, rows=…)` existente continua funcionando.

### O padrão "conduzido pelo app"

Seguindo o mesmo padrão das **listas virtualizadas**, a `DataTable` **não guarda
estado**. Ela é uma projeção pura do estado que **a aplicação** mantém:

- **Ordenação** — o app guarda `sort_column` / `sort_ascending` e **passa as
  linhas já ordenadas**. A tabela só desenha a seta direcional `▲`/`▼` no
  cabeçalho ativo e emite `on_sort(col)` quando um cabeçalho é tocado.
- **Paginação** — o app guarda `page`; quando `page_size` está setado a tabela
  **fatia** `rows[page*page_size : …]` para exibir, desenha uma linha
  paginadora (prev / next + `"page X / Y"`) e emite `on_page(page)` no
  prev/next.

!!! danger "A tabela não ordena nem fatia os seus dados — você ordena"
    `on_sort(col)` é um **pedido**, não uma ação. A tabela nunca reordena `rows`
    sozinha; ela avisa qual coluna foi tocada e **você** reordena a lista e
    reconstrói. Passar `rows` desordenadas com um `sort_column` setado só desenha a
    seta no lugar errado — os dados continuam na ordem que você deu. Mesma regra
    vale para a paginação: a tabela fatia a página atual, mas é o seu `on_page` que
    move o `page`.

### Ordenação: como o cabeçalho vira botão

Quando você liga `on_sort`, cada cabeçalho vira um `Button` tapável e o rótulo
ganha um indicador conforme o estado:

| Situação | Rótulo renderizado |
| --- | --- |
| Coluna é a ordenada (`sort_column == index`), ascendente | `Nome ▲` |
| Coluna é a ordenada, descendente | `Nome ▼` |
| `on_sort` ligado, coluna inativa | `Nome ↕` |
| `sortable=True` sem `on_sort` (modo legado) | `Nome ▾` |
| Nada disso | `Nome` |

!!! note "`sortable=True` é o modo legado"
    `DataTable(sortable=True)` sem `on_sort` mantém o comportamento antigo de
    "anotar todo cabeçalho com um glifo de ordenação" (`▾`), mas os cabeçalhos
    **não** são tapáveis. Para ordenação real e interativa, ligue `on_sort` — aí a
    tabela desenha `↕`/`▲`/`▼` e emite o índice da coluna tocada.

### Paginação: a fatia da página atual

Setar `page_size` faz a tabela projetar só a fatia da página atual e desenhar um
paginador `‹ Prev` / `Next ›` com um rótulo `page X / Y` no centro. Os alvos de
prev/next já vêm **limitados** a `[0, última página]`, então o paginador nunca
sai do intervalo:

```python
from tempest_core import DataTable

pagina = DataTable(
    columns=["Nome", "Idade"],
    rows=[["Ana", "42"], ["Bruno", "17"], ["Carla", "88"], ["Diego", "5"]],
    page=0,
    page_size=2,  # duas linhas por página → 2 páginas
    on_page=lambda p: None,  # troque pela sua re-renderização
)
```

!!! tip "A zebra é contínua entre páginas"
    A listra zebrada segue o **índice absoluto** da linha (`page*page_size + i`),
    não a posição dentro da fatia. Assim a paridade par/ímpar não reinicia a cada
    página — a segunda página continua a listra de onde a primeira parou, e o
    padrão fica visualmente estável ao navegar.

### Exemplo ponta a ponta

Juntando ordenação e paginação, o app mantém um pequeno estado, ordena os dados
e reconstrói a tabela a cada mudança — a tabela é sempre uma função pura desse
estado:

```python
from typing import Any

from tempest_core import DataTable

# O app é dono do estado — a tabela é só uma projeção dele.
state: dict[str, Any] = {"sort_column": 0, "sort_ascending": True, "page": 0}

data: list[list[str]] = [
    ["Ana", "42"],
    ["Bruno", "17"],
    ["Carla", "88"],
    ["Diego", "5"],
]


def sorted_rows() -> list[list[str]]:
    """Return the rows sorted by the app's active column and direction."""
    col: int = state["sort_column"]
    return sorted(data, key=lambda row: row[col], reverse=not state["sort_ascending"])


def on_sort(col: int) -> None:
    """Toggle direction when re-tapping the active column, else sort it ascending."""
    if state["sort_column"] == col:
        state["sort_ascending"] = not state["sort_ascending"]
    else:
        state["sort_column"] = col
        state["sort_ascending"] = True
    app.rebuild()  # (1)!


def on_page(page: int) -> None:
    """Move to the requested (already clamped) page index."""
    state["page"] = page
    app.rebuild()


def build() -> DataTable:
    """Build the table as a pure projection of the current app state."""
    return DataTable(
        columns=["Nome", "Idade"],
        rows=sorted_rows(),  # o app passa as linhas já ordenadas
        sort_column=state["sort_column"],
        sort_ascending=state["sort_ascending"],
        on_sort=on_sort,
        page=state["page"],
        page_size=2,
        on_page=on_page,
    )
```

1. `app.rebuild()` representa a re-renderização do seu framework — o gatilho que
   reconstrói a árvore a partir do novo estado (veja [Referência da API](../reference.md)).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `columns` | `list[str]` | `[]` | Os rótulos de cabeçalho das colunas. |
| `rows` | `list[list[str]]` | `[]` | As linhas do corpo como matriz de células string (o app pré-ordena). |
| `sortable` | `bool` | `False` | Cabeçalhos carregam uma afordância de ordenação (glifo legado quando não há `on_sort`). |
| `sort_column` | `int \| None` | `None` | Índice da coluna pela qual as linhas estão ordenadas, ou `None` para sem ordenação ativa. |
| `sort_ascending` | `bool` | `True` | Se a ordenação ativa é ascendente (`▲`) ou descendente (`▼`). |
| `on_sort` | `Callable[[int], Any] \| None` | `None` | Chamado com o índice da coluna tocada para pedir uma mudança de ordenação. |
| `page` | `int` | `0` | O índice da página atual (base zero), usado quando `page_size` está setado. |
| `page_size` | `int \| None` | `None` | Número de linhas por página; `None` mostra todas (sem paginador). |
| `on_page` | `Callable[[int], Any] \| None` | `None` | Chamado com o índice da página pedida (base zero) no prev/next. |
| `theme` | `Theme` | `Theme()` | O tema do design-system cujos tokens fornecem as cores. |
| `style` | `Style \| None` | `None` | Um `Style` sobreposto ao fundo `SURFACE` padrão da tabela. |

!!! note "Cores por token, sem hexadecimal fixo"
    A `DataTable` deriva **toda** cor do `theme`: o preenchimento do cabeçalho de
    `SURFACE_VARIANT`, o texto de `ON_SURFACE`, o divisor de `OUTLINE_VARIANT` e a
    zebra de `SURFACE_VARIANT` misturada até a metade com `SURFACE` (o modelo de
    token não tem um papel `SURFACE_CONTAINER` dedicado, então a mistura é
    determinística). Troque o `theme` e a tabela inteira reveste sozinha.

## Recapitulando

- **Duas tabelas, problemas opostos**: `Table` é uma grade **estática** montada à
  mão; `DataTable` é uma matriz de strings **temática** e interativa.
- **`Table`** é feita de `TableRow`s de `TableCell`s; `headers` viram uma primeira
  linha enfatizada e cada célula cresce por igual.
- **`TableCell` / `TableRow`** são valores `frozen`; `colspan`/`rowspan` são
  informativos por enquanto, e o `style` da linha é **mesclado** por cima do
  divisor padrão.
- **`DataTable` não guarda estado** — como as listas, o **app** mantém
  `sort_column` / `sort_ascending` / `page` e passa as `rows` **já ordenadas**.
- **Ordenação**: ligar `on_sort` torna os cabeçalhos botões e desenha `↕`/`▲`/`▼`;
  `sortable=True` sozinho é só o glifo legado `▾`.
- **Paginação**: `page_size` fatia a página atual, desenha um paginador prev/next
  limitado ao intervalo e mantém a zebra contínua entre páginas.
