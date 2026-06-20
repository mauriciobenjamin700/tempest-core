"""Tests for the H4 styled data-display & feedback kit (Trilho H, phase H4).

Pins the H4 status color families (success / warning / info) added to the token
model, the pure :func:`~tempest_core.variants.resolve_badge_variant` /
:func:`~tempest_core.variants.resolve_alert_variant` resolvers across every
``variant × size × color_scheme × state`` combination, the WCAG-AA gate on the
status pairings the resolvers actually emit (the A1 fix for the success-3.02
solid problem), the re-themed ``Badge`` / ``Banner`` / ``Avatar`` / ``EmptyState``
/ ``SegmentedControl`` / ``Rating`` / ``Chip`` lowering, the new ``Alert`` /
``Stat`` / ``ProgressStepper`` components and the ``Tag`` :class:`Chip` preset,
full backward-compatibility of the old call sites and old ``ColorScheme``
constructors, and the hard constraint that NO new ``Style`` field was added.
"""

from __future__ import annotations

import pytest

from tempest_core import (
    Alert,
    AlertVariant,
    Badge,
    BadgeVariant,
    Banner,
    Chip,
    ProgressStepper,
    Stat,
    Style,
    Tag,
    Theme,
    build,
    resolve_alert_variant,
    resolve_badge_variant,
    resolve_badge_variant_states,
)
from tempest_core.components import Avatar, EmptyState, Rating, SegmentedControl
from tempest_core.core import Node
from tempest_core.style import Border, Color, ComponentState, SideBorder, Size
from tempest_core.tokens import (
    ColorRole,
    ColorScheme,
    color_schemes_from_seed,
    contrast_ratio,
    default_tokens,
)

THEME = Theme()
SIZES = list(Size)
STATES = list(ComponentState)
BADGE_VARIANTS = list(BadgeVariant)
ALERT_VARIANTS = list(AlertVariant)

#: Every accepted color scheme, including the H4 status families.
SCHEMES = (
    "primary",
    "secondary",
    "tertiary",
    "error",
    "neutral",
    "success",
    "warning",
    "info",
)

#: The H4 status families specifically (the ones added in H4a).
STATUS_SCHEMES = ("success", "warning", "info")


# --------------------------------------------------------------------------- #
# H4a — status color families (tokens)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("family", ("success", "warning", "info"))
def test_status_roles_exist(family: str) -> None:
    """Each status family adds its four M3 roles to ``ColorRole``."""
    for prefix in ("", "on_"):
        assert f"{prefix}{family}" in {r.value for r in ColorRole}
    assert f"{family}_container" in {r.value for r in ColorRole}
    assert f"on_{family}_container" in {r.value for r in ColorRole}


@pytest.mark.parametrize("is_dark", (False, True))
@pytest.mark.parametrize("family", STATUS_SCHEMES)
def test_status_roles_resolved_in_scheme(family: str, is_dark: bool) -> None:
    """A seeded scheme resolves every status role to a concrete color."""
    scheme = default_tokens().scheme(is_dark=is_dark)
    for role in (
        ColorRole(family),
        ColorRole(f"on_{family}"),
        ColorRole(f"{family}_container"),
        ColorRole(f"on_{family}_container"),
    ):
        assert isinstance(scheme.role(role), Color)


@pytest.mark.parametrize("is_dark", (False, True))
@pytest.mark.parametrize("family", STATUS_SCHEMES)
def test_status_container_pairs_clear_wcag_aa(family: str, is_dark: bool) -> None:
    """The container/on-container pairing the resolvers emit clears WCAG-AA.

    This is the A1 gate: the saturated status role on white can fail AA (success
    solid = 3.02), so the subtle status surfaces use the ``*_container`` /
    ``on_*_container`` pairing — which must clear 4.5 in both modes.
    """
    scheme = default_tokens().scheme(is_dark=is_dark)
    container = scheme.role(ColorRole(f"{family}_container"))
    on_container = scheme.role(ColorRole(f"on_{family}_container"))
    assert contrast_ratio(container, on_container) >= 4.5


def test_success_solid_fails_aa_proving_the_container_fix_is_needed() -> None:
    """The success solid pairing on white is below AA (the verified 3.02 problem)."""
    scheme = default_tokens().scheme(is_dark=False)
    role = scheme.role(ColorRole.SUCCESS)
    on_role = scheme.role(ColorRole.ON_SUCCESS)
    assert contrast_ratio(role, on_role) < 4.5


def test_status_seeds_are_semantic_not_brand() -> None:
    """The status families are seeded green / amber / blue regardless of brand hue.

    Seeding a magenta brand still yields a recognizably green ``success`` (its
    green channel dominates), proving the fixed semantic seeds are used.
    """
    schemes = color_schemes_from_seed(Color.from_hex("#ff00ff"))
    success = schemes.light.role(ColorRole.SUCCESS)
    assert success.g > success.r and success.g > success.b


def test_status_seeds_overridable() -> None:
    """A custom ``success_seed`` retunes the success family."""
    teal = Color.from_hex("#0d9488")
    schemes = color_schemes_from_seed(Color.from_hex("#6750a4"), success_seed=teal)
    default = color_schemes_from_seed(Color.from_hex("#6750a4"))
    assert schemes.light.role(ColorRole.SUCCESS) != default.light.role(
        ColorRole.SUCCESS
    )


def test_old_color_scheme_constructor_still_validates() -> None:
    """A pre-H4 ``ColorScheme`` (no status roles) still validates and back-fills."""
    fields = default_tokens().schemes.light.model_dump()
    for key in list(fields):
        if any(s in key for s in ("success", "warning", "info")):
            del fields[key]
    scheme = ColorScheme(**fields)
    # Every status role is back-filled (here from the error family) so ``role``
    # never returns ``None``.
    assert scheme.role(ColorRole.SUCCESS) == scheme.role(ColorRole.ERROR)
    assert scheme.role(ColorRole.WARNING_CONTAINER) == scheme.role(
        ColorRole.ERROR_CONTAINER
    )
    assert all(scheme.role(role) is not None for role in ColorRole)


def test_no_style_field_added() -> None:
    """H4 introduces NO new ``Style`` field — status flows via ``color_scheme``.

    The tempestroid sentinels assert ``len(Style.model_fields) == 41``.
    """
    assert len(Style.model_fields) == 41


# --------------------------------------------------------------------------- #
# H4b — badge resolver
# --------------------------------------------------------------------------- #


def test_badge_variant_members() -> None:
    """``BadgeVariant`` exposes the three M3 pill treatments."""
    assert {v.value for v in BadgeVariant} == {"solid", "subtle", "outline"}


def test_alert_variant_members() -> None:
    """``AlertVariant`` exposes the four M3 alert treatments."""
    assert {v.value for v in AlertVariant} == {
        "subtle",
        "solid",
        "left_accent",
        "top_accent",
    }


@pytest.mark.parametrize("variant", BADGE_VARIANTS)
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("state", STATES)
def test_badge_resolves_all_combos(
    variant: BadgeVariant, size: Size, scheme: str, state: ComponentState
) -> None:
    """Every badge combo resolves with content, a pill radius and a font."""
    style = resolve_badge_variant(
        variant=variant,
        size=size,
        color_scheme=scheme,
        theme=THEME,
        state=state,
    )
    assert style.color is not None
    assert style.padding is not None
    assert style.radius == THEME.radius("full")
    assert style.font_size is not None


def test_badge_solid_uses_role_and_on_role() -> None:
    """A solid badge fills with the role and its on-role content."""
    style = resolve_badge_variant(
        variant=BadgeVariant.SOLID, size=Size.SM, color_scheme="info", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.INFO)
    assert style.color == THEME.color(ColorRole.ON_INFO)


def test_badge_subtle_uses_container_pair() -> None:
    """A subtle badge fills with the container and its on-container content."""
    style = resolve_badge_variant(
        variant=BadgeVariant.SUBTLE, size=Size.SM, color_scheme="success", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.SUCCESS_CONTAINER)
    assert style.color == THEME.color(ColorRole.ON_SUCCESS_CONTAINER)


@pytest.mark.parametrize("scheme", STATUS_SCHEMES)
def test_badge_subtle_clears_wcag_aa(scheme: str) -> None:
    """A subtle status badge's emitted pairing clears WCAG-AA (the A1 gate)."""
    style = resolve_badge_variant(
        variant=BadgeVariant.SUBTLE, size=Size.MD, color_scheme=scheme, theme=THEME
    )
    assert isinstance(style.background, Color) and style.color is not None
    assert contrast_ratio(style.background, style.color) >= 4.5


def test_badge_outline_transparent_with_border() -> None:
    """An outline badge has the role as content and a same-color border."""
    style = resolve_badge_variant(
        variant=BadgeVariant.OUTLINE, size=Size.SM, color_scheme="warning", theme=THEME
    )
    assert isinstance(style.border, Border)
    assert style.border.color == THEME.color(ColorRole.WARNING)
    assert style.color == THEME.color(ColorRole.WARNING)


def test_badge_states_table_has_every_state() -> None:
    """The badge state table resolves a style per interaction state."""
    table = resolve_badge_variant_states(
        variant=BadgeVariant.SOLID, size=Size.SM, color_scheme="primary", theme=THEME
    )
    assert set(table) == set(ComponentState)
    for style in table.values():
        assert isinstance(style, Style)


def test_badge_unknown_scheme_raises() -> None:
    """An unknown ``color_scheme`` raises for the badge resolver."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        resolve_badge_variant(
            variant=BadgeVariant.SOLID, size=Size.SM, color_scheme="nope", theme=THEME
        )


# --------------------------------------------------------------------------- #
# H4b — alert resolver
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("variant", ALERT_VARIANTS)
@pytest.mark.parametrize("scheme", SCHEMES)
def test_alert_resolves_all_combos(variant: AlertVariant, scheme: str) -> None:
    """Every alert combo resolves with a fill, content, padding and radius."""
    style = resolve_alert_variant(variant=variant, color_scheme=scheme, theme=THEME)
    assert style.background is not None
    assert style.color is not None
    assert style.padding is not None
    assert style.radius is not None


def test_alert_subtle_uses_container_pair() -> None:
    """A subtle alert fills with the container and its on-container content."""
    style = resolve_alert_variant(
        variant=AlertVariant.SUBTLE, color_scheme="warning", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.WARNING_CONTAINER)
    assert style.color == THEME.color(ColorRole.ON_WARNING_CONTAINER)


def test_alert_solid_uses_role_pair() -> None:
    """A solid alert fills with the role and its on-role content."""
    style = resolve_alert_variant(
        variant=AlertVariant.SOLID, color_scheme="info", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.INFO)
    assert style.color == THEME.color(ColorRole.ON_INFO)


@pytest.mark.parametrize("scheme", STATUS_SCHEMES)
def test_alert_subtle_clears_wcag_aa(scheme: str) -> None:
    """A subtle status alert's emitted pairing clears WCAG-AA (the A1 gate)."""
    style = resolve_alert_variant(
        variant=AlertVariant.SUBTLE, color_scheme=scheme, theme=THEME
    )
    assert isinstance(style.background, Color) and style.color is not None
    assert contrast_ratio(style.background, style.color) >= 4.5


def test_alert_left_accent_has_left_side_border() -> None:
    """A left-accent alert carries a thick left side border in the saturated role."""
    style = resolve_alert_variant(
        variant=AlertVariant.LEFT_ACCENT, color_scheme="success", theme=THEME
    )
    assert isinstance(style.border, SideBorder)
    assert style.border.left is not None
    assert style.border.left.width == 4.0
    assert style.border.left.color == THEME.color(ColorRole.SUCCESS)
    assert style.border.top is None and style.border.right is None


def test_alert_top_accent_has_top_side_border() -> None:
    """A top-accent alert carries a thick top side border in the saturated role."""
    style = resolve_alert_variant(
        variant=AlertVariant.TOP_ACCENT, color_scheme="error", theme=THEME
    )
    assert isinstance(style.border, SideBorder)
    assert style.border.top is not None
    assert style.border.top.width == 4.0
    assert style.border.left is None


def test_alert_unknown_scheme_raises() -> None:
    """An unknown ``color_scheme`` raises for the alert resolver."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        resolve_alert_variant(
            variant=AlertVariant.SUBTLE, color_scheme="nope", theme=THEME
        )


# --------------------------------------------------------------------------- #
# H4c — components
# --------------------------------------------------------------------------- #


def _find(node: Node, predicate: object) -> Node | None:
    """Depth-first search for the first node matching a predicate.

    Args:
        node: The root node.
        predicate: A callable taking a node and returning ``bool``.

    Returns:
        The first matching node, or ``None``.
    """
    if predicate(node):  # type: ignore[operator]
        return node
    for child in node.children:
        found = _find(child, predicate)
        if found is not None:
            return found
    return None


def test_badge_component_themed() -> None:
    """``Badge`` lowers to a themed pill via the badge resolver."""
    node = build(Badge(label="3", color_scheme="success", variant=BadgeVariant.SOLID))
    assert node.type == "Text"
    assert node.props["style"].background == THEME.color(ColorRole.SUCCESS)


def test_badge_legacy_tone_maps_to_scheme() -> None:
    """The legacy ``tone`` prop maps onto the status family (back-compat)."""
    node = build(Badge(label="!", tone="warning"))
    assert node.props["style"].background == THEME.color(ColorRole.WARNING)


def test_banner_legacy_tone_still_works() -> None:
    """``Banner(tone=...)`` keeps working, lowering through the alert resolver."""
    node = build(Banner(message="hi", tone="success"))
    assert node.type == "Row"
    text = _find(node, lambda n: n.type == "Text")
    assert text is not None


def test_alert_lowers_with_title_body_glyph() -> None:
    """``Alert`` lowers to a row with the glyph, title/body column and dismiss."""
    node = build(
        Alert(title="Saved", body="All good", glyph="✓", color_scheme="success")
    )
    assert node.type == "Row"
    title = _find(
        node, lambda n: n.type == "Text" and n.props.get("content") == "Saved"
    )
    assert title is not None


def test_alert_left_accent_lowers() -> None:
    """An ``Alert`` with the left-accent variant lowers with the side border."""
    node = build(Alert(title="Heads up", variant=AlertVariant.LEFT_ACCENT))
    assert isinstance(node.props["style"].border, SideBorder)


def test_stat_lowers_with_delta_tinted() -> None:
    """``Stat`` lowers to label/value/delta, tinting the delta by direction."""
    up = build(Stat(label="Users", value="1.2k", delta="+12%", delta_up=True))
    delta = _find(
        up, lambda n: n.type == "Text" and "12%" in n.props.get("content", "")
    )
    assert delta is not None
    assert delta.props["style"].color == THEME.color(ColorRole.SUCCESS)
    down = build(Stat(label="Errors", value="3", delta="-1", delta_up=False))
    d2 = _find(down, lambda n: n.type == "Text" and "-1" in n.props.get("content", ""))
    assert d2 is not None
    assert d2.props["style"].color == THEME.color(ColorRole.ERROR)


def test_stat_without_delta_omits_it() -> None:
    """A ``Stat`` with no delta lowers to just the label and value."""
    node = build(Stat(label="Total", value="42"))
    assert len(node.children) == 2


def test_progress_stepper_lowers() -> None:
    """``ProgressStepper`` lowers to a row of step cells joined by connectors."""
    node = build(ProgressStepper(steps=["One", "Two", "Three"], current=1))
    assert node.type == "Row"
    # 3 step cells + 2 connectors.
    assert len(node.children) == 5
    label = _find(node, lambda n: n.type == "Text" and n.props.get("content") == "Two")
    assert label is not None


def test_progress_stepper_done_step_uses_accent() -> None:
    """A done/active step's disc fills with the color-scheme accent."""
    node = build(ProgressStepper(steps=["a", "b"], current=0, color_scheme="primary"))
    disc = _find(node, lambda n: n.type == "Text" and n.props.get("content") == "1")
    assert disc is not None
    assert disc.props["style"].background == THEME.color(ColorRole.PRIMARY)


def test_tag_is_a_static_chip_preset() -> None:
    """``Tag`` is a non-selectable, non-tappable ``Chip`` preset (static pill)."""
    tag = Tag(label="beta", color_scheme="info")
    assert isinstance(tag, Chip)
    assert tag.selected is False
    assert tag.on_click is None
    node = build(tag)
    assert node.type == "Text"
    assert node.props["style"].background == THEME.color(ColorRole.INFO_CONTAINER)


def test_chip_selectable_lowers_to_button() -> None:
    """A tappable ``Chip`` lowers to a ``Button`` carrying the badge style."""
    node = build(Chip(label="filter", on_click=lambda: None, color_scheme="primary"))
    assert node.type == "Button"


def test_avatar_uses_container_pair() -> None:
    """``Avatar`` fills with the color-scheme container and on-container content."""
    node = build(Avatar(initials="MB", color_scheme="success"))
    assert node.props["style"].background == THEME.color(ColorRole.SUCCESS_CONTAINER)
    text = _find(node, lambda n: n.type == "Text")
    assert text is not None
    assert text.props["style"].color == THEME.color(ColorRole.ON_SUCCESS_CONTAINER)


def test_avatar_default_is_primary_container() -> None:
    """A default ``Avatar`` uses the primary-container fill (back-compat shape)."""
    node = build(Avatar(initials="AB"))
    assert node.props["style"].background == THEME.color(ColorRole.PRIMARY_CONTAINER)


def test_segmented_control_active_is_solid() -> None:
    """The active segment resolves to a solid treatment via the H1 resolver."""
    node = build(
        SegmentedControl(
            options=["A", "B"],
            selected=0,
            on_select=lambda i: None,
            color_scheme="primary",
        )
    )
    assert node.type == "Row"
    first = node.children[0]
    assert first.props["style"].background == THEME.color(ColorRole.PRIMARY)


def test_rating_star_uses_scheme_role() -> None:
    """``Rating`` colors its stars with the color-scheme role."""
    node = build(Rating(value=3, max_stars=5, color_scheme="warning"))
    star = node.children[0]
    assert star.props["style"].color == THEME.color(ColorRole.WARNING)


def test_empty_state_uses_muted_tokens() -> None:
    """``EmptyState`` reads the muted on-surface-variant role for its glyph."""
    node = build(EmptyState(title="Nothing here", glyph="∅"))
    glyph = _find(node, lambda n: n.type == "Text" and n.props.get("content") == "∅")
    assert glyph is not None
    assert glyph.props["style"].color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


# --------------------------------------------------------------------------- #
# Indicator / overlay color_scheme props
# --------------------------------------------------------------------------- #


def test_indicator_widgets_carry_color_scheme() -> None:
    """ProgressBar / Spinner / Tooltip / Skeleton carry a ``color_scheme`` prop."""
    from tempest_core.widgets import ProgressBar, Skeleton, Spinner, Tooltip

    assert ProgressBar(value=0.5, color_scheme="success").color_scheme == "success"
    assert Spinner(color_scheme="error").color_scheme == "error"
    assert Tooltip(message="hi", color_scheme="primary").color_scheme == "primary"
    assert Skeleton(color_scheme="neutral").color_scheme == "neutral"
