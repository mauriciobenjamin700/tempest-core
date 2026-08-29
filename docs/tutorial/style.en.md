# 2. Styling

Styling is **inline and typed** — no stylesheets, no cascade, no specificity. A
`Style` is a Pydantic object each renderer translates to its target (CSS on the
web, Qt/Compose properties on native).

```python
from tempest_core import Container, Style, Text, Widget
from tempest_core import Color, Edge


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

## Every number is finite

A numeric field on `Style` — and on any widget — refuses `nan`, `inf` and
`-inf`:

```python
from tempest_core import Style

Style(width=float("nan"))
# ValidationError: width — Input should be a finite number
```

That looks harsh for a value nobody types on purpose. But nobody types it: it
**arrives**, from outside data.

```python
metrics = await backend.get("/metrics")  # {"load_pct": "NaN"}
Style(width=float(metrics["load_pct"]))  # float("NaN") == nan
```

A division by zero, a sensor with no reading, a field the backend serialized as
the string `"NaN"` — and the `nan` enters the tree with no signal at all.

!!! danger "Why this cannot be allowed through"
    `nan` and `inf` have **no token in JSON**, and every renderer this core feeds
    is reached through JSON. Python's encoder writes the bare words
    `NaN`/`Infinity`, and no browser's `JSON.parse` accepts them.

    The damage is not the wrong property: it is the **whole batch** carrying it.
    One `nan` in a `width` takes down the patch batch it travelled with —
    including changes to widgets that have nothing to do with it.

    This was measured in tempestweb issue #160: a metric that arrived as `"NaN"`
    killed the batch inside the client's decode — before the transport, before
    the renderer, before any diagnostic — and the visible error showed up **one
    rebuild later** as `patch path out of range`, on an app bar whose second
    action had simply never been delivered. Three of seven reproductions logged
    **nothing** at all.

!!! tip "A bound is not a finiteness check"
    `Style.opacity` (`ge=0.0, le=1.0`) already refused `inf` — but only because
    `inf <= 1.0` is false. A one-sided bound does not hold: `text_scale` and
    `aspect_ratio` carry `gt=0.0`, and `inf > 0.0` is true. That is why the guard
    checks **finiteness**, not range.

Refusing at construction is the point: the `ValidationError` names the field on
the line that built the widget. Validate where the number enters:

```python
import math

from tempest_core import Style


def bar_width(raw: str) -> Style:
    """Convert the backend's number, falling back to 0 when it is not finite."""
    load = float(raw)
    return Style(width=load if math.isfinite(load) else 0.0)


print(bar_width("42.5").width)  # 42.5
print(bar_width("NaN").width)  # 0.0
```

## Implicit animation

Declare a `Transition` and a property change animates instead of snapping:

```python
from tempest_core import Curve, Transition

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
- Every number is finite: `nan`/`inf` are refused at construction, because
  JSON cannot represent them and one alone takes down a whole patch batch.
- See the [API reference](../reference.md) for everything.
