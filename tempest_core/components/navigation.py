"""Navigation components: ``NavBar`` (tab bar), ``Tabs`` and ``Breadcrumb``.

``NavBar`` generalises the ``examples/tabs`` pattern into a reusable component:
a row of selectable items with a highlighted active index. ``Tabs`` is a tab
strip whose active tab carries an underline indicator. ``Breadcrumb`` renders a
path trail with separators. Because a :class:`Component`'s :meth:`render` runs
wherever ``build`` runs (desktop *and* device), the per-item handlers can close
over the caller's ``on_select`` and the item index directly.

Themed (Trilho H5): ``NavBar``'s bar is a
:func:`~tempest_core.variants.resolve_surface_variant` surface, the active item is
an accent pill via :func:`~tempest_core.variants.resolve_badge_variant` (SOLID)
and inactive items are a :func:`~tempest_core.variants.resolve_variant` (GHOST)
text. ``Tabs`` mirrors that: a surface strip + per-tab GHOST text, the active tab
taking the role color plus a thin bottom-``SideBorder`` underline. ``Breadcrumb``
reads its colors from the theme roles, with the optional link crumb resolved via
:func:`~tempest_core.variants.resolve_variant` (LINK). Every existing call site
still works — the H5 props are additive with backward-compatible defaults.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import (
    AlignItems,
    BadgeVariant,
    Border,
    CardVariant,
    Color,
    Edge,
    FontWeight,
    JustifyContent,
    SideBorder,
    Size,
    Style,
    Variant,
)
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_badge_variant,
    resolve_surface_variant,
    resolve_variant,
)
from tempest_core.widgets import Button, Component, Row, Text, Widget

__all__ = ["NavBar", "Tabs", "Breadcrumb"]


def _no_labels() -> list[str]:
    """Provide a fresh, typed empty label list for the default factory.

    Returns:
        A new empty list of strings.
    """
    return []


class NavBar(Component):
    """A horizontal navigation/tab bar with a highlighted active item.

    Themed (Trilho H5): the bar surface is resolved from
    :func:`~tempest_core.variants.resolve_surface_variant`; the active item is an
    accent pill from :func:`~tempest_core.variants.resolve_badge_variant` (SOLID,
    ``color_scheme``); inactive items are a low-emphasis GHOST treatment from
    :func:`~tempest_core.variants.resolve_variant` (neutral). Backward-compatible:
    ``NavBar(items=…, active=…, on_select=…)`` is a primary-accented bar over a
    neutral surface.

    Attributes:
        items: The visible item labels, in order.
        active: The index of the currently selected item.
        on_select: Called with the tapped item's index when an item is pressed.
        color_scheme: The Material 3 role family the active pill paints with.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        theme: The design-system theme whose tokens resolve the bar and items.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
    """

    items: list[str] = Field(
        description="The visible item labels, in order.", default_factory=_no_labels
    )
    active: int = Field(
        default=0, description="The index of the currently selected item."
    )
    on_select: Callable[[int], Any] = Field(
        description="Called with the tapped item's index when an item is pressed."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the active pill paints with.",
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the bar and items.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def _make_handler(self, index: int) -> Callable[[], None]:
        """Build a zero-argument handler that selects ``index``.

        Args:
            index: The item index this handler selects.

        Returns:
            A click handler invoking ``on_select`` with ``index``.
        """

        def handler() -> None:
            self.on_select(index)

        return handler

    def _item(self, index: int, label: str) -> Widget:
        """Build one navigation item button.

        Args:
            index: The item's position in the bar.
            label: The item's visible label.

        Returns:
            A button styled as an accent pill (active) or GHOST (inactive).
        """
        active = index == self.active
        if active:
            item_style = resolve_badge_variant(
                variant=BadgeVariant.SOLID,
                size=self.size,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            )
        else:
            item_style = resolve_variant(
                variant=Variant.GHOST,
                size=self.size,
                color_scheme="neutral",
                theme=self.theme,
                media=self.media,
            )
        item_style = merge_styles(item_style, Style(grow=1.0))
        return Button(
            label=label,
            on_click=self._make_handler(index),
            key=f"nav-{index}",
            style=item_style,
        )

    def render(self) -> Widget:
        """Lower the navigation bar into a primitive row of buttons.

        Returns:
            A ``Row`` of item buttons with the active one highlighted as an accent
            pill, carrying the resolved surface style.
        """
        surface = resolve_surface_variant(
            variant=CardVariant.FILLED,
            color_scheme="neutral",
            theme=self.theme,
            padding_step="none",
            media=self.media,
        )
        default = merge_styles(
            surface,
            Style(
                gap=8.0,
                padding=Edge.all(8.0),
                justify=JustifyContent.CENTER,
            ),
        )
        return Row(
            key=self.key or "navbar",
            style=merge_style(default, self.style),
            children=[
                self._item(index, label) for index, label in enumerate(self.items)
            ],
        )


class Tabs(Component):
    """A tab strip whose active tab carries an underline indicator.

    Themed (Trilho H5): the strip is a
    :func:`~tempest_core.variants.resolve_surface_variant` surface; each tab is a
    :func:`~tempest_core.variants.resolve_variant` (GHOST, neutral) text; the
    active tab takes the ``color_scheme`` role ``color`` plus a thin **underline
    indicator** — a one-pixel-tall bottom :class:`~tempest_core.style.SideBorder`
    in the accent role (existing ``Border`` / ``SideBorder`` fields, **no** new
    style field). Mirrors :class:`NavBar`'s lowering and the same zero-argument
    select handler. ``Tabs`` is presentational selection: the active index lives
    in app state, toggled from ``on_select``.

    Attributes:
        tabs: The visible tab labels, in order.
        active: The index of the currently selected tab.
        on_select: Called with the tapped tab's index when a tab is pressed.
        color_scheme: The Material 3 role family the active tab + underline use.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        theme: The design-system theme whose tokens resolve the strip and tabs.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
    """

    tabs: list[str] = Field(
        description="The visible tab labels, in order.", default_factory=_no_labels
    )
    active: int = Field(
        default=0, description="The index of the currently selected tab."
    )
    on_select: Callable[[int], Any] = Field(
        description="Called with the tapped tab's index when a tab is pressed."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the active tab + underline use.",
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the strip and tabs.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def _make_handler(self, index: int) -> Callable[[], None]:
        """Build a zero-argument handler that selects ``index``.

        Args:
            index: The tab index this handler selects.

        Returns:
            A click handler invoking ``on_select`` with ``index``.
        """

        def handler() -> None:
            self.on_select(index)

        return handler

    def _tab(self, index: int, label: str, accent: Color) -> Widget:
        """Build one tab button.

        Args:
            index: The tab's position in the strip.
            label: The tab's visible label.
            accent: The resolved accent color for the active tab + underline.

        Returns:
            A GHOST button, the active one taking the accent color plus a bottom
            underline border.
        """
        active = index == self.active
        base = resolve_variant(
            variant=Variant.GHOST,
            size=self.size,
            color_scheme=self.color_scheme if active else "neutral",
            theme=self.theme,
            media=self.media,
        )
        overrides = Style(grow=1.0)
        if active:
            # The underline indicator: a thin bottom SideBorder in the accent role
            # (existing fields only — no new Style field).
            overrides = merge_styles(
                overrides,
                Style(border=SideBorder(bottom=Border(width=2.0, color=accent))),
            )
        return Button(
            label=label,
            on_click=self._make_handler(index),
            key=f"tab-{index}",
            style=merge_styles(base, overrides),
        )

    def render(self) -> Widget:
        """Lower the tab strip into a primitive row of tab buttons.

        Returns:
            A ``Row`` of GHOST tab buttons with the active one underlined,
            carrying the resolved surface strip style.
        """
        surface = resolve_surface_variant(
            variant=CardVariant.FILLED,
            color_scheme="neutral",
            theme=self.theme,
            padding_step="none",
            radius_step="none",
            media=self.media,
        )
        accent = self.theme.color(self.color_scheme)
        default = merge_styles(
            surface,
            Style(
                gap=4.0,
                padding=Edge.symmetric(vertical=0.0, horizontal=4.0),
                justify=JustifyContent.CENTER,
                align=AlignItems.STRETCH,
            ),
        )
        return Row(
            key=self.key or "tabs",
            style=merge_style(default, self.style),
            children=[
                self._tab(index, label, accent) for index, label in enumerate(self.tabs)
            ],
        )


class Breadcrumb(Component):
    """A path trail of crumbs joined by a separator.

    Themed (Trilho H5, tokens-only): the separators use the theme's
    ``ON_SURFACE_VARIANT`` role, the current (last) crumb uses ``ON_SURFACE`` and a
    non-current crumb uses ``ON_SURFACE_VARIANT``; a tappable link crumb resolves
    its style via :func:`~tempest_core.variants.resolve_variant` (LINK,
    ``color_scheme``). Backward-compatible: ``Breadcrumb(items=…)`` is a neutral
    trail.

    Attributes:
        items: The crumb labels from root to current, in order.
        separator: The text drawn between crumbs.
        on_select: Optional handler called with a crumb's index when tapped; when
            ``None`` the crumbs are presentational. The last crumb (current) is
            never tappable.
        color_scheme: The Material 3 role family the link crumb paints with.
        theme: The design-system theme whose tokens supply colors and the link.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    items: list[str] = Field(
        description="The crumb labels from root to current, in order.",
        default_factory=_no_labels,
    )
    separator: str = Field(default="/", description="The text drawn between crumbs.")
    on_select: Callable[[int], Any] | None = Field(
        default=None,
        description="Optional handler called with a crumb's index when tapped; when "
        "``None`` the crumbs are presentational. The last crumb (current) is never "
        "tappable.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the link crumb paints with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens supply colors and the link.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; forwarded).",
    )

    def _handler(self, index: int) -> Callable[[], None]:
        """Build a zero-argument handler selecting crumb ``index``.

        Args:
            index: The crumb index to report.

        Returns:
            A click handler invoking ``on_select`` with ``index``.
        """

        def handler() -> None:
            if self.on_select is not None:
                self.on_select(index)

        return handler

    def _crumb(self, index: int, label: str) -> Widget:
        """Build one crumb (tappable unless it is the current/last one).

        Args:
            index: The crumb's position.
            label: The crumb text.

        Returns:
            A ``Button`` for navigable crumbs, else a ``Text``.
        """
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        is_last = index == len(self.items) - 1
        if self.on_select is not None and not is_last:
            link = resolve_variant(
                variant=Variant.LINK,
                size=Size.SM,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            )
            return Button(
                label=label,
                on_click=self._handler(index),
                key=f"crumb-{index}",
                style=link,
            )
        return Text(
            content=label,
            key=f"crumb-{index}",
            style=Style(
                color=on_surface if is_last else on_surface_variant,
                font_size=14.0,
                font_weight=FontWeight.BOLD if is_last else FontWeight.NORMAL,
            ),
        )

    def render(self) -> Widget:
        """Lower the breadcrumb into a primitive row of crumbs and separators.

        Returns:
            A ``Row`` interleaving crumbs with separator labels.
        """
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        children: list[Widget] = []
        for index, label in enumerate(self.items):
            if index:
                children.append(
                    Text(
                        content=self.separator,
                        style=Style(color=on_surface_variant, font_size=14.0),
                        key=f"sep-{index}",
                    )
                )
            children.append(self._crumb(index, label))
        default = Style(gap=6.0, align=AlignItems.CENTER)
        return Row(
            key=self.key or "breadcrumb",
            style=merge_style(default, self.style),
            children=children,
        )
