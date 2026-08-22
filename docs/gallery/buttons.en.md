# Buttons

Buttons are the most basic tappable affordance in `tempest-core`. There are two:
**`Button`** (with text) and **`IconButton`** (icon-only). Both share the
**Chakra-ergonomics variant API** (`variant` / `size` / `color_scheme`) anchored
on **Material 3** — you describe the *intent* and a **pure resolver** produces the
concrete `Style` from the `Theme` tokens. 🚀

!!! info "What you'll learn here"
    - The four **variants** and which M3 treatment each lowers to.
    - The four **sizes** and why a small button never breaks the touch target.
    - How `color_scheme` picks the color family.
    - How a button **resolves and bakes** its `Style`, and how to read the
      **per-state table**.

## `Button`

A tappable button with a text label. In the minimal case you pass only `label` —
everything else has a sane default (`SOLID` / `MD` / `primary`):

```python
from tempest_core import Button

save = Button(label="Save")
```

That single `Button(label="Save")` is already a **filled, primary, medium-density**
button — ready for the renderers. Pass an `on_click` to react to the tap:

```python
from tempest_core import Button

save = Button(
    label="Save",
    on_click=lambda e: app.set_state(saving=True),  # (1)!
    variant="solid",
    size="md",
    color_scheme="primary",
)
```

1. The handler may be **sync or `async`** — the runtime schedules awaitables on
   the event loop. It receives a `TapEvent` (see [API reference](../reference.md)).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | *(required)* | The text shown on the button. |
| `on_click` | `EventHandler \| None` | `None` | Handler invoked on tap; sync or `async`. Receives `TapEvent`. |
| `variant` | `Variant` | `SOLID` | The visual treatment (solid / outline / ghost / link). |
| `size` | `Size \| dict[str, Size]` | `MD` | The density — a single `Size` or a per-breakpoint map. |
| `color_scheme` | `str` | `"primary"` | The M3 role family (`primary` / `secondary` / `tertiary` / `error` / `neutral`). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the variant. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. **Kept out of the IR.** |

!!! note "`theme` and `media` are build-time inputs, not IR props"
    Both are used **only when resolving** the `Style` and are excluded from the
    node props (`prop_exclude_names`). A full `Theme` per node would bloat the tree
    and the serialized bridge payload — the resolved `style` already carries their
    effect.

### Variants

`variant` picks the emphasis; the H1 resolver (`resolve_variant`) maps it to a
Material 3 treatment. `color_scheme` then decides *which* color family paints that
treatment.

| `Variant` | M3 treatment | Background | Content | Border |
| --- | --- | --- | --- | --- |
| `SOLID` | *filled button* | role color | legible `on_*` | — |
| `OUTLINE` | *outlined button* | transparent | role color | same as role color |
| `GHOST` | *text button* (no underline) | transparent | role color | — |
| `LINK` | inline underlined text | transparent | role color | — |

```python
from tempest_core import Button, Row

bar = Row(
    children=[
        Button(label="Save", variant="solid"),  # highest emphasis
        Button(label="Cancel", variant="outline"),  # medium emphasis
        Button(label="Skip", variant="ghost"),  # low emphasis
        Button(label="Learn more", variant="link"),  # inline
    ]
)
```

!!! tip "Emphasis scale"
    `SOLID` → `OUTLINE` → `GHOST` → `LINK` is a **highest-to-lowest emphasis**
    scale. Reserve `SOLID` for the screen's primary action; use `GHOST` for
    secondary actions that shouldn't compete with it.

### Sizes and the touch target

`size` accepts a single `Size` (`XS` / `SM` / `MD` / `LG`) or a **per-breakpoint
map** for responsive density:

```python
from tempest_core import Button
from tempest_core import Size

# Compact on mobile, roomy from the "md" breakpoint up.
responsive = Button(label="Submit", size={"base": Size.SM, "md": Size.LG})
```

!!! warning "A small button lowers density, never the touch target"
    Every size guarantees `min_height = 48.0` (`MIN_TOUCH_TARGET`, Material's 48dp
    target). Shrinking `size` reduces the visual padding/typography, but the
    tappable area **never** drops below 48dp — motor accessibility is preserved by
    construction.

### How the `Style` is resolved and baked

At construction, `Button` runs a `model_validator(mode="after")` that:

1. captures your explicit `style` as the **override**;
2. resolves the base `Style` from `variant` / `size` / `color_scheme` against the
   `theme` (via `resolve_variant`);
3. **merges the override on top** of the base (the override's set fields win);
4. bakes the result into `.style`, so the renderers consume a plain `Style`,
   unaware any resolution happened.

```python
from tempest_core import Button
from tempest_core import Style

# The override wins on the fields it sets; the rest comes from the resolved variant.
custom = Button(label="Danger", color_scheme="error", style=Style(radius=999.0))
```

!!! info "Override always on top"
    This keeps backward compatibility: `Button(label=...)` with no `style` gives
    the variant button; `Button(label=..., style=…)` hand-styles on top. You never
    lose the variant by setting a single field.

### Per-state table (hover / press / disabled / focus)

`resolve_variant` is pure and lives in the engine — but real buttons have
**interaction states**. The `state_styles()` method returns the resolved `Style`
for each `ComponentState`, with the caller's override merged on top:

```python
from tempest_core import Button
from tempest_core import ComponentState

button = Button(label="Save", color_scheme="primary")
states = button.state_styles()

states[ComponentState.DEFAULT]  # at rest
states[ComponentState.HOVER]  # pointer over (M3 state layer)
states[ComponentState.PRESSED]  # being tapped
states[ComponentState.DISABLED]  # inactive (reduced opacity)
states[ComponentState.FOCUS]  # keyboard/reader focus
```

!!! note "Resolution is pure; only the event→state mapping lives in the renderer"
    The core produces the state **table** deterministically. Applying the Material
    3 *state layer* on the right pointer/focus event is the only part that lives in
    the renderers (Qt / Compose) — keeping the core from ever touching pixels.

## `IconButton`

An **icon-only**, square/circular button. It *is* button-shaped, so it reuses
`resolve_variant` exactly like `Button` — then pins `width`/`height` to the
resolved `min_height` (a square box at least 48dp) and a circular `radius`,
**using only existing `Style` fields** (no new field). It defaults to the `GHOST`
variant (the lowest-emphasis, icon-forward treatment):

```python
from tempest_core import IconButton

close = IconButton(icon="close", label="Close dialog")  # (1)!
settings = IconButton(icon="settings", color_scheme="primary", label="Open settings")
```

1. `icon` is a curated `Icons` value (or its string), or an arbitrary platform
   icon name.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `icon` | `Icons \| str` | *(required)* | The icon — curated `Icons` value or platform name. |
| `on_click` | `EventHandler \| None` | `None` | Handler on tap; sync or `async`. |
| `variant` | `Variant` | `GHOST` | The visual treatment — defaults to `GHOST`. |
| `size` | `Size \| dict[str, Size]` | `MD` | The density. |
| `color_scheme` | `str` | `"primary"` | The M3 role family. |
| `label` | `str` | `""` | The **accessible name** (a11y / `Semantics`) of the text-less button. |
| `theme` | `Theme` | `Theme()` | The theme. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot. **Kept out of the IR.** |

!!! danger "Always pass `label` on an `IconButton`"
    An icon-only button has no visible text, so `label` carries the **accessible
    name** (`contentDescription` / accessible label) that renderers route into the
    node's accessibility surface. Without it, the button is mute to screen readers.
    It isn't optional in practice — it's accessibility.

### Square/circular geometry

`IconButton` pins its geometry via `_squareify`: `width` and `height` take the
resolved `min_height` (≥ 48dp), and `radius` takes half of it (a circle). All with
existing `Style` fields — the touch area never drops below 48dp, just like
`Button`. The per-state table (`state_styles()`) returns each state already pinned
to that geometry.

## Recap

- **Two buttons**, one API: `Button` (text) and `IconButton` (icon) resolve via
  `resolve_variant` from `variant` / `size` / `color_scheme`.
- **Variants**: `SOLID` (filled) → `OUTLINE` (outlined) → `GHOST` (text) →
  `LINK` (inline), highest to lowest emphasis.
- **Sizes**: `XS` / `SM` / `MD` / `LG` or a per-breakpoint map; `min_height`
  guarantees the 48dp touch target at any size.
- **Resolved & baked style**: the caller's override is always merged on top of the
  resolved variant.
- **`state_styles()`** gives the per-`ComponentState` table; only the event→state
  mapping lives in the renderer.
- **`IconButton`** is square/circular, `GHOST` by default, and **requires `label`**
  for accessibility.
