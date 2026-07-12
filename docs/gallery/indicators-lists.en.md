# Indicators & lists

This category groups two families of feedback and data widgets. The
**indicators** — **`ProgressBar`** and **`Spinner`** — are non-interactive leaves
(no events) that communicate progress or activity. The **virtualized lists** —
**`LazyColumn`**, **`LazyRow`**, **`LazyGrid`**, **`SectionList`**, and the
**`RefreshControl`** wrapper — declare an `item_count` plus an `item_builder`, and
only materialize the **visible window** of items into the IR. 🚀

!!! info "What you'll learn here"
    - How a `ProgressBar` toggles between **determinate** and **indeterminate**, and what a `Spinner` always is.
    - How `color_scheme` picks the accent color family on each indicator.
    - How a list **virtualizes**: `item_count` + `item_builder` + the window of size `DEFAULT_WINDOW_SIZE`.
    - Why the first mount already has content, and how the application **slides the window** on a scroll.
    - How `on_end_reached` / `end_reached_threshold` (pagination), pull-to-refresh, and `SectionList` sections work.

## Progress indicators

Indicators are **non-interactive leaf widgets**: they have no event handlers, only
props the renderer paints against the active theme. Use them to signal that
something is happening — a bar for measurable progress, a spinner for activity of
unknown duration.

### `ProgressBar`

A horizontal progress bar. It shows either a **determinate fraction** in
`[0.0, 1.0]`, or an **indeterminate** (looping) bar when the duration is unknown:

```python
from tempest_core import ProgressBar

# Determinate: 42% complete.
loading = ProgressBar(value=0.42)

# Indeterminate: work of unknown duration (value is ignored).
processing = ProgressBar(indeterminate=True)
```

The accent (the filled stretch of the track) is painted by the `color_scheme`
role family:

```python
from tempest_core import ProgressBar

upload = ProgressBar(value=0.7, color_scheme="secondary")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `value` | `float` | `0.0` | The completed fraction in `[0.0, 1.0]` (ignored when `indeterminate` is set). |
| `indeterminate` | `bool` | `False` | When `True`, render a looping bar with no fixed value (work of unknown duration). |
| `color_scheme` | `str` | `"primary"` | The M3 role family the renderer paints the bar's accent with. |

!!! note "`value` is validated to the `[0.0, 1.0]` range"
    The `value` field has `ge=0.0` and `le=1.0` — passing something outside that
    range is a Pydantic validation error at construction, not a silent clamp. When
    `indeterminate=True`, `value` is simply ignored by the renderer.

!!! tip "Determinate when you know the fraction; indeterminate when you don't"
    Prefer `value=` whenever you can measure progress (a download with a known
    size, step N of M). Reserve `indeterminate=True` for opaque waits — that's
    what avoids a bar stuck at 10% because you don't know the total.

### `Spinner`

A circular activity indicator — **always indeterminate**. It has no `value`; it
exists only to say "something is running". `size` is the diameter in logical
pixels, or `None` for the renderer default:

```python
from tempest_core import Spinner

# Renderer's default diameter.
busy = Spinner()

# Larger spinner, painted with the error role.
reloading = Spinner(size=48.0, color_scheme="error")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `size` | `float \| None` | `None` | The indicator's diameter in logical pixels, or `None` for the renderer default. |
| `color_scheme` | `str` | `"primary"` | The M3 role family the renderer paints the spinner's accent with. |

!!! info "`Spinner` has no `value` or `indeterminate`"
    Unlike `ProgressBar`, the spinner is circular and **always** looping — there is
    no "determinate" state for it. If you need to show a fraction, use
    `ProgressBar`.

## Virtualized lists

Lists are the framework's **virtual** container primitives. Instead of declaring a
materialized list of children, they declare an `item_count` plus an
`item_builder(index) -> Widget`. Only the **visible window** of items ever reaches
the IR: the renderer reports the scroll `offset` via `ScrollEvent`, the
application recomputes the `[start, end)` window and rebuilds, and the keyed diff
(item key = `str(index)`) turns a window slide into a minimal
remove/reorder/insert sequence.

`item_builder` is a Python callable that materializes the widget on the **same**
thread as `build` — it never crosses the native boundary. The serializer drops it;
the device receives `item_count` plus the already-materialized window children and
renders natively (Compose `LazyColumn`).

### `DEFAULT_WINDOW_SIZE`

The constant that defines **how many items** enter the initial visible window when
a list doesn't declare an explicit `window`:

```python
from tempest_core import DEFAULT_WINDOW_SIZE

print(DEFAULT_WINDOW_SIZE)  # 20
```

`DEFAULT_WINDOW_SIZE` is **`20`**. It is the default value of every list's
`window_size` field (and of every `SectionHeader`). It keeps the first mount cheap
— the device renders those 20 items, not the total `item_count` — while still
showing content immediately.

!!! info "The virtualization window, in one sentence"
    The window is `window` when set (the application slides it in response to a
    `ScrollEvent` via `App.slide_window`), otherwise the initial default
    `[0, min(window_size, item_count)]`. That's what makes the **first** mount
    non-empty: `build` materializes `window_size` items immediately, without
    waiting for a scroll event. Virtualization is preserved — only the window is
    ever built, never all `item_count` items.

### `LazyColumn`

A vertically virtualized list (Compose `LazyColumn`). It declares an `item_count`
and an `item_builder` instead of materialized children; only the visible window is
built into the IR:

```python
from tempest_core import LazyColumn, Text

def build_item(index: int) -> Text:
    return Text(content=f"Item {index}")

lst = LazyColumn(item_count=10_000, item_builder=build_item)
```

That `LazyColumn` with 10,000 items materializes only the first `20`
(`DEFAULT_WINDOW_SIZE`) on the first mount. It emits `ScrollEvent` as it scrolls,
`RefreshEvent` on pull-to-refresh, and `EndReachedEvent` when scrolling past
`end_reached_threshold`:

```python
from tempest_core import LazyColumn, Text

async def load_more(event) -> None:  # (1)!
    ...

lst = LazyColumn(
    item_count=10_000,
    item_builder=lambda i: Text(content=f"Item {i}"),
    end_reached_threshold=0.8,
    on_end_reached=load_more,
)
```

1. The handler may be **sync or `async`** — the runtime schedules awaitables on
   the event loop. It receives an `EndReachedEvent` (see [API reference](../reference.md)).

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `item_count` | `int` | *(required)* | The total number of items in the list. |
| `item_builder` | `ItemBuilder` | *(required)* | Factory building the item widget at a given index. Lives only on the Python side; never serialized. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | How many items enter the initial window when `window` is unset. |
| `window` | `tuple[int, int] \| None` | `None` | The current visible `[start, end)` window, or `None` for the initial default. The application slides it on a scroll. |
| `end_reached_threshold` | `float` | `0.8` | The fraction `0..1` of total scroll at which `on_end_reached` fires. |
| `refreshing` | `bool` | `False` | Whether the pull-to-refresh spinner is active. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Optional handler for scroll events. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Optional handler for pull-to-refresh. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Optional handler fired near the end of the list. |

!!! warning "Don't materialize the whole list yourself"
    The point of virtualization is for `item_builder` to build **one** item per
    index, on demand. Passing a huge `item_count` is great — only the window is
    built. But building the entire list of widgets up front and returning them
    through the builder throws away virtualization and bloats the IR.

!!! note "The application slides the `window`, not the widget"
    `LazyColumn` doesn't move on its own. When the renderer reports a
    `ScrollEvent`, the application calls `App.slide_window` to compute the new
    `[start, end)` and rebuilds with the updated `window`. The widget only
    describes which window to materialize; the movement comes from outside.

### `LazyRow`

The horizontal analogue of `LazyColumn` (Compose `LazyRow`): **identical
contract**, items laid out and scrolled left-to-right.

```python
from tempest_core import LazyRow, Text

carousel = LazyRow(
    item_count=500,
    item_builder=lambda i: Text(content=f"Slide {i}"),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `item_count` | `int` | *(required)* | The total number of items in the list. |
| `item_builder` | `ItemBuilder` | *(required)* | Factory building the item widget at a given index. Lives only on the Python side; never serialized. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | How many items enter the initial window when `window` is unset. |
| `window` | `tuple[int, int] \| None` | `None` | The current visible `[start, end)` window, or `None` for the initial default. |
| `end_reached_threshold` | `float` | `0.8` | The fraction `0..1` of total scroll at which `on_end_reached` fires. |
| `refreshing` | `bool` | `False` | Whether the pull-to-refresh spinner is active. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Optional handler for scroll events. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Optional handler for pull-to-refresh. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Optional handler fired near the end of the list. |

!!! tip "Same API, different axis"
    If you already know `LazyColumn`, you already know `LazyRow` — the fields and
    events are exactly the same. The only difference is the scroll orientation.

### `LazyGrid`

A virtualized grid (Compose `LazyVerticalGrid`). It lays virtualized items out in
a fixed number of `columns`, scrolling vertically. It has **no pull-to-refresh** —
wrap it in a `RefreshControl` if you need it:

```python
from tempest_core import LazyGrid, Text

gallery = LazyGrid(
    item_count=1_000,
    item_builder=lambda i: Text(content=f"Photo {i}"),
    columns=3,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `item_count` | `int` | *(required)* | The total number of items in the grid. |
| `item_builder` | `ItemBuilder` | *(required)* | Factory building the item widget at a given index. Lives only on the Python side; never serialized. |
| `columns` | `int` | `2` | The number of grid columns. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | How many items enter the initial window when `window` is unset. |
| `window` | `tuple[int, int] \| None` | `None` | The current visible `[start, end)` window, or `None` for the initial default. |
| `end_reached_threshold` | `float` | `0.8` | The fraction `0..1` of total scroll at which `on_end_reached` fires. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Optional handler for scroll events. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Optional handler fired near the end of the grid. |

!!! warning "The grid has no `on_refresh` or `refreshing`"
    Unlike `LazyColumn` / `LazyRow`, `LazyGrid` doesn't expose pull-to-refresh. For
    the pull-to-refresh gesture on a grid, wrap it in a `RefreshControl` (see
    below).

### `SectionHeader`

One section of a `SectionList`: a header plus virtualized items. It is **not a
widget** — it's a **frozen** value object (`frozen=True`) describing how to build a
section's sticky header and its items. Each section has its own virtualization
window:

```python
from tempest_core import SectionHeader, Text

section_a = SectionHeader(
    title="A",
    item_count=200,
    item_builder=lambda i: Text(content=f"A-{i}"),
    header_builder=lambda: Text(content="Section A"),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str` | *(required)* | A stable label for the section (used as a key and for the header). |
| `item_count` | `int` | *(required)* | The number of items in this section. |
| `item_builder` | `ItemBuilder` | *(required)* | Factory building the item widget at a section-local index. |
| `header_builder` | `HeaderBuilder` | *(required)* | Factory building this section's sticky header widget. |
| `window_size` | `int` | `DEFAULT_WINDOW_SIZE` (`20`) | How many items enter this section's initial window when `window` is unset. |
| `window` | `tuple[int, int] \| None` | `None` | This section's current visible `[start, end)` window, or `None` for the initial default. |

!!! note "The section is frozen; the application replaces it via `model_copy`"
    Because `SectionHeader` is `frozen=True`, sliding its window doesn't mutate the
    section — the application **replaces** the (frozen) section with a copy carrying
    the new `window` via `model_copy`. Each materialized item is keyed
    `"sec:<title>:<index>"` and the header `"sec:<title>:header"`, so every child of
    a `SectionList` has a globally unique key for the keyed diff.

### `SectionList`

A sectioned virtualized list with sticky headers. Each `SectionHeader` declares
its header plus its own virtualized items. The renderer renders the headers sticky
(Compose `stickyHeader`; the Qt simulator pins a label above the scroll area):

```python
from tempest_core import SectionHeader, SectionList, Text

def make_section(letter: str) -> SectionHeader:
    return SectionHeader(
        title=letter,
        item_count=100,
        item_builder=lambda i: Text(content=f"{letter}-{i}"),
        header_builder=lambda: Text(content=f"Section {letter}"),
    )

contacts = SectionList(
    sections=[make_section("A"), make_section("B"), make_section("C")],
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `sections` | `list[SectionHeader]` | `[]` | The ordered sections to render. |
| `end_reached_threshold` | `float` | `0.8` | The fraction `0..1` of total scroll at which `on_end_reached` fires. |
| `on_scroll` | `ScrollHandler \| None` | `None` | Optional handler for scroll events. |
| `on_end_reached` | `EndReachedHandler \| None` | `None` | Optional handler fired near the end of the list. |

!!! info "Each section virtualizes its own window"
    A `SectionList` has no single window — each `SectionHeader` carries its own
    `window_size` / `window`. On build, `SectionList` flattens, in order, each
    section's header plus its windowed items, all keyed for the reconciler's keyed
    diff.

!!! note "`sections` defaults to `[]`, never `None`"
    The `sections` field uses `default_factory` for an empty list — a `SectionList`
    with no sections is a valid state (empty list), not an error.

### `RefreshControl`

A **standalone** pull-to-refresh wrapper (Compose `PullToRefreshBox`), decoupled
from a virtualized list. Wrap it around any scrollable content — including a
`LazyGrid`, which has no refresh of its own. The content is supplied by the
renderer; the widget carries only the refresh contract:

```python
from tempest_core import RefreshControl

async def reload(event) -> None:
    ...

control = RefreshControl(refreshing=False, on_refresh=reload)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `refreshing` | `bool` | `False` | Whether the pull-to-refresh spinner is active. |
| `on_refresh` | `RefreshHandler \| None` | `None` | Optional handler for pull-to-refresh. |

!!! tip "You drive `refreshing`"
    The spinner doesn't disappear on its own: in your `on_refresh`, kick off the
    reload and, when it finishes, rebuild with `refreshing=False`. Setting
    `refreshing=True` while the data arrives keeps the indicator spinning; going
    back to `False` hides it.

## Recap

- **Indicators** are non-interactive leaves: `ProgressBar` toggles
  **determinate** (`value` in `[0.0, 1.0]`) and **indeterminate**; `Spinner` is
  circular and **always** indeterminate. `color_scheme` paints the accent.
- **Virtualization**: lists declare `item_count` + `item_builder` and only
  materialize the **visible window**; `item_builder` never crosses the native
  boundary.
- **`DEFAULT_WINDOW_SIZE` is `20`** — the default `window_size` that gives the
  first mount content without building all `item_count` items.
- **The application slides the `window`** on a `ScrollEvent` (via
  `App.slide_window`); the widget only describes which window to materialize.
- **`LazyColumn` / `LazyRow`** have pull-to-refresh (`refreshing` / `on_refresh`);
  **`LazyGrid` doesn't** — wrap it in a `RefreshControl`.
- **Pagination**: `on_end_reached` fires at `end_reached_threshold` (default
  `0.8`) of total scroll.
- **`SectionList`** flattens frozen `SectionHeader`s, each with its own window and
  sticky header; the application replaces the section via `model_copy` to slide.
