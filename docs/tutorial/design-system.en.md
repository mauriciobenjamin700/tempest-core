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

## Recap

- `variant` / `size` / `color_scheme` describe the intent; the pure resolver
  produces the `Style`.
- Surfaces (`Card` / `Surface` / `resolve_surface_variant`) are non-interactive:
  elevation, tonal fill, or border.
- `HStack` / `VStack` accept a token-step `gap`; `Spacer` is a flex.
- An explicit `style=` is always merged on top.
