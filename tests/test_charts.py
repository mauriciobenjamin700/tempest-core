"""The chart family on one palette and one scale (issue #24).

``AreaChart``, ``PieChart`` and ``RadarChart`` are new; ``LineChart`` and
``BarChart`` moved onto the same palette and nice-tick axis. Each chart lowers to
a single ``Canvas`` whose command list is pinned structurally here, together with
the value contracts that have to be defined rather than guessed: a negative pie
slice, a zero total, a radar with too few axes, a stack of uneven series.
"""

from __future__ import annotations

import json
import math

import pytest
from pydantic import ValidationError

from tempest_core import (
    AreaChart,
    BarChart,
    ChartSeries,
    LineChart,
    MediaQueryData,
    PieChart,
    RadarChart,
    Theme,
    ThemeMode,
    build,
    chart_palette,
)
from tempest_core.components import charts as charts_module
from tempest_core.components.charts import _color_floats
from tempest_core.tokens import ColorRole
from tempest_core.widgets import (
    Canvas,
    Close,
    DrawCommand,
    DrawRect,
    DrawText,
    FillCmd,
    LineTo,
    MoveTo,
    StrokeCmd,
)

THEME = Theme(mode=ThemeMode.LIGHT)


def _commands(widget: object) -> list[DrawCommand]:
    canvas = widget.render()  # type: ignore[attr-defined]
    assert isinstance(canvas, Canvas)
    return list(canvas.commands)


def _texts(commands: list[DrawCommand]) -> list[str]:
    return [c.text for c in commands if isinstance(c, DrawText)]


def _points(commands: list[DrawCommand]) -> list[tuple[float, float]]:
    return [(c.x, c.y) for c in commands if isinstance(c, MoveTo | LineTo)]


def _palette_floats(count: int, **kwargs: object) -> list[list[float]]:
    return [
        _color_floats(c)
        for c in chart_palette(count, theme=kwargs.pop("theme", THEME), **kwargs)  # type: ignore[arg-type]
    ]


def test_charts_module_surface() -> None:
    assert charts_module.__all__ == [
        "ChartSeries",
        "LineChart",
        "BarChart",
        "AreaChart",
        "PieChart",
        "RadarChart",
    ]


def test_research_module_still_exports_the_moved_charts() -> None:
    """``from tempest_core.components.research import BarChart`` keeps working."""
    from tempest_core.components import research

    assert research.BarChart is BarChart
    assert research.LineChart is LineChart
    assert research.ChartSeries is ChartSeries


# --------------------------------------------------------------------------- #
# Shared: nice axis + palette on Line/Bar
# --------------------------------------------------------------------------- #


def test_value_axis_labels_are_nice_ticks() -> None:
    """The y labels step on round numbers and always include zero."""
    chart = LineChart(theme=THEME, series=[ChartSeries(points=[3.0, 23.1, 12.0])])
    assert _texts(_commands(chart)) == ["0", "5", "10", "15", "20", "25"]


def test_value_axis_covers_negative_data() -> None:
    chart = BarChart(theme=THEME, values=[-3.0, 7.0])
    assert _texts(_commands(chart)) == ["-4", "-2", "0", "2", "4", "6", "8"]


def test_line_chart_unnamed_series_take_the_palette() -> None:
    chart = LineChart(
        theme=THEME,
        color_scheme="tertiary",
        series=[ChartSeries(points=[0.0, 1.0]) for _ in range(4)],
    )
    strokes = [c.color for c in _commands(chart) if isinstance(c, StrokeCmd)]
    assert strokes[-4:] == _palette_floats(4, color_scheme="tertiary")


def test_line_chart_named_series_keep_their_role() -> None:
    chart = LineChart(
        theme=THEME,
        series=[
            ChartSeries(points=[0.0, 1.0]),
            ChartSeries(points=[1.0, 0.0], color_scheme="error"),
        ],
    )
    strokes = [c.color for c in _commands(chart) if isinstance(c, StrokeCmd)]
    assert strokes[-2] == _palette_floats(2)[0]
    assert strokes[-1] == _color_floats(THEME.color("error"))


def test_bar_chart_default_color_is_still_the_role() -> None:
    """One series anchors the palette, so the bars keep the role color."""
    fills = [
        c
        for c in _commands(BarChart(theme=THEME, values=[1.0, 2.0]))
        if isinstance(c, FillCmd)
    ]
    assert {tuple(f.color) for f in fills} == {
        tuple(_color_floats(THEME.color("primary")))
    }


def test_bar_chart_draws_its_labels_under_the_bars() -> None:
    chart = BarChart(theme=THEME, width=200.0, values=[1.0, 2.0], labels=["jan", "fev"])
    commands = _commands(chart)
    labels = [
        c for c in commands if isinstance(c, DrawText) and c.text in {"jan", "fev"}
    ]
    rects = [c for c in commands if isinstance(c, DrawRect)]
    assert [label.text for label in labels] == ["jan", "fev"]
    for label, rect in zip(labels, rects, strict=True):
        assert rect.x < label.x + 1.0 < rect.x + rect.width
        assert label.y > rect.y + rect.height


def test_bar_chart_negative_bar_hangs_below_the_baseline() -> None:
    commands = _commands(BarChart(theme=THEME, values=[4.0, -4.0]))
    up, down = [c for c in commands if isinstance(c, DrawRect)]
    assert up.height > 0.0 and down.height > 0.0
    assert up.y + up.height == pytest.approx(down.y)


def test_media_dark_mode_reaches_a_system_theme() -> None:
    """``media.platform_dark_mode`` resolves a SYSTEM theme to the dark palette."""
    theme = Theme(mode=ThemeMode.SYSTEM)
    series = [ChartSeries(points=[0.0, 1.0]), ChartSeries(points=[1.0, 2.0])]
    light = LineChart(theme=theme, series=series)
    dark = LineChart(
        theme=theme, series=series, media=MediaQueryData(platform_dark_mode=True)
    )
    dark_strokes = [c.color for c in _commands(dark) if isinstance(c, StrokeCmd)]
    assert dark_strokes[-2:] == _palette_floats(2, theme=Theme(mode=ThemeMode.DARK))
    assert _commands(light) != _commands(dark)


# --------------------------------------------------------------------------- #
# AreaChart
# --------------------------------------------------------------------------- #


def _bands(commands: list[DrawCommand]) -> list[list[DrawCommand]]:
    """Split an area chart's series section into per-series command groups."""
    groups: list[list[DrawCommand]] = []
    current: list[DrawCommand] = []
    for command in commands:
        current.append(command)
        if isinstance(command, StrokeCmd) and command.width == 2.0:
            groups.append(current)
            current = []
    return groups


def test_area_chart_band_structure() -> None:
    """Each series: filled polygon (tint) + stroked top edge (solid)."""
    chart = AreaChart(theme=THEME, series=[ChartSeries(points=[1.0, 3.0, 2.0])])
    commands = _commands(chart)
    first_band = next(i for i, c in enumerate(commands) if isinstance(c, Close)) - 6
    band = commands[first_band:]
    kinds = [type(c).__name__ for c in band[:10]]
    assert kinds == [
        "MoveTo",
        "LineTo",
        "LineTo",
        "LineTo",
        "LineTo",
        "LineTo",
        "Close",
        "FillCmd",
        "MoveTo",
        "LineTo",
    ]
    fill = next(c for c in band if isinstance(c, FillCmd))
    stroke = next(c for c in band if isinstance(c, StrokeCmd) and c.width == 2.0)
    color = _palette_floats(1)[0]
    assert fill.color == [*color[:3], 0.28]
    assert stroke.color == color


def test_area_chart_unstacked_fills_to_zero() -> None:
    chart = AreaChart(
        theme=THEME, height=200.0, series=[ChartSeries(points=[2.0, 4.0])]
    )
    commands = _commands(chart)
    zero_y = chart._y(0.0, chart._value_ticks([0.0, 2.0, 4.0]))  # noqa: SLF001
    close = next(i for i, c in enumerate(commands) if isinstance(c, Close))
    bottom = commands[close - 2 : close]
    assert all(isinstance(c, LineTo) and c.y == zero_y for c in bottom)


def test_area_chart_stacked_bands_sit_on_each_other() -> None:
    """Band 2's bottom edge is band 1's top edge; the axis covers the sum."""
    chart = AreaChart(
        theme=THEME,
        stacked=True,
        series=[
            ChartSeries(points=[1.0, 2.0, 3.0]),
            ChartSeries(points=[4.0, 4.0, 4.0]),
        ],
    )
    commands = _commands(chart)
    assert _texts(commands)[-1] == "8"
    closes = [i for i, c in enumerate(commands) if isinstance(c, Close)]
    first_top = [(c.x, c.y) for c in commands[closes[0] - 6 : closes[0] - 3]]
    second_bottom = [(c.x, c.y) for c in commands[closes[1] - 3 : closes[1]]]
    assert second_bottom == list(reversed(first_top))


def test_area_chart_stack_reads_missing_points_as_zero() -> None:
    chart = AreaChart(
        theme=THEME,
        stacked=True,
        series=[ChartSeries(points=[5.0]), ChartSeries(points=[1.0, 1.0])],
    )
    layers = chart._layers()  # noqa: SLF001
    assert layers == [([5.0], [0.0]), ([6.0, 1.0], [5.0, 0.0])]


def test_area_chart_labels_and_empty_series() -> None:
    chart = AreaChart(
        theme=THEME,
        labels=["jan", "fev", "mar"],
        series=[ChartSeries(points=[1.0, 2.0, 3.0]), ChartSeries()],
    )
    commands = _commands(chart)
    assert _texts(commands)[-3:] == ["jan", "fev", "mar"]
    assert sum(isinstance(c, Close) for c in commands) == 1


def test_area_chart_with_no_series_draws_only_the_axes() -> None:
    commands = _commands(AreaChart(theme=THEME))
    assert not any(isinstance(c, FillCmd | Close) for c in commands)


# --------------------------------------------------------------------------- #
# PieChart
# --------------------------------------------------------------------------- #


def test_pie_rejects_a_negative_slice() -> None:
    with pytest.raises(ValidationError, match="negative"):
        PieChart(slices=[("a", 1.0), ("b", -1.0)])


@pytest.mark.parametrize("bad", [math.nan, math.inf])
def test_pie_rejects_non_finite_slices(bad: float) -> None:
    with pytest.raises(ValidationError):
        PieChart(slices=[("a", bad)])


@pytest.mark.parametrize("hole", [-0.1, 1.0])
def test_pie_hole_bounds(hole: float) -> None:
    with pytest.raises(ValidationError):
        PieChart(hole=hole)


def test_pie_one_fill_per_nonzero_slice_in_palette_order() -> None:
    chart = PieChart(
        theme=THEME,
        slices=[("orgânico", 62.0), ("zero", 0.0), ("pago", 38.0)],
        show_legend=False,
    )
    commands = _commands(chart)
    fills = [c.color for c in commands if isinstance(c, FillCmd)]
    palette = _palette_floats(3)
    assert fills == [palette[0], palette[2]]
    assert not _texts(commands)


def test_pie_legend_lists_every_slice_with_its_share() -> None:
    chart = PieChart(
        theme=THEME, slices=[("orgânico", 62.0), ("zero", 0.0), ("pago", 38.0)]
    )
    commands = _commands(chart)
    assert _texts(commands) == ["orgânico 62%", "zero 0%", "pago 38%"]
    swatches = [c for c in commands if isinstance(c, DrawRect)]
    assert len(swatches) == 3


def test_pie_slices_start_at_twelve_and_turn_clockwise() -> None:
    chart = PieChart(
        theme=THEME,
        width=200.0,
        height=200.0,
        slices=[("a", 1.0), ("b", 3.0)],
        show_legend=False,
    )
    commands = _commands(chart)
    cx, cy, radius = chart._geometry()  # noqa: SLF001
    assert commands[0] == MoveTo(x=cx, y=cy)
    assert (commands[1].x, commands[1].y) == pytest.approx((cx, cy - radius))  # type: ignore[union-attr]
    closes = [i for i, c in enumerate(commands) if isinstance(c, Close)]
    quarter_end = commands[closes[0] - 1]
    assert (quarter_end.x, quarter_end.y) == pytest.approx((cx + radius, cy))  # type: ignore[union-attr]


def test_pie_single_slice_is_a_full_disc() -> None:
    chart = PieChart(theme=THEME, slices=[("tudo", 5.0)], show_legend=False)
    commands = _commands(chart)
    assert sum(isinstance(c, FillCmd) for c in commands) == 1
    ring = _points(commands)[1:]
    assert ring[0] == pytest.approx(ring[-1])


def test_pie_donut_never_touches_the_center() -> None:
    chart = PieChart(
        theme=THEME, hole=0.5, slices=[("a", 1.0), ("b", 1.0)], show_legend=False
    )
    cx, cy, radius = chart._geometry()  # noqa: SLF001
    for px, py in _points(_commands(chart)):
        distance = math.hypot(px - cx, py - cy)
        assert distance == pytest.approx(radius, abs=1e-2) or distance == pytest.approx(
            radius * 0.5, abs=1e-2
        )


@pytest.mark.parametrize("slices", [[], [("a", 0.0), ("b", 0.0)]])
def test_pie_zero_total_draws_the_empty_ring(slices: list[tuple[str, float]]) -> None:
    commands = _commands(PieChart(theme=THEME, slices=slices, show_legend=False))
    assert not any(isinstance(c, FillCmd) for c in commands)
    (stroke,) = [c for c in commands if isinstance(c, StrokeCmd)]
    assert stroke.color == _color_floats(THEME.color(ColorRole.OUTLINE_VARIANT))


def test_pie_arcs_are_polylines_not_arc_to() -> None:
    """``ArcTo`` angles differ between the Qt and Compose leaves; a polyline doesn't."""
    commands = _commands(PieChart(theme=THEME, slices=[("a", 1.0), ("b", 2.0)]))
    assert {type(c).__name__ for c in commands} <= {
        "MoveTo",
        "LineTo",
        "Close",
        "FillCmd",
        "DrawRect",
        "DrawText",
    }


def test_pie_geometry_stays_inside_the_canvas() -> None:
    chart = PieChart(
        theme=THEME, width=300.0, height=160.0, slices=[("a", 1.0), ("b", 2.0)]
    )
    for px, py in _points(_commands(chart)):
        assert 0.0 <= px <= 300.0 and 0.0 <= py <= 160.0


# --------------------------------------------------------------------------- #
# RadarChart
# --------------------------------------------------------------------------- #

AXES = ["força", "velocidade", "alcance", "defesa", "custo"]


def test_radar_structure() -> None:
    chart = RadarChart(
        theme=THEME,
        axes=AXES,
        series=[
            ChartSeries(points=[3.0, 4.0, 2.0, 5.0, 1.0]),
            ChartSeries(points=[1.0] * 5),
        ],
    )
    commands = _commands(chart)
    fills = [c for c in commands if isinstance(c, FillCmd)]
    palette = _palette_floats(2)
    assert [f.color for f in fills] == [[*p[:3], 0.22] for p in palette]
    assert _texts(commands) == AXES


def test_radar_first_axis_points_up_and_values_scale_to_the_rim() -> None:
    chart = RadarChart(
        theme=THEME,
        width=200.0,
        height=200.0,
        axes=["a", "b", "c"],
        max_value=10.0,
        series=[ChartSeries(points=[10.0, 5.0, 0.0])],
    )
    commands = _commands(chart)
    fill_at = next(i for i, c in enumerate(commands) if isinstance(c, FillCmd))
    top, half, center = [(c.x, c.y) for c in commands[fill_at - 4 : fill_at - 1]]
    radius = 100.0 - 28.0
    assert top == pytest.approx((100.0, 100.0 - radius))
    assert math.hypot(half[0] - 100.0, half[1] - 100.0) == pytest.approx(
        radius / 2, abs=1e-2
    )
    assert center == pytest.approx((100.0, 100.0))


def test_radar_clamps_values_outside_the_range() -> None:
    chart = RadarChart(
        theme=THEME,
        width=200.0,
        height=200.0,
        axes=["a", "b", "c"],
        max_value=10.0,
        series=[ChartSeries(points=[99.0, -5.0, 10.0])],
    )
    commands = _commands(chart)
    fill_at = next(i for i, c in enumerate(commands) if isinstance(c, FillCmd))
    rim, center, _ = [(c.x, c.y) for c in commands[fill_at - 4 : fill_at - 1]]
    assert rim == pytest.approx((100.0, 28.0))
    assert center == pytest.approx((100.0, 100.0))


def test_radar_derived_range_uses_nice_ticks() -> None:
    chart = RadarChart(
        theme=THEME, axes=AXES, series=[ChartSeries(points=[3.0, 7.3, 1.0, 2.0, 6.0])]
    )
    assert chart._rings() == [0.0, 2.0, 4.0, 6.0, 8.0]  # noqa: SLF001


def test_radar_missing_points_read_as_zero_and_extras_are_ignored() -> None:
    short = RadarChart(
        theme=THEME,
        axes=["a", "b", "c"],
        max_value=1.0,
        series=[ChartSeries(points=[1.0])],
    )
    padded = RadarChart(
        theme=THEME,
        axes=["a", "b", "c"],
        max_value=1.0,
        series=[ChartSeries(points=[1.0, 0.0, 0.0, 9.0])],
    )
    assert _commands(short) == _commands(padded)


@pytest.mark.parametrize("axes", [["a"], ["a", "b"]])
def test_radar_below_three_axes_draws_spokes_only(axes: list[str]) -> None:
    commands = _commands(
        RadarChart(theme=THEME, axes=axes, series=[ChartSeries(points=[1.0, 2.0])])
    )
    assert not any(isinstance(c, FillCmd | Close) for c in commands)
    assert sum(isinstance(c, StrokeCmd) for c in commands) == len(axes)
    assert _texts(commands) == axes


def test_radar_without_axes_is_an_empty_canvas() -> None:
    assert _commands(RadarChart(theme=THEME)) == []


def test_radar_max_value_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        RadarChart(max_value=0.0)


# --------------------------------------------------------------------------- #
# All charts: keys, determinism, serializability
# --------------------------------------------------------------------------- #


def _all_charts(key: str | None = None) -> list[object]:
    series = [ChartSeries(points=[1.0, 4.0, 2.0]), ChartSeries(points=[2.0, 1.0, 3.0])]
    return [
        LineChart(key=key, theme=THEME, series=series),
        BarChart(key=key, theme=THEME, series=series, labels=["a", "b", "c"]),
        AreaChart(
            key=key, theme=THEME, series=series, stacked=True, labels=["a", "b", "c"]
        ),
        PieChart(key=key, theme=THEME, slices=[("a", 1.0), ("b", 2.0)], hole=0.4),
        RadarChart(key=key, theme=THEME, axes=["x", "y", "z"], series=series),
    ]


def test_every_chart_builds_to_one_keyed_canvas() -> None:
    defaults = ["line-chart", "bar-chart", "area-chart", "pie-chart", "radar-chart"]
    for chart, default in zip(_all_charts(), defaults, strict=True):
        node = build(chart)  # type: ignore[arg-type]
        assert node.type == "Canvas"
        assert node.key == default
    for chart in _all_charts(key="sales"):
        assert build(chart).key == "sales"  # type: ignore[arg-type]


def test_every_chart_is_deterministic_and_json_safe() -> None:
    for first, second in zip(_all_charts(), _all_charts(), strict=True):
        a = [c.model_dump() for c in _commands(first)]
        assert a == [c.model_dump() for c in _commands(second)]
        encoded = json.dumps(a, allow_nan=False)
        assert "NaN" not in encoded


def test_every_chart_emits_only_the_existing_vocabulary() -> None:
    allowed = {
        "MoveTo",
        "LineTo",
        "Close",
        "FillCmd",
        "StrokeCmd",
        "DrawText",
        "DrawRect",
    }
    for chart in _all_charts():
        assert {type(c).__name__ for c in _commands(chart)} <= allowed
