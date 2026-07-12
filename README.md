# Tempest Core

📚 **Documentation:** [Português (Brasil)](https://mauriciobenjamin700.github.io/tempest-core/)
· [English (US)](https://mauriciobenjamin700.github.io/tempest-core/en/) — bilingual, on GitHub Pages.
Includes an in-depth **[component gallery](https://mauriciobenjamin700.github.io/tempest-core/gallery/buttons/)** — every widget and component with its props, variants, states and nuances.

**Renderer-agnostic UI core** shared across the tempest stack — the engine behind
both [tempestroid](https://github.com/mauriciobenjamin700/tempestroid) (native
renderers: Qt / Compose / Android) and tempestweb (DOM, WASM + server modes).

It is the *one tree, many renderers* core: the IR, the reconciler (`build` /
`diff`), the state model (`App`), the typed style model (`Style`, `Color`, `Edge`),
the widget and component trees, plus the cross-cutting helpers (animation, i18n,
navigation, theme, validators). It carries **no platform-coupled code** — no Qt, no
JNI, no Android, no DOM — so it imports cleanly under CPython, Pyodide and a
headless server. Renderers live in the consumers; this package only produces and
diffs the tree.

```python
from tempest_core import App, Column, Text, Button, Style, build, diff

old = build(Column(children=[Text(content="Count: 0", key="label")]))
new = build(Column(children=[Text(content="Count: 1", key="label")]))
patches = diff(old, new)          # -> [Update(set_props={"content": "Count: 1"})]
```

### Design system (Chakra-style variants → Material 3)

Components take Chakra-ergonomics props (`variant`/`size`/`color_scheme`) and a
`theme`, and resolve a concrete Material 3 `Style` via pure resolvers in
`variants.py` — `resolve_variant` (buttons), `resolve_field_variant` (text
inputs / select / masked / autocomplete / pin), `resolve_selection_variant`
(checkbox / switch), `resolve_slider_variant` (sliders), `resolve_surface_variant`
(cards / surfaces — H3), `resolve_badge_variant` (badges / tags / chips — H4) and
`resolve_alert_variant` (alerts / banners — H4). The interactive resolvers each
ship a `*_states` sibling returning the per-state table (default/hover/pressed/
disabled/focus) the renderers apply on real events; surfaces and alerts are
non-interactive, so there is no state table. The touch target is held ≥ 48dp and
WCAG-AA contrast is preserved. An explicit `style=` is always merged on top.

```python
from tempest_core import Alert, Badge, CardVariant, IconButton, Stat, Tabs, Theme
from tempest_core.components import AppBar, Card, HStack, NavBar, SearchBar, Surface, VStack
from tempest_core.widgets import Input, Spacer, Text
from tempest_core.style import AlertVariant, BadgeVariant, FieldVariant

field = Input(value="", field_variant=FieldVariant.FILLED, color_scheme="primary")
button = IconButton(icon="settings", color_scheme="primary", label="Open settings")

# H3 styled surface & layout kit: cards/surfaces (elevated/filled/outlined) +
# SwiftUI-style stacks with token-step gaps + a flex Spacer.
card = Card(variant=CardVariant.OUTLINED, color_scheme="primary", children=[
    HStack(gap="md", children=[Text(content="Title"), Spacer(), Text(content="42")]),
])

# H4 styled data-display & feedback kit: status families (success/warning/info) +
# badge/tag/chip + alert/banner + stat.
ok = Badge(label="LIVE", variant=BadgeVariant.SUBTLE, color_scheme="success")
note = Alert(title="Saved", body="Your changes are live.",
             variant=AlertVariant.LEFT_ACCENT, color_scheme="success")
metric = Stat(label="Active users", value="1.2k", delta="+12%", delta_up=True)

# H5 styled navigation kit: themed bars + an active accent pill / underline tab.
bar = AppBar(title="Inbox", color_scheme="primary", actions=[button])
search = SearchBar(value="", on_change=lambda e: None, color_scheme="primary")
nav = NavBar(items=["Home", "Search", "You"], active=0, on_select=lambda i: None)
tabs = Tabs(tabs=["Overview", "Activity"], active=0, on_select=lambda i: None)

# H6 research kit: metric cards, charts (over the Canvas) and a detection overlay
# for showing an ONNX / ort-vision-sdk result end to end.
from tempest_core import (
    BarChart, ChartSeries, ConfidenceBadge, DetectionBox, DetectionOverlay,
    LineChart, MetricCard,
)

acc = MetricCard(label="Accuracy", value="92%", delta="+3%", delta_up=True)
conf = ConfidenceBadge(confidence=0.92, label="cat")  # success pill "cat 92%"
chart = LineChart(series=[ChartSeries(points=[0.1, 0.4, 0.35, 0.8], color_scheme="primary")])
bars = BarChart(values=[3.0, 5.0, 2.0], labels=["a", "b", "c"])
boxed = DetectionOverlay(image_src="photo.jpg", boxes=[
    DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="cat", conf=0.93),
])
```

The H3 surface kit (`CardVariant`, `resolve_surface_variant`, `Surface`,
`StyledContainer`, `HStack`/`VStack`, `Spacer`) realizes Material 3 elevation as a
`Shadow` mapped from the M3 level (`elevation=0..5`) — **no new `Style` field**.
`Card`/`Divider`/`ListTile`/`Accordion`/`Grid` are themed off the tokens, and the
old call sites stay backward-compatible.

The H4 data-display & feedback kit adds three Material 3 status color families —
`success` / `warning` / `info` (new `ColorRole` members + `ColorScheme` fields,
generated from fixed semantic seeds, fully back-compatible) — and two new variant
resolvers/enums (`BadgeVariant`/`resolve_badge_variant`,
`AlertVariant`/`resolve_alert_variant`). New components `Alert`, `Stat`,
`ProgressStepper` and the `Tag` (a static `Chip` preset) join the re-themed
`Badge`/`Banner`/`Avatar`/`EmptyState`/`SegmentedControl`/`Rating`/`Chip`. Because a
saturated status role on white can fail WCAG-AA (e.g. success solid = 3.02), the
subtle status surfaces use the tonal `*_container` / `on_*_container` pairing (AA-
safe). Still **no new `Style` field** — status flows through `color_scheme`.

The H5 navigation kit is a pure **skin pass** over the existing navigation
components — **no new resolver, no new enum, no new `Style` field**. `AppBar` /
`Footer` / `CollapsingAppBar` / `Sidebar` / `Drawer` resolve their bar/panel
surface via `resolve_surface_variant` (variant / color_scheme / elevation);
`NavBar` paints the active item as an accent pill (`resolve_badge_variant`) over a
ghost inactive item (`resolve_variant`); the new **`Tabs`** strip gives the active
tab an underline indicator (a bottom `SideBorder` in the accent role); `SearchBar`
resolves its field via `resolve_field_variant` and its clear button as an
`IconButton`; `Burger` lowers to an `IconButton` (the `menu` icon); `Header` and
`Breadcrumb` migrate to theme roles. Every old call site and explicit `style=`
keeps working.

The H6 research / data-science kit (`tempest_core/components/research.py`) is the
surface a researcher uses to show an ONNX / [`ort-vision-sdk`](https://github.com/mauriciobenjamin700/ort-vision-sdk)
result end to end — **no new `Style` field, no new resolver, no new `Canvas` draw
command**. `MetricCard` / `StatCard` compose the H3 `Card` around the H4 `Stat`;
`ConfidenceBadge` colors a `Badge` by the `confidence_scheme` traffic-light helper
(`success`/`warning`/`error`); `LineChart` / `BarChart` draw over the E7 `Canvas`
using only the existing command vocabulary (a line is `MoveTo`+`LineTo`+`StrokeCmd`
— there is no `DrawLine`; a bar is `DrawRect`+`FillCmd`; y-tick labels are
right-aligned `DrawText`) and emit a **deterministic** command list;
`DetectionOverlay` stacks an `Image` under a `Canvas` of confidence-colored
bounding boxes (`DetectionBox` is normalized `[0, 1]` `xyxy`, multiplied by the
canvas size at draw time — the engine takes no `ort-vision-sdk` dependency); and
`ResultView` is the image-picker → result flow. `DataTable` gains app-driven sort
(`sort_column`/`on_sort`) + pagination (`page`/`page_size`/`on_page`) and themed
colors; `Calendar`/`Clock` migrate to theme tokens (the default look shifts from
the legacy dark palette to M3 light).

## Install

```bash
pip install tempest-core
```

Requires Python `>=3.11`. Only hard dependency: `pydantic>=2`.

## Status

Extracted from tempestroid's vendored core. **tempestweb** consumes it directly
(no vendored copy). tempestroid's own migration to depend on this package — with
its full Qt↔Compose conformance suite green — is the next phase.

## Develop

```bash
uv sync --extra dev
ruff check . && ruff format --check .
mypy tempest_core && pyright tempest_core
pytest -q
```
