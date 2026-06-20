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

## Recap

- `variant` / `size` / `color_scheme` describe the intent; the pure resolver
  produces the `Style`.
- Surfaces (`Card` / `Surface` / `resolve_surface_variant`) are non-interactive:
  elevation, tonal fill, or border.
- Feedback (`Badge` / `Alert` / `Stat` / `resolve_badge_variant` /
  `resolve_alert_variant`) brings the `success` / `warning` / `info` status
  families — subtle uses the `*_container` pair for AA.
- `HStack` / `VStack` accept a token-step `gap`; `Spacer` is a flex.
- An explicit `style=` is always merged on top.
