"""Research / data-science components (Trilho H, phase H6).

The styled kit an academic researcher reaches for to show an ONNX /
``ort-vision-sdk`` result end to end: dashboard metric cards, a detection overlay
that boxes objects on top of an image, and the image-picker → result flow. Every
component lowers to **existing** primitives (composition) or to a ``Canvas``
command list (overlays) — no renderer change is needed, and **no new**
:class:`~tempest_core.style.Style` field, variant resolver or ``Canvas`` draw
command is introduced.

The charts that shipped here (:class:`ChartSeries`, :class:`LineChart`,
:class:`BarChart`) now live in :mod:`tempest_core.components.charts` beside the
area, pie and radar charts that share their palette and scale; they stay
importable from this module.

Design notes:

* **Detection boxes are normalized** ``[0, 1]`` ``xyxy`` (:class:`DetectionBox`),
  multiplied by the canvas width/height at ``render`` time. The engine takes **no**
  ``ort-vision-sdk`` dependency — a ``det.box.xyxy`` → :class:`DetectionBox`
  adapter belongs on the tempestroid side, not here.
* **The overlay emits only the existing draw vocabulary** — a box is a
  :class:`~tempest_core.widgets.DrawRect` + :class:`~tempest_core.widgets.StrokeCmd`
  and its caption a baseline-anchored :class:`~tempest_core.widgets.DrawText`. The
  command list is deterministic for fixed input, so the conformance suite pins
  it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import ConfigDict, Field

from tempest_core._model import _CoreModel
from tempest_core.components.base import merge_style
from tempest_core.components.cards import Card
from tempest_core.components.charts import (
    BarChart,
    ChartSeries,
    LineChart,
    _color_floats,  # pyright: ignore[reportPrivateUsage]
    _estimate_text_width,  # pyright: ignore[reportPrivateUsage]
)
from tempest_core.components.feedback import Badge, Stat
from tempest_core.components.mediainputs import ImagePicker
from tempest_core.style import (
    AlignItems,
    BadgeVariant,
    CardVariant,
    Style,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
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


def _no_boxes() -> list[DetectionBox]:
    """Provide a fresh, typed empty detection-box list for default factories.

    Returns:
        A new empty list of detection boxes.
    """
    return []


class DetectionBox(_CoreModel):
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
