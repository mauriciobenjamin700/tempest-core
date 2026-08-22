# Forms

Forms in `tempest-core` are **declarative and validated at the boundary**: you
describe the fields and their rules in Python, and validation runs **once, in
Python**, producing a structured, JSON-serializable result — the same philosophy
as `parse_event`. No validation scattered across the renderers. 🚀

Four symbols work together: **`Validator`** (the rule), **`FormField`** (the field
that wraps an input and carries its rules), **`Form`** (the container that
aggregates fields, validates, and gates submit), and **`FormState`** (the flat
validation result, ready to live in the application state).

!!! info "What you'll learn here"
    - How a `Validator` is just a **pure callable** `(value) -> str | None`.
    - How a `FormField` wraps an input as a **child** and holds its rules.
    - How `Form.validate()` runs every rule and **gates the submit**.
    - How to read a `FormState` — the flat error `dict` + the `valid` flag.
    - An **end-to-end** example assembling a form and reacting to submit.

## `Validator`

A `Validator` is the most basic building block: a **pure function** that receives a
field's raw value and returns an **error message** (`str`) when the value is
invalid, or `None` when it passes. The real signature is a `TypeAlias`:

```python
from typing import Any, TypeAlias
from collections.abc import Callable

Validator: TypeAlias = Callable[[Any], str | None]
```

That means any callable of that shape is a valid validator — including `lambda`s
and closures over your application logic:

```python
from tempest_core import Validator


def required(value: str) -> str | None:
    """Reject empty or whitespace-only values."""
    return "This field is required" if not value.strip() else None


def looks_like_email(value: str) -> str | None:
    """A minimal email sanity check."""
    return None if "@" in value else "Enter a valid email"


# A Validator can also close over application state:
def min_length(n: int) -> Validator:
    """Build a validator that requires at least ``n`` characters."""
    return lambda value: None if len(value) >= n else f"At least {n} characters"
```

!!! info "Validators run in Python only, never cross the boundary"
    A `Validator` is pure application logic — it is **never serialized** to the
    renderers. That's why it can close over anything (database, config, another
    function). What crosses the bridge is only the **result** of validation (the
    `FormState`), not the rule itself.

!!! tip "The first failing rule wins"
    When a field has several rules, they run **in order** and the **first** one that
    returns a message short-circuits the rest (see `FormField.run_validators`
    below). Order them from the most fundamental (`required`) to the most specific
    (`looks_like_email`).

## `FormField`

A `FormField` is a **labelled wrapper** around a single input. It carries the
field's `name`, the list of `validators`, and — as a **child** (`child`) — the
input widget itself. The input is exposed as a child node (not as a prop) so that
renderers draw it recursively and it crosses the boundary like any other child:

```python
from tempest_core import FormField, Input

email = FormField(
    name="email",  # (1)!
    label="Email",
    validators=[required, looks_like_email],
    child=Input(placeholder="you@example.com"),
)
```

1. `name` is the **key** used in `FormState.errors` and `SubmitEvent.values` — it's
   how the field's value is matched to its rule at validation time.

### Fields

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `name` | `str` | *(required)* | The field's name — the key in `FormState.errors` and `SubmitEvent.values`. |
| `validators` | `list[Validator]` | `[]` | The validation rules run against the field's value. Pure Python; never serialized. |
| `label` | `str` | `""` | An optional label shown above the input. |
| `error` | `str` | `""` | The current validation message (`""` when valid). Mirrored from the owning form's `FormState`. |
| `child` | `Widget \| None` | `None` | The wrapped input widget, rendered inside the field. |
| `on_validate` | `ValidationHandler \| None` | `None` | Optional handler invoked with a `ValidationEvent` when the field is validated. |

!!! note "The input is a child, not a prop"
    `child_field_names = {"child"}`: the wrapped input is declared as a **child** of
    the `FormField`. This keeps the serialized tree uniform — inputs cross the
    boundary as normal children, never as nested models inside a prop. The
    `FormField` also inherits `key`, `style`, and `semantics` from `Widget`.

### Running a field's rules

A `FormField` knows how to validate itself via `run_validators`, which runs each
rule in order and returns the **first** error message (or `None` if all pass):

```python
from tempest_core import FormField, Input

field = FormField(
    name="password",
    validators=[required, min_length(8)],
    child=Input(secure=True),
)

field.run_validators("")  # "This field is required"  (stops at 1st rule)
field.run_validators("short")  # "At least 8 characters"
field.run_validators("supersecret")  # None  → valid
```

!!! note "Why `run_validators` and not `validate`"
    The method is called `run_validators` (not `validate`) on purpose: `validate` is
    a reserved name, a deprecated Pydantic classmethod. `tempest-core` avoids
    shadowing it at the field level — only `Form` exposes a public `validate()` (with
    its own instance-level signature).

## `Form`

A `Form` is the container that **aggregates the fields, validates them all, and
gates the submit**. The `fields` are exposed as child nodes (each a `FormField`),
so the serialized tree carries them as children — never as a prop holding nested
models.

### Fields

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `fields` | `list[FormField]` | `[]` | The form's fields, in display order. |
| `on_submit` | `SubmitHandler \| None` | `None` | Handler invoked with a `SubmitEvent` when the form is submitted with valid values. |

`on_submit` is a `SubmitHandler` — it may be **sync or `async`** and receives a
`SubmitEvent`, which carries the raw field values in a flat `dict[str, str]`
(`SubmitEvent.values`).

### `Form.validate(values)`

The heart of the form is the `validate` method. It is **pure** — no side effects at
all. It takes a `dict[str, Any]` mapping field name → raw value, runs each field's
validators against the matching value (an **absent** value validates as the empty
string), collects the failures into a flat `dict[str, str]`, and reports overall
validity as a `FormState`:

```python
from tempest_core import Form, FormField, Input

form = Form(
    fields=[
        FormField(name="email", validators=[required, looks_like_email], child=Input()),
        FormField(name="password", validators=[required], child=Input(secure=True)),
    ],
)

state = form.validate({"email": "no-at-sign", "password": ""})
state.errors  # {"email": "Enter a valid email", "password": "This field is required"}
state.valid  # False
```

!!! warning "`validate` does not fire submit — it only informs it"
    `validate` is deliberately **side-effect-free**: it hands you the `FormState`, and
    **you** decide what to do. The pattern is: if `state.valid`, dispatch the
    `SubmitEvent`; otherwise, mirror each error back onto its field
    (`FormField.error`) so the user sees it. The core never dispatches on its own —
    keeping the business decision in your hands.

!!! tip "An absent field validates as the empty string"
    If `values` has no key for a field, `validate` runs its validators against `""`.
    In practice this means an unfilled required field **fails** naturally — you don't
    need a separate presence check.

### Assembling a form and reacting to submit

Putting it all together: a complete login form, assembled from `FormField` +
`Validator`, validated, with submit **gated to fire only when everything passes**.
This example is copy-paste runnable as-is:

```python
from tempest_core import Form, FormField, FormState, Input, SubmitEvent


def required(value: str) -> str | None:
    """Reject empty or whitespace-only values."""
    return "This field is required" if not value.strip() else None


def looks_like_email(value: str) -> str | None:
    """A minimal email sanity check."""
    return None if "@" in value else "Enter a valid email"


def build_login_form(state: FormState | None = None) -> Form:
    """Build the login form, mirroring any prior errors onto their fields."""
    errors = state.errors if state is not None else {}
    return Form(
        fields=[
            FormField(
                name="email",
                label="Email",
                validators=[required, looks_like_email],
                error=errors.get("email", ""),
                child=Input(placeholder="you@example.com"),
            ),
            FormField(
                name="password",
                label="Password",
                validators=[required],
                error=errors.get("password", ""),
                child=Input(placeholder="••••••", secure=True),
            ),
        ],
        on_submit=lambda event: print("Submitting", event.values),  # (1)!
    )


form = build_login_form()

# The raw values the application collected from the inputs at submit time.
submitted = {"email": "ada@example.com", "password": "strong-pass"}

state = form.validate(submitted)  # (2)!

if state.valid and form.on_submit is not None:
    form.on_submit(SubmitEvent(values=submitted))  # (3)!  gated dispatch
else:
    form = build_login_form(state)  # (4)!  rebuild the form with errors shown
```

1. `on_submit` may be sync or `async`; a sync `lambda` is enough here.
2. `validate` is pure — it just returns the `FormState`, without touching the
   fields.
3. Submit is **gated**: we only dispatch the `SubmitEvent` because `state.valid` is
   `True`.
4. Since the IR is declarative, the idiomatic way to "show the errors" is to
   **rebuild** the tree with the `error` fields filled in — the reconciler diffs it
   and updates only what changed.

!!! check "Submit is always gated by validation"
    Notice the `SubmitEvent` is only dispatched inside the `if state.valid`. That's
    the form's contract: **no submit ever leaves with invalid values**. You never
    need to re-validate in the handler — if it was called, the values already passed.

## `FormState`

`FormState` is the **structured result** of validating a form. It is intentionally
flat — no tree of nested models — so it serializes to plain JSON
(`{"errors": {...}, "valid": bool}`) and drops straight into the application state.
It is **frozen** (immutable), so it can be diffed by value and dropped into state
without fear of accidental mutation.

### Fields

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `errors` | `dict[str, str]` | `{}` | Mapping of field name → its error message. Only failing fields appear. |
| `valid` | `bool` | `True` | `True` when no field has an error. |

```python
from tempest_core import FormState

# A fully valid form:
FormState()  # errors={}, valid=True
FormState(errors={}, valid=True)  # equivalent

# A form with one failure:
state = FormState(errors={"email": "Enter a valid email"}, valid=False)
state.errors["email"]  # "Enter a valid email"
state.valid  # False
```

!!! note "Only failing fields appear in `errors`"
    `errors` holds **only** the invalid fields — an **empty** mapping means every
    field passed. Don't expect one key per field; iterate over `errors` to find what
    to fix, or use `errors.get(name, "")` when mirroring back onto the fields.

!!! info "`valid` is derived, but explicit"
    When `Form.validate` builds the state, it passes `valid=not errors` — that is,
    `valid` is `True` exactly when `errors` is empty. The field is explicit (not a
    property) so `FormState` serializes both values as flat JSON.

## Recap

- **`Validator`** is a `TypeAlias` for `Callable[[Any], str | None]` — a pure
  function returning the error message or `None`. It runs in Python only, never
  serializes.
- **`FormField`** wraps an input as a **child** (`child`) and carries `name`,
  `validators`, `label`, and `error`. `run_validators` runs the rules in order and
  stops at the **first** failure.
- **`Form`** aggregates the `fields` and exposes `validate(values)` — pure, no side
  effects — which returns a `FormState`. An absent field validates as `""`.
- **Submit is gated**: only dispatch the `SubmitEvent` when `state.valid`; the core
  never dispatches on its own.
- **`FormState`** is the flat, **frozen** result (`{"errors": {...}, "valid": ...}`),
  ready to live in app state. Only failing fields appear in `errors`.
- Need the full signature of each symbol? See the [API reference](../reference.md).
