# Charts

Five charts, **one palette and one scale**. `LineChart`, `BarChart`,
`AreaChart`, `PieChart` and `RadarChart` all lower to a single `Canvas` carrying
a deterministic draw-command list — and they take color and axis from the same
place, `tempest_core.dataviz`. That is what makes two charts side by side look
like one product: series `0` is the same color in both, and both axes count in
steps of `5` instead of `0.0 · 7.7 · 15.4`. 📊

!!! info "What you will learn"
    - How to declare series with `ChartSeries` and plot lines, bars and areas.
    - How to stack areas (`stacked=True`) to read a running total.
    - How to show the composition of a total with `PieChart` (pie or donut).
    - How to compare series across several axes with `RadarChart`.
    - Where the colors (`chart_palette`) and the ticks (`nice_ticks`) come from —
      and why you almost never have to pick them.

## First chart

A chart takes a list of `ChartSeries`: the values (`points`), a label and, when
the color matters semantically, a `color_scheme`. Build it and you get a `Canvas`
node:

```python
from tempest_core import ChartSeries, LineChart, Theme, ThemeMode, build

theme = Theme(mode=ThemeMode.LIGHT)
chart = LineChart(
    theme=theme,
    series=[
        ChartSeries(points=[3.0, 23.1, 12.0, 18.4], label="2025"),
        ChartSeries(points=[5.0, 9.0, 14.0, 21.0], label="2026"),
    ],
)

node = build(chart)
print(node.type, node.key)
labels = [c.text for c in node.props["commands"] if c.kind == "draw_text"]
print(labels)
```

Output:

```text
Canvas line-chart
['0', '5', '10', '15', '20', '25']
```

Look at the axis: the data goes up to `23.1`, but the ticks are
`0 · 5 · … · 25`. That is `nice_ticks` at work — more on it below.

!!! tip "One series, the role color"
    When a series names no `color_scheme`, the chart takes the **palette** color
    at the series' index. Palette color `0` is the chart's own `color_scheme` role
    (`primary` by default), so a single-series chart paints exactly the color you
    expect.

## `LineChart` and `BarChart`

`LineChart` draws each series as a polyline. `BarChart` draws one series as bars
— from `series` (the first one) or the `values` shortcut — and writes each
`labels[i]` centered under its bar. A negative bar hangs below the zero line:

```python
from tempest_core import BarChart, Theme, ThemeMode, build

chart = BarChart(
    theme=Theme(mode=ThemeMode.LIGHT),
    values=[12.0, -4.0, 30.0, 18.0],
    labels=["jan", "feb", "mar", "apr"],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
```

Output:

```text
['-10', '0', '10', '20', '30', 'jan', 'feb', 'mar', 'apr']
```

## `AreaChart`

An area is a line filled down to its base. Each series becomes a polygon with a
translucent tint and, on top, a solid upper edge:

```python
from tempest_core import AreaChart, ChartSeries, Theme, ThemeMode, build

chart = AreaChart(
    key="revenue",
    theme=Theme(mode=ThemeMode.LIGHT),
    labels=["jan", "feb", "mar", "apr"],
    stacked=True,
    series=[
        ChartSeries(points=[10.0, 14.0, 9.0, 22.0], label="organic"),
        ChartSeries(points=[4.0, 6.0, 8.0, 7.0], label="paid"),
    ],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
print(sum(c.kind == "fill" for c in commands), "bands")
```

Output:

```text
['0', '10', '20', '30', 'jan', 'feb', 'mar', 'apr']
2 bands
```

With `stacked=True` the second band sits on the first, and the top edge is the
**total**: the axis reaches `30` because `22 + 7 = 29`. Without `stacked`, each
area fills to zero and later series paint over earlier ones.

!!! note "The edge carries the contrast"
    Each series' solid edge meets the palette's minimum contrast. The fill is a
    tint at 28% opacity, meant to show volume without hiding the grid — it is not
    the part that has to be read.

!!! info "A shorter series in a stack"
    A series with fewer points than the others counts as `0` at the positions it
    lacks, so whatever sits on top still has a defined base.

## `PieChart`

The composition of a total. Pass `(label, value)` pairs; slices run clockwise
from 12 o'clock, and a legend beside the pie shows a swatch and the percentage:

```python
from tempest_core import PieChart, Theme, ThemeMode, build

chart = PieChart(
    key="mix",
    theme=Theme(mode=ThemeMode.LIGHT),
    slices=[("organic", 62.0), ("paid", 38.0)],
    hole=0.5,
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
```

Output:

```text
['organic 62%', 'paid 38%']
```

`hole=0.5` cuts the center out and turns the pie into a donut. `show_legend=False`
drops the legend and gives the whole canvas to the circle.

The value contract is defined, not guessed:

| Input | What happens |
| --- | --- |
| negative value | `ValidationError` at construction — a share of a total is never negative |
| value `0` | its legend row and color slot stay; no slice is drawn |
| total `0` (no slices, or all zero) | draws the empty ring outline, in `outline_variant` |
| `nan` / `inf` | `ValidationError`, like every model in the core |

!!! note "An arc is a polyline, not `ArcTo`"
    The Qt renderer reads `ArcTo` angles counter-clockwise and Compose reads them
    clockwise — the same list would draw mirrored pies. So every arc is a run of
    `LineTo` points (one every 6° at most), which draws the same everywhere.
    Coordinates are rounded to 3 decimals so the list is identical on every
    platform.

## `RadarChart`

Compares series across three or more axes. The axes run clockwise from
12 o'clock; each series is a translucent polygon with a solid outline:

```python
from tempest_core import ChartSeries, RadarChart, Theme, ThemeMode, build

chart = RadarChart(
    theme=Theme(mode=ThemeMode.LIGHT),
    axes=["power", "speed", "range", "defense", "cost"],
    series=[
        ChartSeries(points=[3.0, 4.0, 2.0, 5.0, 1.0], label="model A"),
        ChartSeries(points=[4.5, 2.0, 4.0, 3.0, 3.5], label="model B"),
    ],
)

commands = build(chart).props["commands"]
print([c.text for c in commands if c.kind == "draw_text"])
print(sum(c.kind == "fill" for c in commands), "series")
```

Output:

```text
['power', 'speed', 'range', 'defense', 'cost']
2 series
```

The grid rings sit on the `nice_ticks` from `0` to the largest value — here
`0 · 1 · … · 5`. Pass `max_value=10.0` to pin the scale, handy when two radars
have to be compared with each other.

| Input | What happens |
| --- | --- |
| value below `0` | sits at the center |
| value above the range | sits on the rim |
| series with fewer points than axes | the missing ones read as `0`; extra points are ignored |
| fewer than 3 axes | no polygon is possible: only the spokes and labels |

## The palette: `chart_palette`

Every color a chart uses without you asking comes from here:

```python
from tempest_core import Theme, ThemeMode, chart_palette
from tempest_core.tokens import ColorRole, contrast_ratio

theme = Theme(mode=ThemeMode.LIGHT)
surface = theme.color(ColorRole.SURFACE)
for color in chart_palette(4, theme=theme):
    ratio = contrast_ratio(color, surface)
    print(f"#{color.r:02x}{color.g:02x}{color.b:02x}", round(ratio, 1))
```

Output:

```text
#584785 7.7
#b37b32 3.5
#319b8c 3.3
#cc33b5 4.3
```

Three rules define the sequence:

1. **Color 0 is the role.** `color_scheme="primary"` anchors the palette on the
   theme's `primary` — in light and in dark mode.
2. **Each next color rotates the hue by the golden angle** (~137.5°). Unlike
   splitting the circle into `N` parts, this does not depend on `N`: series `2`
   is the same color in a 3-series chart and in an 8-series one
   (`chart_palette(3) == chart_palette(8)[:3]`).
3. **Every color has at least 3:1 contrast against the `surface`.** A color that
   falls short walks its tone (darker on light, lighter on dark) until it clears.

!!! info "Why 3:1 and not 4.5:1"
    3:1 is WCAG 2.1 **1.4.11 — non-text contrast**, the criterion for graphical
    objects: a line, a bar, a slice. The 4.5:1 of 1.4.3 is for text, and chart
    text (ticks, legend) is already painted with the `on_surface` roles, which the
    theme holds to text contrast. Demanding 4.5:1 of every series would push the
    light palette toward near-black and wash out exactly the hues it exists to
    separate.

!!! warning "The anchor walks too"
    The baseline theme's `success` role sits at ~2.9:1 on the light `surface` —
    the theme guarantees `on_success` on `success`, not `success` on `surface`. In
    a chart with `color_scheme="success"`, color 0 comes out slightly darker than
    the role. A series with an explicit `ChartSeries(color_scheme="success")`, on
    the other hand, paints the role exactly: there the choice was yours.

## The scale: `nice_ticks`

Every chart's value axis uses `nice_ticks`, which picks the nearest
`1 / 2 / 5 × 10ⁿ` step and widens the domain out to multiples of it:

```python
from tempest_core import format_tick, nice_ticks

for lo, hi in [(0.0, 23.1), (-3.0, 7.0), (0.0, 0.3), (5.0, 5.0), (0.0, 0.0)]:
    ticks = nice_ticks(lo, hi, count=4)
    print((lo, hi), [format_tick(t, ticks) for t in ticks])
```

Output:

```text
(0.0, 23.1) ['0', '5', '10', '15', '20', '25']
(-3.0, 7.0) ['-4', '-2', '0', '2', '4', '6', '8']
(0.0, 0.3) ['0.0', '0.1', '0.2', '0.3']
(5.0, 5.0) ['4.4', '4.6', '4.8', '5.0', '5.2', '5.4', '5.6']
(0.0, 0.0) ['0.0', '0.2', '0.4', '0.6', '0.8', '1.0']
```

The cases that break a hand-rolled axis have a defined answer: a single-value
domain opens 10% on each side, a zero domain becomes `[0, 1]`, reversed bounds
are swapped, and `nan`/`inf` raise `ValueError` — for the same reason every core
model rejects non-finite numbers: one `nan` in a draw command takes down the
whole patch batch. `format_tick` prints each tick with the decimals its step
needs, never `-0`.

??? info "Technical details: where the step comes from"
    The thresholds are d3-array 3.2.4's `tickSpec` ones (`√50`, `√10`, `√2`) —
    the algorithm under the recharts axes the tempest-react-sdk charts use. Each
    threshold is the geometric mean of the two mantissas it separates, so the
    chosen step is the one nearest the raw step on a log scale. For a fractional
    step the ticks are computed as `i / 10` rather than `i * 0.1` — the division
    is exact where the multiplication accumulates binary error. `linear_map`
    completes the pair: it maps a domain value to pixels, and a zero-width domain
    lands in the middle of the output.

## Shared props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `width` | `float` | `320.0` | The canvas width, in logical pixels. |
| `height` | `float` | `200.0` | The canvas height, in logical pixels. |
| `color_scheme` | `str` | `"primary"` | The M3 role that anchors the palette. |
| `theme` | `Theme` | `current_theme()` | The theme colors and palette come from. **Not part of the IR.** |
| `media` | `MediaQueryData \| None` | `None` | Its `platform_dark_mode` resolves a `SYSTEM` theme. |

Per chart:

| Chart | Own props |
| --- | --- |
| `LineChart` | `series` |
| `BarChart` | `series` (the first becomes bars), `values`, `labels` |
| `AreaChart` | `series`, `labels`, `stacked` |
| `PieChart` | `slices: list[tuple[str, float]]`, `hole` (`0 ≤ hole < 1`), `show_legend` |
| `RadarChart` | `axes`, `series`, `max_value` (`> 0` or `None`) |

## Recap

- **Five charts, one `Canvas` each**, using only the draw vocabulary that already
  exists — no new renderer work.
- **`ChartSeries`** carries `points`, `label` and an optional `color_scheme`; a
  series without one takes the palette by index.
- **`AreaChart(stacked=True)`** reads as a running total; **`PieChart`** shows
  composition with a legend and an optional donut; **`RadarChart`** compares
  across 3+ axes.
- **`chart_palette`**: color 0 = the role, the rest rotate by the golden angle,
  all at ≥ 3:1 against the `surface` (WCAG 1.4.11), prefix-stable.
- **`nice_ticks`**: a `1 / 2 / 5 × 10ⁿ` step, a domain that always encloses the
  data, a defined answer for degenerate domains, and non-finite input rejected.
