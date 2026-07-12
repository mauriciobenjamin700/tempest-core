# Selection

**Selection** components let a person **pick a value**: a segment, a radio option,
a chip, a star rating. Unlike buttons, they aren't just a tappable affordance —
they carry the idea of a *chosen state*. They are **composite components**
(`Component`): each **lowers** (`render`) to a tree of primitives (`Row` /
`Column` / `Button` / `Text`), so they work in both renderers (Qt and Compose)
and on the device with no changes. 🚀

All of them are **themed via tokens** (Trilho H4): the "chosen" color, the
background, the pill — everything is **resolved from the `Theme`**, not hard-coded.
Dark mode and brand color come for free.

!!! info "What you'll learn here"
    - The **stateless pattern**: the component never stores the choice — the **app**
      holds it and passes it via props (`selected` / `value`) plus a handler
      (`on_select` / `on_rate`).
    - How each component **lowers** to primitives, and why that makes it
      device-ready with no renderer code.
    - How `color_scheme` picks the M3 color family of the chosen item.
    - The difference between a **selectable** chip, a **presentational** chip, and
      the `Tag` (the closed preset of `Chip`).

## The stateless pattern 🧠

Before the components, the core idea. **No** selection component stores its own
choice. The single source of truth is **your app** — it holds the selected
index/value in its state, passes that value in via a prop (`selected`, `value`),
and receives the new value back through the handler (`on_select`, `on_rate`). The
component only **draws** the state you gave it.

```python
from tempest_core.components import SegmentedControl

# The app owns the choice; the component only reflects `selected` and reports taps.
class Preferences:
    def __init__(self) -> None:
        self.tab: int = 0  # (1)!

    def view(self) -> SegmentedControl:
        return SegmentedControl(
            options=["Day", "Week", "Month"],
            selected=self.tab,             # (2)!
            on_select=self._switch_tab,    # (3)!
        )

    def _switch_tab(self, index: int) -> None:
        self.tab = index                   # (4)!
        # ... schedule a rebuild of the view
```

1. The state lives in the **app**, not the component.
2. You **push** the current choice into the component on every build.
3. The handler is called with the tapped index.
4. You **update your state** and rebuild — the component redraws already
   highlighting the new `selected`.

!!! tip "Why stateless?"
    A pure component is **deterministic**: same props → same primitive tree. That
    makes the diff/rebuild predictable, avoids two sources of truth (an "internal
    selected" that disagrees with the app state), and lets the same widget serve
    the renderer and the device with no hidden sync.

## `SegmentedControl`

A compact pill group for a **single choice** — the tabs sit side by side and one
is active. It lowers to a `Row` of `Button`s, with the active segment resolved as
`SOLID` and the rest as `GHOST`.

```python
from tempest_core.components import SegmentedControl

period = SegmentedControl(
    options=["Day", "Week", "Month"],
    selected=1,                              # "Week" active
    on_select=lambda index: print(index),    # (1)!
    color_scheme="primary",
    size="sm",
)
```

1. `on_select` receives the **index** of the tapped segment (an `int`).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | The segment labels, in order. |
| `selected` | `int` | `0` | The index of the active segment. |
| `on_select` | `Callable[[int], Any]` | *(required)* | Called with the tapped segment's index. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the active segment paints with. |
| `size` | `ResponsiveSize` | `SM` | The density of each segment — a `Size` or a per-breakpoint map. |
| `theme` | `Theme` | `Theme()` | The theme resolving the segments. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! note "Active = solid, rest = ghost"
    The segment whose index matches `selected` resolves through the `SOLID` variant
    (filled, highest emphasis) via `resolve_variant`; the others resolve as `GHOST`
    (transparent, quiet). `color_scheme` decides *which* color family paints the
    active one. The track background is the theme's `surface_variant` token.

## `RadioGroup`

A **vertical** single-choice list with radio markers (◉ / ○). It lowers to a
`Column` of `Button`s — one per option — with the chosen row marked and tinted by
the theme accent.

```python
from tempest_core.components import RadioGroup

shipping = RadioGroup(
    options=["Standard", "Express", "Pickup"],
    selected=0,
    on_select=lambda index: print(index),   # (1)!
    color_scheme="primary",
    size="md",
)
```

1. Like `SegmentedControl`: the handler receives the **index** of the tapped
   option.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `options` | `list[str]` | `[]` | The choice labels, in order. |
| `selected` | `int` | `0` | The index of the chosen option. |
| `on_select` | `Callable[[int], Any]` | *(required)* | Called with the tapped option's index. |
| `size` | `ResponsiveSize` | `MD` | The density of each row's marker. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the chosen row's accent paints with. |
| `theme` | `Theme` | `Theme()` | The theme resolving the row colors. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! note "Row colors come from the theme"
    The marker/text color is resolved by the H2 selection variant
    (`resolve_selection_variant`): the chosen row reads the `color_scheme` accent,
    the rest read a muted `on_surface_variant` tone. The ◉/○ glyphs are fixed; only
    the **colors** become theme-driven — which gives dark mode and brand color for
    free.

!!! tip "`SegmentedControl` vs `RadioGroup`"
    Both are single choice over `options`/`selected`/`on_select`. Prefer
    `SegmentedControl` for a **few** short options that fit on one line (filters,
    periods); prefer `RadioGroup` when the options are **longer** or numerous and
    call for a readable vertical list.

## `Chip`

A small rounded label (a "pill"), **optionally selectable**. It's the most
flexible selection component: depending on its props, it lowers to different
things.

```python
from tempest_core.components import Chip

# Selectable filter chip — the app owns `selected`.
filter_chip = Chip(
    label="On sale",
    selected=True,
    on_click=lambda: print("chip tapped"),   # (1)!
    color_scheme="primary",
    size="md",
)

# Presentational chip (no on_click) — becomes a static text pill.
label_chip = Chip(label="New")
```

1. `on_click` takes **no argument** — the chip only reports the tap; knowing which
   chip it is is on you (via closure/app state).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The chip text. |
| `selected` | `bool` | `False` | Whether the chip reads as active (*solid* vs *subtle* badge). |
| `on_click` | `Callable[[], Any] \| None` | `None` | Tap handler; when `None`, the chip is presentational only. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the chip tints with. |
| `size` | `ResponsiveSize` | `MD` | The density of the pill. |
| `theme` | `Theme` | `Theme()` | The theme resolving the chip treatment. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! info "How `Chip` lowers — two paths"
    - `on_click` **set** → lowers to a `Button` carrying the resolved badge style
      (it's tappable).
    - `on_click` **`None`** → lowers to a `Text` (a static pill, no tap
      affordance).

    In both, the pill comes from `resolve_badge_variant`: a `SOLID` badge when
    `selected=True`, a `SUBTLE` badge (tonal, low emphasis) otherwise.

!!! warning "The app owns `selected`"
    Like every selection component, `Chip` **does not toggle itself**. A tap calls
    your `on_click`; it's **your** code that updates the state and rebuilds the chip
    with the new `selected`. The chip only draws the boolean you gave it.

## `Tag`

A **closed, non-selectable** label — a thin preset of `Chip`. A `Tag` is exactly a
`Chip` locked to its presentational, low-emphasis form: never selectable, never
tappable. Use it for **read-only** category/status labels, where a `Chip`'s
interactivity would be wrong.

```python
from tempest_core.components import Tag

status = Tag(label="Archived", color_scheme="neutral")
category = Tag(label="Backend", size="sm")
```

### Props

A `Tag` shares the `Chip` theming props (`label` / `color_scheme` / `size` /
`theme` / `media`), but **pins** two fields:

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `selected` | `bool` | `False` *(frozen)* | A tag is never selected — locked to the *subtle* badge. |
| `on_click` | `Callable[[], Any] \| None` | `None` *(frozen)* | A tag is never tappable — always a static pill. |

!!! note "`selected` and `on_click` are `frozen`"
    On both fields the `Field` is declared with `frozen=True`, so trying to set them
    on a `Tag` is a validation error, not a silent path. That's what makes a `Tag`
    always lower to a static `SUBTLE` pill (a `Text`), reusing the same
    `resolve_badge_variant` as `Chip`.

!!! tip "`Chip` vs `Tag`"
    Need the person to **toggle/pick**? Use `Chip` (with `selected` + `on_click`).
    Just want to **display** a category or status that doesn't react to taps? Use
    `Tag` — the "read-only" intent is explicit in the type.

## `Rating`

A row of stars that **shows** (and optionally **sets**) a 1-based rating. It lowers
to a `Row` of star cells (★ filled / ☆ empty).

```python
from tempest_core.components import Rating

# Interactive: the app owns `value`, the tap reports the new rating.
rating = Rating(
    value=3,
    max_stars=5,
    on_rate=lambda stars: print(stars),   # (1)!
    color_scheme="primary",
)

# Display only (no on_rate) — non-tappable stars.
average = Rating(value=4, max_stars=5)
```

1. `on_rate` receives the **1-based** value of the tapped star (tapping the 3rd
   star reports `3`).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `int` | `0` | The number of filled stars. |
| `max_stars` | `int` | `5` | The total number of stars shown. |
| `on_rate` | `Callable[[int], Any] \| None` | `None` | Handler called with the tapped star's 1-based value; when `None`, it's display only. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the filled stars paint with. |
| `theme` | `Theme` | `Theme()` | The theme resolving the star color. |

!!! note "A clickable star is a transparent `GHOST`"
    When `on_rate` is set, each star lowers to a `GHOST`-variant `Button` with an
    **explicitly transparent** fill — so the glyph reads as a bare star, not a
    filled pill (the `SOLID` default would paint the role color over it). Without
    `on_rate`, each star is a plain `Text`.

!!! warning "`Rating` is stateless too"
    `Rating` draws exactly `value` filled stars — it **does not** increment itself
    on tap. Your `on_rate` reports the chosen rating; the **app** stores that number
    and rebuilds the `Rating` with the new `value`.

## Recap

- **Stateless pattern**: no component stores the choice. The **app** holds
  `selected`/`value`, passes it via a prop, and gets the new value back through
  `on_select` / `on_click` / `on_rate`; the component only draws the given state.
- **Composites that lower**: each is a `Component` that `render`s to a primitive
  tree — device-ready with no renderer code.
- **`SegmentedControl`**: single-choice pills (active = `SOLID`, rest = `GHOST`);
  `on_select` receives the index.
- **`RadioGroup`**: vertical radio list; row colors resolved by
  `resolve_selection_variant`; `on_select` receives the index.
- **`Chip`**: optionally-selectable pill — lowers to a `Button` with `on_click`, or
  a `Text` without it; `SOLID` when `selected`, `SUBTLE` when not.
- **`Tag`**: closed preset of `Chip` with `frozen` `selected`/`on_click` — always a
  static `SUBTLE` pill, for read-only labels.
- **`Rating`**: row of stars; clickable = transparent `GHOST`; `on_rate` receives
  the 1-based rating.
- **Themed via tokens (H4)**: chosen color, background, and pill come from the
  `Theme` and `color_scheme` — dark mode and brand color for free.
