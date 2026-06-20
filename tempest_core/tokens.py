"""Material 3 design-token foundation (Trilho H, phase H0).

This module is the **token layer** of the design system: the typed, frozen
value objects that a :class:`~tempest_core.theme.Theme` resolves and that a
:class:`~tempest_core.style.Style` can *reference* (instead of hard-coding a raw
value). It mirrors the Material 3 token model — a **tonal palette** generated
from a seed/brand color, a set of named **color schemes** (the M3 color roles
for light and dark), plus the systematic scales for **spacing**, **shape**
(radius), **typography**, **elevation** and **motion**.

The design follows the Chakra ergonomics goal of Trilho H: a researcher seeds a
brand color, gets a full M3 palette for free, and components ask the theme for a
token (``primary``, ``space("md")``, ``radius("lg")``…) rather than wiring raw
``Style`` values by hand. Everything here is **additive and
backward-compatible**: raw ``Style`` values keep working unchanged; a token is
just an alternative, resolvable source for a value.

All models are frozen (immutable value objects), so the reconciler can keep
diffing by value and the runtime can swap a whole theme wholesale.

The tonal-palette generation is **dependency-free**: rather than pulling the
full ``material-color-utilities`` HCT pipeline, it derives the thirteen standard
M3 tones (0, 10, 20, …, 95, 99, 100) from the seed by mapping the tone value to
a perceptual lightness in HSL while preserving the seed's hue and a
tone-dependent chroma falloff. This is the documented lightweight approximation
of an M3 tonal palette and is deterministic, which is what the conformance suite
pins.
"""

from __future__ import annotations

import colorsys
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from tempest_core.style import Color, Curve, FontWeight

__all__ = [
    "TonalPalette",
    "ColorScheme",
    "ColorSchemes",
    "SpacingScale",
    "ShapeScale",
    "TypographyToken",
    "TypographyScale",
    "ElevationScale",
    "MotionScale",
    "Breakpoints",
    "TokenSet",
    "TokenRef",
    "ColorRole",
    "default_tokens",
    "tonal_palette_from_seed",
    "color_schemes_from_seed",
]

#: The thirteen standard Material 3 tone steps of a tonal palette.
#: A tone of ``0`` is pure black, ``100`` pure white; the named roles read
#: specific tones (light ``primary`` is tone 40, dark ``primary`` tone 80).
TONES: tuple[int, ...] = (0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 100)


class ColorRole(StrEnum):
    """The Material 3 color roles a :class:`ColorScheme` exposes.

    These are the semantic slots components paint against — never raw tones.
    Each ``on_*`` role is the legible foreground for its base role and is
    generated to meet WCAG-AA contrast against it.

    Attributes:
        PRIMARY: The highest-emphasis brand color (key actions, active state).
        ON_PRIMARY: Legible content drawn on top of ``PRIMARY``.
        PRIMARY_CONTAINER: A tonal, lower-emphasis fill derived from primary.
        ON_PRIMARY_CONTAINER: Content drawn on ``PRIMARY_CONTAINER``.
        SECONDARY: A complementary, lower-emphasis accent.
        ON_SECONDARY: Content drawn on ``SECONDARY``.
        SECONDARY_CONTAINER: A tonal fill derived from secondary.
        ON_SECONDARY_CONTAINER: Content drawn on ``SECONDARY_CONTAINER``.
        TERTIARY: A contrasting accent used to balance primary/secondary.
        ON_TERTIARY: Content drawn on ``TERTIARY``.
        TERTIARY_CONTAINER: A tonal fill derived from tertiary.
        ON_TERTIARY_CONTAINER: Content drawn on ``TERTIARY_CONTAINER``.
        ERROR: The role signalling errors and destructive actions.
        ON_ERROR: Content drawn on ``ERROR``.
        ERROR_CONTAINER: A tonal error fill.
        ON_ERROR_CONTAINER: Content drawn on ``ERROR_CONTAINER``.
        BACKGROUND: The screen background.
        ON_BACKGROUND: Content drawn on ``BACKGROUND``.
        SURFACE: The base surface of cards, sheets and menus.
        ON_SURFACE: Content drawn on ``SURFACE``.
        SURFACE_VARIANT: A subtly differentiated surface for dividers/fills.
        ON_SURFACE_VARIANT: Lower-emphasis content on a surface.
        OUTLINE: The color of borders and dividers.
        OUTLINE_VARIANT: A lower-emphasis outline.
        INVERSE_SURFACE: A surface inverted relative to the scheme (snackbars).
        INVERSE_ON_SURFACE: Content drawn on ``INVERSE_SURFACE``.
        INVERSE_PRIMARY: The primary color as it appears on an inverse surface.
    """

    PRIMARY = "primary"
    ON_PRIMARY = "on_primary"
    PRIMARY_CONTAINER = "primary_container"
    ON_PRIMARY_CONTAINER = "on_primary_container"
    SECONDARY = "secondary"
    ON_SECONDARY = "on_secondary"
    SECONDARY_CONTAINER = "secondary_container"
    ON_SECONDARY_CONTAINER = "on_secondary_container"
    TERTIARY = "tertiary"
    ON_TERTIARY = "on_tertiary"
    TERTIARY_CONTAINER = "tertiary_container"
    ON_TERTIARY_CONTAINER = "on_tertiary_container"
    ERROR = "error"
    ON_ERROR = "on_error"
    ERROR_CONTAINER = "error_container"
    ON_ERROR_CONTAINER = "on_error_container"
    BACKGROUND = "background"
    ON_BACKGROUND = "on_background"
    SURFACE = "surface"
    ON_SURFACE = "on_surface"
    SURFACE_VARIANT = "surface_variant"
    ON_SURFACE_VARIANT = "on_surface_variant"
    OUTLINE = "outline"
    OUTLINE_VARIANT = "outline_variant"
    INVERSE_SURFACE = "inverse_surface"
    INVERSE_ON_SURFACE = "inverse_on_surface"
    INVERSE_PRIMARY = "inverse_primary"


def _relative_luminance(color: Color) -> float:
    """Compute the WCAG relative luminance of a color.

    Args:
        color: The color to measure (alpha is ignored — luminance is opaque).

    Returns:
        The relative luminance, 0.0 (black) to 1.0 (white).
    """

    def _channel(value: int) -> float:
        srgb = value / 255.0
        if srgb <= 0.03928:
            return srgb / 12.92
        return float(((srgb + 0.055) / 1.055) ** 2.4)

    r = _channel(color.r)
    g = _channel(color.g)
    b = _channel(color.b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a: Color, b: Color) -> float:
    """Compute the WCAG contrast ratio between two colors.

    Args:
        a: The first color.
        b: The second color.

    Returns:
        The contrast ratio, 1.0 (identical) to 21.0 (black on white).
    """
    la = _relative_luminance(a)
    lb = _relative_luminance(b)
    lighter = max(la, lb)
    darker = min(la, lb)
    return (lighter + 0.05) / (darker + 0.05)


def _tone_to_color(hue: float, saturation: float, tone: int) -> Color:
    """Build the palette color at a given M3 tone.

    The tone maps to HSL lightness (``tone / 100``); chroma (saturation) is
    attenuated near the extremes (very dark / very light tones desaturate), the
    same falloff M3 applies so tone 0/100 are near-neutral.

    Args:
        hue: The seed hue, 0.0-1.0 (HLS convention).
        saturation: The seed saturation, 0.0-1.0.
        tone: The M3 tone, 0-100.

    Returns:
        The color at that tone.
    """
    lightness = tone / 100.0
    # Desaturate as the tone approaches pure black/white (chroma falls off at
    # the extremes), mirroring M3's tonal-palette behaviour.
    falloff = 1.0 - abs(lightness - 0.5) * 2.0
    sat = saturation * (0.35 + 0.65 * falloff)
    r, g, b = colorsys.hls_to_rgb(hue, lightness, sat)
    return Color(
        r=round(r * 255),
        g=round(g * 255),
        b=round(b * 255),
        a=1.0,
    )


class TonalPalette(BaseModel):
    """A Material 3 tonal palette: one hue sampled at the standard tones.

    Generated from a single key color via :func:`tonal_palette_from_seed`; the
    color schemes read specific tones from it (light ``primary`` = tone 40, dark
    ``primary`` = tone 80, etc.). Frozen so it diffs by value.

    Attributes:
        tones: Mapping of each standard M3 tone (0-100) to its color.

    Methods:
        tone: Read the color at a given tone (nearest standard tone).
    """

    model_config = ConfigDict(frozen=True)

    tones: dict[int, Color]

    def tone(self, value: int) -> Color:
        """Read the palette color at a tone, snapping to the nearest standard tone.

        Args:
            value: The desired tone, 0-100.

        Returns:
            The color at the nearest available standard tone.
        """
        if value in self.tones:
            return self.tones[value]
        nearest = min(self.tones, key=lambda t: abs(t - value))
        return self.tones[nearest]


def tonal_palette_from_seed(seed: Color) -> TonalPalette:
    """Generate a Material 3 tonal palette from a seed/brand color.

    The seed's hue and saturation are preserved while lightness is swept across
    the thirteen standard M3 tones; chroma is attenuated at the extremes. The
    result is deterministic for a given seed.

    Args:
        seed: The key/brand color to derive the palette from.

    Returns:
        The tonal palette sampling the seed's hue at every standard tone.
    """
    hue, _lightness, saturation = colorsys.rgb_to_hls(
        seed.r / 255.0,
        seed.g / 255.0,
        seed.b / 255.0,
    )
    return TonalPalette(
        tones={tone: _tone_to_color(hue, saturation, tone) for tone in TONES}
    )


class ColorScheme(BaseModel):
    """A resolved Material 3 color scheme — every role as a concrete color.

    One scheme is the full set of M3 roles for a single mode (light or dark).
    Built from tonal palettes via :func:`color_schemes_from_seed`, or supplied
    directly to fully hand-author a brand scheme. Frozen so it diffs by value.

    Attributes:
        primary: The ``PRIMARY`` role color.
        on_primary: The ``ON_PRIMARY`` role color.
        primary_container: The ``PRIMARY_CONTAINER`` role color.
        on_primary_container: The ``ON_PRIMARY_CONTAINER`` role color.
        secondary: The ``SECONDARY`` role color.
        on_secondary: The ``ON_SECONDARY`` role color.
        secondary_container: The ``SECONDARY_CONTAINER`` role color.
        on_secondary_container: The ``ON_SECONDARY_CONTAINER`` role color.
        tertiary: The ``TERTIARY`` role color.
        on_tertiary: The ``ON_TERTIARY`` role color.
        tertiary_container: The ``TERTIARY_CONTAINER`` role color.
        on_tertiary_container: The ``ON_TERTIARY_CONTAINER`` role color.
        error: The ``ERROR`` role color.
        on_error: The ``ON_ERROR`` role color.
        error_container: The ``ERROR_CONTAINER`` role color.
        on_error_container: The ``ON_ERROR_CONTAINER`` role color.
        background: The ``BACKGROUND`` role color.
        on_background: The ``ON_BACKGROUND`` role color.
        surface: The ``SURFACE`` role color.
        on_surface: The ``ON_SURFACE`` role color.
        surface_variant: The ``SURFACE_VARIANT`` role color.
        on_surface_variant: The ``ON_SURFACE_VARIANT`` role color.
        outline: The ``OUTLINE`` role color.
        outline_variant: The ``OUTLINE_VARIANT`` role color.
        inverse_surface: The ``INVERSE_SURFACE`` role color.
        inverse_on_surface: The ``INVERSE_ON_SURFACE`` role color.
        inverse_primary: The ``INVERSE_PRIMARY`` role color.

    Methods:
        role: Read the color for a :class:`ColorRole`.
    """

    model_config = ConfigDict(frozen=True)

    primary: Color
    on_primary: Color
    primary_container: Color
    on_primary_container: Color
    secondary: Color
    on_secondary: Color
    secondary_container: Color
    on_secondary_container: Color
    tertiary: Color
    on_tertiary: Color
    tertiary_container: Color
    on_tertiary_container: Color
    error: Color
    on_error: Color
    error_container: Color
    on_error_container: Color
    background: Color
    on_background: Color
    surface: Color
    on_surface: Color
    surface_variant: Color
    on_surface_variant: Color
    outline: Color
    outline_variant: Color
    inverse_surface: Color
    inverse_on_surface: Color
    inverse_primary: Color

    def role(self, role: ColorRole) -> Color:
        """Read the color for a given Material 3 color role.

        Args:
            role: The semantic role to resolve.

        Returns:
            The concrete color for that role in this scheme.
        """
        color: Color = getattr(self, role.value)
        return color


class ColorSchemes(BaseModel):
    """The light and dark :class:`ColorScheme` pair of a theme.

    Attributes:
        light: The color scheme used when the theme renders light.
        dark: The color scheme used when the theme renders dark.

    Methods:
        for_mode: Pick the scheme for a resolved dark/light flag.
    """

    model_config = ConfigDict(frozen=True)

    light: ColorScheme
    dark: ColorScheme

    def for_mode(self, *, is_dark: bool) -> ColorScheme:
        """Pick the scheme matching a resolved dark/light flag.

        Args:
            is_dark: ``True`` to select the dark scheme, ``False`` for light.

        Returns:
            The matching color scheme.
        """
        return self.dark if is_dark else self.light


def _scheme_from_palettes(
    *,
    primary: TonalPalette,
    secondary: TonalPalette,
    tertiary: TonalPalette,
    neutral: TonalPalette,
    error: TonalPalette,
    is_dark: bool,
) -> ColorScheme:
    """Assemble one :class:`ColorScheme` from tonal palettes for a mode.

    The tone each role reads follows the Material 3 light/dark mapping (e.g.
    primary is tone 40 light / 80 dark, surface is tone 99 light / 10 dark).

    Args:
        primary: The primary tonal palette.
        secondary: The secondary tonal palette.
        tertiary: The tertiary tonal palette.
        neutral: The neutral tonal palette (surfaces, background, outline).
        error: The error tonal palette.
        is_dark: Whether to assemble the dark scheme.

    Returns:
        The assembled color scheme for the requested mode.
    """
    if is_dark:
        return ColorScheme(
            primary=primary.tone(80),
            on_primary=primary.tone(20),
            primary_container=primary.tone(30),
            on_primary_container=primary.tone(90),
            secondary=secondary.tone(80),
            on_secondary=secondary.tone(20),
            secondary_container=secondary.tone(30),
            on_secondary_container=secondary.tone(90),
            tertiary=tertiary.tone(80),
            on_tertiary=tertiary.tone(20),
            tertiary_container=tertiary.tone(30),
            on_tertiary_container=tertiary.tone(90),
            error=error.tone(80),
            on_error=error.tone(20),
            error_container=error.tone(30),
            on_error_container=error.tone(90),
            background=neutral.tone(10),
            on_background=neutral.tone(90),
            surface=neutral.tone(10),
            on_surface=neutral.tone(90),
            surface_variant=neutral.tone(30),
            on_surface_variant=neutral.tone(80),
            outline=neutral.tone(60),
            outline_variant=neutral.tone(30),
            inverse_surface=neutral.tone(90),
            inverse_on_surface=neutral.tone(20),
            inverse_primary=primary.tone(40),
        )
    return ColorScheme(
        primary=primary.tone(40),
        on_primary=primary.tone(100),
        primary_container=primary.tone(90),
        on_primary_container=primary.tone(10),
        secondary=secondary.tone(40),
        on_secondary=secondary.tone(100),
        secondary_container=secondary.tone(90),
        on_secondary_container=secondary.tone(10),
        tertiary=tertiary.tone(40),
        on_tertiary=tertiary.tone(100),
        tertiary_container=tertiary.tone(90),
        on_tertiary_container=tertiary.tone(10),
        error=error.tone(40),
        on_error=error.tone(100),
        error_container=error.tone(90),
        on_error_container=error.tone(10),
        background=neutral.tone(99),
        on_background=neutral.tone(10),
        surface=neutral.tone(99),
        on_surface=neutral.tone(10),
        surface_variant=neutral.tone(90),
        on_surface_variant=neutral.tone(30),
        outline=neutral.tone(50),
        outline_variant=neutral.tone(80),
        inverse_surface=neutral.tone(20),
        inverse_on_surface=neutral.tone(95),
        inverse_primary=primary.tone(80),
    )


#: The default Material 3 error key color (M3 baseline red).
_DEFAULT_ERROR_SEED: Color = Color(r=179, g=38, b=30, a=1.0)


def _rotate_hue(seed: Color, degrees: float, *, desaturate: float = 1.0) -> Color:
    """Rotate a seed's hue by a number of degrees (for derived key colors).

    Args:
        seed: The base color.
        degrees: Hue rotation in degrees (positive is toward magenta).
        desaturate: Multiplier applied to the seed's saturation (``<1.0``
            yields a more neutral key color, e.g. for the neutral palette).

    Returns:
        The rotated, optionally desaturated key color.
    """
    hue, lightness, saturation = colorsys.rgb_to_hls(
        seed.r / 255.0,
        seed.g / 255.0,
        seed.b / 255.0,
    )
    hue = (hue + degrees / 360.0) % 1.0
    r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation * desaturate)
    return Color(r=round(r * 255), g=round(g * 255), b=round(b * 255), a=1.0)


def color_schemes_from_seed(
    seed: Color,
    *,
    secondary_seed: Color | None = None,
    tertiary_seed: Color | None = None,
    error_seed: Color | None = None,
) -> ColorSchemes:
    """Generate the light + dark Material 3 schemes from a brand seed color.

    By default the secondary and tertiary key colors are derived by rotating the
    seed hue (M3 derives related palettes from one seed); a researcher can
    override any of them to hand-pick a brand accent. The neutral palette is the
    desaturated seed so surfaces carry a hint of the brand tint, as M3 does.

    Args:
        seed: The primary brand/key color.
        secondary_seed: Override key color for the secondary palette; defaults
            to the seed hue rotated ``-60°``.
        tertiary_seed: Override key color for the tertiary palette; defaults to
            the seed hue rotated ``+60°``.
        error_seed: Override key color for the error palette; defaults to the
            Material 3 baseline red.

    Returns:
        The light/dark scheme pair derived from the seed.
    """
    primary = tonal_palette_from_seed(seed)
    secondary = tonal_palette_from_seed(
        secondary_seed if secondary_seed is not None else _rotate_hue(seed, -60.0)
    )
    tertiary = tonal_palette_from_seed(
        tertiary_seed if tertiary_seed is not None else _rotate_hue(seed, 60.0)
    )
    neutral = tonal_palette_from_seed(_rotate_hue(seed, 0.0, desaturate=0.12))
    error = tonal_palette_from_seed(
        error_seed if error_seed is not None else _DEFAULT_ERROR_SEED
    )
    return ColorSchemes(
        light=_scheme_from_palettes(
            primary=primary,
            secondary=secondary,
            tertiary=tertiary,
            neutral=neutral,
            error=error,
            is_dark=False,
        ),
        dark=_scheme_from_palettes(
            primary=primary,
            secondary=secondary,
            tertiary=tertiary,
            neutral=neutral,
            error=error,
            is_dark=True,
        ),
    )


class SpacingScale(BaseModel):
    """The 4dp-grid spacing scale (named steps → logical pixels).

    Named ``t-shirt`` steps mapping to a 4dp grid, matching Chakra's spacing
    ergonomics over Material's raw dp. Components ask for ``space("md")`` rather
    than a literal ``16.0``. Frozen so it diffs by value.

    Attributes:
        none: ``0`` dp.
        xs: ``4`` dp (one grid unit).
        sm: ``8`` dp.
        md: ``16`` dp (the default content gutter).
        lg: ``24`` dp.
        xl: ``32`` dp.
        xxl: ``48`` dp.

    Methods:
        get: Resolve a named step to its pixel value.
    """

    model_config = ConfigDict(frozen=True)

    none: float = 0.0
    xs: float = 4.0
    sm: float = 8.0
    md: float = 16.0
    lg: float = 24.0
    xl: float = 32.0
    xxl: float = 48.0

    def get(self, name: str) -> float:
        """Resolve a named spacing step to its pixel value.

        Args:
            name: The step name (``"none"``, ``"xs"``, …, ``"xxl"``).

        Returns:
            The spacing in logical pixels.

        Raises:
            KeyError: If ``name`` is not a defined spacing step.
        """
        if name not in type(self).model_fields:
            raise KeyError(f"unknown spacing step: {name!r}")
        value: float = getattr(self, name)
        return value


class ShapeScale(BaseModel):
    """The Material 3 shape (corner-radius) scale in logical pixels.

    ``full`` uses the framework's pill sentinel (``999``) so the renderer clamps
    it to a fully-rounded shape. Frozen so it diffs by value.

    Attributes:
        none: ``0`` dp — square corners.
        xs: ``4`` dp.
        sm: ``8`` dp.
        md: ``12`` dp (the M3 default for cards/buttons).
        lg: ``16`` dp.
        xl: ``28`` dp (large containers, sheets).
        full: ``999`` dp — the pill/circle sentinel.

    Methods:
        get: Resolve a named radius step to its pixel value.
    """

    model_config = ConfigDict(frozen=True)

    none: float = 0.0
    xs: float = 4.0
    sm: float = 8.0
    md: float = 12.0
    lg: float = 16.0
    xl: float = 28.0
    full: float = 999.0

    def get(self, name: str) -> float:
        """Resolve a named radius step to its pixel value.

        Args:
            name: The step name (``"none"``, ``"xs"``, …, ``"full"``).

        Returns:
            The radius in logical pixels.

        Raises:
            KeyError: If ``name`` is not a defined radius step.
        """
        if name not in type(self).model_fields:
            raise KeyError(f"unknown radius step: {name!r}")
        value: float = getattr(self, name)
        return value


class TypographyToken(BaseModel):
    """One role of the Material 3 type scale (size + line-height + weight).

    Attributes:
        font_size: The font size in logical pixels.
        line_height: The line height in logical pixels.
        font_weight: The font weight.
        letter_spacing: The tracking in logical pixels (M3 uses small values).
    """

    model_config = ConfigDict(frozen=True)

    font_size: float
    line_height: float
    font_weight: FontWeight = FontWeight.NORMAL
    letter_spacing: float = 0.0


class TypographyScale(BaseModel):
    """The Material 3 type scale (display/headline/title/body/label × sizes).

    Each role is a :class:`TypographyToken` carrying size, line-height and
    weight, matching the M3 baseline values. Frozen so it diffs by value.

    Attributes:
        display_large: Largest display role (57/64).
        display_medium: Medium display role (45/52).
        display_small: Small display role (36/44).
        headline_large: Large headline (32/40).
        headline_medium: Medium headline (28/36).
        headline_small: Small headline (24/32).
        title_large: Large title (22/28).
        title_medium: Medium title (16/24, medium weight).
        title_small: Small title (14/20, medium weight).
        body_large: Large body (16/24).
        body_medium: Medium body (14/20).
        body_small: Small body (12/16).
        label_large: Large label (14/20, medium weight).
        label_medium: Medium label (12/16, medium weight).
        label_small: Small label (11/16, medium weight).

    Methods:
        get: Resolve a named type role to its :class:`TypographyToken`.
    """

    model_config = ConfigDict(frozen=True)

    display_large: TypographyToken = TypographyToken(font_size=57.0, line_height=64.0)
    display_medium: TypographyToken = TypographyToken(font_size=45.0, line_height=52.0)
    display_small: TypographyToken = TypographyToken(font_size=36.0, line_height=44.0)
    headline_large: TypographyToken = TypographyToken(font_size=32.0, line_height=40.0)
    headline_medium: TypographyToken = TypographyToken(font_size=28.0, line_height=36.0)
    headline_small: TypographyToken = TypographyToken(font_size=24.0, line_height=32.0)
    title_large: TypographyToken = TypographyToken(font_size=22.0, line_height=28.0)
    title_medium: TypographyToken = TypographyToken(
        font_size=16.0,
        line_height=24.0,
        font_weight=FontWeight.MEDIUM,
        letter_spacing=0.15,
    )
    title_small: TypographyToken = TypographyToken(
        font_size=14.0,
        line_height=20.0,
        font_weight=FontWeight.MEDIUM,
        letter_spacing=0.1,
    )
    body_large: TypographyToken = TypographyToken(
        font_size=16.0, line_height=24.0, letter_spacing=0.5
    )
    body_medium: TypographyToken = TypographyToken(
        font_size=14.0, line_height=20.0, letter_spacing=0.25
    )
    body_small: TypographyToken = TypographyToken(
        font_size=12.0, line_height=16.0, letter_spacing=0.4
    )
    label_large: TypographyToken = TypographyToken(
        font_size=14.0,
        line_height=20.0,
        font_weight=FontWeight.MEDIUM,
        letter_spacing=0.1,
    )
    label_medium: TypographyToken = TypographyToken(
        font_size=12.0,
        line_height=16.0,
        font_weight=FontWeight.MEDIUM,
        letter_spacing=0.5,
    )
    label_small: TypographyToken = TypographyToken(
        font_size=11.0,
        line_height=16.0,
        font_weight=FontWeight.MEDIUM,
        letter_spacing=0.5,
    )

    def get(self, name: str) -> TypographyToken:
        """Resolve a named type role to its token.

        Args:
            name: The role name (``"body_medium"``, ``"title_large"``, …).

        Returns:
            The typography token for that role.

        Raises:
            KeyError: If ``name`` is not a defined type role.
        """
        if name not in type(self).model_fields:
            raise KeyError(f"unknown typography role: {name!r}")
        token: TypographyToken = getattr(self, name)
        return token


class ElevationScale(BaseModel):
    """The Material 3 elevation scale (levels 0-5 → dp).

    Maps the six M3 elevation levels to their dp values; renderers turn the dp
    into a tonal-surface tint (Compose) or a drop shadow (Qt). Frozen so it
    diffs by value.

    Attributes:
        level0: ``0`` dp — flush with the background.
        level1: ``1`` dp.
        level2: ``3`` dp.
        level3: ``6`` dp.
        level4: ``8`` dp.
        level5: ``12`` dp.

    Methods:
        get: Resolve an elevation level (0-5) to its dp value.
    """

    model_config = ConfigDict(frozen=True)

    level0: float = 0.0
    level1: float = 1.0
    level2: float = 3.0
    level3: float = 6.0
    level4: float = 8.0
    level5: float = 12.0

    def get(self, level: int) -> float:
        """Resolve an elevation level to its dp value.

        Args:
            level: The elevation level, 0-5.

        Returns:
            The elevation in dp.

        Raises:
            KeyError: If ``level`` is outside 0-5.
        """
        name = f"level{level}"
        if name not in type(self).model_fields:
            raise KeyError(f"unknown elevation level: {level!r}")
        value: float = getattr(self, name)
        return value


class MotionScale(BaseModel):
    """The Material 3 motion scale (standard durations + easing curves).

    Durations are in milliseconds (M3's ``short``/``medium``/``long`` buckets);
    easing reuses the framework's :class:`~tempest_core.style.Curve`. Frozen so
    it diffs by value.

    Attributes:
        duration_short: A short transition (150 ms) — small UI changes.
        duration_medium: A medium transition (300 ms) — the default.
        duration_long: A long transition (500 ms) — large/expressive motion.
        easing_standard: The default easing for most transitions.
        easing_emphasized: A more expressive easing for prominent motion.
    """

    model_config = ConfigDict(frozen=True)

    duration_short: int = 150
    duration_medium: int = 300
    duration_long: int = 500
    easing_standard: Curve = Curve.EASE_IN_OUT
    easing_emphasized: Curve = Curve.EASE_OUT


class Breakpoints(BaseModel):
    """Responsive width breakpoints in logical pixels (Chakra-style).

    Used by H1's responsive token resolution against the E9
    :class:`~tempest_core.theme.MediaQueryData` (e.g. ``size={"base": "sm",
    "md": "lg"}``). Frozen so it diffs by value.

    Attributes:
        sm: The small breakpoint (compact phones).
        md: The medium breakpoint (large phones / small tablets).
        lg: The large breakpoint (tablets).
        xl: The extra-large breakpoint (desktop).
    """

    model_config = ConfigDict(frozen=True)

    sm: float = 360.0
    md: float = 600.0
    lg: float = 905.0
    xl: float = 1240.0


class TokenSet(BaseModel):
    """The full set of design tokens a theme resolves against.

    Bundles the color schemes with every systematic scale (spacing, shape,
    typography, elevation, motion, breakpoints). Build one from a seed via
    :meth:`from_seed`, or hand-author any scale. Frozen so the runtime can hold
    it as an immutable snapshot and swap it wholesale.

    Attributes:
        schemes: The light/dark color schemes.
        spacing: The 4dp spacing scale.
        shape: The corner-radius scale.
        typography: The type scale.
        elevation: The elevation scale.
        motion: The motion (duration/easing) scale.
        breakpoints: The responsive width breakpoints.

    Methods:
        from_seed: Build a token set from a brand seed color (classmethod).
        scheme: Resolve the color scheme for a dark/light flag.
    """

    model_config = ConfigDict(frozen=True)

    schemes: ColorSchemes
    spacing: SpacingScale = SpacingScale()
    shape: ShapeScale = ShapeScale()
    typography: TypographyScale = TypographyScale()
    elevation: ElevationScale = ElevationScale()
    motion: MotionScale = MotionScale()
    breakpoints: Breakpoints = Breakpoints()

    @classmethod
    def from_seed(
        cls,
        seed: Color,
        *,
        secondary_seed: Color | None = None,
        tertiary_seed: Color | None = None,
        error_seed: Color | None = None,
    ) -> TokenSet:
        """Build a token set from a brand seed color with M3 default scales.

        Args:
            seed: The primary brand/key color.
            secondary_seed: Override key color for the secondary palette.
            tertiary_seed: Override key color for the tertiary palette.
            error_seed: Override key color for the error palette.

        Returns:
            A token set with schemes derived from the seed and default M3
            spacing/shape/typography/elevation/motion scales.
        """
        return cls(
            schemes=color_schemes_from_seed(
                seed,
                secondary_seed=secondary_seed,
                tertiary_seed=tertiary_seed,
                error_seed=error_seed,
            )
        )

    def scheme(self, *, is_dark: bool) -> ColorScheme:
        """Resolve the color scheme for a dark/light flag.

        Args:
            is_dark: ``True`` for the dark scheme, ``False`` for light.

        Returns:
            The matching color scheme.
        """
        return self.schemes.for_mode(is_dark=is_dark)


class TokenRef(BaseModel):
    """A reference to a design token, resolved by the theme at build time.

    This is the **seam** that lets a :class:`~tempest_core.style.Style` field
    carry a *token reference* instead of a raw value: a component (or app) writes
    ``Style(background=TokenRef.color("primary"))`` and the theme resolves it to
    a concrete value before the diff. Raw values keep working unchanged — a
    ``TokenRef`` is purely an additional, opt-in source.

    The reference names a *category* and a *token name*; the theme's
    :meth:`~tempest_core.theme.Theme.resolve_ref` reads the right scale. Frozen
    so it diffs by value and can sit inside a frozen ``Style``.

    Attributes:
        category: Which token scale to read — ``"color"``, ``"space"``,
            ``"radius"``, ``"type"``, ``"elevation"`` or ``"motion"``.
        name: The token name within the category (e.g. ``"primary"``,
            ``"md"``, ``"body_medium"``, ``"level2"``, ``"duration_short"``).

    Methods:
        color: Build a color-role reference (classmethod).
        space: Build a spacing-step reference (classmethod).
        radius: Build a radius-step reference (classmethod).
        type_: Build a typography-role reference (classmethod).
        elevation: Build an elevation-level reference (classmethod).
        motion: Build a motion-token reference (classmethod).
    """

    model_config = ConfigDict(frozen=True)

    category: str
    name: str

    @classmethod
    def color(cls, role: ColorRole | str) -> TokenRef:
        """Build a reference to a color role.

        Args:
            role: The color role (a :class:`ColorRole` or its string value).

        Returns:
            The token reference.
        """
        name = role.value if isinstance(role, ColorRole) else role
        return cls(category="color", name=str(name))

    @classmethod
    def space(cls, name: str) -> TokenRef:
        """Build a reference to a spacing step.

        Args:
            name: The spacing step name (``"md"``, …).

        Returns:
            The token reference.
        """
        return cls(category="space", name=name)

    @classmethod
    def radius(cls, name: str) -> TokenRef:
        """Build a reference to a radius step.

        Args:
            name: The radius step name (``"lg"``, …).

        Returns:
            The token reference.
        """
        return cls(category="radius", name=name)

    @classmethod
    def type_(cls, name: str) -> TokenRef:
        """Build a reference to a typography role.

        Args:
            name: The type role name (``"body_medium"``, …).

        Returns:
            The token reference.
        """
        return cls(category="type", name=name)

    @classmethod
    def elevation(cls, level: int) -> TokenRef:
        """Build a reference to an elevation level.

        Args:
            level: The elevation level, 0-5.

        Returns:
            The token reference.
        """
        return cls(category="elevation", name=f"level{level}")

    @classmethod
    def motion(cls, name: str) -> TokenRef:
        """Build a reference to a motion token.

        Args:
            name: The motion token name (``"duration_short"``,
                ``"easing_standard"``, …).

        Returns:
            The token reference.
        """
        return cls(category="motion", name=name)


#: The Material 3 baseline seed color (the M3 reference purple, ``#6750A4``).
DEFAULT_SEED: Color = Color(r=103, g=80, b=164, a=1.0)


def default_tokens() -> TokenSet:
    """Build the default Material 3 token set (the baseline M3 theme).

    Seeded with the Material 3 reference purple so an app that sets no brand
    color still gets a complete, M3-faithful token set.

    Returns:
        The default token set.
    """
    return TokenSet.from_seed(DEFAULT_SEED)
