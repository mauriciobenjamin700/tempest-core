# Inputs

Os inputs são as **folhas que carregam valor** da IR: campos de texto, controles
de seleção e sliders. Cada um guarda seu valor atual como um escalar JSON
(`str` / `bool` / `float`) e declara seu handler de mudança em `event_schemas`,
para a boundary validar o payload. E todos são estilizados pela **API de
variantes de ergonomia Chakra (fase H2)** ancorada em **Material 3**: você
descreve a *intenção* (`size` / `color_scheme`, mais `field_variant` na família
FIELD) e um **resolver puro** assa o `Style` concreto a partir dos tokens do
`Theme` — exatamente como o [`Button`](../reference.md). 🚀

!!! info "O que você aprende aqui"
    - As **três famílias** de input (FIELD / SELECTION / SLIDER) e qual resolver
      cada uma usa.
    - As três **variantes de campo** (`FieldVariant`) e para qual tratamento M3
      cada uma abaixa.
    - Os props compartilhados de variante (`size` / `color_scheme` / `theme` /
      `media`) e por que `theme` e `media` ficam de fora da IR.
    - Como cada input **resolve e assa** seu `Style`, e como ler a **tabela por
      estado** (`state_styles()`).
    - Os 14 widgets — de `Input` a `MaskedInput` — com seus props reais e padrões.

## As três famílias de variantes

Todo input estilizado herda uma de três mixins internas, e cada família resolve
seu `Style` por uma função pura distinta (`resolve_*_variant`), com override do
chamador sempre mesclado por cima:

| Família | Widgets | Props de variante | Resolver |
| --- | --- | --- | --- |
| **FIELD** | `Input`, `TextArea`, `DatePicker`, `FilePicker`, `Dropdown`, `TimePicker`, `Autocomplete`, `PinInput`, `MaskedInput` | `field_variant` + `size` + `color_scheme` | `resolve_field_variant` |
| **SELECTION** | `Checkbox`, `Switch` | `checked` + `size` + `color_scheme` | `resolve_selection_variant` |
| **SLIDER** | `Slider`, `RangeSlider` | `size` + `color_scheme` | `resolve_slider_variant` |

Todas compartilham quatro props de resolução, além dos específicos da família:

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `size` | `Size \| dict[str, Size]` | `Size.MD` | A densidade — um `Size` único (`XS` / `SM` / `MD` / `LG`) ou um mapa por breakpoint. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que a tinta de foco/acento pinta (`primary` / `secondary` / `tertiary` / `error` / `neutral` / `success` / `warning` / `info`). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a variante. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para resolver um `size` responsivo. **Não entra na IR.** |

!!! note "`theme` e `media` são entradas de build, não props da IR"
    Os dois entram **só na hora de resolver** o `Style` e ficam fora dos props do
    nó (`prop_exclude_names = {"theme", "media"}`). Um `Theme` inteiro por nó
    incharia a árvore e o payload serializado da ponte — o `style` resolvido já
    carrega o efeito deles.

### A tabela de `FieldVariant` (só a família FIELD)

Diferente dos botões, um campo é **liderado pelo foco**: o tratamento em repouso é
de baixa ênfase e o `color_scheme` só tinge o foco/caret/label, nunca o
preenchimento em repouso. O `field_variant` escolhe esse tratamento de repouso:

| `FieldVariant` | Tratamento M3 | Fundo | Borda em repouso | Raio |
| --- | --- | --- | --- | --- |
| `OUTLINE` | *outlined text field* (o padrão) | transparente | borda inteira na cor `outline` | pequeno |
| `FILLED` | *filled text field* | tonal (`surface_variant`) | nenhuma | pequeno |
| `FLUSHED` | campo só com sublinhado | transparente | só a borda inferior | nenhum |

```python
from tempest_core import Input
from tempest_core.style import FieldVariant

outlined = Input(placeholder="E-mail", field_variant=FieldVariant.OUTLINE)
filled = Input(placeholder="E-mail", field_variant=FieldVariant.FILLED)
flushed = Input(placeholder="E-mail", field_variant=FieldVariant.FLUSHED)
```

!!! tip "O acento de `color_scheme` só aparece no foco"
    Na família FIELD, o `color_scheme` não pinta o fundo em repouso — ele tinge a
    borda/caret quando o campo ganha foco (2px na cor do papel). Um campo com
    `error` não vazio força a borda/label para o papel `error` em **todos** os
    estados (o `Input` faz isso a partir do próprio `error`).

### A tabela por estado (`state_styles()`)

Os resolvers são puros e moram no engine, mas os inputs reais têm **estados de
interação**. Cada widget expõe `state_styles()`, que devolve o `Style` resolvido
para cada `ComponentState`, já com o override do chamador mesclado por cima:

```python
from tempest_core import Input
from tempest_core.style import ComponentState

campo = Input(placeholder="Nome", color_scheme="primary")
estados = campo.state_styles()

estados[ComponentState.DEFAULT]  # repouso
estados[ComponentState.HOVER]  # ponteiro em cima
estados[ComponentState.PRESSED]  # tratado como FOCUS num campo (ganha foco)
estados[ComponentState.DISABLED]  # inativo (conteúdo a 38%)
estados[ComponentState.FOCUS]  # foco de teclado/leitor (borda de acento 2px)
```

!!! note "A resolução é pura; só o mapeamento evento→estado mora no renderizador"
    O core produz a **tabela** de estados de forma determinística. Aplicar a
    *state layer* do Material 3 no evento certo de foco/ponteiro é a única parte
    que vive nos renderizadores (Qt / Compose) — mantém o core sem tocar em pixels.
    Um `style` explícito passado ao widget é sempre mesclado por cima da variante
    resolvida (os campos setados do override vencem), então `Input(...)` sem
    `style` te dá o campo da variante e `Input(..., style=…)` estiliza à mão por
    cima sem perder a variante.

## `KeyboardType`

O enum que diz **qual teclado virtual** um campo de texto pede no dispositivo.
Mapeia para o `inputType` do Android no renderizador de device e para as dicas de
input-method do Qt no simulador.

```python
from tempest_core import Input, KeyboardType

telefone = Input(placeholder="(11) 90000-0000", keyboard=KeyboardType.PHONE)
```

| Membro | Valor | O que faz |
| --- | --- | --- |
| `TEXT` | `"text"` | Teclado alfanumérico completo, sem especialização (o padrão). |
| `NUMBER` | `"number"` | Teclado numérico para dígitos (com tecla de decimal/sinal). |
| `EMAIL` | `"email"` | Teclado de texto ajustado para e-mail, com `@` e `.` à mão. |
| `PHONE` | `"phone"` | Discador telefônico (dígitos mais `+`, `*` e `#`). |
| `URL` | `"url"` | Teclado ajustado para URLs, com `/` e `.` e sem a barra de espaço. |
| `PASSWORD` | `"password"` | Teclado para entrada secreta; mascara os caracteres e desliga sugestões/autocorreção. |

## `Input`

Um campo de texto editável de **uma linha**, estilizado pela API de variantes de
campo. No mínimo você não passa nada — os padrões dão um campo `OUTLINE`,
primário, de densidade média:

```python
from tempest_core import Input

nome = Input(placeholder="Seu nome")
```

Passe um `on_change` para reagir a cada edição; o handler recebe um
`TextChangeEvent` (com o novo `value` e a flag `valid` do `pattern`):

```python
from tempest_core import Input, KeyboardType
from tempest_core.style import FieldVariant

email = Input(
    value="",
    placeholder="voce@exemplo.com",
    keyboard=KeyboardType.EMAIL,
    field_variant=FieldVariant.FILLED,
    on_change=lambda e: app.set_state(email=e.value),  # (1)!
)
```

1. O handler pode ser **síncrono ou `async`** — o runtime agenda os awaitables no
   event loop.

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`), o `Input` carrega:

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O texto atual. |
| `placeholder` | `str` | `""` | A dica mostrada com o campo vazio. |
| `secure` | `bool` | `False` | Se mascara o texto (campo de senha); o renderizador oferece o toggle de "olho". |
| `pattern` | `str \| None` | `None` | Regex que o valor precisa casar por inteiro para ser válido; o renderizador avalia e reporta via `TextChangeEvent.valid`. |
| `error` | `str` | `""` | Mensagem de validação; um `error` não vazio força a borda/label para o papel `error`. |
| `keyboard` | `KeyboardType` | `KeyboardType.TEXT` | O teclado virtual pedido. |
| `max_length` | `int \| None` | `None` | Um teto opcional de caracteres. |
| `leading_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda inicial (leading) — valor curado de `Icons` ou nome de plataforma. |
| `trailing_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda final (trailing). |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler chamado com um `TextChangeEvent` a cada edição. |

!!! info "`error` é o que dispara o `invalid` do resolver"
    O `Input` sobrescreve `_field_invalid()` para devolver `bool(self.error)`. Ou
    seja: setar uma mensagem em `error` não só a mostra — também pinta a
    borda/label de vermelho (`error`) em todos os estados, sem você mexer no
    `color_scheme`.

## `TextArea`

Um campo de texto editável de **várias linhas**. Resolve seu `Style` igual ao
`Input` (mesma família FIELD), só trocando a afordância renderizada e adicionando
uma dica de altura inicial:

```python
from tempest_core import TextArea

bio = TextArea(placeholder="Fale sobre você", rows=5, max_length=500)
```

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O texto atual. |
| `placeholder` | `str` | `""` | A dica mostrada com o campo vazio. |
| `rows` | `int` | `3` | O número de linhas visíveis (dica de altura inicial). |
| `max_length` | `int \| None` | `None` | Um teto opcional de caracteres. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler chamado com um `TextChangeEvent` a cada edição. |

## `Checkbox`

Uma **caixa de seleção booleana** com rótulo, estilizada pela API de variantes de
seleção. Aqui não há `field_variant`: o M3 dá a cada controle de seleção uma
afordância única, então o resolver usa `size` / `color_scheme` mais o estado
`checked`:

```python
from tempest_core import Checkbox

aceito = Checkbox(
    label="Aceito os termos",
    checked=False,
    on_change=lambda e: app.set_state(aceito=e.value),  # (1)!
)
```

1. O `on_change` recebe um `ToggleEvent`, cujo `value` booleano é o novo estado.

### Props

Além dos props de variante compartilhados de seleção (`size` / `color_scheme` /
`theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | O texto mostrado ao lado do controle. |
| `checked` | `bool` | `False` | Se a caixa está marcada. |
| `on_change` | `ToggleHandler \| None` | `None` | Handler chamado com um `ToggleEvent` na alternância. |

!!! note "`checked` entra na resolução do `Style`"
    O `resolve_selection_variant` recebe o `checked`: marcado, a caixa pinta o
    acento (`color_scheme`) como fundo; desmarcado, vira um anel transparente com
    borda `outline` de 2px. O tamanho do box vem de `SELECTION_SIZE`, mas o alvo de
    toque de 48dp é responsabilidade da linha que o contém, nunca do box.

## `Switch`

Um **interruptor liga/desliga** (toggle) com rótulo. Difere do `Checkbox` só na
afordância renderizada — carrega a mesma semântica booleana e a mesma resolução de
acento:

```python
from tempest_core import Switch

notificacoes = Switch(
    label="Notificações",
    checked=True,
    color_scheme="success",
    on_change=lambda e: app.set_state(notify=e.value),
)
```

### Props

Além dos props de variante compartilhados de seleção (`size` / `color_scheme` /
`theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | O texto mostrado ao lado do controle. |
| `checked` | `bool` | `False` | Se o interruptor está ligado. |
| `on_change` | `ToggleHandler \| None` | `None` | Handler chamado com um `ToggleEvent` na alternância. |

## `Slider`

Um **slider de valor único** arrastável sobre um intervalo numérico, estilizado
pela API de variantes de slider (`size` / `color_scheme`, sem `variant` — o M3 dá
ao slider uma afordância só):

```python
from tempest_core import Slider

volume = Slider(
    value=40.0,
    min_value=0.0,
    max_value=100.0,
    step=5.0,
    on_change=lambda e: app.set_state(volume=e.value),  # (1)!
)
```

1. O `on_change` recebe um `SlideEvent` conforme o valor se move.

### Props

Além dos props de variante compartilhados de slider (`size` / `color_scheme` /
`theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `float` | `0.0` | O valor atual, limitado a `[min_value, max_value]`. |
| `min_value` | `float` | `0.0` | O menor valor selecionável. |
| `max_value` | `float` | `100.0` | O maior valor selecionável. |
| `step` | `float` | `1.0` | O incremento entre valores selecionáveis. |
| `on_change` | `SlideHandler \| None` | `None` | Handler chamado com um `SlideEvent` conforme o valor se move. |

!!! note "O `size` mexe na espessura do trilho, não no alvo de toque"
    O `resolve_slider_variant` pega a espessura do trilho de `SLIDER_SIZE` (2px no
    `XS` a 6px no `LG`) e pinta o trilho ativo com o acento do `color_scheme`. O
    halo do thumb e o alvo de toque de 48dp são trabalho do renderizador, nunca da
    altura do trilho.

## `DatePicker`

Um **campo de seleção de data** — um gatilho em forma de campo (família FIELD) que
abre o seletor de data da plataforma. Guarda a data como uma string ISO
`yyyy-mm-dd`:

```python
from tempest_core import DatePicker

nascimento = DatePicker(
    label="Data de nascimento",
    value="2000-01-01",
    on_change=lambda e: app.set_state(dob=e.value),  # (1)!
)
```

1. O `on_change` recebe um `DateChangeEvent` na seleção.

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | A data selecionada como string ISO `yyyy-mm-dd` (`""` se vazia). |
| `label` | `str` | `""` | Um rótulo opcional mostrado com o campo. |
| `on_change` | `DateChangeHandler \| None` | `None` | Handler chamado com um `DateChangeEvent` na seleção. |

## `FilePicker`

Um **gatilho em forma de campo** que abre o seletor de arquivos da plataforma
(família FIELD). Guarda o nome/URI de exibição do arquivo escolhido:

```python
from tempest_core import FilePicker

anexo = FilePicker(
    label="Enviar comprovante",
    on_select=lambda e: app.set_state(arquivo=e.value),  # (1)!
)
```

1. O `on_select` recebe um `FileSelectEvent` na seleção.

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `"Choose file"` | O texto do botão. |
| `value` | `str` | `""` | O nome/URI de exibição do arquivo selecionado (`""` até escolher um). |
| `on_select` | `FileSelectHandler \| None` | `None` | Handler chamado com um `FileSelectEvent` na seleção. |

## `Dropdown`

Um **controle de escolha única** (select) estilizado pela API de campo. As opções
são strings em ordem de exibição, e `value` é `None` enquanto nada estiver
escolhido:

```python
from tempest_core import Dropdown

uf = Dropdown(
    options=["SP", "RJ", "MG", "BA"],
    placeholder="Selecione o estado",
    on_select=lambda e: app.set_state(uf=e.value, indice=e.index),  # (1)!
)
```

1. O `on_select` recebe um `SelectEvent` carregando o `value` da opção e seu
   `index` (0-based).

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | As opções selecionáveis, em ordem de exibição. |
| `value` | `str \| None` | `None` | A opção atualmente selecionada, ou `None` quando nada foi escolhido. |
| `placeholder` | `str` | `"Select…"` | A dica mostrada enquanto nenhuma opção está selecionada. |
| `leading_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda inicial (leading). |
| `trailing_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda final (trailing). |
| `on_select` | `SelectHandler \| None` | `None` | Handler chamado com um `SelectEvent` (com `value` e `index`) na seleção. |

## `TimePicker`

Um **campo de seleção de hora** (família FIELD), gêmeo do `DatePicker`. Guarda a
hora como uma string `"HH:MM"` de 24 horas:

```python
from tempest_core import TimePicker

horario = TimePicker(
    label="Horário",
    value="14:30",
    on_change=lambda e: app.set_state(hora=e.value),  # (1)!
)
```

1. O `on_change` recebe um `TimeChangeEvent` na seleção.

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | A hora selecionada como string `"HH:MM"` de 24h (`""` se vazia). |
| `label` | `str` | `""` | Um rótulo opcional mostrado com o campo. |
| `on_change` | `TimeChangeHandler \| None` | `None` | Handler chamado com um `TimeChangeEvent` na seleção. |

## `RangeSlider`

Um **slider de dois thumbs** que seleciona um sub-intervalo `[low, high]` (família
SLIDER). Mesma resolução de acento do `Slider`, com dois limites em vez de um:

```python
from tempest_core import RangeSlider

faixa_preco = RangeSlider(
    low=100.0,
    high=800.0,
    min_value=0.0,
    max_value=1000.0,
    step=50.0,
    on_change=lambda e: app.set_state(faixa=(e.low, e.high)),  # (1)!
)
```

1. O `on_change` recebe um `RangeChangeEvent` carregando os dois limites conforme
   o intervalo se move.

### Props

Além dos props de variante compartilhados de slider (`size` / `color_scheme` /
`theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `low` | `float` | `0.0` | O limite inferior atual, limitado a `[min_value, high]`. |
| `high` | `float` | `100.0` | O limite superior atual, limitado a `[low, max_value]`. |
| `min_value` | `float` | `0.0` | O menor valor selecionável. |
| `max_value` | `float` | `100.0` | O maior valor selecionável. |
| `step` | `float` | `1.0` | O incremento entre valores selecionáveis. |
| `on_change` | `RangeChangeHandler \| None` | `None` | Handler chamado com um `RangeChangeEvent` conforme o intervalo se move. |

## `Autocomplete`

Um **campo de texto que sugere e seleciona** de uma lista de opções (família
FIELD). Emite dois eventos distintos — um `TextChangeEvent` enquanto você digita e
um `SelectEvent` quando uma sugestão é escolhida:

```python
from tempest_core import Autocomplete

cidade = Autocomplete(
    options=["São Paulo", "Salvador", "Sorocaba"],
    placeholder="Cidade",
    on_change=lambda e: app.set_state(texto=e.value),
    on_select=lambda e: app.set_state(cidade=e.value),  # (1)!
)
```

1. Os dois handlers serializam como tokens distintos no nó (o padrão multi-handler
   compartilhado com o `LazyColumn`).

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | As sugestões candidatas, filtradas contra o texto digitado. |
| `value` | `str` | `""` | O texto atual. |
| `placeholder` | `str` | `""` | A dica mostrada com o campo vazio. |
| `leading_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda inicial (leading). |
| `trailing_icon` | `Icons \| str \| None` | `None` | Ícone opcional na borda final (trailing). |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler chamado com um `TextChangeEvent` a cada edição. |
| `on_select` | `SelectHandler \| None` | `None` | Handler chamado com um `SelectEvent` quando uma sugestão é escolhida. |

## `PinInput`

Uma entrada **segmentada de PIN / OTP** de células de um caractere (família
FIELD). Emite um `TextChangeEvent` (o valor concatenado) a cada edição e um
`SubmitEvent` quando todas as células estão preenchidas:

```python
from tempest_core import PinInput

codigo = PinInput(
    length=6,
    secure=False,
    on_change=lambda e: app.set_state(otp=e.value),
    on_complete=lambda e: app.verificar_codigo(),  # (1)!
)
```

1. O `on_complete` recebe um `SubmitEvent` quando a última célula é preenchida.

### Props

Além dos props de variante compartilhados de campo (`size` / `color_scheme` /
`theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `field_variant` | `FieldVariant` | `FieldVariant.OUTLINE` **(frozen)** | Fixo em `OUTLINE` — as células segmentadas são caixas outlined. |
| `length` | `int` | `6` | O número de células de um caractere. |
| `value` | `str` | `""` | O valor concatenado atual. |
| `secure` | `bool` | `False` | Se cada célula mascara seu caractere (PIN em vez de OTP). |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler chamado com um `TextChangeEvent` a cada edição. |
| `on_complete` | `SubmitHandler \| None` | `None` | Handler chamado com um `SubmitEvent` quando todas as células estão preenchidas. |

!!! warning "O `field_variant` do `PinInput` é congelado"
    Diferente dos outros campos, o `field_variant` do `PinInput` é `frozen=True`:
    as células segmentadas só fazem sentido como caixas `OUTLINE`, então tentar
    trocá-lo para `FILLED`/`FLUSHED` levanta erro de validação do Pydantic. Os
    outros props de variante (`size`, `color_scheme`) continuam livres.

## `MaskedInput`

Um **campo de texto que aplica uma máscara** enquanto você digita (família FIELD).
A máscara usa `9` para um dígito obrigatório e `A` para uma letra obrigatória;
qualquer outro caractere é um literal fixo (ex.: `"999.999.999-99"` para um CPF):

```python
from tempest_core import MaskedInput, KeyboardType

cpf = MaskedInput(
    mask="999.999.999-99",
    placeholder="CPF",
    keyboard=KeyboardType.NUMBER,
    on_change=lambda e: app.set_state(cpf=e.value),
)
```

### Props

Além dos props de variante compartilhados (`field_variant` / `size` /
`color_scheme` / `theme` / `media`):

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `mask` | `str` | `""` | O padrão de máscara (`9` dígito, `A` letra, senão literal). |
| `value` | `str` | `""` | O texto atual. |
| `placeholder` | `str` | `""` | A dica mostrada com o campo vazio. |
| `keyboard` | `KeyboardType` | `KeyboardType.TEXT` | O teclado virtual pedido. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler chamado com um `TextChangeEvent` a cada edição. |

!!! tip "O renderizador traduz a máscara para a notação nativa"
    Você escreve a máscara na notação `9`/`A`/literal do `tempest-core`; cada
    renderizador a converte para o seu formato de input-mask nativo. O valor
    carregado no `TextChangeEvent` reflete o texto já mascarado.

## Recapitulando

- **Três famílias**, três resolvers: FIELD (`resolve_field_variant`), SELECTION
  (`resolve_selection_variant`) e SLIDER (`resolve_slider_variant`) — todas puras
  e no engine, com override do chamador mesclado por cima.
- **`FieldVariant`**: `OUTLINE` (padrão) → `FILLED` → `FLUSHED`; o `color_scheme`
  só tinge o foco/caret/label do campo, nunca o preenchimento em repouso.
- **Props compartilhados**: `size` / `color_scheme` moldam a densidade e a cor;
  `theme` / `media` são entradas de build e **ficam fora da IR**.
- **`state_styles()`** dá a tabela por `ComponentState`; só o mapeamento
  evento→estado mora no renderizador. `PRESSED` num campo é tratado como `FOCUS`.
- **`KeyboardType`** (`TEXT` / `NUMBER` / `EMAIL` / `PHONE` / `URL` / `PASSWORD`)
  escolhe o teclado virtual; `Input` e `MaskedInput` o carregam.
- **Nuances por widget**: o `error` do `Input` dispara o `invalid`; o `checked` do
  `Checkbox`/`Switch` entra na resolução; o `field_variant` do `PinInput` é
  congelado em `OUTLINE`.
