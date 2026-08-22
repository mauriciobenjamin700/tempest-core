"""Date/time components: ``Calendar`` (month grid) and ``Clock`` (digital).

``Calendar`` lays out a month as a grid of day buttons and reports the tapped ISO
date through ``on_select``. ``Clock`` renders a preformatted time string (the app
drives the tick from state, as in the ``stopwatch`` example). Both lower to
primitives.
"""

from __future__ import annotations

import calendar as _calendar
import datetime as _datetime
from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import AlignItems, Edge, FontWeight, Style, TextAlign
from tempest_core.theme import Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.widgets import Button, Column, Component, Container, Row, Text, Widget

__all__ = ["Calendar", "Clock"]

_WEEKDAYS: tuple[str, ...] = ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su")


class Calendar(Component):
    """A month grid of selectable day cells.

    Themed (Trilho H6): the title/day text reads the theme's ``ON_SURFACE`` role,
    the weekday header and unselected days the muted ``ON_SURFACE_VARIANT`` /
    ``SURFACE_VARIANT`` roles, and the selected day fills with the
    ``color_scheme`` role (default ``primary``) on its legible ``on_*`` content —
    all resolved from the theme rather than hard-coded hexes. Backward-compatible:
    ``Calendar(on_select=…)`` renders against the default M3 light theme (a visual
    shift from the previous dark palette).

    Attributes:
        month: The displayed month as ``"YYYY-MM"``; empty means the current
            month.
        selected: The selected day as ``"YYYY-MM-DD"`` (highlighted when it falls
            in the displayed month); empty means no selection.
        on_select: Called with the tapped day's ISO ``"YYYY-MM-DD"`` string.
        color_scheme: The Material 3 role family the selected day fills with.
        theme: The design-system theme whose tokens supply the colors.
    """

    month: str = Field(
        default="",
        description='The displayed month as ``"YYYY-MM"``; empty means the current '
        "month.",
    )
    selected: str = Field(
        default="",
        description='The selected day as ``"YYYY-MM-DD"`` (highlighted when it falls '
        "in the displayed month); empty means no selection.",
    )
    on_select: Callable[[str], Any] = Field(
        description='Called with the tapped day\'s ISO ``"YYYY-MM-DD"`` string.'
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the selected day fills with.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply the colors.",
    )

    def _year_month(self) -> tuple[int, int]:
        """Resolve the displayed ``(year, month)``.

        Returns:
            The parsed ``month`` field, or today's year/month when it is empty.
        """
        if self.month:
            year, mon = self.month.split("-")
            return int(year), int(mon)
        today = _datetime.date.today()
        return today.year, today.month

    def _make_handler(self, iso: str) -> Callable[[], None]:
        """Build a zero-argument handler that selects ``iso``.

        Args:
            iso: The ISO date this handler reports.

        Returns:
            A click handler invoking ``on_select`` with ``iso``.
        """

        def handler() -> None:
            self.on_select(iso)

        return handler

    def _cell(self, year: int, mon: int, day: int, week_index: int, col: int) -> Widget:
        """Build one calendar cell (a day button, or a blank pad for ``day == 0``).

        Args:
            year: The displayed year.
            mon: The displayed month (1-12).
            day: The day number, or ``0`` for a padding cell.
            week_index: The row index of this cell (for keying pads).
            col: The column index of this cell (for keying pads).

        Returns:
            A day ``Button`` or an empty growing ``Container``.
        """
        if day == 0:
            return Container(key=f"pad-{week_index}-{col}", style=Style(grow=1.0))
        iso = f"{year:04d}-{mon:02d}-{day:02d}"
        selected = iso == self.selected
        if selected:
            background = self.theme.color(self.color_scheme)
            color = self.theme.color(f"on_{self.color_scheme}")
        else:
            background = self.theme.color(ColorRole.SURFACE_VARIANT)
            color = self.theme.color(ColorRole.ON_SURFACE)
        return Button(
            label=str(day),
            on_click=self._make_handler(iso),
            key=f"day-{day}",
            style=Style(
                grow=1.0,
                padding=Edge.symmetric(vertical=10.0, horizontal=6.0),
                radius=8.0,
                background=background,
                color=color,
            ),
        )

    def render(self) -> Widget:
        """Lower the calendar into a primitive month grid.

        Returns:
            A ``Column`` of a title, a weekday header row and one row per week.
        """
        year, mon = self._year_month()
        weeks = _calendar.Calendar().monthdayscalendar(year, mon)
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        surface = self.theme.color(ColorRole.SURFACE)
        title = Text(
            content=f"{_calendar.month_name[mon]} {year}",
            style=Style(font_size=18.0, font_weight=FontWeight.BOLD, color=on_surface),
            key="calendar-title",
        )
        header = Row(
            style=Style(gap=6.0),
            children=[
                Text(
                    content=name,
                    style=Style(
                        grow=1.0,
                        font_size=12.0,
                        color=muted,
                        text_align=TextAlign.CENTER,
                    ),
                    key=f"wd-{name}",
                )
                for name in _WEEKDAYS
            ],
            key="calendar-header",
        )
        rows = [
            Row(
                style=Style(gap=6.0),
                children=[
                    self._cell(year, mon, day, week_index, col)
                    for col, day in enumerate(week)
                ],
                key=f"week-{week_index}",
            )
            for week_index, week in enumerate(weeks)
        ]
        default = Style(gap=6.0, padding=Edge.all(12.0), background=surface)
        return Column(
            key=self.key or "calendar",
            style=merge_style(default, self.style),
            children=[title, header, *rows],
        )


class Clock(Component):
    """A digital clock face rendering a preformatted time string.

    Themed (Trilho H6): the time reads the theme's ``ON_SURFACE`` role (or an
    optional ``color_scheme`` role), the caption the muted ``ON_SURFACE_VARIANT``
    role, and the background the ``SURFACE`` role — resolved from the theme rather
    than hard-coded hexes. Backward-compatible: ``Clock(time=…)`` renders against
    the default M3 light theme (a visual shift from the previous dark palette).

    Attributes:
        time: The time text to display (e.g. ``"12:34:56"``); the app formats and
            ticks it from state.
        label: An optional caption shown muted under the time.
        color_scheme: Optional Material 3 role family tinting the time; ``None``
            keeps the neutral ``ON_SURFACE`` time.
        theme: The design-system theme whose tokens supply the colors.
    """

    time: str = Field(
        default="",
        description='The time text to display (e.g. ``"12:34:56"``); the app formats '
        "and ticks it from state.",
    )
    label: str | None = Field(
        default=None, description="An optional caption shown muted under the time."
    )
    color_scheme: str | None = Field(
        default=None,
        description="Optional Material 3 role family tinting the time.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply the colors.",
    )

    def render(self) -> Widget:
        """Lower the clock into a centered primitive column.

        Returns:
            A ``Column`` with the time and, when set, the label.
        """
        time_color = (
            self.theme.color(self.color_scheme)
            if self.color_scheme is not None and self.color_scheme != "neutral"
            else self.theme.color(ColorRole.ON_SURFACE)
        )
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        surface = self.theme.color(ColorRole.SURFACE)
        children: list[Widget] = [
            Text(
                content=self.time,
                style=Style(
                    font_size=40.0,
                    font_weight=FontWeight.BOLD,
                    color=time_color,
                    text_align=TextAlign.CENTER,
                ),
                key="clock-time",
            )
        ]
        if self.label is not None:
            children.append(
                Text(
                    content=self.label,
                    style=Style(
                        font_size=14.0, color=muted, text_align=TextAlign.CENTER
                    ),
                    key="clock-label",
                )
            )
        default = Style(
            gap=4.0,
            padding=Edge.all(16.0),
            align=AlignItems.CENTER,
            background=surface,
        )
        return Column(
            key=self.key or "clock",
            style=merge_style(default, self.style),
            children=children,
        )
