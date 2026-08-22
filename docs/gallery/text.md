# Texto

O texto é o **átomo** da interface: quase toda tela tem um rótulo, um título ou
um parágrafo. No `tempest-core` há **um** primitivo para isso — **`Text`** — e
ele é deliberadamente minimalista: carrega só o `content` (a string) e delega
**toda** a aparência (tipografia, cor, alinhamento, overflow) ao objeto `Style`.
Nenhuma prop de tipografia mora no widget; elas moram no `style`, exatamente como
no CSS o texto herda `font-*` do seletor. 🚀

!!! info "O que você aprende aqui"
    - Por que o `Text` só tem `content` e onde vive **toda** a tipografia.
    - Como estilizar peso, tamanho, cor, itálico e decoração via `Style`.
    - Como alinhar (`text_align`) e como controlar **texto multilinha**.
    - Como cortar com `max_lines` e terminar com **ellipsis** (`…`) ou corte seco.
    - Como o `Text` **abaixa na IR** — que props viram `Node.props` e quais não.

## `Text`

Uma corrida de texto. No caso mínimo você passa só `content` — sem estilo, o
renderizador aplica seus próprios defaults de fonte e cor:

```python
from tempest_core import Text

titulo = Text(content="Olá, mundo")
```

Esse `Text(content="Olá, mundo")` já é um nó válido, pronto para os
renderizadores. Para dar aparência, passe um `Style` — o mesmo objeto tipado que
todo widget aceita:

```python
from tempest_core import Text
from tempest_core.style import Style, FontWeight, Color

titulo = Text(
    content="Bem-vindo",
    style=Style(
        font_size=24.0,
        font_weight=FontWeight.BOLD,  # (1)!
        color=Color.from_hex("#1D1B20"),
    ),
)
```

1. `FontWeight` é um `IntEnum` na escala CSS/OpenType: `THIN=100`, `LIGHT=300`,
   `NORMAL=400`, `MEDIUM=500`, `SEMIBOLD=600`, `BOLD=700`, `BLACK=900`.

### Props

O `Text` **só** adiciona `content`. Todo o resto é herdado da base `Widget` — e a
tipografia inteira mora no `style`, não como prop solta:

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `content` | `str` | *(obrigatório)* | A string a exibir. |
| `style` | `Style \| None` | `None` | Estilo inline — tipografia, cor, alinhamento, overflow. Ver a tabela abaixo. |
| `semantics` | `Semantics \| None` | `None` | Metadados de acessibilidade (`label` / `role` / `hint`) roteados para a superfície de a11y. |
| `focusable` | `bool \| None` | `None` | Se o nó aceita foco; `None` mantém o natural (um label não é focável). |
| `focus_order` | `int \| None` | `None` | Ordem de foco/tab explícita; `None` usa a ordem de traversal natural. |
| `tag` | `str \| None` | `None` | Override de tag HTML semântica (ex.: `"h1"`) honrado pelo renderizador HTML/SSR; ignorado pelos não-web. |
| `attrs` | `dict[str, str]` | `{}` | Atributos HTML arbitrários (`id`, `class`, `data-*`, `aria-*`) honrados no SSR; ignorados pelos não-web. |
| `key` | `str \| None` | `None` | Identidade estável usada pelo reconciliador para casar nós entre rebuilds. **Vira `Node.key`, não uma prop.** |

!!! note "`content` é obrigatório; tudo o mais tem padrão"
    Só `content` não tem default — os demais campos herdados são `None`/`{}`, e
    `None` num `Style` significa **"não setado"**, deixando o renderizador cair no
    seu próprio default. Você nunca precisa preencher tudo: setar só o que muda é o
    caminho idiomático.

### Tipografia via `style`

Como o `Text` não tem props de fonte próprias, você molda a aparência pelos
campos de tipografia do `Style`. Todos são opcionais (`None` = herdar o default do
renderizador):

| Campo do `Style` | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `color` | `Color \| None` | `None` | A cor do texto. |
| `font_size` | `float \| None` | `None` | Tamanho da fonte em pixels lógicos. |
| `font_weight` | `FontWeight \| None` | `None` | Peso: `THIN` (100) … `BLACK` (900). |
| `font_style` | `FontStyle \| None` | `None` | Inclinação: `NORMAL` (romano) ou `ITALIC`. |
| `font_family` | `str \| None` | `None` | Nome da família da fonte. |
| `font_asset` | `str \| None` | `None` | Caminho de uma fonte custom no bundle (ex.: `"fonts/Roboto.ttf"`). |
| `text_align` | `TextAlign \| None` | `None` | Alinhamento horizontal: `LEFT` / `CENTER` / `RIGHT` / `JUSTIFY`. |
| `text_decoration` | `TextDecoration \| None` | `None` | Linha decorativa: `NONE` / `UNDERLINE` / `LINE_THROUGH`. |
| `letter_spacing` | `float \| None` | `None` | Espaçamento adicional entre letras, em pixels lógicos. |
| `line_height` | `float \| None` | `None` | Altura da linha (entrelinha). |
| `max_lines` | `int \| None` (`> 0`) | `None` | Máximo de linhas antes de cortar o texto. |
| `text_overflow` | `TextOverflow \| None` | `None` | Como o texto cortado termina: `CLIP` ou `ELLIPSIS`. |
| `text_scale` | `float \| None` (`> 0`) | `None` | Multiplicador aplicado ao `font_size` (`1.0` é neutro). |

```python
from tempest_core import Text
from tempest_core.style import (
    Style,
    FontWeight,
    FontStyle,
    TextDecoration,
    Color,
)

# Um preço em destaque: grande, seminegrito, colorido.
preco = Text(
    content="R$ 49,90",
    style=Style(
        font_size=28.0, font_weight=FontWeight.SEMIBOLD, color=Color.from_hex("#006C4C")
    ),
)

# Uma nota em itálico, riscada (preço antigo).
antigo = Text(
    content="R$ 79,90",
    style=Style(
        font_style=FontStyle.ITALIC, text_decoration=TextDecoration.LINE_THROUGH
    ),
)
```

!!! tip "`text_scale` respeita a acessibilidade do sistema"
    `text_scale` é um multiplicador sobre `font_size` (`1.0` = neutro). No Qt o
    translator escala o `font-size` emitido; no Compose ele vira `textScale` para a
    `LocalDensity` do dispositivo aplicar — ou seja, o texto acompanha o ajuste de
    "tamanho da fonte" do sistema em vez de ignorá-lo. Prefira ajustar a *escala* a
    fixar tamanhos absolutos quando o objetivo é respeitar a preferência do usuário.

### Alinhamento

`text_align` controla o alinhamento horizontal **dentro da caixa de texto** —
para ver efeito, a caixa precisa ser mais larga que a linha (dê largura via
`style.width` ou deixe o `Text` num container que a estica):

```python
from tempest_core import Text
from tempest_core.style import Style, TextAlign

centralizado = Text(
    content="Toque para continuar",
    style=Style(width=320.0, text_align=TextAlign.CENTER),
)
```

!!! note "`JUSTIFY` estica o espaçamento, não a última linha"
    `TextAlign.JUSTIFY` distribui o espaço entre palavras para cada linha ficar
    rente às duas bordas — **exceto a última**, que fica alinhada ao início. É o
    comportamento clássico de texto justificado; use com `line_height` folgado para
    não abrir "rios" de espaço em colunas estreitas.

### Texto multilinha, `max_lines` e overflow

Um `content` com `\n` — ou simplesmente longo demais para a largura da caixa —
vira **várias linhas**. Para limitar a altura, use `max_lines`; para decidir como
o texto cortado termina, use `text_overflow`:

```python
from tempest_core import Text
from tempest_core.style import Style, TextOverflow

# Uma prévia de duas linhas com reticências no fim.
previa = Text(
    content=(
        "Este é um texto longo de descrição que não cabe inteiro no card "
        "e precisa ser truncado de forma elegante no final da segunda linha."
    ),
    style=Style(width=280.0, max_lines=2, text_overflow=TextOverflow.ELLIPSIS),
)
```

!!! warning "`text_overflow` só age depois que o texto estoura o espaço"
    `TextOverflow` (`CLIP` / `ELLIPSIS`) só entra em cena quando o texto **excede**
    o espaço disponível — tipicamente ao passar de `max_lines`. Sem um limite de
    linhas (ou de largura/altura), não há estouro, então nada é cortado e o
    `text_overflow` fica inerte. Combine `max_lines` **com** `text_overflow` para a
    prévia truncada; `CLIP` corta seco na borda, `ELLIPSIS` acrescenta `…` para
    sinalizar que houve corte.

!!! tip "Uma linha só? `max_lines=1` + `ELLIPSIS`"
    Para um rótulo de uma linha que nunca quebra (nomes, títulos de card), use
    `Style(max_lines=1, text_overflow=TextOverflow.ELLIPSIS)`. É o equivalente ao
    idioma CSS `white-space: nowrap; overflow: hidden; text-overflow: ellipsis`.

### Acessibilidade

Um `Text` visível já é lido por leitores de tela a partir do seu `content`. Use
`semantics` quando o texto precisa de um **papel** (ex.: cabeçalho) ou de um rótulo
acessível diferente do visível:

```python
from tempest_core import Text
from tempest_core.widgets import Semantics
from tempest_core.style import Style, FontWeight

titulo = Text(
    content="Configurações",
    style=Style(font_size=22.0, font_weight=FontWeight.BOLD),
    semantics=Semantics(role="heading"),  # (1)!
)
```

1. `Semantics` carrega `label` / `role` / `hint`. Os renderizadores mapeiam para a
   superfície nativa (Qt `QAccessible`; Compose `Modifier.semantics`), então
   TalkBack e leitores anunciam "cabeçalho" em vez de só o texto.

!!! note "Tamanho visual não é hierarquia semântica"
    Deixar um `Text` grande e negrito o faz *parecer* um título, mas não o
    *anuncia* como um para a acessibilidade. Passe `semantics=Semantics(role="heading")`
    (ou `tag="h1"` no SSR) para que a hierarquia seja real, não só visual.

### Como o `Text` abaixa na IR

Na build, o reconciliador **normaliza** cada widget num `Node` uniforme: um `type`
(o nome da classe), um `key` e um mapa **plano** de `props` (mais os filhos, que o
`Text` não tem). O `key` sai dos props e vira `Node.key`; todo o resto do widget
vira prop:

```python
from tempest_core import Text, build
from tempest_core.style import Style, FontWeight

node = build(
    Text(content="Oi", key="saudacao", style=Style(font_weight=FontWeight.BOLD))
)

node.type  # "Text"
node.key  # "saudacao"  — o key sai dos props e vira identidade do nó
node.props  # {"content": "Oi", "style": Style(font_weight=BOLD, ...), "semantics": None, ...}
node.children  # []  — Text é um nó folha
```

!!! info "O `style` já vai baked; o `Text` não resolve variante"
    Ao contrário de `Button`, o `Text` **não** roda um resolver de variante — ele
    não tem `variant`/`size`/`color_scheme`. O `Style` que você passa entra na IR
    exatamente como está (nenhuma resolução de tema no meio), então o `Text` é o
    primitivo mais direto: o que você escreve no `style` é o que o renderizador
    consome. Veja o `Node` completo na [Referência da API](../reference.md).

## Recapitulando

- **Um primitivo, um campo:** `Text` só adiciona `content`; toda a tipografia mora
  no `style`, como o texto herda `font-*` no CSS.
- **Tipografia via `Style`:** `font_size`, `font_weight` (`THIN`…`BLACK`),
  `font_style`, `color`, `letter_spacing`, `line_height`, `font_family`/`font_asset`
  e `text_scale` — todos opcionais (`None` = default do renderizador).
- **Alinhamento:** `text_align` (`LEFT`/`CENTER`/`RIGHT`/`JUSTIFY`) age dentro da
  caixa; `JUSTIFY` não estica a última linha.
- **Multilinha e overflow:** `\n` ou texto longo quebra em várias linhas;
  `max_lines` + `text_overflow` (`CLIP`/`ELLIPSIS`) fazem a prévia truncada.
- **Acessibilidade:** o `content` já é lido; use `semantics` (ou `tag` no SSR) para
  papel semântico — tamanho visual não é hierarquia.
- **Na IR:** `Text` vira um `Node` folha; `key` vira `Node.key`, o resto vira
  `props`, e o `style` entra baked, sem resolução de variante.
