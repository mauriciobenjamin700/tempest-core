# Research

The **research / data-science** kit is the layer an academic researcher reaches
for to show an ONNX /
[`ort-vision-sdk`](https://github.com/mauriciobenjamin700/ort-vision-sdk) result
end to end: dashboard metric cards, simple charts (line / bar), detection boxes on
top of an image, and the *pick an image → show the result* flow. Everything here
**lowers to primitives that already exist** (composition) or to a **`Canvas`
command list** (charts / overlays) — no new `Style` field, no new resolver, and
**no new draw command** is introduced. 🔬

!!! info "What you'll learn here"
    - How `MetricCard` / `StatCard` compose the **`Card` (H3) + `Stat` (H4)**
      without inventing a primitive.
    - How the pure `confidence_scheme` function maps confidence → status and feeds
      both `ConfidenceBadge` and `DetectionOverlay`.
    - How `LineChart` / `BarChart` emit a **deterministic command list** over the
      `Canvas` using only the existing draw vocabulary.
    - Why a `DetectionBox` is **normalized `xyxy` in `[0, 1]`** and how it becomes
      boxes over an `Image`.
    - How `ResultView` arranges the picker → result flow while holding no state.

## Metric cards

The top block of a dashboard: a big number with a label and a trend. Nothing here
is a new primitive — the cards **compose** `Card` and `Stat`, and the confidence
badge composes `Badge`. The status color comes entirely from one pure function,
`confidence_scheme`.

### `MetricCard`

A dashboard metric inside a themed card: label, value and an optional tinted trend
(`success` when up, `error` when down). In the minimal case you pass only `label`
and `value`:

```python
from tempest_core import MetricCard

accuracy = MetricCard(label="Accuracy", value="92%", delta="+3%", delta_up=True)
```

Need a tiny chart next to the number? The `trailing` slot accepts any widget — for
example a `LineChart` acting as a sparkline:

```python
from tempest_core import ChartSeries, LineChart, MetricCard

spark = LineChart(
    series=[ChartSeries(points=[0.80, 0.86, 0.89, 0.92])],
    width=96.0,
    height=40.0,
)
accuracy = MetricCard(
    label="Accuracy",
    value="92%",
    delta="+3%",
    delta_up=True,
    color_scheme="success",
    trailing=spark,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | `""` | The metric's caption (shown muted). |
| `value` | `str` | `""` | The metric's value (large and prominent). |
| `delta` | `str \| None` | `None` | The trend line (e.g. `"+12%"`); `None` hides it. |
| `delta_up` | `bool` | `True` | Whether the delta is positive (`success`-tinted) or negative (`error`). |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the card surface tints with. |
| `variant` | `CardVariant` | `ELEVATED` | The surface treatment (elevated / filled / outlined). |
| `trailing` | `Widget \| None` | `None` | An optional widget to the right of the stat block (sparkline, icon…). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the surface and stat. **Kept out of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Viewport snapshot (accepted for parity; **unused** here). |

!!! note "It's `Card` + `Stat`, not a new primitive"
    `MetricCard`'s `render` builds a `Stat` (the H4 label/value/delta block) and
    wraps it in a `Card` (the H3 surface). When `trailing` is set, the stat and the
    extra widget go into a centered `Row`; otherwise the stat is the body directly.
    Nothing beyond those two composed primitives — the card inherits all of their
    surface and token behavior for free.

### `StatCard`

A **compact preset** of `MetricCard`: exactly the same component, just with a
denser default surface (`filled` instead of `elevated`). Handy for a tight grid of
numbers:

```python
from tempest_core import StatCard

total = StatCard(label="Images", value="1,024")
```

#### Props

`StatCard` **inherits every `MetricCard` prop** — the only difference is the
default `variant`.

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `variant` | `CardVariant` | `FILLED` | The preset's dense surface (override to retune). |
| *(the rest)* | — | *(same as `MetricCard`)* | `label`, `value`, `delta`, `delta_up`, `color_scheme`, `trailing`, `theme`, `media`. |

!!! tip "When to use each"
    Use `MetricCard` (elevated) for a screen's headline KPIs; use `StatCard`
    (filled, tighter) for a row/grid of secondary numbers that shouldn't compete
    for attention. Since `StatCard` **is** a `MetricCard`, every prop still applies
    — including setting `variant` back to `ELEVATED` if you want.

### `ConfidenceBadge`

A status pill showing a model's confidence, colored by threshold. It composes the
H4 `Badge`, picks its `color_scheme` from `confidence_scheme`, and labels itself as
a rounded percentage. An optional `label` becomes a prefix:

```python
from tempest_core import ConfidenceBadge

# Green pill "cat 92%" (>= 80% => success).
confidence = ConfidenceBadge(confidence=0.92, label="cat")

# No label, percentage only — and with custom thresholds.
raw = ConfidenceBadge(confidence=0.63, high=0.9, mid=0.6)  # "63%", amber
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `confidence` | `float` | *(required)* | The model confidence in `[0, 1]`. |
| `label` | `str` | `""` | An optional prefix (e.g. the predicted class) before the percentage. |
| `high` | `float` | `0.8` | The `success` threshold passed to `confidence_scheme`. |
| `mid` | `float` | `0.5` | The `warning` threshold passed to `confidence_scheme`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens resolve the pill. **Kept out of the IR.** |

!!! note "`SUBTLE` variant for accessibility"
    The badge paints with `BadgeVariant.SUBTLE` (the tonal *container* pair, WCAG-AA
    safe), **not** `SOLID`. A `SOLID` badge would paint white on the saturated
    status role — `success` (~3.02) and `warning` (~4.0) both **fail** AA contrast.
    The choice mirrors the H4 decision and keeps the badge legible on any status
    family.

### `confidence_scheme`

The pure function behind every confidence color in the kit. It's the classic
traffic light: `>= high` is green (`"success"`), `>= mid` is amber (`"warning"`),
below is red (`"error"`). Being pure and deterministic, every confidence-driven
component (badge, detection box) colors consistently:

```python
from tempest_core import confidence_scheme

confidence_scheme(0.92)              # "success"
confidence_scheme(0.63)              # "warning"
confidence_scheme(0.31)              # "error"
confidence_scheme(0.63, high=0.9, mid=0.6)  # "warning" (custom thresholds)
```

#### Signature

`confidence_scheme(conf: float, *, high: float = 0.8, mid: float = 0.5) -> str`

| Parameter | Type | Default | What it does |
| --- | --- | --- | --- |
| `conf` | `float` | *(required)* | The confidence score, typically in `[0, 1]`. |
| `high` | `float` | `0.8` | **Inclusive** threshold at/above which the score reads as high (`"success"`). |
| `mid` | `float` | `0.5` | **Inclusive** threshold at/above which it reads as medium (`"warning"`); below, low (`"error"`). |

!!! info "Inclusive thresholds, cascading comparison"
    The comparison is `conf >= high` first, then `conf >= mid`, else `error` — so
    the thresholds are **inclusive** (exactly `0.8` with the default is already
    `success`). Pass your own `high` / `mid` to recalibrate without swapping
    functions: `ConfidenceBadge` and `DetectionOverlay` forward those two names
    straight here.

## Charts over the Canvas

Charts aren't new widgets: each one **lowers to a `Canvas`** carrying a draw
command list. The list is **deterministic** for fixed input — the conformance
suite pins the exact sequence — and uses only the draw vocabulary that already
exists. Data arrives in a frozen `ChartSeries`, so one chart plots several named,
colored series.

### `ChartSeries`

A single named, optionally-colored data series. A chart takes a **list** of these
rather than a bare `list[float]`, so it can plot several series at once, each with
its own label and (optionally) its own `color_scheme`. It's a **frozen** model:

```python
from tempest_core import ChartSeries

loss = ChartSeries(points=[0.90, 0.42, 0.31, 0.18], label="loss", color_scheme="error")
acc = ChartSeries(points=[0.55, 0.71, 0.84, 0.92], label="acc", color_scheme="success")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `points` | `list[float]` | `[]` | The series' y-values, in plot order (one per x position). |
| `label` | `str` | `""` | An optional label (e.g. for a legend; carried, not drawn by the minimal charts). |
| `color_scheme` | `str \| None` | `None` | The series' M3 role family; `None` falls back to the chart's rotating palette. |

!!! note "Rotating palette when `color_scheme` is `None`"
    When a series doesn't name its color, the chart picks from the rotating palette
    (`primary` → `secondary` → `tertiary` → `error` → `success` → `warning` →
    `info`) by the series **index**. So two uncolored series never come out the
    same, and you only set `color_scheme` when the color carries meaning.

### `LineChart`

A multi-series line chart drawn over a `Canvas`. Each `ChartSeries` becomes a
connected polyline over a framed plot with y-axis gridlines and right-aligned tick
labels:

```python
from tempest_core import ChartSeries, LineChart

curve = LineChart(
    series=[
        ChartSeries(points=[0.90, 0.42, 0.31, 0.18], label="loss", color_scheme="error"),
        ChartSeries(points=[0.55, 0.71, 0.84, 0.92], label="acc", color_scheme="success"),
    ],
    width=320.0,
    height=200.0,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `series` | `list[ChartSeries]` | `[]` | The series to plot (each its own polyline + color). |
| `width` | `float` | `320.0` | The canvas width, in logical pixels. |
| `height` | `float` | `200.0` | The canvas height, in logical pixels. |
| `color_scheme` | `str` | `"primary"` | The default M3 family for a series with no color of its own. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens become the concrete colors. **Kept out of the IR.** |

!!! note "Draw vocabulary — there is no `DrawLine`"
    A line is `MoveTo` + a run of `LineTo` + a single `StrokeCmd`; the axes and
    gridlines come from the same trio. The y-axis labels are `DrawText`
    (baseline-anchored, **no** alignment field) — to right-align them the engine
    shifts the anchor left by an estimate of the text width. No new draw command is
    created, and the final list is deterministic for fixed input.

### `BarChart`

A bar chart over a `Canvas`. Accepts either a list of `ChartSeries` (the **first**
series becomes the bars) or, for the trivial single-series case, a plain
`values: list[float]` with optional `labels`:

```python
from tempest_core import BarChart

# Simple path: a list of values (+ labels).
bars = BarChart(values=[3.0, 5.0, 2.0], labels=["a", "b", "c"])
```

```python
from tempest_core import BarChart, ChartSeries

# Typed path: the first series becomes the bars, with an explicit color.
bars = BarChart(
    series=[ChartSeries(points=[3.0, 5.0, 2.0], color_scheme="tertiary")],
    labels=["a", "b", "c"],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `series` | `list[ChartSeries]` | `[]` | The series (the **first** is plotted as bars). Optional if `values` is given. |
| `values` | `list[float]` | `[]` | A single-series value list (used when `series` is empty). |
| `labels` | `list[str]` | `[]` | Optional x-axis labels for the bars. |
| `width` | `float` | `320.0` | The canvas width, in logical pixels. |
| `height` | `float` | `200.0` | The canvas height, in logical pixels. |
| `color_scheme` | `str` | `"primary"` | The default M3 family for the bars (if the series names none). |
| `theme` | `Theme` | `Theme()` | The theme whose tokens become the concrete colors. **Kept out of the IR.** |

!!! note "A bar is `DrawRect` + `FillCmd`; `series` beats `values`"
    Each bar is a `DrawRect` followed by a `FillCmd` over the same framed plot as
    the axes. When **both** `series` and `values` are passed, `series` wins (its
    first series' `points` and `color_scheme` are used); `values` only kicks in when
    `series` is empty. The baseline always includes `0`, so bars have a meaningful
    floor. The command sequence is deterministic — the conformance suite pins it.

## Detection overlay

An object-detection result is an image with boxes on top. The engine takes **no**
`ort-vision-sdk` dependency: boxes arrive normalized in `[0, 1]`, which makes them
resolution-independent, and the adapter from a real `Detection` result to
`DetectionBox` lives on the tempestroid side, not here.

### `DetectionBox`

A **normalized `xyxy` box in `[0, 1]`** — coordinates are fractions of the canvas
width/height (`0` = left/top, `1` = right/bottom), multiplied by the pixel size
only at draw time. It's a **frozen** model:

```python
from tempest_core import DetectionBox

cat = DetectionBox(x1=0.10, y1=0.20, x2=0.50, y2=0.60, name="cat", conf=0.93)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `x1` | `float` | *(required)* | The left edge as a fraction of the width (`[0, 1]`). |
| `y1` | `float` | *(required)* | The top edge as a fraction of the height (`[0, 1]`). |
| `x2` | `float` | *(required)* | The right edge as a fraction of the width (`[0, 1]`). |
| `y2` | `float` | *(required)* | The bottom edge as a fraction of the height (`[0, 1]`). |
| `name` | `str` | `""` | An optional class label drawn beside the box. |
| `conf` | `float` | `1.0` | The confidence in `[0, 1]` (drives the box color and the label percentage). |

!!! tip "Normalized = resolution-independent"
    Because the coordinates are fractions, the **same** box draws correctly at any
    canvas size — change the overlay's `width`/`height` and the boxes follow. It's
    the common normalized `xyxy` convention, but without coupling the engine to any
    vision SDK. Write a `det.box.xyxy` → `DetectionBox` adapter in your app.

### `DetectionOverlay`

An image with detection boxes on top. It lowers to a `Stack` of a base `Image`
(`fit=COVER`) under a `Canvas` overlay; each `DetectionBox` is multiplied by the
canvas size and drawn as a stroked rectangle, colored by `confidence_scheme`, with
a `"{name} {conf:.0%}"` caption:

```python
from tempest_core import DetectionBox, DetectionOverlay

overlay = DetectionOverlay(
    image_src="photo.jpg",
    boxes=[
        DetectionBox(x1=0.10, y1=0.20, x2=0.50, y2=0.60, name="cat", conf=0.93),
        DetectionBox(x1=0.55, y1=0.30, x2=0.90, y2=0.80, name="dog", conf=0.61),
    ],
    width=320.0,
    height=320.0,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `image_src` | `str` | *(required)* | The image source (URL or asset path) to box over. |
| `boxes` | `list[DetectionBox]` | `[]` | The normalized boxes to draw. |
| `width` | `float` | `320.0` | The canvas/image width, in logical pixels. |
| `height` | `float` | `320.0` | The canvas/image height, in logical pixels. |
| `high` | `float` | `0.8` | The `success` threshold passed to `confidence_scheme`. |
| `mid` | `float` | `0.5` | The `warning` threshold passed to `confidence_scheme`. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply the label color. **Kept out of the IR.** |

!!! note "`Stack(Image + Canvas)` — each box is stroke + label, no new command"
    The overlay is a `Stack` of the `Image` (`COVER`) under a `Canvas`. Each box
    becomes a `DrawRect` + `StrokeCmd` (in the color from
    `confidence_scheme(box.conf, high=..., mid=...)`) and, when there's a caption, a
    small background (`DrawRect` + `FillCmd`) plus the `DrawText` in the
    `on_<scheme>` pair for contrast. Each box colors consistently with
    `ConfidenceBadge` because both go through the **same** function. No new draw
    command is introduced.

## Pick → result flow

The last link: pick an image, run inference, show the result. The component
**holds no state** — the app owns the inference and builds the result widget;
`ResultView` only arranges the picker and the result in a column.

### `ResultView`

Stacks an `ImagePicker` over an optional `result` slot — the widget the app builds
from the model output (a `DetectionOverlay`, a `MetricCard`, a `ConfidenceBadge` or
a chart):

```python
from tempest_core import DetectionBox, DetectionOverlay, ResultView

def on_pick(uri: str) -> None:
    """Run inference and store the result in the app state."""
    ...  # the app runs the model and set_state's the built widget

view = ResultView(
    label="Upload a photo",
    on_pick=on_pick,
    result=DetectionOverlay(
        image_src="photo.jpg",
        boxes=[DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="cat", conf=0.93)],
    ),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `str` | `""` | The picked image URI (forwarded to the picker; `""` until one is chosen). |
| `label` | `str` | `""` | An optional heading above the picker. |
| `on_pick` | `Callable[[str], Any]` | *(required)* | Called with the picked image URI on selection. |
| `result` | `Widget \| None` | `None` | The result widget below the picker; `None` shows only the picker. |
| `theme` | `Theme` | `Theme()` | The theme whose tokens supply the spacing. **Kept out of the IR.** |

!!! note "The app owns the inference"
    `render` builds a `Column` of an `ImagePicker` and, when set, the `result`. The
    component runs no model: you handle `on_pick`, run inference, build the result
    widget (overlay, card, chart…) and pass it back in `result` on a rebuild. This
    keeps `ResultView` stateless and reusable for **any** vision task —
    classification, detection or segmentation.

## Recap

- **Everything composes or draws** — no research component invents a primitive,
  `Style` field, resolver or new draw command.
- **Cards**: `MetricCard` = `Card` (H3) + `Stat` (H4); `StatCard` is the same, a
  compact `filled` preset; `ConfidenceBadge` = `Badge` (H4) `SUBTLE`, colored by
  `confidence_scheme`.
- **`confidence_scheme(conf, *, high=0.8, mid=0.5)`** is the pure, deterministic
  function behind every confidence color: `>= high` → `success`, `>= mid` →
  `warning`, else `error`.
- **Charts**: `LineChart` / `BarChart` lower to a **deterministic** `Canvas`
  command list — line = `MoveTo` + `LineTo` + `StrokeCmd`, bar = `DrawRect` +
  `FillCmd`, no `DrawLine`. Data comes in a frozen `ChartSeries`; on `BarChart`,
  `series` beats `values`.
- **Detection**: `DetectionBox` is normalized `xyxy` in `[0, 1]`;
  `DetectionOverlay` is a `Stack(Image COVER + Canvas)` that colors each box by the
  same `confidence_scheme`, with no `ort-vision-sdk` dependency.
- **`ResultView`** arranges `ImagePicker` + a `result` slot statelessly — the app
  runs the inference and builds the result.
