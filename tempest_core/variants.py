"""Chakra-style variant resolution → ``Style`` (Trilho H, phase H1).

This module is the **resolution layer** of the design system: the pure function
:func:`resolve_variant` that turns the Chakra-ergonomics props ``variant`` /
``size`` / ``color_scheme`` (plus an interaction ``state``) into a concrete,
frozen :class:`~tempest_core.style.Style`, resolved against a
:class:`~tempest_core.theme.Theme`'s Material 3 tokens (H0).

It is renderer-agnostic and side-effect-free — the same inputs always produce the
same ``Style`` — so it is unit-testable without a renderer and pinnable in the
conformance suite. The two leaf renderers (tempestroid Qt, android-host Compose)
consume the *resolved* styles; they never re-derive the variant logic.

Design (mirrors Material 3 + Chakra):

* **variant → treatment.** ``solid`` fills with the role color and its legible
  ``on_*`` content; ``outline`` is a transparent fill with the role color as both
  content and a same-color border; ``ghost`` is a transparent fill with the role
  color as content (no border); ``link`` is ``ghost`` plus an underline.
* **size → density.** Padding + font size come from the spacing/typography
  scales, but the **hit target is always kept ≥ 48dp** (the M3 minimum) via
  :data:`MIN_TOUCH_TARGET` — a smaller ``size`` only reduces visual density, never
  the accessible touch area. Radius comes from the shape scale.
* **state → M3 state layer.** ``hover``/``pressed`` overlay the content color over
  the background at the M3 state opacities (:data:`HOVER_OPACITY` /
  :data:`PRESSED_OPACITY`); ``focus`` adds a focus indicator (a contrasting
  border) plus the focus state layer; ``disabled`` drops content/background to
  the M3 disabled opacities (:data:`DISABLED_CONTENT_OPACITY` /
  :data:`DISABLED_CONTAINER_OPACITY`). State layers composite against the resolved
  scheme so contrast is preserved.

Transversais baked into the resolution:

* **a11y / contrast.** The tokens already guarantee WCAG-AA between each role and
  its ``on_*``; the resolver preserves that pairing (solid uses role + on-role;
  outline/ghost/link use role on the surface background, which the M3 tones keep
  legible). Touch target ≥ 48dp is enforced here.
* **RTL.** Padding is emitted as a symmetric :class:`~tempest_core.style.Edge`
  (equal left/right), so there are no fixed ``left``/``right`` sides for a
  renderer to mirror incorrectly — the renderers' ``rtl`` mirroring stays a
  no-op for a button's box. (Directional sides remain the renderers' job for
  asymmetric components.)
* **responsive.** ``size`` may be a single :class:`~tempest_core.style.Size` or a
  per-breakpoint map (``{"base": Size.SM, "md": Size.LG}``) resolved against the
  theme's :class:`~tempest_core.tokens.Breakpoints` and an optional
  :class:`~tempest_core.theme.MediaQueryData` viewport width.
"""

from __future__ import annotations

from tempest_core.style import (
    Border,
    CardVariant,
    Color,
    ComponentState,
    Edge,
    FieldVariant,
    Shadow,
    SideBorder,
    Size,
    Style,
    TextDecoration,
    Variant,
)
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.tokens import ColorRole, ColorScheme

__all__ = [
    "VALID_COLOR_SCHEMES",
    "MIN_TOUCH_TARGET",
    "HOVER_OPACITY",
    "PRESSED_OPACITY",
    "FOCUS_OPACITY",
    "DISABLED_CONTENT_OPACITY",
    "DISABLED_CONTAINER_OPACITY",
    "SELECTION_SIZE",
    "SLIDER_SIZE",
    "ELEVATION_SHADOW_COLOR",
    "ResponsiveSize",
    "merge_styles",
    "resolve_size",
    "resolve_variant",
    "resolve_variant_states",
    "resolve_field_variant",
    "resolve_field_variant_states",
    "resolve_selection_variant",
    "resolve_selection_variant_states",
    "resolve_slider_variant",
    "resolve_slider_variant_states",
    "resolve_surface_variant",
]

#: The ``color_scheme`` names a styled component accepts. Each names a Material 3
#: role *family* present in the tokens; ``"neutral"`` maps onto the surface roles
#: (surface / on-surface / outline) so a low-chroma, neutral treatment is
#: available without inventing a role.
VALID_COLOR_SCHEMES: frozenset[str] = frozenset(
    {"primary", "secondary", "tertiary", "error", "neutral"}
)

#: The Material 3 minimum touch-target size in logical pixels. Every resolved
#: style pins ``min_height`` to at least this, regardless of ``size``, so an
#: ``xs``/``sm`` button stays accessible even though it looks more compact.
MIN_TOUCH_TARGET: float = 48.0

#: The Material 3 hover state-layer opacity (content color over the background).
HOVER_OPACITY: float = 0.08

#: The Material 3 pressed state-layer opacity.
PRESSED_OPACITY: float = 0.12

#: The Material 3 focus state-layer opacity.
FOCUS_OPACITY: float = 0.12

#: The Material 3 disabled *content* opacity (text/icon at ~38%).
DISABLED_CONTENT_OPACITY: float = 0.38

#: The Material 3 disabled *container* opacity (filled background at ~12%).
DISABLED_CONTAINER_OPACITY: float = 0.12

#: A ``size`` prop: either a single :class:`~tempest_core.style.Size` or a
#: per-breakpoint map keyed by ``"base"`` plus any of the theme's breakpoint names
#: (``"sm"``/``"md"``/``"lg"``/``"xl"``), Chakra-style.
ResponsiveSize = Size | dict[str, Size]

#: Per-``size`` density: ``(vertical_padding, horizontal_padding, font_size,
#: radius_step)`` in logical pixels (radius is a shape-scale step name). These
#: tune the *visual* density only; the hit target is clamped to
#: :data:`MIN_TOUCH_TARGET` separately.
_SIZE_DENSITY: dict[Size, tuple[float, float, str, str]] = {
    Size.XS: (4.0, 12.0, "label_medium", "sm"),
    Size.SM: (6.0, 16.0, "label_large", "sm"),
    Size.MD: (10.0, 24.0, "label_large", "full"),
    Size.LG: (14.0, 32.0, "title_small", "full"),
}

#: The ascending breakpoint order used to resolve a responsive ``size`` map: the
#: widest breakpoint whose min-width the viewport meets wins (mobile-first, like
#: Chakra). ``"base"`` is the implicit ``0``-width entry.
_BREAKPOINT_ORDER: tuple[str, ...] = ("base", "sm", "md", "lg", "xl")

#: The control-box edge (width == height) per ``size`` for a selection control
#: (checkbox / switch thumb dimension) in logical pixels. The visible box scales
#: with size; the *touch target* stays ≥ 48dp via the parent row, never the box.
SELECTION_SIZE: dict[Size, float] = {
    Size.XS: 16.0,
    Size.SM: 18.0,
    Size.MD: 20.0,
    Size.LG: 24.0,
}

#: The active/inactive track thickness per ``size`` for a slider, in logical
#: pixels. The thumb halo + touch target stay ≥ 48dp via the renderer, never the
#: track height.
SLIDER_SIZE: dict[Size, float] = {
    Size.XS: 2.0,
    Size.SM: 3.0,
    Size.MD: 4.0,
    Size.LG: 6.0,
}


def _scheme_roles(color_scheme: str) -> tuple[ColorRole, ColorRole, ColorRole]:
    """Map a ``color_scheme`` to its ``(role, on_role, container)`` color roles.

    Args:
        color_scheme: A validated color-scheme name (see
            :data:`VALID_COLOR_SCHEMES`).

    Returns:
        The base role, its legible ``on_*`` foreground role, and a container
        role used as a low-emphasis fill (e.g. for a disabled container).
    """
    if color_scheme == "primary":
        return ColorRole.PRIMARY, ColorRole.ON_PRIMARY, ColorRole.PRIMARY_CONTAINER
    if color_scheme == "secondary":
        return (
            ColorRole.SECONDARY,
            ColorRole.ON_SECONDARY,
            ColorRole.SECONDARY_CONTAINER,
        )
    if color_scheme == "tertiary":
        return ColorRole.TERTIARY, ColorRole.ON_TERTIARY, ColorRole.TERTIARY_CONTAINER
    if color_scheme == "error":
        return ColorRole.ERROR, ColorRole.ON_ERROR, ColorRole.ERROR_CONTAINER
    # "neutral" — the surface roles give a low-chroma treatment without a
    # dedicated neutral role family.
    return ColorRole.ON_SURFACE, ColorRole.SURFACE, ColorRole.SURFACE_VARIANT


def resolve_size(
    size: ResponsiveSize,
    theme: Theme,
    *,
    media: MediaQueryData | None = None,
) -> Size:
    """Resolve a (possibly responsive) ``size`` prop to a concrete ``Size``.

    A bare :class:`~tempest_core.style.Size` resolves to itself. A per-breakpoint
    map is resolved mobile-first against the theme's
    :class:`~tempest_core.tokens.Breakpoints` and the optional viewport width
    from ``media``: the entry for the widest breakpoint whose min-width the
    viewport meets wins, falling back to ``"base"`` (or the smallest provided
    entry) when no width context is available.

    Args:
        size: The size prop — a single ``Size`` or a ``{"base": …, "md": …}`` map.
        theme: The theme whose breakpoints resolve the map.
        media: The current viewport snapshot; when ``None`` (or width ``0``) the
            ``"base"`` entry is used.

    Returns:
        The concrete ``Size`` for the current viewport.

    Raises:
        ValueError: If ``size`` is an empty map or names an unknown breakpoint.
    """
    if isinstance(size, Size):
        return size
    if not size:
        raise ValueError("responsive size map must not be empty")
    unknown = set(size) - set(_BREAKPOINT_ORDER)
    if unknown:
        raise ValueError(f"unknown breakpoint(s) in size map: {sorted(unknown)}")

    width = media.width if media is not None else 0.0
    breakpoints = theme.tokens.breakpoints
    min_widths: dict[str, float] = {
        "base": 0.0,
        "sm": breakpoints.sm,
        "md": breakpoints.md,
        "lg": breakpoints.lg,
        "xl": breakpoints.xl,
    }

    chosen: Size | None = None
    for name in _BREAKPOINT_ORDER:
        if name in size and width >= min_widths[name]:
            chosen = size[name]
    if chosen is not None:
        return chosen
    # Width below every provided breakpoint's min-width: use the smallest
    # provided entry (mobile-first fallback).
    for name in _BREAKPOINT_ORDER:
        if name in size:
            return size[name]
    raise ValueError("responsive size map must not be empty")


def _base_style(
    *,
    variant: Variant,
    role_color: Color,
    on_role_color: Color,
    surface_color: Color,
    size: Size,
    theme: Theme,
) -> Style:
    """Build the resting (``DEFAULT``-state) style for a variant + size.

    Args:
        variant: The visual treatment.
        role_color: The resolved base role color.
        on_role_color: The resolved legible ``on_*`` color for the role.
        surface_color: The resolved surface color (the background outline/ghost/
            link treatments sit on).
        size: The concrete density size.
        theme: The theme (for the shape scale).

    Returns:
        The base, opaque ``Style`` for the resting state.
    """
    vpad, hpad, font_role, radius_step = _SIZE_DENSITY[size]
    typography = theme.typography(font_role)
    padding = Edge.symmetric(vertical=vpad, horizontal=hpad)
    radius = theme.radius(radius_step)

    if variant is Variant.SOLID:
        return Style(
            background=role_color,
            color=on_role_color,
            padding=padding,
            radius=radius,
            min_height=MIN_TOUCH_TARGET,
            font_size=typography.font_size,
            font_weight=typography.font_weight,
        )
    if variant is Variant.OUTLINE:
        return Style(
            background=surface_color,
            color=role_color,
            border=Border(width=1.0, color=role_color),
            padding=padding,
            radius=radius,
            min_height=MIN_TOUCH_TARGET,
            font_size=typography.font_size,
            font_weight=typography.font_weight,
        )
    if variant is Variant.GHOST:
        return Style(
            background=surface_color,
            color=role_color,
            padding=padding,
            radius=radius,
            min_height=MIN_TOUCH_TARGET,
            font_size=typography.font_size,
            font_weight=typography.font_weight,
        )
    # LINK.
    return Style(
        background=surface_color,
        color=role_color,
        text_decoration=TextDecoration.UNDERLINE,
        padding=padding,
        radius=radius,
        min_height=MIN_TOUCH_TARGET,
        font_size=typography.font_size,
        font_weight=typography.font_weight,
    )


def merge_styles(base: Style, override: Style) -> Style:
    """Layer ``override`` over ``base`` and re-validate nested value objects.

    Unlike :meth:`~tempest_core.style.Style.merge` (which updates via
    ``model_copy`` without re-validation, leaving a nested ``Color`` as a raw
    dict), this dumps both styles, overlays the override's set fields and
    validates once — so the resulting ``Style`` keeps properly-typed ``Color`` /
    ``Border`` / ``Edge`` values. Mirrors ``Theme.resolve_style``'s approach.

    Args:
        base: The base style.
        override: The style whose set (non-``None``) fields win.

    Returns:
        A new, fully-validated merged ``Style``.
    """
    merged = base.model_dump(exclude_none=True)
    merged.update(override.model_dump(exclude_none=True))
    return Style.model_validate(merged)


def _layer_color(base: Style, surface_color: Color) -> Color:
    """Pick the opaque backdrop a state layer composites against.

    Args:
        base: The resting style.
        surface_color: The scheme's surface color, the fallback backdrop for a
            transparent (outline/ghost/link) treatment.

    Returns:
        The opaque backdrop color.
    """
    background = base.background
    if isinstance(background, Color):
        return background
    return surface_color


def _apply_state(
    base: Style,
    *,
    state: ComponentState,
    role_color: Color,
    on_role_color: Color,
    surface_color: Color,
) -> Style:
    """Layer a Material 3 state layer over a resting style.

    Args:
        base: The resting (``DEFAULT``) style.
        state: The interaction state to resolve for.
        role_color: The resolved base role color.
        on_role_color: The resolved legible ``on_*`` color.
        surface_color: The resolved surface color.

    Returns:
        The state-adjusted style (``base`` unchanged for ``DEFAULT``).
    """
    if state is ComponentState.DEFAULT:
        return base

    backdrop = _layer_color(base, surface_color)
    # The state layer paints the *content* color over the backdrop, except solid,
    # whose content is the on-role (already legible) so the layer uses the role
    # color for a visible tint over the filled background.
    is_filled = isinstance(base.background, Color) and base.color == on_role_color
    layer_source = on_role_color if is_filled else role_color

    if state is ComponentState.HOVER:
        return merge_styles(
            base, Style(background=layer_source.overlay(backdrop, HOVER_OPACITY))
        )
    if state is ComponentState.PRESSED:
        return merge_styles(
            base, Style(background=layer_source.overlay(backdrop, PRESSED_OPACITY))
        )
    if state is ComponentState.FOCUS:
        # A focus indicator (a contrasting border in the role color) plus the
        # focus state layer over the backdrop.
        return merge_styles(
            base,
            Style(
                background=layer_source.overlay(backdrop, FOCUS_OPACITY),
                border=Border(width=2.0, color=role_color),
            ),
        )
    # DISABLED: M3 mutes per element (content vs container), NOT a blanket box
    # opacity. Fade the content color to 38% and (filled) the container to 12%.
    # Setting BOTH Style.opacity AND a faded color would double up (0.38 x 0.38),
    # so the box opacity is intentionally left unset.
    disabled_content = base.color
    overrides = Style()
    if disabled_content is not None:
        faded = disabled_content.with_alpha(DISABLED_CONTENT_OPACITY)
        overrides = merge_styles(overrides, Style(color=faded))
    if isinstance(base.background, Color) and base.color == on_role_color:
        overrides = merge_styles(
            overrides,
            Style(
                background=role_color.overlay(surface_color, DISABLED_CONTAINER_OPACITY)
            ),
        )
    return merge_styles(base, overrides)


def resolve_variant(
    *,
    variant: Variant,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    state: ComponentState = ComponentState.DEFAULT,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> Style:
    """Resolve Chakra-style variant props into a concrete Material 3 ``Style``.

    This is the heart of H1: a pure function that maps ``variant`` / ``size`` /
    ``color_scheme`` (+ an interaction ``state``) onto a frozen
    :class:`~tempest_core.style.Style`, resolved against the theme's M3 tokens. It
    is renderer-agnostic and deterministic, so it is unit-tested exhaustively and
    pinned by the conformance suite. See the module docstring for the full
    variant→treatment, size→density and state→state-layer mapping.

    Args:
        variant: The visual treatment (solid/outline/ghost/link).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map resolved against the theme + ``media``.
        color_scheme: The Material 3 role family to paint with — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply colors, spacing, shape and type.
        state: The interaction state to resolve for (default
            :attr:`~tempest_core.style.ComponentState.DEFAULT`).
        platform_dark_mode: The OS dark-mode flag, used to resolve ``SYSTEM``
            theme mode to the right color scheme.
        media: The current viewport snapshot, used to resolve a responsive
            ``size`` map; ``None`` resolves to the ``"base"`` entry.

    Returns:
        The resolved, frozen ``Style`` for the requested combination.

    Raises:
        ValueError: If ``color_scheme`` is not one of :data:`VALID_COLOR_SCHEMES`,
            or the responsive ``size`` map is malformed.
    """
    if color_scheme not in VALID_COLOR_SCHEMES:
        raise ValueError(
            f"unknown color_scheme: {color_scheme!r}; "
            f"expected one of {sorted(VALID_COLOR_SCHEMES)}"
        )

    concrete_size = resolve_size(size, theme, media=media)
    scheme = theme.scheme(platform_dark_mode=platform_dark_mode)
    role, on_role, _container = _scheme_roles(color_scheme)
    role_color = scheme.role(role)
    on_role_color = scheme.role(on_role)
    surface_color = scheme.role(ColorRole.SURFACE)

    base = _base_style(
        variant=variant,
        role_color=role_color,
        on_role_color=on_role_color,
        surface_color=surface_color,
        size=concrete_size,
        theme=theme,
    )
    return _apply_state(
        base,
        state=state,
        role_color=role_color,
        on_role_color=on_role_color,
        surface_color=surface_color,
    )


def resolve_variant_states(
    *,
    variant: Variant,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> dict[ComponentState, Style]:
    """Resolve the full per-state style table for a variant + size + scheme.

    This is the **seam the renderers consume**: a styled component asks for every
    interaction state up front (``default``/``hover``/``pressed``/``disabled``/
    ``focus``) and hands the table to the renderer, which applies the matching
    style on real pointer/focus events (Qt QSS pseudo-states; Compose
    ``InteractionSource`` / Material3 state layers). The resolution stays pure and
    in the engine; only the event→state mapping lives in the renderers.

    Args:
        variant: The visual treatment.
        size: The density size (single or responsive map).
        color_scheme: The Material 3 role family — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply the values.
        platform_dark_mode: The OS dark-mode flag.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        A mapping of every :class:`~tempest_core.style.ComponentState` to its
        resolved ``Style``.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    return {
        state: resolve_variant(
            variant=variant,
            size=size,
            color_scheme=color_scheme,
            theme=theme,
            state=state,
            platform_dark_mode=platform_dark_mode,
            media=media,
        )
        for state in ComponentState
    }


# --------------------------------------------------------------------------- #
# H2 — field family (text inputs / select / masked / autocomplete / pin)
# --------------------------------------------------------------------------- #


def _field_base_style(
    *,
    variant: FieldVariant,
    role_color: Color,
    on_surface: Color,
    surface_variant: Color,
    outline: Color,
    size: Size,
    theme: Theme,
) -> Style:
    """Build the resting (``DEFAULT``-state) style for a field variant + size.

    Fields are focus-led: the resting treatment is low-emphasis (an outline, a
    tonal fill, or a single bottom rule) and the ``color_scheme`` role only tints
    the focus/caret/label (applied by :func:`_apply_field_state`), never the
    resting fill. The content (typed text) is always ``on_surface`` so it stays
    legible on every variant.

    Args:
        variant: The field treatment (outline / filled / flushed).
        role_color: The resolved ``color_scheme`` role color (unused at rest; the
            focus tint reads it later).
        on_surface: The resolved ``ON_SURFACE`` color (the typed-text content).
        surface_variant: The resolved ``SURFACE_VARIANT`` color (the filled fill).
        outline: The resolved ``OUTLINE`` color (the resting border).
        size: The concrete density size.
        theme: The theme (for the shape scale).

    Returns:
        The base, resting ``Style`` for the field.
    """
    vpad, hpad, font_role, _radius_step = _SIZE_DENSITY[size]
    typography = theme.typography(font_role)
    padding = Edge.symmetric(vertical=vpad, horizontal=hpad)
    radius_sm = theme.radius("sm")

    if variant is FieldVariant.FILLED:
        return Style(
            background=surface_variant,
            color=on_surface,
            radius=radius_sm,
            padding=padding,
            min_height=MIN_TOUCH_TARGET,
            font_size=typography.font_size,
            font_weight=typography.font_weight,
        )
    if variant is FieldVariant.FLUSHED:
        return Style(
            border=SideBorder(bottom=Border(width=1.0, color=outline)),
            color=on_surface,
            radius=theme.radius("none"),
            padding=padding,
            min_height=MIN_TOUCH_TARGET,
            font_size=typography.font_size,
            font_weight=typography.font_weight,
        )
    # OUTLINE — a full same-color outline border at the resting outline role.
    return Style(
        border=Border(width=1.0, color=outline),
        color=on_surface,
        radius=radius_sm,
        padding=padding,
        min_height=MIN_TOUCH_TARGET,
        font_size=typography.font_size,
        font_weight=typography.font_weight,
    )


def _apply_field_state(
    base: Style,
    *,
    variant: FieldVariant,
    state: ComponentState,
    accent: Color,
    on_surface: Color,
    on_surface_variant: Color,
    outline_variant: Color,
    error: Color,
    invalid: bool,
) -> Style:
    """Layer the focus/hover/disabled treatment over a resting field style.

    The border color leads the field's state feedback: ``FOCUS``/``PRESSED`` tint
    it to the ``color_scheme`` ``accent`` (2px), ``HOVER`` to
    ``on_surface_variant``, ``DISABLED`` fades the content to 38% and the border
    to ``outline_variant``. When ``invalid`` is set the border/label are forced to
    the ``error`` role regardless of state (the focus accent gives way to error).

    Args:
        base: The resting field style.
        variant: The field treatment (decides which border slot to tint).
        state: The interaction state to resolve for.
        accent: The resolved ``color_scheme`` role color (focus tint).
        on_surface: The resolved ``ON_SURFACE`` color.
        on_surface_variant: The resolved ``ON_SURFACE_VARIANT`` color (hover).
        outline_variant: The resolved ``OUTLINE_VARIANT`` color (disabled border).
        error: The resolved ``ERROR`` color (invalid border).
        invalid: Whether the field is in an invalid (error) state.

    Returns:
        The state-adjusted field style.
    """

    def _border(color: Color, width: float) -> Border | SideBorder:
        if variant is FieldVariant.FLUSHED:
            return SideBorder(bottom=Border(width=width, color=color))
        return Border(width=width, color=color)

    # An invalid field paints its border error-red in every state; focus still
    # thickens it to 2px so the active error field reads as focused-and-wrong.
    if invalid:
        width = 2.0 if state in (ComponentState.FOCUS, ComponentState.PRESSED) else 1.0
        return merge_styles(base, Style(border=_border(error, width), color=error))

    if state is ComponentState.DEFAULT:
        return base
    if state is ComponentState.HOVER:
        return merge_styles(base, Style(border=_border(on_surface_variant, 1.0)))
    if state in (ComponentState.FOCUS, ComponentState.PRESSED):
        # PRESSED is treated as FOCUS for a field (no ripple — it gains focus).
        return merge_styles(base, Style(border=_border(accent, 2.0)))
    # DISABLED — fade content to 38% and the border to the low-emphasis outline.
    return merge_styles(
        base,
        Style(
            color=on_surface.with_alpha(DISABLED_CONTENT_OPACITY),
            border=_border(outline_variant, 1.0),
        ),
    )


def resolve_field_variant(
    *,
    variant: FieldVariant,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    state: ComponentState = ComponentState.DEFAULT,
    invalid: bool = False,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> Style:
    """Resolve a text-field's Chakra-style props into a Material 3 ``Style``.

    The H2 sibling of :func:`resolve_variant` for the **field family** (text input,
    text area, select/dropdown, masked input, autocomplete, pin). A field is
    focus-led: the resting treatment is low-emphasis (outline / filled / flushed)
    and the ``color_scheme`` role only tints the focus border/caret/label. An
    ``invalid`` field forces the border + label to the ``error`` role in every
    state (it coexists with the field's separate error-message text, which the
    field widget renders elsewhere). Pure and deterministic, like every resolver.

    Args:
        variant: The field treatment (outline / filled / flushed).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map resolved against the theme + ``media``.
        color_scheme: The Material 3 role family the focus tint paints with — one
            of :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply colors, spacing, shape and type.
        state: The interaction state to resolve for (default
            :attr:`~tempest_core.style.ComponentState.DEFAULT`).
        invalid: Whether the field is in an invalid (error) state — forces the
            border/label to the ``error`` role.
        platform_dark_mode: The OS dark-mode flag, used to resolve the scheme.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        The resolved, frozen ``Style`` for the requested field combination.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    if color_scheme not in VALID_COLOR_SCHEMES:
        raise ValueError(
            f"unknown color_scheme: {color_scheme!r}; "
            f"expected one of {sorted(VALID_COLOR_SCHEMES)}"
        )

    concrete_size = resolve_size(size, theme, media=media)
    scheme = theme.scheme(platform_dark_mode=platform_dark_mode)
    role, _on_role, _container = _scheme_roles(color_scheme)
    accent = scheme.role(role)
    on_surface = scheme.role(ColorRole.ON_SURFACE)
    surface_variant = scheme.role(ColorRole.SURFACE_VARIANT)
    outline = scheme.role(ColorRole.OUTLINE)
    on_surface_variant = scheme.role(ColorRole.ON_SURFACE_VARIANT)
    outline_variant = scheme.role(ColorRole.OUTLINE_VARIANT)
    error = scheme.role(ColorRole.ERROR)

    base = _field_base_style(
        variant=variant,
        role_color=accent,
        on_surface=on_surface,
        surface_variant=surface_variant,
        outline=outline,
        size=concrete_size,
        theme=theme,
    )
    return _apply_field_state(
        base,
        variant=variant,
        state=state,
        accent=accent,
        on_surface=on_surface,
        on_surface_variant=on_surface_variant,
        outline_variant=outline_variant,
        error=error,
        invalid=invalid,
    )


def resolve_field_variant_states(
    *,
    variant: FieldVariant,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    invalid: bool = False,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> dict[ComponentState, Style]:
    """Resolve the full per-state style table for a field variant + size + scheme.

    The H2 field-family counterpart of :func:`resolve_variant_states` — the seam
    the renderers consume to apply the matching style on real focus/hover events.

    Args:
        variant: The field treatment (outline / filled / flushed).
        size: The density size (single or responsive map).
        color_scheme: The Material 3 role family — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply the values.
        invalid: Whether the field is in an invalid (error) state.
        platform_dark_mode: The OS dark-mode flag.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        A mapping of every :class:`~tempest_core.style.ComponentState` to its
        resolved ``Style``.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    return {
        state: resolve_field_variant(
            variant=variant,
            size=size,
            color_scheme=color_scheme,
            theme=theme,
            state=state,
            invalid=invalid,
            platform_dark_mode=platform_dark_mode,
            media=media,
        )
        for state in ComponentState
    }


# --------------------------------------------------------------------------- #
# H2 — selection family (checkbox / switch / radio row)
# --------------------------------------------------------------------------- #


def resolve_selection_variant(
    *,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    state: ComponentState = ComponentState.DEFAULT,
    checked: bool = False,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> Style:
    """Resolve a selection control's props into a Material 3 ``Style``.

    The H2 sibling of :func:`resolve_variant` for the **selection family**
    (checkbox, switch, radio row). Material 3 gives selection controls a single
    affordance each, so there is **no** ``variant`` param. The resolved style
    carries: the accent (``color_scheme`` role) as ``color`` (the tick / on-track);
    ``background`` = the accent when ``checked`` else transparent (no fill); the
    ``outline`` role as the empty-ring ``border`` when unchecked; and the control
    box dimension (``width`` == ``height``) from :data:`SELECTION_SIZE`. The 48dp
    touch target is the parent row's job, never the box.

    Args:
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map resolved against the theme + ``media``.
        color_scheme: The Material 3 role family the accent paints with — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply colors and the dimension.
        state: The interaction state to resolve for.
        checked: Whether the control is currently selected/on.
        platform_dark_mode: The OS dark-mode flag, used to resolve the scheme.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        The resolved, frozen ``Style`` for the requested selection combination.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    if color_scheme not in VALID_COLOR_SCHEMES:
        raise ValueError(
            f"unknown color_scheme: {color_scheme!r}; "
            f"expected one of {sorted(VALID_COLOR_SCHEMES)}"
        )

    concrete_size = resolve_size(size, theme, media=media)
    scheme = theme.scheme(platform_dark_mode=platform_dark_mode)
    role, _on_role, _container = _scheme_roles(color_scheme)
    accent = scheme.role(role)
    on_surface = scheme.role(ColorRole.ON_SURFACE)
    outline = scheme.role(ColorRole.OUTLINE)
    dim = SELECTION_SIZE[concrete_size]

    if checked:
        base = Style(
            color=accent,
            background=accent,
            width=dim,
            height=dim,
        )
    else:
        base = Style(
            color=accent,
            border=Border(width=2.0, color=outline),
            width=dim,
            height=dim,
        )

    if state is ComponentState.DEFAULT:
        return base
    # A selection control's state layer paints the ``on_surface`` content color
    # over the backdrop — the accent fill (when checked) or the surface (when
    # unchecked) — so the layer is always a visible tint distinct from the fill.
    layer_source = on_surface
    backdrop = accent if checked else scheme.role(ColorRole.SURFACE)
    if state is ComponentState.HOVER:
        return merge_styles(
            base, Style(background=layer_source.overlay(backdrop, HOVER_OPACITY))
        )
    if state is ComponentState.PRESSED:
        return merge_styles(
            base, Style(background=layer_source.overlay(backdrop, PRESSED_OPACITY))
        )
    if state is ComponentState.FOCUS:
        return merge_styles(
            base,
            Style(
                background=layer_source.overlay(backdrop, FOCUS_OPACITY),
                border=Border(width=2.0, color=accent),
            ),
        )
    # DISABLED — fade the accent (and the ring, when unchecked) to 38%.
    overrides = Style(color=accent.with_alpha(DISABLED_CONTENT_OPACITY))
    if checked:
        overrides = merge_styles(
            overrides, Style(background=accent.with_alpha(DISABLED_CONTENT_OPACITY))
        )
    else:
        overrides = merge_styles(
            overrides,
            Style(
                border=Border(
                    width=2.0, color=outline.with_alpha(DISABLED_CONTENT_OPACITY)
                )
            ),
        )
    return merge_styles(base, overrides)


def resolve_selection_variant_states(
    *,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    checked: bool = False,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> dict[ComponentState, Style]:
    """Resolve the full per-state style table for a selection control.

    The H2 selection-family counterpart of :func:`resolve_variant_states`.

    Args:
        size: The density size (single or responsive map).
        color_scheme: The Material 3 role family — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply the values.
        checked: Whether the control is currently selected/on.
        platform_dark_mode: The OS dark-mode flag.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        A mapping of every :class:`~tempest_core.style.ComponentState` to its
        resolved ``Style``.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    return {
        state: resolve_selection_variant(
            size=size,
            color_scheme=color_scheme,
            theme=theme,
            state=state,
            checked=checked,
            platform_dark_mode=platform_dark_mode,
            media=media,
        )
        for state in ComponentState
    }


# --------------------------------------------------------------------------- #
# H2 — slider family (slider / range slider)
# --------------------------------------------------------------------------- #


def resolve_slider_variant(
    *,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    state: ComponentState = ComponentState.DEFAULT,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> Style:
    """Resolve a slider's props into a Material 3 ``Style``.

    The H2 sibling of :func:`resolve_variant` for the **slider family** (slider,
    range slider). Material 3 gives a slider a single affordance, so there is
    **no** ``variant`` param. The resolved style carries: the accent
    (``color_scheme`` role) as ``color`` (the active track + thumb); the
    ``surface_variant`` role as ``background`` (the inactive track); the track
    thickness as ``height`` from :data:`SLIDER_SIZE`; and a thumb radius hint as
    ``radius`` (the M3 ``full`` pill). The thumb halo + 48dp touch target are the
    renderer's job, never the track height.

    Args:
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map resolved against the theme + ``media``.
        color_scheme: The Material 3 role family the accent paints with — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply colors and the track thickness.
        state: The interaction state to resolve for.
        platform_dark_mode: The OS dark-mode flag, used to resolve the scheme.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        The resolved, frozen ``Style`` for the requested slider combination.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    if color_scheme not in VALID_COLOR_SCHEMES:
        raise ValueError(
            f"unknown color_scheme: {color_scheme!r}; "
            f"expected one of {sorted(VALID_COLOR_SCHEMES)}"
        )

    concrete_size = resolve_size(size, theme, media=media)
    scheme = theme.scheme(platform_dark_mode=platform_dark_mode)
    role, _on_role, _container = _scheme_roles(color_scheme)
    accent = scheme.role(role)
    surface_variant = scheme.role(ColorRole.SURFACE_VARIANT)
    track = SLIDER_SIZE[concrete_size]

    base = Style(
        color=accent,
        background=surface_variant,
        height=track,
        radius=theme.radius("full"),
    )

    if state is ComponentState.DEFAULT:
        return base
    if state in (ComponentState.HOVER, ComponentState.PRESSED, ComponentState.FOCUS):
        # The thumb halo is a state layer over the accent; the active track stays
        # the accent (carried in ``color``).
        opacity = {
            ComponentState.HOVER: HOVER_OPACITY,
            ComponentState.PRESSED: PRESSED_OPACITY,
            ComponentState.FOCUS: FOCUS_OPACITY,
        }[state]
        return merge_styles(base, Style(color=accent.overlay(surface_variant, opacity)))
    # DISABLED — fade both tracks to 38%.
    return merge_styles(
        base,
        Style(
            color=accent.with_alpha(DISABLED_CONTENT_OPACITY),
            background=surface_variant.with_alpha(DISABLED_CONTENT_OPACITY),
        ),
    )


def resolve_slider_variant_states(
    *,
    size: ResponsiveSize,
    color_scheme: str,
    theme: Theme,
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> dict[ComponentState, Style]:
    """Resolve the full per-state style table for a slider.

    The H2 slider-family counterpart of :func:`resolve_variant_states`.

    Args:
        size: The density size (single or responsive map).
        color_scheme: The Material 3 role family — one of
            :data:`VALID_COLOR_SCHEMES`.
        theme: The theme whose tokens supply the values.
        platform_dark_mode: The OS dark-mode flag.
        media: The current viewport snapshot for a responsive ``size``.

    Returns:
        A mapping of every :class:`~tempest_core.style.ComponentState` to its
        resolved ``Style``.

    Raises:
        ValueError: If ``color_scheme`` is unknown or the ``size`` map is
            malformed.
    """
    return {
        state: resolve_slider_variant(
            size=size,
            color_scheme=color_scheme,
            theme=theme,
            state=state,
            platform_dark_mode=platform_dark_mode,
            media=media,
        )
        for state in ComponentState
    }


# --------------------------------------------------------------------------- #
# H3 — surface family (card / surface / panel)
# --------------------------------------------------------------------------- #


#: The color a Material 3 elevation shadow is painted in — opaque black at a low
#: alpha (M3 ambient/key shadows are a soft, near-black umbra). Renderers map the
#: resulting :class:`~tempest_core.style.Shadow` to native elevation (Compose
#: ``Modifier.shadow`` / Qt ``QGraphicsDropShadowEffect``).
ELEVATION_SHADOW_COLOR: Color = Color(r=0, g=0, b=0, a=0.30)

#: Maps a Material 3 elevation level (0-5) to the ``(blur, offset_y)`` of the
#: :class:`~tempest_core.style.Shadow` that realizes it (D1: elevation is a
#: ``Shadow`` mapped from the level, **not** a new ``Style`` field). Level ``0``
#: emits no shadow; higher levels grow the blur and the downward offset, tracking
#: the M3 elevation dp scale (0/1/3/6/8/12 dp).
_ELEVATION_SHADOW: dict[int, tuple[float, float]] = {
    0: (0.0, 0.0),
    1: (3.0, 1.0),
    2: (6.0, 2.0),
    3: (8.0, 4.0),
    4: (10.0, 6.0),
    5: (12.0, 8.0),
}

#: The default elevation level per surface variant. ``elevated`` raises to level 1
#: by default; ``filled``/``outlined`` are flush (level 0). An explicit
#: ``elevation`` argument overrides this.
_SURFACE_DEFAULT_ELEVATION: dict[CardVariant, int] = {
    CardVariant.ELEVATED: 1,
    CardVariant.FILLED: 0,
    CardVariant.OUTLINED: 0,
}


def _elevation_shadow(level: int) -> Shadow | None:
    """Build the :class:`~tempest_core.style.Shadow` for an M3 elevation level.

    Realizes D1: an elevation level is mapped to a ``Shadow`` (blur + downward
    offset in :data:`ELEVATION_SHADOW_COLOR`) rather than a new ``Style`` field.
    Level ``0`` casts no shadow and returns ``None`` so the resolved style leaves
    ``shadow`` unset.

    Args:
        level: The Material 3 elevation level, 0-5.

    Returns:
        The shadow for that level, or ``None`` for level ``0`` (no shadow).

    Raises:
        ValueError: If ``level`` is outside the 0-5 range.
    """
    if level not in _ELEVATION_SHADOW:
        raise ValueError(f"unknown elevation level: {level!r}; expected an integer 0-5")
    if level == 0:
        return None
    blur, offset_y = _ELEVATION_SHADOW[level]
    return Shadow(color=ELEVATION_SHADOW_COLOR, blur=blur, offset_y=offset_y)


def _surface_colors(
    *,
    color_scheme: str,
    scheme: ColorScheme,
) -> tuple[Color, Color]:
    """Resolve the ``(background, content)`` colors for a surface.

    A ``"neutral"`` surface uses the plain surface roles (``SURFACE`` /
    ``ON_SURFACE``); a tinted ``color_scheme`` uses the tonal ``*_container`` role
    as the fill and its legible ``on_*_container`` role as the content (D2).

    Args:
        color_scheme: A validated color-scheme name.
        scheme: The resolved :class:`~tempest_core.tokens.ColorScheme`.

    Returns:
        The ``(background, content)`` colors for the surface.
    """
    if color_scheme == "neutral":
        return scheme.role(ColorRole.SURFACE), scheme.role(ColorRole.ON_SURFACE)
    # Tinted container surface — the third element of ``_scheme_roles`` is the
    # ``*_container`` role; its matching ``on_*_container`` is the content.
    _role, _on_role, container = _scheme_roles(color_scheme)
    on_container = _CONTAINER_ON_ROLE[container]
    return scheme.role(container), scheme.role(on_container)


#: Maps a ``*_container`` role to its legible ``on_*_container`` content role, so a
#: tinted surface pairs the container fill with the right foreground (WCAG-AA by
#: construction in the M3 tonal palette).
_CONTAINER_ON_ROLE: dict[ColorRole, ColorRole] = {
    ColorRole.PRIMARY_CONTAINER: ColorRole.ON_PRIMARY_CONTAINER,
    ColorRole.SECONDARY_CONTAINER: ColorRole.ON_SECONDARY_CONTAINER,
    ColorRole.TERTIARY_CONTAINER: ColorRole.ON_TERTIARY_CONTAINER,
    ColorRole.ERROR_CONTAINER: ColorRole.ON_ERROR_CONTAINER,
}


def resolve_surface_variant(
    *,
    variant: CardVariant,
    color_scheme: str = "neutral",
    theme: Theme,
    elevation: int | None = None,
    padding_step: str = "md",
    radius_step: str = "md",
    platform_dark_mode: bool = False,
    media: MediaQueryData | None = None,
) -> Style:
    """Resolve a surface/card's Chakra-style props into a Material 3 ``Style``.

    The H3 sibling of :func:`resolve_variant` for the **surface family** (card,
    surface, panel, accordion header). A surface is **non-interactive** — there is
    no ``state`` parameter and no per-state table (D5): it simply chooses how the
    box is filled and whether it carries an elevation shadow (``elevated``), a
    tonal fill (``filled``) or a hairline outline (``outlined``). Every treatment
    paints onto **existing** :class:`~tempest_core.style.Style` fields, so no new
    field is introduced (D1): elevation is realized as a
    :class:`~tempest_core.style.Shadow` mapped from the M3 level, never an
    ``elevation`` style field.

    The ``color_scheme`` tints the surface (D2): ``"neutral"`` uses the plain
    ``SURFACE`` / ``ON_SURFACE`` roles; a role family (``"primary"``, …) uses the
    tonal ``*_container`` role as the background and its ``on_*_container`` role as
    the content. Padding and radius come from the spacing/shape scales via the
    ``padding_step`` / ``radius_step`` token-step names (D6). Pure and
    deterministic, like every resolver.

    Args:
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with — one of
            :data:`VALID_COLOR_SCHEMES` (default ``"neutral"``).
        theme: The theme whose tokens supply colors, spacing, shape and elevation.
        elevation: An explicit Material 3 elevation level (0-5) overriding the
            variant default; ``None`` uses the per-variant default (``elevated``
            → level 1, ``filled``/``outlined`` → level 0).
        padding_step: The spacing-scale step name for the surface padding (default
            ``"md"``).
        radius_step: The shape-scale step name for the surface corner radius
            (default ``"md"``).
        platform_dark_mode: The OS dark-mode flag, used to resolve the scheme.
        media: The current viewport snapshot (accepted for signature parity with
            the other resolvers; unused here as a surface has no responsive size).

    Returns:
        The resolved, frozen ``Style`` for the requested surface combination.

    Raises:
        ValueError: If ``color_scheme`` is unknown or ``elevation`` is outside
            the 0-5 range.
    """
    if color_scheme not in VALID_COLOR_SCHEMES:
        raise ValueError(
            f"unknown color_scheme: {color_scheme!r}; "
            f"expected one of {sorted(VALID_COLOR_SCHEMES)}"
        )

    scheme = theme.scheme(platform_dark_mode=platform_dark_mode)
    background, content = _surface_colors(color_scheme=color_scheme, scheme=scheme)
    outline = scheme.role(ColorRole.OUTLINE)
    padding = Edge.all(theme.space(padding_step))
    radius = theme.radius(radius_step)

    level = elevation if elevation is not None else _SURFACE_DEFAULT_ELEVATION[variant]

    if variant is CardVariant.ELEVATED:
        shadow = _elevation_shadow(level)
        return Style(
            background=background,
            color=content,
            radius=radius,
            padding=padding,
            shadow=shadow,
        )
    if variant is CardVariant.FILLED:
        # FILLED is a flat tonal fill: SURFACE_VARIANT for neutral, the tinted
        # container otherwise. Elevation may still be requested explicitly.
        if color_scheme == "neutral":
            background = scheme.role(ColorRole.SURFACE_VARIANT)
            content = scheme.role(ColorRole.ON_SURFACE)
        return Style(
            background=background,
            color=content,
            radius=radius,
            padding=padding,
            shadow=_elevation_shadow(level),
        )
    # OUTLINED — a hairline OUTLINE border, no shadow by default.
    return Style(
        background=background,
        color=content,
        border=Border(width=1.0, color=outline),
        radius=radius,
        padding=padding,
        shadow=_elevation_shadow(level),
    )
