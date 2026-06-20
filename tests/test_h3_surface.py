"""Tests for the H3 styled surface & layout kit (Trilho H, phase H3).

Pins the pure :func:`~tempest_core.variants.resolve_surface_variant` resolver
across every ``variant × color_scheme × elevation`` combination, the new
:class:`~tempest_core.style.CardVariant` enum, the elevation→``Shadow`` mapping,
the tinted-container roles, the new ``Surface`` / ``StyledContainer`` / ``HStack``
/ ``VStack`` components and the ``Spacer`` leaf, the themed
``Card`` / ``Divider`` / ``ListTile`` / ``Accordion`` / ``Grid``, the token-step
``str`` unions (D6), full backward-compatibility of the old call sites, and the
hard constraint that NO new ``Style`` field was added.
"""

from __future__ import annotations

import pytest

from tempest_core import (
    CardVariant,
    Spacer,
    Style,
    Theme,
    build,
    resolve_surface_variant,
)
from tempest_core.components import (
    Accordion,
    Card,
    Divider,
    Grid,
    HStack,
    ListTile,
    StyledContainer,
    Surface,
    VStack,
)
from tempest_core.core.introspection import WIDGET_TYPES, widget_catalog
from tempest_core.style import Border, Color, Edge, Shadow
from tempest_core.tokens import ColorRole, contrast_ratio
from tempest_core.variants import (
    ELEVATION_SHADOW_COLOR,
    VALID_COLOR_SCHEMES,
    merge_styles,
)
from tempest_core.widgets import Text

THEME = Theme()
SCHEMES = sorted(VALID_COLOR_SCHEMES)
VARIANTS = list(CardVariant)
LEVELS = [0, 1, 2, 3, 4, 5]


# --------------------------------------------------------------------------- #
# CardVariant enum + exports
# --------------------------------------------------------------------------- #


def test_card_variant_members() -> None:
    """``CardVariant`` exposes the three M3 surface treatments."""
    assert {v.value for v in CardVariant} == {"elevated", "filled", "outlined"}


def test_new_public_surface_importable() -> None:
    """The new H3 surface is importable from the package root."""
    assert CardVariant.ELEVATED == "elevated"
    assert callable(resolve_surface_variant)
    assert Surface.__name__ == "Surface"
    assert StyledContainer.__name__ == "StyledContainer"
    assert HStack.__name__ == "HStack"
    assert VStack.__name__ == "VStack"
    assert Spacer.__name__ == "Spacer"


# --------------------------------------------------------------------------- #
# resolve_surface_variant — per-variant treatment
# --------------------------------------------------------------------------- #


def test_elevated_has_shadow_no_border() -> None:
    """An elevated surface fills with SURFACE, casts a shadow and has no border."""
    style = resolve_surface_variant(variant=CardVariant.ELEVATED, theme=THEME)
    assert style.background == THEME.color(ColorRole.SURFACE)
    assert style.color == THEME.color(ColorRole.ON_SURFACE)
    assert isinstance(style.shadow, Shadow)
    assert style.shadow.blur > 0.0
    assert style.border is None


def test_filled_no_shadow_no_border() -> None:
    """A filled surface uses SURFACE_VARIANT, no shadow and no border."""
    style = resolve_surface_variant(variant=CardVariant.FILLED, theme=THEME)
    assert style.background == THEME.color(ColorRole.SURFACE_VARIANT)
    assert style.color == THEME.color(ColorRole.ON_SURFACE)
    assert style.shadow is None
    assert style.border is None


def test_outlined_border_no_shadow() -> None:
    """An outlined surface uses SURFACE, an OUTLINE border and no shadow."""
    style = resolve_surface_variant(variant=CardVariant.OUTLINED, theme=THEME)
    assert style.background == THEME.color(ColorRole.SURFACE)
    assert isinstance(style.border, Border)
    assert style.border.width == 1.0
    assert style.border.color == THEME.color(ColorRole.OUTLINE)
    assert style.shadow is None


@pytest.mark.parametrize("variant", VARIANTS)
def test_padding_and_radius_from_tokens(variant: CardVariant) -> None:
    """Every variant takes its padding/radius from the named token steps."""
    style = resolve_surface_variant(
        variant=variant, theme=THEME, padding_step="lg", radius_step="xl"
    )
    assert style.padding == Edge.all(THEME.space("lg"))
    assert style.radius == THEME.radius("xl")


# --------------------------------------------------------------------------- #
# Tinted container surfaces (D2)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("scheme", ["primary", "secondary", "tertiary", "error"])
@pytest.mark.parametrize("variant", VARIANTS)
def test_tinted_uses_container_roles(scheme: str, variant: CardVariant) -> None:
    """A non-neutral scheme paints with the tonal ``*_container`` roles."""
    style = resolve_surface_variant(variant=variant, color_scheme=scheme, theme=THEME)
    container_role = ColorRole(f"{scheme}_container")
    on_container_role = ColorRole(f"on_{scheme}_container")
    assert style.background == THEME.color(container_role)
    assert style.color == THEME.color(on_container_role)


def test_neutral_uses_surface_roles() -> None:
    """The neutral scheme uses the plain surface roles, not a container."""
    style = resolve_surface_variant(
        variant=CardVariant.ELEVATED, color_scheme="neutral", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.SURFACE)


@pytest.mark.parametrize("scheme", ["primary", "secondary", "tertiary", "error"])
def test_tinted_content_contrast_aa(scheme: str) -> None:
    """The tinted content keeps WCAG-AA contrast against the container fill."""
    style = resolve_surface_variant(
        variant=CardVariant.FILLED, color_scheme=scheme, theme=THEME
    )
    assert isinstance(style.background, Color)
    assert style.color is not None
    assert contrast_ratio(style.color, style.background) >= 4.5


# --------------------------------------------------------------------------- #
# Elevation → Shadow (D1)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("level", LEVELS)
def test_elevation_level_maps_to_shadow(level: int) -> None:
    """Each elevation level maps to a Shadow (or none for level 0)."""
    style = resolve_surface_variant(
        variant=CardVariant.ELEVATED, theme=THEME, elevation=level
    )
    if level == 0:
        assert style.shadow is None
    else:
        assert isinstance(style.shadow, Shadow)
        assert style.shadow.color == ELEVATION_SHADOW_COLOR
        assert style.shadow.blur > 0.0
        assert style.shadow.offset_y > 0.0


def test_elevation_grows_with_level() -> None:
    """A higher elevation level produces a larger blur + offset."""
    blurs: list[float] = []
    for level in [1, 2, 3, 4, 5]:
        style = resolve_surface_variant(
            variant=CardVariant.ELEVATED, theme=THEME, elevation=level
        )
        assert isinstance(style.shadow, Shadow)
        blurs.append(style.shadow.blur)
    assert blurs == sorted(blurs)
    assert len(set(blurs)) == len(blurs)


def test_elevation_overrides_variant_default() -> None:
    """An explicit elevation overrides the per-variant default level."""
    # FILLED defaults to level 0 (no shadow) but an explicit level adds one.
    style = resolve_surface_variant(
        variant=CardVariant.FILLED, theme=THEME, elevation=3
    )
    assert isinstance(style.shadow, Shadow)
    # ELEVATED defaults to level 1; forcing 0 removes the shadow.
    flat = resolve_surface_variant(
        variant=CardVariant.ELEVATED, theme=THEME, elevation=0
    )
    assert flat.shadow is None


def test_invalid_elevation_raises() -> None:
    """An out-of-range elevation level is rejected."""
    with pytest.raises(ValueError, match="elevation level"):
        resolve_surface_variant(variant=CardVariant.ELEVATED, theme=THEME, elevation=9)


def test_unknown_color_scheme_raises() -> None:
    """An unknown color_scheme is rejected with the expected message."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        resolve_surface_variant(
            variant=CardVariant.ELEVATED, color_scheme="brand", theme=THEME
        )


# --------------------------------------------------------------------------- #
# No new Style field (the hard constraint)
# --------------------------------------------------------------------------- #


def test_no_style_field_added() -> None:
    """H3 must not add any new ``Style`` field (sentinel for conformance).

    The H0/H1/H2 baseline: this count is pinned in the tempestroid conformance
    suite too. If H3 added a field, both break.
    """
    assert len(Style.model_fields) == 41


def test_surface_uses_only_existing_style_fields() -> None:
    """Every resolved surface field is an existing ``Style`` field."""
    for variant in VARIANTS:
        for scheme in SCHEMES:
            style = resolve_surface_variant(
                variant=variant, color_scheme=scheme, theme=THEME
            )
            # Re-dumping and re-validating must round-trip with no extra keys.
            assert Style.model_validate(style.model_dump()) == style


# --------------------------------------------------------------------------- #
# Surface / StyledContainer components
# --------------------------------------------------------------------------- #


def test_surface_lowers_to_container_with_resolved_style() -> None:
    """``Surface`` lowers to a Container carrying the resolved variant style."""
    node = build(Surface(variant=CardVariant.OUTLINED, child=Text(content="x")))
    assert node.type == "Container"
    style = node.props["style"]
    assert isinstance(style, Style)
    assert isinstance(style.border, Border)


def test_surface_explicit_style_wins() -> None:
    """An explicit ``style`` on a Surface overrides the resolved fields."""
    red = Color.from_hex("#ff0000")
    node = build(Surface(variant=CardVariant.ELEVATED, style=Style(background=red)))
    assert node.props["style"].background == red


def test_surface_has_no_inner_padding() -> None:
    """A bare ``Surface`` owns no inner padding (cards add their own)."""
    node = build(Surface(variant=CardVariant.FILLED))
    assert node.props["style"].padding == Edge.all(0.0)


def test_styled_container_token_step_padding() -> None:
    """``StyledContainer`` resolves a token-step padding against the theme."""
    node = build(StyledContainer(padding="lg", child=Text(content="x")))
    assert node.type == "Container"
    assert node.props["style"].padding == Edge.all(THEME.space("lg"))


def test_styled_container_float_padding_backcompat() -> None:
    """``StyledContainer`` still accepts a raw float padding."""
    node = build(StyledContainer(padding=20.0))
    assert node.props["style"].padding == Edge.all(20.0)


# --------------------------------------------------------------------------- #
# Spacer leaf
# --------------------------------------------------------------------------- #


def test_spacer_defaults_to_grow_one() -> None:
    """A bare ``Spacer`` bakes ``grow == 1.0`` into its style."""
    spacer = Spacer()
    assert spacer.style is not None
    assert spacer.style.grow == 1.0


def test_spacer_flex_weight() -> None:
    """A ``Spacer(flex=…)`` bakes that weight as ``grow``."""
    spacer = Spacer(flex=2.5)
    assert spacer.style is not None
    assert spacer.style.grow == 2.5


def test_spacer_explicit_grow_wins() -> None:
    """An explicit ``style.grow`` is not overwritten by the flex default."""
    spacer = Spacer(flex=2.0, style=Style(grow=4.0))
    assert spacer.style is not None
    assert spacer.style.grow == 4.0


def test_spacer_registered_in_introspection() -> None:
    """The ``Spacer`` leaf appears in the introspection catalog."""
    assert Spacer in WIDGET_TYPES
    assert "Spacer" in widget_catalog()


# --------------------------------------------------------------------------- #
# HStack / VStack
# --------------------------------------------------------------------------- #


def test_hstack_lowers_to_row_with_token_gap() -> None:
    """``HStack`` lowers to a Row whose gap is the resolved token step."""
    node = build(HStack(children=[Text(content="a")], gap="lg"))
    assert node.type == "Row"
    assert node.props["style"].gap == THEME.space("lg")


def test_vstack_lowers_to_column_with_token_gap() -> None:
    """``VStack`` lowers to a Column whose gap is the resolved token step."""
    node = build(VStack(children=[Text(content="a")], gap="md"))
    assert node.type == "Column"
    assert node.props["style"].gap == THEME.space("md")


def test_stack_float_gap_backcompat() -> None:
    """A stack still accepts a raw float gap."""
    node = build(HStack(children=[Text(content="a")], gap=7.0))
    assert node.props["style"].gap == 7.0


def test_stack_children_preserved() -> None:
    """A stack carries its children through to the lowered container."""
    node = build(VStack(children=[Text(content="a"), Text(content="b")], gap="sm"))
    assert [c.type for c in node.children] == ["Text", "Text"]


# --------------------------------------------------------------------------- #
# Card — themed surface + back-compat
# --------------------------------------------------------------------------- #


def test_card_back_compat_default_is_elevated_neutral() -> None:
    """A no-variant ``Card(children=…)`` is an elevated, neutral surface."""
    node = build(Card(children=[Text(content="hi")]))
    # Card → Surface → Container; the outer node is the surface container.
    assert node.type == "Container"
    style = node.props["style"]
    assert isinstance(style.shadow, Shadow)
    assert style.background == THEME.color(ColorRole.SURFACE)


def test_card_outlined_variant() -> None:
    """A ``Card(variant=OUTLINED)`` lowers to an outlined surface."""
    node = build(Card(variant=CardVariant.OUTLINED, children=[Text(content="hi")]))
    assert isinstance(node.props["style"].border, Border)
    assert node.props["style"].shadow is None


def test_card_wraps_padded_column() -> None:
    """A ``Card`` wraps a padded inner body containing the children column."""
    node = build(Card(children=[Text(content="a"), Text(content="b")]))
    # Surface container → padded body container → column of children.
    body = node.children[0]
    assert body.type == "Container"
    column = body.children[0]
    assert column.type == "Column"
    assert [c.type for c in column.children] == ["Text", "Text"]


def test_card_tinted() -> None:
    """A tinted ``Card`` uses the container roles."""
    node = build(Card(color_scheme="primary", children=[Text(content="x")]))
    assert node.props["style"].background == THEME.color(ColorRole.PRIMARY_CONTAINER)


# --------------------------------------------------------------------------- #
# Divider / ListTile — themed
# --------------------------------------------------------------------------- #


def test_divider_default_outline_variant_color() -> None:
    """A default ``Divider`` paints in the OUTLINE_VARIANT role color."""
    node = build(Divider())
    assert node.props["style"].background == THEME.color(ColorRole.OUTLINE_VARIANT)
    assert node.props["style"].height == 1.0


def test_divider_token_step_thickness() -> None:
    """A ``Divider`` thickness accepts a spacing-step name."""
    node = build(Divider(thickness="sm"))
    assert node.props["style"].height == THEME.space("sm")


def test_divider_color_scheme() -> None:
    """A ``Divider(color_scheme=…)`` paints in the role color."""
    node = build(Divider(color_scheme="primary"))
    assert node.props["style"].background == THEME.color(ColorRole.PRIMARY)


def test_listtile_themed_colors() -> None:
    """A ``ListTile`` title/subtitle use the on-surface theme roles."""
    node = build(ListTile(title="T", subtitle="S"))
    assert node.type == "Row"
    column = next(c for c in node.children if c.type == "Column")
    title = column.children[0]
    subtitle = column.children[1]
    assert title.props["style"].color == THEME.color(ColorRole.ON_SURFACE)
    assert subtitle.props["style"].color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


def test_listtile_preserves_semantics() -> None:
    """A ``ListTile`` propagates its Semantics onto the lowered row."""
    from tempest_core.widgets import Semantics

    node = build(ListTile(title="T", semantics=Semantics(label="row")))
    assert node.props["semantics"] == Semantics(label="row")


# --------------------------------------------------------------------------- #
# Accordion / Grid — themed
# --------------------------------------------------------------------------- #


def test_accordion_themed_header() -> None:
    """An ``Accordion`` header carries a resolved surface style."""
    node = build(
        Accordion(
            title="T",
            open=True,
            children=[Text(content="b")],
            on_toggle=lambda: None,
        )
    )
    assert node.type == "Column"
    header = node.children[0]
    assert header.type == "Button"
    # The header style is the resolved filled surface + bold weight.
    assert header.props["style"].background is not None


def test_accordion_closed_hides_body() -> None:
    """A closed ``Accordion`` lowers to just the header (no body)."""
    node = build(
        Accordion(
            title="T",
            open=False,
            children=[Text(content="b")],
            on_toggle=lambda: None,
        )
    )
    assert len(node.children) == 1


def test_grid_token_step_gap() -> None:
    """A ``Grid`` gap accepts a token-step name resolved against the theme."""
    node = build(Grid(children=[Text(content="a")], gap="md"))
    assert node.type == "Column"
    assert node.props["style"].gap == THEME.space("md")


def test_grid_float_gap_backcompat() -> None:
    """A ``Grid`` still accepts a raw float gap (old call site)."""
    node = build(Grid(children=[Text(content="a")], gap=8.0))
    assert node.props["style"].gap == 8.0


# --------------------------------------------------------------------------- #
# Resolver determinism + merge ordering
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("variant", VARIANTS)
@pytest.mark.parametrize("scheme", SCHEMES)
def test_resolver_is_deterministic(variant: CardVariant, scheme: str) -> None:
    """The resolver is pure: same inputs → equal styles."""
    a = resolve_surface_variant(variant=variant, color_scheme=scheme, theme=THEME)
    b = resolve_surface_variant(variant=variant, color_scheme=scheme, theme=THEME)
    assert a == b


def test_merge_override_layers_over_surface() -> None:
    """An override merged over a surface keeps the unset surface fields."""
    base = resolve_surface_variant(variant=CardVariant.OUTLINED, theme=THEME)
    override = Style(background=Color.from_hex("#123456"))
    merged = merge_styles(base, override)
    assert merged.background == Color.from_hex("#123456")
    # The border (unset on the override) is inherited from the surface.
    assert isinstance(merged.border, Border)


def test_dark_mode_resolves_dark_scheme() -> None:
    """The platform_dark_mode flag resolves against the dark scheme."""
    light = resolve_surface_variant(variant=CardVariant.ELEVATED, theme=THEME)
    dark = resolve_surface_variant(
        variant=CardVariant.ELEVATED, theme=THEME, platform_dark_mode=True
    )
    assert light.background != dark.background


def test_lowered_primitives_are_renderer_agnostic() -> None:
    """No H3 component leaks a Component into its lowered tree."""
    for widget in (
        Surface(child=Text(content="x")),
        StyledContainer(child=Text(content="x")),
        HStack(children=[Text(content="x")]),
        VStack(children=[Text(content="x")]),
        Card(children=[Text(content="x")]),
        Divider(),
        ListTile(title="t"),
    ):
        node = build(widget)
        assert node.type in {"Container", "Row", "Column"}
        # Lowered children are primitives (no Component subtype survives build).
        for child in node.children:
            assert child.type in {
                "Container",
                "Row",
                "Column",
                "Text",
                "Button",
            }
