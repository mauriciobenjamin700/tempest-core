# Text

Text is the **atom** of a UI: almost every screen has a label, a heading or a
paragraph. `tempest-core` has **one** primitive for it — **`Text`** — and it is
deliberately minimal: it carries only `content` (the string) and delegates **all**
appearance (typography, color, alignment, overflow) to the `Style` object. No
typography prop lives on the widget; they all live on `style`, exactly the way
text inherits `font-*` from a selector in CSS. 🚀

!!! info "What you'll learn here"
    - Why `Text` has only `content` and where **all** the typography lives.
    - How to style weight, size, color, italics and decoration via `Style`.
    - How to align (`text_align`) and how to control **multiline text**.
    - How to clip with `max_lines` and terminate with an **ellipsis** (`…`) or a
      hard cut.
    - How `Text` **lowers into the IR** — which props become `Node.props` and which
      don't.

## `Text`

A run of text. In the minimal case you pass only `content` — with no style, the
renderer applies its own font and color defaults:

```python
from tempest_core import Text

heading = Text(content="Hello, world")
```

That `Text(content="Hello, world")` is already a valid node, ready for the
renderers. To give it appearance, pass a `Style` — the same typed object every
widget accepts:

```python
from tempest_core import Text
from tempest_core import Style, FontWeight, Color

heading = Text(
    content="Welcome",
    style=Style(
        font_size=24.0,
        font_weight=FontWeight.BOLD,  # (1)!
        color=Color.from_hex("#1D1B20"),
    ),
)
```

1. `FontWeight` is an `IntEnum` on the CSS/OpenType scale: `THIN=100`, `LIGHT=300`,
   `NORMAL=400`, `MEDIUM=500`, `SEMIBOLD=600`, `BOLD=700`, `BLACK=900`.

### Props

`Text` **only** adds `content`. Everything else is inherited from the base
`Widget` — and the entire typography lives on `style`, not as loose props:

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `content` | `str` | *(required)* | The string to display. |
| `style` | `Style \| None` | `None` | Inline style — typography, color, alignment, overflow. See the table below. |
| `semantics` | `Semantics \| None` | `None` | Accessibility metadata (`label` / `role` / `hint`) routed to the a11y surface. |
| `focusable` | `bool \| None` | `None` | Whether the node accepts focus; `None` keeps the natural behavior (a label is not focusable). |
| `focus_order` | `int \| None` | `None` | Explicit focus/tab order; `None` uses the natural traversal order. |
| `tag` | `str \| None` | `None` | Semantic HTML tag override (e.g. `"h1"`) honored by the HTML/SSR renderer; ignored by non-web ones. |
| `attrs` | `dict[str, str]` | `{}` | Arbitrary HTML attributes (`id`, `class`, `data-*`, `aria-*`) honored in SSR; ignored by non-web ones. |
| `key` | `str \| None` | `None` | Stable identity the reconciler uses to match nodes across rebuilds. **Becomes `Node.key`, not a prop.** |

!!! note "`content` is required; everything else has a default"
    Only `content` has no default — the other inherited fields are `None`/`{}`, and
    `None` in a `Style` means **"unset"**, letting the renderer fall back to its own
    default. You never need to fill everything in: setting only what changes is the
    idiomatic path.

### Typography via `style`

Since `Text` has no font props of its own, you shape the appearance through the
typography fields of `Style`. They are all optional (`None` = inherit the
renderer's default):

| `Style` field | Type | Default | What it does |
| --- | --- | --- | --- |
| `color` | `Color \| None` | `None` | The text color. |
| `font_size` | `float \| None` | `None` | Font size in logical pixels. |
| `font_weight` | `FontWeight \| None` | `None` | Weight: `THIN` (100) … `BLACK` (900). |
| `font_style` | `FontStyle \| None` | `None` | Slant: `NORMAL` (roman) or `ITALIC`. |
| `font_family` | `str \| None` | `None` | Font family name. |
| `font_asset` | `str \| None` | `None` | Path to a custom font in the bundle (e.g. `"fonts/Roboto.ttf"`). |
| `text_align` | `TextAlign \| None` | `None` | Horizontal alignment: `LEFT` / `CENTER` / `RIGHT` / `JUSTIFY`. |
| `text_decoration` | `TextDecoration \| None` | `None` | Decorative line: `NONE` / `UNDERLINE` / `LINE_THROUGH`. |
| `letter_spacing` | `float \| None` | `None` | Extra spacing between letters, in logical pixels. |
| `line_height` | `float \| None` | `None` | Line height (leading). |
| `max_lines` | `int \| None` (`> 0`) | `None` | Maximum lines before the text is clipped. |
| `text_overflow` | `TextOverflow \| None` | `None` | How clipped text terminates: `CLIP` or `ELLIPSIS`. |
| `text_scale` | `float \| None` (`> 0`) | `None` | Multiplier applied to `font_size` (`1.0` is neutral). |

```python
from tempest_core import Text
from tempest_core import (
    Style,
    FontWeight,
    FontStyle,
    TextDecoration,
    Color,
)

# A highlighted price: large, semibold, colored.
price = Text(
    content="$49.90",
    style=Style(
        font_size=28.0, font_weight=FontWeight.SEMIBOLD, color=Color.from_hex("#006C4C")
    ),
)

# A note in italics, struck through (old price).
old = Text(
    content="$79.90",
    style=Style(
        font_style=FontStyle.ITALIC, text_decoration=TextDecoration.LINE_THROUGH
    ),
)
```

!!! tip "`text_scale` respects the system's accessibility setting"
    `text_scale` is a multiplier over `font_size` (`1.0` = neutral). On Qt the
    translator scales the emitted `font-size`; on Compose it becomes `textScale` for
    the device's `LocalDensity` to apply — i.e. the text follows the system's "font
    size" setting instead of ignoring it. Prefer adjusting the *scale* over pinning
    absolute sizes when the goal is to honor the user's preference.

### Alignment

`text_align` controls horizontal alignment **within the text box** — to see an
effect the box must be wider than the line (give it width via `style.width` or let
the `Text` sit in a container that stretches it):

```python
from tempest_core import Text
from tempest_core import Style, TextAlign

centered = Text(
    content="Tap to continue",
    style=Style(width=320.0, text_align=TextAlign.CENTER),
)
```

!!! note "`JUSTIFY` stretches spacing, not the last line"
    `TextAlign.JUSTIFY` distributes the space between words so each line is flush on
    both edges — **except the last**, which stays start-aligned. It's the classic
    justified-text behavior; use it with a roomy `line_height` to avoid opening
    "rivers" of space in narrow columns.

### Multiline text, `max_lines` and overflow

A `content` with `\n` — or simply too long for the box width — becomes **multiple
lines**. To cap the height, use `max_lines`; to decide how clipped text
terminates, use `text_overflow`:

```python
from tempest_core import Text
from tempest_core import Style, TextOverflow

# A two-line preview with an ellipsis at the end.
preview = Text(
    content=(
        "This is a long description that does not fit entirely inside the card "
        "and needs to be truncated elegantly at the end of the second line."
    ),
    style=Style(width=280.0, max_lines=2, text_overflow=TextOverflow.ELLIPSIS),
)
```

!!! warning "`text_overflow` only acts once the text overflows its space"
    `TextOverflow` (`CLIP` / `ELLIPSIS`) only kicks in when the text **exceeds** the
    available space — typically once it passes `max_lines`. With no line limit (or
    width/height cap) there is no overflow, so nothing is clipped and
    `text_overflow` stays inert. Combine `max_lines` **with** `text_overflow` for
    the truncated preview; `CLIP` cuts sharply at the edge, `ELLIPSIS` appends `…`
    to signal that content was cut.

!!! tip "Single line? `max_lines=1` + `ELLIPSIS`"
    For a one-line label that never wraps (names, card titles), use
    `Style(max_lines=1, text_overflow=TextOverflow.ELLIPSIS)`. It's the equivalent
    of the CSS idiom `white-space: nowrap; overflow: hidden; text-overflow: ellipsis`.

### Accessibility

A visible `Text` is already read by screen readers from its `content`. Use
`semantics` when the text needs a **role** (e.g. a heading) or an accessible label
different from the visible one:

```python
from tempest_core import Text
from tempest_core import Semantics
from tempest_core import Style, FontWeight

heading = Text(
    content="Settings",
    style=Style(font_size=22.0, font_weight=FontWeight.BOLD),
    semantics=Semantics(role="heading"),  # (1)!
)
```

1. `Semantics` carries `label` / `role` / `hint`. The renderers map it to the
   native surface (Qt `QAccessible`; Compose `Modifier.semantics`), so TalkBack and
   readers announce "heading" instead of just the text.

!!! note "Visual size is not semantic hierarchy"
    Making a `Text` large and bold makes it *look* like a title, but it does not
    *announce* it as one to accessibility. Pass
    `semantics=Semantics(role="heading")` (or `tag="h1"` in SSR) so the hierarchy is
    real, not just visual.

### How `Text` lowers into the IR

At build time the reconciler **normalizes** each widget into a uniform `Node`: a
`type` (the class name), a `key` and a **flat** map of `props` (plus children,
which `Text` has none of). The `key` is pulled out of the props and becomes
`Node.key`; everything else on the widget becomes a prop:

```python
from tempest_core import Text, build
from tempest_core import Style, FontWeight

node = build(
    Text(content="Hi", key="greeting", style=Style(font_weight=FontWeight.BOLD))
)

node.type  # "Text"
node.key  # "greeting"  — the key leaves the props and becomes node identity
node.props  # {"content": "Hi", "style": Style(font_weight=BOLD, ...), "semantics": None, ...}
node.children  # []  — Text is a leaf node
```

!!! info "The `style` goes in baked; `Text` resolves no variant"
    Unlike `Button`, `Text` runs **no** variant resolver — it has no
    `variant`/`size`/`color_scheme`. The `Style` you pass enters the IR exactly as
    written (no theme resolution in between), so `Text` is the most direct
    primitive: what you write in `style` is what the renderer consumes. See the full
    `Node` in the [API reference](../reference.md).

## Recap

- **One primitive, one field:** `Text` only adds `content`; all typography lives on
  `style`, the way text inherits `font-*` in CSS.
- **Typography via `Style`:** `font_size`, `font_weight` (`THIN`…`BLACK`),
  `font_style`, `color`, `letter_spacing`, `line_height`, `font_family`/`font_asset`
  and `text_scale` — all optional (`None` = renderer default).
- **Alignment:** `text_align` (`LEFT`/`CENTER`/`RIGHT`/`JUSTIFY`) acts inside the
  box; `JUSTIFY` does not stretch the last line.
- **Multiline and overflow:** `\n` or long text wraps onto several lines;
  `max_lines` + `text_overflow` (`CLIP`/`ELLIPSIS`) build the truncated preview.
- **Accessibility:** `content` is already read; use `semantics` (or `tag` in SSR)
  for a semantic role — visual size is not hierarchy.
- **In the IR:** `Text` becomes a leaf `Node`; `key` becomes `Node.key`, the rest
  becomes `props`, and the `style` goes in baked, with no variant resolution.
