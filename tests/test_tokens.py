"""Tests for the Material 3 design-token foundation (Trilho H, phase H0).

Pins the tonal-palette generation (a seed → deterministic role values), the
scale defaults, light/dark scheme resolution, theme token overrides, the
Style ⟷ token seam, WCAG-AA contrast of every ``on_*`` role, and backward
compatibility (a plain ``Style``/``Theme`` still works unchanged).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tempest_core import (
    ColorRole,
    Style,
    Theme,
    ThemeMode,
    TokenRef,
    TokenSet,
    default_tokens,
    tonal_palette_from_seed,
)
from tempest_core.style import Color
from tempest_core.tokens import (
    DEFAULT_SEED,
    Breakpoints,
    ElevationScale,
    MotionScale,
    ShapeScale,
    SpacingScale,
    TypographyScale,
    color_schemes_from_seed,
    contrast_ratio,
)

#: The Material 3 reference purple used as the default seed.
SEED = Color(r=103, g=80, b=164)


def test_tonal_palette_is_deterministic_from_seed() -> None:
    """A seed produces a deterministic, M3-faithful tonal palette."""
    palette = tonal_palette_from_seed(SEED)
    assert palette.tone(0).to_hex() == "#000000"
    assert palette.tone(100).to_hex() == "#ffffff"
    # Light primary reads tone 40; dark primary reads tone 80.
    assert palette.tone(40).to_hex() == "#584785"
    assert palette.tone(80).to_hex() == "#c7c1d7"
    # Regenerating from the same seed yields identical colors.
    assert tonal_palette_from_seed(SEED) == palette


def test_tonal_palette_tone_snaps_to_nearest_standard() -> None:
    """A non-standard tone snaps to the nearest standard tone."""
    palette = tonal_palette_from_seed(SEED)
    # 42 is closest to standard tone 40.
    assert palette.tone(42) == palette.tone(40)


def test_light_and_dark_schemes_differ_and_map_expected_tones() -> None:
    """The light/dark schemes read the M3 light/dark tone mapping."""
    schemes = color_schemes_from_seed(SEED)
    assert schemes.light.primary.to_hex() == "#584785"
    assert schemes.dark.primary.to_hex() == "#c7c1d7"
    # On-primary inverts: white on the light primary, dark tone on dark.
    assert schemes.light.on_primary.to_hex() == "#ffffff"
    assert schemes.light != schemes.dark


def test_scheme_for_mode_picks_correct_scheme() -> None:
    """``ColorSchemes.for_mode`` selects light vs dark by the resolved flag."""
    schemes = color_schemes_from_seed(SEED)
    assert schemes.for_mode(is_dark=False) == schemes.light
    assert schemes.for_mode(is_dark=True) == schemes.dark


def test_on_roles_meet_wcag_aa_contrast() -> None:
    """Every ``on_*`` role clears WCAG-AA (>= 4.5:1) against its base role."""
    pairs = [
        (ColorRole.PRIMARY, ColorRole.ON_PRIMARY),
        (ColorRole.SECONDARY, ColorRole.ON_SECONDARY),
        (ColorRole.TERTIARY, ColorRole.ON_TERTIARY),
        (ColorRole.ERROR, ColorRole.ON_ERROR),
        (ColorRole.SURFACE, ColorRole.ON_SURFACE),
        (ColorRole.BACKGROUND, ColorRole.ON_BACKGROUND),
    ]
    for is_dark in (False, True):
        scheme = color_schemes_from_seed(SEED).for_mode(is_dark=is_dark)
        for base, on in pairs:
            ratio = contrast_ratio(scheme.role(base), scheme.role(on))
            assert ratio >= 4.5, f"{base}/{on} dark={is_dark} ratio={ratio:.2f}"


def test_scale_defaults_match_material3() -> None:
    """The default scales carry the documented Material 3 baseline values."""
    spacing = SpacingScale()
    assert (spacing.xs, spacing.sm, spacing.md, spacing.lg) == (4.0, 8.0, 16.0, 24.0)
    assert spacing.get("md") == 16.0

    shape = ShapeScale()
    assert (shape.sm, shape.md, shape.lg, shape.full) == (8.0, 12.0, 16.0, 999.0)
    assert shape.get("lg") == 16.0

    elevation = ElevationScale()
    assert elevation.get(0) == 0.0
    assert elevation.get(2) == 3.0
    assert elevation.get(5) == 12.0

    typography = TypographyScale()
    body = typography.get("body_medium")
    assert body.font_size == 14.0
    assert body.line_height == 20.0
    assert typography.get("display_large").font_size == 57.0

    motion = MotionScale()
    assert motion.duration_short == 150
    assert motion.duration_medium == 300

    breakpoints = Breakpoints()
    assert breakpoints.md == 600.0


def test_scale_get_rejects_unknown_name() -> None:
    """Unknown scale steps/levels raise ``KeyError``, not return a default."""
    with pytest.raises(KeyError):
        SpacingScale().get("huge")
    with pytest.raises(KeyError):
        ShapeScale().get("round")
    with pytest.raises(KeyError):
        ElevationScale().get(9)
    with pytest.raises(KeyError):
        TypographyScale().get("caption")


def test_theme_from_seed_resolves_tokens() -> None:
    """A seeded theme resolves color roles, spacing, radius, type and elevation."""
    theme = Theme.from_seed(SEED)
    assert theme.color("primary").to_hex() == "#584785"
    assert theme.color(ColorRole.PRIMARY).to_hex() == "#584785"
    assert theme.space("md") == 16.0
    assert theme.radius("lg") == 16.0
    assert theme.typography("title_large").font_size == 22.0
    assert theme.elevation(3) == 6.0


def test_theme_mode_drives_scheme_resolution() -> None:
    """Forced LIGHT/DARK ignore the platform flag; SYSTEM defers to it."""
    light = Theme.from_seed(SEED, mode=ThemeMode.LIGHT)
    dark = Theme.from_seed(SEED, mode=ThemeMode.DARK)
    # Forced modes ignore platform_dark_mode.
    assert light.color("primary", platform_dark_mode=True).to_hex() == "#584785"
    assert dark.color("primary", platform_dark_mode=False).to_hex() == "#c7c1d7"
    # SYSTEM follows the platform flag.
    system = Theme.from_seed(SEED, mode=ThemeMode.SYSTEM)
    assert system.color("primary", platform_dark_mode=False).to_hex() == "#584785"
    assert system.color("primary", platform_dark_mode=True).to_hex() == "#c7c1d7"


def test_theme_token_override_takes_effect() -> None:
    """Overriding a single scale token on a theme changes resolution."""
    base = default_tokens()
    custom_tokens = base.model_copy(update={"spacing": SpacingScale(md=20.0)})
    theme = Theme(tokens=custom_tokens)
    assert theme.space("md") == 20.0
    # Untouched scales keep their defaults.
    assert theme.radius("lg") == 16.0


def test_custom_brand_seed_changes_palette() -> None:
    """A different brand seed yields a different (still valid) palette."""
    blue = Color(r=33, g=150, b=243)
    blue_theme = Theme.from_seed(blue)
    purple_theme = Theme.from_seed(SEED)
    assert blue_theme.color("primary") != purple_theme.color("primary")
    # The brand seed's on-primary still clears AA contrast.
    ratio = contrast_ratio(blue_theme.color("primary"), blue_theme.color("on_primary"))
    assert ratio >= 4.5


def test_style_token_ref_seam_resolves_to_concrete_style() -> None:
    """``Theme.resolve_style`` turns token refs into a concrete frozen Style."""
    theme = Theme.from_seed(SEED)
    style = theme.resolve_style(
        {
            "background": TokenRef.color("primary"),
            "color": TokenRef.color(ColorRole.ON_PRIMARY),
            "radius": TokenRef.radius("lg"),
        }
    )
    assert isinstance(style, Style)
    assert style.background == theme.color("primary")
    assert style.color == theme.color("on_primary")
    assert style.radius == 16.0


def test_style_token_ref_type_expands_to_font_fields() -> None:
    """A typography token ref expands into the font_* Style fields."""
    theme = Theme.from_seed(SEED)
    style = theme.resolve_style({"font_size": TokenRef.type_("title_large")})
    token = theme.typography("title_large")
    assert style.font_size == token.font_size
    assert style.line_height == token.line_height
    assert style.font_weight == token.font_weight


def test_resolve_style_layers_onto_base() -> None:
    """``resolve_style`` layers resolved fields onto an optional base style."""
    theme = Theme.from_seed(SEED)
    base = Style(gap=8.0)
    style = theme.resolve_style({"background": TokenRef.color("primary")}, base=base)
    assert style.gap == 8.0  # preserved from base
    assert style.background == theme.color("primary")  # added from token


def test_resolve_ref_motion_and_elevation() -> None:
    """A motion/elevation ref resolves to the curve/duration/dp value."""
    theme = Theme.from_seed(SEED)
    assert theme.resolve_ref(TokenRef.motion("duration_short")) == 150
    assert theme.resolve_ref(TokenRef.elevation(2)) == 3.0


def test_resolve_ref_rejects_unknown_category_and_name() -> None:
    """An unknown category raises ValueError; an unknown name raises KeyError."""
    theme = Theme.from_seed(SEED)
    with pytest.raises(ValueError):
        theme.resolve_ref(TokenRef(category="bogus", name="x"))
    with pytest.raises(KeyError):
        theme.resolve_ref(TokenRef.space("nope"))


def test_default_theme_is_backward_compatible() -> None:
    """A plain Theme()/Style() still works — tokens are additive."""
    # A bare Theme carries the default M3 token set (seeded from the M3 purple).
    theme = Theme()
    assert theme.tokens == TokenSet.from_seed(DEFAULT_SEED)
    assert theme.mode is ThemeMode.SYSTEM
    # Legacy flat color fields still default to None.
    assert theme.primary is None
    # A raw Style with concrete values is unaffected by the token machinery.
    raw = Style(gap=12.0, radius=8.0)
    assert raw.gap == 12.0
    assert raw.radius == 8.0


def test_token_models_are_frozen() -> None:
    """Token value objects are immutable (frozen), so they diff by value."""
    spacing = SpacingScale()
    with pytest.raises(ValidationError):
        spacing.md = 99.0  # type: ignore[misc]
