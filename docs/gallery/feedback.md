# Feedback

A camada de **Feedback** (Trilho H4) são as superfícies de status *inline* — nada
de sobreposição (snackbar, toast, diálogo): isso precisa de uma camada de
empilhamento e fica de fora daqui. São seis componentes: **`Alert`** e
**`Banner`** (blocos de status), **`Badge`** (pílula compacta), **`EmptyState`**
(placeholder de tela vazia), **`Stat`** (métrica com tendência) e
**`ProgressStepper`** (passos numerados de um fluxo). Todos falam a mesma
**API de variantes de ergonomia Chakra** (`variant` / `color_scheme`) ancorada em
**Material 3**: você descreve a *intenção de status* e um **resolver puro** produz
o `Style` concreto a partir dos tokens do `Theme`. 🚦

!!! info "O que você aprende aqui"
    - As **famílias de status** `success` / `warning` / `info` (mais `error` /
      `neutral` / `primary`…) e como o `color_scheme` escolhe qual pinta.
    - As **variantes de `Badge`** (`resolve_badge_variant`) e de `Alert`/`Banner`
      (`resolve_alert_variant`), e para qual tratamento M3 cada uma abaixa.
    - Por que o padrão `SUBTLE` usa o par tonal `*_container` / `on_*_container` —
      e como isso mantém o **contraste WCAG-AA** que um papel saturado no branco
      quebraria.
    - O mapeamento legado `tone` → `color_scheme`, retrocompatível.
    - Como `Stat` tinge o delta com `success` (alta) ou `error` (baixa), e como o
      `ProgressStepper` colore passos feitos/ativos vs. pendentes.

## `Badge`

Uma **pílula de status** pequena e inline — um contador (`"3"`) ou um rótulo
curto (`"NEW"`). No caso mínimo você só passa `label`; o resto tem padrão sensato
(`SOLID` / `SM` / derivado do `tone`, que começa em `"error"`):

```python
from tempest_core import Badge

nao_lidas = Badge(label="3")
```

Passe `color_scheme` e `variant` para a API H4 completa:

```python
from tempest_core import Badge, BadgeVariant

novo = Badge(label="NEW", color_scheme="success", variant=BadgeVariant.SUBTLE)  # (1)!
```

1. `variant` aceita o enum `BadgeVariant` ou sua string (`"subtle"`) — os dois
   resolvem igual pelo `resolve_badge_variant`.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | O texto da pílula (um contador como `"3"` ou `"NEW"`). |
| `tone` | `str` | `"error"` | A **tonalidade legada**, mapeada em `color_scheme` quando este é `None`. |
| `color_scheme` | `str \| None` | `None` | A família de status M3; derivada de `tone` quando `None`. |
| `variant` | `BadgeVariant` | `SOLID` | O tratamento da pílula (solid / subtle / outline). |
| `size` | `ResponsiveSize` | `SM` | A densidade — um `Size` só ou um mapa por breakpoint. |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem o tratamento. **Não entra na IR.** |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. **Não entra na IR.** |

### Variantes do `Badge`

O `variant` escolhe a ênfase; `resolve_badge_variant` o abaixa para um tratamento
Material 3, e o `color_scheme` decide *qual* família de cor pinta:

| `BadgeVariant` | Tratamento M3 | Fundo | Conteúdo | Borda |
| --- | --- | --- | --- | --- |
| `SOLID` | pílula preenchida | cor do papel | `on_*` legível | — |
| `SUBTLE` | tonal de baixa ênfase | `*_container` | `on_*_container` | — |
| `OUTLINE` | contorno transparente | transparente | cor do papel | mesma cor do papel |

!!! warning "Por que `SUBTLE` não usa o papel saturado direto: contraste WCAG-AA"
    Um papel de status saturado sobre branco pode **falhar no WCAG-AA** — está
    verificado no engine que `success` sólido dá ≈ **3.02** de contraste (abaixo do
    mínimo 4.5 para texto). Por isso o tratamento `SUBTLE` (o padrão de `Alert` e
    `Banner`) usa o **par tonal** `*_container` / `on_*_container` (≈ **13.7** de
    contraste), que passa no AA **por construção** na paleta tonal M3. Ou seja: um
    `success` de baixa ênfase legível não é o verde forte com texto por cima — é o
    *container* verde-claro com o *on-container* escuro.

## `Alert`

Um **callout de status em bloco**: glifo opcional, título (negrito), corpo
opcional e um widget de dispensa opcional. É o irmão mais rico do `Banner`, e
abaixa pelo mesmo `resolve_alert_variant`. O padrão é `SUBTLE` na família `"info"`:

```python
from tempest_core import Alert

aviso = Alert(
    title="Backup concluído",
    body="Seus dados foram salvos com sucesso.",
    color_scheme="success",
    glyph="✅",
)
```

Use `variant=LEFT_ACCENT` para o callout clássico de borda acentuada, e passe um
`dismiss` para o botão de fechar:

```python
from tempest_core import Alert, AlertVariant, IconButton

erro = Alert(
    title="Falha ao enviar",
    body="Verifique sua conexão e tente de novo.",
    color_scheme="error",
    variant=AlertVariant.LEFT_ACCENT,
    dismiss=IconButton(icon="close", label="Dispensar alerta"),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | O título do alerta (negrito). |
| `body` | `str \| None` | `None` | Uma linha secundária de detalhe. |
| `glyph` | `str \| None` | `None` | Um glifo de texto à frente (sem fonte de ícone). |
| `color_scheme` | `str` | `"info"` | A família de status M3 com que tingir. |
| `variant` | `AlertVariant` | `SUBTLE` | O tratamento (subtle / solid / left_accent / top_accent). |
| `dismiss` | `Widget \| None` | `None` | Widget de dispensa opcional à direita (ex.: um `IconButton` de fechar). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem o tratamento. **Não entra na IR.** |

### Variantes do `Alert` (e `Banner`)

`resolve_alert_variant` abaixa o `variant` para um tratamento de bloco M3. Um
alerta é **não-interativo** (sem *state layer*, como uma superfície) — não há
tabela por estado:

| `AlertVariant` | Tratamento M3 | Fundo | Conteúdo | Acento |
| --- | --- | --- | --- | --- |
| `SUBTLE` | tonal de baixa ênfase (padrão) | `*_container` | `on_*_container` | — |
| `SOLID` | preenchido de alta ênfase | cor do papel | `on_*` legível | — |
| `LEFT_ACCENT` | fill subtle + regra direcional | `*_container` | `on_*_container` | borda de 4px na borda inicial, cor do papel |
| `TOP_ACCENT` | fill subtle + regra direcional | `*_container` | `on_*_container` | borda de 4px no topo, cor do papel |

!!! note "As bordas de acento espelham sob RTL"
    `LEFT_ACCENT` desenha a regra na borda **inicial** (esquerda em LTR); os
    renderizadores espelham o lado físico esquerdo/direito sob RTL pelo mesmo flag
    `rtl` que já usam na borda inferior do campo `flushed`. Você descreve *início*,
    não *esquerda*.

## `Banner`

Uma **barra de status inline** com uma mensagem que cresce e uma ação opcional à
direita — mais enxuta que o `Alert`, sem título/corpo separados. Abaixa pelo mesmo
`resolve_alert_variant`, então `variant` e `color_scheme` funcionam igual:

```python
from tempest_core import Banner, Button

manutencao = Banner(
    message="Manutenção programada às 02h.",
    color_scheme="warning",
    action=Button(label="Detalhes", variant="ghost"),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `message` | `str` | `""` | O texto do banner. |
| `tone` | `str` | `"info"` | A **tonalidade legada**, mapeada em `color_scheme` quando este é `None`. |
| `color_scheme` | `str \| None` | `None` | A família de status M3; derivada de `tone` quando `None`. |
| `variant` | `AlertVariant` | `SUBTLE` | O tratamento (subtle / solid / left_accent / top_accent). |
| `action` | `Widget \| None` | `None` | Widget opcional à direita (ex.: um `Button` de dispensa). |
| `theme` | `Theme` | `Theme()` | O tema cujos tokens resolvem o tratamento. **Não entra na IR.** |

!!! tip "O par `tone` → `color_scheme` é o caminho de retrocompatibilidade"
    `Banner` e `Badge` nasceram com a prop `tone` (`"info"` / `"success"` /
    `"warning"` / `"error"`). Com a H4 essa prop virou um **atalho legado**:
    quando `color_scheme` é `None`, ele é derivado de `tone` (`_tone_scheme`, com
    fallback em `"info"`). Ou seja, `Banner(tone="success")` continua funcionando
    intacto; para a família completa (ex.: `"primary"`, `"neutral"`, `"tertiary"`)
    passe `color_scheme` direto — ele **vence** o `tone`.

## `EmptyState`

Um **placeholder centralizado** para telas vazias: um glifo grande, título,
subtítulo opcional e uma ação opcional. Sem famílias de status aqui — ele lê os
tons neutros do tema (`ON_SURFACE` no título, `ON_SURFACE_VARIANT` mudo no glifo e
no subtítulo) e o espaçamento da escala do tema:

```python
from tempest_core import EmptyState, Button

vazio = EmptyState(
    title="Nenhum pedido ainda",
    subtitle="Quando você fizer um pedido, ele aparece aqui.",
    glyph="📦",
    action=Button(label="Explorar catálogo"),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `title` | `str` | `""` | A mensagem principal. |
| `subtitle` | `str \| None` | `None` | Uma linha secundária opcional. |
| `glyph` | `str` | `"○"` | Um glifo de texto grande acima do título (sem fonte de ícone). |
| `action` | `Widget \| None` | `None` | Widget de call-to-action opcional (ex.: um `Button`). |
| `theme` | `Theme` | `Theme()` | O tema que fornece cores e espaçamento. **Não entra na IR.** |

!!! note "Nada de `*NotFoundError` na UI — o vazio é um estado válido"
    O `EmptyState` existe justamente para tratar "a consulta não retornou nada"
    como um **resultado bem-sucedido**, não um erro. Renderize-o quando uma coleção
    vier vazia, em vez de mostrar uma tela de erro.

## `Stat`

Uma **métrica rotulada**: um rótulo mudo sobre um valor grande, com uma linha de
`delta` opcional para a tendência. O delta é tingido pela família de status
**`success`** (alta) ou **`error`** (baixa) conforme `delta_up`, com a seta
canônica "▲" / "▼":

```python
from tempest_core import Stat

receita = Stat(label="Receita", value="R$ 128k", delta="+12%", delta_up=True)
churn = Stat(label="Churn", value="4,1%", delta="-0,3%", delta_up=False)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `label` | `str` | `""` | A legenda da métrica (muda). |
| `value` | `str` | `""` | O valor da métrica (grande, em destaque). |
| `delta` | `str \| None` | `None` | Uma linha de tendência opcional (ex.: `"+12%"`); `None` a esconde. |
| `delta_up` | `bool` | `True` | Se o delta é positivo (tinge `success`) ou negativo (tinge `error`). |
| `theme` | `Theme` | `Theme()` | O tema que fornece cores e espaçamento. **Não entra na IR.** |

!!! warning "`delta_up` é semântico, não cosmético"
    `delta_up` diz se a tendência é **positiva ou negativa** — e é isso que decide
    a cor (`success` vs. `error`) e a seta (▲ vs. ▼). Numa métrica onde "menos é
    melhor" (churn, latência, custo), uma **queda** é positiva: passe
    `delta_up=True` mesmo com um delta de texto `"-0,3%"`, para que ela apareça em
    verde. A cor segue o *sentido* da métrica, não o sinal do número.

## `ProgressStepper`

Um **stepper horizontal** de fluxo/assistente: cada passo é um círculo numerado
(disco de acento preenchido para feito/ativo, contorno mudo para pendente) acima
do rótulo, unidos por regras conectoras. Os passos até `current` (inclusive) leem
o `color_scheme`; os pendentes leem o `ON_SURFACE_VARIANT` mudo:

```python
from tempest_core import ProgressStepper

fluxo = ProgressStepper(
    steps=["Carrinho", "Entrega", "Pagamento", "Revisão"],
    current=1,  # (1)!
    color_scheme="primary",
)
```

1. `current=1` marca o passo de índice 1 ("Entrega") como ativo; os anteriores
   ("Carrinho") contam como feitos, os posteriores como pendentes.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `steps` | `list[str]` | `[]` | Os rótulos dos passos, em ordem. |
| `current` | `int` | `0` | O índice do passo ativo (os anteriores contam como feitos). |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que os passos feitos/ativos pintam. |
| `theme` | `Theme` | `Theme()` | O tema que resolve as cores e o espaçamento dos passos. **Não entra na IR.** |

!!! note "Por que `ProgressStepper` e não `Stepper`"
    O nome evita colidir com o `Stepper` numérico (o *spinner* de +/− da camada de
    campos). Um é um indicador de **progresso** de várias etapas; o outro é um
    **input** de número. Nomes distintos, papéis distintos.

## Recapitulando

- **Seis superfícies inline**: `Alert` / `Banner` (blocos), `Badge` (pílula),
  `EmptyState` (tela vazia), `Stat` (métrica) e `ProgressStepper` (passos) — nada
  de sobreposição (toast/diálogo) fica aqui.
- **Famílias de status**: `success` / `warning` / `info` (mais `error` /
  `neutral` / `primary` / …) via `color_scheme`; `Badge` resolve por
  `resolve_badge_variant`, `Alert`/`Banner` por `resolve_alert_variant`.
- **Variantes**: `Badge` → `SOLID` / `SUBTLE` / `OUTLINE`; `Alert`/`Banner` →
  `SUBTLE` / `SOLID` / `LEFT_ACCENT` / `TOP_ACCENT`.
- **Contraste WCAG-AA**: o `SUBTLE` usa o par tonal `*_container` /
  `on_*_container` (≈ 13.7) porque o papel saturado no branco pode falhar o AA
  (`success` sólido ≈ 3.02).
- **`tone` → `color_scheme`**: prop legada retrocompatível; `color_scheme` explícito
  vence o `tone`.
- **`Stat`** tinge o delta com `success` (alta) ou `error` (baixa) por `delta_up`,
  seguindo o *sentido* da métrica.
- **`ProgressStepper`** colore feito/ativo com o `color_scheme` e deixa os
  pendentes mudos; distinto do `Stepper` numérico.
