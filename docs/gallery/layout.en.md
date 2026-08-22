# Layout & structure

Layout widgets are a screen's **skeleton** in `tempest-core`: they paint no
content of their own, but they **position, stack, clip and protect** their
children. Every one is an immutable IR node (a frozen Pydantic model) the
reconciler diffs and the leaf renderers apply — the flexbox geometry comes from
the node's `Style` (anchored on the **Material 3 / CSS flexbox** box model),
while each widget here only declares *which* container behavior it has. 🚀

!!! info "What you'll learn here"
    - The two **axis containers** (`Column`, `Row`) and how `justify` / `align` /
      `gap` shape the children's distribution.
    - The **single-child** containers (`Container`, `SafeArea`, `AspectRatio`) and
      the **multi-child** ones (`ScrollView`, `Stack`, `Wrap`, `PageView`,
      `KeyboardAvoidingView`).
    - The `Spacer` — the flexible-space primitive — and **how it lowers** to
      `style.grow`.
    - How `Stack` layers children by z-order and how `SafeAreaEdge` selects the
      protected edges.

!!! note "Layout config lives on `style`, not on per-widget props"
    `Column`, `Row`, `Stack` and `Wrap` do **not** have props like `justify` or
    `gap`; those values live on the node's `Style` (inherited from `Widget`). You
    compose the layout like this:

    ```python
    from tempest_core import Row
    from tempest_core.style import AlignItems, JustifyContent, Style

    bar = Row(
        style=Style(
            justify=JustifyContent.SPACE_BETWEEN,  # distribute along the main axis
            align=AlignItems.CENTER,  # center on the cross axis
            gap=8.0,  # space between children
        ),
        children=[],
    )
    ```

    The real flex enum members live in `tempest_core.style` (`FlexDirection`,
    `JustifyContent`, `AlignItems`, `FlexWrap`, `Position`, `StackAlign`) — see the
    [API reference](../reference.md).

!!! tip "Some widgets only live in `tempest_core.widgets`"
    `Column`, `Row`, `Container` and `Spacer` are re-exported at the top level
    (`from tempest_core import Column`). The rest (`ScrollView`, `SafeArea`,
    `SafeAreaEdge`, `Stack`, `Wrap`, `PageView`, `AspectRatio`,
    `KeyboardAvoidingView`) come from `from tempest_core.widgets import ...` — which
    is what the examples below use.

## `Column`

A **vertical flex** container: the main axis runs top-to-bottom. Children are
stacked in the order they appear in `children`.

```python
from tempest_core import Column, Text

column = Column(
    children=[
        Text(content="First row"),
        Text(content="Second row"),
        Text(content="Third row"),
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, stacked top-to-bottom. |

!!! tip "`justify` is the main axis, `align` is the cross axis"
    In a `Column` the main axis is **vertical**: `Style(justify=...)` distributes
    children top-to-bottom (`JustifyContent.SPACE_BETWEEN`, `CENTER`, …) and
    `Style(align=...)` aligns them horizontally (`AlignItems.START`, `CENTER`,
    `STRETCH`, …). You don't need to set `Style(direction=FlexDirection.COLUMN)` —
    a `Column` already *is* the column direction; the `direction` field is for
    advanced generic-container cases.

!!! note "Empty children is a valid state"
    `children` has a `default_factory` of an empty list — a `Column()` with no
    children is a legitimate empty column, not an error. This follows the project's
    collection convention (never raise on an empty collection).

## `Row`

A **horizontal flex** container: the main axis runs left-to-right. It's the
mirror of `Column` on the other axis.

```python
from tempest_core import Button, Row

bar = Row(
    children=[
        Button(label="Save"),
        Button(label="Cancel", variant="outline"),
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, laid out left-to-right. |

!!! tip "Push children to the edges with `Spacer` or `justify`"
    To separate two groups in a `Row`, you can either set
    `Style(justify=JustifyContent.SPACE_BETWEEN)` **or** drop a [`Spacer`](#spacer)
    between them. Both techniques resolve the same layout; `Spacer` shines when you
    want different weights between gaps.

## `Container`

A **single-child box** used for padding, background, borders and sizing. Unlike
`Column`/`Row`, it distributes no axis — it wraps **one** widget (or none) and
applies its `Style` box model.

```python
from tempest_core import Container, Text
from tempest_core.style import Edge, Style

card = Container(
    style=Style(
        padding=Edge.all(16.0),
        background="#FFFFFF",  # a str coerces to Color anywhere a Color is expected
        radius=12.0,
    ),
    child=Text(content="Card content"),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget (optional). |

!!! note "`child` is optional — a childless `Container` is an empty box"
    With `child=None`, the `Container` becomes a purely visual box (a painted
    spacer, a divider, a color block). `child_nodes()` returns `[]` in that case, so
    the reconciler treats it as a leaf.

## `ScrollView`

A **scrollable** container for an overflowing list of children. It scrolls
vertically by default; set `horizontal` to scroll sideways.

```python
from tempest_core import Text
from tempest_core.widgets import ScrollView

feed = ScrollView(children=[Text(content=f"Item {i}") for i in range(200)])

carousel = ScrollView(horizontal=True, children=[])
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `horizontal` | `bool` | `False` | When `True`, children lay out and scroll left-to-right; otherwise they stack and scroll top-to-bottom. |
| `children` | `list[Widget]` | `[]` | The ordered children. |

!!! warning "`ScrollView` mounts every child at once"
    A `ScrollView` builds the whole list in memory — great for dozens of items, bad
    for thousands. For large lists with virtualization (a sliding window), use the
    `LazyColumn` / `LazyRow` / `LazyGrid` widgets (see the
    [API reference](../reference.md)).

## `SafeArea`

A single-child box that **insets its content away from system intrusions** — the
status bar, the navigation bar, or a display cutout/notch. It mirrors React
Native's `SafeAreaView`. On the device renderer the inset is the *real*
`WindowInsets.safeDrawing` reported by the platform; the desktop simulator (no
system bars) stands in with fixed approximate insets.

```python
from tempest_core import Column, Text
from tempest_core.widgets import SafeArea

screen = SafeArea(child=Column(children=[Text(content="Protected content")]))
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget (optional). |
| `edges` | `list[SafeAreaEdge]` | *(all four)* | The edges to inset against. |

### The `SafeAreaEdge` enum

`edges` selects **which** edges get an inset. The default is all four; pass a
subset to leave the others flush against the physical edge.

| Member | Value | What insetting protects |
| --- | --- | --- |
| `SafeAreaEdge.TOP` | `"top"` | Pushes content below the status bar or a top display cutout/notch. |
| `SafeAreaEdge.RIGHT` | `"right"` | Keeps content clear of right-side intrusions (rounded corner, landscape notch). |
| `SafeAreaEdge.BOTTOM` | `"bottom"` | Lifts content above the navigation bar or the home-indicator gesture area. |
| `SafeAreaEdge.LEFT` | `"left"` | Keeps content clear of left-side intrusions (rounded corner, landscape notch). |

```python
from tempest_core import Column, Text
from tempest_core.widgets import SafeArea, SafeAreaEdge

# Protect only the top — the bottom stays flush (e.g. a bar that already hugs it).
screen = SafeArea(
    edges=[SafeAreaEdge.TOP],
    child=Column(children=[Text(content="Content")]),
)
```

!!! tip "Protect only what you need"
    A full-bleed bottom navigation bar usually wants to stay flush with the bottom
    edge, so you pass `edges=[SafeAreaEdge.TOP, SafeAreaEdge.LEFT,
    SafeAreaEdge.RIGHT]` and leave `BOTTOM` out. Protecting an edge that doesn't
    need it creates visible dead space.

## `Spacer`

A **flexible empty box** that consumes the free space along its parent's main
axis. Dropped between two children of a `Row`/`Column`, it expands and pushes the
siblings to the ends. It's an invisible leaf — only its `Style`'s `grow` matters.

```python
from tempest_core import Button, Row, Spacer

# "Back" on the left, "Next" on the right — the Spacer pushes them to the ends.
footer = Row(
    children=[
        Button(label="Back", variant="ghost"),
        Spacer(),
        Button(label="Next"),
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `flex` | `float` | `1.0` | The flex weight the spacer grows by (must be `> 0`); baked into `style.grow`. |

!!! note "How `Spacer` lowers: `flex` becomes `style.grow`"
    At construction a `model_validator(mode="after")` bakes `flex` into
    `style.grow` **when `grow` is unset**. So the `Style` the renderers consume
    always carries a `grow`, and a `Spacer()` stretches even with no explicit
    `style`. An explicit `style.grow` **wins** — so a double-weight spacer is
    `Spacer(style=Style(grow=2.0))` (or `flex` itself). The renderers realize it as
    a stretchable box (Qt `addStretch` / a growing `QWidget`; Compose
    `Modifier.weight`), reusing only the existing `grow` field — no new field.

!!! tip "Asymmetric weights with two `Spacer`s"
    Two spacers with different `flex` split the free space in that ratio:
    `Spacer(flex=1.0)` + `Spacer(flex=2.0)` gives the second twice the gap — handy
    for centering a child off the geometric middle.

## `Stack`

An **overlapping** container: children share one box and are painted in layers by
z-order. Unlike `Column`/`Row` (which lay children out along an axis), a `Stack`
paints its children **on top of one another** in declaration order — the first
child is the bottom layer, the last is on top. It's the framework's overlay
primitive: a scrim, a modal card, a toast or a FAB is just a later child of a
`Stack` wrapping the page content.

```python
from tempest_core import Container, Text
from tempest_core.style import Position, Style
from tempest_core.widgets import Stack

screen = Stack(
    children=[
        Container(child=Text(content="Page content")),  # bottom layer
        Container(  # full-bleed scrim on top
            style=Style(
                position=Position.ABSOLUTE,
                top=0.0,
                right=0.0,
                bottom=0.0,
                left=0.0,
                background="#000000",
                opacity=0.5,
            ),
        ),
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, bottom layer first. |

!!! note "Positioned vs non-positioned children"
    A child **without** a position is aligned within the box by the `Stack`'s
    `Style.stack_align`. A child whose `Style` sets `position = ABSOLUTE` leaves the
    flow and is anchored by its `top`/`right`/`bottom`/`left` insets (like Flutter's
    `Positioned` / CSS `position: absolute`). Setting `left` **and** `right` (or
    `top` and `bottom`) stretches the child across that axis — a full-bleed scrim is
    `ABSOLUTE` with all four insets at `0`.

!!! info "`stack_align` uses the `StackAlign` enum, not `justify`/`align`"
    Alignment of a `Stack`'s non-positioned children is **two-axis** and uses
    `Style(stack_align=...)`. The real members are: `TOP_START`, `TOP_CENTER`,
    `TOP_END`, `CENTER_START`, `CENTER`, `CENTER_END`, `BOTTOM_START`,
    `BOTTOM_CENTER`, `BOTTOM_END` — each crosses a vertical band (top/center/bottom)
    with a horizontal one (start/center/end). Ordinary flex containers keep using
    single-axis `JustifyContent`/`AlignItems`.

## `Wrap`

A **flow-layout** container: children flow left-to-right and break onto the next
line once the current one fills. It's the natural primitive for chips, tags or
any free-flowing set of pills — unlike `Row`, which keeps every child on a single
line.

```python
from tempest_core import Button
from tempest_core.widgets import Wrap

chips = Wrap(
    children=[
        Button(label=tag, variant="outline") for tag in ["Python", "Rust", "Go", "Zig"]
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children, flowed and wrapped in order. |

!!! note "`Wrap` wraps by default — and how it lowers"
    Wrapping is controlled by `Style.flex_wrap`, but a `Wrap` **wraps even with the
    field unset**, since wrapping is the widget's whole purpose. The real `FlexWrap`
    members are `NOWRAP`, `WRAP` and `WRAP_REVERSE` (the last stacks the new lines
    in reverse cross-axis order). The Compose renderer lowers `Wrap` to
    `FlowRow`/`FlowColumn`; Qt realizes the flow imperatively.

## `PageView`

A **paginated horizontal carousel**: one full-width page visible at a time. Each
child is a page; the user swipes (device) or uses prev/next controls (simulator)
to move between them. The active index lives in the **application's own state** —
the app passes the current `page` and updates it from the `on_page_change`
handler.

```python
from tempest_core import Container, Text
from tempest_core.widgets import PageView

onboarding = PageView(
    page=0,
    on_page_change=lambda e: print("new page:", e.page),  # (1)!
    children=[
        Container(child=Text(content="Welcome")),
        Container(child=Text(content="Features")),
        Container(child=Text(content="Ready!")),
    ],
)
```

1. The handler receives a `PageChangeEvent` with the new index in `.page` (see the
   [API reference](../reference.md)).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered pages. |
| `page` | `int` | `0` | The active page index (0-based), driven by the application state. |
| `on_page_change` | `PageChangeHandler \| None` | `None` | Handler invoked with a `PageChangeEvent` when the active page changes. |

!!! warning "Ignore the event whose `page` already matches the state"
    To avoid a feedback loop, the handler should **ignore** a `PageChangeEvent`
    whose `page` already equals the index in state. `PageView` is controlled: the
    source of truth is the app state, not the widget. The Compose renderer lowers it
    to a `HorizontalPager`; Qt uses a `QStackedWidget` with prev/next navigation.

## `AspectRatio`

A single-child box that **constrains its child to a fixed width/height ratio**.
`ratio` is `width / height`: `1.0` is square, `16/9` is widescreen. The renderer
derives the missing dimension from whichever one the parent bounds.

```python
from tempest_core.widgets import AspectRatio, Image

# A video/thumb always 16:9, no matter the available width.
thumb = AspectRatio(ratio=16 / 9, child=Image(src="cover.jpg"))
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `ratio` | `float` | *(required)* | The `width / height` ratio to enforce (must be `> 0`). |
| `child` | `Widget \| None` | `None` | The wrapped widget (optional). |

!!! note "It's the explicit counterpart to `Style.aspect_ratio` — and how it lowers"
    There's also a `Style.aspect_ratio` field; use the **widget** when fixing the
    ratio is the box's only purpose, and the `Style` field when the ratio is just
    one rule among several. The two coexist. The Compose renderer lowers the widget
    to `Modifier.aspectRatio`; Qt derives the fixed dimension imperatively.

## `KeyboardAvoidingView`

A **vertical container that recedes its content when the keyboard appears**. It
wraps its children and, while the on-screen keyboard is open, insets them so the
focused input stays visible above it.

```python
from tempest_core import Button, Column
from tempest_core.widgets import Input, KeyboardAvoidingView

form = KeyboardAvoidingView(
    children=[
        Column(
            children=[
                Input(placeholder="Email"),
                Input(placeholder="Password"),
                Button(label="Sign in"),
            ]
        ),
    ]
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered children the view insets. |

!!! info "No event contract — the inset is 100% the renderer's job"
    `KeyboardAvoidingView` declares **no** events; the keyboard inset is handled by
    the renderer, not surfaced to application handlers. On device, Compose lowers it
    to a `Column` with `Modifier.imePadding()` (driven by `WindowInsets.ime`); the
    Qt simulator listens on
    `QApplication.inputMethod().keyboardRectangleChanged` and adjusts its margins,
    behaving like a plain `Column` on desktop (no virtual keyboard).

## Recap

- **Axis containers**: `Column` (vertical) and `Row` (horizontal) lay children out
  along the main axis; `justify`/`align`/`gap` live on the `Style`.
- **Single child**: `Container` (the box model you define), `SafeArea` (insets the
  system reports, by `SafeAreaEdge`), `AspectRatio` (a fixed `width/height` ratio).
- **Multi child**: `ScrollView` (scrolls, mounts everything), `Stack` (z-order
  overlay + `position`/`stack_align`), `Wrap` (flow-layout that wraps by default),
  `PageView` (a state-controlled carousel), `KeyboardAvoidingView` (recedes under
  the keyboard).
- **`Spacer`** is the invisible leaf that stretches: `flex` lowers to `style.grow`,
  and an explicit `style.grow` wins.
- **Flexbox geometry lives on the `Style`** — widgets only declare *which*
  container behavior they have; the renderers lower each to native primitives
  (Compose `FlowRow`/`HorizontalPager`/`Modifier.*`; Qt imperative).
