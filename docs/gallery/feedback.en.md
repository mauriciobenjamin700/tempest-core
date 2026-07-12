# Feedback

The **Feedback** layer (Trilho H4) is the set of *inline* status surfaces — no
overlays (snackbar, toast, dialog): those need a stacking layer and are out of
scope here. Six components: **`Alert`** and **`Banner`** (status blocks),
**`Badge`** (compact pill), **`EmptyState`** (empty-screen placeholder), **`Stat`**
(metric with a trend) and **`ProgressStepper`** (numbered steps of a flow). They
all speak the same **Chakra-ergonomics variant API** (`variant` / `color_scheme`)
anchored on **Material 3**: you describe the *status intent* and a **pure
resolver** produces the concrete `Style` from the `Theme` tokens. 🚦

!!! info "What you'll learn here"
    - The **status families** `success` / `warning` / `info` (plus `error` /
      `neutral` / `primary`…) and how `color_scheme` picks which one paints.
    - The **`Badge` variants** (`resolve_badge_variant`) and the `Alert`/`Banner`
      variants (`resolve_alert_variant`), and which M3 treatment each lowers to.
    - Why the `SUBTLE` default uses the tonal `*_container` / `on_*_container` pair
      — and how that keeps the **WCAG-AA contrast** a saturated role on white
      would break.
    - The legacy `tone` → `color_scheme` mapping, kept backward-compatible.
    - How `Stat` tints its delta with `success` (up) or `error` (down), and how
      `ProgressStepper` colors done/active vs. pending steps.

## `Badge`

A small inline **status pill** — a count (`"3"`) or a short label (`"NEW"`). In
the minimal case you pass only `label`; everything else has a sane default
(`SOLID` / `SM` / derived from `tone`, which starts at `"error"`):

```python
from tempest_core import Badge

unread = Badge(label="3")
```

Pass `color_scheme` and `variant` for the full H4 API:

```python
from tempest_core import Badge, BadgeVariant

new = Badge(label="NEW", color_scheme="success", variant=BadgeVariant.SUBTLE)  # (1)!
```

1. `variant` accepts the `BadgeVariant` enum or its string (`"subtle"`) — both
   resolve identically through `resolve_badge_variant`.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The pill text (a count like `"3"` or `"NEW"`). |
| `tone` | `str` | `"error"` | The **legacy tone**, mapped onto `color_scheme` when the latter is `None`. |
| `color_scheme` | `str \| None` | `None` | The M3 status family; derived from `tone` when `None`. |
| `variant` | `BadgeVariant` | `SOLID` | The pill treatment (solid / subtle / outline). |
| `size` | `ResponsiveSize` | `SM` | The density — a single `Size` or a per-breakpoint map. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the treatment. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot for a responsive `size`. **Kept out of the IR.** |

### `Badge` variants

`variant` picks the emphasis; `resolve_badge_variant` lowers it to a Material 3
treatment, and `color_scheme` decides *which* color family paints it:

| `BadgeVariant` | M3 treatment | Background | Content | Border |
| --- | --- | --- | --- | --- |
| `SOLID` | filled pill | role color | legible `on_*` | — |
| `SUBTLE` | low-emphasis tonal | `*_container` | `on_*_container` | — |
| `OUTLINE` | transparent outline | transparent | role color | same as role color |

!!! warning "Why `SUBTLE` doesn't use the saturated role directly: WCAG-AA contrast"
    A saturated status role on white can **fail WCAG-AA** — the engine verifies
    that solid `success` yields ≈ **3.02** contrast (below the 4.5 minimum for
    text). That's why the `SUBTLE` treatment (the default for `Alert` and `Banner`)
    uses the **tonal pair** `*_container` / `on_*_container` (≈ **13.7** contrast),
    which clears AA **by construction** in the M3 tonal palette. In other words: a
    legible low-emphasis `success` isn't the strong green with text on top — it's
    the light-green *container* with the dark *on-container* content.

## `Alert`

A block-level **status callout**: optional glyph, title (bold), optional body and
an optional dismiss widget. It's the richer sibling of `Banner`, and lowers
through the same `resolve_alert_variant`. It defaults to `SUBTLE` in the `"info"`
family:

```python
from tempest_core import Alert

done = Alert(
    title="Backup complete",
    body="Your data was saved successfully.",
    color_scheme="success",
    glyph="✅",
)
```

Use `variant=LEFT_ACCENT` for the classic accented-edge callout, and pass a
`dismiss` for the close button:

```python
from tempest_core import Alert, AlertVariant, IconButton

failure = Alert(
    title="Upload failed",
    body="Check your connection and try again.",
    color_scheme="error",
    variant=AlertVariant.LEFT_ACCENT,
    dismiss=IconButton(icon="close", label="Dismiss alert"),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The alert's headline (bold). |
| `body` | `str \| None` | `None` | An optional secondary line of detail. |
| `glyph` | `str \| None` | `None` | An optional leading text glyph (no icon font). |
| `color_scheme` | `str` | `"info"` | The M3 status family to tint with. |
| `variant` | `AlertVariant` | `SUBTLE` | The treatment (subtle / solid / left_accent / top_accent). |
| `dismiss` | `Widget \| None` | `None` | Optional trailing dismiss widget (e.g. a close `IconButton`). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the treatment. **Kept out of the IR.** |

### `Alert` (and `Banner`) variants

`resolve_alert_variant` lowers `variant` to an M3 block treatment. An alert is
**non-interactive** (no state layer, like a surface) — there is no per-state
table:

| `AlertVariant` | M3 treatment | Background | Content | Accent |
| --- | --- | --- | --- | --- |
| `SUBTLE` | low-emphasis tonal (default) | `*_container` | `on_*_container` | — |
| `SOLID` | high-emphasis filled | role color | legible `on_*` | — |
| `LEFT_ACCENT` | subtle fill + directional rule | `*_container` | `on_*_container` | 4px border on the leading edge, role color |
| `TOP_ACCENT` | subtle fill + directional rule | `*_container` | `on_*_container` | 4px border on the top edge, role color |

!!! note "Accent borders mirror under RTL"
    `LEFT_ACCENT` draws the rule on the **leading** edge (left in LTR); the
    renderers mirror the physical left/right side under RTL via the same `rtl` flag
    they already use for the `flushed` field's bottom border. You describe *start*,
    not *left*.

## `Banner`

An inline **status bar** with a growing message and an optional trailing action —
leaner than `Alert`, no separate title/body. It lowers through the same
`resolve_alert_variant`, so `variant` and `color_scheme` work identically:

```python
from tempest_core import Banner, Button

maintenance = Banner(
    message="Scheduled maintenance at 2 AM.",
    color_scheme="warning",
    action=Button(label="Details", variant="ghost"),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `message` | `str` | `""` | The banner text. |
| `tone` | `str` | `"info"` | The **legacy tone**, mapped onto `color_scheme` when the latter is `None`. |
| `color_scheme` | `str \| None` | `None` | The M3 status family; derived from `tone` when `None`. |
| `variant` | `AlertVariant` | `SUBTLE` | The treatment (subtle / solid / left_accent / top_accent). |
| `action` | `Widget \| None` | `None` | Optional trailing widget (e.g. a dismiss `Button`). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the treatment. **Kept out of the IR.** |

!!! tip "The `tone` → `color_scheme` pair is the backward-compat path"
    `Banner` and `Badge` were born with a `tone` prop (`"info"` / `"success"` /
    `"warning"` / `"error"`). With H4 that prop became a **legacy shortcut**: when
    `color_scheme` is `None`, it is derived from `tone` (`_tone_scheme`, falling
    back to `"info"`). So `Banner(tone="success")` keeps working untouched; for the
    full family (e.g. `"primary"`, `"neutral"`, `"tertiary"`) pass `color_scheme`
    directly — it **wins** over `tone`.

## `EmptyState`

A **centered placeholder** for empty screens: a large glyph, a title, an optional
subtitle and an optional action. No status families here — it reads the theme's
neutral tones (`ON_SURFACE` on the title, muted `ON_SURFACE_VARIANT` on the glyph
and subtitle) and the theme's spacing scale:

```python
from tempest_core import EmptyState, Button

empty = EmptyState(
    title="No orders yet",
    subtitle="When you place an order, it shows up here.",
    glyph="📦",
    action=Button(label="Browse catalog"),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | `""` | The primary message. |
| `subtitle` | `str \| None` | `None` | An optional secondary line. |
| `glyph` | `str` | `"○"` | A large text glyph shown above the title (no icon font). |
| `action` | `Widget \| None` | `None` | An optional call-to-action widget (e.g. a `Button`). |
| `theme` | `Theme` | `Theme()` | The theme supplying colors and spacing. **Kept out of the IR.** |

!!! note "No `*NotFoundError` in the UI — empty is a valid state"
    `EmptyState` exists precisely to treat "the query returned nothing" as a
    **successful outcome**, not an error. Render it when a collection comes back
    empty, instead of showing an error screen.

## `Stat`

A **labelled metric**: a muted label over a large value, with an optional `delta`
trend line. The delta is tinted by the **`success`** (up) or **`error`** (down)
status family depending on `delta_up`, with the canonical "▲" / "▼" arrow:

```python
from tempest_core import Stat

revenue = Stat(label="Revenue", value="$128k", delta="+12%", delta_up=True)
churn = Stat(label="Churn", value="4.1%", delta="-0.3%", delta_up=False)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The metric's caption (muted). |
| `value` | `str` | `""` | The metric's value (large, prominent). |
| `delta` | `str \| None` | `None` | An optional trend line (e.g. `"+12%"`); `None` hides it. |
| `delta_up` | `bool` | `True` | Whether the delta is positive (tints `success`) or negative (tints `error`). |
| `theme` | `Theme` | `Theme()` | The theme supplying colors and spacing. **Kept out of the IR.** |

!!! warning "`delta_up` is semantic, not cosmetic"
    `delta_up` says whether the trend is **positive or negative** — and that's what
    picks the color (`success` vs. `error`) and the arrow (▲ vs. ▼). On a metric
    where "lower is better" (churn, latency, cost), a **drop** is positive: pass
    `delta_up=True` even with a text delta of `"-0.3%"`, so it shows in green. The
    color follows the metric's *meaning*, not the number's sign.

## `ProgressStepper`

A horizontal wizard/flow **stepper**: each step is a numbered circle (a filled
accent disc for done/active, a muted outline for pending) above its label, joined
by connector rules. Steps up to `current` (inclusive) read the `color_scheme`;
pending ones read the muted `ON_SURFACE_VARIANT`:

```python
from tempest_core import ProgressStepper

flow = ProgressStepper(
    steps=["Cart", "Shipping", "Payment", "Review"],
    current=1,  # (1)!
    color_scheme="primary",
)
```

1. `current=1` marks the step at index 1 ("Shipping") as active; earlier steps
   ("Cart") count as done, later ones as pending.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `steps` | `list[str]` | `[]` | The step labels, in order. |
| `current` | `int` | `0` | The index of the active step (earlier steps count as done). |
| `color_scheme` | `str` | `"primary"` | The M3 role family the done/active steps paint with. |
| `theme` | `Theme` | `Theme()` | The theme resolving the step colors and spacing. **Kept out of the IR.** |

!!! note "Why `ProgressStepper` and not `Stepper`"
    The name avoids colliding with the numeric `Stepper` (the +/− spinner in the
    fields layer). One is a multi-step **progress** indicator; the other is a
    number **input**. Distinct names, distinct roles.

## Recap

- **Six inline surfaces**: `Alert` / `Banner` (blocks), `Badge` (pill),
  `EmptyState` (empty screen), `Stat` (metric) and `ProgressStepper` (steps) — no
  overlays (toast/dialog) live here.
- **Status families**: `success` / `warning` / `info` (plus `error` / `neutral` /
  `primary` / …) via `color_scheme`; `Badge` resolves through
  `resolve_badge_variant`, `Alert`/`Banner` through `resolve_alert_variant`.
- **Variants**: `Badge` → `SOLID` / `SUBTLE` / `OUTLINE`; `Alert`/`Banner` →
  `SUBTLE` / `SOLID` / `LEFT_ACCENT` / `TOP_ACCENT`.
- **WCAG-AA contrast**: `SUBTLE` uses the tonal `*_container` / `on_*_container`
  pair (≈ 13.7) because the saturated role on white can fail AA (solid `success`
  ≈ 3.02).
- **`tone` → `color_scheme`**: a backward-compatible legacy prop; an explicit
  `color_scheme` wins over `tone`.
- **`Stat`** tints the delta with `success` (up) or `error` (down) via `delta_up`,
  following the metric's *meaning*.
- **`ProgressStepper`** colors done/active with the `color_scheme` and leaves
  pending steps muted; distinct from the numeric `Stepper`.
