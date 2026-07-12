# Brazilian forms & media pickers

A Brazilian sign-up form is always the same story: e-mail, password, phone, CPF
or CNPJ, address — and, almost always, a photo and a document to attach.
`tempest-core` ships those fields **ready-made, labelled and masked**, plus the
three media pickers. Each is a `Component` that **lowers** to the primitive
widgets (`Input` / `MaskedInput` / `FilePicker` / `Image`), so it behaves
identically in both renderers (Qt and Compose) with no renderer change. 🚀

!!! info "What you'll learn here"
    - The six labelled **Brazilian fields** and which mask each one applies.
    - Why every masked/validated field **pairs with a validator** from
      `tempest_core.validators` — the mask formats, the validator checks.
    - How `AddressInput` **groups** seven fields under a single `on_change`.
    - The three **media pickers** and why `button_label` is localisable.
    - Why `ImagePicture` is the **circular** profile-photo picker, not an `Avatar`.

## Brazilian fields

The six fields share the same base (`_BRField`): each takes a controlled `value`,
a `label` above, a `placeholder`, an `error` line below (in the theme's error
color) and an `on_change` that receives **the new string** — you never touch the
event object. All of them also thread `field_variant` / `size` / `color_scheme` /
`theme` / `media` into the inner input, which resolves its Material 3 look against
the theme (dark mode + brand color for free).

!!! tip "The mask formats; the validator checks"
    Masking and validation are different jobs. `MaskedInput` only **formats** the
    digits as the user types — it does not guarantee the CPF is valid. For that,
    pair each field with the sibling validator from
    [`tempest_core.validators`](../reference.md): `validate_email`,
    `validate_phone`, `validate_cpf`, `validate_cnpj`. The mask is UX; the
    validator is business rule.

## `EmailInput`

A labelled e-mail field, with the **e-mail keyboard**, a mail icon and the
built-in `EMAIL_PATTERN`. In the minimal case you pass only `on_change`:

```python
from tempest_core import EmailInput

email = EmailInput(
    value="",
    on_change=lambda v: app.set_state(email=v),  # (1)!
)
```

1. The handler receives **the new string** directly — not an event. It may be
   sync or `async`.

Validate with `validate_email` from [`tempest_core.validators`](../reference.md),
and surface the message by feeding it back into `error`:

```python
from tempest_core import EmailInput
from tempest_core.validators import validate_email

def on_email(value: str) -> None:
    error = "" if validate_email(value) else "Invalid e-mail"
    app.set_state(email=value, email_error=error)

email = EmailInput(
    value=app.state.email,
    label="Your e-mail",
    placeholder="you@example.com",
    error=app.state.email_error,
    on_change=on_email,
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current value (controlled). |
| `label` | `str` | `"E-mail"` | The label shown above the field (omitted when empty). |
| `placeholder` | `str` | `""` | The empty-field hint. |
| `error` | `str` | `""` | The validation message; in the theme's error color. |
| `on_change` | `Callable[[str], Any]` | *(required)* | Called with the new string on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner input treatment (outline / filled / flushed). |
| `size` | `ResponsiveSize` | `MD` | The density — a single `Size` or a per-breakpoint map. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the field's focus paints with. |
| `theme` | `Theme` | `Theme()` | The theme resolving the field + label/error colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! note "The keyboard and the icon come pre-set"
    `EmailInput` pins `keyboard=EMAIL`, `leading_icon="mail"` and
    `pattern=EMAIL_PATTERN` on the inner input — you don't (and can't) swap them
    via the component API. Those three defaults are exactly why an `EmailInput`
    exists instead of a raw `Input`.

## `PasswordInput`

A labelled password field: **secure** (masked text), with a lock icon and the
built-in **eye toggle** to show/hide. Both `label` and `placeholder` default to
`"Senha"`:

```python
from tempest_core import PasswordInput

password = PasswordInput(
    value=app.state.password,
    error=app.state.password_error,
    on_change=lambda v: app.set_state(password=v),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current value (controlled). |
| `label` | `str` | `"Senha"` | The label shown above the field (omitted when empty). |
| `placeholder` | `str` | `"Senha"` | The empty-field hint. |
| `error` | `str` | `""` | The validation message; in the theme's error color. |
| `on_change` | `Callable[[str], Any]` | *(required)* | Called with the new string on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner input treatment. |
| `size` | `ResponsiveSize` | `MD` | The density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `theme` | `Theme` | `Theme()` | The theme resolving the field + label/error colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! info "Secure by construction"
    `PasswordInput` pins `secure=True` and `leading_icon="lock"` on the inner
    input. The eye toggle comes from the secure `Input` itself — you don't wire
    anything for the user to reveal the password.

## `PhoneInput`

A Brazilian phone field, **masked** `(99) 99999-9999`, with the phone number
keyboard. Each `9` is a digit; parentheses, space and dash are inserted
automatically as the user types:

```python
from tempest_core import PhoneInput
from tempest_core.validators import validate_phone

def on_phone(value: str) -> None:
    error = "" if validate_phone(value) else "Invalid phone"
    app.set_state(phone=value, phone_error=error)

phone = PhoneInput(
    value=app.state.phone,
    error=app.state.phone_error,
    on_change=on_phone,
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current value (controlled). |
| `label` | `str` | `"Telefone"` | The label shown above the field (omitted when empty). |
| `placeholder` | `str` | `""` | The empty-field hint. |
| `error` | `str` | `""` | The validation message; in the theme's error color. |
| `on_change` | `Callable[[str], Any]` | *(required)* | Called with the new string on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner input treatment. |
| `size` | `ResponsiveSize` | `MD` | The density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `theme` | `Theme` | `Theme()` | The theme resolving the field + label/error colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! warning "The `(99) 99999-9999` mask covers the 9-digit mobile"
    The mask is fixed and designed for the Brazilian mobile number (area code +
    nine digits). `on_change` reports the value **as it sits in the field** (with
    the mask) — use `validate_phone` to check it, and if you need the raw number,
    strip the mask in your handler before persisting.

## `CPFInput`

A labelled CPF field, **masked** `999.999.999-99`, numeric keyboard. Pair it with
`validate_cpf` (which checks the verifier digits, not just the format):

```python
from tempest_core import CPFInput
from tempest_core.validators import validate_cpf

def on_cpf(value: str) -> None:
    error = "" if validate_cpf(value) else "Invalid CPF"
    app.set_state(cpf=value, cpf_error=error)

cpf = CPFInput(
    value=app.state.cpf,
    error=app.state.cpf_error,
    on_change=on_cpf,
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current value (controlled). |
| `label` | `str` | `"CPF"` | The label shown above the field (omitted when empty). |
| `placeholder` | `str` | `""` | The empty-field hint. |
| `error` | `str` | `""` | The validation message; in the theme's error color. |
| `on_change` | `Callable[[str], Any]` | *(required)* | Called with the new string on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner input treatment. |
| `size` | `ResponsiveSize` | `MD` | The density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `theme` | `Theme` | `Theme()` | The theme resolving the field + label/error colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! danger "A mask is not CPF validation"
    `999.999.999-99` only formats eleven digits — `111.111.111-11` passes the mask
    and is an invalid CPF. **Always** pair `CPFInput` with `validate_cpf`, which
    runs the verifier-digit algorithm. Trusting the mask alone lets fake CPFs into
    your database.

## `CNPJInput`

A labelled CNPJ field, **masked** `99.999.999/9999-99`, numeric keyboard. Pair it
with `validate_cnpj`:

```python
from tempest_core import CNPJInput
from tempest_core.validators import validate_cnpj

def on_cnpj(value: str) -> None:
    error = "" if validate_cnpj(value) else "Invalid CNPJ"
    app.set_state(cnpj=value, cnpj_error=error)

cnpj = CNPJInput(
    value=app.state.cnpj,
    error=app.state.cnpj_error,
    on_change=on_cnpj,
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current value (controlled). |
| `label` | `str` | `"CNPJ"` | The label shown above the field (omitted when empty). |
| `placeholder` | `str` | `""` | The empty-field hint. |
| `error` | `str` | `""` | The validation message; in the theme's error color. |
| `on_change` | `Callable[[str], Any]` | *(required)* | Called with the new string on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner input treatment. |
| `size` | `ResponsiveSize` | `MD` | The density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `theme` | `Theme` | `Theme()` | The theme resolving the field + label/error colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! danger "Same goes for the CNPJ"
    The `99.999.999/9999-99` mask formats fourteen digits but doesn't check the
    verifiers. **Always** pair it with `validate_cnpj`.

## `AddressInput`

A **grouped** Brazilian address block: instead of seven loose components,
`AddressInput` renders a labelled `Column` with CEP (masked `99999-999`), street,
number, complement, neighborhood, city and UF all at once. A **single**
`on_change` is called as `on_change(field_name, new_value)`, where `field_name`
is one of `"cep"`, `"street"`, `"number"`, `"complement"`, `"neighborhood"`,
`"city"` or `"state"`:

```python
from tempest_core import AddressInput

def on_address(field_name: str, value: str) -> None:  # (1)!
    app.set_state(**{field_name: value})

address = AddressInput(
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

1. Note the **two-argument signature**: `AddressInput` tells you **which** field
   changed, so a single handler updates the right field's state.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `cep` | `str` | `""` | The current postal code (masked `99999-999`). |
| `street` | `str` | `""` | The current street value. |
| `number` | `str` | `""` | The current house/building number. |
| `complement` | `str` | `""` | The current address complement. |
| `neighborhood` | `str` | `""` | The current neighborhood value. |
| `city` | `str` | `""` | The current city value. |
| `state` | `str` | `""` | The current state (UF) value. |
| `label` | `str` | `"Endereço"` | The block heading (omitted when empty). |
| `on_change` | `Callable[[str, str], Any]` | *(required)* | Called as `on_change(field_name, new_value)` on each edit. |
| `field_variant` | `FieldVariant` | `OUTLINE` | The inner inputs' treatment. |
| `size` | `ResponsiveSize` | `MD` | The inputs' density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `theme` | `Theme` | `Theme()` | The theme resolving the fields + heading color. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! note "One handler, many fields"
    Unlike the simple fields (which call `on_change(value)`), `AddressInput` calls
    `on_change(field_name, value)`. It's the only BR field with this two-argument
    signature — it exists because the block gathers seven inputs under a single
    handler. Only the CEP is masked; street, number, complement, neighborhood,
    city and UF are plain text inputs.

## Media pickers

The three pickers lower to `FilePicker` (and, for the ones that preview, to
`Image`). All expose an `on_pick` that receives **the picked file's URI** — never
the event object. `on_pick` may be `async`: the returned value is forwarded to the
dispatcher and awaited, so loading/analyzing the picked file inside the handler
works without stranding a coroutine.

## `ImagePicker`

A labelled image picker with an **inline preview**: as soon as a URI is chosen it
shows the image (160×160, rounded corners) above the button:

```python
from tempest_core import ImagePicker

photo = ImagePicker(
    value=app.state.photo_uri,
    label="Product photo",
    button_label="Choose image",  # (1)!
    on_pick=lambda uri: app.set_state(photo_uri=uri),
)
```

1. `button_label` is **localisable** — pass the text in the app's language. The
   default `"Choose image"` is English on purpose, to force the locale decision.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The picked image URI (empty until one is chosen). When set, a preview appears. |
| `label` | `str` | `""` | An optional heading above the picker (omitted when empty). |
| `button_label` | `str` | `"Choose image"` | The picker button's caption (localise it per app locale). |
| `on_pick` | `Callable[[str], Any]` | *(required)* | Called with the picked image URI. |

!!! tip "Localise the `button_label`"
    Both `ImagePicker` and `DocumentPicker` expose `button_label` precisely so you
    can translate the button caption. The default is English (`"Choose image"` /
    `"Choose document"`) — swap it for the app's locale string, like
    `"Escolher imagem"`.

## `DocumentPicker`

A labelled document picker. Like `ImagePicker`, but **without a preview** — a
document isn't an image to render:

```python
from tempest_core import DocumentPicker

attachment = DocumentPicker(
    value=app.state.doc_uri,
    label="Proof of address",
    button_label="Choose document",
    on_pick=lambda uri: app.set_state(doc_uri=uri),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The picked document URI (empty until one is chosen). |
| `label` | `str` | `""` | An optional heading above the picker (omitted when empty). |
| `button_label` | `str` | `"Choose document"` | The picker button's caption (localise it per app locale). |
| `on_pick` | `Callable[[str], Any]` | *(required)* | Called with the picked document URI. |

## `ImagePicture`

The **circular** profile-photo picker: a round photo over a change affordance.
Unlike `Avatar` (which shows initials), `ImagePicture` clips the chosen image to a
circle and, with no photo, falls back to a **`user` icon placeholder**. `size` is
the circle's diameter in logical pixels:

```python
from tempest_core import ImagePicture

profile = ImagePicture(
    src=app.state.avatar_uri,
    size=96.0,
    on_pick=lambda uri: app.set_state(avatar_uri=uri),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `src` | `str` | `""` | The current photo URI (empty shows the placeholder). |
| `size` | `float` | `96.0` | The circle's diameter in logical pixels. |
| `on_pick` | `Callable[[str], Any]` | *(required)* | Called with the picked photo URI. |

!!! note "`ImagePicture` picks; `Avatar` displays"
    Both are round, but they solve different problems. `Avatar` **displays** an
    identity (photo or initials) and doesn't let you change it. `ImagePicture`
    **collects** a photo: circular clip when `src` is set, a `user` icon when not,
    and always a "change" `FilePicker` below. Use `ImagePicture` on the
    profile-edit screen; use `Avatar` anywhere that only shows.

## Recap

- **Six labelled Brazilian fields**: `EmailInput`, `PasswordInput`, `PhoneInput`,
  `CPFInput`, `CNPJInput` and the grouped `AddressInput` — all with a controlled
  `value`, a `label`, an `error` and `on_change(value)`.
- **Mask formats, validator checks**: pair the masked/validated fields with
  `validate_email` / `validate_phone` / `validate_cpf` / `validate_cnpj` from
  `tempest_core.validators`. The mask is UX; validation is the rule.
- **`AddressInput` is grouped**: seven fields (masked CEP + six text) under a
  single `on_change(field_name, new_value)`.
- **Three media pickers**: `ImagePicker` (with inline preview), `DocumentPicker`
  (no preview) and `ImagePicture` (circular profile photo). All take
  `on_pick(uri)`, which accepts `async`.
- **`button_label` is localisable** on `ImagePicker`/`DocumentPicker` — the
  English default exists to force per-locale translation.
- **`ImagePicture` collects, `Avatar` displays**: the circular picker clips the
  photo to a circle with a `user`-icon fallback; `Avatar` only shows.
