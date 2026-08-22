# Surfaces & cards

**Surfaces** are the themed boxes everything else in `tempest-core` sits on. At
the bottom there is a single primitive — the **`Surface`** — and everything else
(`Card`, `Sidebar`, panels) is that plus a bit of padding and an arrangement of
children. They all resolve their `Style` from the **Chakra** variant API
(`variant` / `color_scheme` / `elevation`) anchored on **Material 3**: you
describe the surface *intent* and the **pure resolver** `resolve_surface_variant`
bakes the concrete `Style` from the `Theme` tokens. 🚀

!!! info "What you'll learn here"
    - The **`Surface` primitive** (un-padded) and how a `Card` is just it + padding + `Column`.
    - The three `CardVariant` **variants** (`ELEVATED` / `FILLED` / `OUTLINED`) and which M3 treatment each lowers to.
    - Why **elevation is a `Shadow`** mapped from the M3 level, never a new `Style` field.
    - The **content items** (`ListTile`, `Avatar`, `Divider`) and how they read color and spacing from the theme.
    - The **layout** components (`Grid`, `HStack`, `VStack`, `Scaffold`, `Sidebar`) and the token-step `gap`.
    - The **composition helpers**: `merge_style` and the default palette tokens.

## Surfaces

The surface is the raw themed box. `Surface` has no padding of its own;
`StyledContainer` adds a token-step padding over the primitive `Container`.

### `Surface`

The **un-padded** surface primitive: a single-child box carrying the resolved
variant `Style`, with no inner padding or gap. It is what every higher-level
surface (`Card`, `Accordion` header, …) builds on.

```python
from tempest_core.components import Surface
from tempest_core.widgets import Text

surface = Surface(child=Text(content="Hello"))
```

That `Surface(child=…)` is already an **elevated, neutral** surface — ready for
the renderers. Pick the variant and color family by *intent*:

```python
from tempest_core.components import Surface
from tempest_core.style import CardVariant
from tempest_core.widgets import Text

panel = Surface(
    variant=CardVariant.OUTLINED,  # (1)!
    color_scheme="primary",  # tonal *_container
    elevation=0,  # explicit M3 level
    child=Text(content="Panel"),
)
```

1. `variant` also accepts the equivalent string (`"outlined"`); the `CardVariant`
   enum makes the intent explicit.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget (optional). |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family (`"neutral"` uses the plain surface roles; a family uses the tonal `*_container` roles). |
| `elevation` | `int \| None` | `None` | Explicit M3 level (0-5) overriding the variant default. |
| `radius_step` | `str` | `"md"` | The shape-scale step for the corner radius. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (accepted for parity; unused here). |

!!! note "`Surface` is the un-padded base; `Card` is `Surface` + padding + `Column`"
    Unlike `Card`, `Surface` adds **no inner padding or gap** — it is the bare
    surface, leaving content layout to whatever it wraps. It resolves the variant
    `Style`, merges the caller's explicit `style` on top (its set fields win), and
    lowers to a single-child `Container`.

### `StyledContainer`

A single-child box with **token-step padding** over the primitive `Container`. It
gives the primitive design-system ergonomics without mutating it: `padding`
accepts a step name (`"md"` / `"lg"`) resolved against the theme's spacing scale,
or a raw `float` for backward-compatibility.

```python
from tempest_core.components import StyledContainer
from tempest_core.widgets import Text

box = StyledContainer(padding="lg", child=Text(content="Roomy content"))
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget (optional). |
| `padding` | `float \| str` | `"md"` | The inner padding — a token-step name (`"md"`) or a `float` in logical pixels. |
| `theme` | `Theme` | `Theme()` | The theme whose spacing scale resolves a step name. |

!!! tip "Token step or float — both work"
    A string (`"md"`) resolves via `Theme.space(...)`; a raw `float`
    (`padding=24.0`) passes straight through. An explicit `style` is merged on top
    of the resolved padding.

## Cards & items

Classic presentational building blocks that lower to primitives. With the
design-system tokens, each reads color and spacing from the `Theme` rather than
hard-coded hexes.

### `Card`

A themed surface grouping a stack of children (Material 3 card). It is exactly
**`Surface` + padding + `Column`**: it resolves the surface treatment from
`variant` / `color_scheme` / `elevation`, adds its own padding, and stacks the
children in a `Column`.

```python
from tempest_core.components import Card
from tempest_core.widgets import Text

card = Card(
    children=[
        Text(content="Title"),
        Text(content="Card body."),
    ]
)
```

A no-arg `Card(children=…)` produces an **elevated, neutral** card. Pick the
variant and tune the spacing steps:

```python
from tempest_core.components import Card
from tempest_core.style import CardVariant
from tempest_core.widgets import Text

featured = Card(
    variant=CardVariant.FILLED,
    color_scheme="primary",
    padding_step="lg",  # inner padding
    gap_step="md",  # space between children
    children=[Text(content="Pro plan")],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The widgets stacked vertically inside the card. |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the card tints with. |
| `elevation` | `int \| None` | `None` | Explicit M3 level (0-5) overriding the default. |
| `padding_step` | `str` | `"md"` | The spacing-scale step for the inner padding. |
| `radius_step` | `str` | `"md"` | The shape-scale step for the corner radius. |
| `gap_step` | `str` | `"sm"` | The spacing-scale step for the gap between children. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (accepted for parity; unused). |

!!! info "The three `CardVariant` variants"
    | `CardVariant` | M3 treatment | Background | Shadow | Border |
    | --- | --- | --- | --- | --- |
    | `ELEVATED` | *elevated card* | `surface` | elevation level 1 | — |
    | `FILLED` | *filled card* | `surface_variant` (tonal) | — | — |
    | `OUTLINED` | *outlined card* | `surface` | — | `outline` (1px) |

    `color_scheme` decides *which* color family paints the treatment: `"neutral"`
    uses the plain surface roles; a family (`"primary"`, `"error"`, …) uses the
    tonal `*_container` roles.

!!! warning "Elevation is a `Shadow`, not a new `Style` field"
    An M3 elevation level (0-5) is **mapped to a `Shadow`** (blur + downward offset)
    via `_elevation_shadow` — never an `elevation` field on `Style`. By default
    `ELEVATED` raises to level 1 and `FILLED`/`OUTLINED` stay flush (level 0);
    passing `elevation=` overrides that default. The renderer translates the
    resolved `Shadow` into native elevation (Compose `Modifier.shadow` / Qt
    `QGraphicsDropShadowEffect`).

### `ListTile`

A single list row: optional `leading`/`trailing` widgets around a title block.
The title uses `ON_SURFACE`, the subtitle uses `ON_SURFACE_VARIANT`, and the
gaps/padding come from the theme's spacing scale.

```python
from tempest_core.components import Avatar, ListTile
from tempest_core import IconButton

row = ListTile(
    title="Mauricio Benjamin",
    subtitle="mauricio@example.com",
    leading=Avatar(initials="MB"),
    trailing=IconButton(icon="chevron_right", label="Open"),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The row's primary text. |
| `subtitle` | `str \| None` | `None` | An optional second line, shown muted under the title. |
| `leading` | `Widget \| None` | `None` | Optional widget before the text (e.g. an `Avatar`). |
| `trailing` | `Widget \| None` | `None` | Optional widget after the text (e.g. a `Button`). |
| `color_scheme` | `str \| None` | `None` | Optional M3 family tinting the title; `None` keeps the neutral `ON_SURFACE`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply colors and spacing. |

!!! note "`ListTile` is presentational — no row-level `on_click`"
    Because tap handling only exists on `Button` in the primitive set, the row has
    no `on_click`. Place a `Button` (or `IconButton`) in the `trailing` slot for
    actions. The title block grows (`grow=1.0`) and pushes `trailing` to the edge;
    the accessibility surface (`semantics`) is preserved on the row.

### `Avatar`

A round badge showing short initials, tinted via the container roles. The circle
fills with the `color_scheme`'s tonal `*_container` role and the initials use its
legible `on_*_container` role (WCAG-AA safe by construction).

```python
from tempest_core.components import Avatar

avatar = Avatar(initials="MB", size=48.0, color_scheme="secondary")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `initials` | `str` | `""` | The short text inside the circle (e.g. `"MB"`). |
| `size` | `float` | `40.0` | The circle's diameter in logical pixels. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the circle tints with. |
| `theme` | `Theme` | `Theme()` | The theme resolving the circle colors. |

!!! tip "The radius follows the size"
    `radius` is pinned to `size / 2.0` — always a perfect circle, whatever the
    `size`. Colors come from the scheme's `(*_container, on_*_container)` pair; an
    unknown scheme falls back to the primary container.

### `Divider`

A thin horizontal rule, tinted with Material 3's `OUTLINE_VARIANT` color.
`thickness` accepts a token-step name (resolved against the shape scale) or a raw
`float`.

```python
from tempest_core.components import Divider

rule = Divider()  # 1px outline-variant rule
thick = Divider(thickness=2.0, color_scheme="primary")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `thickness` | `float \| str` | `1.0` | The line's height — a token-step name (`"xs"`) or a `float`. |
| `color_scheme` | `str \| None` | `None` | Optional M3 family for the rule color; `None` uses the neutral `OUTLINE_VARIANT`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply the color and step. |

## Layout components

Page-structure components. They all lower to primitive `Column` / `Row` /
`Container` trees.

### `Grid`

A fixed-column grid laying children out in equal-width cells, filled
left-to-right then top-to-bottom.

```python
from tempest_core.components import Card, Grid
from tempest_core.widgets import Text

grid = Grid(
    columns=3,
    gap="md",  # token step or float
    children=[Card(children=[Text(content=f"Item {i}")]) for i in range(6)],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The cells, filled left→right, then top→bottom. |
| `columns` | `int` | `2` | The number of columns per row (clamped to at least 1). |
| `gap` | `float \| str` | `8.0` | The spacing between cells — a token-step name (`"md"`) or a `float`. |
| `theme` | `Theme` | `Theme()` | The theme whose spacing scale resolves a step name. |

!!! note "Cells grow to share width; the final row is padded"
    Each child is wrapped in a `Container` that grows (`grow=1.0`), so columns
    share the width equally (the *flex*). Short final rows are padded with empty
    cells to keep the columns aligned.

### `HStack`

A horizontal stack: children left-to-right with a token-step `gap`. A
SwiftUI-style ergonomic wrapper over the primitive `Row`, with `align`
(cross-axis) and `justify` (main-axis) surfaced.

```python
from tempest_core.components import HStack
from tempest_core.style import JustifyContent
from tempest_core.widgets import Text

bar = HStack(
    gap="sm",
    justify=JustifyContent.SPACE_BETWEEN,
    children=[Text(content="Left"), Text(content="Right")],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, laid left-to-right. |
| `gap` | `float \| str` | `"md"` | The spacing between children — a token-step name or a `float`. |
| `align` | `AlignItems \| None` | `CENTER` | The cross-axis (vertical) alignment of the children. |
| `justify` | `JustifyContent \| None` | `None` | The main-axis (horizontal) distribution of the children. |
| `theme` | `Theme` | `Theme()` | The theme whose spacing scale resolves the gap. |

### `VStack`

The vertical sibling of `HStack`, over the primitive `Column`: children
top-to-bottom with a token-step `gap`. Here `align` is the cross-axis
(horizontal) and `justify` is the main-axis (vertical).

```python
from tempest_core.components import VStack
from tempest_core.widgets import Text

column = VStack(
    gap="lg",
    children=[Text(content="One"), Text(content="Two"), Text(content="Three")],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, laid top-to-bottom. |
| `gap` | `float \| str` | `"md"` | The spacing between children — a token-step name or a `float`. |
| `align` | `AlignItems \| None` | `None` | The cross-axis (horizontal) alignment of the children. |
| `justify` | `JustifyContent \| None` | `None` | The main-axis (vertical) distribution of the children. |
| `theme` | `Theme` | `Theme()` | The theme whose spacing scale resolves the gap. |

!!! tip "Token-step `gap`, always coherent"
    In both stacks (and in `Grid`), a string `gap` (`"md"`) resolves against the
    theme's spacing scale via `Theme.space(...)`; a raw `float` passes straight
    through. Preferring the steps keeps the vertical/horizontal rhythm consistent
    with the rest of the design system.

### `Scaffold`

The page frame: an app bar on top, a growing body, and an optional bottom bar.
The theme's `BACKGROUND` fills the frame.

```python
from tempest_core.components import Scaffold
from tempest_core import AppBar
from tempest_core.widgets import Text

page = Scaffold(
    app_bar=AppBar(title="Home"),
    body=Text(content="Page content"),
    scroll=True,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `app_bar` | `Widget \| None` | `None` | The top bar (commonly an `AppBar`); omitted when `None`. |
| `body` | `Widget \| None` | `None` | The main content; becomes an empty column when `None`. |
| `bottom_bar` | `Widget \| None` | `None` | The bottom bar (e.g. a `NavBar` or `Footer`); omitted when `None`. |
| `scroll` | `bool` | `False` | When `True`, wraps the body in a `ScrollView` (a Qt convenience). |
| `theme` | `Theme` | `Theme()` | The theme whose `BACKGROUND` role fills the frame. |

!!! note "The body grows; the bars stay at the edges"
    `Scaffold` lowers to a `Column` stacking, in order, the app bar, the body
    (wrapped in a growing container, `grow=1.0`, or a `ScrollView` when
    `scroll=True`), and the bottom bar. The body *flex* pushes the bars to the top
    and bottom of the frame.

### `Sidebar`

A fixed-width lateral column of navigation/content widgets. The panel surface is
resolved from `variant` / `color_scheme` / `elevation`, mirroring a card; the
fixed width and padding are unchanged.

```python
from tempest_core.components import Sidebar
from tempest_core import Button

sidebar = Sidebar(
    width=280.0,
    children=[
        Button(label="Home", variant="ghost"),
        Button(label="Settings", variant="ghost"),
    ],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The widgets stacked top-to-bottom in the sidebar. |
| `width` | `float` | `240.0` | The sidebar's fixed width in logical pixels. |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the sidebar tints with. |
| `elevation` | `int \| None` | `None` | Explicit M3 level (0-5) overriding the default. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the panel surface. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (accepted for parity; forwarded). |

## Composition helpers

To build custom components in the same idiom, the package re-exports the
style-merge helper and a small default dark palette.

### `merge_style`

Overlays the **set** fields of an `override` onto a base `Style`. Only fields
explicitly non-`None` on the override win; everything else keeps the component's
default. Since `Style` is frozen, it returns a fresh merged copy.

```python
from tempest_core.components import merge_style
from tempest_core.style import Style

base = Style(padding=None, radius=8.0, gap=4.0)
final = merge_style(base, Style(radius=16.0))  # radius wins; gap and padding from base
```

This is exactly the mechanism every component uses to let you override only the
fields you care about: each `render` builds a default `Style` and calls
`merge_style(default, self.style)`. Passing `override=None` returns the untouched
`base`.

!!! info "Override always on top, without losing the default"
    It's the same idiom as the buttons (the override wins on the fields it sets)
    applied to surfaces and items. You never lose the component's default style by
    setting a single field via `style`.

### Default palette tokens

Six `Color` constants — a restrained dark palette matching the examples. They
serve as ready-made values when assembling components outside a full `Theme`.

```python
from tempest_core.components import (
    BACKGROUND,
    SURFACE,
    ACCENT,
    MUTED,
    ON_SURFACE,
    ON_MUTED,
)
from tempest_core.style import Style
from tempest_core.widgets import Container, Text

box = Container(
    style=Style(background=SURFACE),
    child=Text(content="Label", style=Style(color=ON_SURFACE)),
)
```

| Token | Hex | Role |
| --- | --- | --- |
| `BACKGROUND` | `#0b0f14` | Page / frame background. |
| `SURFACE` | `#1f2937` | Elevated surface (cards, panels). |
| `ACCENT` | `#2563eb` | Accent / action color. |
| `MUTED` | `#374151` | Muted / secondary surface. |
| `ON_SURFACE` | `#f9fafb` | Legible content over `SURFACE`. |
| `ON_MUTED` | `#9ca3af` | Muted content over `MUTED`. |

!!! tip "Tokens are ready-made values, not a `Theme` replacement"
    They give an `AppBar` or `Scaffold` an intentional look out of the box. For
    full theming and role resolution (the M3 `*_container` roles, elevation, etc.),
    pass a `Theme` — see the [design-system tutorial](../tutorial/design-system.md).

## Recap

- **`Surface`** is the un-padded primitive; **`Card` is `Surface` + padding +
  `Column`**. Both resolve via `resolve_surface_variant` from `variant` /
  `color_scheme` / `elevation`.
- **`CardVariant`**: `ELEVATED` (elevated card, level-1 shadow) → `FILLED` (tonal
  `surface_variant`, no shadow) → `OUTLINED` (`outline` border, no shadow).
- **Elevation is a `Shadow`** mapped from the M3 level (0-5), never a new `Style`
  field; the renderer translates it into native elevation.
- **`StyledContainer`** gives the primitive `Container` token-step padding without
  mutating it.
- **Content items** — `ListTile` (presentational, action goes in `trailing`),
  `Avatar` (tonal circle, radius = `size / 2`), `Divider` (`OUTLINE_VARIANT` rule)
  — read color and spacing from the theme.
- **Layout** — `Grid` (cells grow to share width), `HStack` / `VStack` (stacks
  with a token-step `gap`), `Scaffold` (body grows between the bars), `Sidebar`
  (fixed-width panel with a resolved surface).
- **Helpers** — `merge_style` overlays the override's set fields; the tokens
  `BACKGROUND` / `SURFACE` / `ACCENT` / `MUTED` / `ON_SURFACE` / `ON_MUTED` are
  ready-made palette values.
