# Botões

Os botões são a afordância tapável mais básica do `tempest-core`. Há dois:
**`Button`** (com texto) e **`IconButton`** (só ícone). Os dois compartilham a
**API de variantes de ergonomia Chakra** (`variant` / `size` / `color_scheme`)
ancorada em **Material 3** — você descreve a *intenção* e um **resolver puro**
produz o `Style` concreto a partir dos tokens do `Theme`. 🚀

!!! info "O que você aprende aqui"
    - As quatro **variantes** e para qual tratamento M3 cada uma abaixa.
    - Os quatro **tamanhos** e por que um botão pequeno nunca fura o alvo de toque.
    - Como o `color_scheme` escolhe a família de cor.
    - Como o botão **resolve e assa** seu `Style`, e como ler a **tabela por estado**.

## `Button`

Um botão tapável com rótulo de texto. No caso mínimo, você só passa `label` — o
resto tem padrão sensato (`SOLID` / `MD` / `primary`):

```python
from tempest_core import Button

salvar = Button(label="Salvar")
```

Esse único `Button(label="Salvar")` já é um botão **preenchido, primário, de
densidade média** — pronto para os renderizadores. Passe um `on_click` para
reagir ao toque:

```python
from tempest_core import Button

salvar = Button(
    label="Salvar",
    on_click=lambda e: app.set_state(salvando=True),  # (1)!
    variant="solid",
    size="md",
    color_scheme="primary",
)
```

1. O handler pode ser **síncrono ou `async`** — o runtime agenda os awaitables no
   event loop. Ele recebe um `TapEvent` (veja [Referência da API](../reference.md)).

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | *(obrigatório)* | O texto mostrado no botão. |
| `on_click` | `EventHandler \| None` | `None` | Handler chamado no toque; sync ou `async`. Recebe `TapEvent`. |
| `variant` | `Variant` | `SOLID` | O tratamento visual (solid / outline / ghost / link). |
| `size` | `Size \| dict[str, Size]` | `MD` | A densidade — um `Size` só ou um mapa por breakpoint. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 (`primary` / `secondary` / `tertiary` / `error` / `neutral`). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem a variante. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para resolver um `size` responsivo. **Não entra na IR.** |

!!! note "`theme` e `media` são entradas de build, não props da IR"
    Os dois são usados **só na hora de resolver** o `Style` e ficam de fora dos
    props do nó (`prop_exclude_names`). Um `Theme` inteiro por nó incharia a árvore
    e o payload serializado da ponte — o `style` resolvido já carrega o efeito
    deles.

### Variantes

O `variant` escolhe a ênfase; o resolver H1
(`resolve_variant`) o mapeia para um tratamento Material 3. O `color_scheme`
decide *qual* família de cor pinta esse tratamento.

| `Variant` | Tratamento M3 | Fundo | Conteúdo | Borda |
| --- | --- | --- | --- | --- |
| `SOLID` | *filled button* | cor do papel | `on_*` legível | — |
| `OUTLINE` | *outlined button* | transparente | cor do papel | mesma cor do papel |
| `GHOST` | *text button* (sem sublinhado) | transparente | cor do papel | — |
| `LINK` | texto inline sublinhado | transparente | cor do papel | — |

```python
from tempest_core import Button, Row

barra = Row(
    children=[
        Button(label="Salvar", variant="solid"),  # ênfase máxima
        Button(label="Cancelar", variant="outline"),  # ênfase média
        Button(label="Pular", variant="ghost"),  # ênfase baixa
        Button(label="Saiba mais", variant="link"),  # inline
    ]
)
```

!!! tip "Escala de ênfase"
    `SOLID` → `OUTLINE` → `GHOST` → `LINK` é uma escala de **maior para menor
    ênfase**. Reserve `SOLID` para a ação primária da tela; use `GHOST` para ações
    secundárias que não devem competir com ela.

### Tamanhos e o alvo de toque

`size` aceita um `Size` único (`XS` / `SM` / `MD` / `LG`) ou um **mapa por
breakpoint** para densidade responsiva:

```python
from tempest_core import Button
from tempest_core import Size

# Compacto no mobile, folgado a partir do breakpoint "md".
responsivo = Button(label="Enviar", size={"base": Size.SM, "md": Size.LG})
```

!!! warning "Um botão pequeno reduz densidade, nunca o alvo de toque"
    Todos os tamanhos garantem `min_height = 48.0` (`MIN_TOUCH_TARGET`, o alvo de
    48dp do Material). Diminuir o `size` reduz o padding/tipografia visual, mas a
    área tapável **nunca** fica abaixo de 48dp — acessibilidade motora fica
    preservada por construção.

### Como o `Style` é resolvido e assado

Na construção, o `Button` roda um `model_validator(mode="after")` que:

1. captura seu `style` explícito como **override**;
2. resolve o `Style` base de `variant` / `size` / `color_scheme` contra o `theme`
   (via `resolve_variant`);
3. **mescla o override por cima** do base (os campos setados do override vencem);
4. assa o resultado em `.style`, então os renderizadores consomem um `Style`
   plano, sem saber que houve resolução.

```python
from tempest_core import Button
from tempest_core import Style

# O override ganha nos campos que ele seta; o resto vem da variante resolvida.
custom = Button(label="Perigo", color_scheme="error", style=Style(radius=999.0))
```

!!! info "Override sempre por cima"
    Isso mantém a retrocompatibilidade: `Button(label=...)` sem `style` dá o botão
    da variante; `Button(label=..., style=…)` estiliza à mão por cima. Você nunca
    perde a variante ao setar um campo pontual.

### Tabela por estado (hover / press / disabled / focus)

`resolve_variant` é puro e mora no engine — mas os botões reais têm **estados de
interação**. O método `state_styles()` devolve o `Style` resolvido para cada
`ComponentState`, já com o override do chamador mesclado por cima:

```python
from tempest_core import Button
from tempest_core import ComponentState

botao = Button(label="Salvar", color_scheme="primary")
estados = botao.state_styles()

estados[ComponentState.DEFAULT]  # repouso
estados[ComponentState.HOVER]  # ponteiro em cima (state layer M3)
estados[ComponentState.PRESSED]  # sendo tocado
estados[ComponentState.DISABLED]  # inativo (opacidade reduzida)
estados[ComponentState.FOCUS]  # foco de teclado/leitor
```

!!! note "A resolução é pura; só o mapeamento evento→estado mora no renderizador"
    O core produz a **tabela** de estados de forma determinística. Aplicar a
    *state layer* do Material 3 no evento certo de ponteiro/foco é a única parte que
    vive nos renderizadores (Qt / Compose) — mantém o core sem tocar em pixels.

## `IconButton`

Um botão **só de ícone**, quadrado/circular. Ele *é* um botão, então reusa
`resolve_variant` igual ao `Button` — e então fixa `width`/`height` no
`min_height` resolvido (uma caixa quadrada de pelo menos 48dp) e um `radius`
circular, **usando só campos de `Style` existentes** (nenhum campo novo). O
padrão é a variante `GHOST` (a mais discreta, focada no ícone):

```python
from tempest_core import IconButton

fechar = IconButton(icon="close", label="Fechar diálogo")  # (1)!
ajustes = IconButton(icon="settings", color_scheme="primary", label="Abrir ajustes")
```

1. O `icon` é um valor curado de `Icons` (ou sua string), ou um nome de ícone de
   plataforma qualquer.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `icon` | `Icons \| str` | *(obrigatório)* | O ícone — valor curado de `Icons` ou nome de plataforma. |
| `on_click` | `EventHandler \| None` | `None` | Handler no toque; sync ou `async`. |
| `variant` | `Variant` | `GHOST` | O tratamento visual — padrão `GHOST`. |
| `size` | `Size \| dict[str, Size]` | `MD` | A densidade. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `label` | `str` | `""` | O **nome acessível** (a11y / `Semantics`) do botão sem texto. |
| `theme` | `Theme` | `Theme()` | O tema. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport. **Não entra na IR.** |

!!! danger "Sempre passe `label` num `IconButton`"
    Um botão só de ícone não tem texto visível, então o `label` carrega o **nome
    acessível** (`contentDescription` / accessible label) que os renderizadores
    roteiam para a superfície de acessibilidade do nó. Sem ele, o botão fica mudo
    para leitores de tela. Não é opcional na prática — é acessibilidade.

### Geometria quadrada/circular

O `IconButton` fixa a geometria via `_squareify`: `width` e `height` recebem o
`min_height` resolvido (≥ 48dp), e `radius` recebe metade disso (um círculo). Tudo
com campos de `Style` já existentes — a área de toque nunca cai abaixo de 48dp,
como no `Button`. A tabela por estado (`state_styles()`) devolve cada estado já
fixado nessa geometria.

## Recapitulando

- **Dois botões**, uma API: `Button` (texto) e `IconButton` (ícone) resolvem via
  `resolve_variant` a partir de `variant` / `size` / `color_scheme`.
- **Variantes**: `SOLID` (filled) → `OUTLINE` (outlined) → `GHOST` (text) →
  `LINK` (inline), de maior para menor ênfase.
- **Tamanhos**: `XS` / `SM` / `LG` / `MD` ou mapa por breakpoint; `min_height`
  garante o alvo de toque de 48dp em qualquer tamanho.
- **Style resolvido e assado**: o override do chamador sempre é mesclado por cima
  da variante resolvida.
- **`state_styles()`** dá a tabela por `ComponentState`; só o mapeamento
  evento→estado mora no renderizador.
- **`IconButton`** é quadrado/circular, `GHOST` por padrão, e **exige `label`**
  para acessibilidade.
