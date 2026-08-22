# Overlays

Os **overlays** são as superfícies que flutuam *acima* da árvore da tela:
diálogos, sheets, toasts, menus, tooltips e popovers. No `tempest-core` eles não
são aninhados no layout — são **empurrados na camada de overlays** da `Scene`, e
um renderizador realiza cada um como a superfície nativa da plataforma (Qt
`QDialog`/`QMenu`; Compose `AlertDialog`/`ModalBottomSheet`/`DropdownMenu`). 🚀

O detalhe que atravessa toda esta página: **um widget de overlay não tem flag de
"aberto"**. Ele descreve *o que* aparece; *quando* aparece é decisão do app, via
a API imperativa (`show_dialog` / `show_sheet` / `toast` / `show_menu`), que
gerencia o ciclo de vida do overlay. O widget declara só o conteúdo e os
handlers.

!!! info "O que você aprende aqui"
    - Por que a **visibilidade é controlada pelo app**, não por uma prop do widget.
    - Os dois contratos de handler: **`on_dismiss`** (fechou) e **`on_select`** (escolheu).
    - Como `Menu` e `ActionSheet` usam **`MenuItem`**, um value model serializável.
    - Como o **`anchor`** posiciona menus e popovers a partir da `key` de outro widget.
    - Por que `Toast` **se fecha sozinho** e não tem `on_dismiss`.

## `Dialog`

Um diálogo **modal** flutuado acima da tela, opcionalmente com título. O corpo é
uma lista de widgets filhos; o `on_dismiss` reage ao fechamento por toque na
barreira (o scrim atrás) ou pelo botão *voltar* do sistema:

```python
from tempest_core import Dialog, Text, Button, Column

confirmar = Dialog(
    title="Excluir projeto?",
    children=[
        Text(text="Essa ação não pode ser desfeita."),
        Button(label="Excluir", color_scheme="error"),
    ],
    on_dismiss=lambda e: app.set_state(dialog_aberto=False),  # (1)!
)
```

1. O handler pode ser **síncrono ou `async`**. Recebe um `DismissEvent` com o
   `overlay_id` do overlay fechado (ou `None` — veja [Referência da API](../reference.md)).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str \| None` | `None` | Título opcional do diálogo. |
| `children` | `list[Widget]` | `[]` | Os widgets do corpo do diálogo. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler no fechamento (toque na barreira ou *voltar*); recebe `DismissEvent`. |

!!! note "Visibilidade é do app, não do widget"
    Repare que **não há prop `open` nem `visible`**. Um `Dialog` só existe na tela
    enquanto o app o mantém na camada de overlays da `Scene`. Você abre com a API
    imperativa (`show_dialog`) e fecha reagindo ao `on_dismiss` — o widget nunca
    guarda seu próprio estado de aberto/fechado.

## `BottomSheet`

Um sheet que **desliza de baixo para cima** a partir da borda inferior da tela.
Mesma forma do `Dialog` — corpo em `children`, fechamento em `on_dismiss` — mas
o gesto de dispensa inclui o **arrastar para baixo** além do toque na barreira:

```python
from tempest_core import BottomSheet, Column, Text, Button

filtros = BottomSheet(
    children=[
        Text(text="Ordenar por"),
        Button(label="Mais recentes", variant="ghost"),
        Button(label="Mais populares", variant="ghost"),
    ],
    on_dismiss=lambda e: app.set_state(sheet_aberto=False),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | Os widgets do corpo do sheet. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler no fechamento (toque na barreira ou arrastar para baixo); recebe `DismissEvent`. |

!!! tip "Dialog vs. BottomSheet"
    Os dois são modais dispensáveis e compartilham o contrato `on_dismiss`. Escolha
    o `Dialog` para confirmações e decisões centradas; o `BottomSheet` para opções e
    formulários que combinam com o polegar no mobile, ancorados na borda de baixo.

## `Toast`

Uma mensagem **transitória** que aparece por um instante e **se fecha sozinha**.
Diferente dos outros overlays, o `Toast` não tem `on_dismiss`: o
`App.toast` agenda a auto-dispensa no event loop, e `duration_s` também viaja
para o renderizador para que o dispositivo espelhe a mesma temporização:

```python
from tempest_core import Toast

salvo = Toast(message="Alterações salvas")
demorado = Toast(message="Sincronizando…", duration_s=5.0)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `message` | `str` | *(obrigatório)* | O texto a exibir. |
| `duration_s` | `float` | `2.5` | Quanto tempo o toast fica visível, em segundos. |

!!! note "Sem `on_dismiss` — o fechamento é automático"
    O `Toast` é o único overlay desta página sem handler de dispensa. Ele não espera
    interação: aparece, conta `duration_s` e some. O `App.toast` cuida do timer no
    loop; o `duration_s` só é replicado no renderizador para o feedback visual ficar
    sincronizado.

## `Tooltip`

Um pequeno rótulo de dica mostrado ao lado de um **filho ancorado**. Anota um
widget sem consumir o toque dele; o `color_scheme` diz ao renderizador qual
família de papéis Material 3 pintar na superfície da dica:

```python
from tempest_core import Tooltip, IconButton

dica = Tooltip(
    message="Arquivar conversa",
    child=IconButton(icon="archive", label="Arquivar"),
    color_scheme="neutral",
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `message` | `str` | *(obrigatório)* | O texto da dica. |
| `child` | `Widget \| None` | `None` | Widget opcional que a tooltip anota. |
| `color_scheme` | `str` | `"neutral"` | A família de papéis M3 que o renderizador usa na superfície da dica. |

!!! info "O engine carrega a prop; o renderizador resolve o acento (H4)"
    A `Tooltip` não resolve cor no core: ela só **carrega** o `color_scheme`. O
    renderizador é quem casa o acento contra o tema ativo — mantendo o core sem
    tocar em pixels, como no resto da biblioteca.

## `Menu` e `MenuItem`

Um `Menu` é uma lista de itens selecionáveis **ancorada a um widget**. Os itens
não são widgets: cada um é um **`MenuItem`**, um value model *frozen* e
serializável em JSON, então a lista atravessa a ponte do dispositivo como dados
puros. A seleção dispara `on_select` com o `value` e o `label` do item escolhido:

```python
from tempest_core import Menu, MenuItem

acoes = Menu(
    items=[
        MenuItem(label="Renomear", value="rename", icon="edit"),
        MenuItem(label="Duplicar", value="duplicate", icon="copy"),
        MenuItem(label="Excluir", value="delete", icon="trash"),
    ],
    anchor="botao-opcoes",  # (1)!
    on_select=lambda e: app.executar(e.value),  # (2)!
)
```

1. O `anchor` é a **`key`** do widget a partir do qual o menu se posiciona.
2. O handler recebe um `MenuSelectEvent` com `value` (estável) e `label` (visível).

### Props do `Menu`

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `items` | `list[MenuItem]` | `[]` | As entradas selecionáveis. |
| `anchor` | `str \| None` | `None` | A `key` do widget ao qual o menu se ancora. |
| `on_select` | `MenuSelectHandler \| None` | `None` | Handler na seleção de item; recebe `MenuSelectEvent`. |

### Props do `MenuItem`

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | *(obrigatório)* | O rótulo exibido. |
| `value` | `str` | *(obrigatório)* | O valor estável reportado pelo `MenuSelectEvent` na seleção. |
| `icon` | `str \| None` | `None` | Nome de ícone opcional para renderizar ao lado do rótulo. |

!!! note "`MenuItem` é dado, não widget"
    O `MenuItem` é `frozen` e carrega apenas campos serializáveis (`label`,
    `value`, `icon`). Por isso ele não vive na árvore de widgets: cruza a ponte como
    um `dict` puro. Separe sempre o **`value` estável** (o que seu código compara) do
    **`label` visível** (o que o usuário lê) — é o `value` que chega no handler.

!!! tip "Posicionamento por `anchor`"
    O `anchor` não move o menu no layout: ele nomeia a `key` do widget disparador
    para o renderizador ancorar a superfície nativa perto dele (um `DropdownMenu`
    embaixo do botão, por exemplo). Sem `anchor`, o renderizador posiciona com seu
    padrão de plataforma.

## `Popover`

Um painel flutuante **ancorado perto de um widget**, dispensável ao tocar fora.
Como o `Menu`, aceita um `anchor` (a `key` do disparador); como o `Dialog`, tem
`on_dismiss`. A diferença é o conteúdo livre: em vez de itens, um `child`
qualquer:

```python
from tempest_core import Popover, Column, Text, Switch

preferencias = Popover(
    child=Column(
        children=[
            Text(text="Notificações"),
            Switch(value=True),
        ]
    ),
    anchor="icone-sino",
    on_dismiss=lambda e: app.set_state(popover_aberto=False),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | Widget opcional mostrado dentro do popover. |
| `anchor` | `str \| None` | `None` | A `key` do widget ao qual o popover se ancora. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler no fechamento; recebe `DismissEvent`. |

!!! tip "Popover vs. Menu"
    Use o `Menu` quando o conteúdo é uma **lista de escolhas** (ele carrega `items` +
    `on_select`). Use o `Popover` quando é um **painel de conteúdo livre** ancorado
    ao disparador — um mini-formulário, um resumo, controles soltos.

## `ActionSheet`

Uma lista de ações **ancorada na base** da tela, opcionalmente com título. É o
primo do `Menu` para o padrão de sheet inferior do mobile: mesmos `MenuItem`,
mesmo `on_select`, mas ancorado embaixo em vez de junto a um widget:

```python
from tempest_core import ActionSheet, MenuItem

compartilhar = ActionSheet(
    title="Compartilhar via",
    items=[
        MenuItem(label="Copiar link", value="copy", icon="link"),
        MenuItem(label="E-mail", value="email", icon="mail"),
        MenuItem(label="Mensagem", value="sms", icon="chat"),
    ],
    on_select=lambda e: app.compartilhar(e.value),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str \| None` | `None` | Título opcional do sheet. |
| `items` | `list[MenuItem]` | `[]` | As ações selecionáveis. |
| `on_select` | `MenuSelectHandler \| None` | `None` | Handler na seleção de ação; recebe `MenuSelectEvent`. |

!!! note "`ActionSheet` seleciona; `BottomSheet` compõe"
    Os dois sobem da borda de baixo, mas resolvem contratos diferentes. O
    `ActionSheet` é **seleção** (`items` + `on_select`, via `MenuSelectEvent`), como
    um menu deitado no rodapé. O `BottomSheet` é **conteúdo livre** (`children` +
    `on_dismiss`) — um layout inteiro que sobe. Escolha pelo contrato, não pela
    aparência.

## Recapitulando

- **Overlays flutuam acima da tela** e vivem na camada de overlays da `Scene`, não
  no layout — o app os empurra pela API imperativa e gerencia o ciclo de vida.
- **Sem flag de visibilidade**: nenhum overlay tem prop `open`/`visible`; abrir e
  fechar é decisão do app, e o widget só declara conteúdo e handlers.
- **Dois contratos de handler**: `on_dismiss` → `DismissEvent` (`Dialog`,
  `BottomSheet`, `Popover`); `on_select` → `MenuSelectEvent` (`Menu`,
  `ActionSheet`).
- **`Toast`** é a exceção: **se fecha sozinho** por `duration_s`, sem `on_dismiss`.
- **`MenuItem`** é um value model *frozen* e serializável (`label` / `value` /
  `icon`) — dado, não widget; separe sempre o `value` estável do `label` visível.
- **`anchor`** é a `key` do widget disparador — posiciona `Menu` e `Popover` perto
  dele; sem ele, vale o padrão de plataforma.
- **`Tooltip`** carrega `color_scheme`, mas quem resolve o acento contra o tema é o
  renderizador (H4).
