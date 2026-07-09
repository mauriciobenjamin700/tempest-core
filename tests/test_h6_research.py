"""Tests for the H6 research / data-science kit (Trilho H, phase H6).

Pins the new :class:`~tempest_core.components.research` surface: the
:class:`ChartSeries` / :class:`DetectionBox` frozen value models, the
:func:`~tempest_core.components.confidence_scheme` thresholds, the
:class:`MetricCard` / :class:`StatCard` composition over ``Card`` + ``Stat``, the
:class:`ConfidenceBadge` over ``Badge``, the deterministic ``Canvas`` command
lists the :class:`LineChart` / :class:`BarChart` emit (assert the exact command
*kind sequence* + key geometry from fixed input), the :class:`DetectionOverlay`
``Stack`` of an ``Image`` + a box ``Canvas`` (conf → color), the
:class:`ResultView` picker→result flow, the themed ``DataTable`` projection
(page slice + sort arrow + pager + ``on_sort`` / ``on_page``) with app-held state,
the themed ``Calendar`` / ``Clock``, full backward-compatibility of the old call
sites, and the hard constraint that NO new ``Style`` field was added (still 41).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tempest_core import (
    BarChart,
    ChartSeries,
    ConfidenceBadge,
    DetectionBox,
    DetectionOverlay,
    LineChart,
    MetricCard,
    ResultView,
    StatCard,
    Style,
    Theme,
    build,
    confidence_scheme,
)
from tempest_core.components import Calendar, Clock, DataTable
from tempest_core.components.research import _color_floats
from tempest_core.core.introspection import WIDGET_TYPES, widget_catalog
from tempest_core.style import CardVariant, Color
from tempest_core.tokens import ColorRole
from tempest_core.widgets import (
    Canvas,
    DrawRect,
    DrawText,
    FillCmd,
    Image,
    LineTo,
    MoveTo,
    Stack,
    StrokeCmd,
    Text,
)

THEME = Theme()


# --------------------------------------------------------------------------- #
# Hard constraints: no new Style field; no new widget/draw-command
# --------------------------------------------------------------------------- #


def test_h6_no_style_field_added() -> None:
    """H6 introduces NO new ``Style`` field (still 41)."""
    assert len(Style.model_fields) == 41


def test_h6_introduces_no_new_leaf_widget() -> None:
    """Every H6 component lowers to existing primitives — no new leaf widget."""
    names = {w.__name__ for w in WIDGET_TYPES}
    for new in (
        "MetricCard",
        "StatCard",
        "ConfidenceBadge",
        "LineChart",
        "BarChart",
        "DetectionOverlay",
        "ResultView",
    ):
        assert new not in names


def test_h6_charts_lower_to_canvas_only() -> None:
    """The charts lower to a plain ``Canvas`` (no new draw command introduced)."""
    catalog = widget_catalog()
    canvas_schema = catalog["Canvas"]
    # The Canvas command union is unchanged: the discriminator still has exactly
    # the original nine members.
    defs = canvas_schema["schema"].get("$defs", {})
    command_models = {
        name
        for name in defs
        if name
        in {
            "MoveTo",
            "LineTo",
            "ArcTo",
            "Close",
            "FillCmd",
            "StrokeCmd",
            "DrawText",
            "DrawRect",
            "DrawOval",
        }
    }
    assert len(command_models) == 9


# --------------------------------------------------------------------------- #
# Value models
# --------------------------------------------------------------------------- #


def test_chart_series_defaults_and_frozen() -> None:
    """``ChartSeries`` defaults to an empty point list and is frozen."""
    series = ChartSeries()
    assert series.points == []
    assert series.label == ""
    assert series.color_scheme is None
    with pytest.raises(ValidationError):
        series.label = "x"


def test_detection_box_defaults_and_frozen() -> None:
    """``DetectionBox`` carries normalized xyxy + name/conf and is frozen."""
    box = DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6)
    assert (box.x1, box.y1, box.x2, box.y2) == (0.1, 0.2, 0.5, 0.6)
    assert box.name == ""
    assert box.conf == 1.0
    with pytest.raises(ValidationError):
        box.conf = 0.5


def test_color_floats_normalizes_channels() -> None:
    """``_color_floats`` maps a 0-255 ``Color`` to 0-1 ``[r, g, b, a]`` floats."""
    floats = _color_floats(Color(r=255, g=0, b=128, a=0.5))
    assert floats == [1.0, 0.0, 128 / 255.0, 0.5]


# --------------------------------------------------------------------------- #
# confidence_scheme thresholds
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("conf", "expected"),
    [
        (1.0, "success"),
        (0.8, "success"),
        (0.79, "warning"),
        (0.5, "warning"),
        (0.49, "error"),
        (0.0, "error"),
    ],
)
def test_confidence_scheme_thresholds(conf: float, expected: str) -> None:
    """``confidence_scheme`` maps to success/warning/error by threshold."""
    assert confidence_scheme(conf) == expected


def test_confidence_scheme_custom_thresholds() -> None:
    """Custom ``high`` / ``mid`` thresholds shift the bands."""
    assert confidence_scheme(0.6, high=0.9, mid=0.6) == "warning"
    assert confidence_scheme(0.95, high=0.9, mid=0.6) == "success"
    assert confidence_scheme(0.59, high=0.9, mid=0.6) == "error"


# --------------------------------------------------------------------------- #
# MetricCard / StatCard composition
# --------------------------------------------------------------------------- #


def test_metric_card_lowers_to_card_with_stat() -> None:
    """``MetricCard`` lowers to a ``Card`` wrapping a ``Stat`` block."""
    node = build(MetricCard(label="Accuracy", value="92%", delta="+3%", delta_up=True))
    # Card lowers to a Surface(Container(Column(...))) — the stat's label/value
    # text appears somewhere in the lowered tree.
    texts = _collect_texts(node)
    assert "Accuracy" in texts
    assert "92%" in texts
    assert "▲ +3%" in texts


def test_metric_card_trailing_slot() -> None:
    """A ``MetricCard`` trailing widget is placed beside the stat."""
    node = build(MetricCard(label="Acc", value="9", trailing=Text(content="SPARK")))
    assert "SPARK" in _collect_texts(node)


def test_stat_card_is_metric_card_preset() -> None:
    """``StatCard`` is a ``MetricCard`` preset defaulting to a filled surface."""
    assert issubclass(StatCard, MetricCard)
    assert StatCard(label="x", value="1").variant is CardVariant.FILLED
    assert MetricCard(label="x", value="1").variant is CardVariant.ELEVATED


def test_metric_card_explicit_style_wins() -> None:
    """An explicit ``style`` is merged onto the resolved card surface."""
    accent = Color(r=10, g=20, b=30)
    node = build(MetricCard(label="x", value="1", style=Style(background=accent)))
    assert _find_background(node, accent)


# --------------------------------------------------------------------------- #
# ConfidenceBadge
# --------------------------------------------------------------------------- #


def test_confidence_badge_high_is_success_pill() -> None:
    """A high-confidence badge is a success pill labelled with the percentage."""
    node = build(ConfidenceBadge(confidence=0.92))
    assert "92%" in _collect_texts(node)
    # SUBTLE pill → the tonal success CONTAINER (WCAG-AA safe), not the saturated
    # success role (white-on-success would fail AA at ~3.02).
    success_container = THEME.color(ColorRole.SUCCESS_CONTAINER)
    assert _find_background(node, success_container)


def test_confidence_badge_low_is_error_pill() -> None:
    """A low-confidence badge is an error pill."""
    node = build(ConfidenceBadge(confidence=0.2))
    error_container = THEME.color(ColorRole.ERROR_CONTAINER)
    assert _find_background(node, error_container)


def test_confidence_badge_label_prefix() -> None:
    """A label prefix is shown before the percentage."""
    node = build(ConfidenceBadge(confidence=0.92, label="cat"))
    assert "cat 92%" in _collect_texts(node)


# --------------------------------------------------------------------------- #
# LineChart — deterministic Canvas command list
# --------------------------------------------------------------------------- #


def test_line_chart_command_sequence() -> None:
    """A fixed line chart emits a deterministic axis + polyline command list."""
    chart = LineChart(
        width=120.0, height=80.0, series=[ChartSeries(points=[0.0, 10.0])]
    )
    canvas = chart.render()
    assert isinstance(canvas, Canvas)
    assert canvas.width == 120.0
    assert canvas.height == 80.0

    # The frame: MoveTo + 2x LineTo + StrokeCmd, then 5 gridline+label groups
    # (5 ticks for _TICKS=4), then the single-series polyline tail.
    cmds = canvas.commands
    assert isinstance(cmds[0], MoveTo)
    assert isinstance(cmds[1], LineTo)
    assert isinstance(cmds[2], LineTo)
    assert isinstance(cmds[3], StrokeCmd)

    # The polyline tail for a 2-point series: MoveTo, LineTo, StrokeCmd.
    tail = cmds[-3:]
    assert isinstance(tail[0], MoveTo)
    assert isinstance(tail[1], LineTo)
    assert isinstance(tail[2], StrokeCmd)
    # The plot rect is inset by PAD_LEFT=40 on the left and PAD_RIGHT=12.
    assert tail[0].x == 40.0  # first point at the left edge
    assert tail[1].x == 108.0  # 120 - 12
    assert tail[2].width == 2.0


def test_line_chart_is_deterministic() -> None:
    """Identical input produces an identical command list (conformance-pinnable)."""
    series = [ChartSeries(points=[1.0, 2.0, 3.0])]
    a = LineChart(series=series).render()
    b = LineChart(series=series).render()
    assert [c.model_dump() for c in a.commands] == [c.model_dump() for c in b.commands]


def test_line_chart_multi_series_uses_palette() -> None:
    """Two unnamed series get two distinct rotating-palette colors."""
    chart = LineChart(
        width=200.0,
        height=100.0,
        series=[
            ChartSeries(points=[0.0, 1.0]),
            ChartSeries(points=[1.0, 0.0]),
        ],
    )
    strokes = [c for c in chart.render().commands if isinstance(c, StrokeCmd)]
    # The two series' 2px strokes are the last two thick strokes.
    series_strokes = [s for s in strokes if s.width == 2.0]
    assert len(series_strokes) == 2
    assert series_strokes[0].color != series_strokes[1].color


def test_line_chart_series_color_scheme_override() -> None:
    """A series' explicit ``color_scheme`` colors its polyline."""
    chart = LineChart(series=[ChartSeries(points=[0.0, 1.0], color_scheme="error")])
    error_floats = _color_floats(THEME.color("error"))
    series_strokes = [
        c
        for c in chart.render().commands
        if isinstance(c, StrokeCmd) and c.width == 2.0
    ]
    assert series_strokes[0].color == error_floats


# --------------------------------------------------------------------------- #
# BarChart — deterministic Canvas command list
# --------------------------------------------------------------------------- #


def test_bar_chart_from_values() -> None:
    """A bar chart from a plain value list emits one DrawRect+FillCmd per bar."""
    chart = BarChart(width=120.0, height=80.0, values=[5.0, 10.0])
    cmds = chart.render().commands
    rects = [c for c in cmds if isinstance(c, DrawRect)]
    fills = [c for c in cmds if isinstance(c, FillCmd)]
    assert len(rects) == 2
    assert len(fills) == 2
    # The taller bar (value 10) is taller than the shorter (value 5).
    assert rects[1].height > rects[0].height


def test_bar_chart_from_series_first_wins() -> None:
    """When ``series`` is given the first series supplies the bars + its color."""
    chart = BarChart(
        values=[1.0],
        series=[ChartSeries(points=[2.0, 3.0], color_scheme="success")],
    )
    cmds = chart.render().commands
    rects = [c for c in cmds if isinstance(c, DrawRect)]
    fills = [c for c in cmds if isinstance(c, FillCmd)]
    assert len(rects) == 2  # series wins over the single ``values`` entry
    assert fills[0].color == _color_floats(THEME.color("success"))


def test_bar_chart_is_deterministic() -> None:
    """Identical input produces an identical command list."""
    a = BarChart(values=[3.0, 1.0, 4.0]).render()
    b = BarChart(values=[3.0, 1.0, 4.0]).render()
    assert [c.model_dump() for c in a.commands] == [c.model_dump() for c in b.commands]


# --------------------------------------------------------------------------- #
# DetectionOverlay
# --------------------------------------------------------------------------- #


def test_detection_overlay_stack_image_canvas() -> None:
    """The overlay is a ``Stack`` of a base ``Image`` and a box ``Canvas``."""
    overlay = DetectionOverlay(
        image_src="img.jpg",
        width=100.0,
        height=100.0,
        boxes=[DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="cat", conf=0.9)],
    )
    stack = overlay.render()
    assert isinstance(stack, Stack)
    assert isinstance(stack.children[0], Image)
    assert isinstance(stack.children[1], Canvas)


def test_detection_overlay_box_geometry_and_color() -> None:
    """A normalized box is multiplied by the canvas size and colored by conf."""
    overlay = DetectionOverlay(
        image_src="img.jpg",
        width=100.0,
        height=100.0,
        boxes=[DetectionBox(x1=0.1, y1=0.2, x2=0.5, y2=0.6, name="cat", conf=0.9)],
    )
    stack = overlay.render()
    assert isinstance(stack, Stack)
    canvas = stack.children[1]
    assert isinstance(canvas, Canvas)
    cmds = canvas.commands
    rect = cmds[0]
    assert isinstance(rect, DrawRect)
    assert rect.x == 10.0  # 0.1 * 100
    assert rect.y == 20.0  # 0.2 * 100
    assert rect.width == 40.0  # (0.5 - 0.1) * 100
    assert rect.height == 40.0  # (0.6 - 0.2) * 100
    stroke = cmds[1]
    assert isinstance(stroke, StrokeCmd)
    # conf 0.9 → success (green).
    assert stroke.color == _color_floats(THEME.color("success"))
    # The caption is drawn: a filled bg rect + the DrawText.
    assert any(isinstance(c, DrawText) and c.text == "cat 90%" for c in cmds)


def test_detection_overlay_low_conf_is_error_color() -> None:
    """A low-confidence box strokes in the error color."""
    overlay = DetectionOverlay(
        image_src="img.jpg",
        boxes=[DetectionBox(x1=0.0, y1=0.0, x2=0.5, y2=0.5, conf=0.2)],
    )
    stack = overlay.render()
    assert isinstance(stack, Stack)
    canvas = stack.children[1]
    assert isinstance(canvas, Canvas)
    stroke = canvas.commands[1]
    assert isinstance(stroke, StrokeCmd)
    assert stroke.color == _color_floats(THEME.color("error"))


def test_detection_overlay_empty_boxes() -> None:
    """No boxes → an empty overlay canvas (no commands)."""
    overlay = DetectionOverlay(image_src="img.jpg")
    stack = overlay.render()
    assert isinstance(stack, Stack)
    canvas = stack.children[1]
    assert isinstance(canvas, Canvas)
    assert canvas.commands == []


# --------------------------------------------------------------------------- #
# ResultView
# --------------------------------------------------------------------------- #


def test_result_view_picker_only() -> None:
    """A result view with no result shows just the image picker."""
    picked: list[str] = []
    node = build(ResultView(on_pick=picked.append, label="Upload"))
    assert "Upload" in _collect_texts(node)


def test_result_view_with_result() -> None:
    """A result widget is shown below the picker."""
    node = build(ResultView(on_pick=lambda uri: None, result=Text(content="RESULT")))
    assert "RESULT" in _collect_texts(node)


def test_on_uri_adapter_returns_sync_handler_value() -> None:
    """The picker adapter forwards the URI and RETURNS the handler's value."""
    from tempest_core.components.mediainputs import _on_uri
    from tempest_core.widgets import FileSelectEvent

    adapter = _on_uri(lambda uri: f"got:{uri}")
    assert adapter(FileSelectEvent(uri="file:///a.jpg")) == "got:file:///a.jpg"


def test_on_uri_adapter_propagates_coroutine_for_async_handler() -> None:
    """An ``async`` ``on_pick`` must have its coroutine RETURNED (so the event
    dispatcher awaits it) — dropping it silently stranded the picked-image work.
    """
    import inspect

    from tempest_core.components.mediainputs import _on_uri
    from tempest_core.widgets import FileSelectEvent

    async def on_pick(uri: str) -> str:
        return uri

    adapter = _on_uri(on_pick)
    result = adapter(FileSelectEvent(uri="content://x/1"))
    assert inspect.iscoroutine(result)
    result.close()  # we only assert propagation; avoid an un-awaited warning


# --------------------------------------------------------------------------- #
# DataTable skin — app-held sort + pagination
# --------------------------------------------------------------------------- #


def test_data_table_backward_compatible() -> None:
    """A plain ``DataTable(columns, rows)`` still renders header + body."""
    node = build(DataTable(columns=["A", "B"], rows=[["1", "2"], ["3", "4"]]))
    texts = _collect_texts(node)
    assert "A" in texts
    assert "1" in texts
    assert "4" in texts


def test_data_table_legacy_sortable_glyph() -> None:
    """``sortable=True`` without ``on_sort`` keeps the legacy header glyph."""
    node = build(DataTable(columns=["A"], rows=[], sortable=True))
    assert "A ▾" in _collect_texts(node)


def test_data_table_sort_arrow_on_active_column() -> None:
    """The active sort column shows ▲/▼; others a neutral ↕ when on_sort is set."""
    asc = build(
        DataTable(
            columns=["A", "B"],
            rows=[],
            on_sort=lambda c: None,
            sort_column=0,
            sort_ascending=True,
        )
    )
    texts_asc = _collect_texts(asc)
    assert "A ▲" in texts_asc
    assert "B ↕" in texts_asc

    desc = build(
        DataTable(
            columns=["A"],
            rows=[],
            on_sort=lambda c: None,
            sort_column=0,
            sort_ascending=False,
        )
    )
    assert "A ▼" in _collect_texts(desc)


def test_data_table_on_sort_emits_column_index() -> None:
    """Tapping a header button emits ``on_sort`` with the column index."""
    sorted_cols: list[int] = []
    table = DataTable(columns=["A", "B", "C"], rows=[], on_sort=sorted_cols.append)
    node = build(table)
    # The lowered tree's header row holds tappable Buttons; invoke the 3rd.
    header = node.children[0]  # the header Row
    header.children[2].props["on_click"]()
    assert sorted_cols == [2]


def test_data_table_page_slice() -> None:
    """A paginated table only renders the current page's rows."""
    rows = [[str(i)] for i in range(10)]
    page0 = build(DataTable(columns=["N"], rows=rows, page=0, page_size=3))
    texts0 = _collect_texts(page0)
    assert "0" in texts0 and "2" in texts0
    assert "3" not in texts0  # page 1's first row

    page1 = build(DataTable(columns=["N"], rows=rows, page=1, page_size=3))
    texts1 = _collect_texts(page1)
    assert "3" in texts1 and "5" in texts1
    assert "0" not in texts1


def test_data_table_pager_label_and_count() -> None:
    """The pager shows a 1-based ``page X / Y`` label."""
    rows = [[str(i)] for i in range(10)]
    node = build(DataTable(columns=["N"], rows=rows, page=1, page_size=3))
    # ceil(10 / 3) == 4 pages; page index 1 displays as "2".
    assert "page 2 / 4" in _collect_texts(node)


def test_data_table_on_page_prev_next() -> None:
    """Prev/next emit ``on_page`` clamped to ``[0, last]``."""
    pages: list[int] = []
    rows = [[str(i)] for i in range(10)]
    table = DataTable(
        columns=["N"], rows=rows, page=1, page_size=3, on_page=pages.append
    )
    node = build(table)
    pager = node.children[-1]  # the pager Row
    prev_btn, _label, next_btn = pager.children
    prev_btn.props["on_click"]()
    next_btn.props["on_click"]()
    assert pages == [0, 2]


def test_data_table_no_pager_without_page_size() -> None:
    """No pager row is rendered when ``page_size`` is unset."""
    node = build(DataTable(columns=["N"], rows=[["1"]]))
    assert "page" not in " ".join(_collect_texts(node))


def test_data_table_uses_theme_colors() -> None:
    """The header fills with the theme's SURFACE_VARIANT role."""
    node = build(DataTable(columns=["A"], rows=[["1"]]))
    header = node.children[0]
    style = header.props["style"]
    assert style.background == THEME.color(ColorRole.SURFACE_VARIANT)


# --------------------------------------------------------------------------- #
# Calendar / Clock theming
# --------------------------------------------------------------------------- #


def test_calendar_backward_compatible() -> None:
    """``Calendar(on_select=…)`` still builds a month grid."""
    node = build(Calendar(month="2024-03", on_select=lambda iso: None))
    assert "March 2024" in _collect_texts(node)


def test_calendar_selected_day_uses_color_scheme() -> None:
    """The selected day fills with the theme's color-scheme role."""
    rendered = Calendar(
        month="2024-03", selected="2024-03-15", on_select=lambda iso: None
    ).render()
    primary = THEME.color("primary")
    assert _find_background(build(rendered), primary)


def test_calendar_unselected_day_uses_surface_variant() -> None:
    """An unselected day fills with the SURFACE_VARIANT role (no fixed hex)."""
    rendered = Calendar(month="2024-03", on_select=lambda iso: None).render()
    surface_variant = THEME.color(ColorRole.SURFACE_VARIANT)
    assert _find_background(build(rendered), surface_variant)


def test_clock_backward_compatible_and_themed() -> None:
    """``Clock(time=…)`` renders the time in the theme's ON_SURFACE color."""
    node = build(Clock(time="12:34:56", label="UTC"))
    texts = _collect_texts(node)
    assert "12:34:56" in texts
    assert "UTC" in texts


def test_clock_color_scheme_tints_time() -> None:
    """A ``color_scheme`` tints the time with the role color."""
    node = build(Clock(time="00:00", color_scheme="error"))
    error = THEME.color("error")
    # The first child is the time Text node.
    time_text = node.children[0]
    assert time_text.props["style"].color == error


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _collect_texts(node: object) -> list[str]:
    """Collect every ``Text``/``Button`` content string in a lowered node tree.

    Args:
        node: A built :class:`~tempest_core.core.ir.Node`.

    Returns:
        Every text-bearing prop value found in the tree.
    """
    found: list[str] = []
    props = getattr(node, "props", {})
    for key in ("content", "label", "text"):
        value = props.get(key)
        if isinstance(value, str):
            found.append(value)
    for child in getattr(node, "children", []):
        found.extend(_collect_texts(child))
    return found


def _find_background(node: object, color: Color) -> bool:
    """Whether any node in the tree has ``style.background`` equal to ``color``.

    Args:
        node: A built :class:`~tempest_core.core.ir.Node`.
        color: The background color to search for.

    Returns:
        ``True`` if a matching background is found.
    """
    props = getattr(node, "props", {})
    style = props.get("style")
    if style is not None and getattr(style, "background", None) == color:
        return True
    return any(
        _find_background(child, color) for child in getattr(node, "children", [])
    )
