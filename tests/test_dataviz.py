"""The shared chart scale and palette (issue #24).

Two things make a set of charts look like one product: the axes step on the same
round numbers, and series ``i`` is the same color everywhere. Both live in
``tempest_core.dataviz`` and are pure, so this file pins them exhaustively —
including the degenerate domains a hand-rolled axis always gets wrong, and the
WCAG non-text contrast of every color the palette can emit.
"""

from __future__ import annotations

import itertools
import math

import pytest

from tempest_core import (
    CHART_HUE_STEP,
    CHART_MIN_CONTRAST,
    CHART_MIN_SATURATION,
    NICE_FACTORS,
    NICE_THRESHOLDS,
    Theme,
    ThemeMode,
    chart_palette,
    format_tick,
    linear_map,
    nice_step,
    nice_ticks,
)
from tempest_core.dataviz import _darkens, _walk_to_contrast
from tempest_core.style import Color
from tempest_core.tokens import ColorRole, contrast_ratio

NON_FINITE: list[float] = [math.nan, math.inf, -math.inf]

SEEDS: list[Color | None] = [
    None,
    Color(r=22, g=163, b=74, a=1.0),
    Color(r=250, g=200, b=0, a=1.0),
    Color(r=120, g=120, b=120, a=1.0),
    Color(r=37, g=99, b=235, a=1.0),
    Color(r=220, g=38, b=38, a=1.0),
    Color(r=6, g=182, b=212, a=1.0),
]

SCHEMES: list[str] = [
    "primary",
    "secondary",
    "tertiary",
    "error",
    "success",
    "warning",
    "info",
]


def _theme(seed: Color | None, mode: ThemeMode) -> Theme:
    return Theme(mode=mode) if seed is None else Theme.from_seed(seed, mode=mode)


def _lab(color: Color) -> tuple[float, float, float]:
    """CIE L*a*b* (D65) of an sRGB color, for a perceptual distance check."""

    def linear(channel: int) -> float:
        value = channel / 255.0
        if value <= 0.04045:
            return value / 12.92
        return ((value + 0.055) / 1.055) ** 2.4

    r, g, b = linear(color.r), linear(color.g), linear(color.b)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1.0 / 3.0) if t > 0.008856 else 7.787 * t + 16.0 / 116.0

    return 116.0 * f(y) - 16.0, 500.0 * (f(x) - f(y)), 200.0 * (f(y) - f(z))


def _delta_e(a: Color, b: Color) -> float:
    return math.dist(_lab(a), _lab(b))


# --------------------------------------------------------------------------- #
# Ported constants
# --------------------------------------------------------------------------- #


def test_nice_thresholds_match_d3() -> None:
    """The step thresholds are d3-array's ``e10``/``e5``/``e2``, unchanged."""
    assert NICE_THRESHOLDS == (math.sqrt(50.0), math.sqrt(10.0), math.sqrt(2.0))
    assert NICE_FACTORS == (10, 5, 2)


def test_palette_constants() -> None:
    """The contrast floor is WCAG 1.4.11 and the hue step the golden angle."""
    assert CHART_MIN_CONTRAST == 3.0
    assert CHART_HUE_STEP == pytest.approx(0.3819660112501051)
    assert CHART_HUE_STEP * 360.0 == pytest.approx(137.50776405003785)
    assert CHART_MIN_SATURATION == 0.6


# --------------------------------------------------------------------------- #
# nice_step / nice_ticks
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("lo", "hi", "count", "expected"),
    [
        (0.0, 10.0, 10, 1.0),
        (0.0, 10.0, 5, 2.0),
        (0.0, 100.0, 4, 20.0),
        (0.0, 100.0, 2, 50.0),
        (0.0, 1.0, 5, 0.2),
        (0.0, 0.03, 3, 0.01),
        (0.0, 700.0, 1, 500.0),
        (0.0, 720.0, 1, 1000.0),
    ],
)
def test_nice_step_picks_1_2_5(
    lo: float, hi: float, count: int, expected: float
) -> None:
    assert nice_step(lo, hi, count=count) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("lo", "hi", "expected"),
    [
        (0.0, 40.0, [0.0, 10.0, 20.0, 30.0, 40.0]),
        (0.0, 23.1, [0.0, 5.0, 10.0, 15.0, 20.0, 25.0]),
        (12.0, 98.0, [0.0, 20.0, 40.0, 60.0, 80.0, 100.0]),
        (-3.0, 7.0, [-4.0, -2.0, 0.0, 2.0, 4.0, 6.0, 8.0]),
        (-50.0, -10.0, [-50.0, -40.0, -30.0, -20.0, -10.0]),
        (0.0, 0.3, [0.0, 0.1, 0.2, 0.3]),
    ],
)
def test_nice_ticks_known_domains(lo: float, hi: float, expected: list[float]) -> None:
    """Ticks are exact decimals: ``0.1 * 3`` is ``0.3``, not ``0.300…04``."""
    assert nice_ticks(lo, hi, count=4) == expected


def test_nice_ticks_zero_domain_widens_to_unit() -> None:
    """``[0, 0]`` has no scale of its own, so it becomes ``[0, 1]``."""
    ticks = nice_ticks(0.0, 0.0, count=4)
    assert ticks[0] == 0.0
    assert ticks[-1] == 1.0


@pytest.mark.parametrize("value", [5.0, -5.0, 0.001, 1e9])
def test_nice_ticks_single_value_is_enclosed(value: float) -> None:
    """All-equal data still gets a real axis around the value, not a division by 0."""
    ticks = nice_ticks(value, value, count=4)
    assert len(ticks) >= 2
    assert ticks[0] < value < ticks[-1]


def test_nice_ticks_swaps_reversed_bounds() -> None:
    assert nice_ticks(40.0, 0.0, count=4) == nice_ticks(0.0, 40.0, count=4)


def test_nice_ticks_enclose_and_space_evenly() -> None:
    """Over a sweep of domains the ticks enclose the data, evenly, near ``count``."""
    bounds = [-1234.5, -40.0, -3.0, -0.07, 0.0, 0.002, 1.0, 9.99, 250.0, 1e6]
    for lo, hi in itertools.combinations(bounds, 2):
        for count in (2, 4, 5, 10):
            ticks = nice_ticks(lo, hi, count=count)
            assert ticks[0] <= lo and ticks[-1] >= hi
            steps = [b - a for a, b in itertools.pairwise(ticks)]
            assert max(steps) == pytest.approx(min(steps))
            assert 1 <= len(steps) <= count * 3
            assert all(math.isfinite(t) for t in ticks)


@pytest.mark.parametrize("bad", NON_FINITE)
def test_nice_ticks_rejects_non_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        nice_ticks(bad, 1.0)
    with pytest.raises(ValueError, match="finite"):
        nice_ticks(0.0, bad)
    with pytest.raises(ValueError, match="finite"):
        nice_step(0.0, bad)


def test_nice_ticks_rejects_bad_count() -> None:
    with pytest.raises(ValueError, match="count"):
        nice_ticks(0.0, 1.0, count=0)
    with pytest.raises(ValueError, match="count"):
        nice_step(0.0, 1.0, count=0)


def test_nice_step_rejects_empty_domain() -> None:
    with pytest.raises(ValueError, match="differ"):
        nice_step(3.0, 3.0)


# --------------------------------------------------------------------------- #
# format_tick / linear_map
# --------------------------------------------------------------------------- #


def test_format_tick_uses_the_step_decimals() -> None:
    assert [format_tick(t, [0.0, 10.0]) for t in (0.0, 20.0)] == ["0", "20"]
    assert format_tick(1.5, [0.0, 0.5]) == "1.5"
    assert format_tick(0.04, [0.0, 0.02]) == "0.04"


def test_format_tick_never_prints_negative_zero() -> None:
    assert format_tick(-0.0, [-0.02, 0.0]) == "0.00"
    assert format_tick(-0.0001, [-10.0, 0.0]) == "0"


def test_linear_map_maps_and_reverses() -> None:
    assert linear_map(5.0, (0.0, 10.0), (0.0, 100.0)) == 50.0
    assert linear_map(0.0, (0.0, 10.0), (200.0, 0.0)) == 200.0
    assert linear_map(-5.0, (-10.0, 10.0), (0.0, 100.0)) == 25.0


def test_linear_map_zero_width_domain_is_the_midpoint() -> None:
    """Every datum equal reads as "no variation": the middle of the output."""
    assert linear_map(7.0, (7.0, 7.0), (0.0, 100.0)) == 50.0


@pytest.mark.parametrize("bad", NON_FINITE)
def test_linear_map_rejects_non_finite(bad: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        linear_map(bad, (0.0, 1.0), (0.0, 1.0))
    with pytest.raises(ValueError, match="finite"):
        linear_map(0.5, (0.0, bad), (0.0, 1.0))


# --------------------------------------------------------------------------- #
# chart_palette — contrast, anchor, stability, distinctness
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
@pytest.mark.parametrize("seed", SEEDS)
def test_every_palette_color_clears_non_text_contrast(
    seed: Color | None, mode: ThemeMode
) -> None:
    """WCAG 1.4.11: each emitted color is at least 3:1 against the surface."""
    theme = _theme(seed, mode)
    surface = theme.color(ColorRole.SURFACE)
    for scheme in SCHEMES:
        for color in chart_palette(12, theme=theme, color_scheme=scheme):
            assert contrast_ratio(color, surface) >= CHART_MIN_CONTRAST, (
                seed,
                mode,
                scheme,
                color,
            )


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
@pytest.mark.parametrize("seed", SEEDS)
def test_first_eight_palette_colors_are_distinguishable(
    seed: Color | None, mode: ThemeMode
) -> None:
    """Every pair among the first eight is at least ΔE*76 = 10 apart."""
    theme = _theme(seed, mode)
    for scheme in SCHEMES:
        palette = chart_palette(8, theme=theme, color_scheme=scheme)
        worst = min(_delta_e(a, b) for a, b in itertools.combinations(palette, 2))
        assert worst >= 10.0, (seed, mode, scheme, worst)


@pytest.mark.parametrize("mode", [ThemeMode.LIGHT, ThemeMode.DARK])
def test_palette_anchor_is_the_role_color(mode: ThemeMode) -> None:
    """Color 0 is the ``color_scheme`` role whenever the role clears the floor.

    So a one-series chart keeps painting exactly the role color it always did.
    """
    theme = Theme(mode=mode)
    surface = theme.color(ColorRole.SURFACE)
    for scheme in SCHEMES:
        role = theme.color(scheme)
        if contrast_ratio(role, surface) >= CHART_MIN_CONTRAST:
            assert chart_palette(1, theme=theme, color_scheme=scheme) == [role]


def test_palette_anchor_below_the_floor_is_walked() -> None:
    """A role that fails 3:1 on the surface is darkened, keeping its hue.

    Measured: the baseline light ``success`` role (``#22aa54``) sits at about
    2.9:1 on the light surface — the token set holds ``on_success`` on
    ``success`` to AA, not ``success`` on ``surface``.
    """
    theme = Theme(mode=ThemeMode.LIGHT)
    surface = theme.color(ColorRole.SURFACE)
    role = theme.color("success")
    assert contrast_ratio(role, surface) < CHART_MIN_CONTRAST
    (anchor,) = chart_palette(1, theme=theme, color_scheme="success")
    assert anchor != role
    assert contrast_ratio(anchor, surface) >= CHART_MIN_CONTRAST
    assert anchor.g > anchor.r and anchor.g > anchor.b


def test_palette_is_prefix_stable() -> None:
    """Series ``i`` gets the same color whatever the series count."""
    theme = Theme(mode=ThemeMode.LIGHT)
    eight = chart_palette(8, theme=theme)
    for count in range(9):
        assert chart_palette(count, theme=theme) == eight[:count]


def test_palette_follows_the_mode() -> None:
    """Dark mode derives its own colors instead of reusing the light ones."""
    light = chart_palette(4, theme=Theme(mode=ThemeMode.LIGHT))
    dark = chart_palette(4, theme=Theme(mode=ThemeMode.DARK))
    system_dark = chart_palette(
        4, theme=Theme(mode=ThemeMode.SYSTEM), platform_dark_mode=True
    )
    assert light != dark
    assert dark == system_dark


def test_palette_is_deterministic() -> None:
    theme = Theme.from_seed(Color(r=250, g=200, b=0, a=1.0))
    assert chart_palette(6, theme=theme) == chart_palette(6, theme=theme)


def test_palette_rejects_bad_input() -> None:
    assert chart_palette(0) == []
    with pytest.raises(ValueError, match="negative"):
        chart_palette(-1)
    with pytest.raises(ValueError):
        chart_palette(2, color_scheme="not-a-role")


@pytest.mark.parametrize(
    "surface",
    [
        Color(r=255, g=255, b=255, a=1.0),
        Color(r=119, g=119, b=119, a=1.0),
        Color(r=118, g=118, b=118, a=1.0),
        Color(r=18, g=18, b=18, a=1.0),
    ],
)
def test_contrast_walk_terminates_on_any_surface(surface: Color) -> None:
    """Even a mid-grey surface ends the walk above the floor, from any start."""
    darken = _darkens(surface)
    for tone in (0, 30, 50, 70, 100):
        for hue in (0.0, 0.17, 0.5, 0.66):
            color = _walk_to_contrast(hue, 1.0, tone, surface, darken=darken)
            assert contrast_ratio(color, surface) >= CHART_MIN_CONTRAST
