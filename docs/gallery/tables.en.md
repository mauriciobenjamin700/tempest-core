# Tables

Tables display data in **rows by columns**. There are two, and they solve
opposite problems: **`Table`** is a **static** grid you build by hand from typed
values (`TableRow` / `TableCell`); **`DataTable`** is a **themed** string table
with **app-driven sort and pagination**. Like every `tempest-core` component,
both lower to a `Column` of `Row`s of `Container`/`Text` cells, so they render
identically in the Qt simulator and on the Compose device with no renderer
changes. 🚀

!!! info "What you'll learn here"
    - How to build a **static grid** with `Table` from `TableRow` and `TableCell`.
    - What `colspan` / `rowspan` do today (and what they don't yet).
    - `DataTable`'s **app-driven** pattern: the component **owns no state**.
    - How **sort** turns headers into tappable cells with a `▲`/`▼` arrow, and how to **paginate** with `page_size`.

## `Table`

A **static** data table laid out as rows of equal-width cells. You build it from
typed `TableRow`s, each carrying a list of `TableCell`s. In the minimal case,
just `rows`:

```python
from tempest_core import Table, TableRow, TableCell

table = Table(
    headers=["Name", "Role"],
    rows=[
        TableRow(cells=[TableCell(content="Ana"), TableCell(content="Admin")]),
        TableRow(cells=[TableCell(content="Bruno"), TableCell(content="Editor")]),
    ],
)
```

The `headers` become an **emphasised first row** (fill `SURFACE`, text
`ON_SURFACE` in bold); each body row gets a bottom divider and each cell
**grows** (`grow=1.0`) to share the row width evenly. Without `headers`, you get
the body only.

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `rows` | `list[TableRow]` | `[]` | The body rows, each a `TableRow` of `TableCell`s. |
| `headers` | `list[str]` | `[]` | Header labels rendered as an emphasised first row. Empty = no header. |
| `style` | `Style \| None` | `None` | A `Style` overlaid on the table's default `SURFACE` background. |

!!! note "Columns by position, equal width"
    There's no column model: the *n*-th `TableCell` of each row occupies the *n*-th
    column, and every cell grows equally. Align your rows yourself — a row with
    fewer cells simply has fewer columns on that row.

## `TableCell`

A single cell of a `Table`. It's an **immutable value** model (`frozen`): it
carries the text plus optional `colspan` / `rowspan` and its own `style`.

```python
from tempest_core import TableCell
from tempest_core import Style

highlight = TableCell(content="Total", style=Style(grow=1.0))
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `content` | `str` | *(required)* | The cell's text content. |
| `colspan` | `int` | `1` | How many columns the cell spans. |
| `rowspan` | `int` | `1` | How many rows the cell spans. |
| `style` | `Style \| None` | `None` | A `Style` overlaid on the cell's default padding/text. |

!!! warning "`colspan` and `rowspan` are informational for now"
    Both fields exist and are validated, but the **primitive lowering renders one
    cell per entry** — there's no cell merging yet. Treat them as metadata that
    renderers may honor in the future, not as a layout effect guaranteed today.

## `TableRow`

A single row of a `Table` — the ordered cells plus an optional `style` overlaid
on the row's default layout. Also `frozen`.

```python
from tempest_core import TableRow, TableCell
from tempest_core import Style

row = TableRow(
    cells=[TableCell(content="Ana"), TableCell(content="Admin")],
    style=Style(grow=1.0),  # overlaid on the row's default bottom divider
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `cells` | `list[TableCell]` | `[]` | The ordered cells of the row. |
| `style` | `Style \| None` | `None` | A `Style` overlaid on the row's default layout (which already carries a bottom divider). |

!!! tip "The row `style` is merged, not replaced"
    `Table` builds each row with a default bottom divider and then **merges your
    `style` on top** (via `merge_style`). You tweak a single field without losing
    the divider — the same override rule buttons use for `Style`.

## `DataTable`

A **themed string-matrix** table with **app-driven sort and pagination**. It's
the styled convenience for the common "headers + string matrix" case: it reads
every color from the `Theme` tokens (header `SURFACE_VARIANT` / `ON_SURFACE`,
body `SURFACE` with a subtle zebra stripe, divider `OUTLINE_VARIANT`) — no
hard-coded hexes. In the minimal case, just `columns` and `rows`:

```python
from tempest_core import DataTable

table = DataTable(
    columns=["Name", "Age"],
    rows=[["Ana", "42"], ["Bruno", "17"], ["Carla", "88"]],
)
```

That's already a themed table, ready for the renderers. The sort and pagination
props below are **additive**: every existing `DataTable(columns=…, rows=…)` call
site keeps working.

### The app-driven pattern

Following the same pattern as the **virtualized lists**, `DataTable` **owns no
state**. It is a pure projection of the state that **the application** holds:

- **Sort** — the app holds `sort_column` / `sort_ascending` and **passes the
  rows already sorted**. The table only draws the directional `▲`/`▼` arrow on
  the active header and emits `on_sort(col)` when a header is tapped.
- **Paginate** — the app holds `page`; when `page_size` is set the table
  **slices** `rows[page*page_size : …]` for display, draws a pager row
  (prev / next + `"page X / Y"`), and emits `on_page(page)` on prev/next.

!!! danger "The table doesn't sort or slice your data — you do"
    `on_sort(col)` is a **request**, not an action. The table never reorders `rows`
    itself; it tells you which column was tapped and **you** re-sort the list and
    rebuild. Passing unsorted `rows` with a `sort_column` set just draws the arrow
    in the wrong place — the data stays in the order you gave it. The same rule
    applies to pagination: the table slices the current page, but it's your
    `on_page` that moves `page`.

### Sort: how a header becomes a button

When you wire `on_sort`, each header becomes a tappable `Button` and the label
gains an indicator depending on state:

| Situation | Rendered label |
| --- | --- |
| Column is the sorted one (`sort_column == index`), ascending | `Name ▲` |
| Column is the sorted one, descending | `Name ▼` |
| `on_sort` wired, column inactive | `Name ↕` |
| `sortable=True` with no `on_sort` (legacy mode) | `Name ▾` |
| None of the above | `Name` |

!!! note "`sortable=True` is the legacy mode"
    `DataTable(sortable=True)` with no `on_sort` keeps the old "annotate every
    header with a sort glyph" behavior (`▾`), but the headers are **not** tappable.
    For real interactive sorting, wire `on_sort` — then the table draws
    `↕`/`▲`/`▼` and emits the tapped column index.

### Pagination: the current page slice

Setting `page_size` makes the table project only the current page's slice and
draw a `‹ Prev` / `Next ›` pager with a `page X / Y` label in the center. The
prev/next targets come **clamped** to `[0, last page]`, so the pager never leaves
the range:

```python
from tempest_core import DataTable

paged = DataTable(
    columns=["Name", "Age"],
    rows=[["Ana", "42"], ["Bruno", "17"], ["Carla", "88"], ["Diego", "5"]],
    page=0,
    page_size=2,  # two rows per page → 2 pages
    on_page=lambda p: None,  # swap for your re-render
)
```

!!! tip "The zebra is continuous across pages"
    The zebra stripe follows the **absolute** row index (`page*page_size + i`), not
    the position within the slice. So the even/odd parity doesn't restart each page
    — the second page continues the stripe where the first left off, keeping the
    pattern visually stable as you navigate.

### End-to-end example

Putting sort and pagination together, the app holds a little state, sorts the
data, and rebuilds the table on every change — the table is always a pure
function of that state:

```python
from typing import Any

from tempest_core import DataTable

# The app owns the state — the table is just a projection of it.
state: dict[str, Any] = {"sort_column": 0, "sort_ascending": True, "page": 0}

data: list[list[str]] = [
    ["Ana", "42"],
    ["Bruno", "17"],
    ["Carla", "88"],
    ["Diego", "5"],
]


def sorted_rows() -> list[list[str]]:
    """Return the rows sorted by the app's active column and direction."""
    col: int = state["sort_column"]
    return sorted(data, key=lambda row: row[col], reverse=not state["sort_ascending"])


def on_sort(col: int) -> None:
    """Toggle direction when re-tapping the active column, else sort it ascending."""
    if state["sort_column"] == col:
        state["sort_ascending"] = not state["sort_ascending"]
    else:
        state["sort_column"] = col
        state["sort_ascending"] = True
    app.rebuild()  # (1)!


def on_page(page: int) -> None:
    """Move to the requested (already clamped) page index."""
    state["page"] = page
    app.rebuild()


def build() -> DataTable:
    """Build the table as a pure projection of the current app state."""
    return DataTable(
        columns=["Name", "Age"],
        rows=sorted_rows(),  # the app passes rows already sorted
        sort_column=state["sort_column"],
        sort_ascending=state["sort_ascending"],
        on_sort=on_sort,
        page=state["page"],
        page_size=2,
        on_page=on_page,
    )
```

1. `app.rebuild()` stands for your framework's re-render — the trigger that
   rebuilds the tree from the new state (see [API reference](../reference.md)).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `columns` | `list[str]` | `[]` | The column header labels. |
| `rows` | `list[list[str]]` | `[]` | The body rows as a matrix of string cells (the app pre-sorts them). |
| `sortable` | `bool` | `False` | Whether headers carry a sort affordance (legacy glyph when no `on_sort` is wired). |
| `sort_column` | `int \| None` | `None` | The index of the column the rows are sorted by, or `None` for no active sort. |
| `sort_ascending` | `bool` | `True` | Whether the active sort is ascending (`▲`) or descending (`▼`). |
| `on_sort` | `Callable[[int], Any] \| None` | `None` | Called with the tapped column index to request a sort change. |
| `page` | `int` | `0` | The current zero-based page index, used when `page_size` is set. |
| `page_size` | `int \| None` | `None` | Rows shown per page; `None` shows every row (no pager). |
| `on_page` | `Callable[[int], Any] \| None` | `None` | Called with the requested zero-based page index on prev/next. |
| `theme` | `Theme` | `Theme()` | The design-system theme whose tokens supply the colors. |
| `style` | `Style \| None` | `None` | A `Style` overlaid on the table's default `SURFACE` background. |

!!! note "Colors by token, no hard-coded hexes"
    `DataTable` derives **every** color from the `theme`: the header fill from
    `SURFACE_VARIANT`, the text from `ON_SURFACE`, the divider from
    `OUTLINE_VARIANT`, and the zebra from `SURFACE_VARIANT` blended halfway toward
    `SURFACE` (the token model has no dedicated `SURFACE_CONTAINER` role, so the
    blend is deterministic). Swap the `theme` and the whole table re-skins itself.

## Recap

- **Two tables, opposite problems**: `Table` is a **static** hand-built grid;
  `DataTable` is a **themed**, interactive string matrix.
- **`Table`** is made of `TableRow`s of `TableCell`s; `headers` become an
  emphasised first row and every cell grows equally.
- **`TableCell` / `TableRow`** are `frozen` values; `colspan`/`rowspan` are
  informational for now, and the row `style` is **merged** on top of the default
  divider.
- **`DataTable` owns no state** — like the lists, the **app** holds `sort_column`
  / `sort_ascending` / `page` and passes the `rows` **already sorted**.
- **Sort**: wiring `on_sort` turns headers into buttons and draws `↕`/`▲`/`▼`;
  `sortable=True` alone is just the legacy `▾` glyph.
- **Paginate**: `page_size` slices the current page, draws a range-clamped
  prev/next pager, and keeps the zebra continuous across pages.
