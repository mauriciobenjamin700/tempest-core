# 3. Design system (variants → Material 3)

`tempest-core` ships a **design system** with **Chakra-style API ergonomics**
(`variant` / `size` / `color_scheme`) anchored in **Material 3**. Instead of
hand-writing colors and spacing, you describe the *intent* and a **pure resolver**
produces the concrete `Style` from the `Theme` tokens. 🚀

## Buttons, fields, selection, slider

The interactive resolvers live in `variants.py`; each resolves a `Style`:

```python
from tempest_core import IconButton, Theme
from tempest_core.widgets import Input
from tempest_core.style import FieldVariant

field = Input(value="", field_variant=FieldVariant.FILLED, color_scheme="primary")
button = IconButton(icon="settings", color_scheme="primary", label="Open settings")
```

!!! info "States (hover/press/disabled/focus)"
    The interactive resolvers each ship a `*_states` sibling returning the
    per-state table the renderers apply on real pointer/focus events.

## Surfaces and layout (H3)

The **surface** layer is non-interactive, so it has **no state table**: it only
chooses how the box is filled and whether it casts an elevation shadow.

```python
from tempest_core import CardVariant
from tempest_core.components import Card, HStack, Surface, VStack
from tempest_core.widgets import Spacer, Text

card = Card(                                  # (1)!
    variant=CardVariant.OUTLINED,
    color_scheme="primary",                   # (2)!
    children=[
        HStack(gap="md", children=[           # (3)!
            Text(content="Title"),
            Spacer(),                         # (4)!
            Text(content="42"),
        ]),
    ],
)
```

1. `Card` = `Surface` + padding + `Column`. The three variants are `ELEVATED`
   (surface bg + shadow), `FILLED` (tonal fill, no shadow) and `OUTLINED`
   (hairline border, no shadow).
2. `color_scheme="neutral"` uses the surface roles; a role family (`"primary"`, …)
   tints with the tonal `*_container` / `on_*_container` roles.
3. `gap="md"` is a **token step** resolved against the theme's spacing scale; a
   raw `float` is also accepted (backward-compatible).
4. `Spacer()` is a flexible spacer (`grow=1.0`) that pushes its siblings apart.

!!! tip "Elevation is a `Shadow`, not a new field"
    Material 3 elevation is realized as a `Shadow` mapped from the level
    (`elevation=0..5`) — **no new `Style` field** was added. That is why
    `len(Style.model_fields)` stays the same.

## Data display and feedback (H4)

The **feedback** layer adds three Material 3 status color families —
`success` / `warning` / `info` — and two new resolvers: `resolve_badge_variant`
(badge / tag / chip) and `resolve_alert_variant` (alert / banner). Alerts, like
surfaces, are **non-interactive** (no state table).

```python
from tempest_core import Alert, Badge, Stat
from tempest_core.style import AlertVariant, BadgeVariant

ok = Badge(label="LIVE", variant=BadgeVariant.SUBTLE, color_scheme="success")  # (1)!
note = Alert(                                  # (2)!
    title="Saved",
    body="Your changes are live.",
    variant=AlertVariant.LEFT_ACCENT,
    color_scheme="success",
)
metric = Stat(label="Active users", value="1.2k", delta="+12%", delta_up=True)  # (3)!
```

1. Badge: `SOLID` (role + on-role), `SUBTLE` (the `*_container` / `on_*_container`
   pair, AA-safe), or `OUTLINE` (transparent + role border).
2. Alert: `SUBTLE` (default), `SOLID`, `LEFT_ACCENT` / `TOP_ACCENT` (subtle fill +
   a thick directional border in the saturated role; the renderers mirror the
   physical side under RTL).
3. `Stat` tints the delta with the `success` (up) or `error` (down) role.

!!! warning "Contrast: why `SUBTLE` uses the `*_container` pair"
    A saturated status role on white can **fail WCAG-AA** (measured: `success`
    solid = 3.02). The subtle status surfaces therefore use the tonal
    `*_container` / `on_*_container` pair (~13.7 contrast), which clears AA. The
    status families are generated from fixed semantic seeds (green / amber / blue)
    and stay **additive + backward-compatible** — no new `Style` field.

`Alert` / `Stat` / `ProgressStepper` are new components; `Tag` is a static
(non-selectable) `Chip` preset. `Badge` / `Banner` / `Avatar` / `EmptyState` /
`SegmentedControl` / `Rating` / `Chip` are re-themed off the tokens, and the old
call sites keep working (the legacy `tone` maps onto `color_scheme`).

## Navigation (H5)

Bars, panels and tabs are **themed** too — and with no new resolver, enum or
`Style` field: phase H5 is a **skin pass** that reuses the resolvers you already
know. The bars (`AppBar` / `Footer` / `Sidebar` / `Drawer`) use the H3 surface
resolver; the active `NavBar` item is an accent pill (the H4 badge resolver) and
the inactive ones are *ghost* (the H1 variant resolver).

```python
from tempest_core import Tabs
from tempest_core.components import AppBar, NavBar, SearchBar

bar = AppBar(title="Inbox", color_scheme="primary")  # (1)!
search = SearchBar(value="", on_change=lambda e: None, color_scheme="primary")  # (2)!
nav = NavBar(items=["Home", "Search", "You"], active=0, on_select=lambda i: None)  # (3)!
tabs = Tabs(tabs=["Overview", "Activity"], active=0, on_select=lambda i: None)  # (4)!
```

1. `AppBar` / `Footer` / `CollapsingAppBar` resolve the surface (background +
   elevation shadow + tinted container) via `resolve_surface_variant`; the title
   color is the legible surface content. `variant` (`ELEVATED` / `FILLED` /
   `OUTLINED`) and `color_scheme` apply here too.
2. `SearchBar` resolves the inner `Input` with `resolve_field_variant` (a
   focus-led field), the outer pill with `resolve_surface_variant`, and the clear
   button lowers to an `IconButton` (the `x` icon).
3. `NavBar`: the active item is an **accent pill** (`resolve_badge_variant`
   `SOLID`) in the `color_scheme` role; the inactive ones are `resolve_variant`
   `GHOST` (neutral). `on_select` receives the tapped index.
4. `Tabs` (new component): each tab is a `GHOST` text; the active tab takes the
   role color **plus an underline indicator** — a thin bottom `SideBorder` in the
   accent role (existing `Border` / `SideBorder` fields only).

!!! tip "Same ergonomics as buttons"
    Every navigation component accepts `color_scheme` / `size` / `theme` / `media`
    and an explicit `style=` on top — the same API as `Button`. The old call sites
    (`AppBar(title=…)`, `NavBar(items=…, …)`, `Burger(on_click=…)`) keep working
    unchanged: the H5 props are additive.

!!! note "`Burger` is now an `IconButton`"
    `Burger` lowers to an `IconButton` with the `menu` icon (`GHOST`), reusing the
    icon system. The old `glyph` prop stays as a **deprecated** backward-compat
    fallback, but the button always shows the real icon.

## Research components (H6) 🔬

The last layer of the design system is the **research / data-science** kit: the
components an academic researcher uses to show an ONNX /
[`ort-vision-sdk`](https://github.com/mauriciobenjamin700/ort-vision-sdk) result
end to end. Everything lowers to **existing** primitives (composition) or to a
`Canvas` command list (charts / overlays) — **no new `Style` field, no new
resolver and no new draw command**.

### Metric cards and confidence badge

```python
from tempest_core import ConfidenceBadge, MetricCard, StatCard

# Card (H3) + Stat (H4) — label, value and a status-tinted trend (success/error).
accuracy = MetricCard(label="Accuracy", value="92%", delta="+3%", delta_up=True)

# A compact preset (a "filled" surface).
total = StatCard(label="Images", value="1,024")

# Badge (H4) colored by confidence: >=80% = success, >=50% = warning, else error.
conf = ConfidenceBadge(confidence=0.92, label="cat")  # the pill "cat 92%"
```

!!! info "`confidence_scheme`"
    The badge picks its color family with the pure
    `confidence_scheme(conf, *, high=0.8, mid=0.5)` → `"success"` / `"warning"` /
    `"error"`. Use it to color your own confidence affordances too.

### Charts over the `Canvas`

```python
from tempest_core import BarChart, ChartSeries, LineChart

line = LineChart(series=[
    ChartSeries(points=[0.1, 0.4, 0.35, 0.8], label="loss", color_scheme="primary"),
])
bars = BarChart(values=[3.0, 5.0, 2.0], labels=["a", "b", "c"])
```

A series' data is a frozen `ChartSeries` (`points` + `label` + optional
`color_scheme`), not a bare list, so a chart can plot several named series.
`BarChart` also accepts a plain `values: list[float]` for the single-series case.
Each chart emits a **deterministic** `Canvas` command list — the conformance suite
pins the sequence.

!!! note "Draw vocabulary — there is no `DrawLine`"
    A line is `MoveTo` + a run of `LineTo` + one `StrokeCmd`; a bar is `DrawRect` +
    `FillCmd`; y-axis labels are `DrawText` (baseline-anchored, no align field → 
    right-aligned by estimating the text width). No new draw command is introduced.

### Detection overlay

```python
from tempest_core import DetectionBox, DetectionOverlay

overlay = DetectionOverlay(image_src="photo.jpg", boxes=[
    DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="cat", conf=0.93),
])
```

A `DetectionBox` is **normalized `[0, 1]` `xyxy`** — resolution-independent,
multiplied by the canvas size at draw time. The overlay is a `Stack` of an `Image`
(`fit=COVER`) under a `Canvas` that draws each box (`DrawRect` + `StrokeCmd`,
colored by `confidence_scheme(box.conf)`) with a `"{name} {conf:.0%}"` caption. The
engine takes **no** `ort-vision-sdk` dependency — the `Detection` → `DetectionBox`
adapter lives on the tempestroid side.

### Image-picker → result flow

```python
from tempest_core import ResultView

view = ResultView(
    label="Upload a photo",
    on_pick=lambda uri: app.set_state(...),  # run inference
    result=overlay,                          # the widget you built from the result
)
```

### `DataTable` with sort and pagination

`DataTable` gained themed colors and **app-driven** affordances (the component
holds no state — it mirrors the E1 list pattern): the app holds `sort_column` /
`sort_ascending` / `page` and passes the rows already sorted.

```python
from tempest_core.components import DataTable

table = DataTable(
    columns=["Class", "Confidence"],
    rows=sorted_rows,                 # the app sorts
    sort_column=1, sort_ascending=False, on_sort=lambda col: app.sort(col),
    page=0, page_size=10, on_page=lambda p: app.go_to(p),
)
```

The active column shows the ▲/▼ arrow; with `on_sort` the header cells become
buttons; with `page_size` the table projects the current page slice and renders a
prev/next pager. `Calendar` / `Clock` also migrated to the theme tokens (the
default look shifts from the legacy dark palette to M3 light).

## Recap

- `variant` / `size` / `color_scheme` describe the intent; the pure resolver
  produces the `Style`.
- Surfaces (`Card` / `Surface` / `resolve_surface_variant`) are non-interactive:
  elevation, tonal fill, or border.
- Feedback (`Badge` / `Alert` / `Stat` / `resolve_badge_variant` /
  `resolve_alert_variant`) brings the `success` / `warning` / `info` status
  families — subtle uses the `*_container` pair for AA.
- Navigation (`AppBar` / `NavBar` / `Tabs` / `SearchBar`) is a skin pass: bars via
  the surface resolver, active item via the accent pill, tabs with an underline —
  no new resolver/enum/field.
- Research (`MetricCard` / `StatCard` / `ConfidenceBadge` / `LineChart` /
  `BarChart` / `DetectionOverlay` / `ResultView`) composes primitives and draws
  charts/overlays via a `Canvas` command list — deterministic, no new draw command;
  `confidence_scheme` maps confidence → status; `DataTable` gains app-driven
  sort/pagination.
- `HStack` / `VStack` accept a token-step `gap`; `Spacer` is a flex.
- An explicit `style=` is always merged on top.
