"""Content components: ``Card``, ``ListTile``, ``Avatar`` and ``Divider``.

Classic presentational building blocks that lower to primitives. With Trilho H3
these are **themed via the design-system tokens**: ``Card`` resolves its surface
treatment from the Chakra-style ``variant`` / ``color_scheme`` / ``elevation``
props (a Material 3 elevated/filled/outlined surface) through
:func:`~tempest_core.variants.resolve_surface_variant`; ``Divider`` / ``ListTile``
read their colors and spacing from the :class:`~tempest_core.theme.Theme` tokens
rather than hard-coded hexes. Every existing call site (``Card(children=…)``,
``Divider(...)``, ``ListTile(title=…)``) still works: the H3 props are additive
with backward-compatible defaults.

Because tap handling only exists on ``Button`` in the primitive set, ``ListTile``
is presentational (no row-level ``on_click``); place a ``Button`` in its
``trailing`` slot for actions.
"""

from __future__ import annotations

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.components.surface import Surface
from tempest_core.style import (
    AlignItems,
    CardVariant,
    Color,
    Edge,
    FontWeight,
    Style,
    TextAlign,
)
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.tokens import ColorRole
from tempest_core.widgets import Column, Component, Container, Row, Text, Widget

__all__ = ["Card", "ListTile", "Avatar", "Divider"]

#: Maps a ``color_scheme`` family to its ``(container, on_container)`` color roles,
#: the WCAG-AA-safe tonal pairing the :class:`Avatar` fills with. ``"neutral"``
#: uses the surface-variant roles.
_AVATAR_ROLES: dict[str, tuple[ColorRole, ColorRole]] = {
    "primary": (ColorRole.PRIMARY_CONTAINER, ColorRole.ON_PRIMARY_CONTAINER),
    "secondary": (ColorRole.SECONDARY_CONTAINER, ColorRole.ON_SECONDARY_CONTAINER),
    "tertiary": (ColorRole.TERTIARY_CONTAINER, ColorRole.ON_TERTIARY_CONTAINER),
    "error": (ColorRole.ERROR_CONTAINER, ColorRole.ON_ERROR_CONTAINER),
    "success": (ColorRole.SUCCESS_CONTAINER, ColorRole.ON_SUCCESS_CONTAINER),
    "warning": (ColorRole.WARNING_CONTAINER, ColorRole.ON_WARNING_CONTAINER),
    "info": (ColorRole.INFO_CONTAINER, ColorRole.ON_INFO_CONTAINER),
    "neutral": (ColorRole.SURFACE_VARIANT, ColorRole.ON_SURFACE),
}


def _avatar_colors(color_scheme: str, theme: Theme) -> tuple[Color, Color]:
    """Resolve the ``(background, content)`` colors for an avatar circle.

    Args:
        color_scheme: The Material 3 role family to tint with.
        theme: The theme whose scheme resolves the roles.

    Returns:
        The tonal ``*_container`` fill and its legible ``on_*_container`` content,
        falling back to the primary container for an unknown scheme.
    """
    container, on_container = _AVATAR_ROLES.get(color_scheme, _AVATAR_ROLES["primary"])
    return theme.color(container), theme.color(on_container)


def _no_widgets() -> list[Widget]:
    """Provide a fresh, typed empty widget list for default factories.

    Returns:
        A new empty list of widgets.
    """
    return []


class Card(Component):
    """A themed surface grouping a stack of children (Material 3 card).

    Builds on :class:`~tempest_core.components.Surface`: it resolves the surface
    treatment from ``variant`` / ``color_scheme`` / ``elevation`` against the
    ``theme`` (via :func:`~tempest_core.variants.resolve_surface_variant`), adds
    its own padding, and stacks the children in a ``Column``. ``Card`` is exactly
    ``Surface`` + padding + ``Column``. Backward-compatible: a no-arg
    ``Card(children=…)`` produces an elevated, neutral card; an explicit ``style``
    is merged on top of the resolved surface (its set fields win).

    Attributes:
        children: The widgets stacked vertically inside the card.
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        padding_step: The spacing-scale step name for the inner padding.
        radius_step: The shape-scale step name for the corner radius.
        gap_step: The spacing-scale step name for the gap between children.
        theme: The design-system theme whose tokens resolve the surface.
        media: Optional viewport snapshot (accepted for parity; unused).
    """

    children: list[Widget] = Field(
        description="The widgets stacked vertically inside the card.",
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
    padding_step: str = Field(
        default="md", description="The spacing-scale step name for the inner padding."
    )
    radius_step: str = Field(
        default="md", description="The shape-scale step name for the corner radius."
    )
    gap_step: str = Field(
        default="sm",
        description="The spacing-scale step name for the gap between children.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; unused).",
    )

    def render(self) -> Widget:
        """Lower the card into a themed, padded surface wrapping a column.

        Returns:
            A ``Surface`` (the resolved variant style) wrapping a padded
            ``Column`` of the children.
        """
        padding = self.theme.space(self.padding_step)
        gap = self.theme.space(self.gap_step)
        inner = Container(
            key="card-body",
            style=Style(padding=Edge.all(padding)),
            child=Column(style=Style(gap=gap), children=self.children, key="card-col"),
        )
        return Surface(
            key=self.key or "card",
            variant=self.variant,
            color_scheme=self.color_scheme,
            elevation=self.elevation,
            radius_step=self.radius_step,
            theme=self.theme,
            media=self.media,
            style=self.style,
            child=inner,
        )


class ListTile(Component):
    """A single list row: optional leading/trailing widgets around a title block.

    Themed (Trilho H3): the title uses ``ON_SURFACE``, the subtitle uses
    ``ON_SURFACE_VARIANT``, and the gaps/padding come from the theme's spacing
    scale rather than fixed pixels. An optional ``color_scheme`` tints the title
    with the role color (e.g. a highlighted/active row). The accessibility surface
    (``semantics``) is preserved on the row.

    Attributes:
        title: The row's primary text.
        subtitle: An optional secondary line shown muted under the title.
        leading: An optional widget shown before the text (e.g. an ``Avatar``).
        trailing: An optional widget shown after the text (e.g. a ``Button``).
        color_scheme: Optional Material 3 role family tinting the title; ``None``
            keeps the neutral ``ON_SURFACE`` title.
        theme: The design-system theme whose tokens supply colors and spacing.
    """

    title: str = Field(default="", description="The row's primary text.")
    subtitle: str | None = Field(
        default=None,
        description="An optional secondary line shown muted under the title.",
    )
    leading: Widget | None = Field(
        default=None,
        description="An optional widget shown before the text (e.g. an ``Avatar``).",
    )
    trailing: Widget | None = Field(
        default=None,
        description="An optional widget shown after the text (e.g. a ``Button``).",
    )
    color_scheme: str | None = Field(
        default=None,
        description="Optional Material 3 role family tinting the title.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens supply colors and spacing.",
    )

    def render(self) -> Widget:
        """Lower the list tile into a primitive row.

        Returns:
            A ``Row`` of the leading widget, the growing title block and the
            trailing widget; ``self.semantics`` is preserved on the row.
        """
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        title_role = self.theme.typography("body_large")
        subtitle_role = self.theme.typography("body_small")
        title_color = (
            self.theme.color(self.color_scheme)
            if self.color_scheme is not None and self.color_scheme != "neutral"
            else on_surface
        )
        text_children: list[Widget] = [
            Text(
                content=self.title,
                style=Style(
                    font_size=title_role.font_size,
                    font_weight=title_role.font_weight,
                    color=title_color,
                ),
                key="tile-title",
            )
        ]
        if self.subtitle is not None:
            text_children.append(
                Text(
                    content=self.subtitle,
                    style=Style(
                        font_size=subtitle_role.font_size, color=on_surface_variant
                    ),
                    key="tile-subtitle",
                )
            )
        children: list[Widget] = []
        if self.leading is not None:
            children.append(self.leading)
        children.append(
            Column(
                style=Style(grow=1.0, gap=self.theme.space("xs")),
                children=text_children,
                key="tile-text",
            )
        )
        if self.trailing is not None:
            children.append(self.trailing)
        default = Style(
            gap=self.theme.space("sm"),
            align=AlignItems.CENTER,
            padding=Edge.symmetric(
                vertical=self.theme.space("sm"), horizontal=self.theme.space("md")
            ),
        )
        return Row(
            key=self.key or "listtile",
            style=merge_style(default, self.style),
            children=children,
            semantics=self.semantics,
        )


class Avatar(Component):
    """A round badge showing short initials, themed via the container roles.

    Themed (Trilho H4): the circle fills with the ``color_scheme``'s tonal
    ``*_container`` role and the initials use its legible ``on_*_container`` role
    (WCAG-AA safe by construction), resolved from the theme rather than a fixed
    hex. Backward-compatible: ``Avatar(initials="MB")`` is a primary-container
    circle.

    Attributes:
        initials: The short text shown inside the circle (e.g. ``"MB"``).
        size: The circle's diameter in logical pixels.
        color_scheme: The Material 3 role family the circle tints with.
        theme: The design-system theme resolving the circle colors.
    """

    initials: str = Field(
        default="",
        description='The short text shown inside the circle (e.g. ``"MB"``).',
    )
    size: float = Field(
        default=40.0, description="The circle's diameter in logical pixels."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the circle tints with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme resolving the circle colors.",
    )

    def render(self) -> Widget:
        """Lower the avatar into a circular container with centered initials.

        Returns:
            A ``Container`` sized to ``size`` wrapping a centered ``Text``.
        """
        background, content = _avatar_colors(self.color_scheme, self.theme)
        default = Style(
            width=self.size,
            height=self.size,
            radius=self.size / 2.0,
            background=background,
            align=AlignItems.CENTER,
        )
        return Container(
            key=self.key or "avatar",
            style=merge_style(default, self.style),
            child=Text(
                content=self.initials,
                style=Style(
                    color=content,
                    font_weight=FontWeight.BOLD,
                    text_align=TextAlign.CENTER,
                ),
                key="avatar-text",
            ),
        )


class Divider(Component):
    """A thin horizontal rule, themed with the Material 3 outline-variant color.

    Themed (Trilho H3): the line color comes from the theme's ``OUTLINE_VARIANT``
    role (or an optional ``color_scheme`` role) rather than a fixed hex, and the
    ``thickness`` accepts a token-step name (resolved against the shape scale) or a
    raw float. Backward-compatible: ``Divider()`` is a 1px outline-variant rule.

    Attributes:
        thickness: The line's height — a token-step name (``"xs"``) or a float in
            logical pixels.
        color_scheme: Optional Material 3 role family to color the rule; ``None``
            uses the neutral ``OUTLINE_VARIANT``.
        theme: The design-system theme whose tokens supply the color and step.
    """

    thickness: float | str = Field(
        default=1.0,
        description='The line\'s height — a spacing-step name (``"xs"``) or a float.',
    )
    color_scheme: str | None = Field(
        default=None,
        description="Optional Material 3 role family to color the rule.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens supply the color and step.",
    )

    def render(self) -> Widget:
        """Lower the divider into a thin, full-width container.

        Returns:
            An empty ``Container`` styled as a line in the resolved color.
        """
        height = (
            self.theme.space(self.thickness)
            if isinstance(self.thickness, str)
            else self.thickness
        )
        color = (
            self.theme.color(self.color_scheme)
            if self.color_scheme is not None and self.color_scheme != "neutral"
            else self.theme.color(ColorRole.OUTLINE_VARIANT)
        )
        default = Style(height=height, background=color)
        return Container(
            key=self.key or "divider",
            style=merge_style(default, self.style),
        )
