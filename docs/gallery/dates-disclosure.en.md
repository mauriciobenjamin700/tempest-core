# Dates & disclosure

This page groups two small but heavily used families in `tempest-core`: the
**date/time** components — **`Calendar`** (month grid) and **`Clock`** (digital
clock) — and the one **disclosure** component, **`Accordion`** (a section that
expands and collapses). All are `Component`s: they describe *intent* and **lower
to primitives** (`Text` / `Row` / `Column` / `Container` / `Button`) at `render`
time, so they work in both renderers with no renderer changes. 🚀

!!! info "What you'll learn here"
    - How `Calendar` builds the month grid and reports the tapped day via `on_select`.
    - How `Clock` merely **displays** a time string — the app drives the tick.
    - Why both moved to the **M3 theme tokens** (Track H6) and what that changes
      visually.
    - How `Accordion` is **app-controlled**: `open` lives in state and `on_toggle`
      flips it.

## Dates & time

Both time components share the same philosophy: **the core does not tell time**.
`Calendar` draws a month and reports which day you tapped; `Clock` just paints
the string the app already formatted. Both read colors from the `theme` instead
of hard-coded hexes.

### `Calendar`

A month grid of selectable day cells. In the minimal case you pass only
`on_select` — the month and selection default to empty (current month, nothing
selected):

```python
from tempest_core.components import Calendar

agenda = Calendar(on_select=lambda iso: print(iso))
```

That single `Calendar(on_select=…)` already renders the **current month** against
the default M3 light theme, with a title, a weekday header and one row per week.
To control the displayed month and the highlighted day, pass `month` and
`selected` from app state:

```python
from tempest_core.components import Calendar

agenda = Calendar(
    month="2026-07",  # (1)!
    selected="2026-07-12",
    on_select=lambda iso: app.set_state(selected=iso),  # (2)!
    color_scheme="primary",
)
```

1. `month` is `"YYYY-MM"`; empty falls back to the current month. `selected` is
   `"YYYY-MM-DD"` and only highlights when it falls in the displayed month.
2. `on_select` receives the tapped day's **ISO** `"YYYY-MM-DD"` string. Store it
   in state and feed it back through `selected` to close the loop (see
   [API reference](../reference.md)).

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `on_select` | `Callable[[str], Any]` | *(required)* | Called with the tapped day's ISO `"YYYY-MM-DD"`. |
| `month` | `str` | `""` | The displayed month as `"YYYY-MM"`; empty means the current month. |
| `selected` | `str` | `""` | The selected day as `"YYYY-MM-DD"`; highlighted when it falls in the displayed month; empty = no selection. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the selected day fills with. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply the colors. |
| `style` | `Style \| None` | `None` | Override merged on top of the grid's default `Style` (via `merge_style`). |
| `key` | `str \| None` | `None` | Reconciliation key; falls back to `"calendar"` when absent. |

!!! note "Moved to the theme tokens (Track H6)"
    `Calendar` **no longer hard-codes hexes**. The title and day text read the
    `ON_SURFACE` role; the weekday header and unselected days read the muted
    `ON_SURFACE_VARIANT` / `SURFACE_VARIANT` roles; the selected day fills with the
    `color_scheme` role (default `primary`) over its legible `on_*` content — all
    resolved from the `theme`. It's backward-compatible — `Calendar(on_select=…)`
    now renders against the M3 **light** theme (a visual shift from the previous
    dark palette).

!!! tip "`Calendar` is controlled, like the rest of the kit"
    Selection doesn't live inside the component: `on_select` hands you the date,
    you store it in app state and feed it back through `selected`. Same pattern as
    `Drawer` and `Accordion` — the core stays stateless, the app is the source of
    truth.

### `Clock`

A digital clock face that renders a **preformatted** time string. The component
does not tick on its own — the app formats and updates the text from state (as in
the `stopwatch` example):

```python
from tempest_core.components import Clock

clock = Clock(time="12:34:56")
```

Pass a `label` for a muted caption under the time, and an optional `color_scheme`
to tint the time:

```python
from tempest_core.components import Clock

stopwatch = Clock(
    time="00:00:42",
    label="Elapsed time",  # (1)!
    color_scheme="primary",  # (2)!
)
```

1. `label` is an optional caption; when `None`, `Clock` renders the time only.
2. `color_scheme` is optional — `None` (or `"neutral"`) keeps the time in the
   neutral `ON_SURFACE`.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `time` | `str` | `""` | The time text (e.g. `"12:34:56"`); the app formats and ticks it from state. |
| `label` | `str \| None` | `None` | Optional caption shown muted under the time. |
| `color_scheme` | `str \| None` | `None` | Optional M3 role family tinting the time; `None` keeps the neutral `ON_SURFACE`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply the colors. |
| `style` | `Style \| None` | `None` | Override merged on top of the centered default `Style`. |
| `key` | `str \| None` | `None` | Reconciliation key; falls back to `"clock"` when absent. |

!!! note "Moved to the theme tokens (Track H6)"
    Like `Calendar`, `Clock` stopped hard-coding hexes: the time reads `ON_SURFACE`
    (or the `color_scheme` role, when given), the caption reads the muted
    `ON_SURFACE_VARIANT` and the background reads `SURFACE` — all from the `theme`.
    `Clock(time=…)` still works and now renders against the M3 **light** theme (a
    visual shift from the previous dark palette).

!!! warning "`Clock` does not count time"
    It's a **face**, not a timer. Passing `time="12:34:56"` shows exactly that
    string. Whatever increments the clock (an `asyncio` loop, a `Timer`, a state
    tick) is the app — the core stays stateless and deterministic on purpose.

## Disclosure

Disclosure is the "show/hide on demand" pattern. The kit ships one component for
it: `Accordion`.

### `Accordion`

A titled section whose body shows **only when `open`**. There's no overlay: an
open accordion simply renders its body below the header. `open` is
**controlled** — it lives in app state and is flipped by the header's
`on_toggle`, mirroring `Drawer`:

```python
from tempest_core.components import Accordion
from tempest_core.widgets import Text

details = Accordion(
    title="Order details",
    open=app.state.details_open,  # (1)!
    on_toggle=lambda: app.set_state(details_open=not app.state.details_open),
    children=[Text(content="Delivery expected on Friday.")],  # (2)!
)
```

1. `open` comes from app state — the component never stores this boolean.
2. `children` are revealed only when `open` is `True`; closed, the header renders
   on its own.

The header gets a simple rotation marker — `▸` when closed, `▾` when open —
prefixed to the title, so the user sees the state at no renderer cost.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `on_toggle` | `Callable[[], Any]` | *(required)* | Called when the header is tapped (flip `open` in state). |
| `title` | `str` | `""` | The header text. |
| `open` | `bool` | `False` | Whether the body is expanded. |
| `children` | `list[Widget]` | `[]` | The widgets revealed when open. |
| `variant` | `CardVariant` | `FILLED` | The header's surface treatment (filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to tint the header with. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the header surface. |
| `style` | `Style \| None` | `None` | Override merged on top of the container's default `Style`. |
| `key` | `str \| None` | `None` | Reconciliation key; falls back to `"accordion"` when absent. |

!!! note "The header is a resolved surface (Track H3)"
    The header doesn't hard-code colors: it goes through `resolve_surface_variant`,
    which produces a *filled* or *outlined* Material 3 surface from `variant` and
    `color_scheme`, with the spacing steps (`padding`/`radius`) coming from the
    theme's scale. On top of that, the header text gets `FontWeight.BOLD`.

!!! tip "Expand/collapse is the app's call"
    Because `open` is external, you own the policy: an accordion open by default, a
    "single-open" group where opening one closes the others, a state persisted
    across sessions — it all lives in your `set_state`. `Accordion` just reflects
    the boolean you give it.

!!! info "No body when closed, no hidden cost"
    Closed, `Accordion` renders **only** the header button — the `children` never
    enter the primitive tree. Opening inserts a `Column` with the body below;
    closing removes it. Nothing stays mounted and hidden.

## Recap

- **Three components, two families**: `Calendar` + `Clock` (date/time) and
  `Accordion` (disclosure), all `Component`s that lower to primitives.
- **`Calendar`**: a controlled month grid; `on_select` hands you the ISO
  `"YYYY-MM-DD"`, you feed it back through `selected`. The chosen day fills with
  the `color_scheme`.
- **`Clock`**: a **face**, not a timer — it shows the `time` string the app
  formats and ticks; `label` and `color_scheme` optional.
- **Theme tokens (Track H6)**: `Calendar` and `Clock` stopped hard-coding hexes
  and read `ON_SURFACE` / `ON_SURFACE_VARIANT` / `SURFACE` from the `theme` — M3
  light by default.
- **`Accordion`**: a controlled titled section; `open` lives in state and
  `on_toggle` flips it. The header is resolved by `resolve_surface_variant`
  (Track H3); closed, the body isn't even mounted.
