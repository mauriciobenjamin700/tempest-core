"""Research / data-science components (Trilho H, phase H6).

The styled kit an academic researcher reaches for to show an ONNX /
``ort-vision-sdk`` result end to end: dashboard metric cards, simple charts
(line / bar) drawn over the E7 :class:`~tempest_core.widgets.Canvas`, a detection
overlay that boxes objects on top of an image, and the image-picker → result
flow. Every component lowers to **existing** primitives (composition) or to a
``Canvas`` command list (charts / overlays) — no renderer change is needed, and
**no new** :class:`~tempest_core.style.Style` field, variant resolver or
``Canvas`` draw command is introduced.

Design notes:

* **Chart data is a frozen** :class:`ChartSeries` (``points`` + ``label`` +
  optional ``color_scheme``), not a bare list, so a chart can carry several
  named, individually-colored series. :class:`BarChart` additionally accepts a
  plain ``list[float]`` (+ ``labels``) for the trivial single-series case.
* **Detection boxes are normalized** ``[0, 1]`` ``xyxy`` (:class:`DetectionBox`),
  multiplied by the canvas width/height at ``render`` time. The engine takes **no**
  ``ort-vision-sdk`` dependency — a ``det.box.xyxy`` → :class:`DetectionBox`
  adapter belongs on the tempestroid side, not here.
* **Charts emit only the existing draw vocabulary** — a line is
  :class:`~tempest_core.widgets.MoveTo` + :class:`~tempest_core.widgets.LineTo` +
  :class:`~tempest_core.widgets.StrokeCmd` (there is no ``DrawLine``); a bar is a
  :class:`~tempest_core.widgets.DrawRect` + :class:`~tempest_core.widgets.FillCmd`;
  text is the baseline-anchored :class:`~tempest_core.widgets.DrawText` (no align
  field, so y-axis labels are right-aligned by estimating text width). The
  command list is deterministic for fixed input, so the conformance suite pins
  it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field

from tempest_core.components.base import merge_style
from tempest_core.components.cards import Card
from tempest_core.components.feedback import Badge, Stat
from tempest_core.components.mediainputs import ImagePicker
from tempest_core.style import (
    AlignItems,
    BadgeVariant,
    CardVariant,
    Color,
    Style,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.widgets import (
    Canvas,
    Column,
    Component,
    DrawCommand,
    DrawRect,
    DrawText,
    FillCmd,
    Image,
    ImageFit,
    LineTo,
    MoveTo,
    Row,
    Stack,
    StrokeCmd,
    Widget,
)

__all__ = [
    "ChartSeries",
    "DetectionBox",
    "confidence_scheme",
    "MetricCard",
    "StatCard",
    "ConfidenceBadge",
    "LineChart",
    "BarChart",
    "DetectionOverlay",
    "ResultView",
]


# --------------------------------------------------------------------------- #
# Value models + helpers
# --------------------------------------------------------------------------- #


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


def _no_boxes() -> list[DetectionBox]:
    """Provide a fresh, typed empty detection-box list for default factories.

    Returns:
        A new empty list of detection boxes.
    """
    return []


def _color_floats(color: Color) -> list[float]:
    """Lower a :class:`~tempest_core.style.Color` to a Canvas ``[r, g, b, a]`` list.

    The :class:`~tempest_core.widgets.Canvas` draw commands carry color as a list
    of floats in ``[0, 1]`` (never a ``Color`` object or a tuple, so the command
    is JSON-serializable directly). ``Color`` stores ``r``/``g``/``b`` as ``0-255``
    ints and ``a`` as a ``0-1`` float.

    Args:
        color: The color to lower.

    Returns:
        The ``[r, g, b, a]`` float list with the channels normalized to ``[0, 1]``.
    """
    return [color.r / 255.0, color.g / 255.0, color.b / 255.0, color.a]


class ChartSeries(BaseModel):
    """A single named, optionally-colored data series for a chart.

    A chart takes a list of these rather than bare ``list[float]`` so it can plot
    several series at once, each with its own label and (optionally) its own
    ``color_scheme``; an unset ``color_scheme`` lets the chart pick from its
    rotating themed palette by series index.

    Attributes:
        points: The series' y-values, in plot order (one per x position).
        label: An optional series label (e.g. for a legend; not drawn by the
            minimal v1 charts but carried for the renderers/legend to read).
        color_scheme: An optional Material 3 role family to color this series
            with; ``None`` falls back to the chart's rotating palette.
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
        "``None`` falls back to the chart's rotating palette.",
    )


class DetectionBox(BaseModel):
    """A normalized object-detection bounding box (``xyxy`` in ``[0, 1]``).

    Coordinates are fractions of the canvas width/height (``0`` = left/top, ``1`` =
    right/bottom), so a box is resolution-independent and multiplied by the
    canvas pixel size at draw time. This mirrors the common normalized-``xyxy``
    convention without depending on ``ort-vision-sdk`` — an adapter from a
    ``Detection`` result lives on the tempestroid side.

    Attributes:
        x1: The left edge as a fraction of the canvas width (``[0, 1]``).
        y1: The top edge as a fraction of the canvas height (``[0, 1]``).
        x2: The right edge as a fraction of the canvas width (``[0, 1]``).
        y2: The bottom edge as a fraction of the canvas height (``[0, 1]``).
        name: An optional class label drawn beside the box.
        conf: The detection confidence in ``[0, 1]`` (drives the box color and the
            label percentage).
    """

    model_config = ConfigDict(frozen=True)

    x1: float = Field(description="The left edge as a fraction of the width.")
    y1: float = Field(description="The top edge as a fraction of the height.")
    x2: float = Field(description="The right edge as a fraction of the width.")
    y2: float = Field(description="The bottom edge as a fraction of the height.")
    name: str = Field(default="", description="An optional class label.")
    conf: float = Field(
        default=1.0, description="The detection confidence in ``[0, 1]``."
    )


def confidence_scheme(conf: float, *, high: float = 0.8, mid: float = 0.5) -> str:
    """Map a confidence score to a status ``color_scheme``.

    The canonical traffic-light cue for a model's confidence: at or above
    ``high`` is ``"success"`` (green), at or above ``mid`` is ``"warning"``
    (amber), and below ``mid`` is ``"error"`` (red). Pure and deterministic, so
    every confidence-driven component (badge, detection box) colors consistently.

    Args:
        conf: The confidence score, typically in ``[0, 1]``.
        high: The inclusive threshold at or above which the score reads as high
            confidence (``"success"``).
        mid: The inclusive threshold at or above which the score reads as medium
            confidence (``"warning"``); below it reads as low (``"error"``).

    Returns:
        One of ``"success"`` / ``"warning"`` / ``"error"``.
    """
    if conf >= high:
        return "success"
    if conf >= mid:
        return "warning"
    return "error"


# --------------------------------------------------------------------------- #
# Metric / stat cards + confidence badge (composition)
# --------------------------------------------------------------------------- #


class MetricCard(Component):
    """A dashboard metric inside a themed card: label, value and optional trend.

    Composes the H3 :class:`~tempest_core.components.Card` (the surface) around the
    H4 :class:`~tempest_core.components.Stat` (the label/value/delta block), with
    an optional trailing slot (e.g. a sparkline :class:`LineChart` or an icon).
    No new primitive is introduced — it is ``Card`` + ``Stat``.

    Attributes:
        label: The metric's caption (muted).
        value: The metric's value (large, prominent).
        delta: An optional trend line (e.g. ``"+12%"``); ``None`` hides it.
        delta_up: Whether the delta is positive (success-tinted) or negative
            (error-tinted).
        color_scheme: The Material 3 role family the card surface tints with.
        variant: The card surface treatment (elevated / filled / outlined).
        trailing: An optional widget shown to the right of the stat block.
        theme: The design-system theme whose tokens resolve the surface and stat.
        media: Optional viewport snapshot (accepted for parity; unused).
    """

    default_key: ClassVar[str] = "metric-card"

    label: str = Field(default="", description="The metric's caption (muted).")
    value: str = Field(default="", description="The metric's value (prominent).")
    delta: str | None = Field(
        default=None, description='An optional trend line (e.g. ``"+12%"``).'
    )
    delta_up: bool = Field(
        default=True,
        description="Whether the delta is positive (success) or negative (error).",
    )
    color_scheme: str = Field(
        default="neutral",
        description="The Material 3 role family the card surface tints with.",
    )
    variant: CardVariant = Field(
        default=CardVariant.ELEVATED,
        description="The card surface treatment (elevated / filled / outlined).",
    )
    trailing: Widget | None = Field(
        default=None,
        description="An optional widget shown to the right of the stat block.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; unused).",
    )

    def _stat(self) -> Widget:
        """Build the inner :class:`~tempest_core.components.Stat` block.

        Returns:
            A ``Stat`` carrying the label/value/delta, growing to fill the card.
        """
        return Stat(
            label=self.label,
            value=self.value,
            delta=self.delta,
            delta_up=self.delta_up,
            theme=self.theme,
            style=Style(grow=1.0),
            key=self.child_key("stat"),
        )

    def render(self) -> Widget:
        """Lower the metric card into a themed card wrapping a stat.

        Returns:
            A :class:`~tempest_core.components.Card` containing the stat block and,
            when set, a trailing widget laid out in a centered ``Row``-like column.
        """
        if self.trailing is not None:
            body: Widget = Row(
                style=Style(gap=self.theme.space("md"), align=AlignItems.CENTER),
                children=[self._stat(), self.trailing],
                key=self.child_key("row"),
            )
        else:
            body = self._stat()
        return Card(
            key=self.base_key,
            variant=self.variant,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
            style=self.style,
            children=[body],
        )


class StatCard(MetricCard):
    """A compact preset of :class:`MetricCard` (a filled, tighter card).

    Exactly a :class:`MetricCard` with a denser default surface (``filled``,
    smaller padding) — handy for a tight grid of stats. Every ``MetricCard`` prop
    still applies; override ``variant`` / ``padding`` via ``style`` to retune.

    Attributes:
        variant: Defaults to ``filled`` for the compact look (overridable).
    """

    default_key: ClassVar[str] = "stat-card"

    variant: CardVariant = Field(
        default=CardVariant.FILLED,
        description="The card surface treatment (defaults to ``filled``).",
    )


class ConfidenceBadge(Component):
    """A status pill showing a model's confidence, colored by threshold.

    Composes the H4 :class:`~tempest_core.components.Badge`, picking its
    ``color_scheme`` from :func:`confidence_scheme` (success / warning / error)
    and labelling it as a rounded percentage (``"92%"``). Optionally prefixes a
    class name (``"cat 92%"``).

    Attributes:
        confidence: The model confidence in ``[0, 1]``.
        label: An optional prefix (e.g. the predicted class) shown before the
            percentage.
        high: The success threshold passed to :func:`confidence_scheme`.
        mid: The warning threshold passed to :func:`confidence_scheme`.
        theme: The design-system theme whose tokens resolve the pill.
    """

    default_key: ClassVar[str] = "confidence-badge"

    confidence: float = Field(description="The model confidence in ``[0, 1]``.")
    label: str = Field(
        default="",
        description="An optional prefix shown before the percentage.",
    )
    high: float = Field(
        default=0.8, description="The success threshold (see ``confidence_scheme``)."
    )
    mid: float = Field(
        default=0.5, description="The warning threshold (see ``confidence_scheme``)."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the pill.",
    )

    def render(self) -> Widget:
        """Lower the confidence badge into a themed status pill.

        Returns:
            A :class:`~tempest_core.components.Badge` whose ``color_scheme`` and
            label encode the confidence.

        Note:
            ``SUBTLE`` uses the tonal container pair (WCAG-AA safe), unlike
            ``SOLID``, which paints white on the saturated status role (success
            ~3.02, warning ~4.0 — both fail AA). Consistent with the H4 A1
            decision.
        """
        scheme = confidence_scheme(self.confidence, high=self.high, mid=self.mid)
        percent = f"{self.confidence:.0%}"
        text = f"{self.label} {percent}".strip() if self.label else percent
        return Badge(
            key=self.base_key,
            label=text,
            color_scheme=scheme,
            variant=BadgeVariant.SUBTLE,
            theme=self.theme,
            style=self.style,
        )


# --------------------------------------------------------------------------- #
# Charts (Canvas command list)
# --------------------------------------------------------------------------- #

#: The rotating palette of Material 3 role families a multi-series chart cycles
#: through when a series does not name its own ``color_scheme``. The renderers
#: resolve each against the theme to a concrete color before lowering to a
#: Canvas command's float list.
_CHART_PALETTE: tuple[str, ...] = (
    "primary",
    "secondary",
    "tertiary",
    "error",
    "success",
    "warning",
    "info",
)


def _nice_bounds(values: list[float]) -> tuple[float, float]:
    """Compute a padded ``(min, max)`` plot range for a set of y-values.

    Includes ``0`` in the range (so bars/lines have a meaningful baseline) and
    pads the top by ~5% so the topmost point is not flush against the frame. A
    degenerate (all-equal) range is widened to ``[v - 1, v + 1]`` so the mapping
    never divides by zero.

    Args:
        values: The y-values across every series.

    Returns:
        The ``(y_min, y_max)`` plot bounds.
    """
    if not values:
        return 0.0, 1.0
    lo = min(0.0, min(values))
    hi = max(0.0, max(values))
    if hi == lo:
        return lo - 1.0, hi + 1.0
    pad = (hi - lo) * 0.05
    return lo, hi + pad


def _estimate_text_width(text: str, size: float) -> float:
    """Estimate a text run's pixel width (no font metrics available in the engine).

    The :class:`~tempest_core.widgets.DrawText` command is baseline-anchored with
    no alignment field, so to right-align a y-axis label we shift its anchor left
    by an estimate of its width. A flat per-character factor (~0.6 of the font
    size) is plenty for axis tick labels.

    Args:
        text: The text run.
        size: The font size, in logical pixels.

    Returns:
        The estimated width, in logical pixels.
    """
    return len(text) * size * 0.6


class _ChartBase(Component):
    """Shared geometry/state for the Canvas-backed charts.

    Holds the canvas size, axis insets, label font size and the theme; subclasses
    only emit the series geometry. Not exported — concrete charts are
    :class:`LineChart` / :class:`BarChart`.

    Attributes:
        width: The canvas width, in logical pixels.
        height: The canvas height, in logical pixels.
        color_scheme: The default Material 3 role family for an unnamed series.
        theme: The design-system theme whose tokens supply colors.
    """

    width: float = Field(default=320.0, description="The canvas width, in pixels.")
    height: float = Field(default=200.0, description="The canvas height, in pixels.")
    color_scheme: str = Field(
        default="primary",
        description="The default Material 3 role family for an unnamed series.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply colors.",
    )

    #: The plot insets (left for y labels, bottom for x labels, top/right pad).
    _PAD_LEFT: ClassVar[float] = 40.0
    _PAD_BOTTOM: ClassVar[float] = 24.0
    _PAD_TOP: ClassVar[float] = 12.0
    _PAD_RIGHT: ClassVar[float] = 12.0
    _AXIS_FONT: ClassVar[float] = 11.0
    _TICKS: ClassVar[int] = 4

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

    def _series_color(self, series: ChartSeries, index: int) -> Color:
        """Resolve a series' concrete color from its scheme or the palette.

        Args:
            series: The series being colored.
            index: The series' position (used to rotate the default palette).

        Returns:
            The concrete color for the series.
        """
        scheme = series.color_scheme or _CHART_PALETTE[index % len(_CHART_PALETTE)]
        return self.theme.color(scheme)

    def _axes_commands(self, y_min: float, y_max: float) -> list[DrawCommand]:
        """Emit the axis frame, y-tick gridlines and right-aligned y labels.

        A line is :class:`~tempest_core.widgets.MoveTo` + ``LineTo`` + ``StrokeCmd``
        (there is no ``DrawLine``). Y-axis labels are right-aligned by shifting
        their baseline-anchor left by an estimated text width.

        Args:
            y_min: The plot range minimum.
            y_max: The plot range maximum.

        Returns:
            The axis/grid/label draw commands.
        """
        x, y, w, h = self._plot_rect()
        outline = self.theme.color(ColorRole.OUTLINE_VARIANT)
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        axis_floats = _color_floats(outline)
        label_floats = _color_floats(on_surface_variant)
        commands: list[DrawCommand] = []

        # Y axis (left rule) and X axis (bottom rule) as two strokes.
        commands.append(MoveTo(x=x, y=y))
        commands.append(LineTo(x=x, y=y + h))
        commands.append(LineTo(x=x + w, y=y + h))
        commands.append(StrokeCmd(color=axis_floats, width=1.0))

        # Horizontal gridlines + right-aligned y tick labels.
        span = y_max - y_min
        for tick in range(self._TICKS + 1):
            frac = tick / self._TICKS
            py = y + h - frac * h
            value = y_min + frac * span
            commands.append(MoveTo(x=x, y=py))
            commands.append(LineTo(x=x + w, y=py))
            commands.append(StrokeCmd(color=axis_floats, width=0.5))
            text = f"{value:.1f}"
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


class LineChart(_ChartBase):
    """A multi-series line chart drawn over a :class:`~tempest_core.widgets.Canvas`.

    Each :class:`ChartSeries` becomes a connected polyline
    (:class:`~tempest_core.widgets.MoveTo` + a run of
    :class:`~tempest_core.widgets.LineTo` + one
    :class:`~tempest_core.widgets.StrokeCmd`) over a shared, framed plot rect with
    y-axis gridlines and right-aligned tick labels. The command list is
    deterministic for fixed input, so the conformance suite pins it. No new draw
    command is introduced.

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
        x, y, w, h = self._plot_rect()
        all_values = [v for s in self.series for v in s.points]
        y_min, y_max = _nice_bounds(all_values)
        span = y_max - y_min
        commands: list[DrawCommand] = self._axes_commands(y_min, y_max)

        for index, series in enumerate(self.series):
            n = len(series.points)
            if n == 0:
                continue
            color_floats = _color_floats(self._series_color(series, index))
            step = w / (n - 1) if n > 1 else 0.0
            for point_index, value in enumerate(series.points):
                px = x + point_index * step
                frac = (value - y_min) / span if span else 0.0
                py = y + h - frac * h
                if point_index == 0:
                    commands.append(MoveTo(x=px, y=py))
                else:
                    commands.append(LineTo(x=px, y=py))
            commands.append(StrokeCmd(color=color_floats, width=2.0))

        return Canvas(
            key=self.base_key,
            commands=commands,
            width=self.width,
            height=self.height,
            style=self.style,
        )


class BarChart(_ChartBase):
    """A bar chart drawn over a :class:`~tempest_core.widgets.Canvas`.

    Accepts either a list of :class:`ChartSeries` (the first series' points become
    the bars) or, for the trivial single-series case, a plain ``values`` list
    (+ optional ``labels``). Each bar is a
    :class:`~tempest_core.widgets.DrawRect` + a
    :class:`~tempest_core.widgets.FillCmd` over the shared framed plot rect; the
    command list is deterministic, so the conformance suite pins it. No new draw
    command is introduced.

    Attributes:
        series: The data series (the first series is plotted as bars). Optional
            when ``values`` is given.
        values: A convenience single-series value list (used when ``series`` is
            empty).
        labels: Optional x-axis labels for the bars.
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

    def _bars(self) -> tuple[list[float], str | None]:
        """Resolve the bar y-values and their color scheme.

        ``series`` wins when present (its first series); otherwise ``values`` is
        used as a single, default-colored series.

        Returns:
            The bar values and an optional explicit ``color_scheme`` (``None``
            falls back to the chart default).
        """
        if self.series:
            first = self.series[0]
            return list(first.points), first.color_scheme
        return list(self.values), None

    def render(self) -> Widget:
        """Lower the bar chart into a ``Canvas`` of axis + bar commands.

        Returns:
            A :class:`~tempest_core.widgets.Canvas` carrying the deterministic
            draw-command list.
        """
        x, y, w, h = self._plot_rect()
        values, scheme = self._bars()
        y_min, y_max = _nice_bounds(values)
        span = y_max - y_min
        commands: list[DrawCommand] = self._axes_commands(y_min, y_max)

        color = self.theme.color(scheme or self.color_scheme)
        color_floats = _color_floats(color)
        n = len(values)
        baseline_frac = (0.0 - y_min) / span if span else 0.0
        baseline_y = y + h - baseline_frac * h
        if n > 0:
            slot = w / n
            bar_w = slot * 0.7
            gap = (slot - bar_w) / 2.0
            for index, value in enumerate(values):
                frac = (value - y_min) / span if span else 0.0
                top = y + h - frac * h
                bar_x = x + index * slot + gap
                bar_h = baseline_y - top
                commands.append(DrawRect(x=bar_x, y=top, width=bar_w, height=bar_h))
                commands.append(FillCmd(color=color_floats))

        return Canvas(
            key=self.base_key,
            commands=commands,
            width=self.width,
            height=self.height,
            style=self.style,
        )


# --------------------------------------------------------------------------- #
# Detection overlay (image + Canvas boxes)
# --------------------------------------------------------------------------- #


class DetectionOverlay(Component):
    """An image with object-detection boxes drawn on top of it.

    Lowers to a :class:`~tempest_core.widgets.Stack` of a base
    :class:`~tempest_core.widgets.Image` (``fit=COVER``) and a
    :class:`~tempest_core.widgets.Canvas` overlay. Each :class:`DetectionBox`
    (normalized ``xyxy``) is multiplied by the canvas size and drawn as a stroked
    rectangle (:class:`~tempest_core.widgets.DrawRect` +
    :class:`~tempest_core.widgets.StrokeCmd`) colored by
    :func:`confidence_scheme`, with a small filled label background
    (:class:`~tempest_core.widgets.DrawRect` +
    :class:`~tempest_core.widgets.FillCmd`) and a ``"{name} {conf:.0%}"`` caption
    (:class:`~tempest_core.widgets.DrawText`). No new draw command is introduced.

    Attributes:
        image_src: The image source (URL or asset path) to box over.
        boxes: The normalized detection boxes to draw.
        width: The canvas/image width, in logical pixels.
        height: The canvas/image height, in logical pixels.
        high: The success threshold passed to :func:`confidence_scheme`.
        mid: The warning threshold passed to :func:`confidence_scheme`.
        theme: The design-system theme whose tokens supply the label color.
    """

    default_key: ClassVar[str] = "detection-overlay"

    image_src: str = Field(description="The image source to box over.")
    boxes: list[DetectionBox] = Field(
        description="The normalized detection boxes to draw.",
        default_factory=_no_boxes,
    )
    width: float = Field(default=320.0, description="The canvas width, in pixels.")
    height: float = Field(default=320.0, description="The canvas height, in pixels.")
    high: float = Field(
        default=0.8, description="The success threshold (see ``confidence_scheme``)."
    )
    mid: float = Field(
        default=0.5, description="The warning threshold (see ``confidence_scheme``)."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply the label color.",
    )

    _LABEL_FONT: ClassVar[float] = 12.0

    def _box_commands(self, box: DetectionBox) -> list[DrawCommand]:
        """Emit the draw commands for one detection box.

        Args:
            box: The normalized detection box.

        Returns:
            A stroked rectangle, a filled label background and the caption text.
        """
        scheme = confidence_scheme(box.conf, high=self.high, mid=self.mid)
        color = self.theme.color(scheme)
        color_floats = _color_floats(color)
        on_color = self.theme.color(f"on_{scheme}")
        px1 = box.x1 * self.width
        py1 = box.y1 * self.height
        px2 = box.x2 * self.width
        py2 = box.y2 * self.height
        commands: list[DrawCommand] = [
            DrawRect(x=px1, y=py1, width=px2 - px1, height=py2 - py1),
            StrokeCmd(color=color_floats, width=2.0),
        ]
        caption = f"{box.name} {box.conf:.0%}".strip()
        if caption:
            text_w = _estimate_text_width(caption, self._LABEL_FONT)
            label_h = self._LABEL_FONT + 4.0
            commands.append(
                DrawRect(x=px1, y=py1 - label_h, width=text_w + 6.0, height=label_h)
            )
            commands.append(FillCmd(color=color_floats))
            commands.append(
                DrawText(
                    text=caption,
                    x=px1 + 3.0,
                    y=py1 - 4.0,
                    size=self._LABEL_FONT,
                    color=_color_floats(on_color),
                )
            )
        return commands

    def render(self) -> Widget:
        """Lower the overlay into a stack of an image and a box canvas.

        Returns:
            A :class:`~tempest_core.widgets.Stack` of the base image and the
            detection-box canvas, sized to ``width`` × ``height``.
        """
        commands: list[DrawCommand] = []
        for box in self.boxes:
            commands.extend(self._box_commands(box))
        size_style = Style(width=self.width, height=self.height)
        image = Image(
            src=self.image_src,
            fit=ImageFit.COVER,
            style=size_style,
            key=self.child_key("image"),
        )
        canvas = Canvas(
            commands=commands,
            width=self.width,
            height=self.height,
            key=self.child_key("canvas"),
        )
        return Stack(
            key=self.base_key,
            style=merge_style(size_style, self.style),
            children=[image, canvas],
        )


# --------------------------------------------------------------------------- #
# Image picker → result flow (composition)
# --------------------------------------------------------------------------- #


class ResultView(Component):
    """The image-picker → result flow: pick an image, then show its result.

    Stacks an :class:`~tempest_core.components.ImagePicker` over an optional
    ``result`` slot — the widget the app builds from the model output (e.g. a
    :class:`DetectionOverlay`, a :class:`MetricCard`, a :class:`ConfidenceBadge`
    or a chart). The app owns the inference + builds the result; this component
    only arranges the picker and the result.

    Attributes:
        value: The picked image URI (forwarded to the picker; ``""`` until one is
            chosen).
        label: An optional heading shown above the picker.
        on_pick: Called with the picked image URI on selection.
        result: The optional result widget shown below the picker; ``None`` shows
            only the picker.
        theme: The design-system theme whose tokens supply the spacing.
    """

    default_key: ClassVar[str] = "result-view"

    value: str = Field(
        default="", description="The picked image URI (empty until one is chosen)."
    )
    label: str = Field(
        default="", description="An optional heading shown above the picker."
    )
    on_pick: Callable[[str], Any] = Field(
        description="Called with the picked image URI on selection."
    )
    result: Widget | None = Field(
        default=None,
        description="The optional result widget shown below the picker.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply the spacing.",
    )

    def render(self) -> Widget:
        """Lower the result view into a column of the picker and the result.

        Returns:
            A :class:`~tempest_core.widgets.Column` of the
            :class:`~tempest_core.components.ImagePicker` and, when set, the result
            widget.
        """
        children: list[Widget] = [
            ImagePicker(
                value=self.value,
                label=self.label,
                on_pick=self.on_pick,
                key=self.child_key("picker"),
            )
        ]
        if self.result is not None:
            children.append(self.result)
        default = Style(gap=self.theme.space("md"))
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=children,
        )
