"""Menu components: ``Burger`` (menu button) and ``Drawer`` (lateral panel).

Both lower to primitives. ``Drawer`` is *controlled*: its ``open`` flag lives in
app state (toggle it from a ``Burger``'s ``on_click``), mirroring every other
component. Because the layout model is flex-only (no stacking/overlay), an open
drawer renders as a lateral panel rather than a floating overlay with a scrim;
true overlay is a renderer follow-up.

Themed (Trilho H5): ``Burger`` lowers to an :class:`~tempest_core.widgets.IconButton`
(the curated :data:`~tempest_core.icons.Icons.MENU` glyph, ``GHOST`` variant), so
it reuses the H1 :func:`~tempest_core.variants.resolve_variant` resolver and the
icon system; ``Drawer`` resolves its panel surface from the Chakra-style
``variant`` / ``color_scheme`` / ``elevation`` props via
:func:`~tempest_core.variants.resolve_surface_variant`. Every existing call site
still works — the H5 props are additive with backward-compatible defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.icons import Icons
from tempest_core.style import CardVariant, Edge, Size, Style, Variant
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.variants import ResponsiveSize, merge_styles, resolve_surface_variant
from tempest_core.widgets import Column, Component, Container, IconButton, Widget

__all__ = ["Burger", "Drawer"]


def _no_widgets() -> list[Widget]:
    """Provide a fresh, typed empty widget list for default factories.

    Returns:
        A new empty list of widgets.
    """
    return []


class Burger(Component):
    """A hamburger menu button.

    Themed (Trilho H5): lowers to an :class:`~tempest_core.widgets.IconButton`
    showing the curated :data:`~tempest_core.icons.Icons.MENU` glyph in the
    ``GHOST`` variant, so it reuses the H1 variant resolver and the icon system
    (a real line icon, not a literal glyph). The legacy ``glyph`` prop is a
    **deprecated** backward-compatibility fallback: when set to a non-default
    value it is carried as the accessible label, but the icon is always the
    Material ``menu`` glyph.

    Attributes:
        on_click: Invoked when the button is tapped (e.g. to toggle a ``Drawer``).
        variant: The visual treatment (solid/outline/ghost/link); defaults to
            ``GHOST``.
        color_scheme: The Material 3 role family to paint with.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        glyph: Deprecated. The icon character that previous versions rendered;
            kept only for backward-compatibility. The button now always shows the
            Material ``menu`` icon — set ``style`` to customise.
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
    """

    default_key: ClassVar[str] = "burger"

    on_click: Callable[[], Any] = Field(
        description="Invoked when the button is tapped (e.g. to toggle a ``Drawer``)."
    )
    variant: Variant = Field(
        default=Variant.GHOST,
        description="The visual treatment (solid/outline/ghost/link).",
    )
    color_scheme: str = Field(
        default="neutral", description="The Material 3 role family to paint with."
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    glyph: str = Field(
        default="☰",
        description="Deprecated backward-compat fallback; the button always shows the "
        "Material ``menu`` icon.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def render(self) -> Widget:
        """Lower the burger into a primitive icon button.

        Returns:
            An :class:`~tempest_core.widgets.IconButton` showing the menu glyph.
        """
        return IconButton(
            icon=Icons.MENU,
            on_click=self.on_click,
            variant=self.variant,
            color_scheme=self.color_scheme,
            size=self.size,
            label="menu",
            theme=self.theme,
            media=self.media,
            key=self.base_key,
            style=self.style,
        )


class Drawer(Component):
    """A controlled lateral panel that shows its children when ``open``.

    Themed (Trilho H5): when open, the panel surface is resolved from ``variant``
    / ``color_scheme`` / ``elevation`` via
    :func:`~tempest_core.variants.resolve_surface_variant`, mirroring a card; the
    width and the open/closed behavior are unchanged. Backward-compatible:
    ``Drawer(open=…, children=…)`` is an elevated neutral panel.

    Attributes:
        open: Whether the drawer is expanded; when ``False`` it collapses to an
            empty box.
        children: The widgets stacked inside the open drawer.
        width: The panel width in logical pixels when open.
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        theme: The design-system theme whose tokens resolve the panel surface.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    default_key: ClassVar[str] = "drawer"

    open: bool = Field(
        default=False,
        description="Whether the drawer is expanded; when ``False`` it collapses to an "
        "empty box.",
    )
    children: list[Widget] = Field(
        description="The widgets stacked inside the open drawer.",
        default_factory=_no_widgets,
    )
    width: float = Field(
        default=260.0, description="The panel width in logical pixels when open."
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
        description="The design-system theme whose tokens resolve the panel surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; forwarded).",
    )

    def render(self) -> Widget:
        """Lower the drawer into a primitive panel or an empty box.

        Returns:
            A styled ``Column`` panel when open, otherwise an empty ``Container``.
        """
        if not self.open:
            return Container(key=self.base_key)
        surface = resolve_surface_variant(
            variant=self.variant,
            color_scheme=self.color_scheme,
            theme=self.theme,
            elevation=self.elevation,
            padding_step="none",
            media=self.media,
        )
        default = merge_styles(
            surface,
            Style(width=self.width, padding=Edge.all(16.0), gap=10.0),
        )
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=self.children,
        )
