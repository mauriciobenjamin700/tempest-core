"""Tests for the Chakra-style variant API (Trilho H, phase H1).

Pins the pure ``variant × size × state × color_scheme → Style`` resolution (the
conformance anchors the two renderers consume), the M3 state-layer math,
``Color.blend``/``overlay``, the enforced ≥48dp touch target, WCAG-AA contrast on
the solid/outline foreground-vs-background pairing, responsive ``size``
resolution per breakpoint, RTL safety (symmetric padding, no fixed left/right),
``color_scheme`` validation, and backward compatibility of ``Button``.
"""

from __future__ import annotations

import pytest

from tempest_core import (
    Button,
    ComponentState,
    MediaQueryData,
    Size,
    Theme,
    Variant,
    resolve_size,
    resolve_variant,
    resolve_variant_states,
)
from tempest_core.style import Border, Color, Edge, Style, TextDecoration
from tempest_core.tokens import contrast_ratio
from tempest_core.variants import (
    DISABLED_CONTENT_OPACITY,
    HOVER_OPACITY,
    MIN_TOUCH_TARGET,
    PRESSED_OPACITY,
    VALID_COLOR_SCHEMES,
    merge_styles,
)

THEME = Theme()


# --------------------------------------------------------------------------- #
# Color.blend / Color.overlay math
# --------------------------------------------------------------------------- #


def test_blend_endpoints_and_midpoint() -> None:
    """``blend`` returns each endpoint at t=0/1 and the midpoint at t=0.5."""
    black = Color.from_hex("#000000")
    white = Color.from_hex("#ffffff")
    assert black.blend(white, 0.0) == black
    assert black.blend(white, 1.0) == white
    assert black.blend(white, 0.5).to_hex() == "#808080"


def test_blend_clamps_factor() -> None:
    """``blend`` clamps the factor into ``[0, 1]``."""
    black = Color.from_hex("#000000")
    white = Color.from_hex("#ffffff")
    assert black.blend(white, -1.0) == black
    assert black.blend(white, 2.0) == white


def test_blend_interpolates_alpha() -> None:
    """``blend`` interpolates the alpha channel too."""
    a = Color(r=0, g=0, b=0, a=0.0)
    b = Color(r=0, g=0, b=0, a=1.0)
    assert a.blend(b, 0.5).a == pytest.approx(0.5)


def test_overlay_is_opaque_blend_at_opacity() -> None:
    """``overlay`` composites the layer over an opaque backdrop at the opacity."""
    layer = Color.from_hex("#ffffff")
    backdrop = Color.from_hex("#000000")
    result = layer.overlay(backdrop, 0.5)
    assert result == backdrop.blend(layer, 0.5)
    assert result.a == 1.0


def test_with_alpha_clamps() -> None:
    """``with_alpha`` replaces and clamps the alpha channel."""
    c = Color.from_hex("#112233")
    assert c.with_alpha(0.5).a == pytest.approx(0.5)
    assert c.with_alpha(2.0).a == 1.0
    assert c.with_alpha(-1.0).a == 0.0
    assert c.with_alpha(0.5).to_hex()[:7] == "#112233"


# --------------------------------------------------------------------------- #
# variant → treatment (the resolution table — conformance anchors)
# --------------------------------------------------------------------------- #


def _scheme_color(role: str) -> Color:
    return THEME.color(role)


def test_solid_fills_role_with_on_role_content() -> None:
    """``solid`` paints the role color with its legible ``on_*`` content."""
    style = resolve_variant(
        variant=Variant.SOLID, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.background == _scheme_color("primary")
    assert style.color == _scheme_color("on_primary")
    assert style.border is None
    assert style.text_decoration is None


def test_outline_is_transparent_with_role_border_and_content() -> None:
    """``outline`` is a surface bg with the role as both content and border."""
    style = resolve_variant(
        variant=Variant.OUTLINE, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.background == _scheme_color("surface")
    assert style.color == _scheme_color("primary")
    assert isinstance(style.border, Border)
    assert style.border.color == _scheme_color("primary")
    assert style.border.width == 1.0


def test_ghost_is_transparent_role_content_no_border() -> None:
    """``ghost`` is a surface bg with role content and no border."""
    style = resolve_variant(
        variant=Variant.GHOST, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.background == _scheme_color("surface")
    assert style.color == _scheme_color("primary")
    assert style.border is None
    assert style.text_decoration is None


def test_link_is_ghost_plus_underline() -> None:
    """``link`` adds an underline to the ghost treatment."""
    style = resolve_variant(
        variant=Variant.LINK, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.color == _scheme_color("primary")
    assert style.text_decoration is TextDecoration.UNDERLINE


def test_color_scheme_selects_role_family() -> None:
    """Each ``color_scheme`` selects its own M3 role family for a solid fill."""
    for scheme in ("primary", "secondary", "tertiary", "error"):
        style = resolve_variant(
            variant=Variant.SOLID, size=Size.MD, color_scheme=scheme, theme=THEME
        )
        assert style.background == THEME.color(scheme)
        assert style.color == THEME.color(f"on_{scheme}")


def test_neutral_scheme_uses_surface_roles() -> None:
    """``neutral`` paints with the surface roles (no dedicated role family)."""
    style = resolve_variant(
        variant=Variant.SOLID, size=Size.MD, color_scheme="neutral", theme=THEME
    )
    assert style.background == THEME.color("on_surface")
    assert style.color == THEME.color("surface")


# --------------------------------------------------------------------------- #
# size → density + touch target
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("size", list(Size))
def test_every_size_enforces_min_touch_target(size: Size) -> None:
    """No ``size`` produces a hit target below the M3 48dp minimum."""
    for variant in Variant:
        style = resolve_variant(
            variant=variant, size=size, color_scheme="primary", theme=THEME
        )
        assert style.min_height is not None
        assert style.min_height >= MIN_TOUCH_TARGET


def test_size_changes_visual_density_not_touch_target() -> None:
    """A smaller ``size`` shrinks padding/font but keeps the 48dp target."""
    xs = resolve_variant(
        variant=Variant.SOLID, size=Size.XS, color_scheme="primary", theme=THEME
    )
    lg = resolve_variant(
        variant=Variant.SOLID, size=Size.LG, color_scheme="primary", theme=THEME
    )
    assert xs.min_height == lg.min_height == MIN_TOUCH_TARGET
    assert xs.font_size is not None and lg.font_size is not None
    assert xs.font_size < lg.font_size
    assert isinstance(xs.padding, Edge) and isinstance(lg.padding, Edge)
    assert xs.padding.left < lg.padding.left


# --------------------------------------------------------------------------- #
# state → M3 state layer
# --------------------------------------------------------------------------- #


def test_default_state_has_no_state_layer() -> None:
    """The default state equals the plain base style (no overlay)."""
    base = resolve_variant(
        variant=Variant.SOLID, size=Size.MD, color_scheme="primary", theme=THEME
    )
    explicit = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.DEFAULT,
    )
    assert base == explicit


def test_hover_and_pressed_overlay_at_m3_opacities() -> None:
    """Hover/pressed overlay the content color over the fill at M3 opacities."""
    on_primary = _scheme_color("on_primary")
    primary = _scheme_color("primary")
    hover = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.HOVER,
    )
    pressed = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.PRESSED,
    )
    assert hover.background == on_primary.overlay(primary, HOVER_OPACITY)
    assert pressed.background == on_primary.overlay(primary, PRESSED_OPACITY)


def test_focus_adds_indicator_border() -> None:
    """The focus state adds a contrasting role-colored indicator border."""
    focus = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.FOCUS,
    )
    assert isinstance(focus.border, Border)
    assert focus.border.width == 2.0
    assert focus.border.color == _scheme_color("primary")


def test_disabled_drops_content_opacity() -> None:
    """Disabled mutes per element (content 38% + filled container 12%).

    M3 fades the content color and the container separately, not via a blanket
    box opacity — so ``Style.opacity`` stays unset (else the faded color and the
    box opacity would compound to ~0.14 instead of the spec's 0.38).
    """
    base = resolve_variant(
        variant=Variant.SOLID, size=Size.MD, color_scheme="primary", theme=THEME
    )
    disabled = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.DISABLED,
    )
    assert disabled.opacity is None  # no blanket box opacity (no double-fade)
    assert disabled.color is not None
    assert disabled.color.a == pytest.approx(DISABLED_CONTENT_OPACITY)
    # The filled container is muted (changed from the base solid fill).
    assert disabled.background != base.background


def test_resolve_variant_states_covers_every_state() -> None:
    """The state table resolves a style for every ``ComponentState``."""
    table = resolve_variant_states(
        variant=Variant.OUTLINE, size=Size.SM, color_scheme="secondary", theme=THEME
    )
    assert set(table) == set(ComponentState)
    for style in table.values():
        assert isinstance(style, Style)


# --------------------------------------------------------------------------- #
# transversais: contrast, RTL, responsive
# --------------------------------------------------------------------------- #


def test_solid_foreground_clears_wcag_aa() -> None:
    """A solid button's content clears WCAG-AA against its fill for every scheme."""
    for scheme in VALID_COLOR_SCHEMES:
        style = resolve_variant(
            variant=Variant.SOLID, size=Size.MD, color_scheme=scheme, theme=THEME
        )
        assert isinstance(style.background, Color) and style.color is not None
        assert contrast_ratio(style.background, style.color) >= 4.5


def test_outline_foreground_clears_wcag_aa() -> None:
    """An outline button's content clears WCAG-AA against its surface fill."""
    for scheme in ("primary", "secondary", "tertiary", "error"):
        style = resolve_variant(
            variant=Variant.OUTLINE, size=Size.MD, color_scheme=scheme, theme=THEME
        )
        assert isinstance(style.background, Color) and style.color is not None
        assert contrast_ratio(style.background, style.color) >= 4.5


def test_padding_is_symmetric_no_fixed_left_right() -> None:
    """Padding is left/right symmetric, with no fixed positional insets (RTL-safe)."""
    style = resolve_variant(
        variant=Variant.SOLID, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert isinstance(style.padding, Edge)
    assert style.padding.left == style.padding.right
    assert style.left is None and style.right is None


def test_responsive_size_resolves_per_breakpoint() -> None:
    """A responsive ``size`` map resolves mobile-first against the breakpoints."""
    size = {"base": Size.SM, "md": Size.LG}
    narrow = resolve_size(size, THEME, media=MediaQueryData(width=300.0))
    wide = resolve_size(size, THEME, media=MediaQueryData(width=700.0))
    assert narrow is Size.SM
    assert wide is Size.LG


def test_responsive_size_no_media_uses_base() -> None:
    """Without a viewport width the responsive map resolves to ``base``."""
    size = {"base": Size.XS, "lg": Size.LG}
    assert resolve_size(size, THEME, media=None) is Size.XS


def test_responsive_size_below_all_breakpoints_uses_smallest() -> None:
    """A width below every provided breakpoint falls back to the smallest entry."""
    size = {"md": Size.MD, "lg": Size.LG}
    assert resolve_size(size, THEME, media=MediaQueryData(width=0.0)) is Size.MD


def test_bare_size_resolves_to_itself() -> None:
    """A bare ``Size`` resolves to itself regardless of the viewport."""
    assert resolve_size(Size.LG, THEME, media=MediaQueryData(width=10.0)) is Size.LG


def test_empty_responsive_map_raises() -> None:
    """An empty responsive ``size`` map is a programming error."""
    with pytest.raises(ValueError, match="must not be empty"):
        resolve_size({}, THEME)


def test_unknown_breakpoint_in_map_raises() -> None:
    """A responsive map naming an unknown breakpoint raises."""
    with pytest.raises(ValueError, match="unknown breakpoint"):
        resolve_size({"base": Size.SM, "huge": Size.LG}, THEME)


# --------------------------------------------------------------------------- #
# color_scheme validation
# --------------------------------------------------------------------------- #


def test_unknown_color_scheme_raises() -> None:
    """An unknown ``color_scheme`` name raises ``ValueError``."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        resolve_variant(
            variant=Variant.SOLID, size=Size.MD, color_scheme="bogus", theme=THEME
        )


# --------------------------------------------------------------------------- #
# merge_styles seam
# --------------------------------------------------------------------------- #


def test_merge_styles_keeps_typed_value_objects() -> None:
    """``merge_styles`` re-validates so nested ``Color`` stays a ``Color``."""
    base = Style(background=Color.from_hex("#000000"), min_height=48.0)
    merged = merge_styles(base, Style(color=Color.from_hex("#ffffff")))
    assert isinstance(merged.color, Color)
    assert isinstance(merged.background, Color)
    assert merged.min_height == 48.0


# --------------------------------------------------------------------------- #
# Button integration + backward compatibility
# --------------------------------------------------------------------------- #


def test_button_defaults_to_solid_primary_md() -> None:
    """``Button(label=...)`` resolves a solid/primary/md style by default."""
    button = Button(label="Save")
    assert button.variant is Variant.SOLID
    assert button.size is Size.MD
    assert button.color_scheme == "primary"
    assert button.style is not None
    assert button.style.background == THEME.color("primary")
    assert button.style.color == THEME.color("on_primary")
    assert button.style.min_height == MIN_TOUCH_TARGET


def test_button_explicit_style_overrides_resolved() -> None:
    """An explicit ``style`` is merged on top of the resolved variant style."""
    override = Color.from_hex("#ff0000")
    button = Button(label="X", style=Style(background=override))
    assert button.style is not None
    # Override wins on background; resolved fields it didn't set survive.
    assert button.style.background == override
    assert button.style.min_height == MIN_TOUCH_TARGET
    assert button.style.color == THEME.color("on_primary")


def test_button_state_styles_layer_override_per_state() -> None:
    """``state_styles`` layers the override on each state, not on the default."""
    override = Style(color=Color.from_hex("#00ff00"))
    button = Button(label="X", style=override)
    states = button.state_styles()
    # The hover overlay (state-specific background) survives; the override color
    # is applied on top of it (not clobbered by the baked default).
    plain_hover = resolve_variant(
        variant=Variant.SOLID,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.HOVER,
    )
    assert states[ComponentState.HOVER].background == plain_hover.background
    assert states[ComponentState.HOVER].color == Color.from_hex("#00ff00")


def test_button_variant_props_select_treatment() -> None:
    """The button's variant/size/color_scheme drive its resolved style."""
    button = Button(
        label="Cancel", variant=Variant.OUTLINE, size=Size.LG, color_scheme="neutral"
    )
    assert button.style is not None
    assert isinstance(button.style.border, Border)
    assert button.style.color == THEME.color("on_surface")


def test_button_responsive_size() -> None:
    """A button accepts a responsive ``size`` map resolved against ``media``."""
    button = Button(
        label="X",
        size={"base": Size.SM, "md": Size.LG},
        media=MediaQueryData(width=700.0),
    )
    lg = resolve_variant(
        variant=Variant.SOLID, size=Size.LG, color_scheme="primary", theme=THEME
    )
    assert button.style is not None
    assert button.style.font_size == lg.font_size


def test_button_preserves_accessibility_surface() -> None:
    """The styled button keeps ``semantics``/``focusable``/``focus_order``."""
    from tempest_core.widgets import Semantics

    button = Button(
        label="Save",
        semantics=Semantics(label="Save form", role="button"),
        focusable=True,
        focus_order=2,
    )
    assert button.semantics is not None
    assert button.semantics.label == "Save form"
    assert button.focusable is True
    assert button.focus_order == 2


def test_button_bad_color_scheme_raises() -> None:
    """A button with an unknown ``color_scheme`` fails to construct."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        Button(label="X", color_scheme="bogus")


def test_button_event_contract_unchanged() -> None:
    """The button still declares its ``on_click`` tap event contract."""
    from tempest_core.widgets.events import TapEvent

    assert Button.event_schemas == {"on_click": TapEvent}


def test_button_build_excludes_theme_from_props() -> None:
    """The Button IR node carries the resolved style but NOT the heavy theme/media.

    ``theme``/``media`` are build-time resolution inputs; baking them into every
    node's props would bloat the tree and the serialized bridge payload. The
    resolved ``style`` already captures the theme's effect.
    """
    from tempest_core import Button
    from tempest_core.core.reconciler import build

    node = build(Button(label="Save", variant=Variant.SOLID, color_scheme="primary"))
    assert "theme" not in node.props
    assert "media" not in node.props
    # The resolved style + the small variant props are still present.
    assert node.props.get("style") is not None
    assert node.props["variant"] == Variant.SOLID
    assert node.props["label"] == "Save"
