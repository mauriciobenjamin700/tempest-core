# Inputs

Inputs are the **value-bearing leaves** of the IR: text fields, selection controls
and value sliders. Each stores its current value as a JSON scalar (`str` / `bool`
/ `float`) and declares its change handler in `event_schemas`, so the boundary can
validate the payload. And every one is styled by the **Chakra-ergonomics variant
API (phase H2)** anchored on **Material 3**: you describe the *intent* (`size` /
`color_scheme`, plus `field_variant` on the FIELD family) and a **pure resolver**
bakes the concrete `Style` from the `Theme` tokens — exactly like
[`Button`](../reference.md). 🚀

!!! info "What you'll learn here"
    - The **three families** of input (FIELD / SELECTION / SLIDER) and which
      resolver each one uses.
    - The three **field variants** (`FieldVariant`) and which M3 treatment each
      lowers to.
    - The shared variant props (`size` / `color_scheme` / `theme` / `media`) and
      why `theme` and `media` stay out of the IR.
    - How each input **resolves and bakes** its `Style`, and how to read the
      **per-state table** (`state_styles()`).
    - The 14 widgets — from `Input` to `MaskedInput` — with their real props and
      defaults.

## The three variant families

Every styled input inherits one of three internal mixins, and each family resolves
its `Style` through a distinct pure function (`resolve_*_variant`), with the
caller's override always merged on top:

| Family | Widgets | Variant props | Resolver |
| --- | --- | --- | --- |
| **FIELD** | `Input`, `TextArea`, `DatePicker`, `FilePicker`, `Dropdown`, `TimePicker`, `Autocomplete`, `PinInput`, `MaskedInput` | `field_variant` + `size` + `color_scheme` | `resolve_field_variant` |
| **SELECTION** | `Checkbox`, `Switch` | `checked` + `size` + `color_scheme` | `resolve_selection_variant` |
| **SLIDER** | `Slider`, `RangeSlider` | `size` + `color_scheme` | `resolve_slider_variant` |

All three share four resolution props, on top of their family-specific ones:

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `size` | `Size \| dict[str, Size]` | `Size.MD` | The density — a single `Size` (`XS` / `SM` / `MD` / `LG`) or a per-breakpoint map. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the focus/accent tint paints with (`primary` / `secondary` / `tertiary` / `error` / `neutral` / `success` / `warning` / `info`). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the variant. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. **Kept out of the IR.** |

!!! note "`theme` and `media` are build-time inputs, not IR props"
    Both are used **only when resolving** the `Style` and are excluded from the
    node props (`prop_exclude_names = {"theme", "media"}`). A full `Theme` per node
    would bloat the tree and the serialized bridge payload — the resolved `style`
    already carries their effect.

### The `FieldVariant` table (FIELD family only)

Unlike buttons, a field is **focus-led**: the resting treatment is low-emphasis and
`color_scheme` only tints the focus/caret/label, never the resting fill.
`field_variant` picks that resting treatment:

| `FieldVariant` | M3 treatment | Background | Resting border | Radius |
| --- | --- | --- | --- | --- |
| `OUTLINE` | *outlined text field* (the default) | transparent | full border in the `outline` color | small |
| `FILLED` | *filled text field* | tonal (`surface_variant`) | none | small |
| `FLUSHED` | underline-only field | transparent | bottom border only | none |

```python
from tempest_core import Input
from tempest_core.style import FieldVariant

outlined = Input(placeholder="Email", field_variant=FieldVariant.OUTLINE)
filled = Input(placeholder="Email", field_variant=FieldVariant.FILLED)
flushed = Input(placeholder="Email", field_variant=FieldVariant.FLUSHED)
```

!!! tip "The `color_scheme` accent only shows on focus"
    On the FIELD family, `color_scheme` doesn't paint the resting fill — it tints
    the border/caret when the field gains focus (2px in the role color). A field
    with a non-empty `error` forces the border/label to the `error` role in
    **every** state (`Input` does exactly this from its own `error`).

### The per-state table (`state_styles()`)

The resolvers are pure and live in the engine, but real inputs have **interaction
states**. Every widget exposes `state_styles()`, which returns the resolved `Style`
for each `ComponentState`, with the caller's override already merged on top:

```python
from tempest_core import Input
from tempest_core.style import ComponentState

field = Input(placeholder="Name", color_scheme="primary")
states = field.state_styles()

states[ComponentState.DEFAULT]  # at rest
states[ComponentState.HOVER]  # pointer over
states[ComponentState.PRESSED]  # treated as FOCUS on a field (it gains focus)
states[ComponentState.DISABLED]  # inactive (content at 38%)
states[ComponentState.FOCUS]  # keyboard/reader focus (2px accent border)
```

!!! note "Resolution is pure; only the event→state mapping lives in the renderer"
    The core produces the state **table** deterministically. Applying the Material
    3 *state layer* on the right focus/pointer event is the only part that lives in
    the renderers (Qt / Compose) — keeping the core from ever touching pixels. An
    explicit `style` passed to the widget is always merged on top of the resolved
    variant (the override's set fields win), so `Input(...)` with no `style` gives
    the variant field, and `Input(..., style=…)` hand-styles on top without losing
    the variant.

## `KeyboardType`

The enum that says **which soft keyboard** a text field requests on the device. It
maps to Android `inputType` on the device renderer and to Qt input-method hints in
the simulator.

```python
from tempest_core import Input, KeyboardType

phone = Input(placeholder="(555) 000-0000", keyboard=KeyboardType.PHONE)
```

| Member | Value | What it does |
| --- | --- | --- |
| `TEXT` | `"text"` | Full alphanumeric keyboard, no specialization (the default). |
| `NUMBER` | `"number"` | Numeric keypad for digits (with a decimal/sign key). |
| `EMAIL` | `"email"` | Text keyboard tuned for email, surfacing `@` and `.`. |
| `PHONE` | `"phone"` | Telephone dial pad (digits plus `+`, `*` and `#`). |
| `URL` | `"url"` | Keyboard tuned for URLs, surfacing `/` and `.`, no space bar. |
| `PASSWORD` | `"password"` | Keyboard for secret entry; masks characters and disables suggestions/auto-correct. |

## `Input`

A **single-line** editable text field, styled via the field-variant API. In the
minimal case you pass nothing — the defaults give you an `OUTLINE`, primary,
medium-density field:

```python
from tempest_core import Input

name = Input(placeholder="Your name")
```

Pass an `on_change` to react to each edit; the handler receives a
`TextChangeEvent` (with the new `value` and the `pattern`'s `valid` flag):

```python
from tempest_core import Input, KeyboardType
from tempest_core.style import FieldVariant

email = Input(
    value="",
    placeholder="you@example.com",
    keyboard=KeyboardType.EMAIL,
    field_variant=FieldVariant.FILLED,
    on_change=lambda e: app.set_state(email=e.value),  # (1)!
)
```

1. The handler may be **sync or `async`** — the runtime schedules awaitables on
   the event loop.

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`), `Input` carries:

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current text value. |
| `placeholder` | `str` | `""` | The hint shown when the field is empty. |
| `secure` | `bool` | `False` | Whether the text is masked (password field); the renderer offers an "eye" toggle. |
| `pattern` | `str \| None` | `None` | Regex the value must fully match to be valid; the renderer evaluates it and reports via `TextChangeEvent.valid`. |
| `error` | `str` | `""` | A validation message; a non-empty `error` forces the border/label to the `error` role. |
| `keyboard` | `KeyboardType` | `KeyboardType.TEXT` | The soft keyboard requested. |
| `max_length` | `int \| None` | `None` | An optional cap on the number of characters. |
| `leading_icon` | `Icons \| str \| None` | `None` | Optional icon on the start (leading) edge — a curated `Icons` value or platform name. |
| `trailing_icon` | `Icons \| str \| None` | `None` | Optional icon on the end (trailing) edge. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler invoked with a `TextChangeEvent` on each edit. |

!!! info "`error` is what drives the resolver's `invalid`"
    `Input` overrides `_field_invalid()` to return `bool(self.error)`. That means
    setting a message in `error` doesn't just show it — it also paints the
    border/label red (`error`) in every state, without you touching `color_scheme`.

## `TextArea`

A **multi-line** editable text field. It resolves its `Style` just like `Input`
(same FIELD family), only swapping the rendered affordance and adding an initial
height hint:

```python
from tempest_core import TextArea

bio = TextArea(placeholder="Tell us about yourself", rows=5, max_length=500)
```

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current text value. |
| `placeholder` | `str` | `""` | The hint shown when the field is empty. |
| `rows` | `int` | `3` | The number of visible text rows (initial height hint). |
| `max_length` | `int \| None` | `None` | An optional cap on the number of characters. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler invoked with a `TextChangeEvent` on each edit. |

## `Checkbox`

A **labelled boolean checkbox**, styled via the selection-variant API. There is no
`field_variant` here: M3 gives each selection control a single affordance, so the
resolver uses `size` / `color_scheme` plus the `checked` state:

```python
from tempest_core import Checkbox

agree = Checkbox(
    label="I accept the terms",
    checked=False,
    on_change=lambda e: app.set_state(agree=e.value),  # (1)!
)
```

1. `on_change` receives a `ToggleEvent`, whose boolean `value` is the new state.

### Props

On top of the shared selection variant props (`size` / `color_scheme` / `theme` /
`media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The text shown beside the control. |
| `checked` | `bool` | `False` | Whether the box is currently checked. |
| `on_change` | `ToggleHandler \| None` | `None` | Handler invoked with a `ToggleEvent` on toggle. |

!!! note "`checked` feeds the `Style` resolution"
    `resolve_selection_variant` takes `checked`: when on, the box paints the accent
    (`color_scheme`) as its background; when off, it becomes a transparent ring
    with a 2px `outline` border. The box dimension comes from `SELECTION_SIZE`, but
    the 48dp touch target is the containing row's job, never the box.

## `Switch`

A **labelled on/off switch** (toggle). It differs from `Checkbox` only in its
rendered affordance — it carries the same boolean semantics and the same accent
resolution:

```python
from tempest_core import Switch

notifications = Switch(
    label="Notifications",
    checked=True,
    color_scheme="success",
    on_change=lambda e: app.set_state(notify=e.value),
)
```

### Props

On top of the shared selection variant props (`size` / `color_scheme` / `theme` /
`media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The text shown beside the control. |
| `checked` | `bool` | `False` | Whether the switch is currently on. |
| `on_change` | `ToggleHandler \| None` | `None` | Handler invoked with a `ToggleEvent` on toggle. |

## `Slider`

A draggable **single-value slider** over a numeric range, styled via the
slider-variant API (`size` / `color_scheme`, no `variant` — M3 gives a slider a
single affordance):

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

1. `on_change` receives a `SlideEvent` as the value moves.

### Props

On top of the shared slider variant props (`size` / `color_scheme` / `theme` /
`media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `float` | `0.0` | The current value, clamped to `[min_value, max_value]`. |
| `min_value` | `float` | `0.0` | The lowest selectable value. |
| `max_value` | `float` | `100.0` | The highest selectable value. |
| `step` | `float` | `1.0` | The increment between selectable values. |
| `on_change` | `SlideHandler \| None` | `None` | Handler invoked with a `SlideEvent` as the value moves. |

!!! note "`size` changes the track thickness, not the touch target"
    `resolve_slider_variant` takes the track thickness from `SLIDER_SIZE` (2px at
    `XS` to 6px at `LG`) and paints the active track with the `color_scheme`
    accent. The thumb halo and the 48dp touch target are the renderer's job, never
    the track height.

## `DatePicker`

A **date selection field** — a field-shaped trigger (FIELD family) that opens the
platform date picker. It stores the date as an ISO `yyyy-mm-dd` string:

```python
from tempest_core import DatePicker

birthday = DatePicker(
    label="Date of birth",
    value="2000-01-01",
    on_change=lambda e: app.set_state(dob=e.value),  # (1)!
)
```

1. `on_change` receives a `DateChangeEvent` on selection.

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The selected date as an ISO `yyyy-mm-dd` string (`""` if unset). |
| `label` | `str` | `""` | An optional label shown with the field. |
| `on_change` | `DateChangeHandler \| None` | `None` | Handler invoked with a `DateChangeEvent` on selection. |

## `FilePicker`

A **field-shaped trigger** that opens the platform file picker (FIELD family). It
stores the chosen file's display name/URI:

```python
from tempest_core import FilePicker

attachment = FilePicker(
    label="Upload receipt",
    on_select=lambda e: app.set_state(file=e.value),  # (1)!
)
```

1. `on_select` receives a `FileSelectEvent` on selection.

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `"Choose file"` | The button text. |
| `value` | `str` | `""` | The selected file's display name/URI (`""` until one is chosen). |
| `on_select` | `FileSelectHandler \| None` | `None` | Handler invoked with a `FileSelectEvent` on selection. |

## `Dropdown`

A **single-choice** control (select) styled via the field API. The options are
strings in display order, and `value` is `None` while nothing is chosen:

```python
from tempest_core import Dropdown

state = Dropdown(
    options=["CA", "NY", "TX", "FL"],
    placeholder="Select a state",
    on_select=lambda e: app.set_state(state=e.value, index=e.index),  # (1)!
)
```

1. `on_select` receives a `SelectEvent` carrying the option `value` and its 0-based
   `index`.

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | The selectable option strings, in display order. |
| `value` | `str \| None` | `None` | The currently selected option, or `None` when nothing is chosen. |
| `placeholder` | `str` | `"Select…"` | The hint shown while no option is selected. |
| `leading_icon` | `Icons \| str \| None` | `None` | Optional icon on the start (leading) edge. |
| `trailing_icon` | `Icons \| str \| None` | `None` | Optional icon on the end (trailing) edge. |
| `on_select` | `SelectHandler \| None` | `None` | Handler invoked with a `SelectEvent` (with `value` and `index`) on selection. |

## `TimePicker`

A **time selection field** (FIELD family), the twin of `DatePicker`. It stores the
time as a 24-hour `"HH:MM"` string:

```python
from tempest_core import TimePicker

slot = TimePicker(
    label="Time",
    value="14:30",
    on_change=lambda e: app.set_state(time=e.value),  # (1)!
)
```

1. `on_change` receives a `TimeChangeEvent` on selection.

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The selected time as a 24-hour `"HH:MM"` string (`""` if unset). |
| `label` | `str` | `""` | An optional label shown with the field. |
| `on_change` | `TimeChangeHandler \| None` | `None` | Handler invoked with a `TimeChangeEvent` on selection. |

## `RangeSlider`

A **dual-handle slider** selecting a `[low, high]` sub-range (SLIDER family). Same
accent resolution as `Slider`, with two bounds instead of one:

```python
from tempest_core import RangeSlider

price_range = RangeSlider(
    low=100.0,
    high=800.0,
    min_value=0.0,
    max_value=1000.0,
    step=50.0,
    on_change=lambda e: app.set_state(range=(e.low, e.high)),  # (1)!
)
```

1. `on_change` receives a `RangeChangeEvent` carrying both bounds as the range
   moves.

### Props

On top of the shared slider variant props (`size` / `color_scheme` / `theme` /
`media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `low` | `float` | `0.0` | The current lower bound, clamped to `[min_value, high]`. |
| `high` | `float` | `100.0` | The current upper bound, clamped to `[low, max_value]`. |
| `min_value` | `float` | `0.0` | The lowest selectable value. |
| `max_value` | `float` | `100.0` | The highest selectable value. |
| `step` | `float` | `1.0` | The increment between selectable values. |
| `on_change` | `RangeChangeHandler \| None` | `None` | Handler invoked with a `RangeChangeEvent` as the range moves. |

## `Autocomplete`

A **text field that suggests and selects** from a list of options (FIELD family).
It emits two distinct events — a `TextChangeEvent` as you type and a `SelectEvent`
when a suggestion is chosen:

```python
from tempest_core import Autocomplete

city = Autocomplete(
    options=["San Francisco", "San Diego", "San Jose"],
    placeholder="City",
    on_change=lambda e: app.set_state(text=e.value),
    on_select=lambda e: app.set_state(city=e.value),  # (1)!
)
```

1. Both handlers serialize as distinct tokens on the node (the multi-handler
   pattern shared with `LazyColumn`).

### Props

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | The candidate suggestions, filtered against the typed text. |
| `value` | `str` | `""` | The current text value. |
| `placeholder` | `str` | `""` | The hint shown when the field is empty. |
| `leading_icon` | `Icons \| str \| None` | `None` | Optional icon on the start (leading) edge. |
| `trailing_icon` | `Icons \| str \| None` | `None` | Optional icon on the end (trailing) edge. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler invoked with a `TextChangeEvent` on each edit. |
| `on_select` | `SelectHandler \| None` | `None` | Handler invoked with a `SelectEvent` when a suggestion is chosen. |

## `PinInput`

A **segmented PIN / OTP** entry of single-character cells (FIELD family). It emits
a `TextChangeEvent` (the concatenated value) on each edit and a `SubmitEvent` once
every cell is filled:

```python
from tempest_core import PinInput

code = PinInput(
    length=6,
    secure=False,
    on_change=lambda e: app.set_state(otp=e.value),
    on_complete=lambda e: app.verify_code(),  # (1)!
)
```

1. `on_complete` receives a `SubmitEvent` when the last cell is filled.

### Props

On top of the shared field variant props (`size` / `color_scheme` / `theme` /
`media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `field_variant` | `FieldVariant` | `FieldVariant.OUTLINE` **(frozen)** | Fixed to `OUTLINE` — the segmented cells are outlined boxes. |
| `length` | `int` | `6` | The number of single-character cells. |
| `value` | `str` | `""` | The current concatenated value. |
| `secure` | `bool` | `False` | Whether each cell masks its character (PIN rather than OTP). |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler invoked with a `TextChangeEvent` on each edit. |
| `on_complete` | `SubmitHandler \| None` | `None` | Handler invoked with a `SubmitEvent` when all cells are filled. |

!!! warning "`PinInput`'s `field_variant` is frozen"
    Unlike the other fields, `PinInput`'s `field_variant` is `frozen=True`: the
    segmented cells only make sense as `OUTLINE` boxes, so trying to switch it to
    `FILLED`/`FLUSHED` raises a Pydantic validation error. The other variant props
    (`size`, `color_scheme`) stay free.

## `MaskedInput`

A **text field that enforces an input mask** while you type (FIELD family). The
mask uses `9` for a required digit and `A` for a required letter; any other
character is a fixed literal (e.g. `"999.999.999-99"` for a Brazilian CPF):

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

On top of the shared variant props (`field_variant` / `size` / `color_scheme` /
`theme` / `media`):

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `mask` | `str` | `""` | The input mask pattern (`9` digit, `A` letter, else literal). |
| `value` | `str` | `""` | The current text value. |
| `placeholder` | `str` | `""` | The hint shown when the field is empty. |
| `keyboard` | `KeyboardType` | `KeyboardType.TEXT` | The soft keyboard requested. |
| `on_change` | `TextChangeHandler \| None` | `None` | Handler invoked with a `TextChangeEvent` on each edit. |

!!! tip "The renderer translates the mask to its native notation"
    You write the mask in `tempest-core`'s `9`/`A`/literal notation; each renderer
    converts it to its own native input-mask format. The value carried in the
    `TextChangeEvent` reflects the already-masked text.

## Recap

- **Three families**, three resolvers: FIELD (`resolve_field_variant`), SELECTION
  (`resolve_selection_variant`) and SLIDER (`resolve_slider_variant`) — all pure
  and in the engine, with the caller's override merged on top.
- **`FieldVariant`**: `OUTLINE` (default) → `FILLED` → `FLUSHED`; `color_scheme`
  only tints the field's focus/caret/label, never the resting fill.
- **Shared props**: `size` / `color_scheme` shape the density and color; `theme` /
  `media` are build-time inputs and **stay out of the IR**.
- **`state_styles()`** gives the per-`ComponentState` table; only the event→state
  mapping lives in the renderer. `PRESSED` on a field is treated as `FOCUS`.
- **`KeyboardType`** (`TEXT` / `NUMBER` / `EMAIL` / `PHONE` / `URL` / `PASSWORD`)
  picks the soft keyboard; `Input` and `MaskedInput` carry it.
- **Per-widget nuances**: `Input`'s `error` drives `invalid`; `Checkbox`/`Switch`'s
  `checked` feeds resolution; `PinInput`'s `field_variant` is frozen to `OUTLINE`.
