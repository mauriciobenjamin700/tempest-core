# Formulários BR & seletores de mídia

Formulário de cadastro no Brasil é sempre o mesmo enredo: e-mail, senha,
telefone, CPF ou CNPJ, endereço — e, quase sempre, uma foto e um documento pra
anexar. O `tempest-core` traz esses campos **prontos, rotulados e com máscara**,
mais os três seletores de mídia. Cada um é um `Component` que **abaixa** para os
widgets primitivos (`Input` / `MaskedInput` / `FilePicker` / `Image`), então
funciona igual nos dois renderizadores (Qt e Compose) sem mudar nada. 🚀

!!! info "O que você aprende aqui"
    - Os seis **campos brasileiros** rotulados e qual máscara cada um aplica.
    - Por que cada campo mascarado/validado **pareia com um validator** de
      `tempest_core.validators` — a máscara formata, o validator confere.
    - Como o `AddressInput` **agrupa** sete campos sob um único `on_change`.
    - Os três **seletores de mídia** e por que o `button_label` é localizável.
    - Por que o `ImagePicture` é o seletor **circular** de foto de perfil, e não
      um `Avatar`.

## Campos brasileiros

Os seis campos compartilham a mesma base (`_BRField`): todos recebem um `value`
controlado, um `label` acima, um `placeholder`, uma linha de `error` embaixo (na
cor de erro do tema) e um `on_change` que recebe **a string nova** — você nunca
toca no objeto de evento. Todos também repassam `field_variant` / `size` /
`color_scheme` / `theme` / `media` para o input interno, que resolve sua
aparência Material 3 contra o tema (dark mode e cor de marca de graça).

!!! tip "A máscara formata; o validator confere"
    Máscara e validação são coisas diferentes. `MaskedInput` só **formata** os
    dígitos enquanto o usuário digita — ela não garante que o CPF é válido. Para
    isso, pareie cada campo com o validator irmão de
    [`tempest_core.validators`](../reference.md): `validate_email`,
    `validate_phone`, `validate_cpf`, `validate_cnpj`. A máscara é UX; o validator
    é regra de negócio.

## `EmailInput`

Um campo de e-mail rotulado, com o **teclado de e-mail**, um ícone de envelope e o
`EMAIL_PATTERN` embutido. No caso mínimo você só passa `on_change`:

```python
from tempest_core import EmailInput

email = EmailInput(
    value="",
    on_change=lambda v: app.set_state(email=v),  # (1)!
)
```

1. O handler recebe **a string nova** diretamente — não um evento. Ele pode ser
   síncrono ou `async`.

Valide com `validate_email` de [`tempest_core.validators`](../reference.md), e
mostre a mensagem devolvendo-a em `error`:

```python
from tempest_core import EmailInput
from tempest_core.validators import validate_email

def on_email(value: str) -> None:
    erro = "" if validate_email(value) else "E-mail inválido"
    app.set_state(email=value, email_error=erro)

email = EmailInput(
    value=app.state.email,
    label="Seu e-mail",
    placeholder="voce@exemplo.com",
    error=app.state.email_error,
    on_change=on_email,
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O valor atual (controlado). |
| `label` | `str` | `"E-mail"` | O rótulo mostrado acima do campo (omitido se vazio). |
| `placeholder` | `str` | `""` | A dica do campo vazio. |
| `error` | `str` | `""` | A mensagem de validação; na cor de erro do tema. |
| `on_change` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a string nova a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento do input interno (outline / filled / flushed). |
| `size` | `ResponsiveSize` | `MD` | A densidade — um `Size` ou um mapa por breakpoint. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3 que o foco do campo pinta. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o campo + as cores de label/erro. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! note "O teclado e o ícone já vêm setados"
    O `EmailInput` fixa `keyboard=EMAIL`, `leading_icon="mail"` e
    `pattern=EMAIL_PATTERN` no input interno — você não precisa (nem consegue)
    trocá-los pela API do componente. Esses três defaults são o motivo de existir
    um `EmailInput` em vez de um `Input` cru.

## `PasswordInput`

Um campo de senha rotulado: **seguro** (texto oculto), com ícone de cadeado e o
**botão de olho** embutido para mostrar/ocultar. O `label` e o `placeholder` já
vêm com `"Senha"`:

```python
from tempest_core import PasswordInput

senha = PasswordInput(
    value=app.state.senha,
    error=app.state.senha_error,
    on_change=lambda v: app.set_state(senha=v),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O valor atual (controlado). |
| `label` | `str` | `"Senha"` | O rótulo mostrado acima do campo (omitido se vazio). |
| `placeholder` | `str` | `"Senha"` | A dica do campo vazio. |
| `error` | `str` | `""` | A mensagem de validação; na cor de erro do tema. |
| `on_change` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a string nova a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento do input interno. |
| `size` | `ResponsiveSize` | `MD` | A densidade. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o campo + as cores de label/erro. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! info "Seguro por construção"
    O `PasswordInput` fixa `secure=True` e `leading_icon="lock"` no input interno.
    O toggle de olho vem do próprio `Input` seguro — você não precisa cablear nada
    para o usuário conseguir revelar a senha.

## `PhoneInput`

Um campo de telefone brasileiro, **mascarado** `(99) 99999-9999`, com o teclado
numérico de telefone. Cada `9` é um dígito; parênteses, espaço e hífen são
inseridos automaticamente enquanto o usuário digita:

```python
from tempest_core import PhoneInput
from tempest_core.validators import validate_phone

def on_phone(value: str) -> None:
    erro = "" if validate_phone(value) else "Telefone inválido"
    app.set_state(telefone=value, telefone_error=erro)

telefone = PhoneInput(
    value=app.state.telefone,
    error=app.state.telefone_error,
    on_change=on_phone,
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O valor atual (controlado). |
| `label` | `str` | `"Telefone"` | O rótulo mostrado acima do campo (omitido se vazio). |
| `placeholder` | `str` | `""` | A dica do campo vazio. |
| `error` | `str` | `""` | A mensagem de validação; na cor de erro do tema. |
| `on_change` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a string nova a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento do input interno. |
| `size` | `ResponsiveSize` | `MD` | A densidade. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o campo + as cores de label/erro. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! warning "A máscara `(99) 99999-9999` cobre o celular de 9 dígitos"
    A máscara é fixa e desenhada para o celular brasileiro (DDD + nove dígitos).
    O `on_change` reporta o valor **como está no campo** (com a máscara) — use
    `validate_phone` para conferir e, se precisar do número cru, remova a máscara
    no seu handler antes de persistir.

## `CPFInput`

Um campo de CPF rotulado, **mascarado** `999.999.999-99`, teclado numérico. Pareie
com `validate_cpf` (que confere os dígitos verificadores, não só o formato):

```python
from tempest_core import CPFInput
from tempest_core.validators import validate_cpf

def on_cpf(value: str) -> None:
    erro = "" if validate_cpf(value) else "CPF inválido"
    app.set_state(cpf=value, cpf_error=erro)

cpf = CPFInput(
    value=app.state.cpf,
    error=app.state.cpf_error,
    on_change=on_cpf,
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O valor atual (controlado). |
| `label` | `str` | `"CPF"` | O rótulo mostrado acima do campo (omitido se vazio). |
| `placeholder` | `str` | `""` | A dica do campo vazio. |
| `error` | `str` | `""` | A mensagem de validação; na cor de erro do tema. |
| `on_change` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a string nova a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento do input interno. |
| `size` | `ResponsiveSize` | `MD` | A densidade. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o campo + as cores de label/erro. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! danger "Máscara não é validação de CPF"
    `999.999.999-99` só formata onze dígitos — `111.111.111-11` passa na máscara e
    é um CPF inválido. **Sempre** pareie o `CPFInput` com `validate_cpf`, que roda
    o algoritmo dos dígitos verificadores. Confiar só na máscara deixa CPF falso
    entrar no banco.

## `CNPJInput`

Um campo de CNPJ rotulado, **mascarado** `99.999.999/9999-99`, teclado numérico.
Pareie com `validate_cnpj`:

```python
from tempest_core import CNPJInput
from tempest_core.validators import validate_cnpj

def on_cnpj(value: str) -> None:
    erro = "" if validate_cnpj(value) else "CNPJ inválido"
    app.set_state(cnpj=value, cnpj_error=erro)

cnpj = CNPJInput(
    value=app.state.cnpj,
    error=app.state.cnpj_error,
    on_change=on_cnpj,
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | O valor atual (controlado). |
| `label` | `str` | `"CNPJ"` | O rótulo mostrado acima do campo (omitido se vazio). |
| `placeholder` | `str` | `""` | A dica do campo vazio. |
| `error` | `str` | `""` | A mensagem de validação; na cor de erro do tema. |
| `on_change` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a string nova a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento do input interno. |
| `size` | `ResponsiveSize` | `MD` | A densidade. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `theme` | `Theme` | `Theme()` | O tema que resolve o campo + as cores de label/erro. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! danger "O mesmo vale para o CNPJ"
    A máscara `99.999.999/9999-99` formata quatorze dígitos, mas não confere os
    verificadores. Pareie **sempre** com `validate_cnpj`.

## `AddressInput`

Um bloco de endereço brasileiro **agrupado**: em vez de sete componentes soltos,
o `AddressInput` renderiza uma `Column` rotulada com CEP (mascarado `99999-999`),
rua, número, complemento, bairro, cidade e UF de uma vez. Um **único** `on_change`
é chamado como `on_change(field_name, new_value)`, onde `field_name` é um de
`"cep"`, `"street"`, `"number"`, `"complement"`, `"neighborhood"`, `"city"` ou
`"state"`:

```python
from tempest_core import AddressInput

def on_address(field_name: str, value: str) -> None:  # (1)!
    app.set_state(**{field_name: value})

endereco = AddressInput(
    cep=app.state.cep,
    street=app.state.street,
    number=app.state.number,
    complement=app.state.complement,
    neighborhood=app.state.neighborhood,
    city=app.state.city,
    state=app.state.state,
    on_change=on_address,
)
```

1. Repare na **assinatura de dois argumentos**: o `AddressInput` avisa **qual**
   campo mudou, então um só handler atualiza o estado do campo certo.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `cep` | `str` | `""` | O CEP atual (mascarado `99999-999`). |
| `street` | `str` | `""` | A rua atual. |
| `number` | `str` | `""` | O número atual. |
| `complement` | `str` | `""` | O complemento atual. |
| `neighborhood` | `str` | `""` | O bairro atual. |
| `city` | `str` | `""` | A cidade atual. |
| `state` | `str` | `""` | A UF atual. |
| `label` | `str` | `"Endereço"` | O título do bloco (omitido se vazio). |
| `on_change` | `Callable[[str, str], Any]` | *(obrigatório)* | Chamado como `on_change(field_name, new_value)` a cada edição. |
| `field_variant` | `FieldVariant` | `OUTLINE` | O tratamento dos inputs internos. |
| `size` | `ResponsiveSize` | `MD` | A densidade dos inputs. |
| `color_scheme` | `str` | `"primary"` | A família de papéis M3. |
| `theme` | `Theme` | `Theme()` | O tema que resolve os campos + a cor do título. |
| `media` | `MediaQueryData \| None` | `None` | Snapshot de viewport para um `size` responsivo. |

!!! note "Um handler, muitos campos"
    Diferente dos campos simples (que chamam `on_change(value)`), o `AddressInput`
    chama `on_change(field_name, value)`. É o único campo BR com essa assinatura de
    dois argumentos — ela existe porque o bloco reúne sete inputs sob um único
    handler. Só o CEP é mascarado; rua, número, complemento, bairro, cidade e UF
    são inputs de texto simples.

## Seletores de mídia

Os três seletores abaixam para o `FilePicker` (e, no caso dos que mostram prévia,
para o `Image`). Todos expõem um `on_pick` que recebe **a URI do arquivo
escolhido** — nunca o objeto de evento. O `on_pick` pode ser `async`: o valor
devolvido é repassado ao dispatcher e aguardado, então carregar/analisar o
arquivo escolhido dentro do handler funciona sem deixar coroutine órfã.

## `ImagePicker`

Um seletor de imagem rotulado com **prévia inline**: assim que uma URI é
escolhida, ele mostra a imagem (160×160, cantos arredondados) acima do botão:

```python
from tempest_core import ImagePicker

foto = ImagePicker(
    value=app.state.foto_uri,
    label="Foto do produto",
    button_label="Escolher imagem",  # (1)!
    on_pick=lambda uri: app.set_state(foto_uri=uri),
)
```

1. O `button_label` é **localizável** — passe o texto no idioma do app. O padrão
   `"Choose image"` está em inglês de propósito, para forçar a decisão de locale.

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | A URI da imagem escolhida (vazia até escolher). Quando setada, aparece uma prévia. |
| `label` | `str` | `""` | Um título opcional acima do seletor (omitido se vazio). |
| `button_label` | `str` | `"Choose image"` | A legenda do botão do seletor (localize-a por idioma do app). |
| `on_pick` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a URI da imagem escolhida. |

!!! tip "Localize o `button_label`"
    Tanto o `ImagePicker` quanto o `DocumentPicker` têm o `button_label` como prop
    justamente para você traduzir a legenda do botão. O padrão vem em inglês
    (`"Choose image"` / `"Choose document"`) — troque-o pela string do locale do
    app, como `"Escolher imagem"`.

## `DocumentPicker`

Um seletor de documento rotulado. Igual ao `ImagePicker`, mas **sem prévia** — um
documento não é uma imagem para exibir:

```python
from tempest_core import DocumentPicker

anexo = DocumentPicker(
    value=app.state.doc_uri,
    label="Comprovante",
    button_label="Escolher documento",
    on_pick=lambda uri: app.set_state(doc_uri=uri),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `value` | `str` | `""` | A URI do documento escolhido (vazia até escolher). |
| `label` | `str` | `""` | Um título opcional acima do seletor (omitido se vazio). |
| `button_label` | `str` | `"Choose document"` | A legenda do botão do seletor (localize-a por idioma do app). |
| `on_pick` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a URI do documento escolhido. |

## `ImagePicture`

O seletor **circular** de foto de perfil: uma foto redonda sobre um botão de
troca. Diferente do `Avatar` (que mostra iniciais), o `ImagePicture` recorta a
imagem escolhida num círculo e, sem foto, cai num **placeholder de ícone `user`**.
O `size` é o diâmetro do círculo em pixels lógicos:

```python
from tempest_core import ImagePicture

perfil = ImagePicture(
    src=app.state.avatar_uri,
    size=96.0,
    on_pick=lambda uri: app.set_state(avatar_uri=uri),
)
```

### Props

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `src` | `str` | `""` | A URI da foto atual (vazia mostra o placeholder). |
| `size` | `float` | `96.0` | O diâmetro do círculo em pixels lógicos. |
| `on_pick` | `Callable[[str], Any]` | *(obrigatório)* | Chamado com a URI da foto escolhida. |

!!! note "`ImagePicture` é seletor; `Avatar` é exibição"
    Os dois são redondos, mas resolvem problemas diferentes. O `Avatar` **mostra**
    uma identidade (foto ou iniciais) e não deixa trocar. O `ImagePicture`
    **coleta** uma foto: clipe circular quando há `src`, ícone `user` quando não
    há, e sempre um `FilePicker` de troca embaixo. Use `ImagePicture` na tela de
    edição de perfil; use `Avatar` em qualquer lugar que só exibe.

## Recapitulando

- **Seis campos brasileiros** rotulados: `EmailInput`, `PasswordInput`,
  `PhoneInput`, `CPFInput`, `CNPJInput` e o agrupado `AddressInput` — todos com
  `value` controlado, `label`, `error` e `on_change(value)`.
- **Máscara formata, validator confere**: pareie os campos mascarados/validados
  com `validate_email` / `validate_phone` / `validate_cpf` / `validate_cnpj` de
  `tempest_core.validators`. Máscara é UX; validação é regra.
- **`AddressInput` é agrupado**: sete campos (CEP mascarado + seis de texto) sob
  um único `on_change(field_name, new_value)`.
- **Três seletores de mídia**: `ImagePicker` (com prévia inline), `DocumentPicker`
  (sem prévia) e `ImagePicture` (foto de perfil circular). Todos com `on_pick(uri)`
  que aceita `async`.
- **`button_label` é localizável** no `ImagePicker`/`DocumentPicker` — o padrão em
  inglês existe para forçar a tradução por locale.
- **`ImagePicture` coleta, `Avatar` exibe**: o seletor circular recorta a foto num
  círculo com fallback de ícone `user`; o `Avatar` só mostra.
