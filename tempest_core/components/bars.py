"""Bar components: ``AppBar``, ``Header``, ``Footer`` and ``CollapsingAppBar``.

Each is a :class:`Component` that lowers to a primitive ``Row``/``Column`` tree,
so they render identically in the Qt simulator and on the Compose device.

With Trilho H5 these bars are **themed via the design-system tokens**: ``AppBar``
/ ``Footer`` / ``CollapsingAppBar`` resolve their bar surface (background +
elevation shadow + tinted container) from the Chakra-style ``variant`` /
``color_scheme`` / ``elevation`` props through
:func:`~tempest_core.variants.resolve_surface_variant`; the title/content color
is the resolved surface content. ``Header`` reads its colors and spacing straight
from the :class:`~tempest_core.theme.Theme` tokens. Every existing call site
(``AppBar(title=…)``, ``Footer(children=…)``, an explicit ``style=``) still works
— the H5 props are additive with backward-compatible defaults.
"""

from __future__ import annotations

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import (
    AlignItems,
    CardVariant,
    Color,
    Edge,
    FontWeight,
    JustifyContent,
    Style,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import merge_styles, resolve_surface_variant
from tempest_core.widgets import Column, Component, Container, Row, Text, Widget

__all__ = ["AppBar", "Header", "Footer", "CollapsingAppBar"]


def _no_widgets() -> list[Widget]:
    """Provide a fresh, typed empty widget list for default factories.

    Returns:
        A new empty list of widgets.
    """
    return []


def _bar_surface(
    *,
    variant: CardVariant,
    color_scheme: str,
    elevation: int | None,
    theme: Theme,
    media: MediaQueryData | None,
) -> Style:
    """Resolve a bar's surface style (background + elevation + content color).

    Reuses the H3 :func:`~tempest_core.variants.resolve_surface_variant` resolver
    so a bar carries the same Material 3 background / elevation shadow / tinted
    container treatment as a card, with **no** inner padding of its own (the bar
    applies its own padding). The resolver's ``color`` is the legible surface
    content color the bar's title/labels inherit.

    Args:
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5), or ``None`` for the
            per-variant default.
        theme: The design-system theme whose tokens resolve the surface.
        media: Optional viewport snapshot (forwarded for parity).

    Returns:
        The resolved surface ``Style`` (no inner padding).
    """
    return resolve_surface_variant(
        variant=variant,
        color_scheme=color_scheme,
        theme=theme,
        elevation=elevation,
        padding_step="none",
        media=media,
    )


class AppBar(Component):
    """A top application bar: optional leading widget, title and trailing actions.

    Themed (Trilho H5): the bar surface is resolved from ``variant`` /
    ``color_scheme`` / ``elevation`` via
    :func:`~tempest_core.variants.resolve_surface_variant` (a Material 3 elevated /
    filled / outlined bar), and the title color is the resolved surface content
    color. An explicit ``style`` is merged on top of the resolved surface (its set
    fields win). Backward-compatible: ``AppBar(title=…)`` is an elevated neutral
    bar matching the previous dark-surface look.

    Attributes:
        title: The bar's title text.
        leading: An optional widget shown before the title (e.g. a menu or back
            button); omitted when ``None``.
        actions: Trailing action widgets laid out at the end of the bar.
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        theme: The design-system theme whose tokens resolve the bar surface.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    title: str = Field(default="", description="The bar's title text.")
    leading: Widget | None = Field(
        default=None,
        description="An optional widget shown before the title (e.g. a menu or back "
        "button); omitted when ``None``.",
    )
    actions: list[Widget] = Field(
        description="Trailing action widgets laid out at the end of the bar.",
        default_factory=_no_widgets,
    )
    variant: CardVariant = Field(
        default=CardVariant.ELEVATED,
        description="The surface treatment (elevated / filled / outlined).",
    )
    color_scheme: str = Field(
        default="neutral", description="The Material 3 role family to tint with."
    )
    elevation: int | None = Field(
        default=None,
        description="An explicit M3 elevation level (0-5) overriding the default.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the bar surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; forwarded).",
    )

    def render(self) -> Widget:
        """Lower the app bar into a horizontal primitive row.

        Returns:
            A ``Row`` with the leading widget, a growing title and the actions,
            carrying the resolved surface style.
        """
        surface = _bar_surface(
            variant=self.variant,
            color_scheme=self.color_scheme,
            elevation=self.elevation,
            theme=self.theme,
            media=self.media,
        )
        content = surface.color or self.theme.color(ColorRole.ON_SURFACE)
        children: list[Widget] = []
        if self.leading is not None:
            children.append(self.leading)
        children.append(
            Text(
                content=self.title,
                style=Style(
                    grow=1.0,
                    font_size=20.0,
                    font_weight=FontWeight.BOLD,
                    color=content,
                ),
                key="appbar-title",
            )
        )
        if self.actions:
            children.append(
                Row(style=Style(gap=8.0), children=self.actions, key="appbar-actions")
            )
        default = merge_styles(
            surface,
            Style(
                padding=Edge.symmetric(vertical=14.0, horizontal=16.0),
                gap=12.0,
                align=AlignItems.CENTER,
            ),
        )
        return Row(
            key=self.key or "appbar",
            style=merge_style(default, self.style),
            children=children,
        )


class Header(Component):
    """A page header band: a title with an optional subtitle.

    Themed (Trilho H5, tokens-only): the band fills with the theme's
    ``SURFACE_VARIANT`` role, the title uses ``ON_SURFACE`` and the subtitle uses
    ``ON_SURFACE_VARIANT``, with spacing/typography read from the theme tokens. An
    optional ``color_scheme`` tints the title with the role color (e.g. a section
    header). There is no surface ``variant`` — a header is a flat band, not an
    elevated surface. Backward-compatible: ``Header(title=…)`` is a neutral band.

    Attributes:
        title: The header's primary line.
        subtitle: An optional secondary line shown muted under the title.
        color_scheme: Optional Material 3 role family tinting the title; ``None``
            keeps the neutral ``ON_SURFACE`` title.
        theme: The design-system theme whose tokens supply colors and spacing.
    """

    title: str = Field(default="", description="The header's primary line.")
    subtitle: str | None = Field(
        default=None,
        description="An optional secondary line shown muted under the title.",
    )
    color_scheme: str | None = Field(
        default=None,
        description="Optional Material 3 role family tinting the title.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply colors and spacing.",
    )

    def render(self) -> Widget:
        """Lower the header into a stacked primitive column.

        Returns:
            A ``Column`` with the title and, when set, the subtitle.
        """
        surface_variant = self.theme.color(ColorRole.SURFACE_VARIANT)
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        title_color = (
            self.theme.color(self.color_scheme)
            if self.color_scheme is not None and self.color_scheme != "neutral"
            else on_surface
        )
        title_role = self.theme.typography("headline_small")
        subtitle_role = self.theme.typography("body_medium")
        children: list[Widget] = [
            Text(
                content=self.title,
                style=Style(
                    font_size=title_role.font_size,
                    font_weight=FontWeight.BOLD,
                    color=title_color,
                ),
                key="header-title",
            )
        ]
        if self.subtitle is not None:
            children.append(
                Text(
                    content=self.subtitle,
                    style=Style(
                        font_size=subtitle_role.font_size, color=on_surface_variant
                    ),
                    key="header-subtitle",
                )
            )
        default = Style(
            padding=Edge.all(self.theme.space("lg")),
            gap=self.theme.space("xs"),
            background=surface_variant,
        )
        return Column(
            key=self.key or "header",
            style=merge_style(default, self.style),
            children=children,
        )


class Footer(Component):
    """A bottom bar holding arbitrary, centered content.

    Themed (Trilho H5): the footer surface is resolved from ``variant`` /
    ``color_scheme`` / ``elevation`` via
    :func:`~tempest_core.variants.resolve_surface_variant`, mirroring
    :class:`AppBar`. Backward-compatible: ``Footer(children=…)`` is an elevated
    neutral bar.

    Attributes:
        children: The widgets laid out in the footer (e.g. links or labels).
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        theme: The design-system theme whose tokens resolve the bar surface.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    children: list[Widget] = Field(
        description="The widgets laid out in the footer (e.g. links or labels).",
        default_factory=_no_widgets,
    )
    variant: CardVariant = Field(
        default=CardVariant.ELEVATED,
        description="The surface treatment (elevated / filled / outlined).",
    )
    color_scheme: str = Field(
        default="neutral", description="The Material 3 role family to tint with."
    )
    elevation: int | None = Field(
        default=None,
        description="An explicit M3 elevation level (0-5) overriding the default.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the bar surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; forwarded).",
    )

    def render(self) -> Widget:
        """Lower the footer into a centered primitive row.

        Returns:
            A ``Row`` containing the footer's children, carrying the resolved
            surface style.
        """
        surface = _bar_surface(
            variant=self.variant,
            color_scheme=self.color_scheme,
            elevation=self.elevation,
            theme=self.theme,
            media=self.media,
        )
        default = merge_styles(
            surface,
            Style(
                padding=Edge.symmetric(vertical=12.0, horizontal=16.0),
                gap=12.0,
                align=AlignItems.CENTER,
            ),
        )
        return Row(
            key=self.key or "footer",
            style=merge_style(default, self.style),
            children=self.children,
        )


class CollapsingAppBar(Component):
    """A sliver-style app bar that shrinks as the user scrolls the content down.

    Coordinates with a scrollable container's ``on_scroll`` handler entirely
    through state: the application reads the current scroll offset from the
    list's :class:`~tempestroid.ScrollEvent`, stores it, and passes it back as
    :attr:`scroll_offset`. The component derives a height that eases from
    :attr:`expanded_height` (offset ``0``) down to :attr:`collapsed_height` (once
    the offset exceeds the collapse distance) and renders accordingly — so the
    reconciler simply diffs the derived ``Style.height`` as an ordinary prop,
    needing no new IR, no new event and no renderer change. The title's font
    shrinks in step with the bar.

    Themed (Trilho H5): the bar surface is resolved from ``variant`` /
    ``color_scheme`` / ``elevation`` via
    :func:`~tempest_core.variants.resolve_surface_variant` exactly like
    :class:`AppBar`; the height/font collapse derivation is unchanged pure Python.
    The legacy ``background`` prop still wins when set (backward-compatible).

    Attributes:
        title: The bar's title text.
        expanded_height: The bar height at the top of the scroll (offset ``0``).
        collapsed_height: The minimum bar height once fully collapsed.
        scroll_offset: The current scroll offset (logical pixels) driven by the
            application from the scrollable's ``on_scroll`` handler.
        background: An optional background color overriding the resolved surface
            fill (legacy escape hatch).
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        theme: The design-system theme whose tokens resolve the bar surface.
        media: Optional viewport snapshot (accepted for parity; forwarded).
        style: An optional style overlaid on the bar's derived default.
    """

    title: str = Field(default="", description="The bar's title text.")
    expanded_height: float = Field(
        default=200.0,
        description="The bar height at the top of the scroll (offset ``0``).",
    )
    collapsed_height: float = Field(
        default=56.0, description="The minimum bar height once fully collapsed."
    )
    scroll_offset: float = Field(
        default=0.0,
        description="The current scroll offset (logical pixels) driven by the "
        "application from the scrollable's ``on_scroll`` handler.",
    )
    background: Color | None = Field(
        default=None,
        description="An optional background color overriding the resolved surface "
        "fill (legacy escape hatch).",
    )
    variant: CardVariant = Field(
        default=CardVariant.ELEVATED,
        description="The surface treatment (elevated / filled / outlined).",
    )
    color_scheme: str = Field(
        default="neutral", description="The Material 3 role family to tint with."
    )
    elevation: int | None = Field(
        default=None,
        description="An explicit M3 elevation level (0-5) overriding the default.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the bar surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; forwarded).",
    )
    style: Style | None = None

    def _height(self) -> float:
        """Derive the current bar height from the scroll offset.

        The bar collapses linearly over a distance equal to the difference
        between the expanded and collapsed heights, clamped to that band.

        Returns:
            The current bar height in logical pixels.
        """
        span = max(0.0, self.expanded_height - self.collapsed_height)
        consumed = min(max(self.scroll_offset, 0.0), span)
        return self.expanded_height - consumed

    def render(self) -> Widget:
        """Lower the collapsing app bar into a primitive container with a title.

        Returns:
            A bottom-aligned ``Container`` whose height tracks the scroll offset,
            wrapping the title (whose size eases between expanded and collapsed).
        """
        height = self._height()
        span = max(1.0, self.expanded_height - self.collapsed_height)
        progress = (self.expanded_height - height) / span  # 0 expanded .. 1 collapsed
        font_size = 28.0 - 8.0 * progress  # 28 expanded -> 20 collapsed
        surface = _bar_surface(
            variant=self.variant,
            color_scheme=self.color_scheme,
            elevation=self.elevation,
            theme=self.theme,
            media=self.media,
        )
        content = surface.color or self.theme.color(ColorRole.ON_SURFACE)
        default = merge_styles(
            surface,
            Style(
                height=height,
                padding=Edge.symmetric(vertical=10.0, horizontal=16.0),
                justify=JustifyContent.END,
            ),
        )
        if self.background is not None:
            default = merge_styles(default, Style(background=self.background))
        return Container(
            key=self.key or "collapsing-app-bar",
            style=merge_style(default, self.style),
            child=Column(
                style=Style(justify=JustifyContent.END, align=AlignItems.START),
                children=[
                    Text(
                        content=self.title,
                        style=Style(
                            font_size=font_size,
                            font_weight=FontWeight.BOLD,
                            color=content,
                        ),
                        key="collapsing-title",
                    )
                ],
            ),
        )
