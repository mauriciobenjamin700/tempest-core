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
    Color,
    ComponentState,
    Edge,
    Size,
    Style,
    TextDecoration,
    Variant,
)
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.tokens import ColorRole

__all__ = [
    "VALID_COLOR_SCHEMES",
    "MIN_TOUCH_TARGET",
    "HOVER_OPACITY",
    "PRESSED_OPACITY",
    "FOCUS_OPACITY",
    "DISABLED_CONTENT_OPACITY",
    "DISABLED_CONTAINER_OPACITY",
    "ResponsiveSize",
    "merge_styles",
    "resolve_size",
    "resolve_variant",
    "resolve_variant_states",
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
    # DISABLED: drop content + (filled) container to the M3 disabled opacities;
    # keep contrast structure but visibly muted.
    disabled_content = base.color
    overrides = Style(opacity=DISABLED_CONTENT_OPACITY)
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
