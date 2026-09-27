"""Pure data-visualization helpers shared by every chart: scales and palette.

Two pieces make a set of charts read as one product rather than five screens that
each picked their own numbers and colors:

* **Scales.** :func:`nice_ticks` turns a data domain into axis ticks on a
  ``1 / 2 / 5 × 10ⁿ`` step, so an axis reads ``0 · 10 · 20 · 30`` instead of
  ``0.0 · 7.7 · 15.4 · 23.1``; :func:`linear_map` maps a value from that domain to
  pixels; :func:`format_tick` prints a tick with exactly the decimals its step
  needs. All three are pure, deterministic and reject non-finite input, because a
  ``nan`` that reaches a draw command destroys the whole patch batch (see
  :class:`~tempest_core._model._CoreModel`).
* **Palette.** :func:`chart_palette` derives N categorical colors from the theme
  — the chart's ``color_scheme`` role anchors the first color and each next one is
  rotated by the golden angle — and walks every color's tone until it clears
  :data:`CHART_MIN_CONTRAST` against the theme surface. The sequence is
  prefix-stable: series ``i`` gets the same color whether the chart has three
  series or eight, so a ``BarChart`` and a ``LineChart`` on the same screen agree.

The tempest-react-sdk ships its categorical palette as a fixed list of hex tokens
(``--tempest-chart-1…8``) and its ``scales.ts`` only maps values onto sequential
/ diverging token ramps; neither derives from a seed nor produces axis ticks. The
core derives both from the theme instead, because it has to render identically in
Qt, Compose and the DOM, where no stylesheet exists to hold the tokens.
"""

from __future__ import annotations

import colorsys
import math

from tempest_core.style import Color
from tempest_core.theme import Theme, current_theme
from tempest_core.tokens import (
    ColorRole,
    _tone_to_color,  # pyright: ignore[reportPrivateUsage]
    contrast_ratio,
)

__all__ = [
    "CHART_HUE_STEP",
    "CHART_MIN_CONTRAST",
    "CHART_MIN_SATURATION",
    "NICE_FACTORS",
    "NICE_THRESHOLDS",
    "chart_palette",
    "format_tick",
    "linear_map",
    "nice_step",
    "nice_ticks",
]

#: The minimum WCAG contrast every palette color keeps against the theme surface.
#: ``3.0`` is WCAG 2.1 success criterion 1.4.11 (non-text contrast), the criterion
#: that governs graphical objects such as a line, a bar or a pie slice. The 4.5:1
#: of 1.4.3 applies to text, and chart text (axis labels, legend) is painted with
#: the theme's ``on_surface`` roles, which the token set already holds to text
#: contrast. Demanding 4.5:1 of every series would push the light-mode palette
#: toward near-black and collapse the hues it exists to separate.
CHART_MIN_CONTRAST: float = 3.0

#: The hue rotation between consecutive palette colors, as a fraction of a turn:
#: the golden angle (``1 - 1/φ`` turns, ~137.5°). Unlike an even ``1/N`` split it
#: does not depend on N, which is what makes the palette prefix-stable, and it
#: keeps the first eight hues at least 32.5° apart.
CHART_HUE_STEP: float = 1.0 - 1.0 / ((1.0 + math.sqrt(5.0)) / 2.0)

#: The saturation floor applied to the rotated (non-anchor) palette colors. A
#: low-chroma anchor — a grey brand, a muted ``secondary`` — would otherwise give
#: every rotated hue the same grey; the floor keeps them distinguishable.
CHART_MIN_SATURATION: float = 0.6

#: The error thresholds that pick a tick step's mantissa, highest first: a raw
#: step whose mantissa is at least ``√50`` rounds to 10, at least ``√10`` to 5, at
#: least ``√2`` to 2, else 1. Each threshold is the geometric mean of the two
#: mantissas it separates, so the chosen step is the nice one closest to the raw
#: step on a log scale. Ported from d3-array's ``tickSpec`` (``e10``, ``e5``,
#: ``e2``, d3-array 3.2.4), the tick algorithm under the recharts axes the
#: tempest-react-sdk charts draw with.
NICE_THRESHOLDS: tuple[float, float, float] = (
    math.sqrt(50.0),
    math.sqrt(10.0),
    math.sqrt(2.0),
)

#: The mantissa each of :data:`NICE_THRESHOLDS` selects, in the same order; a
#: mantissa below every threshold selects 1.
NICE_FACTORS: tuple[int, int, int] = (10, 5, 2)

#: The tone a rotated palette color starts from on a light surface, before the
#: contrast walk darkens it.
_LIGHT_START_TONE: int = 50

#: The tone a rotated palette color starts from on a dark surface, before the
#: contrast walk lightens it.
_DARK_START_TONE: int = 65

#: How far one step of the contrast walk moves the tone.
_TONE_STEP: int = 5


def _require_finite(name: str, value: float) -> None:
    """Reject a non-finite number with an error that names its argument.

    Args:
        name: The argument name, echoed in the error.
        value: The value to check.

    Raises:
        ValueError: If ``value`` is ``nan``, ``inf`` or ``-inf``.
    """
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number, got {value!r}")


def _tick_increment(lo: float, hi: float, count: int) -> float:
    """Compute d3's signed tick increment for ``[lo, hi]`` cut into ~``count`` parts.

    A step of 1 or more is returned as itself; a fractional step is returned as
    the **negated inverse** (``-10`` for a step of ``0.1``) so ticks are computed
    as ``i / 10`` rather than ``i * 0.1`` — the division is exact where the
    multiplication accumulates binary error. Ported from d3-array's ``tickSpec``.

    Args:
        lo: The domain minimum (``lo < hi``).
        hi: The domain maximum.
        count: The desired number of intervals (at least 1).

    Returns:
        The step (positive) or the negated inverse step (negative).
    """
    raw = (hi - lo) / count
    power = math.floor(math.log10(raw))
    error = raw / 10.0**power
    factor = 1
    for threshold, candidate in zip(NICE_THRESHOLDS, NICE_FACTORS, strict=True):
        if error >= threshold:
            factor = candidate
            break
    if power < 0:
        return -(10.0**-power) / factor
    return 10.0**power * factor


def _step_of(increment: float) -> float:
    """Turn a signed d3 increment back into the plain step it encodes.

    Args:
        increment: A value from :func:`_tick_increment`.

    Returns:
        The positive step.
    """
    return 1.0 / -increment if increment < 0 else increment


def nice_step(lo: float, hi: float, *, count: int = 5) -> float:
    """Pick the ``1 / 2 / 5 × 10ⁿ`` step closest to cutting ``[lo, hi]`` in ``count``.

    The step is the nice number nearest (on a log scale) to ``(hi - lo) / count``,
    so the actual interval count lands near ``count`` — not always exactly on it.

    Args:
        lo: The domain minimum.
        hi: The domain maximum; must differ from ``lo``.
        count: The desired number of intervals; must be at least 1.

    Returns:
        The nice step.

    Raises:
        ValueError: If a bound is not finite, the bounds are equal, or
            ``count < 1``.
    """
    _require_finite("lo", lo)
    _require_finite("hi", hi)
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count!r}")
    if lo == hi:
        raise ValueError(f"lo and hi must differ, got {lo!r} for both")
    return _step_of(_tick_increment(min(lo, hi), max(lo, hi), count))


def nice_ticks(lo: float, hi: float, *, count: int = 5) -> list[float]:
    """Compute round, evenly spaced ticks that enclose ``[lo, hi]``.

    The domain is widened outward to the nearest step multiples (d3's
    ``scale.nice()``) and re-stepped until the step stops changing, so the first
    tick is at or below ``lo``, the last at or above ``hi``, and the pair can
    serve directly as the axis domain. The degenerate cases have a defined answer
    rather than a division by zero:

    * reversed bounds are swapped;
    * ``lo == hi == 0`` widens to ``[0, 1]``;
    * ``lo == hi != 0`` widens by 10% of ``|lo|`` on each side.

    Args:
        lo: The domain minimum.
        hi: The domain maximum.
        count: The desired number of intervals between ticks (at least 1).

    Returns:
        The ascending tick values, always at least two.

    Raises:
        ValueError: If ``lo`` or ``hi`` is not finite, or ``count < 1``.
    """
    _require_finite("lo", lo)
    _require_finite("hi", hi)
    if count < 1:
        raise ValueError(f"count must be at least 1, got {count!r}")
    if lo > hi:
        lo, hi = hi, lo
    if lo == hi:
        if lo == 0.0:
            hi = 1.0
        else:
            delta = abs(lo) * 0.1
            lo, hi = lo - delta, hi + delta
    increment = _tick_increment(lo, hi, count)
    for _attempt in range(10):
        if increment > 0:
            lo = math.floor(lo / increment) * increment
            hi = math.ceil(hi / increment) * increment
        else:
            lo = math.floor(lo * -increment) / -increment
            hi = math.ceil(hi * -increment) / -increment
        following = _tick_increment(lo, hi, count)
        if following == increment:
            break
        increment = following
    if increment > 0:
        first = round(lo / increment)
        last = round(hi / increment)
        return [index * increment + 0.0 for index in range(first, last + 1)]
    first = round(lo * -increment)
    last = round(hi * -increment)
    return [index / -increment + 0.0 for index in range(first, last + 1)]


def _decimals(step: float) -> int:
    """Count the decimals a tick on ``step`` needs to print exactly.

    Args:
        step: A positive nice step.

    Returns:
        ``0`` for a step of 1 or more, else the power-of-ten depth of the step
        (``1`` for 0.5, ``2`` for 0.05).
    """
    return max(0, -math.floor(math.log10(step) + 1e-9))


def format_tick(value: float, ticks: list[float]) -> str:
    """Print a tick with the decimals its axis step needs, and no more.

    Args:
        value: The tick value to print.
        ticks: The axis ticks (from :func:`nice_ticks`), used to read the step.

    Returns:
        The formatted value — ``"20"`` on a step of 10, ``"0.5"`` on 0.5, and
        never ``"-0"``.
    """
    step = ticks[1] - ticks[0] if len(ticks) > 1 else 1.0
    decimals = _decimals(step) if step > 0.0 else 0
    text = f"{value:.{decimals}f}"
    if text.startswith("-") and float(text) == 0.0:
        return text[1:]
    return text


def linear_map(
    value: float,
    domain: tuple[float, float],
    output: tuple[float, float],
) -> float:
    """Map ``value`` linearly from ``domain`` onto ``output``.

    A zero-width domain (every datum equal) maps to the middle of the output —
    the honest reading of "no variation", and the same answer the tempest-react-sdk
    ``normalize`` gives. Values outside the domain extrapolate; clamping is the
    caller's decision.

    Args:
        value: The value to map.
        domain: The ``(start, end)`` of the input range.
        output: The ``(start, end)`` of the output range (may be reversed, as a
            y axis in screen space is).

    Returns:
        The mapped value.

    Raises:
        ValueError: If any argument is not finite.
    """
    _require_finite("value", value)
    for bound in (*domain, *output):
        _require_finite("bound", bound)
    d0, d1 = domain
    r0, r1 = output
    if d0 == d1:
        return (r0 + r1) / 2.0
    return r0 + (value - d0) / (d1 - d0) * (r1 - r0)


def _darkens(surface: Color) -> bool:
    """Decide whether palette colors must go darker to separate from ``surface``.

    Chosen by which extreme contrasts more with the surface rather than by the
    theme mode, so a custom mid-tone surface still gets a walk that terminates:
    the better extreme always clears 4.58:1, above :data:`CHART_MIN_CONTRAST`.

    Args:
        surface: The surface the chart is painted on.

    Returns:
        ``True`` when the walk darkens (a light surface), ``False`` when it
        lightens.
    """
    black = Color(r=0, g=0, b=0, a=1.0)
    white = Color(r=255, g=255, b=255, a=1.0)
    return contrast_ratio(surface, black) >= contrast_ratio(surface, white)


def _walk_to_contrast(
    hue: float, saturation: float, tone: int, surface: Color, *, darken: bool
) -> Color:
    """Step a color's tone away from ``surface`` until it clears the contrast floor.

    Args:
        hue: The color hue, 0.0-1.0 (HLS convention).
        saturation: The color saturation, 0.0-1.0.
        tone: The starting tone, 0-100.
        surface: The surface the color must separate from.
        darken: Whether each step lowers the tone (else raises it).

    Returns:
        The first color on the walk with at least :data:`CHART_MIN_CONTRAST`
        against ``surface`` (the walk ends at pure black or white, which always
        clears it on the side :func:`_darkens` picked).
    """
    step = -_TONE_STEP if darken else _TONE_STEP
    current = max(0, min(100, tone))
    color = _tone_to_color(hue, saturation, current)
    limit = 0 if darken else 100
    while contrast_ratio(color, surface) < CHART_MIN_CONTRAST and current != limit:
        current = max(0, min(100, current + step))
        color = _tone_to_color(hue, saturation, current)
    return color


def chart_palette(
    count: int,
    *,
    theme: Theme | None = None,
    color_scheme: str = "primary",
    platform_dark_mode: bool = False,
) -> list[Color]:
    """Derive ``count`` distinguishable categorical colors from the theme.

    Color 0 is the ``color_scheme`` role itself, unchanged whenever it already
    clears :data:`CHART_MIN_CONTRAST` against the surface — so a single-series
    chart keeps painting exactly the role color it always did. Each next color
    rotates the anchor hue by :data:`CHART_HUE_STEP`, lifts its saturation to at
    least :data:`CHART_MIN_SATURATION`, and starts from a mode-appropriate tone.
    Every color, anchor included, then walks its tone away from the surface until
    it clears the contrast floor.

    The result is deterministic and prefix-stable:
    ``chart_palette(3) == chart_palette(8)[:3]``.

    Args:
        count: How many colors to emit; ``0`` yields an empty list.
        theme: The theme to derive from; defaults to :func:`current_theme`.
        color_scheme: The Material 3 role that anchors the palette.
        platform_dark_mode: The OS dark-mode flag, used to resolve ``SYSTEM``
            mode (typically :attr:`MediaQueryData.platform_dark_mode`).

    Returns:
        The palette colors, in series order.

    Raises:
        ValueError: If ``count`` is negative or ``color_scheme`` is not a
            :class:`~tempest_core.tokens.ColorRole`.
    """
    if count < 0:
        raise ValueError(f"count must not be negative, got {count!r}")
    resolved = theme if theme is not None else current_theme()
    anchor = resolved.color(color_scheme, platform_dark_mode=platform_dark_mode)
    surface = resolved.color(ColorRole.SURFACE, platform_dark_mode=platform_dark_mode)
    darken = _darkens(surface)
    hue, lightness, saturation = colorsys.rgb_to_hls(
        anchor.r / 255.0, anchor.g / 255.0, anchor.b / 255.0
    )
    colors: list[Color] = []
    for index in range(count):
        if index == 0:
            if contrast_ratio(anchor, surface) >= CHART_MIN_CONTRAST:
                colors.append(anchor)
            else:
                colors.append(
                    _walk_to_contrast(
                        hue,
                        saturation,
                        round(lightness * 100),
                        surface,
                        darken=darken,
                    )
                )
            continue
        colors.append(
            _walk_to_contrast(
                (hue + index * CHART_HUE_STEP) % 1.0,
                max(saturation, CHART_MIN_SATURATION),
                _LIGHT_START_TONE if darken else _DARK_START_TONE,
                surface,
                darken=darken,
            )
        )
    return colors
