"""Selection components: SegmentedControl, RadioGroup, Chip, Tag and Rating.

Single-choice / value pickers built from primitive ``Button`` rows. They lower to
primitives via :meth:`Component.render`, so they work in both renderers and on the
device with no renderer changes. With Trilho H4 these are **themed via the
design-system tokens**: ``SegmentedControl`` resolves its active/inactive segments
through :func:`~tempest_core.variants.resolve_variant` (active = solid, rest =
ghost); ``Chip`` resolves its pill through
:func:`~tempest_core.variants.resolve_badge_variant`; ``Rating`` reads its star
color from the theme. ``Tag`` is a closed, non-selectable :class:`Chip` preset.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import (
    BadgeVariant,
    Color,
    Edge,
    Size,
    Style,
    Variant,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import (
    ResponsiveSize,
    resolve_badge_variant,
    resolve_selection_variant,
    resolve_variant,
)
from tempest_core.widgets import Button, Column, Component, Row, Text, Widget

__all__ = ["SegmentedControl", "RadioGroup", "Chip", "Tag", "Rating"]


def _no_labels() -> list[str]:
    """Provide a fresh, typed empty label list for default factories.

    Returns:
        A new empty list of strings.
    """
    return []


class SegmentedControl(Component):
    """A compact single-choice pill group, themed via the H1 variant resolver.

    Themed (Trilho H4): the active segment resolves to a Material 3 ``solid``
    treatment and the inactive ones to ``ghost`` via
    :func:`~tempest_core.variants.resolve_variant` against the ``theme`` — so dark
    mode and brand color work for free instead of hard-coded hexes.

    Attributes:
        options: The visible segment labels, in order.
        selected: The index of the active segment.
        on_select: Called with the tapped segment's index.
        color_scheme: The Material 3 role family the active segment paints with.
        size: The density size of each segment.
        theme: The design-system theme resolving the segments.
        media: Optional viewport snapshot for a responsive ``size``.
    """

    options: list[str] = Field(
        description="The visible segment labels, in order.", default_factory=_no_labels
    )
    selected: int = Field(default=0, description="The index of the active segment.")
    on_select: Callable[[int], Any] = Field(
        description="Called with the tapped segment's index."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the active segment paints with.",
    )
    size: ResponsiveSize = Field(
        default=Size.SM, description="The density size of each segment."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme resolving the segments.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def _handler(self, index: int) -> Callable[[], None]:
        """Build a zero-argument handler selecting ``index``.

        Args:
            index: The segment index to select.

        Returns:
            A click handler invoking ``on_select`` with ``index``.
        """

        def handler() -> None:
            self.on_select(index)

        return handler

    def render(self) -> Widget:
        """Lower the control into a primitive row of segment buttons.

        Returns:
            A ``Row`` of segment buttons with the active one highlighted.
        """
        surface = self.theme.color(ColorRole.SURFACE_VARIANT)
        default = Style(
            gap=self.theme.space("xs"),
            padding=Edge.all(self.theme.space("xs")),
            radius=self.theme.radius("md"),
            background=surface,
        )
        children: list[Widget] = []
        for index, label in enumerate(self.options):
            active = index == self.selected
            seg = resolve_variant(
                variant=Variant.SOLID if active else Variant.GHOST,
                size=self.size,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            )
            children.append(
                Button(
                    label=label,
                    on_click=self._handler(index),
                    key=f"seg-{index}",
                    style=merge_style(seg, Style(grow=1.0)),
                )
            )
        return Row(
            key=self.key or "segmented",
            style=merge_style(default, self.style),
            children=children,
        )


class RadioGroup(Component):
    """A vertical single-choice list with radio markers, theme-driven colors.

    Each row's marker/text color is resolved from the H2 selection variant
    (:func:`~tempest_core.variants.resolve_selection_variant`) against the
    ``theme`` — the chosen row reads the ``color_scheme`` accent, the rest read
    a muted on-surface tone — so dark mode and brand color work for free. The
    ◉/○ glyphs are unchanged; only the colors become theme-driven.

    Attributes:
        options: The choice labels, in order.
        selected: The index of the chosen option.
        on_select: Called with the tapped option's index.
        size: The density size of each row's marker.
        color_scheme: The Material 3 role family the chosen row's accent paints
            with.
        theme: The design-system theme resolving the row colors.
        media: Optional viewport snapshot for a responsive ``size``.
    """

    options: list[str] = Field(
        description="The choice labels, in order.", default_factory=_no_labels
    )
    selected: int = Field(default=0, description="The index of the chosen option.")
    on_select: Callable[[int], Any] = Field(
        description="Called with the tapped option's index."
    )
    size: ResponsiveSize = Field(
        default=Size.MD, description="The density size of each row's marker."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the chosen row's accent paints with.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme resolving the row colors.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def _handler(self, index: int) -> Callable[[], None]:
        """Build a zero-argument handler selecting ``index``.

        Args:
            index: The option index to select.

        Returns:
            A click handler invoking ``on_select`` with ``index``.
        """

        def handler() -> None:
            self.on_select(index)

        return handler

    def _row_colors(self, *, chosen: bool) -> tuple[Color, Color]:
        """Resolve the (marker/text color, row background) for a radio row.

        Args:
            chosen: Whether this row is the selected option.

        Returns:
            The marker/text color (the accent when chosen, else the muted
            on-surface variant) and the row surface background, from the theme.
        """
        accent_style = resolve_selection_variant(
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            checked=chosen,
            media=self.media,
        )
        accent = accent_style.color
        marker = (
            accent
            if (chosen and accent is not None)
            else self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        )
        surface = self.theme.color(ColorRole.SURFACE)
        return marker, surface

    def render(self) -> Widget:
        """Lower the group into a primitive column of radio buttons.

        Returns:
            A ``Column`` of one button per option, the chosen one marked.
        """
        default = Style(gap=self.theme.space("sm"))
        children: list[Widget] = []
        for index, label in enumerate(self.options):
            chosen = index == self.selected
            marker, surface = self._row_colors(chosen=chosen)
            children.append(
                Button(
                    label=("◉" if chosen else "○") + f"  {label}",
                    on_click=self._handler(index),
                    key=f"radio-{index}",
                    style=Style(
                        padding=Edge.symmetric(vertical=10.0, horizontal=14.0),
                        radius=self.theme.radius("sm"),
                        background=surface,
                        color=marker,
                    ),
                )
            )
        return Column(
            key=self.key or "radiogroup",
            style=merge_style(default, self.style),
            children=children,
        )


class Chip(Component):
    """A small rounded label, optionally selectable, themed via the badge resolver.

    Themed (Trilho H4): the pill treatment comes from
    :func:`~tempest_core.variants.resolve_badge_variant` against the theme — a
    ``solid`` badge when selected, a ``subtle`` badge otherwise. A tappable chip
    (``on_click`` set) lowers to a ``Button`` carrying the resolved badge style;
    a presentational chip lowers to a ``Text`` pill.

    Attributes:
        label: The chip text.
        selected: Whether the chip reads as active (a solid badge vs a subtle one).
        on_click: Optional tap handler; when ``None`` the chip is presentational.
        color_scheme: The Material 3 role family the chip tints with.
        size: The density size of the pill.
        theme: The design-system theme resolving the chip treatment.
        media: Optional viewport snapshot for a responsive ``size``.
    """

    label: str = Field(default="", description="The chip text.")
    selected: bool = Field(
        default=False,
        description="Whether the chip reads as active (solid vs subtle badge).",
    )
    on_click: Callable[[], Any] | None = Field(
        default=None,
        description="Optional tap handler; when ``None`` the chip is presentational.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the chip tints with.",
    )
    size: ResponsiveSize = Field(
        default=Size.MD, description="The density size of the pill."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme resolving the chip treatment.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def render(self) -> Widget:
        """Lower the chip into a primitive button or a static pill.

        Returns:
            A ``Button`` when ``on_click`` is set, otherwise a ``Text`` pill.
        """
        chip_style = resolve_badge_variant(
            variant=BadgeVariant.SOLID if self.selected else BadgeVariant.SUBTLE,
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )
        if self.on_click is not None:
            return Button(
                label=self.label,
                on_click=self.on_click,
                key=self.key or "chip",
                style=merge_style(chip_style, self.style),
            )
        return Text(
            content=self.label,
            key=self.key or "chip",
            style=merge_style(chip_style, self.style),
        )


class Tag(Chip):
    """A closed, non-selectable label — a thin preset of :class:`Chip`.

    A ``Tag`` is exactly a :class:`Chip` fixed to its presentational, low-emphasis
    form: never selectable and never tappable (``selected`` and ``on_click`` are
    not exposed), so it always lowers to a static ``subtle`` badge ``Text`` pill.
    It carries the same theming props (``color_scheme`` / ``size`` / ``theme``) as
    ``Chip`` and reuses :func:`~tempest_core.variants.resolve_badge_variant`. Use it
    for read-only category/status labels where a ``Chip``'s interactivity is wrong.
    """

    selected: bool = Field(
        default=False,
        frozen=True,
        description="A tag is never selected — fixed to the subtle badge.",
    )
    on_click: Callable[[], Any] | None = Field(
        default=None,
        frozen=True,
        description="A tag is never tappable — always a static pill.",
    )


class Rating(Component):
    """A row of stars showing (and optionally setting) a 1-based rating.

    Themed (Trilho H4): the star color reads the ``color_scheme`` role from the
    theme rather than a hard-coded accent, so dark mode and brand color apply.

    Attributes:
        value: The number of filled stars.
        max_stars: The total number of stars shown.
        on_rate: Optional handler called with the tapped star's 1-based value;
            when ``None`` the rating is presentational.
        color_scheme: The Material 3 role family the filled stars paint with.
        theme: The design-system theme resolving the star color.
    """

    value: int = Field(default=0, description="The number of filled stars.")
    max_stars: int = Field(default=5, description="The total number of stars shown.")
    on_rate: Callable[[int], Any] | None = Field(
        default=None,
        description="Optional handler called with the tapped star's 1-based value; "
        "when ``None`` the rating is presentational.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the filled stars paint with.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme resolving the star color.",
    )

    def _handler(self, rating: int) -> Callable[[], None]:
        """Build a zero-argument handler reporting ``rating``.

        Args:
            rating: The 1-based rating this star reports.

        Returns:
            A click handler invoking ``on_rate`` with ``rating``.
        """

        def handler() -> None:
            if self.on_rate is not None:
                self.on_rate(rating)

        return handler

    def _star(self, index: int, color: Color) -> Widget:
        """Build one star cell.

        Args:
            index: The zero-based star position.
            color: The resolved star color.

        Returns:
            A tappable ``Button`` when ``on_rate`` is set, else a ``Text`` glyph.
        """
        glyph = "★" if index < self.value else "☆"
        star_style = Style(font_size=24.0, color=color)
        if self.on_rate is not None:
            # A clickable star is an icon-forward GHOST button with an explicitly
            # transparent fill, so the glyph reads as a bare star instead of a
            # filled pill (the SOLID default would paint the role color over it).
            return Button(
                label=glyph,
                on_click=self._handler(index + 1),
                key=f"star-{index}",
                variant=Variant.GHOST,
                style=Style(
                    font_size=24.0,
                    color=color,
                    background=Color(r=0, g=0, b=0, a=0.0),
                ),
            )
        return Text(content=glyph, key=f"star-{index}", style=star_style)

    def render(self) -> Widget:
        """Lower the rating into a primitive row of stars.

        Returns:
            A ``Row`` of star cells.
        """
        color = self.theme.color(self.color_scheme)
        default = Style(gap=self.theme.space("xs"))
        return Row(
            key=self.key or "rating",
            style=merge_style(default, self.style),
            children=[self._star(index, color) for index in range(self.max_stars)],
        )
