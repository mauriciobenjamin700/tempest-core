# Eventos & handlers

Todo widget interativo do `tempest-core` tem dois lados. O **prop de handler** que
você passa (`on_click`, `on_change`, `on_submit`…) é o lado de fora; do lado de
dentro, cada widget declara **qual tipo de `Event` tipado** aquele handler vai
receber. Esta página documenta esse outro lado: os **eventos**, os **enums** que
eles carregam, os **aliases de handler** que os tipam e a **`Semantics`** que
descreve o nó para leitores de tela. 🚀

!!! info "O que você aprende aqui"
    - Como um evento **cru** vira um `Event` tipado no `parse_event`, e como
      `handler_accepts_event` decide a convenção de chamada.
    - A **tabela completa** de tipos de evento com os campos reais de cada um.
    - Os **enums** que os eventos carregam (`SwipeDirection`, `SensorType`,
      `ConnectivityState`, `AppState`).
    - Os **aliases de handler** (`EventHandler`, `TapHandler`, …) e onde aparecem.
    - A classe **`Semantics`** e como os widgets a expõem para acessibilidade.

## Como eventos fluem

Sem uma WebView não existe fronteira JS↔Python: o contrato tipado vive na
fronteira **Python↔Kotlin**. Quando o lado nativo reporta um toque ou uma
mudança de texto, ele manda um **payload cru** (um `Mapping[str, Any]`) — e esse
payload precisa ser validado *antes* de entrar num handler Python, exatamente
como o FastAPI valida um corpo de requisição. Três peças montam esse fluxo:

- **`event_schemas`** — um `ClassVar` em cada `Widget` que **mapeia o nome do prop
  de handler para o tipo de `Event`** que o payload dele vira. É como a
  introspecção publica o contrato de eventos de cada widget. Um `Button` declara
  `{"on_click": TapEvent}`.
- **`parse_event`** — o portão de validação: recebe o `event_type` esperado e o
  `raw`, e devolve um `Event` tipado (ou levanta `EventValidationError` com os
  erros de campo estruturados).
- **`handler_accepts_event`** — inspeciona a assinatura do handler: um handler que
  aceita **um argumento posicional** recebe o evento tipado; um handler de **zero
  argumentos** é chamado sem nada. O registro da ponte e o renderizador Qt usam
  os dois para concordar na convenção de chamada.

O handler em si pode ser **síncrono ou `async`** — o runtime agenda os awaitables
no event loop. Aqui está o caminho completo de um `Button` com `on_click`:

```python
from tempest_core import Button, TapEvent, parse_event, handler_accepts_event


def on_tap(event: TapEvent) -> None:
    """Handle a tap by reading the tap position off the typed event."""
    print("tapped at", event.x, event.y)


button = Button(label="Salvar", on_click=on_tap)

# 1. O widget publica seu contrato: qual prop vira qual Event.
assert button.event_schemas == {"on_click": TapEvent}

# 2. O lado nativo manda um payload cru; parse_event valida na fronteira.
raw: dict[str, float] = {"x": 12.0, "y": 34.0}
event: TapEvent = parse_event(TapEvent, raw)

# 3. handler_accepts_event decide a convenção: com argumento vs. sem.
if handler_accepts_event(on_tap):
    on_tap(event)  # recebe o TapEvent validado
else:
    on_tap()  # handler de zero argumentos é chamado pelado
```

!!! note "`parse_event` é o único portão de confiança"
    Código nativo manda um mapa sem tipo; **só um payload válido** vira um `Event`
    em que o handler pode confiar. Se o payload não bate com o `event_type`, o
    `parse_event` levanta `EventValidationError` carregando `event_type` e a lista
    de `errors` do Pydantic (JSON-serializável) — nada de dado meio-validado
    escorrega para dentro do handler.

!!! tip "Zero argumentos quando o valor não importa"
    Nem todo handler precisa do evento. `Button(on_click=lambda: contador.incr())`
    é perfeitamente válido: como o lambda não declara argumento posicional,
    `handler_accepts_event` devolve `False` e o runtime o chama pelado. Você só
    declara o parâmetro quando vai **ler** um campo (`event.value`, `event.x`…).

## Tipos de evento

Todo evento herda de **`Event`** (um `BaseModel` *frozen*, para o reconciliador
comparar por valor). A tabela lista cada tipo com seus campos reais e defaults.
Campos sem default são **obrigatórios** no payload.

| `Event` | Emitido por / quando | Campos reais |
| --- | --- | --- |
| `TapEvent` | um toque/clique num widget | `x: float \| None = None`, `y: float \| None = None` |
| `TextChangeEvent` | o valor de um input de texto mudou | `value: str`, `valid: bool \| None = None` |
| `ToggleEvent` | um checkbox/switch alternou | `checked: bool` |
| `SlideEvent` | o valor de um slider mudou | `value: float` (na faixa `[min, max]` do widget) |
| `DateChangeEvent` | o valor de um date picker mudou | `value: str` (ISO `yyyy-mm-dd`, vazio quando limpo) |
| `FileSelectEvent` | um arquivo foi escolhido num file picker | `uri: str`, `name: str \| None = None` |
| `LongPressEvent` | um toque segurou além do limiar de long-press | `x: float \| None = None`, `y: float \| None = None` |
| `SwipeEvent` | um swipe direcional passou do limiar de distância | `direction: SwipeDirection`, `dx: float = 0.0`, `dy: float = 0.0` |
| `RouteChangeEvent` | a rota ativa mudou (push/pop/replace) | `name: str`, `params: dict[str, Any] = {}` |
| `ScrollEvent` | um container rolável rolou | `offset: float`, `direction: str` (`"vertical"`/`"horizontal"`) |
| `RefreshEvent` | um pull-to-refresh completou | *(sem payload — o gesto é o sinal)* |
| `EndReachedEvent` | a lista passou do limiar de fim | *(sem payload — dispara paginação)* |
| `DismissEvent` | um overlay foi descartado (scrim/swipe/back) | `overlay_id: str \| None = None` |
| `MenuSelectEvent` | item selecionado num menu/action sheet | `value: str`, `label: str` |
| `PanEvent` | um pan/drag reportado por frame e no release | `dx: float = 0.0`, `dy: float = 0.0`, `vx: float = 0.0`, `vy: float = 0.0` |
| `ScaleEvent` | um pinch (escala + rotação) com ponto focal | `scale: float = 1.0`, `focus_x: float = 0.0`, `focus_y: float = 0.0`, `rotation: float = 0.0` |
| `DragEvent` | um drag-and-drop (pego e, talvez, solto) | `data: str = ""`, `x: float \| None = None`, `y: float \| None = None` |
| `ReorderEvent` | um item de lista arrastado para outra posição | `from_index: int`, `to_index: int` |
| `SelectEvent` | uma opção selecionada num dropdown/select | `value: str`, `index: int` |
| `TimeChangeEvent` | o valor de um time picker mudou | `value: str` (24h `"HH:MM"`, `""` quando limpo) |
| `RangeChangeEvent` | os limites de um range slider mudaram | `low: float`, `high: float` |
| `SubmitEvent` | um formulário (ou input completável) foi enviado | `values: dict[str, str] = {}` |
| `ValidationEvent` | um campo de formulário foi validado | `field: str`, `value: str`, `error: str \| None = None` |
| `PageChangeEvent` | a página ativa de um `PageView` mudou | `page: int`, `previous: int = 0` |
| `QrScanEvent` | um QR/código de barras foi decodificado | `data: str`, `format: str = "QR_CODE"` |
| `CameraFrameEvent` | um frame RGB de um preview de câmera ao vivo | `width: int`, `height: int`, `data: str` (base64 do buffer `H×W×3`), `rotation: int = 0` |
| `LifecycleEvent` | o app mudou de estado de ciclo de vida | `state: AppState` |
| `SensorEvent` | uma amostra de um stream de sensor do device | `sensor: SensorType`, `values: list[float] = []`, `timestamp_ms: int = 0` |
| `ConnectivityEvent` | a conectividade de rede do device mudou | `state: ConnectivityState` |
| `DeepLinkEvent` | o app foi aberto/retomado via deep link | `url: str`, `params: dict[str, str] = {}` |
| `ThemeChangeEvent` | o modo de tema ativo mudou (dark/light) | `mode: ThemeMode` |
| `LocaleChangeEvent` | o locale / direção de layout mudou | `language: str`, `region: str \| None = None`, `rtl: bool = False` |

!!! info "Payloads são sempre JSON-serializáveis por construção"
    Repare que nenhum evento carrega tuplas ou modelos aninhados. Um `ScaleEvent`
    reporta o ponto focal como **dois floats de topo** (`focus_x`/`focus_y`), não
    uma tupla; o `RangeChangeEvent` manda `low`/`high` separados; o `SensorEvent`
    manda uma **lista plana** de floats. Isso mantém todo payload travessável pela
    ponte sem serialização customizada.

!!! note "Eventos que não vêm de um handler de widget"
    `LifecycleEvent`, `SensorEvent`, `ConnectivityEvent`, `ThemeChangeEvent` e
    `LocaleChangeEvent` **não** saem de um `on_*` de widget. O host os dispara e a
    ponte os roteia por **tokens reservados** — `"__sensor__:<type>"`,
    `"__connectivity__:<state>"`, `"__theme__"`, `"__locale__"` — para métodos do
    `App` (`set_theme`, `set_locale`, …). São eventos de plataforma, não de toque.

## Enums de evento

Alguns eventos carregam um enum ao invés de uma string livre, para o campo ter um
domínio fechado. Todos são `StrEnum`, então serializam como o próprio valor
string.

### `SwipeDirection`

A direção cardinal de um gesto de swipe (carregada por `SwipeEvent.direction`).

| Membro | Valor | Significado |
| --- | --- | --- |
| `LEFT` | `"left"` | O ponteiro andou predominantemente para a borda esquerda (x diminuindo). |
| `RIGHT` | `"right"` | O ponteiro andou para a borda direita (x aumentando). |
| `UP` | `"up"` | O ponteiro andou para o topo da tela (y diminuindo). |
| `DOWN` | `"down"` | O ponteiro andou para a base da tela (y aumentando). |

### `SensorType`

O sensor de hardware sobre o qual um stream contínuo pode ser aberto (carregado
por `SensorEvent.sensor`).

| Membro | Valor | Significado |
| --- | --- | --- |
| `ACCELEROMETER` | `"accelerometer"` | Aceleração linear nos eixos x/y/z (com gravidade), em m/s². |
| `GYROSCOPE` | `"gyroscope"` | Velocidade angular (taxa de rotação) nos eixos x/y/z, em rad/s. |
| `MAGNETOMETER` | `"magnetometer"` | Campo geomagnético nos eixos x/y/z, em microtesla — base da bússola. |
| `PRESSURE` | `"pressure"` | Pressão atmosférica (barométrica), em hectopascais. |
| `LIGHT` | `"light"` | Iluminância ambiente na tela, em lux. |
| `PROXIMITY` | `"proximity"` | Proximidade de um objeto à frente do device (ex.: orelha), em cm. |
| `STEP_COUNTER` | `"step_counter"` | Passos acumulados desde o último boot, pelo pedômetro de hardware. |

### `ConnectivityState`

O estado de conectividade de rede do device (carregado por
`ConnectivityEvent.state`).

| Membro | Valor | Significado |
| --- | --- | --- |
| `CONNECTED` | `"connected"` | Link de rede ativo, de transporte genérico/não distinguido. |
| `DISCONNECTED` | `"disconnected"` | Sem link ativo — requisições falham até a conexão voltar. |
| `WIFI` | `"wifi"` | Conectado por Wi-Fi — tipicamente sem medição, transferências grandes OK. |
| `MOBILE` | `"mobile"` | Conectado por rede celular (dados móveis) — tipicamente medido. |

### `AppState`

O estado de ciclo de vida do processo do app (carregado por
`LifecycleEvent.state`).

| Membro | Valor | Significado |
| --- | --- | --- |
| `FOREGROUND` | `"foreground"` | Visível e recebendo input — a tarefa ativa à frente do usuário. |
| `BACKGROUND` | `"background"` | Não mais visível; deve pausar UI e liberar recursos escassos. |
| `INACTIVE` | `"inactive"` | Transicional/parcialmente obscurecido — visível mas sem receber input. |

## Aliases de handler

Cada prop `on_*` é tipado por um **`TypeAlias` de handler**. Eles não são classes
— são apenas **callables tipados** que documentam qual `Event` o handler recebe e
deixam a introspecção emitir um schema (um `Callable` cru não tem representação
em JSON-schema, então cada alias carrega uma anotação `WithJsonSchema`).

Todo alias com evento aceita **três formas** para o mesmo prop:

- `Callable[[SeuEvento], Any]` — um handler síncrono que lê o evento;
- `Callable[[SeuEvento], Awaitable[Any]]` — a versão `async` do mesmo;
- um handler de **zero argumentos** (sync ou `async`) para quando o valor não
  importa.

O runtime só passa o evento quando o handler aceita um argumento posicional
(exatamente o que `handler_accepts_event` decide).

```python
from tempest_core import Slider, SlideHandler, SlideEvent


# As três formas abaixo são todas SlideHandler válidas.
def sync_handler(event: SlideEvent) -> None:
    """Read the new value synchronously."""
    print(event.value)


async def async_handler(event: SlideEvent) -> None:
    """Persist the new value asynchronously."""
    await store.save(event.value)


def bare_handler() -> None:
    """React without needing the value."""
    mark_dirty()


slider = Slider(on_change=sync_handler)  # (1)!
```

1. O `on_change` do `Slider` é tipado como `SlideHandler`, então qualquer uma das
   três formas é aceita. O widget declara `{"on_change": SlideEvent}` em
   `event_schemas` — é assim que a ponte sabe validar o payload num `SlideEvent`.

| Alias | Evento que entrega | Aparece em (exemplos) |
| --- | --- | --- |
| `EventHandler` | *(zero argumentos)* | `Button.on_click`, `IconButton.on_click` |
| `TapHandler` | `TapEvent` | detectores de toque, `on_double_tap` |
| `TextChangeHandler` | `TextChangeEvent` | `Input.on_change`, `TextArea.on_change` |
| `ToggleHandler` | `ToggleEvent` | `Checkbox.on_change`, `Switch.on_change` |
| `SlideHandler` | `SlideEvent` | `Slider.on_change` |
| `DateChangeHandler` | `DateChangeEvent` | `DatePicker.on_change` |
| `FileSelectHandler` | `FileSelectEvent` | `FilePicker.on_select` |
| `LongPressHandler` | `LongPressEvent` | gestos de press longo |
| `SwipeHandler` | `SwipeEvent` | gestos de swipe |
| `RouteChangeHandler` | `RouteChangeEvent` | `Navigator.on_change`, `TabBar.on_change` |
| `ScrollHandler` | `ScrollEvent` | listas virtualizadas |
| `RefreshHandler` | `RefreshEvent` | `RefreshControl` |
| `EndReachedHandler` | `EndReachedEvent` | listas paginadas |
| `DismissHandler` | `DismissEvent` | `Dialog`, `BottomSheet`, `Dismissible` |
| `MenuSelectHandler` | `MenuSelectEvent` | `Menu.on_select`, `ActionSheet.on_select` |
| `PanHandler` | `PanEvent` | gesto de pan (o *widget* homônimo — veja nota) |
| `ScaleHandler` | `ScaleEvent` | gesto de pinch (o *widget* homônimo — veja nota) |
| `DragHandler` | `DragEvent` | `Draggable.on_drag`, `DragTarget.on_drop` |
| `ReorderHandler` | `ReorderEvent` | `ReorderableList.on_reorder` |
| `SelectHandler` | `SelectEvent` | `Dropdown.on_change` |
| `TimeChangeHandler` | `TimeChangeEvent` | `TimePicker.on_change` |
| `RangeChangeHandler` | `RangeChangeEvent` | `RangeSlider.on_change` |
| `SubmitHandler` | `SubmitEvent` | `Form.on_submit` |
| `ValidationHandler` | `ValidationEvent` | `FormField.on_validate` |
| `PageChangeHandler` | `PageChangeEvent` | `PageView.on_change` |

!!! warning "`PanHandler` e `ScaleHandler` são *widgets* no nível do pacote"
    Os aliases `PanHandler`/`ScaleHandler` existem em `widgets.base`, mas no nível
    do pacote (`from tempest_core import PanHandler`) esses nomes são os **widgets
    de gesto avançado** homônimos, que **sombreiam** os aliases. Os aliases ficam
    privados a `base`. Se você precisa do *tipo do callback*, é `PanEvent` /
    `ScaleEvent` que ele recebe; se importa `PanHandler`, você pega o widget.

## Semantics & acessibilidade

Qualquer nó da árvore carrega metadados de acessibilidade via
`Widget.semantics`, uma instância de **`Semantics`** (um `BaseModel` *frozen*,
para o reconciliador comparar por valor). Os leaf renderers mapeiam esses campos
para a superfície de acessibilidade da plataforma — o `QAccessible` name/description
no Qt e o `Modifier.semantics { contentDescription; role }` no Compose — para que
TalkBack e a AT do Qt consigam descrever o nó.

| Campo | Tipo | O que carrega |
| --- | --- | --- |
| `label` | `str \| None` | O rótulo acessível (`contentDescription` / nome acessível). |
| `role` | `str \| None` | Dica de papel acessível (ex.: `"button"`, `"image"`, `"heading"`); o renderizador mapeia para seu enum de papel nativo. |
| `hint` | `str \| None` | Dica de acessibilidade / tooltip descrevendo o que o nó faz. |

```python
from tempest_core import Container, Semantics

card = Container(
    semantics=Semantics(
        label="Cartão do produto",
        role="button",
        hint="Toque duas vezes para abrir os detalhes",
    ),
)
```

!!! danger "Widgets só-de-ícone dependem de `Semantics` para não ficarem mudos"
    Um botão sem texto visível não tem rótulo acessível derivável. É por isso que
    o `IconButton` roteia seu `label` para a superfície de acessibilidade — sem
    ele, o nó fica mudo para leitores de tela. Sempre que um widget não tem texto
    visível, preencha `semantics` (ou o `label` que o widget dedica à a11y).

!!! note "`focusable` e `focus_order` acompanham a `Semantics`"
    Além de `semantics`, todo `Widget` expõe `focusable: bool | None` (aceita
    foco; `None` mantém a focabilidade natural do widget) e `focus_order: int |
    None` (ordem explícita de tab; `None` usa a ordem natural de travessia). Juntos
    com a `Semantics`, formam a superfície de acessibilidade que os dois
    renderizadores consomem.

## Recapitulando

- **Dois lados**: o prop `on_*` é o de fora; `event_schemas` mapeia cada prop para
  o tipo de `Event` tipado que ele entrega.
- **`parse_event`** é o portão de fronteira: valida o payload cru num `Event`
  tipado ou levanta `EventValidationError` com os erros estruturados.
- **`handler_accepts_event`** decide a convenção: handler com um argumento recebe
  o evento; handler de zero argumentos é chamado pelado. Handlers podem ser sync
  ou `async`.
- **~32 tipos de evento**, todos herdando de `Event` (*frozen*), com payloads
  sempre JSON-serializáveis (floats de topo, listas planas — nunca tuplas).
- **Enums de domínio fechado**: `SwipeDirection`, `SensorType`,
  `ConnectivityState`, `AppState`.
- **Aliases de handler** tipam cada prop e aceitam sync/`async`/zero-arg; cuidado
  que `PanHandler`/`ScaleHandler` no nível do pacote são os *widgets*.
- **`Semantics`** (`label` / `role` / `hint`) mais `focusable` / `focus_order`
  formam a superfície de acessibilidade que Qt e Compose consomem.

Para as assinaturas completas, veja a [Referência da API](../reference.md).
