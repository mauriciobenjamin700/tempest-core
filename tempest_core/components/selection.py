"""Selection components: SegmentedControl, RadioGroup, Chip and Rating.

Single-choice / value pickers built from primitive ``Button`` rows. They lower to
primitives via :meth:`Component.render`, so they work in both renderers and on
the device with no renderer changes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import ACCENT, MUTED, ON_SURFACE, SURFACE, merge_style
from tempest_core.style import Color, Edge, FontWeight, Size, Style
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import ResponsiveSize, resolve_selection_variant
from tempest_core.widgets import Button, Column, Component, Row, Text, Widget

__all__ = ["SegmentedControl", "RadioGroup", "Chip", "Rating"]


def _no_labels() -> list[str]:
    """Provide a fresh, typed empty label list for default factories.

    Returns:
        A new empty list of strings.
    """
    return []


class SegmentedControl(Component):
    """A compact single-choice pill group.

    Attributes:
        options: The visible segment labels, in order.
        selected: The index of the active segment.
        on_select: Called with the tapped segment's index.
    """

    options: list[str] = Field(
        description="The visible segment labels, in order.", default_factory=_no_labels
    )
    selected: int = Field(default=0, description="The index of the active segment.")
    on_select: Callable[[int], Any] = Field(
        description="Called with the tapped segment's index."
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
        default = Style(gap=4.0, padding=Edge.all(4.0), radius=10.0, background=SURFACE)
        return Row(
            key=self.key or "segmented",
            style=merge_style(default, self.style),
            children=[
                Button(
                    label=label,
                    on_click=self._handler(index),
                    key=f"seg-{index}",
                    style=Style(
                        grow=1.0,
                        padding=Edge.symmetric(vertical=8.0, horizontal=12.0),
                        radius=8.0,
                        background=ACCENT if index == self.selected else SURFACE,
                        color=ON_SURFACE,
                        font_weight=(
                            FontWeight.BOLD
                            if index == self.selected
                            else FontWeight.NORMAL
                        ),
                    ),
                )
                for index, label in enumerate(self.options)
            ],
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
        default_factory=Theme,
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
        default = Style(gap=6.0)
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
                        radius=8.0,
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
    """A small rounded label, optionally selectable.

    Attributes:
        label: The chip text.
        selected: Whether the chip reads as active (only meaningful with
            ``on_click``).
        on_click: Optional tap handler; when ``None`` the chip is presentational.
    """

    label: str = Field(default="", description="The chip text.")
    selected: bool = Field(
        default=False,
        description="Whether the chip reads as active (only meaningful with "
        "``on_click``).",
    )
    on_click: Callable[[], Any] | None = Field(
        default=None,
        description="Optional tap handler; when ``None`` the chip is presentational.",
    )

    def render(self) -> Widget:
        """Lower the chip into a primitive button or a static pill.

        Returns:
            A ``Button`` when ``on_click`` is set, otherwise a ``Text`` pill.
        """
        background = ACCENT if self.selected else MUTED
        chip_style = Style(
            padding=Edge.symmetric(vertical=6.0, horizontal=12.0),
            radius=14.0,
            background=background,
            color=ON_SURFACE,
            font_size=14.0,
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


class Rating(Component):
    """A row of stars showing (and optionally setting) a 1-based rating.

    Attributes:
        value: The number of filled stars.
        max_stars: The total number of stars shown.
        on_rate: Optional handler called with the tapped star's 1-based value;
            when ``None`` the rating is presentational.
    """

    value: int = Field(default=0, description="The number of filled stars.")
    max_stars: int = Field(default=5, description="The total number of stars shown.")
    on_rate: Callable[[int], Any] | None = Field(
        default=None,
        description="Optional handler called with the tapped star's 1-based value; "
        "when ``None`` the rating is presentational.",
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

    def _star(self, index: int) -> Widget:
        """Build one star cell.

        Args:
            index: The zero-based star position.

        Returns:
            A tappable ``Button`` when ``on_rate`` is set, else a ``Text`` glyph.
        """
        glyph = "★" if index < self.value else "☆"
        star_style = Style(font_size=24.0, color=ACCENT)
        if self.on_rate is not None:
            return Button(
                label=glyph,
                on_click=self._handler(index + 1),
                key=f"star-{index}",
                style=star_style,
            )
        return Text(content=glyph, key=f"star-{index}", style=star_style)

    def render(self) -> Widget:
        """Lower the rating into a primitive row of stars.

        Returns:
            A ``Row`` of star cells.
        """
        default = Style(gap=4.0)
        return Row(
            key=self.key or "rating",
            style=merge_style(default, self.style),
            children=[self._star(index) for index in range(self.max_stars)],
        )
