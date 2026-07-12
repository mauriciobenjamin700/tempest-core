# Formulários

Formulários no `tempest-core` são **declarativos e validados na fronteira**: você
descreve os campos e suas regras em Python, e a validação roda **uma vez, no
Python**, produzindo um resultado estruturado e serializável em JSON — a mesma
filosofia do `parse_event`. Nada de validação espalhada pelos renderizadores. 🚀

São quatro símbolos que trabalham juntos: **`Validator`** (a regra),
**`FormField`** (o campo que embrulha um input e carrega suas regras), **`Form`**
(o contêiner que agrega campos, valida e libera o submit) e **`FormState`** (o
resultado plano da validação, pronto para morar no estado da aplicação).

!!! info "O que você aprende aqui"
    - Como um `Validator` é só um **callable puro** `(valor) -> str | None`.
    - Como um `FormField` embrulha um input como **filho** e guarda suas regras.
    - Como o `Form.validate()` roda todas as regras e **libera o submit**.
    - Como ler o `FormState` — o `dict` plano de erros + o flag `valid`.
    - Um exemplo **end-to-end** montando um form e reagindo ao submit.

## `Validator`

Um `Validator` é o tijolo mais básico: uma **função pura** que recebe o valor cru
de um campo e devolve uma **mensagem de erro** (`str`) quando o valor é inválido,
ou `None` quando ele passa. A assinatura real é um `TypeAlias`:

```python
from typing import Any, TypeAlias
from collections.abc import Callable

Validator: TypeAlias = Callable[[Any], str | None]
```

Ou seja, qualquer callable com essa forma serve como validador — inclusive
`lambda`s e closures sobre a lógica da sua aplicação:

```python
from tempest_core import Validator

def required(value: str) -> str | None:
    """Reject empty or whitespace-only values."""
    return "Este campo é obrigatório" if not value.strip() else None

def looks_like_email(value: str) -> str | None:
    """A minimal email sanity check."""
    return None if "@" in value else "Informe um e-mail válido"

# Um Validator também pode fechar sobre estado da aplicação:
def min_length(n: int) -> Validator:
    """Build a validator that requires at least ``n`` characters."""
    return lambda value: None if len(value) >= n else f"Mínimo de {n} caracteres"
```

!!! info "Validadores rodam só no Python, nunca cruzam a fronteira"
    Um `Validator` é lógica pura de aplicação — **nunca é serializado** para os
    renderizadores. Por isso ele pode fechar sobre qualquer coisa (banco, config,
    outra função). O que atravessa a ponte é apenas o **resultado** da validação
    (o `FormState`), não a regra em si.

!!! tip "A primeira regra que falha vence"
    Quando um campo tem várias regras, elas rodam **em ordem** e a **primeira** que
    devolver uma mensagem interrompe o resto (veja `FormField.run_validators`
    abaixo). Ordene do mais fundamental (`required`) para o mais específico
    (`looks_like_email`).

## `FormField`

Um `FormField` é um **wrapper rotulado** em torno de um único input. Ele carrega o
`name` do campo, a lista de `validators` e — como **filho** (`child`) — o widget de
input em si. O input é exposto como nó filho (e não como prop) para que os
renderizadores o desenhem recursivamente e ele atravesse a fronteira como qualquer
outro filho:

```python
from tempest_core import FormField, Input

email = FormField(
    name="email",                       # (1)!
    label="E-mail",
    validators=[required, looks_like_email],
    child=Input(placeholder="voce@exemplo.com"),
)
```

1. O `name` é a **chave** usada em `FormState.errors` e em `SubmitEvent.values` —
   é como o valor do campo é casado com sua regra na hora de validar.

### Campos

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `name` | `str` | *(obrigatório)* | O nome do campo — a chave em `FormState.errors` e `SubmitEvent.values`. |
| `validators` | `list[Validator]` | `[]` | As regras de validação rodadas contra o valor do campo. Python puro; nunca serializado. |
| `label` | `str` | `""` | Um rótulo opcional mostrado acima do input. |
| `error` | `str` | `""` | A mensagem de validação atual (`""` quando válido). Espelhada do `FormState` do form dono. |
| `child` | `Widget \| None` | `None` | O widget de input embrulhado, renderizado dentro do campo. |
| `on_validate` | `ValidationHandler \| None` | `None` | Handler opcional chamado com um `ValidationEvent` quando o campo é validado. |

!!! note "O input é um filho, não uma prop"
    `child_field_names = {"child"}`: o input embrulhado é declarado como **filho**
    do `FormField`. Isso mantém a árvore serializada uniforme — inputs cruzam a
    fronteira como filhos normais, nunca como modelos aninhados dentro de uma prop.
    O `FormField` também herda `key`, `style` e `semantics` de `Widget`.

### Rodando as regras de um campo

O `FormField` sabe validar a si mesmo via `run_validators`, que roda cada regra em
ordem e devolve a **primeira** mensagem de erro (ou `None` se todas passarem):

```python
from tempest_core import FormField, Input

campo = FormField(
    name="senha",
    validators=[required, min_length(8)],
    child=Input(secure=True),
)

campo.run_validators("")          # "Este campo é obrigatório"  (para na 1ª regra)
campo.run_validators("curta")     # "Mínimo de 8 caracteres"
campo.run_validators("supersegura")  # None  → válido
```

!!! note "Por que `run_validators` e não `validate`"
    O método se chama `run_validators` (e não `validate`) de propósito: `validate` é
    um nome reservado, um classmethod deprecado do Pydantic. O `tempest-core` evita
    sombrear esse nome no nível do campo — só o `Form` expõe um `validate()` público
    (com assinatura de instância própria).

## `Form`

O `Form` é o contêiner que **agrega os campos, valida todos e libera o submit**. Os
`fields` são expostos como nós filhos (cada um um `FormField`), então a árvore
serializada os carrega como filhos — nunca como uma prop com modelos aninhados.

### Campos

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `fields` | `list[FormField]` | `[]` | Os campos do form, na ordem de exibição. |
| `on_submit` | `SubmitHandler \| None` | `None` | Handler chamado com um `SubmitEvent` quando o form é submetido com valores válidos. |

O `on_submit` é um `SubmitHandler` — pode ser **síncrono ou `async`** e recebe um
`SubmitEvent`, que carrega os valores crus dos campos num `dict[str, str]` plano
(`SubmitEvent.values`).

### `Form.validate(values)`

O coração do form é o método `validate`. Ele é **puro** — não faz efeito colateral
nenhum. Recebe um `dict[str, Any]` mapeando nome de campo → valor cru, roda os
validadores de cada campo contra o valor casado (um valor **ausente** valida como
string vazia), junta as falhas num `dict[str, str]` plano e reporta a validade
geral como um `FormState`:

```python
from tempest_core import Form, FormField, Input

form = Form(
    fields=[
        FormField(name="email", validators=[required, looks_like_email],
                  child=Input()),
        FormField(name="senha", validators=[required], child=Input(secure=True)),
    ],
)

estado = form.validate({"email": "sem-arroba", "senha": ""})
estado.errors  # {"email": "Informe um e-mail válido", "senha": "Este campo é obrigatório"}
estado.valid   # False
```

!!! warning "`validate` não dispara o submit — ela só o informa"
    O `validate` é deliberadamente **sem efeitos**: ele te dá o `FormState`, e **você**
    decide o que fazer. O padrão é: se `state.valid`, despache o `SubmitEvent`; senão,
    espelhe cada erro de volta no seu campo (`FormField.error`) para o usuário ver.
    O core nunca despacha por conta própria — mantendo a decisão de negócio na sua mão.

!!! tip "Campo ausente valida como string vazia"
    Se `values` não tiver a chave de um campo, o `validate` roda os validadores contra
    `""`. Na prática isso significa que um campo obrigatório não preenchido **falha**
    naturalmente — você não precisa checar presença à parte.

### Montando um form e reagindo ao submit

Juntando tudo: um form de login completo, montado com `FormField` + `Validator`,
validado, e com o submit **liberado só quando tudo passa**. Este exemplo é
copiável e roda como está:

```python
from tempest_core import Form, FormField, FormState, Input, SubmitEvent


def required(value: str) -> str | None:
    """Reject empty or whitespace-only values."""
    return "Este campo é obrigatório" if not value.strip() else None


def looks_like_email(value: str) -> str | None:
    """A minimal email sanity check."""
    return None if "@" in value else "Informe um e-mail válido"


def build_login_form(state: FormState | None = None) -> Form:
    """Build the login form, mirroring any prior errors onto their fields."""
    errors = state.errors if state is not None else {}
    return Form(
        fields=[
            FormField(
                name="email",
                label="E-mail",
                validators=[required, looks_like_email],
                error=errors.get("email", ""),
                child=Input(placeholder="voce@exemplo.com"),
            ),
            FormField(
                name="password",
                label="Senha",
                validators=[required],
                error=errors.get("password", ""),
                child=Input(placeholder="••••••", secure=True),
            ),
        ],
        on_submit=lambda event: print("Enviando", event.values),  # (1)!
    )


form = build_login_form()

# Os valores crus que a aplicação coletou dos inputs no momento do submit.
submitted = {"email": "ada@exemplo.com", "password": "s3nha-forte"}

state = form.validate(submitted)  # (2)!

if state.valid and form.on_submit is not None:
    form.on_submit(SubmitEvent(values=submitted))  # (3)!  despacho liberado
else:
    form = build_login_form(state)  # (4)!  remonta o form com os erros à mostra
```

1. O `on_submit` pode ser síncrono ou `async`; aqui um `lambda` síncrono basta.
2. `validate` é puro — só devolve o `FormState`, sem tocar nos campos.
3. O submit é **liberado**: só despachamos o `SubmitEvent` porque `state.valid` é
   `True`.
4. Como o IR é declarativo, o jeito idiomático de "mostrar os erros" é **remontar** a
   árvore com os `error` preenchidos — o reconciliador faz o diff e atualiza só o
   que mudou.

!!! check "O submit é sempre gated pela validação"
    Repare que o `SubmitEvent` só é despachado dentro do `if state.valid`. Esse é o
    contrato do form: **nenhum submit sai com valores inválidos**. Você nunca precisa
    revalidar no handler — se ele foi chamado, os valores já passaram.

## `FormState`

O `FormState` é o **resultado estruturado** de validar um form. Ele é
propositalmente plano — nada de árvore de modelos aninhados — então serializa para
JSON puro (`{"errors": {...}, "valid": bool}`) e cabe direto no estado da aplicação.
É **frozen** (imutável), então pode ser comparado por valor e mergulhado no estado
sem medo de mutação acidental.

### Campos

| Prop | Tipo | Padrão | O que faz |
| --- | --- | --- | --- |
| `errors` | `dict[str, str]` | `{}` | Mapa de nome do campo → sua mensagem de erro. Só campos que falharam aparecem. |
| `valid` | `bool` | `True` | `True` quando nenhum campo tem erro. |

```python
from tempest_core import FormState

# Um form todo válido:
FormState()                          # errors={}, valid=True
FormState(errors={}, valid=True)     # equivalente

# Um form com uma falha:
estado = FormState(errors={"email": "Informe um e-mail válido"}, valid=False)
estado.errors["email"]  # "Informe um e-mail válido"
estado.valid            # False
```

!!! note "Só os campos que falham aparecem em `errors`"
    O `errors` guarda **apenas** os campos inválidos — um mapa **vazio** significa que
    todo campo passou. Não espere uma chave por campo; itere sobre `errors` para achar
    o que corrigir, ou use `errors.get(name, "")` ao espelhar de volta nos campos.

!!! info "`valid` é derivado, mas explícito"
    Quando o `Form.validate` constrói o estado, ele passa `valid=not errors` — ou seja,
    `valid` é `True` exatamente quando `errors` está vazio. O campo é explícito (não
    uma property) para que o `FormState` serialize os dois valores como JSON plano.

## Recapitulando

- **`Validator`** é um `TypeAlias` para `Callable[[Any], str | None]` — uma função
  pura que devolve a mensagem de erro ou `None`. Roda só no Python, nunca serializa.
- **`FormField`** embrulha um input como **filho** (`child`) e carrega `name`,
  `validators`, `label` e `error`. `run_validators` roda as regras em ordem e para
  na **primeira** que falha.
- **`Form`** agrega os `fields` e expõe `validate(values)` — puro, sem efeitos —
  que devolve um `FormState`. Campo ausente valida como `""`.
- **O submit é gated**: só despache o `SubmitEvent` quando `state.valid`; o core
  nunca despacha sozinho.
- **`FormState`** é o resultado plano e **frozen** (`{"errors": {...}, "valid": ...}`),
  pronto para morar no estado da app. Só campos que falham aparecem em `errors`.
- Precisa da assinatura completa de cada símbolo? Veja a
  [Referência da API](../reference.md).
