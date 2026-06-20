"""Disclosure components: ``Accordion`` (controlled expand/collapse section).

The ``open`` flag is controlled (lives in app state), toggled from the header
``on_toggle`` — mirroring ``Drawer``. No overlay needed: an open accordion simply
renders its body below the header.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import CardVariant, Edge, FontWeight, Style
from tempest_core.theme import Theme
from tempest_core.variants import merge_styles, resolve_surface_variant
from tempest_core.widgets import Button, Column, Component, Widget

__all__ = ["Accordion"]


def _no_widgets() -> list[Widget]:
    """Provide a fresh, typed empty widget list for default factories.

    Returns:
        A new empty list of widgets.
    """
    return []


class Accordion(Component):
    """A titled section whose body shows only when ``open``.

    Themed (Trilho H3): the header is styled through
    :func:`~tempest_core.variants.resolve_surface_variant` (a filled or outlined
    Material 3 surface) and the gaps/padding come from the theme's spacing scale.
    The ``open`` flag is controlled (lives in app state), toggled from the header
    ``on_toggle``.

    Attributes:
        title: The header text.
        open: Whether the body is expanded.
        children: The widgets revealed when open.
        on_toggle: Called when the header is tapped (flip ``open`` in state).
        variant: The surface treatment for the header (filled / outlined /
            elevated).
        color_scheme: The Material 3 role family to tint the header with.
        theme: The design-system theme whose tokens resolve the header surface.
    """

    title: str = Field(default="", description="The header text.")
    open: bool = Field(default=False, description="Whether the body is expanded.")
    children: list[Widget] = Field(
        description="The widgets revealed when open.", default_factory=_no_widgets
    )
    on_toggle: Callable[[], Any] = Field(
        description="Called when the header is tapped (flip ``open`` in state)."
    )
    variant: CardVariant = Field(
        default=CardVariant.FILLED,
        description="The surface treatment for the header (filled / outlined).",
    )
    color_scheme: str = Field(
        default="neutral", description="The Material 3 role family to tint with."
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the header surface.",
    )

    def render(self) -> Widget:
        """Lower the accordion into a primitive column.

        Returns:
            A ``Column`` of the header button and, when open, the body widgets.
        """
        marker = "▾" if self.open else "▸"
        header_surface = resolve_surface_variant(
            variant=self.variant,
            color_scheme=self.color_scheme,
            theme=self.theme,
            padding_step="sm",
            radius_step="sm",
        )
        header_style = merge_styles(header_surface, Style(font_weight=FontWeight.BOLD))
        header = Button(
            label=f"{marker}  {self.title}",
            on_click=self.on_toggle,
            key="accordion-header",
            style=header_style,
        )
        body: list[Widget] = []
        if self.open:
            body.append(
                Column(
                    style=Style(
                        gap=self.theme.space("sm"),
                        padding=Edge.all(self.theme.space("md")),
                    ),
                    children=self.children,
                    key="accordion-body",
                )
            )
        default = Style(gap=self.theme.space("xs"))
        return Column(
            key=self.key or "accordion",
            style=merge_style(default, self.style),
            children=[header, *body],
        )
