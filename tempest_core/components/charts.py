"""Chart components drawn over the E7 :class:`~tempest_core.widgets.Canvas`.

Five charts share one geometry base, one scale and one palette, so that any two of
them on the same screen read as the same product:

* :class:`LineChart` / :class:`AreaChart` — series over an ordinal x axis, the
  area variant filling each series down to the baseline (or, ``stacked``, onto
  the series below it).
* :class:`BarChart` — one series as bars, with optional x labels.
* :class:`PieChart` — composition of a total, as a pie or (``hole``) a donut, with
  a legend.
* :class:`RadarChart` — several series compared across three or more axes.

Design notes:

* **Chart data is a frozen** :class:`ChartSeries` (``points`` + ``label`` +
  optional ``color_scheme``), not a bare list, so a chart can carry several named,
  individually-colored series. :class:`BarChart` additionally accepts a plain
  ``list[float]`` for the trivial case; :class:`PieChart` takes
  ``(label, value)`` pairs.
* **Colors come from** :func:`~tempest_core.dataviz.chart_palette`: a series that
  names its own ``color_scheme`` paints that role, every other series takes the
  palette color at its index, so series ``i`` is the same color in every chart.
* **Value axes use** :func:`~tempest_core.dataviz.nice_ticks`, so ticks land on
  ``1 / 2 / 5 × 10ⁿ`` and the axis always includes zero.
* **Charts emit only the existing draw vocabulary.** A line is ``MoveTo`` +
  ``LineTo`` + ``StrokeCmd``; a bar is ``DrawRect`` + ``FillCmd``; an arc is a
  run of ``LineTo`` points rather than ``ArcTo``, because the Qt and Compose
  renderers read ``ArcTo`` angles in opposite rotational senses and a polyline
  draws identically everywhere. Trigonometric coordinates are rounded to
  :data:`_COORD_DECIMALS` decimals so the command list is identical across
  platforms' ``libm`` and the conformance goldens stay pinned.
"""

from __future__ import annotations

import math
from typing import ClassVar

from pydantic import ConfigDict, Field, field_validator

from tempest_core._model import _CoreModel
from tempest_core.dataviz import chart_palette, format_tick, linear_map, nice_ticks
from tempest_core.style import Color
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.widgets import (
    Canvas,
    Close,
    Component,
    DrawCommand,
    DrawRect,
    DrawText,
    FillCmd,
    LineTo,
    MoveTo,
    StrokeCmd,
    Widget,
)

__all__ = [
    "ChartSeries",
    "LineChart",
    "BarChart",
    "AreaChart",
    "PieChart",
    "RadarChart",
]

#: Decimals trigonometric coordinates are rounded to (pie arcs, radar vertices).
_COORD_DECIMALS: int = 3

#: The largest angle, in degrees, one polyline segment of an arc may span.
_ARC_STEP_DEGREES: float = 6.0


def _no_floats() -> list[float]:
    """Provide a fresh, typed empty float list for default factories.

    Returns:
        A new empty list of floats.
    """
    return []


def _no_strs() -> list[str]:
    """Provide a fresh, typed empty string list for default factories.

    Returns:
        A new empty list of strings.
    """
    return []


def _no_series() -> list[ChartSeries]:
    """Provide a fresh, typed empty series list for default factories.

    Returns:
        A new empty list of chart series.
    """
    return []


def _no_slices() -> list[tuple[str, float]]:
    """Provide a fresh, typed empty slice list for default factories.

    Returns:
        A new empty list of ``(label, value)`` slices.
    """
    return []


def _color_floats(color: Color, *, alpha: float | None = None) -> list[float]:
    """Lower a :class:`~tempest_core.style.Color` to a Canvas ``[r, g, b, a]`` list.

    The :class:`~tempest_core.widgets.Canvas` draw commands carry color as a list
    of floats in ``[0, 1]`` (never a ``Color`` object or a tuple, so the command
    is JSON-serializable directly). ``Color`` stores ``r``/``g``/``b`` as ``0-255``
    ints and ``a`` as a ``0-1`` float.

    Args:
        color: The color to lower.
        alpha: An optional alpha that replaces the color's own (for a translucent
            area or radar fill).

    Returns:
        The ``[r, g, b, a]`` float list with the channels normalized to ``[0, 1]``.
    """
    return [
        color.r / 255.0,
        color.g / 255.0,
        color.b / 255.0,
        color.a if alpha is None else alpha,
    ]


def _estimate_text_width(text: str, size: float) -> float:
    """Estimate a text run's pixel width (no font metrics available in the engine).

    The :class:`~tempest_core.widgets.DrawText` command is baseline-anchored with
    no alignment field, so to right-align or center a label we shift its anchor
    left by an estimate of its width. A flat per-character factor (~0.6 of the
    font size) is plenty for axis and legend labels.

    Args:
        text: The text run.
        size: The font size, in logical pixels.

    Returns:
        The estimated width, in logical pixels.
    """
    return len(text) * size * 0.6


def _point(cx: float, cy: float, radius: float, degrees: float) -> tuple[float, float]:
    """Place a point on a circle, clockwise in screen space from 3 o'clock.

    Args:
        cx: The circle center x.
        cy: The circle center y.
        radius: The circle radius.
        degrees: The angle, in degrees (``-90`` is 12 o'clock).

    Returns:
        The ``(x, y)`` point, rounded to :data:`_COORD_DECIMALS` decimals.
    """
    radians = math.radians(degrees)
    return (
        round(cx + radius * math.cos(radians), _COORD_DECIMALS) + 0.0,
        round(cy + radius * math.sin(radians), _COORD_DECIMALS) + 0.0,
    )


def _arc_points(
    cx: float, cy: float, radius: float, start: float, sweep: float
) -> list[tuple[float, float]]:
    """Sample an arc as a polyline, both ends included.

    Args:
        cx: The circle center x.
        cy: The circle center y.
        radius: The circle radius.
        start: The start angle, in degrees.
        sweep: The sweep, in degrees (positive is clockwise on screen).

    Returns:
        The arc's points, one per :data:`_ARC_STEP_DEGREES` or finer.
    """
    segments = max(1, math.ceil(abs(sweep) / _ARC_STEP_DEGREES))
    return [
        _point(cx, cy, radius, start + sweep * step / segments)
        for step in range(segments + 1)
    ]


class ChartSeries(_CoreModel):
    """A single named, optionally-colored data series for a chart.

    A chart takes a list of these rather than bare ``list[float]`` so it can plot
    several series at once, each with its own label and (optionally) its own
    ``color_scheme``; an unset ``color_scheme`` lets the chart take the
    :func:`~tempest_core.dataviz.chart_palette` color at the series' index.

    Attributes:
        points: The series' y-values, in plot order (one per x position, or one
            per axis in a :class:`RadarChart`).
        label: An optional series label (carried for a legend; the line, area and
            radar charts do not draw it).
        color_scheme: An optional Material 3 role family to color this series
            with; ``None`` falls back to the chart's palette.
    """

    model_config = ConfigDict(frozen=True)

    points: list[float] = Field(
        description="The series' y-values, in plot order (one per x position).",
        default_factory=_no_floats,
    )
    label: str = Field(default="", description="An optional series label.")
    color_scheme: str | None = Field(
        default=None,
        description="An optional Material 3 role family to color this series with; "
        "``None`` falls back to the chart's palette.",
    )


class _ChartBase(Component):
    """Shared geometry, color and axis state for the Canvas-backed charts.

    Not exported — the concrete charts are :class:`LineChart`, :class:`BarChart`,
    :class:`AreaChart`, :class:`PieChart` and :class:`RadarChart`.

    Attributes:
        width: The canvas width, in logical pixels.
        height: The canvas height, in logical pixels.
        color_scheme: The Material 3 role that anchors the chart palette.
        theme: The design-system theme whose tokens supply colors.
        media: Optional viewport snapshot; its ``platform_dark_mode`` resolves a
            ``SYSTEM``-mode theme to light or dark.
    """

    width: float = Field(default=320.0, description="The canvas width, in pixels.")
    height: float = Field(default=200.0, description="The canvas height, in pixels.")
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role that anchors the chart palette.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply colors.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot; resolves a SYSTEM-mode theme.",
    )

    _PAD_LEFT: ClassVar[float] = 40.0
    _PAD_BOTTOM: ClassVar[float] = 24.0
    _PAD_TOP: ClassVar[float] = 12.0
    _PAD_RIGHT: ClassVar[float] = 12.0
    _AXIS_FONT: ClassVar[float] = 11.0
    _TICKS: ClassVar[int] = 4

    def _dark(self) -> bool:
        """Read the platform dark-mode flag from :attr:`media`.

        Returns:
            ``True`` when the platform reports dark mode.
        """
        return self.media.platform_dark_mode if self.media is not None else False

    def _role(self, role: ColorRole | str) -> Color:
        """Resolve a color role in the chart's resolved mode.

        Args:
            role: The role to resolve.

        Returns:
            The concrete color.
        """
        return self.theme.color(role, platform_dark_mode=self._dark())

    def _palette(self, count: int) -> list[Color]:
        """Derive the chart's categorical palette.

        Args:
            count: How many colors to derive.

        Returns:
            The :func:`~tempest_core.dataviz.chart_palette` colors.
        """
        return chart_palette(
            count,
            theme=self.theme,
            color_scheme=self.color_scheme,
            platform_dark_mode=self._dark(),
        )

    def _series_colors(self, series: list[ChartSeries]) -> list[Color]:
        """Color every series: its own role when named, else the palette slot.

        Args:
            series: The chart's series, in order.

        Returns:
            One color per series.
        """
        palette = self._palette(len(series))
        return [
            self._role(item.color_scheme) if item.color_scheme else palette[index]
            for index, item in enumerate(series)
        ]

    def _plot_rect(self) -> tuple[float, float, float, float]:
        """Compute the inset plotting rectangle ``(x, y, w, h)``.

        Returns:
            The plot area left/top/width/height, in pixels.
        """
        x = self._PAD_LEFT
        y = self._PAD_TOP
        w = self.width - self._PAD_LEFT - self._PAD_RIGHT
        h = self.height - self._PAD_TOP - self._PAD_BOTTOM
        return x, y, w, h

    def _value_ticks(self, values: list[float]) -> list[float]:
        """Compute the value-axis ticks for a set of plotted values.

        Zero is always inside the range, so bars and areas have a real baseline.

        Args:
            values: Every plotted value.

        Returns:
            The :func:`~tempest_core.dataviz.nice_ticks` for the axis.
        """
        if not values:
            return nice_ticks(0.0, 1.0, count=self._TICKS)
        return nice_ticks(
            min(0.0, min(values)), max(0.0, max(values)), count=self._TICKS
        )

    def _y(self, value: float, ticks: list[float]) -> float:
        """Map a value onto the plot's y pixel coordinate.

        Args:
            value: The value to place.
            ticks: The value-axis ticks (their ends are the domain).

        Returns:
            The y coordinate, in pixels (larger values are higher on screen).
        """
        _, y, _, h = self._plot_rect()
        return linear_map(value, (ticks[0], ticks[-1]), (y + h, y))

    def _axes_commands(self, ticks: list[float]) -> list[DrawCommand]:
        """Emit the axis frame, a gridline per tick and right-aligned tick labels.

        Args:
            ticks: The value-axis ticks.

        Returns:
            The axis/grid/label draw commands.
        """
        x, y, w, h = self._plot_rect()
        axis_floats = _color_floats(self._role(ColorRole.OUTLINE_VARIANT))
        label_floats = _color_floats(self._role(ColorRole.ON_SURFACE_VARIANT))
        commands: list[DrawCommand] = [
            MoveTo(x=x, y=y),
            LineTo(x=x, y=y + h),
            LineTo(x=x + w, y=y + h),
            StrokeCmd(color=axis_floats, width=1.0),
        ]
        for tick in ticks:
            py = self._y(tick, ticks)
            commands.append(MoveTo(x=x, y=py))
            commands.append(LineTo(x=x + w, y=py))
            commands.append(StrokeCmd(color=axis_floats, width=0.5))
            text = format_tick(tick, ticks)
            text_w = _estimate_text_width(text, self._AXIS_FONT)
            commands.append(
                DrawText(
                    text=text,
                    x=x - 4.0 - text_w,
                    y=py + self._AXIS_FONT / 3.0,
                    size=self._AXIS_FONT,
                    color=label_floats,
                )
            )
        return commands

    def _x_label_commands(
        self, labels: list[str], centers: list[float]
    ) -> list[DrawCommand]:
        """Emit x-axis labels centered under their positions.

        Labels beyond the number of positions are ignored.

        Args:
            labels: The labels, in x order.
            centers: The x pixel center of each position.

        Returns:
            One :class:`~tempest_core.widgets.DrawText` per labelled position.
        """
        _, y, _, h = self._plot_rect()
        label_floats = _color_floats(self._role(ColorRole.ON_SURFACE_VARIANT))
        return [
            DrawText(
                text=label,
                x=center - _estimate_text_width(label, self._AXIS_FONT) / 2.0,
                y=y + h + 4.0 + self._AXIS_FONT,
                size=self._AXIS_FONT,
                color=label_floats,
            )
            for label, center in zip(labels, centers, strict=False)
        ]

    def _canvas(self, commands: list[DrawCommand]) -> Canvas:
        """Wrap a command list in the chart's keyed, sized canvas.

        Args:
            commands: The draw commands.

        Returns:
            The :class:`~tempest_core.widgets.Canvas` node.
        """
        return Canvas(
            key=self.base_key,
            commands=commands,
            width=self.width,
            height=self.height,
            style=self.style,
        )


class LineChart(_ChartBase):
    """A multi-series line chart drawn over a :class:`~tempest_core.widgets.Canvas`.

    Each :class:`ChartSeries` becomes a connected polyline over a shared, framed
    plot rect with a gridline and a label per nice tick. The command list is
    deterministic for fixed input, so the conformance suite pins it.

    Attributes:
        series: The data series to plot (each its own polyline + color).
    """

    default_key: ClassVar[str] = "line-chart"

    series: list[ChartSeries] = Field(
        description="The data series to plot.", default_factory=_no_series
    )

    def render(self) -> Widget:
        """Lower the line chart into a ``Canvas`` of axis + polyline commands.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        x, _, w, _ = self._plot_rect()
        ticks = self._value_ticks([v for s in self.series for v in s.points])
        commands: list[DrawCommand] = self._axes_commands(ticks)
        colors = self._series_colors(self.series)
        for series, color in zip(self.series, colors, strict=True):
            n = len(series.points)
            if n == 0:
                continue
            step = w / (n - 1) if n > 1 else 0.0
            for point_index, value in enumerate(series.points):
                px = x + point_index * step
                py = self._y(value, ticks)
                if point_index == 0:
                    commands.append(MoveTo(x=px, y=py))
                else:
                    commands.append(LineTo(x=px, y=py))
            commands.append(StrokeCmd(color=_color_floats(color), width=2.0))
        return self._canvas(commands)


class BarChart(_ChartBase):
    """A bar chart drawn over a :class:`~tempest_core.widgets.Canvas`.

    Accepts either a list of :class:`ChartSeries` (the first series' points become
    the bars) or, for the trivial single-series case, a plain ``values`` list.
    Each bar is a :class:`~tempest_core.widgets.DrawRect` + a
    :class:`~tempest_core.widgets.FillCmd` rising from the zero baseline; each
    ``labels`` entry is drawn centered under its bar.

    Attributes:
        series: The data series (the first series is plotted as bars). Optional
            when ``values`` is given.
        values: A convenience single-series value list (used when ``series`` is
            empty).
        labels: Optional x-axis labels, one per bar.
    """

    default_key: ClassVar[str] = "bar-chart"

    series: list[ChartSeries] = Field(
        description="The data series (first series plotted as bars).",
        default_factory=_no_series,
    )
    values: list[float] = Field(
        description="A convenience single-series value list.",
        default_factory=_no_floats,
    )
    labels: list[str] = Field(
        description="Optional x-axis labels for the bars.",
        default_factory=_no_strs,
    )

    def _bars(self) -> ChartSeries:
        """Resolve the plotted series.

        ``series`` wins when present (its first series); otherwise ``values`` is
        used as a single, palette-colored series.

        Returns:
            The series drawn as bars.
        """
        if self.series:
            return self.series[0]
        return ChartSeries(points=list(self.values))

    def render(self) -> Widget:
        """Lower the bar chart into a ``Canvas`` of axis + bar commands.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        x, _, w, _ = self._plot_rect()
        bars = self._bars()
        values = bars.points
        ticks = self._value_ticks(values)
        commands: list[DrawCommand] = self._axes_commands(ticks)
        color_floats = _color_floats(self._series_colors([bars])[0])
        baseline_y = self._y(0.0, ticks)
        n = len(values)
        centers: list[float] = []
        if n > 0:
            slot = w / n
            bar_w = slot * 0.7
            gap = (slot - bar_w) / 2.0
            for index, value in enumerate(values):
                top = self._y(value, ticks)
                bar_x = x + index * slot + gap
                commands.append(
                    DrawRect(
                        x=bar_x,
                        y=min(top, baseline_y),
                        width=bar_w,
                        height=abs(baseline_y - top),
                    )
                )
                commands.append(FillCmd(color=color_floats))
                centers.append(x + index * slot + slot / 2.0)
        commands.extend(self._x_label_commands(self.labels, centers))
        return self._canvas(commands)


class AreaChart(_ChartBase):
    """A multi-series area chart: each line filled down to its baseline.

    Each :class:`ChartSeries` is drawn as a translucent filled polygon under a
    solid stroke. Unstacked, every area fills to the zero line and later series
    paint over earlier ones; ``stacked=True`` accumulates the series point by
    point, so each band sits on the one below and the top edge reads as the
    running total — the form for "revenue by channel over time". A point a
    shorter series lacks counts as ``0`` in the stack.

    The stroke carries the palette's contrast guarantee; the fill is a tint at
    :attr:`_FILL_OPACITY` and is not held to it.

    Attributes:
        series: The data series, bottom-most first when stacked.
        labels: Optional x-axis labels, one per x position.
        stacked: Whether series accumulate onto each other.
    """

    default_key: ClassVar[str] = "area-chart"

    series: list[ChartSeries] = Field(
        description="The data series, bottom-most first when stacked.",
        default_factory=_no_series,
    )
    labels: list[str] = Field(
        description="Optional x-axis labels, one per x position.",
        default_factory=_no_strs,
    )
    stacked: bool = Field(
        default=False, description="Whether series accumulate onto each other."
    )

    _FILL_OPACITY: ClassVar[float] = 0.28

    def _layers(self) -> list[tuple[list[float], list[float]]]:
        """Compute each series' ``(tops, bottoms)`` in value space.

        Returns:
            One ``(tops, bottoms)`` pair per series, each as long as the series.
        """
        if not self.stacked:
            return [
                (list(item.points), [0.0] * len(item.points)) for item in self.series
            ]
        length = max((len(item.points) for item in self.series), default=0)
        running = [0.0] * length
        layers: list[tuple[list[float], list[float]]] = []
        for item in self.series:
            bottoms = running[: len(item.points)]
            tops = [
                base + value for base, value in zip(bottoms, item.points, strict=True)
            ]
            layers.append((tops, bottoms))
            running = tops + running[len(item.points) :]
        return layers

    def render(self) -> Widget:
        """Lower the area chart into a ``Canvas`` of axis + band commands.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        x, _, w, _ = self._plot_rect()
        layers = self._layers()
        ticks = self._value_ticks(
            [v for tops, bottoms in layers for v in (*tops, *bottoms)]
        )
        commands: list[DrawCommand] = self._axes_commands(ticks)
        colors = self._series_colors(self.series)
        length = max((len(tops) for tops, _ in layers), default=0)
        step = w / (length - 1) if length > 1 else 0.0
        for (tops, bottoms), color in zip(layers, colors, strict=True):
            if not tops:
                continue
            upper = [
                (x + index * step, self._y(value, ticks))
                for index, value in enumerate(tops)
            ]
            lower = [
                (x + index * step, self._y(value, ticks))
                for index, value in enumerate(bottoms)
            ]
            commands.append(MoveTo(x=upper[0][0], y=upper[0][1]))
            for px, py in upper[1:]:
                commands.append(LineTo(x=px, y=py))
            for px, py in reversed(lower):
                commands.append(LineTo(x=px, y=py))
            commands.append(Close())
            commands.append(
                FillCmd(color=_color_floats(color, alpha=self._FILL_OPACITY))
            )
            commands.append(MoveTo(x=upper[0][0], y=upper[0][1]))
            for px, py in upper[1:]:
                commands.append(LineTo(x=px, y=py))
            commands.append(StrokeCmd(color=_color_floats(color), width=2.0))
        commands.extend(
            self._x_label_commands(
                self.labels, [x + index * step for index in range(length)]
            )
        )
        return self._canvas(commands)


class PieChart(_ChartBase):
    """A pie (or donut) chart showing each slice's share of a total.

    Slices are drawn clockwise from 12 o'clock in input order, each a filled
    polygon (the arc sampled as ``LineTo`` points), colored by the palette at the
    slice's index; a legend beside the pie lists every slice with its swatch and
    rounded percentage. A ``hole`` above ``0`` cuts the center out into a donut.

    The value contract is defined rather than guessed:

    * a **negative** value is rejected at construction (``ValidationError``) — a
      share of a total cannot be negative;
    * a **zero** value keeps its legend row and color slot but draws no slice;
    * a **zero total** (no slices, or all zero) draws the empty ring outline in
      the theme's ``outline_variant``, so "no data yet" still has a shape.

    Attributes:
        slices: The ``(label, value)`` pairs, in drawing order.
        hole: The donut hole as a fraction of the radius (``0`` is a full pie).
        show_legend: Whether to draw the legend beside the pie.
    """

    default_key: ClassVar[str] = "pie-chart"

    slices: list[tuple[str, float]] = Field(
        description="The (label, value) pairs, in drawing order.",
        default_factory=_no_slices,
    )
    hole: float = Field(
        default=0.0,
        ge=0.0,
        lt=1.0,
        description="The donut hole as a fraction of the radius (0 is a full pie).",
    )
    show_legend: bool = Field(
        default=True, description="Whether to draw the legend beside the pie."
    )

    _PAD: ClassVar[float] = 12.0
    _LEGEND_FONT: ClassVar[float] = 11.0
    _LEGEND_ROW: ClassVar[float] = 18.0
    _SWATCH: ClassVar[float] = 10.0

    @field_validator("slices")
    @classmethod
    def _non_negative(cls, slices: list[tuple[str, float]]) -> list[tuple[str, float]]:
        """Reject a slice with a negative value.

        Args:
            slices: The candidate slices.

        Returns:
            The slices, unchanged.

        Raises:
            ValueError: If any slice value is negative.
        """
        for label, value in slices:
            if value < 0.0:
                raise ValueError(
                    f"slice {label!r} has a negative value ({value!r}); a share of "
                    "a total cannot be negative"
                )
        return slices

    def _geometry(self) -> tuple[float, float, float]:
        """Place the pie: its center and radius.

        Returns:
            The ``(cx, cy, radius)`` of the pie, in pixels.
        """
        available_w = self.width - 2.0 * self._PAD
        if self.show_legend:
            available_w *= 0.5
        diameter = max(0.0, min(self.height - 2.0 * self._PAD, available_w))
        radius = diameter / 2.0
        return self._PAD + radius, self.height / 2.0, radius

    def _wedge(
        self, cx: float, cy: float, radius: float, start: float, sweep: float
    ) -> list[DrawCommand]:
        """Emit the closed path of one slice (a wedge, or a ring segment).

        Args:
            cx: The pie center x.
            cy: The pie center y.
            radius: The outer radius.
            start: The start angle, in degrees.
            sweep: The sweep, in degrees.

        Returns:
            The path commands, ending in :class:`~tempest_core.widgets.Close`.
        """
        outer = _arc_points(cx, cy, radius, start, sweep)
        if self.hole > 0.0:
            inner = _arc_points(cx, cy, radius * self.hole, start, sweep)
            points = outer + list(reversed(inner))
        else:
            points = [(cx, cy), *outer]
        commands: list[DrawCommand] = [MoveTo(x=points[0][0], y=points[0][1])]
        commands.extend(LineTo(x=px, y=py) for px, py in points[1:])
        commands.append(Close())
        return commands

    def _legend(self, colors: list[Color], total: float) -> list[DrawCommand]:
        """Emit the legend: a swatch and ``"label NN%"`` per slice.

        Args:
            colors: The slice colors, in slice order.
            total: The sum of every slice value.

        Returns:
            The legend draw commands.
        """
        cx, cy, radius = self._geometry()
        left = cx + radius + 16.0
        text_floats = _color_floats(self._role(ColorRole.ON_SURFACE))
        top = cy - len(self.slices) * self._LEGEND_ROW / 2.0
        commands: list[DrawCommand] = []
        for index, ((label, value), color) in enumerate(
            zip(self.slices, colors, strict=True)
        ):
            row_y = top + index * self._LEGEND_ROW
            share = value / total * 100.0 if total > 0.0 else 0.0
            commands.append(
                DrawRect(x=left, y=row_y, width=self._SWATCH, height=self._SWATCH)
            )
            commands.append(FillCmd(color=_color_floats(color)))
            commands.append(
                DrawText(
                    text=f"{label} {share:.0f}%",
                    x=left + self._SWATCH + 6.0,
                    y=row_y + self._SWATCH,
                    size=self._LEGEND_FONT,
                    color=text_floats,
                )
            )
        return commands

    def render(self) -> Widget:
        """Lower the pie into a ``Canvas`` of slice polygons and a legend.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        cx, cy, radius = self._geometry()
        colors = self._palette(len(self.slices))
        total = sum(value for _, value in self.slices)
        commands: list[DrawCommand] = []
        if total <= 0.0:
            ring = _arc_points(cx, cy, radius, -90.0, 360.0)
            commands.append(MoveTo(x=ring[0][0], y=ring[0][1]))
            commands.extend(LineTo(x=px, y=py) for px, py in ring[1:])
            commands.append(Close())
            commands.append(
                StrokeCmd(
                    color=_color_floats(self._role(ColorRole.OUTLINE_VARIANT)),
                    width=1.0,
                )
            )
        else:
            angle = -90.0
            for (_, value), color in zip(self.slices, colors, strict=True):
                if value <= 0.0:
                    continue
                sweep = value / total * 360.0
                commands.extend(self._wedge(cx, cy, radius, angle, sweep))
                commands.append(FillCmd(color=_color_floats(color)))
                angle += sweep
        if self.show_legend:
            commands.extend(self._legend(colors, total))
        return self._canvas(commands)


class RadarChart(_ChartBase):
    """A radar (spider) chart comparing series across three or more axes.

    The axes radiate clockwise from 12 o'clock; concentric grid polygons sit at
    each nice tick of the value range, and each :class:`ChartSeries` is a
    translucent polygon with a solid outline whose ``i``-th point lies on axis
    ``i``.

    The value contract:

    * the range is ``[0, max_value]`` when ``max_value`` is given, else ``0`` to
      the top :func:`~tempest_core.dataviz.nice_ticks` value of the data;
    * values below ``0`` sit at the center and values above the range sit on the
      rim — a radar has no room outside either;
    * a series with fewer points than axes reads the missing ones as ``0``, and
      extra points are ignored;
    * with fewer than three axes there is no polygon to draw, so only the spokes
      and their labels render.

    Attributes:
        axes: The axis labels, clockwise from 12 o'clock.
        series: The data series, one point per axis.
        max_value: An explicit top of the value range; ``None`` derives it.
    """

    default_key: ClassVar[str] = "radar-chart"

    axes: list[str] = Field(
        description="The axis labels, clockwise from 12 o'clock.",
        default_factory=_no_strs,
    )
    series: list[ChartSeries] = Field(
        description="The data series, one point per axis.",
        default_factory=_no_series,
    )
    max_value: float | None = Field(
        default=None,
        gt=0.0,
        description="An explicit top of the value range; None derives it.",
    )

    _LABEL_GAP: ClassVar[float] = 28.0
    _FILL_OPACITY: ClassVar[float] = 0.22

    def _rings(self) -> list[float]:
        """Compute the value of each grid ring, from the center out.

        Returns:
            The ring values; the last one is the top of the range.
        """
        if self.max_value is not None:
            return [
                self.max_value * step / self._TICKS for step in range(self._TICKS + 1)
            ]
        top = max((v for item in self.series for v in item.points), default=0.0)
        return nice_ticks(0.0, max(top, 0.0), count=self._TICKS)

    def _vertex(
        self, cx: float, cy: float, radius: float, axis: int
    ) -> tuple[float, float]:
        """Place a point on axis ``axis`` at ``radius`` from the center.

        Args:
            cx: The chart center x.
            cy: The chart center y.
            radius: The distance from the center.
            axis: The axis index.

        Returns:
            The ``(x, y)`` point.
        """
        return _point(cx, cy, radius, -90.0 + axis * 360.0 / len(self.axes))

    def _polygon(self, points: list[tuple[float, float]]) -> list[DrawCommand]:
        """Emit a closed polygon path.

        Args:
            points: The polygon vertices, in order.

        Returns:
            ``MoveTo`` + ``LineTo`` run + ``Close``.
        """
        commands: list[DrawCommand] = [MoveTo(x=points[0][0], y=points[0][1])]
        commands.extend(LineTo(x=px, y=py) for px, py in points[1:])
        commands.append(Close())
        return commands

    def _label(self, cx: float, cy: float, radius: float, axis: int) -> DrawText:
        """Place one axis label just outside the rim, aligned away from the center.

        Args:
            cx: The chart center x.
            cy: The chart center y.
            radius: The rim radius.
            axis: The axis index.

        Returns:
            The label's draw command.
        """
        text = self.axes[axis]
        degrees = -90.0 + axis * 360.0 / len(self.axes)
        px, py = _point(cx, cy, radius + 6.0, degrees)
        cosine = math.cos(math.radians(degrees))
        text_w = _estimate_text_width(text, self._AXIS_FONT)
        if cosine < -0.1:
            px -= text_w
        elif cosine <= 0.1:
            px -= text_w / 2.0
        sine = math.sin(math.radians(degrees))
        baseline = py + self._AXIS_FONT / 3.0 + sine * self._AXIS_FONT / 2.0
        return DrawText(
            text=text,
            x=round(px, _COORD_DECIMALS) + 0.0,
            y=round(baseline, _COORD_DECIMALS) + 0.0,
            size=self._AXIS_FONT,
            color=_color_floats(self._role(ColorRole.ON_SURFACE_VARIANT)),
        )

    def render(self) -> Widget:
        """Lower the radar into a ``Canvas`` of grid, spokes, series and labels.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        cx = self.width / 2.0
        cy = self.height / 2.0
        radius = max(0.0, min(self.width, self.height) / 2.0 - self._LABEL_GAP)
        count = len(self.axes)
        grid_floats = _color_floats(self._role(ColorRole.OUTLINE_VARIANT))
        commands: list[DrawCommand] = []
        if count == 0:
            return self._canvas(commands)
        rings = self._rings()
        top = rings[-1]
        if count >= 3:
            for ring in rings[1:]:
                ring_radius = ring / top * radius
                commands.extend(
                    self._polygon(
                        [self._vertex(cx, cy, ring_radius, a) for a in range(count)]
                    )
                )
                commands.append(StrokeCmd(color=grid_floats, width=0.5))
        for axis in range(count):
            end_x, end_y = self._vertex(cx, cy, radius, axis)
            commands.append(MoveTo(x=cx, y=cy))
            commands.append(LineTo(x=end_x, y=end_y))
            commands.append(StrokeCmd(color=grid_floats, width=0.5))
        if count >= 3:
            colors = self._series_colors(self.series)
            for item, color in zip(self.series, colors, strict=True):
                values = [
                    item.points[axis] if axis < len(item.points) else 0.0
                    for axis in range(count)
                ]
                points = [
                    self._vertex(cx, cy, min(max(value, 0.0), top) / top * radius, axis)
                    for axis, value in enumerate(values)
                ]
                polygon = self._polygon(points)
                commands.extend(polygon)
                commands.append(
                    FillCmd(color=_color_floats(color, alpha=self._FILL_OPACITY))
                )
                commands.extend(polygon)
                commands.append(StrokeCmd(color=_color_floats(color), width=2.0))
        commands.extend(self._label(cx, cy, radius, axis) for axis in range(count))
        return self._canvas(commands)
