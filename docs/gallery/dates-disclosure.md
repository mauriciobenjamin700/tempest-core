# Datas & disclosure

Esta página junta duas famílias pequenas mas muito usadas do `tempest-core`:
os componentes de **data/hora** — **`Calendar`** (grade do mês) e **`Clock`**
(relógio digital) — e o único componente de **disclosure**, **`Accordion`**
(seção que expande e colapsa). Todos são `Component`s: descrevem *intenção* e
**baixam para primitivas** (`Text` / `Row` / `Column` / `Container` / `Button`)
na hora do `render`, então funcionam nos dois renderizadores sem mudança. 🚀

!!! info "O que você aprende aqui"
    - Como o `Calendar` monta a grade do mês e reporta o dia tocado via `on_select`.
    - Como o `Clock` só **mostra** uma string de hora — quem tica é o app.
    - Por que os dois migraram para os **tokens do tema M3** (Trilho H6) e o que
      isso muda visualmente.
    - Como o `Accordion` é **controlado pelo app**: o `open` mora no estado e o
      `on_toggle` o inverte.

## Datas & hora

Os dois componentes de tempo compartilham a mesma filosofia: **o core não conta
as horas**. O `Calendar` desenha um mês e avisa qual dia você tocou; o `Clock`
apenas pinta a string que o app já formatou. Ambos leem cores do `theme` em vez
de hexes cravados.

### `Calendar`

Uma grade do mês com células de dia selecionáveis. No caso mínimo você só passa
o `on_select` — o mês e a seleção têm padrão vazio (mês atual, nada
selecionado):

```python
from tempest_core.components import Calendar

agenda = Calendar(on_select=lambda iso: print(iso))
```

Esse único `Calendar(on_select=…)` já renderiza o **mês atual** contra o tema M3
claro padrão, com título, cabeçalho de dias da semana e uma linha por semana.
Para controlar o mês exibido e o dia destacado, passe `month` e `selected` a
partir do estado do app:

```python
from tempest_core.components import Calendar

agenda = Calendar(
    month="2026-07",  # (1)!
    selected="2026-07-12",
    on_select=lambda iso: app.set_state(selected=iso),  # (2)!
    color_scheme="primary",
)
```

1. O `month` é `"YYYY-MM"`; vazio cai no mês corrente. O `selected` é
   `"YYYY-MM-DD"` e só destaca quando cair no mês exibido.
2. O `on_select` recebe a **string ISO** `"YYYY-MM-DD"` do dia tocado. Guarde-a
   no estado e reinjete via `selected` para fechar o ciclo (veja
   [Referência da API](../reference.md)).

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `on_select` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a ISO `"YYYY-MM-DD"` do dia tocado. |
| `month` | `str` | `""` | O mês exibido como `"YYYY-MM"`; vazio significa o mês atual. |
| `selected` | `str` | `""` | O dia selecionado como `"YYYY-MM-DD"`; destacado quando cai no mês exibido; vazio = sem seleção. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 com que o dia selecionado se preenche. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem as cores. |
| `style` | `Style \| None` | `None` | Override mesclado por cima do `Style` padrão da grade (via `merge_style`). |
| `key` | `str \| None` | `None` | Chave de reconciliação; cai em `"calendar"` quando ausente. |

!!! note "Migrou para os tokens do tema (Trilho H6)"
    O `Calendar` **não crava mais hexes**. O título e o texto do dia leem o papel
    `ON_SURFACE`; o cabeçalho de dias da semana e os dias não selecionados leem os
    papéis apagados `ON_SURFACE_VARIANT` / `SURFACE_VARIANT`; o dia selecionado se
    preenche com o papel do `color_scheme` (padrão `primary`) sobre seu conteúdo
    legível `on_*`. Tudo resolvido do `theme`. É retrocompatível — `Calendar(on_select=…)`
    passa a renderizar contra o tema M3 **claro** (uma mudança visual em relação à
    paleta escura anterior).

!!! tip "O `Calendar` é controlado, como o resto do kit"
    A seleção não vive dentro do componente: o `on_select` te entrega a data, você
    a guarda no estado do app e a devolve via `selected`. Mesmo padrão do `Drawer`
    e do `Accordion` — o core fica sem estado, o app é a fonte da verdade.

### `Clock`

Uma face de relógio digital que renderiza uma string de hora **preformatada**. O
componente não tica sozinho — o app formata e atualiza o texto a partir do
estado (como no exemplo `stopwatch`):

```python
from tempest_core.components import Clock

relogio = Clock(time="12:34:56")
```

Passe um `label` para uma legenda apagada embaixo da hora, e um `color_scheme`
opcional para tingir o horário:

```python
from tempest_core.components import Clock

cronometro = Clock(
    time="00:00:42",
    label="Tempo decorrido",  # (1)!
    color_scheme="primary",  # (2)!
)
```

1. O `label` é uma legenda opcional; quando `None`, o `Clock` renderiza só a hora.
2. O `color_scheme` é opcional — `None` (ou `"neutral"`) mantém a hora no neutro
   `ON_SURFACE`.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `time` | `str` | `""` | O texto da hora (ex.: `"12:34:56"`); o app formata e tica a partir do estado. |
| `label` | `str \| None` | `None` | Legenda opcional mostrada apagada embaixo da hora. |
| `color_scheme` | `str \| None` | `None` | Família de papéis M3 opcional que tinge a hora; `None` mantém o neutro `ON_SURFACE`. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens fornecem as cores. |
| `style` | `Style \| None` | `None` | Override mesclado por cima do `Style` padrão centralizado. |
| `key` | `str \| None` | `None` | Chave de reconciliação; cai em `"clock"` quando ausente. |

!!! note "Migrou para os tokens do tema (Trilho H6)"
    Como o `Calendar`, o `Clock` deixou de cravar hexes: a hora lê `ON_SURFACE`
    (ou o papel do `color_scheme`, quando dado), a legenda lê o apagado
    `ON_SURFACE_VARIANT` e o fundo lê `SURFACE` — tudo do `theme`. `Clock(time=…)`
    continua funcionando e passa a renderizar contra o tema M3 **claro** (mudança
    visual em relação à paleta escura anterior).

!!! warning "O `Clock` não conta o tempo"
    Ele é uma **face**, não um timer. Passar `time="12:34:56"` mostra exatamente
    essa string. Quem incrementa o relógio (um `asyncio` loop, um `Timer`, um tick
    de estado) é o app — o core fica sem estado e determinístico de propósito.

## Disclosure

Disclosure é o padrão "mostrar/esconder sob demanda". O kit traz um componente
para isso: o `Accordion`.

### `Accordion`

Uma seção com título cujo corpo aparece **só quando `open`**. Não há overlay: um
acordeão aberto simplesmente renderiza seu corpo abaixo do cabeçalho. O `open` é
**controlado** — mora no estado do app e é invertido pelo `on_toggle` do
cabeçalho, espelhando o `Drawer`:

```python
from tempest_core.components import Accordion
from tempest_core.widgets import Text

detalhes = Accordion(
    title="Detalhes do pedido",
    open=app.state.details_open,  # (1)!
    on_toggle=lambda: app.set_state(details_open=not app.state.details_open),
    children=[Text(content="Entrega prevista para sexta.")],  # (2)!
)
```

1. O `open` vem do estado do app — o componente nunca guarda esse booleano.
2. Os `children` só são revelados quando `open` é `True`; fechado, o cabeçalho
   renderiza sozinho.

O cabeçalho ganha um marcador de rotação simples — `▸` quando fechado, `▾`
quando aberto — prefixado ao título, então o usuário vê o estado sem custo de
renderizador.

#### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `on_toggle` | `Callable[[], Any]` | *(obrigatório)* | Chamado quando o cabeçalho é tocado (inverta o `open` no estado). |
| `title` | `str` | `""` | O texto do cabeçalho. |
| `open` | `bool` | `False` | Se o corpo está expandido. |
| `children` | `list[Widget]` | `[]` | Os widgets revelados quando aberto. |
| `variant` | `CardVariant` | `FILLED` | O tratamento de superfície do cabeçalho (filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 com que tingir o cabeçalho. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a superfície do cabeçalho. |
| `style` | `Style \| None` | `None` | Override mesclado por cima do `Style` padrão do container. |
| `key` | `str \| None` | `None` | Chave de reconciliação; cai em `"accordion"` quando ausente. |

!!! note "O cabeçalho é uma superfície resolvida (Trilho H3)"
    O cabeçalho não crava cores: ele passa por
    `resolve_surface_variant`, que produz uma superfície Material 3 *filled* ou
    *outlined* a partir do `variant` e do `color_scheme`, com os passos de
    espaçamento (`padding`/`radius`) vindos da escala do tema. Por cima disso, o
    texto do cabeçalho recebe `FontWeight.BOLD`.

!!! tip "Expandir/colapsar é o app quem controla"
    Como o `open` é externo, você decide a política: um acordeão sempre aberto por
    padrão, um grupo "sanfona" onde abrir um fecha os outros, um estado persistido
    entre sessões — tudo mora no seu `set_state`. O `Accordion` só reflete o
    booleano que você der.

!!! info "Sem corpo quando fechado, sem custo escondido"
    Fechado, o `Accordion` renderiza **apenas** o botão de cabeçalho — os
    `children` nem entram na árvore de primitivas. Abrir insere um `Column` com o
    corpo abaixo; fechar o remove. Nada fica montado e escondido.

## Recapitulando

- **Três componentes, duas famílias**: `Calendar` + `Clock` (data/hora) e
  `Accordion` (disclosure), todos `Component`s que baixam para primitivas.
- **`Calendar`**: grade do mês controlada; `on_select` te dá a ISO
  `"YYYY-MM-DD"`, você devolve via `selected`. Dia escolhido se preenche com o
  `color_scheme`.
- **`Clock`**: uma **face**, não um timer — mostra a string `time` que o app
  formata e tica; `label` e `color_scheme` opcionais.
- **Tokens do tema (Trilho H6)**: `Calendar` e `Clock` deixaram de cravar hexes
  e leem `ON_SURFACE` / `ON_SURFACE_VARIANT` / `SURFACE` do `theme` — padrão M3
  claro.
- **`Accordion`**: seção titulada controlada; o `open` mora no estado e o
  `on_toggle` o inverte. Cabeçalho resolvido por `resolve_surface_variant`
  (Trilho H3); fechado, o corpo nem é montado.
