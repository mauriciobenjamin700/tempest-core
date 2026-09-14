"""Two layout defects that only show up with real data, on a real viewport.

``DataTable`` had no grid: every row was an independent flex line whose cells
sized themselves from their own text, so the columns lined up only while every
value happened to be about as wide as the one above it. Measured in Chrome at
1440px, one long value pushed the following columns of *that row* by up to 175px
(tempestweb#214).

``AppBar`` laid its title and actions out on one non-wrapping row, with the title
taking all the slack. Measured at 320px, the right edge of the actions landed at
x=341: the last action was off-screen and the page gained a horizontal scrollbar
(tempestweb#215).

Both are fixed in the core rather than worked around per renderer, because the
core is what both tempestweb and tempestroid render.
"""

from __future__ import annotations

import pytest

from tempest_core import (
    Button,
    MediaQueryData,
    Node,
    Style,
    Theme,
    build,
)
from tempest_core.components import DataTable
from tempest_core.components.bars import AppBar
from tempest_core.components.table import Table, TableCell, TableRow
from tempest_core.style import FlexDirection, FlexWrap

COLUMNS: list[str] = ["Nome", "Tipo", "Porta local", "Status"]
ROWS: list[list[str]] = [
    ["api", "http", "8000", "ok"],
    ["web", "http", "3000", "ok"],
    ["grafana-com-nome-bem-longo-para-testar-overflow", "http", "3001", "degradado"],
]


def _walk(node: Node) -> list[Node]:
    """Flatten a built node tree, depth first.

    Args:
        node: The root node.

    Returns:
        Every node in the subtree, the root first.
    """
    found = [node]
    for child in node.children:
        found.extend(_walk(child))
    return found


def _style_of(node: Node, key: str) -> Style:
    """Read the inline style of the node carrying ``key``.

    Args:
        node: The built root node.
        key: The key of the node to read.

    Returns:
        That node's ``Style``.
    """
    match = next(found for found in _walk(node) if found.key == key)
    style = match.props["style"]
    assert isinstance(style, Style)
    return style


def test_data_table_columns_share_one_base_width() -> None:
    """Header and every row start column ``c`` from the same width.

    This is the property that makes the columns line up. Before the fix each cell
    was ``grow=1.0`` with no width, so its base was its own text and the column
    drifted per row.
    """
    node = build(DataTable(columns=COLUMNS, rows=ROWS))

    for column in range(len(COLUMNS)):
        widths = {_style_of(node, f"data-table-th-{column}").width} | {
            _style_of(node, f"data-table-td-{row}-{column}").width
            for row in range(len(ROWS))
        }
        assert len(widths) == 1, f"column {column} has drifting bases: {widths}"
        assert widths.pop() is not None


def test_a_long_value_widens_its_own_column_not_the_next_one() -> None:
    """The long name column is wider; the columns after it are unmoved.

    The issue's own reproduction: a 47-character value used to steal the slack of
    the columns to its right, in its row only. Columns 1 and 2 carry the same
    strings in both tables, so their track has to be identical; column 3 is left
    out on purpose — its longest value really does differ between the two.
    """
    node = build(DataTable(columns=COLUMNS, rows=ROWS))
    short = build(DataTable(columns=COLUMNS, rows=[["api", "http", "8000", "ok"]]))

    assert _style_of(node, "data-table-th-0").width is not None
    long_first = _style_of(node, "data-table-th-0").width
    short_first = _style_of(short, "data-table-th-0").width
    assert long_first is not None and short_first is not None
    assert long_first > short_first

    for column in (1, 2):
        assert (
            _style_of(node, f"data-table-th-{column}").width
            == _style_of(short, f"data-table-th-{column}").width
        )


def test_static_table_shares_the_track_too() -> None:
    """``Table`` gets the same treatment — it had the same defect."""
    table = Table(
        headers=COLUMNS,
        rows=[
            TableRow(cells=[TableCell(content=value) for value in row]) for row in ROWS
        ],
    )
    node = build(table)

    for column in range(len(COLUMNS)):
        widths = {_style_of(node, f"table-th-{column}").width} | {
            _style_of(node, f"table-td-{row}-{column}").width
            for row in range(len(ROWS))
        }
        assert len(widths) == 1


def test_the_track_still_lets_cells_grow() -> None:
    """The base is a starting point, not a cage: ``grow`` survives.

    A table narrower than its container still fills it, which is what the
    previous ``grow=1.0``-only layout got right.
    """
    node = build(DataTable(columns=COLUMNS, rows=ROWS))
    assert _style_of(node, "data-table-td-0-0").grow == 1.0


def test_an_empty_table_builds() -> None:
    """No columns and no rows means no track, and no crash."""
    assert build(DataTable(columns=[], rows=[])) is not None
    assert build(Table()) is not None


def test_a_ragged_row_does_not_break_the_track() -> None:
    """A row shorter than the header keeps building — rows are not validated."""
    node = build(DataTable(columns=COLUMNS, rows=[["api", "http"]]))
    assert _style_of(node, "data-table-td-0-1").width is not None


def test_app_bar_actions_wrap() -> None:
    """The actions row wraps, so a wide set of actions cannot overflow."""
    node = build(AppBar(title="tempest-webtunnel", actions=[Button(label="Sair")]))
    assert _style_of(node, "appbar-actions").flex_wrap is FlexWrap.WRAP


@pytest.mark.parametrize("width", [305.0, 320.0, 390.0])
def test_app_bar_stacks_below_the_md_breakpoint(width: float) -> None:
    """Narrow viewport: the bar becomes a column, and the title stops grabbing.

    Args:
        width: The reported viewport width, all below the ``md`` breakpoint.
    """
    bar = AppBar(
        title="tempest-webtunnel",
        actions=[Button(label="Atualizar"), Button(label="Sair")],
        media=MediaQueryData(width=width, height=800.0),
    )
    node = build(bar)

    assert _style_of(node, "appbar").direction is FlexDirection.COLUMN
    assert _style_of(node, "appbar-title").grow is None


@pytest.mark.parametrize("width", [640.0, 1024.0, 1440.0])
def test_app_bar_stays_a_row_above_the_breakpoint(width: float) -> None:
    """Wide viewport: nothing changes — the title still takes the slack.

    Args:
        width: The reported viewport width, all at or above the breakpoint.
    """
    bar = AppBar(
        title="tempest-webtunnel",
        actions=[Button(label="Sair")],
        media=MediaQueryData(width=width, height=800.0),
    )
    node = build(bar)

    assert _style_of(node, "appbar").direction is None
    assert _style_of(node, "appbar-title").grow == 1.0


def test_app_bar_without_media_keeps_the_row() -> None:
    """No viewport report means no responsive decision to make.

    ``MediaQueryData`` defaults ``width`` to ``0.0``, which is "not reported yet",
    not "zero pixels wide" — stacking on it would make every bar built before the
    first report jump.
    """
    assert _style_of(build(AppBar(title="X")), "appbar").direction is None
    unreported = AppBar(title="X", media=MediaQueryData())
    assert _style_of(build(unreported), "appbar").direction is None


def test_app_bar_breakpoint_comes_from_the_theme() -> None:
    """A theme with a different ``md`` moves the threshold with it."""
    theme = Theme()
    wide = theme.model_copy(
        update={
            "tokens": theme.tokens.model_copy(
                update={
                    "breakpoints": theme.tokens.breakpoints.model_copy(
                        update={"md": 1200.0}
                    )
                }
            )
        }
    )
    bar = AppBar(
        title="X", media=MediaQueryData(width=1024.0, height=800.0), theme=wide
    )
    assert _style_of(build(bar), "appbar").direction is FlexDirection.COLUMN
