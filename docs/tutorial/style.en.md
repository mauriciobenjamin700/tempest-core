# 2. Styling

Styling is **inline and typed** — no stylesheets, no cascade, no specificity. A
`Style` is a Pydantic object each renderer translates to its target (CSS on the
web, Qt/Compose properties on native).

```python
from tempest_core import Container, Style, Text, Widget
from tempest_core.style import Color, Edge


def card() -> Widget:
    return Container(
        key="card",
        style=Style(
            padding=Edge.all(16),  # (1)!
            gap=8.0,
            background=Color.from_hex("#f5f5f5"),  # (2)!
            radius=12.0,
        ),
        children=[Text(content="In a card", key="t")],
    )
```

1. `Edge.all(16)` = 16px on all four sides. There's also `Edge.symmetric(
   vertical=…, horizontal=…)` and `Edge(top=…, right=…, …)`.
2. `Color.from_hex("#f5f5f5")` → `Color(r, g, b, a)`. On the web it becomes
   `rgba(...)`; the value crosses the boundary as `{r, g, b, a}`.

## Implicit animation

Declare a `Transition` and a property change animates instead of snapping:

```python
from tempest_core.style import Curve, Transition

Style(transition=Transition(duration_ms=300, curve=Curve.EASE_IN_OUT))
```

!!! tip "Theme = Style values"
    There's no magic theme engine: a theme is just a set of `Color`/`Style` your
    `view` applies. Switching themes is the view producing different Styles.

## HTML escape hatch (`tag` / `attrs`)

Every `Widget` carries two optional "renderer hint" fields — `tag` and `attrs` —
for the HTML/SSR renderer (`tempestweb`). They're ignored by the native renderers
(Qt/Compose), just like `semantics`/`focusable` already are.

```python
from tempest_core import Container, Text, Widget


def navbar() -> Widget:
    return Container(
        key="nav",
        tag="nav",  # (1)!
        attrs={"id": "top", "aria-label": "Primary"},  # (2)!
        children=[
            Text(
                content="Home",
                tag="a",
                attrs={"href": "/", "hx-get": "/", "hx-target": "#main"},  # (3)!
            ),
        ],
    )
```

1. `tag` overrides the semantic HTML element emitted (`<nav>` instead of the
   default `<div>`); `None` lets the renderer pick its natural element.
2. `attrs` is a `dict[str, str]` of arbitrary HTML attributes (`id`, `class`,
   `data-*`, `aria-*`).
3. This is how HTMX attributes (`hx-*`) reach the SSR output without a dedicated
   field on the core.

!!! info "Why a typed escape hatch"
    The core is renderer-agnostic; it does not model every HTML tag/attribute.
    `tag`/`attrs` flow through `build()` into the node's `props` (like any other
    field), so the HTML renderer consumes them and the others ignore them — with
    no special-casing.

## Recap

- `Style` is typed and inline; no CSS cascade.
- `Color.from_hex`, `Edge.all/symmetric`, `Transition` cover the basics.
- Each renderer translates the same `Style` to its target.
- See the [API reference](../reference.md) for everything.
