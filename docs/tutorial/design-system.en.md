# 4. Design system (variants → Material 3)

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
- `HStack` / `VStack` accept a token-step `gap`; `Spacer` is a flex.
- An explicit `style=` is always merged on top.
