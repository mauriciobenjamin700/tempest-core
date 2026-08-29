r"""Tabular components: ``Table`` and ``DataTable``.

Both are :class:`Component`\s that lower to a primitive ``Column`` of ``Row``s of
``Container``/``Text`` cells, so they render identically in the Qt simulator and
on the Compose device with zero renderer changes. ``Table`` is a static
rows-by-columns grid built from typed :class:`TableRow`/:class:`TableCell`
values.

With Trilho H6, ``DataTable`` becomes a **styled, themed** data display: it reads
its header / zebra / divider colors from the design-system :class:`~tempest_core.
theme.Theme` tokens (no hard-coded hexes), and gains app-driven **sort** and
**pagination** affordances. Following the E1 list pattern, the component owns **no
state**: the application holds ``sort_column`` / ``sort_ascending`` / ``page`` and
passes already-sorted ``rows``; the component projects the current page slice,
draws the directional sort arrow on the active header, renders tappable header
cells (emitting ``on_sort(col)``) and an optional pager row (emitting
``on_page(page)``). Every existing ``DataTable(columns=…, rows=…)`` /
``DataTable(sortable=True)`` call site keeps working — the H6 props are additive.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from tempest_core._model import _CoreModel
from tempest_core.components.base import (
    MUTED,
    ON_MUTED,
    ON_SURFACE,
    SURFACE,
    merge_style,
)
from tempest_core.style import (
    AlignItems,
    Border,
    Edge,
    FontWeight,
    SideBorder,
    Style,
    TextAlign,
)
from tempest_core.theme import Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.widgets import Button, Column, Component, Container, Row, Text, Widget

__all__ = ["TableCell", "TableRow", "Table", "DataTable"]

_CELL_PADDING: Edge = Edge.symmetric(vertical=8.0, horizontal=12.0)
_ROW_DIVIDER: SideBorder = SideBorder(bottom=Border(width=1.0, color=MUTED))


def _no_cells() -> list[TableCell]:
    """Provide a fresh, typed empty cell list for default factories.

    Returns:
        A new empty list of table cells.
    """
    return []


def _no_rows() -> list[TableRow]:
    """Provide a fresh, typed empty row list for default factories.

    Returns:
        A new empty list of table rows.
    """
    return []


def _no_str_rows() -> list[list[str]]:
    """Provide a fresh, typed empty string-matrix for default factories.

    Returns:
        A new empty list of string rows.
    """
    return []


def _no_str() -> list[str]:
    """Provide a fresh, typed empty string list for default factories.

    Returns:
        A new empty list of strings.
    """
    return []


class TableCell(_CoreModel):
    """A single cell of a :class:`Table`.

    Attributes:
        content: The cell's text content.
        colspan: How many columns the cell spans (currently informational; the
            primitive lowering renders one cell per entry).
        rowspan: How many rows the cell spans (currently informational).
        style: An optional style overlaid on the cell's default padding/text.
    """

    model_config = ConfigDict(frozen=True)

    content: str = Field(description="The cell's text content.")
    colspan: int = Field(
        default=1,
        description="How many columns the cell spans (currently informational; the "
        "primitive lowering renders one cell per entry).",
    )
    rowspan: int = Field(
        default=1, description="How many rows the cell spans (currently informational)."
    )
    style: Style | None = None


class TableRow(_CoreModel):
    """A single row of a :class:`Table`.

    Attributes:
        cells: The ordered cells of the row.
        style: An optional style overlaid on the row's default layout.
    """

    model_config = ConfigDict(frozen=True)

    cells: list[TableCell] = Field(
        description="The ordered cells of the row.", default_factory=_no_cells
    )
    style: Style | None = None


class Table(Component):
    r"""A static data table laid out as rows of equal-width cells.

    Attributes:
        rows: The body rows, each a :class:`TableRow` of :class:`TableCell`\s.
        headers: Optional header labels rendered as an emphasised first row.
        style: An optional style overlaid on the table's default surface.
    """

    default_key: ClassVar[str] = "table"

    rows: list[TableRow] = Field(
        description="The body rows, each a :class:`TableRow` of :class:`TableCell`\\s.",
        default_factory=_no_rows,
    )
    headers: list[str] = Field(
        description="Optional header labels rendered as an emphasised first row.",
        default_factory=_no_str,
    )
    style: Style | None = None

    def _cell(self, content: str, *, header: bool, key: str) -> Widget:
        """Build one primitive cell wrapped in a growing container.

        Args:
            content: The cell text.
            header: Whether the cell belongs to the header row.
            key: A stable key for the cell container.

        Returns:
            A growing ``Container`` wrapping the cell's ``Text``.
        """
        text_style = Style(
            color=ON_SURFACE if header else ON_MUTED,
            font_weight=FontWeight.BOLD if header else FontWeight.NORMAL,
        )
        return Container(
            key=key,
            style=Style(grow=1.0, padding=_CELL_PADDING),
            child=Text(content=content, style=text_style),
        )

    def render(self) -> Widget:
        """Lower the table into a primitive column of rows.

        Returns:
            A ``Column`` of ``Row``s; each row carries a bottom divider and each
            cell grows to share the row width evenly.
        """
        body: list[Widget] = []
        if self.headers:
            body.append(
                Row(
                    key=self.child_key("header"),
                    style=Style(border=_ROW_DIVIDER, background=SURFACE),
                    children=[
                        self._cell(text, header=True, key=self.child_key(f"th-{index}"))
                        for index, text in enumerate(self.headers)
                    ],
                )
            )
        for r_index, row in enumerate(self.rows):
            default_row = Style(border=_ROW_DIVIDER)
            body.append(
                Row(
                    key=self.child_key(f"row-{r_index}"),
                    style=merge_style(default_row, row.style),
                    children=[
                        self._cell(
                            cell.content,
                            header=False,
                            key=self.child_key(f"td-{r_index}-{c_index}"),
                        )
                        for c_index, cell in enumerate(row.cells)
                    ],
                )
            )
        default = Style(background=SURFACE)
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=body,
        )


class DataTable(Component):
    """A themed string-matrix table with app-driven sort and pagination.

    A styled convenience over the common header-plus-string-matrix case. With
    Trilho H6 it reads its colors from the :class:`~tempest_core.theme.Theme`
    tokens (header fill ``SURFACE_VARIANT`` / ``ON_SURFACE``, body ``SURFACE`` /
    ``ON_SURFACE`` with a subtle zebra stripe derived from ``SURFACE_VARIANT``,
    row divider ``OUTLINE_VARIANT``) and offers sortable, tappable headers and an
    optional pager.

    The component owns **no state** (mirroring the E1 virtualized-list pattern):

    * **Sort** — the application holds ``sort_column`` / ``sort_ascending``,
      passes the rows already sorted, and the table only draws the directional
      ▲/▼ arrow on the active header and emits ``on_sort(col)`` when a header is
      tapped.
    * **Paginate** — the application holds the current ``page``; when
      ``page_size`` is set the table slices ``rows[page*page_size : …]`` for
      display, renders a pager row (prev / next + ``"page X/Y"``), and emits
      ``on_page(page)`` for prev/next.

    Backward-compatible: ``DataTable(columns=…, rows=…)`` is a plain themed table;
    ``DataTable(sortable=True)`` keeps the legacy "annotate every header with a
    sort glyph" behavior when no ``on_sort`` is wired.

    Attributes:
        columns: The column header labels.
        rows: The body rows as a matrix of string cells (the app pre-sorts them).
        sortable: Whether headers carry a sort affordance (legacy glyph when no
            ``on_sort`` is wired).
        sort_column: The index of the column the rows are currently sorted by, or
            ``None`` for no active sort.
        sort_ascending: Whether the active sort is ascending (``▲``) or
            descending (``▼``).
        on_sort: Called with the tapped column index to request a sort change.
        page: The current zero-based page index (used when ``page_size`` is set).
        page_size: The number of rows shown per page; ``None`` shows every row
            (no pager).
        on_page: Called with the requested zero-based page index on prev/next.
        theme: The design-system theme whose tokens supply the colors.
        style: An optional style overlaid on the table's default surface.
    """

    default_key: ClassVar[str] = "data-table"

    columns: list[str] = Field(
        description="The column header labels.", default_factory=_no_str
    )
    rows: list[list[str]] = Field(
        description="The body rows as a matrix of string cells.",
        default_factory=_no_str_rows,
    )
    sortable: bool = Field(
        default=False,
        description="Whether headers carry a sort affordance (legacy glyph when no "
        "``on_sort`` is wired).",
    )
    sort_column: int | None = Field(
        default=None,
        description="The index of the column the rows are currently sorted by.",
    )
    sort_ascending: bool = Field(
        default=True,
        description="Whether the active sort is ascending (``▲``) or descending "
        "(``▼``).",
    )
    on_sort: Callable[[int], Any] | None = Field(
        default=None,
        description="Called with the tapped column index to request a sort change.",
    )
    page: int = Field(default=0, description="The current zero-based page index.")
    page_size: int | None = Field(
        default=None,
        description="The number of rows shown per page; ``None`` shows every row.",
    )
    on_page: Callable[[int], Any] | None = Field(
        default=None,
        description="Called with the requested zero-based page index on prev/next.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply the colors.",
    )
    style: Style | None = None

    def _header_label(self, index: int, label: str) -> str:
        """Compute a header label with its sort indicator.

        Args:
            index: The column index.
            label: The raw column label.

        Returns:
            The label suffixed with ``▲``/``▼`` when it is the active sort column,
            a neutral ``↕`` when sortable-without-active-sort, the legacy ``▾``
            for the no-``on_sort`` legacy mode, or the bare label.
        """
        if self.sort_column == index:
            return f"{label} {'▲' if self.sort_ascending else '▼'}"
        if self.on_sort is not None:
            return f"{label} ↕"
        if self.sortable:
            return f"{label} ▾"
        return label

    def _header_cell(self, index: int, label: str) -> Widget:
        """Build one header cell — a tappable button when ``on_sort`` is wired.

        Args:
            index: The column index.
            label: The raw column label.

        Returns:
            A growing header ``Button`` (when sortable via ``on_sort``) or a plain
            header ``Text`` cell.
        """
        text = self._header_label(index, label)
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        if self.on_sort is not None:
            handler = self.on_sort
            return Button(
                label=text,
                on_click=lambda col=index: handler(col),
                key=self.child_key(f"th-{index}"),
                style=Style(
                    grow=1.0,
                    padding=_CELL_PADDING,
                    background=self.theme.color(ColorRole.SURFACE_VARIANT),
                    color=on_surface,
                    font_weight=FontWeight.BOLD,
                    text_align=TextAlign.LEFT,
                ),
            )
        return Container(
            key=self.child_key(f"th-{index}"),
            style=Style(grow=1.0, padding=_CELL_PADDING),
            child=Text(
                content=text,
                style=Style(color=on_surface, font_weight=FontWeight.BOLD),
            ),
        )

    def _body_cell(self, r_index: int, c_index: int, content: str) -> Widget:
        """Build one body cell.

        Args:
            r_index: The displayed row index (for keying).
            c_index: The column index (for keying).
            content: The cell text.

        Returns:
            A growing ``Container`` wrapping the cell ``Text`` in ``ON_SURFACE``.
        """
        return Container(
            key=self.child_key(f"td-{r_index}-{c_index}"),
            style=Style(grow=1.0, padding=_CELL_PADDING),
            child=Text(
                content=content,
                style=Style(color=self.theme.color(ColorRole.ON_SURFACE)),
            ),
        )

    def _page_rows(self) -> list[list[str]]:
        """Project the rows to the current page slice.

        Returns:
            ``rows[page*page_size : (page+1)*page_size]`` when ``page_size`` is
            set, otherwise every row.
        """
        if self.page_size is None:
            return self.rows
        start = self.page * self.page_size
        return self.rows[start : start + self.page_size]

    def _page_count(self) -> int:
        """Compute the total number of pages.

        Returns:
            The ceil-divided page count (at least ``1``), or ``1`` when
            ``page_size`` is unset.
        """
        if self.page_size is None or self.page_size <= 0:
            return 1
        return max(1, (len(self.rows) + self.page_size - 1) // self.page_size)

    def _pager(self) -> Widget:
        """Build the prev/next pager row.

        Returns:
            A ``Row`` of a prev ``Button``, a centered ``"page X / Y"`` label and
            a next ``Button``; prev/next emit ``on_page`` clamped to ``[0, last]``.
        """
        total = self._page_count()
        on_page = self.on_page
        current = self.page
        prev_target = max(0, current - 1)
        next_target = min(total - 1, current + 1)
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        return Row(
            key=self.child_key("pager"),
            style=Style(
                gap=self.theme.space("sm"),
                align=AlignItems.CENTER,
                padding=Edge.symmetric(
                    vertical=self.theme.space("xs"), horizontal=self.theme.space("md")
                ),
            ),
            children=[
                Button(
                    label="‹ Prev",
                    on_click=(lambda t=prev_target: on_page(t))
                    if on_page is not None
                    else None,
                    key=self.child_key("prev"),
                ),
                Text(
                    content=f"page {current + 1} / {total}",
                    style=Style(grow=1.0, color=muted, text_align=TextAlign.CENTER),
                    key=self.child_key("page-label"),
                ),
                Button(
                    label="Next ›",
                    on_click=(lambda t=next_target: on_page(t))
                    if on_page is not None
                    else None,
                    key=self.child_key("next"),
                ),
            ],
        )

    def render(self) -> Widget:
        """Lower the data table into a themed column of header + body rows.

        Returns:
            A ``Column`` of a header row, the current page's body rows (with a
            zebra stripe and a bottom divider each) and, when paginated, a pager
            row.

        Note:
            The zebra stripe is ``SURFACE_VARIANT`` mixed halfway toward
            ``SURFACE``, since the token model has no dedicated
            ``SURFACE_CONTAINER`` role and H6 adds no new token — deterministic,
            so the conformance suite pins it. Its parity follows the *absolute*
            row index, so stripes stay continuous across pages instead of
            restarting on each page slice.
        """
        divider = SideBorder(
            bottom=Border(width=1.0, color=self.theme.color(ColorRole.OUTLINE_VARIANT))
        )
        surface = self.theme.color(ColorRole.SURFACE)
        zebra = self.theme.color(ColorRole.SURFACE_VARIANT).blend(surface, 0.5)
        body: list[Widget] = []
        if self.columns:
            body.append(
                Row(
                    key=self.child_key("header"),
                    style=Style(
                        border=divider,
                        background=self.theme.color(ColorRole.SURFACE_VARIANT),
                    ),
                    children=[
                        self._header_cell(index, label)
                        for index, label in enumerate(self.columns)
                    ],
                )
            )
        row_offset = self.page * self.page_size if self.page_size else 0
        for r_index, row in enumerate(self._page_rows()):
            stripe = zebra if (row_offset + r_index) % 2 == 1 else surface
            body.append(
                Row(
                    key=self.child_key(f"row-{r_index}"),
                    style=Style(border=divider, background=stripe),
                    children=[
                        self._body_cell(r_index, c_index, value)
                        for c_index, value in enumerate(row)
                    ],
                )
            )
        if self.page_size is not None:
            body.append(self._pager())
        default = Style(background=surface)
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=body,
        )
