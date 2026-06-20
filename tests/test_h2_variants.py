"""Tests for the H2 input/action-kit variant API (Trilho H, phase H2).

Pins the three pure H2 resolvers (field / selection / slider) across every
``variant × size × color_scheme × state`` combination, the new
:class:`~tempest_core.style.FieldVariant` enum, the per-widget baking of the
resolved :class:`~tempest_core.style.Style` (Input/TextArea/Dropdown/… +
Checkbox/Switch + Slider/RangeSlider), the new :class:`IconButton`'s
square/circular geometry, the theme-driven BR inputs + RadioGroup, the engine
Material-alias icon resolution, and the hard constraint that NO new ``Style``
field was added.
"""

from __future__ import annotations

import pytest

from tempest_core import (
    ComponentState,
    FieldVariant,
    IconButton,
    MediaQueryData,
    Size,
    Theme,
    Variant,
    resolve_field_variant,
    resolve_field_variant_states,
    resolve_selection_variant,
    resolve_selection_variant_states,
    resolve_slider_variant,
    resolve_slider_variant_states,
)
from tempest_core.components import (
    CNPJInput,
    CPFInput,
    EmailInput,
    PasswordInput,
    PhoneInput,
    RadioGroup,
)
from tempest_core.icons import MATERIAL_ALIASES, icon_path
from tempest_core.style import Border, Color, SideBorder, Style
from tempest_core.tokens import ColorRole, contrast_ratio
from tempest_core.variants import (
    DISABLED_CONTENT_OPACITY,
    MIN_TOUCH_TARGET,
    SELECTION_SIZE,
    SLIDER_SIZE,
    VALID_COLOR_SCHEMES,
)
from tempest_core.widgets import (
    Autocomplete,
    Checkbox,
    DatePicker,
    Dropdown,
    FilePicker,
    Input,
    MaskedInput,
    PinInput,
    RangeSlider,
    Slider,
    Switch,
    TextArea,
    TimePicker,
)

THEME = Theme()
SCHEMES = sorted(VALID_COLOR_SCHEMES)
SIZES = list(Size)
STATES = list(ComponentState)


# --------------------------------------------------------------------------- #
# FieldVariant enum + exports
# --------------------------------------------------------------------------- #


def test_field_variant_members() -> None:
    """``FieldVariant`` exposes the three M3 text-field treatments."""
    assert {v.value for v in FieldVariant} == {"outline", "filled", "flushed"}


def test_new_public_surface_importable() -> None:
    """The new H2 surface is importable from the package root."""
    assert FieldVariant.OUTLINE == "outline"
    assert callable(resolve_field_variant)
    assert callable(resolve_selection_variant)
    assert callable(resolve_slider_variant)
    assert IconButton.__name__ == "IconButton"


# --------------------------------------------------------------------------- #
# Field family — resolution table
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("variant", list(FieldVariant))
@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("scheme", SCHEMES)
def test_field_resolves_all_combos(
    variant: FieldVariant, size: Size, scheme: str
) -> None:
    """Every field combo resolves with content, padding and a ≥48dp touch area."""
    style = resolve_field_variant(
        variant=variant, size=size, color_scheme=scheme, theme=THEME
    )
    assert style.color is not None
    assert style.padding is not None
    assert style.min_height is not None and style.min_height >= MIN_TOUCH_TARGET
    assert style.font_size is not None


def test_field_outline_has_full_border() -> None:
    """The outline field carries a uniform border in the outline role."""
    style = resolve_field_variant(
        variant=FieldVariant.OUTLINE, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert isinstance(style.border, Border)
    assert style.border.color == THEME.color(ColorRole.OUTLINE)


def test_field_filled_has_surface_variant_fill_no_border() -> None:
    """The filled field uses the surface-variant fill and no resting border."""
    style = resolve_field_variant(
        variant=FieldVariant.FILLED, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.background == THEME.color(ColorRole.SURFACE_VARIANT)
    assert style.border is None


def test_field_flushed_has_bottom_only_border_no_radius() -> None:
    """The flushed field carries only a bottom side border and no radius."""
    style = resolve_field_variant(
        variant=FieldVariant.FLUSHED, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert isinstance(style.border, SideBorder)
    assert style.border.bottom is not None
    assert style.border.top is None and style.border.left is None
    assert style.radius == 0.0


def test_field_focus_tints_border_to_scheme_role() -> None:
    """Focus thickens the border to 2px in the color-scheme role."""
    for scheme in SCHEMES:
        style = resolve_field_variant(
            variant=FieldVariant.OUTLINE,
            size=Size.MD,
            color_scheme=scheme,
            theme=THEME,
            state=ComponentState.FOCUS,
        )
        assert isinstance(style.border, Border)
        assert style.border.width == 2.0
        role, _on, _c = _scheme_role(scheme)
        assert style.border.color == THEME.color(role)


def test_field_pressed_equals_focus() -> None:
    """A field treats PRESSED as FOCUS (it gains focus, no ripple)."""
    focus = resolve_field_variant(
        variant=FieldVariant.OUTLINE,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.FOCUS,
    )
    pressed = resolve_field_variant(
        variant=FieldVariant.OUTLINE,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.PRESSED,
    )
    assert focus == pressed


def test_field_hover_tints_border_on_surface_variant() -> None:
    """Hover tints the border to the on-surface-variant role."""
    style = resolve_field_variant(
        variant=FieldVariant.OUTLINE,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.HOVER,
    )
    assert isinstance(style.border, Border)
    assert style.border.color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


def test_field_disabled_fades_content_38() -> None:
    """Disabled fades the content color to 38% and the border to outline-variant."""
    style = resolve_field_variant(
        variant=FieldVariant.OUTLINE,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.DISABLED,
    )
    assert style.color is not None
    assert style.color.a == pytest.approx(DISABLED_CONTENT_OPACITY)


def test_field_invalid_forces_error_border_and_label() -> None:
    """An invalid field paints the border + label the error role in every state."""
    error = THEME.color(ColorRole.ERROR)
    for state in STATES:
        style = resolve_field_variant(
            variant=FieldVariant.OUTLINE,
            size=Size.MD,
            color_scheme="primary",
            theme=THEME,
            state=state,
            invalid=True,
        )
        assert style.color == error
        assert isinstance(style.border, Border)
        assert style.border.color == error


def test_field_invalid_flushed_keeps_bottom_only() -> None:
    """An invalid flushed field keeps its bottom-only border (error-colored)."""
    style = resolve_field_variant(
        variant=FieldVariant.FLUSHED,
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        invalid=True,
    )
    assert isinstance(style.border, SideBorder)
    assert style.border.bottom is not None
    assert style.border.bottom.color == THEME.color(ColorRole.ERROR)


def test_field_states_table_is_complete() -> None:
    """The field state table covers every ComponentState."""
    states = resolve_field_variant_states(
        variant=FieldVariant.OUTLINE, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert set(states) == set(ComponentState)


def test_field_unknown_scheme_raises() -> None:
    """An unknown color scheme raises ValueError."""
    with pytest.raises(ValueError, match="unknown color_scheme"):
        resolve_field_variant(
            variant=FieldVariant.OUTLINE,
            size=Size.MD,
            color_scheme="brand",
            theme=THEME,
        )


# --------------------------------------------------------------------------- #
# Selection family — resolution table
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("checked", [True, False])
def test_selection_resolves_all_combos(size: Size, scheme: str, checked: bool) -> None:
    """Every selection combo resolves the accent color and a sized box."""
    style = resolve_selection_variant(
        size=size, color_scheme=scheme, theme=THEME, checked=checked
    )
    role, _on, _c = _scheme_role(scheme)
    assert style.color == THEME.color(role)
    assert style.width == SELECTION_SIZE[size]
    assert style.height == SELECTION_SIZE[size]


def test_selection_checked_fills_with_accent() -> None:
    """A checked control fills its background with the accent."""
    style = resolve_selection_variant(
        size=Size.MD, color_scheme="primary", theme=THEME, checked=True
    )
    assert style.background == THEME.color(ColorRole.PRIMARY)


def test_selection_unchecked_has_outline_ring_no_fill() -> None:
    """An unchecked control has the empty outline ring and no fill."""
    style = resolve_selection_variant(
        size=Size.MD, color_scheme="primary", theme=THEME, checked=False
    )
    assert isinstance(style.border, Border)
    assert style.border.color == THEME.color(ColorRole.OUTLINE)
    assert style.background is None


def test_selection_disabled_fades_38() -> None:
    """Disabled fades the accent to 38%."""
    style = resolve_selection_variant(
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        checked=True,
        state=ComponentState.DISABLED,
    )
    assert style.color is not None
    assert style.color.a == pytest.approx(DISABLED_CONTENT_OPACITY)


def test_selection_state_layer_changes_background() -> None:
    """Hover/pressed/focus add a state layer over the accent (checked)."""
    base = resolve_selection_variant(
        size=Size.MD, color_scheme="primary", theme=THEME, checked=True
    )
    for state in (ComponentState.HOVER, ComponentState.PRESSED, ComponentState.FOCUS):
        layered = resolve_selection_variant(
            size=Size.MD,
            color_scheme="primary",
            theme=THEME,
            checked=True,
            state=state,
        )
        assert layered.background != base.background


def test_selection_states_table_complete() -> None:
    """The selection state table covers every ComponentState."""
    states = resolve_selection_variant_states(
        size=Size.MD, color_scheme="primary", theme=THEME, checked=True
    )
    assert set(states) == set(ComponentState)


# --------------------------------------------------------------------------- #
# Slider family — resolution table
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("size", SIZES)
@pytest.mark.parametrize("scheme", SCHEMES)
def test_slider_resolves_all_combos(size: Size, scheme: str) -> None:
    """Every slider combo resolves the active/inactive tracks and thickness."""
    style = resolve_slider_variant(size=size, color_scheme=scheme, theme=THEME)
    role, _on, _c = _scheme_role(scheme)
    assert style.color == THEME.color(role)
    assert style.background == THEME.color(ColorRole.SURFACE_VARIANT)
    assert style.height == SLIDER_SIZE[size]


def test_slider_disabled_fades_both_tracks() -> None:
    """Disabled fades both the active and inactive tracks to 38%."""
    style = resolve_slider_variant(
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.DISABLED,
    )
    assert style.color is not None and style.color.a == pytest.approx(
        DISABLED_CONTENT_OPACITY
    )
    assert style.background is not None and isinstance(style.background, Color)
    assert style.background.a == pytest.approx(DISABLED_CONTENT_OPACITY)


def test_slider_focus_adds_thumb_halo() -> None:
    """Focus tints the thumb/active track via a state layer (color changes)."""
    base = resolve_slider_variant(size=Size.MD, color_scheme="primary", theme=THEME)
    focus = resolve_slider_variant(
        size=Size.MD,
        color_scheme="primary",
        theme=THEME,
        state=ComponentState.FOCUS,
    )
    assert focus.color != base.color


def test_slider_states_table_complete() -> None:
    """The slider state table covers every ComponentState."""
    states = resolve_slider_variant_states(
        size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert set(states) == set(ComponentState)


# --------------------------------------------------------------------------- #
# Widget wiring — fields bake the resolved style
# --------------------------------------------------------------------------- #


def test_input_bakes_field_style() -> None:
    """``Input`` bakes the resolved outline field style and defaults sensibly."""
    field = Input(value="x")
    assert field.style is not None
    assert isinstance(field.style.border, Border)
    assert field.style.min_height == MIN_TOUCH_TARGET


def test_input_invalid_from_error_paints_error_border() -> None:
    """``Input(error=…)`` resolves invalid → an error-colored border."""
    field = Input(value="x", error="required")
    assert field.style is not None and isinstance(field.style.border, Border)
    assert field.style.border.color == THEME.color(ColorRole.ERROR)


def test_input_explicit_style_overrides_resolved() -> None:
    """An explicit ``style`` is merged on top of the resolved field style."""
    custom = Color.from_hex("#123456")
    field = Input(value="x", style=Style(background=custom))
    assert field.style is not None
    assert field.style.background == custom


def test_input_state_styles_exposed() -> None:
    """``Input.state_styles`` exposes the full per-state table."""
    field = Input(value="x")
    assert set(field.state_styles()) == set(ComponentState)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: Input(value="x"),
        lambda: TextArea(value="x"),
        lambda: Dropdown(options=["a"]),
        lambda: Autocomplete(options=["a"]),
        lambda: MaskedInput(mask="999"),
        lambda: PinInput(length=4),
        lambda: DatePicker(),
        lambda: TimePicker(),
        lambda: FilePicker(),
    ],
)
def test_field_widgets_bake_style(factory: object) -> None:
    """Every field-family widget bakes a resolved style with a touch target."""
    widget = factory()  # type: ignore[operator]
    assert widget.style is not None
    assert widget.style.min_height == MIN_TOUCH_TARGET


def test_pin_input_forces_outline() -> None:
    """``PinInput`` forces the OUTLINE field variant for its segmented cells."""
    pin = PinInput(length=4)
    assert pin.field_variant == FieldVariant.OUTLINE
    assert pin.style is not None and isinstance(pin.style.border, Border)


def test_checkbox_bakes_selection_style() -> None:
    """``Checkbox`` bakes the resolved selection style (accent + sized box)."""
    box = Checkbox(checked=True, color_scheme="error")
    assert box.style is not None
    assert box.style.color == THEME.color(ColorRole.ERROR)
    assert box.style.width == SELECTION_SIZE[Size.MD]


def test_switch_unchecked_has_ring() -> None:
    """An unchecked ``Switch`` bakes the empty outline ring."""
    sw = Switch(checked=False)
    assert sw.style is not None and isinstance(sw.style.border, Border)


def test_slider_widget_bakes_track_style() -> None:
    """``Slider`` bakes the active/inactive track style from the theme."""
    sl = Slider(color_scheme="secondary")
    assert sl.style is not None
    assert sl.style.color == THEME.color(ColorRole.SECONDARY)
    assert sl.style.background == THEME.color(ColorRole.SURFACE_VARIANT)


def test_range_slider_bakes_track_style() -> None:
    """``RangeSlider`` bakes the same track style as ``Slider``."""
    rs = RangeSlider()
    assert rs.style is not None
    assert rs.style.height == SLIDER_SIZE[Size.MD]


def test_theme_media_excluded_from_props() -> None:
    """``theme``/``media`` are kept out of the IR props on every styled widget."""
    for widget in (Input(value="x"), Checkbox(), Slider(), IconButton(icon="x")):
        assert "theme" in type(widget).prop_exclude_names
        assert "media" in type(widget).prop_exclude_names


def test_responsive_size_resolves_via_media() -> None:
    """A responsive ``size`` map resolves against the media query width."""
    wide = Input(
        value="x",
        size={"base": Size.SM, "md": Size.LG},
        media=MediaQueryData(width=900.0),
    )
    narrow = Input(
        value="x",
        size={"base": Size.SM, "md": Size.LG},
        media=MediaQueryData(width=100.0),
    )
    # Different density → different padding baked (SM vs LG).
    assert wide.style is not None and narrow.style is not None
    assert wide.style.padding is not None and narrow.style.padding is not None
    assert wide.style.padding.top != narrow.style.padding.top


# --------------------------------------------------------------------------- #
# IconButton — square / circular geometry
# --------------------------------------------------------------------------- #


def test_icon_button_is_square_and_circular() -> None:
    """``IconButton`` pins a square box and a circular radius."""
    ib = IconButton(icon="settings")
    assert ib.style is not None
    assert ib.style.width == ib.style.height
    assert ib.style.width == MIN_TOUCH_TARGET
    assert ib.style.radius == MIN_TOUCH_TARGET / 2.0


def test_icon_button_default_ghost_variant() -> None:
    """``IconButton`` defaults to the GHOST variant (icon-forward)."""
    ib = IconButton(icon="settings")
    assert ib.variant == Variant.GHOST


def test_icon_button_solid_keeps_square() -> None:
    """A solid icon button keeps the square/circular geometry."""
    ib = IconButton(icon="settings", variant=Variant.SOLID, color_scheme="primary")
    assert ib.style is not None
    assert ib.style.width == ib.style.height
    assert ib.style.background == THEME.color(ColorRole.PRIMARY)


def test_icon_button_state_styles_square() -> None:
    """Every per-state icon-button style stays square."""
    ib = IconButton(icon="settings")
    for style in ib.state_styles().values():
        assert style.width == style.height


def test_icon_button_label_for_a11y() -> None:
    """``IconButton`` carries an accessible ``label``."""
    ib = IconButton(icon="settings", label="Open settings")
    assert ib.label == "Open settings"


# --------------------------------------------------------------------------- #
# BR inputs — theme-driven (not the old dark hexes)
# --------------------------------------------------------------------------- #


def _render_tree(component: object) -> Style:
    """Render a BR component and return the inner field's baked style.

    Args:
        component: A BR field component (``EmailInput``/…).

    Returns:
        The resolved ``Style`` of the inner input widget.
    """
    column = component.render()  # type: ignore[attr-defined]
    # The labelled column's children are [label?, field, error?]; find the field.
    for child in column.child_nodes():
        if isinstance(child, (Input, MaskedInput)):
            assert child.style is not None
            return child.style
    raise AssertionError("no inner field found")


def test_br_email_resolves_theme_colors_not_dark_hex() -> None:
    """``EmailInput`` resolves its inner field from the theme, not the old hex."""
    style = _render_tree(EmailInput(value="", on_change=lambda v: None))
    assert style.color == THEME.color(ColorRole.ON_SURFACE)
    # The old hard-coded dark background (#0b0f14) must NOT be present.
    assert style.background != Color.from_hex("#0b0f14")


def test_br_password_secure_with_theme() -> None:
    """``PasswordInput`` keeps secure + lock and resolves from the theme."""
    comp = PasswordInput(value="", on_change=lambda v: None)
    column = comp.render()
    field = next(c for c in column.child_nodes() if isinstance(c, Input))
    assert field.secure is True
    assert field.leading_icon == "lock"
    assert field.style is not None
    assert field.style.color == THEME.color(ColorRole.ON_SURFACE)


def test_br_email_has_mail_icon() -> None:
    """``EmailInput`` keeps the mail leading icon."""
    comp = EmailInput(value="", on_change=lambda v: None)
    column = comp.render()
    field = next(c for c in column.child_nodes() if isinstance(c, Input))
    assert field.leading_icon == "mail"


def test_br_color_scheme_threads_into_field() -> None:
    """A BR field's ``color_scheme`` threads into the inner field's focus role."""
    comp = CPFInput(value="", on_change=lambda v: None, color_scheme="tertiary")
    column = comp.render()
    field = next(c for c in column.child_nodes() if isinstance(c, MaskedInput))
    assert field.color_scheme == "tertiary"


def test_br_dark_mode_label_color() -> None:
    """A BR field's label uses a theme-driven (dark-aware) muted color."""
    from tempest_core.theme import ThemeMode
    from tempest_core.widgets import Text

    dark = Theme(mode=ThemeMode.DARK)
    comp = PhoneInput(value="", on_change=lambda v: None, theme=dark)
    column = comp.render()
    label = next(c for c in column.child_nodes() if isinstance(c, Text))
    assert label.style is not None
    assert label.style.color == dark.color(ColorRole.ON_SURFACE_VARIANT)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: EmailInput(value="", on_change=lambda v: None),
        lambda: PasswordInput(value="", on_change=lambda v: None),
        lambda: PhoneInput(value="", on_change=lambda v: None),
        lambda: CPFInput(value="", on_change=lambda v: None),
        lambda: CNPJInput(value="", on_change=lambda v: None),
    ],
)
def test_br_fields_touch_target(factory: object) -> None:
    """Every BR field's inner control keeps the ≥48dp touch target."""
    style = _render_tree(factory())  # type: ignore[operator]
    assert style.min_height == MIN_TOUCH_TARGET


# --------------------------------------------------------------------------- #
# RadioGroup — theme accent
# --------------------------------------------------------------------------- #


def test_radio_group_chosen_row_uses_accent() -> None:
    """The chosen radio row's marker color is the color-scheme accent."""
    group = RadioGroup(
        options=["a", "b", "c"],
        selected=1,
        on_select=lambda i: None,
        color_scheme="error",
    )
    column = group.render()
    rows = column.child_nodes()
    chosen = rows[1]
    assert chosen.style is not None
    assert chosen.style.color == THEME.color(ColorRole.ERROR)


def test_radio_group_unchosen_muted() -> None:
    """Unchosen radio rows read the muted on-surface-variant tone."""
    group = RadioGroup(options=["a", "b"], selected=0, on_select=lambda i: None)
    column = group.render()
    other = column.child_nodes()[1]
    assert other.style is not None
    assert other.style.color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


# --------------------------------------------------------------------------- #
# Icon alias resolution promoted to the engine
# --------------------------------------------------------------------------- #


def test_material_alias_resolves_to_curated_glyph() -> None:
    """A Material name alias resolves to its curated glyph via ``icon_path``."""
    assert icon_path("photo_camera") == icon_path("eye")
    assert icon_path("history") == icon_path("clock")
    assert icon_path("person") == icon_path("user")


def test_material_aliases_all_point_at_curated() -> None:
    """Every alias points at a real curated icon (single hop)."""
    for alias, target in MATERIAL_ALIASES.items():
        assert icon_path(target) is not None, f"{alias} → missing {target}"


def test_unknown_icon_still_none() -> None:
    """An unknown icon name still resolves to ``None``."""
    assert icon_path("definitely_not_an_icon") is None


# --------------------------------------------------------------------------- #
# Hard constraint — no new Style field
# --------------------------------------------------------------------------- #


def test_no_style_field_added() -> None:
    """H2 must not add any new ``Style`` field (sentinel for conformance)."""
    # The H1 + H0 baseline: this count is pinned in the tempestroid conformance
    # suite too. If H2 added a field, both break.
    assert len(Style.model_fields) == 41


# --------------------------------------------------------------------------- #
# WCAG-AA — field content vs background stays legible
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("variant", list(FieldVariant))
def test_field_content_contrast_aa(variant: FieldVariant) -> None:
    """The typed-text content keeps WCAG-AA contrast against the field fill."""
    style = resolve_field_variant(
        variant=variant, size=Size.MD, color_scheme="primary", theme=THEME
    )
    assert style.color is not None
    bg = (
        style.background
        if isinstance(style.background, Color)
        else THEME.color(ColorRole.SURFACE)
    )
    assert contrast_ratio(style.color, bg) >= 4.5


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _scheme_role(scheme: str) -> tuple[ColorRole, ColorRole, ColorRole]:
    """Map a color-scheme name to its role triple (test mirror of the resolver).

    Args:
        scheme: A valid color-scheme name.

    Returns:
        The base, on-role and container :class:`ColorRole` triple.
    """
    table: dict[str, tuple[ColorRole, ColorRole, ColorRole]] = {
        "primary": (
            ColorRole.PRIMARY,
            ColorRole.ON_PRIMARY,
            ColorRole.PRIMARY_CONTAINER,
        ),
        "secondary": (
            ColorRole.SECONDARY,
            ColorRole.ON_SECONDARY,
            ColorRole.SECONDARY_CONTAINER,
        ),
        "tertiary": (
            ColorRole.TERTIARY,
            ColorRole.ON_TERTIARY,
            ColorRole.TERTIARY_CONTAINER,
        ),
        "error": (ColorRole.ERROR, ColorRole.ON_ERROR, ColorRole.ERROR_CONTAINER),
        "neutral": (
            ColorRole.ON_SURFACE,
            ColorRole.SURFACE,
            ColorRole.SURFACE_VARIANT,
        ),
    }
    return table[scheme]
