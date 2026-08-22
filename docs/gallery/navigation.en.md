# Navigation

Navigation in `tempest-core` splits into **two families**. The **components**
are page pieces that **lower to primitives** (`Row`/`Column`/`Container`) and
resolve their look from the `Theme` tokens — bars, tabs, rails and bar fields. The
**routing widgets** are the IR nodes that host the *route stack* in the tree:
`Navigator`, `TabView`, `TabBar` and `RouteDrawer`. Both families import from the
root (`from tempest_core import ...`); what differs is what they do, not where
they live. 🚀

!!! info "What you'll learn here"
    - The top/bottom **bars** (`AppBar`, `CollapsingAppBar`, `Header`, `Footer`)
      and how they resolve their **surface** from theme tokens.
    - The **tab/rail** navigation (`NavBar`, `Tabs`, `Breadcrumb`): active item as
      a **highlight pill**, active tab with an **underline**, selection
      **controlled by the app**.
    - The **side menu** (`Burger`, `Drawer`): `Burger` lowers to an `IconButton`;
      `Drawer` is a **controlled** panel.
    - The **routing widgets** (`Navigator`, `TabView`, `TabBar`, `RouteDrawer`) —
      the IR nodes that host the route stack.
    - The **bar fields** (`SearchBar`, `Stepper`) assembled over primitives.

!!! note "One place to import from"
    Everything public comes from the root: `from tempest_core import AppBar,
    NavBar, Navigator, TabView, TabBar, RouteDrawer`. The submodules still exist,
    but you no longer have to know which one a symbol lives in.

## Bars

Bars are page-structure `Component`s. `AppBar`, `Footer` and `CollapsingAppBar`
resolve their **surface** (background + elevation shadow + tinted container) via
`resolve_surface_variant`, exactly like a card; the title/content color is that
surface's legible content. `Header` reads colors and spacing straight from the
`Theme` tokens.

### `AppBar`

A top application bar: optional `leading`, `title` and trailing `actions`. In the
minimal case you pass only the `title`:

```python
from tempest_core import AppBar
from tempest_core import Button, IconButton

bar = AppBar(
    title="Inbox",
    leading=IconButton(icon="arrow_back", label="Back"),
    actions=[
        IconButton(icon="search", label="Search"),
        Button(label="New"),
    ],
    variant="elevated",
    color_scheme="primary",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The bar's title text. |
| `leading` | `Widget \| None` | `None` | Widget before the title (menu/back); omitted when `None`. |
| `actions` | `list[Widget]` | `[]` | Trailing action widgets at the end of the bar. |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to tint with. |
| `elevation` | `int \| None` | `None` | M3 elevation level (0-5) overriding the default. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (parity; forwarded). |

!!! tip "Surface via resolver, title on top"
    The bar is assembled with `merge_styles(surface, ...)`: `resolve_surface_variant`
    yields background + elevation + the **legible content color**, and the title
    inherits it. An explicit `style` is merged **on top** of the resolved surface
    (its set fields win). `AppBar(title=…)` alone is already an elevated neutral bar.

### `CollapsingAppBar`

A *sliver*-style bar that shrinks as the user scrolls the content. It doesn't
listen to scroll itself: the app reads the offset from the list's `ScrollEvent`,
stores it in state and passes it back as `scroll_offset` — the height (and title
font) is derived from that in pure Python, so the reconciler only diffs
`Style.height`:

```python
from tempest_core import CollapsingAppBar

bar = CollapsingAppBar(
    title="Gallery",
    expanded_height=200.0,
    collapsed_height=56.0,
    scroll_offset=app.state.scroll,  # (1)!
    color_scheme="primary",
)
```

1. You feed `scroll_offset` from your scrollable list's `on_scroll`; the bar
   derives the height and the title font between expanded and collapsed.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The bar's title text. |
| `expanded_height` | `float` | `200.0` | The height at the top of the scroll (offset `0`). |
| `collapsed_height` | `float` | `56.0` | The minimum height once fully collapsed. |
| `scroll_offset` | `float` | `0.0` | The current offset (logical px) driven by the app via `on_scroll`. |
| `background` | `Color \| None` | `None` | Background overriding the resolved surface fill (legacy escape hatch). |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to tint with. |
| `elevation` | `int \| None` | `None` | M3 elevation level (0-5) overriding the default. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (parity; forwarded). |
| `style` | `Style \| None` | `None` | Style overlaid on the bar's derived default. |

!!! note "Collapse with no new IR"
    The height eases from `expanded_height` (offset `0`) down to `collapsed_height`
    (once the collapse distance is passed), and the title font goes from 28 to 20 in
    step. It's all ordinary `Style.height`/`font_size` — no new event, no renderer
    change. The legacy `background` still wins when set.

### `Header`

A page header band: a title with an optional subtitle. Unlike the other bars, it
has **no `variant`** — a header is a flat band, not an elevated surface. Colors
come straight from the tokens (`SURFACE_VARIANT` fill, `ON_SURFACE` title,
`ON_SURFACE_VARIANT` subtitle):

```python
from tempest_core import Header

header = Header(
    title="Settings",
    subtitle="Manage your account and preferences",
    color_scheme="primary",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The header's primary line. |
| `subtitle` | `str \| None` | `None` | Optional secondary line, shown muted under the title. |
| `color_scheme` | `str \| None` | `None` | Optional M3 role tinting the title; `None` keeps the neutral `ON_SURFACE`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply colors and spacing. |

!!! info "Tokens only, no resolved surface"
    `Header` doesn't go through `resolve_surface_variant`: it reads `SURFACE_VARIANT`,
    `ON_SURFACE` and `ON_SURFACE_VARIANT` directly, and its typography comes from
    `theme.typography("headline_small")`/`("body_medium")`. A `color_scheme` (other
    than `"neutral"`) tints only the title with the role color.

### `Footer`

A bottom bar holding arbitrary, centered content. It mirrors `AppBar` on surface
resolution:

```python
from tempest_core import Footer
from tempest_core import Text

footer = Footer(
    children=[Text(content="© 2026 Tempest")],
    variant="filled",
    color_scheme="neutral",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The widgets laid out in the footer (links, labels). |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to tint with. |
| `elevation` | `int \| None` | `None` | M3 elevation level (0-5) overriding the default. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (parity; forwarded). |

## Tab/rail navigation

These components are **presentational selection**: the active index lives in app
state and is toggled from `on_select`. Each item lowers to a `Button` whose handler
closes over the index — no internal state of its own.

### `NavBar`

A horizontal navigation bar with one highlighted item. The active item becomes a
**highlight pill** (`resolve_badge_variant`, SOLID, on `color_scheme`); inactive
ones are a low-emphasis GHOST treatment (neutral). The bar itself is a resolved
surface:

```python
from tempest_core import NavBar

bar = NavBar(
    items=["Home", "Search", "Profile"],
    active=app.state.tab,  # (1)!
    on_select=lambda i: app.set_state(tab=i),
    color_scheme="primary",
)
```

1. **App-controlled** selection: `NavBar` doesn't hold the index — you pass the
   `active` from your state and react in `on_select`.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `items` | `list[str]` | `[]` | The visible item labels, in order. |
| `active` | `int` | `0` | The index of the currently selected item. |
| `on_select` | `Callable[[int], Any]` | *(required)* | Called with the tapped item's index. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the active pill paints with. |
| `size` | `ResponsiveSize` | `Size.MD` | The density — a single `Size` or a per-breakpoint map. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the bar and items. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! tip "Active item = highlight pill"
    The selected item uses `resolve_badge_variant(SOLID)` — the same highlight pill
    as the badge system — while the others use `resolve_variant(GHOST)` neutral.
    Each item gets `grow=1.0`, so they fill the bar evenly.

### `Tabs`

A tab strip whose active tab carries an **underline**. Each tab is a GHOST button;
the active one takes the `color_scheme` role color plus a thin bottom `SideBorder`
(2px) as the indicator — using only existing `Style` fields, **no** new field:

```python
from tempest_core import Tabs

tabs = Tabs(
    tabs=["Overview", "Activity", "Settings"],
    active=app.state.tab,
    on_select=lambda i: app.set_state(tab=i),
    color_scheme="primary",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | `[]` | The visible tab labels, in order. |
| `active` | `int` | `0` | The index of the currently selected tab. |
| `on_select` | `Callable[[int], Any]` | *(required)* | Called with the tapped tab's index. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the active tab + underline use. |
| `size` | `ResponsiveSize` | `Size.MD` | The density — a single `Size` or a per-breakpoint map. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the strip and tabs. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! note "Active tab = underline, not pill"
    Where `NavBar` highlights with a filled pill, `Tabs` highlights with the
    **underline indicator**: the active tab takes the role color plus a
    `Border(width=2.0, color=accent)` on the bottom. Like `NavBar`, selection is
    controlled by the app via `active`/`on_select`.

### `Breadcrumb`

A trail of crumbs joined by a separator. Colors come from the tokens: the current
(last) crumb uses `ON_SURFACE`, the rest `ON_SURFACE_VARIANT`, and the separators
`ON_SURFACE_VARIANT`. If you pass `on_select`, navigable crumbs become links
(`resolve_variant` LINK) — **the last is never tappable**:

```python
from tempest_core import Breadcrumb

trail = Breadcrumb(
    items=["Home", "Projects", "tempest-core"],
    separator="/",
    on_select=lambda i: app.navigate_to(i),
    color_scheme="primary",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `items` | `list[str]` | `[]` | The crumb labels from root to current, in order. |
| `separator` | `str` | `"/"` | The text drawn between crumbs. |
| `on_select` | `Callable[[int], Any] \| None` | `None` | Optional handler with the crumb's index; `None` keeps everything presentational. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the link crumb paints with. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply colors and the link. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (parity; forwarded). |

!!! info "The last crumb is always presentational"
    Even with `on_select` set, the current crumb (`index == len(items) - 1`) is a
    `Text`, never a `Button` — you don't navigate to where you already are. Without
    `on_select`, every crumb is `Text`.

## Side menu

### `Burger`

A hamburger menu button. It **lowers to an `IconButton`** showing the curated
`Icons.MENU` glyph in the GHOST variant — so it reuses the H1 variant resolver and
the icon system (a real line icon, not a literal character). The typical use is to
toggle a `Drawer`:

```python
from tempest_core import Burger

button = Burger(
    on_click=lambda: app.set_state(menu_open=not app.state.menu_open),
    color_scheme="neutral",
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `on_click` | `Callable[[], Any]` | *(required)* | Invoked on tap (e.g. to toggle a `Drawer`). |
| `variant` | `Variant` | `GHOST` | The visual treatment (solid/outline/ghost/link). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to paint with. |
| `size` | `ResponsiveSize` | `Size.MD` | The density — a single `Size` or a per-breakpoint map. |
| `glyph` | `str` | `"☰"` | **Deprecated**. Backward-compat fallback; the button always shows the `menu` icon. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the variant. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! warning "`glyph` is legacy — the icon is always `menu`"
    Old versions rendered the `glyph` character. Today `Burger` always lowers to the
    `IconButton` with `Icons.MENU`; a non-default `glyph` is carried only as the
    accessible label. To customise the look, pass `style`.

### `Drawer`

A **controlled** lateral panel: it shows its `children` when `open` is `True`, and
collapses to an empty box when `False`. The `open` flag lives in app state (toggle
it from a `Burger`'s `on_click`). When open, the panel resolves its surface via
`resolve_surface_variant`, mirroring a card:

```python
from tempest_core import Drawer
from tempest_core import Text

panel = Drawer(
    open=app.state.menu_open,  # (1)!
    children=[
        Text(content="Home"),
        Text(content="Settings"),
    ],
    width=260.0,
    variant="elevated",
)
```

1. **App-controlled** state: `Drawer` doesn't hold `open` — you feed it and toggle
   it from the `Burger`.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `open` | `bool` | `False` | Whether the drawer is expanded; `False` collapses to an empty box. |
| `children` | `list[Widget]` | `[]` | The widgets stacked inside the open drawer. |
| `width` | `float` | `260.0` | The panel width in logical px when open. |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family to tint with. |
| `elevation` | `int \| None` | `None` | M3 elevation level (0-5) overriding the default. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the panel surface. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (parity; forwarded). |

!!! note "Lateral panel, not a floating overlay"
    The layout model is flex-only (no stacking/overlay), so an open drawer renders
    as a **lateral panel**, not as a floating overlay with a scrim. True overlay is a
    renderer follow-up.

## Routing (widgets)

These four are **IR widgets**, not components — import them from `tempest_core`
directly. They are the navigation surface *in the tree*: the `NavStack` (owned by
`App`) decides *which* route is on top, and these widgets lower that into a
renderable subtree the reconciler diffs on a route change. The node-type names and
props are **frozen** so both renderers (Qt / Compose) agree by value.

### `Navigator`

A navigation-stack host that renders the top screen. The `view` builds `child` from
`app.nav.top` and wraps it in a `Navigator`; pushing/popping rebuilds with a
different `child`, and `depth` lets the renderer tell a push (deeper) from a pop
(shallower) to pick the slide direction:

```python
from tempest_core import Navigator, Column, Text

nav = Navigator(
    child=Column(children=[Text(content="Top screen")]),
    transition="slide",
    depth=app.nav.depth,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget` | *(required)* | The screen currently on top of the stack. |
| `transition` | `str` | `"slide"` | Animation hint for a screen swap (`"slide"` / `"fade"` / `"none"`). |
| `depth` | `int` | `0` | The current stack depth; the renderer compares it against the previous to pick the direction. |

### `TabView`

A tabbed host: a tab strip plus the active tab's content. The `view` builds `child`
for the active tab; tapping a tab fires `on_change` with a `RouteChangeEvent`
carrying `params["index"]`, so the handler switches the active tab and rebuilds:

```python
from tempest_core import TabView, Column, Text

view = TabView(
    tabs=["Feed", "Search", "Profile"],
    active=app.state.tab,
    child=Column(children=[Text(content="Active tab content")]),
    on_change=lambda e: app.set_state(tab=e.params["index"]),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | *(required)* | The tab labels, in order. |
| `active` | `int` | `0` | The index of the currently selected tab. |
| `child` | `Widget` | *(required)* | The content widget for the active tab. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Handler invoked with a `RouteChangeEvent` on a tap. |

### `TabBar`

A standalone tab strip: one selectable label per tab, no content of its own. Emits
a typed `RouteChangeEvent` on a tap, with the index in `params["index"]`. Use it on
its own to drive navigation, or let `TabView` own one implicitly:

```python
from tempest_core import TabBar

strip = TabBar(
    tabs=["Day", "Week", "Month"],
    active=app.state.range,
    on_change=lambda e: app.set_state(range=e.params["index"]),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `tabs` | `list[str]` | *(required)* | The tab labels, paired by index across Qt/Compose. |
| `active` | `int` | `0` | The index of the currently selected tab. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Optional handler invoked with a `RouteChangeEvent` on a tap. |

!!! tip "`TabBar` is the strip; `TabView` is strip + content"
    If you only need the tabs to drive state (and render the content yourself), use
    `TabBar`. If you want the host to manage the strip **and** the active tab's
    screen together, use `TabView`.

### `RouteDrawer`

A drawer-as-route host: main content with a side panel that slides over it. When
`open` is `True` the renderer slides the `drawer` over the `child`; toggling fires
`on_change`. Modelling the drawer as a widget (rather than a transient overlay)
keeps its open/closed state in the declarative tree, so it survives rebuilds and
diffs like any prop:

```python
from tempest_core import RouteDrawer, Column, Text

host = RouteDrawer(
    child=Column(children=[Text(content="Main content")]),
    drawer=Column(children=[Text(content="Route panel")]),
    open=app.state.drawer_open,
    on_change=lambda e: app.set_state(drawer_open=not app.state.drawer_open),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget` | *(required)* | The main content shown under the drawer. |
| `drawer` | `Widget` | *(required)* | The panel that slides over the content when open. |
| `open` | `bool` | `False` | Whether the drawer panel is currently shown. |
| `on_change` | `RouteChangeHandler \| None` | `None` | Handler invoked with a `RouteChangeEvent` when the drawer toggles. |

!!! note "`Drawer` (component) vs `RouteDrawer` (widget)"
    The **Side menu** `Drawer` is a UI `Component` that lowers to a `Column`;
    `RouteDrawer` is an **IR widget** that coordinates content + panel on a route
    change with the `NavStack`. Pick by layer: page piece vs. routing host.

## Bar fields

### `SearchBar`

A search field: a **controlled** text `Input` with an optional clear button. The
inner `Input` resolves its style via `resolve_field_variant`; the outer pill
carries a surface from `resolve_surface_variant`; and the clear button lowers to an
`IconButton` (curated `Icons.X` glyph, GHOST) — shown only when `on_clear` is set
**and** the field is non-empty:

```python
from tempest_core import SearchBar

search = SearchBar(
    value=app.state.query,  # (1)!
    placeholder="Search products",
    on_change=lambda e: app.set_state(query=e.value),
    on_clear=lambda: app.set_state(query=""),
    field_variant="filled",
    color_scheme="neutral",
)
```

1. `on_change` receives a validated `TextChangeEvent` on each edit; `value` is
   controlled by the app.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The current query text (controlled). |
| `placeholder` | `str` | `"Search"` | The empty-field hint. |
| `on_change` | `Callable[[TextChangeEvent], Any]` | *(required)* | Called with the validated `TextChangeEvent` on each edit. |
| `on_clear` | `Callable[[], Any] \| None` | `None` | Clear-button handler; shows only when set and the field is non-empty. |
| `field_variant` | `FieldVariant` | `FILLED` | The inner input's treatment (outline / filled / flushed). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the focus tint paints with. |
| `size` | `ResponsiveSize` | `Size.MD` | The density — a single `Size` or a per-breakpoint map. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the field and pill. |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. |

!!! tip "The clear button is conditional"
    It only appears when you pass `on_clear` **and** `value` is non-empty — no mute
    X on an already-empty field. Without `on_clear`, the bar is just the input.

### `Stepper`

A numeric stepper: `-` decrement, the current value, `+` increment. It **clamps**
the result to the optional bounds before reporting, so the handler never receives
an out-of-range value:

```python
from tempest_core import Stepper

qty = Stepper(
    value=app.state.qty,
    step=1,
    min_value=0,
    max_value=10,
    on_change=lambda v: app.set_state(qty=v),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `int` | `0` | The current value. |
| `step` | `int` | `1` | The amount added/removed per tap. |
| `min_value` | `int \| None` | `None` | The lower bound, or `None` for unbounded. |
| `max_value` | `int \| None` | `None` | The upper bound, or `None` for unbounded. |
| `on_change` | `Callable[[int], Any]` | *(required)* | Called with the new (clamped) value on a tap. |

!!! note "The clamp happens before `on_change`"
    Tapping `+` past `max_value` (or `-` below `min_value`) reports the bound, not
    the overshoot. With both `None`, the stepper is unbounded. Like every component,
    `value` is controlled — you reflect the reported value into state.

## Recap

- **Two families**: components, which lower to primitives, and routing widgets,
  which host the route stack in the IR — both imported from the root
  (`from tempest_core import ...`).
- **Bars**: `AppBar` / `Footer` / `CollapsingAppBar` resolve their **surface** via
  `resolve_surface_variant`; `Header` reads tokens directly (flat band, no
  `variant`).
- **Tab/rail**: `NavBar` highlights the active with a **pill** (SOLID badge); `Tabs`
  with an **underline** (2px SideBorder); `Breadcrumb` is a token trail with the
  last crumb always presentational. Selection is **app-controlled** via `active` /
  `on_select`.
- **Side menu**: `Burger` lowers to an `IconButton` (`Icons.MENU`, GHOST); `Drawer`
  is a panel **controlled** by `open`, a lateral panel (not an overlay).
- **Routing**: `Navigator` (stack), `TabView` (strip + content), `TabBar` (strip
  only), `RouteDrawer` (content + route panel) — IR nodes with frozen props, driven
  by `RouteChangeEvent`.
- **Bar fields**: `SearchBar` (controlled input + conditional clear) and `Stepper`
  (a counter that clamps before reporting).

All these symbols appear in the [API reference](../reference.md); for the controlled
state model see the [state tutorial](../tutorial/state.en.md) and the
[design system](../tutorial/design-system.en.md).
