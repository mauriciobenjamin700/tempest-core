# Seleção

Os componentes de **seleção** deixam a pessoa **escolher um valor**: um segmento,
uma opção de rádio, um chip, uma nota de estrelas. Ao contrário dos botões, eles
não são só uma afordância tapável — carregam a ideia de *estado escolhido*. São
**componentes compostos** (`Component`): cada um **abaixa** (`render`) para uma
árvore de primitivas (`Row` / `Column` / `Button` / `Text`), então funcionam nos
dois renderizadores (Qt e Compose) e no device sem mudar nada. 🚀

Todos são **temáticos via tokens** (Trilho H4): a cor de "escolhido", o fundo, a
pílula — tudo é **resolvido do `Theme`**, não hard-coded. Modo escuro e cor de
marca saem de graça.

!!! info "O que você aprende aqui"
    - O **padrão sem estado**: o componente nunca guarda a escolha — o **app**
      mantém e passa via props (`selected` / `value`) + um handler (`on_select` /
      `on_rate`).
    - Como cada componente **abaixa** para primitivas e por que isso o torna
      device-ready sem código de renderizador.
    - Como `color_scheme` escolhe a família de cor M3 do item escolhido.
    - A diferença entre um chip **selecionável**, um chip **apresentacional** e a
      `Tag` (o preset fechado do `Chip`).

## O padrão sem estado 🧠

Antes dos componentes, o conceito central. **Nenhum** componente de seleção
guarda a própria escolha. Quem é a "fonte da verdade" é o **seu app** — ele
mantém o índice/valor selecionado no estado, passa esse valor via prop
(`selected`, `value`) e recebe o novo valor de volta pelo handler
(`on_select`, `on_rate`). O componente só **desenha** o estado que você deu.

```python
from tempest_core import SegmentedControl


# O app é dono da escolha; o componente só reflete `selected` e reporta o toque.
class Preferencias:
    def __init__(self) -> None:
        self.aba: int = 0  # (1)!

    def view(self) -> SegmentedControl:
        return SegmentedControl(
            options=["Dia", "Semana", "Mês"],
            selected=self.aba,  # (2)!
            on_select=self._trocar_aba,  # (3)!
        )

    def _trocar_aba(self, index: int) -> None:
        self.aba = index  # (4)!
        # ... agende um rebuild da view
```

1. O estado mora no **app**, não no componente.
2. Você **empurra** a escolha atual para dentro do componente a cada build.
3. O handler é chamado com o índice tocado.
4. Você **atualiza seu estado** e reconstrói — o componente redesenha já
   destacando o novo `selected`.

!!! tip "Por que sem estado?"
    Um componente puro é **determinístico**: mesmos props → mesma árvore de
    primitivas. Isso deixa o diff/rebuild previsível, evita duas fontes da verdade
    (o "selecionado interno" que discorda do estado do app) e faz o mesmo widget
    servir renderizador e device sem sincronização escondida.

## `SegmentedControl`

Um grupo de pílulas compacto para **escolha única** — as abas ficam lado a lado e
uma delas está ativa. Ele abaixa para um `Row` de `Button`s, com o segmento ativo
resolvido como `SOLID` e os demais como `GHOST`.

```python
from tempest_core import SegmentedControl

periodo = SegmentedControl(
    options=["Dia", "Semana", "Mês"],
    selected=1,  # "Semana" ativo
    on_select=lambda index: print(index),  # (1)!
    color_scheme="primary",
    size="sm",
)
```

1. `on_select` recebe o **índice** do segmento tocado (um `int`).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | Os rótulos dos segmentos, em ordem. |
| `selected` | `int` | `0` | O índice do segmento ativo. |
| `on_select` | `Callable[[int], Any]` | *(obrigatório)* | Chamado com o índice do segmento tocado. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que pinta o segmento ativo. |
| `size` | `ResponsiveSize` | `SM` | A densidade de cada segmento — um `Size` ou mapa por breakpoint. |
| `theme` | `Theme` | `Theme()` | O tema que resolve os segmentos. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! note "Ativo = solid, resto = ghost"
    O segmento cujo índice bate com `selected` resolve pela variante `SOLID`
    (preenchido, ênfase máxima) via `resolve_variant`; os outros resolvem como
    `GHOST` (transparente, discreto). Quem decide *qual* família de cor pinta o
    ativo é o `color_scheme`. O fundo do trilho é o token `surface_variant` do
    tema.

## `RadioGroup`

Uma lista **vertical** de escolha única com marcadores de rádio (◉ / ○). Abaixa
para um `Column` de `Button`s — um por opção — com a linha escolhida marcada e
tingida pelo accent do tema.

```python
from tempest_core import RadioGroup

envio = RadioGroup(
    options=["Padrão", "Expresso", "Retirada"],
    selected=0,
    on_select=lambda index: print(index),  # (1)!
    color_scheme="primary",
    size="md",
)
```

1. Igual ao `SegmentedControl`: o handler recebe o **índice** da opção tocada.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | Os rótulos das opções, em ordem. |
| `selected` | `int` | `0` | O índice da opção escolhida. |
| `on_select` | `Callable[[int], Any]` | *(obrigatório)* | Chamado com o índice da opção tocada. |
| `size` | `ResponsiveSize` | `MD` | A densidade do marcador de cada linha. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 do accent da linha escolhida. |
| `theme` | `Theme` | `Theme()` | O tema que resolve as cores das linhas. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! note "As cores das linhas vêm do tema"
    A cor do marcador/texto é resolvida pela variante de seleção H2
    (`resolve_selection_variant`): a linha escolhida lê o accent do `color_scheme`,
    as demais leem um tom `on_surface_variant` esmaecido. As glifas ◉/○ são fixas;
    só as **cores** ficam theme-driven — o que dá modo escuro e cor de marca de
    graça.

!!! tip "`SegmentedControl` vs `RadioGroup`"
    Os dois são escolha única sobre `options`/`selected`/`on_select`. Prefira
    `SegmentedControl` para **poucas** opções curtas que cabem numa linha (filtros,
    períodos); prefira `RadioGroup` quando as opções são **mais longas** ou
    numerosas e pedem uma lista vertical legível.

## `Chip`

Um rótulo pequeno e arredondado (uma "pílula"), **opcionalmente selecionável**. É
o componente de seleção mais flexível: dependendo dos props, ele abaixa para
coisas diferentes.

```python
from tempest_core import Chip

# Chip de filtro selecionável — o app é dono de `selected`.
filtro = Chip(
    label="Em promoção",
    selected=True,
    on_click=lambda: print("chip tocado"),  # (1)!
    color_scheme="primary",
    size="md",
)

# Chip apresentacional (sem on_click) — vira uma pílula estática de texto.
rotulo = Chip(label="Novo")
```

1. `on_click` **não recebe argumento** — o chip só reporta o toque; quem sabe qual
   chip é você (via closure/estado do app).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | O texto do chip. |
| `selected` | `bool` | `False` | Se o chip lê como ativo (badge *solid* vs *subtle*). |
| `on_click` | `Callable[[], Any] \| None` | `None` | Handler de toque; quando `None`, o chip é apenas apresentacional. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que tinge o chip. |
| `size` | `ResponsiveSize` | `MD` | A densidade da pílula. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o tratamento do chip. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! info "Como o `Chip` abaixa — dois caminhos"
    - `on_click` **setado** → abaixa para um `Button` carregando o estilo de badge
      resolvido (é tapável).
    - `on_click` **`None`** → abaixa para um `Text` (uma pílula estática, sem
      afordância de toque).

    Em ambos, a pílula vem de `resolve_badge_variant`: um badge `SOLID` quando
    `selected=True`, um badge `SUBTLE` (tonal, baixa ênfase) caso contrário.

!!! warning "O app é dono de `selected`"
    Como todo componente de seleção, o `Chip` **não alterna sozinho**. Um toque
    chama seu `on_click`; é o **seu** código que atualiza o estado e reconstrói o
    chip com o novo `selected`. O chip só desenha o booleano que você deu.

## `Tag`

Um rótulo **fechado, não selecionável** — um preset fino do `Chip`. Uma `Tag` é
exatamente um `Chip` travado na sua forma apresentacional de baixa ênfase: nunca
selecionável, nunca tapável. Use para rótulos **somente leitura** de
categoria/status, onde a interatividade de um `Chip` seria errada.

```python
from tempest_core import Tag

status = Tag(label="Arquivado", color_scheme="neutral")
categoria = Tag(label="Backend", size="sm")
```

### Props

Uma `Tag` compartilha os props de tema do `Chip` (`label` / `color_scheme` /
`size` / `theme` / `media`), mas **fixa** dois campos:

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `selected` | `bool` | `False` *(congelado)* | Uma tag nunca é selecionada — travada no badge *subtle*. |
| `on_click` | `Callable[[], Any] \| None` | `None` *(congelado)* | Uma tag nunca é tapável — sempre uma pílula estática. |

!!! note "`selected` e `on_click` são `frozen`"
    Nos dois campos, o `Field` é declarado com `frozen=True`, então tentar setá-los
    numa `Tag` é um erro de validação, não um caminho silencioso. É isso que faz a
    `Tag` sempre abaixar para uma pílula `SUBTLE` estática (um `Text`), reusando o
    mesmo `resolve_badge_variant` do `Chip`.

!!! tip "`Chip` vs `Tag`"
    Precisa que a pessoa **alterne/escolha**? Use `Chip` (com `selected` +
    `on_click`). Só quer **exibir** uma categoria ou status que não reage a toque?
    Use `Tag` — a intenção "somente leitura" fica explícita no tipo.

## `Rating`

Uma fileira de estrelas que **mostra** (e opcionalmente **define**) uma nota de
base 1. Abaixa para um `Row` de células de estrela (★ cheia / ☆ vazia).

```python
from tempest_core import Rating

# Interativa: o app é dono de `value`, o toque reporta a nova nota.
nota = Rating(
    value=3,
    max_stars=5,
    on_rate=lambda estrelas: print(estrelas),  # (1)!
    color_scheme="primary",
)

# Apenas exibição (sem on_rate) — estrelas não tapáveis.
media = Rating(value=4, max_stars=5)
```

1. `on_rate` recebe o valor **de base 1** da estrela tocada (tocar a 3ª estrela
   reporta `3`).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `int` | `0` | O número de estrelas preenchidas. |
| `max_stars` | `int` | `5` | O total de estrelas mostradas. |
| `on_rate` | `Callable[[int], Any] \| None` | `None` | Handler chamado com a nota de base 1 da estrela tocada; quando `None`, é apenas exibição. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que pinta as estrelas cheias. |
| `theme` | `Theme` | `Theme()` | O tema que resolve a cor das estrelas. |

!!! note "Estrela clicável é um `GHOST` transparente"
    Quando `on_rate` está setado, cada estrela abaixa para um `Button` de variante
    `GHOST` com fundo **explicitamente transparente** — assim a glifa lê como uma
    estrela nua, não uma pílula preenchida (o `SOLID` padrão pintaria a cor do
    papel por cima). Sem `on_rate`, cada estrela é um `Text` simples.

!!! warning "`Rating` também é sem estado"
    A `Rating` desenha exatamente `value` estrelas cheias — ela **não** incrementa
    sozinha ao tocar. Seu `on_rate` reporta a nota escolhida; o **app** guarda esse
    número e reconstrói a `Rating` com o novo `value`.

## Recapitulando

- **Padrão sem estado**: nenhum componente guarda a escolha. O **app** mantém
  `selected`/`value`, passa via prop e recebe o novo valor por `on_select` /
  `on_click` / `on_rate`; o componente só desenha o estado dado.
- **Compostos que abaixam**: cada um é um `Component` que faz `render` para uma
  árvore de primitivas — device-ready sem código de renderizador.
- **`SegmentedControl`**: pílulas de escolha única (ativo = `SOLID`, resto =
  `GHOST`); `on_select` recebe o índice.
- **`RadioGroup`**: lista vertical de rádio; cores das linhas resolvidas por
  `resolve_selection_variant`; `on_select` recebe o índice.
- **`Chip`**: pílula opcionalmente selecionável — abaixa para `Button` com
  `on_click`, ou `Text` sem ele; `SOLID` quando `selected`, `SUBTLE` quando não.
- **`Tag`**: preset fechado do `Chip` com `selected`/`on_click` `frozen` — sempre
  uma pílula `SUBTLE` estática, para rótulos somente leitura.
- **`Rating`**: fileira de estrelas; clicável = `GHOST` transparente; `on_rate`
  recebe a nota de base 1.
- **Temáticos via tokens (H4)**: cor de escolhido, fundo e pílula vêm do `Theme` e
  do `color_scheme` — modo escuro e cor de marca de graça.
