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

import re
from collections.abc import Callable
from typing import Any, ClassVar

from pydantic import ConfigDict, Field, field_validator

from tempest_core._model import _CoreModel
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
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_badge_variant,
    resolve_surface_variant,
    resolve_variant,
)
from tempest_core.widgets import Button, Component, Row, Text, Widget

__all__ = ["NavBar", "Tabs", "Breadcrumb", "BreadcrumbItem", "BREADCRUMB_HREF_SCHEMES"]


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

    default_key: ClassVar[str] = "navbar"

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
        default_factory=current_theme,
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
            key=self.child_key(f"item-{index}"),
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
            key=self.base_key,
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

    default_key: ClassVar[str] = "tabs"

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
        default_factory=current_theme,
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

        Note:
            The underline indicator is a thin bottom ``SideBorder`` in the accent
            role — existing ``Style`` fields only, no new field.
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
            overrides = merge_styles(
                overrides,
                Style(border=SideBorder(bottom=Border(width=2.0, color=accent))),
            )
        return Button(
            label=label,
            on_click=self._make_handler(index),
            key=self.child_key(f"item-{index}"),
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
            key=self.base_key,
            style=merge_style(default, self.style),
            children=[
                self._tab(index, label, accent) for index, label in enumerate(self.tabs)
            ],
        )


#: URL schemes a :class:`BreadcrumbItem` ``href`` may carry. A crumb label is
#: very often data the app did not write (a folder name, a remote path), and the
#: HTML renderer escapes attribute *values* but cannot make a ``javascript:`` URL
#: safe — escaping a script is still a script. Relative references (``/b/fotos``,
#: ``../``, ``?page=2``, ``#top``) carry no scheme and are always allowed.
BREADCRUMB_HREF_SCHEMES: frozenset[str] = frozenset({"http", "https"})

#: Characters the WHATWG URL parser removes from anywhere in an input before it
#: reads the scheme, so ``"java\tscript:alert(1)"`` is ``javascript:`` to a
#: browser. The scheme check strips them the same way before looking.
_URL_STRIPPED_CHARS: dict[int, None] = dict.fromkeys(map(ord, "\t\n\r"))

_SCHEME_RE: re.Pattern[str] = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")


def _href_scheme(href: str) -> str | None:
    """Read the scheme a browser would resolve ``href`` with.

    Mirrors the WHATWG URL parser's pre-processing: leading/trailing C0 control
    characters and spaces are trimmed, and ASCII tab/newline/carriage return are
    removed from anywhere, before the scheme is read.

    Args:
        href: The raw ``href`` value.

    Returns:
        The lower-cased scheme, or ``None`` for a relative reference.
    """
    cleaned = href.translate(_URL_STRIPPED_CHARS).strip("".join(map(chr, range(33))))
    match = _SCHEME_RE.match(cleaned)
    return match.group(1).lower() if match else None


class BreadcrumbItem(_CoreModel):
    """One crumb of a :class:`Breadcrumb` that can carry its own destination.

    A plain ``str`` crumb is still accepted by :class:`Breadcrumb`; this model is
    what gives a step an ``href``, so a server-rendered trail (no event loop to
    resolve ``on_select``) can still take the user back to each folder. The HTML
    renderer emits an ``<a href>`` for it; non-web renderers ignore ``href`` and
    draw the label as text.

    Attributes:
        label: The visible crumb text.
        href: The destination URL, or ``None`` for a crumb without one. Must be a
            relative reference or use a scheme in
            :data:`BREADCRUMB_HREF_SCHEMES`.
    """

    model_config = ConfigDict(frozen=True)

    label: str = Field(description="The visible crumb text.")
    href: str | None = Field(
        default=None,
        description="The destination URL, or ``None`` for a crumb without one. Must "
        "be a relative reference or use an ``http``/``https`` scheme.",
    )

    @field_validator("href")
    @classmethod
    def _check_href(cls, value: str | None) -> str | None:
        """Refuse an ``href`` whose scheme would run or embed content.

        Args:
            value: The candidate ``href``.

        Returns:
            The unchanged ``href``.

        Raises:
            ValueError: If the resolved scheme is not in
                :data:`BREADCRUMB_HREF_SCHEMES` (``javascript:``, ``data:``,
                ``vbscript:`` …), or if the value contains a control character.
        """
        if value is None:
            return None
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("href must not contain control characters")
        scheme = _href_scheme(value)
        if scheme is not None and scheme not in BREADCRUMB_HREF_SCHEMES:
            raise ValueError(
                f"href scheme {scheme!r} is not allowed; use a relative reference "
                f"or one of {sorted(BREADCRUMB_HREF_SCHEMES)}"
            )
        return value


def _no_crumbs() -> list[str | BreadcrumbItem]:
    """Provide a fresh, typed empty crumb list for the default factory.

    Returns:
        A new empty list of crumbs.
    """
    return []


class Breadcrumb(Component):
    """A path trail of crumbs joined by a separator, rendered as a navigation landmark.

    Themed (Trilho H5, tokens-only): the separators use the theme's
    ``ON_SURFACE_VARIANT`` role, the current (last) crumb uses ``ON_SURFACE`` and a
    non-current crumb uses ``ON_SURFACE_VARIANT``; a link crumb resolves its style
    via :func:`~tempest_core.variants.resolve_variant` (LINK, ``color_scheme``).
    Backward-compatible: ``Breadcrumb(items=…)`` is a neutral trail.

    A crumb navigates one of two ways. A :class:`BreadcrumbItem` with an ``href``
    is a real link — the web renderers emit ``<a href>`` and the browser owns the
    navigation, which is what a server-rendered page needs. A crumb without an
    ``href`` (a plain ``str``) becomes a tappable button when ``on_select`` is set,
    for the platforms with an event loop. ``on_select`` never fires for a crumb
    that has an ``href``.

    Semantics on the web: the root is a ``<nav>`` labelled by :attr:`label`, the
    last crumb carries ``aria-current="page"`` and the separators are
    ``aria-hidden``, so a screen reader announces the landmark and the steps but
    not the ``/`` between them. A ``tag`` or ``attrs`` set on the component merges
    over these defaults on the root.

    Attributes:
        items: The crumbs from root to current, in order: plain labels or
            :class:`BreadcrumbItem` s carrying an ``href``.
        separator: The text drawn between crumbs.
        on_select: Optional handler called with a crumb's index when a crumb
            without an ``href`` is tapped; when ``None`` those crumbs are
            presentational. The last crumb (current) is never tappable.
        label: The accessible name of the navigation landmark (``aria-label``).
        color_scheme: The Material 3 role family the link crumb paints with.
        theme: The design-system theme whose tokens supply colors and the link.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    default_key: ClassVar[str] = "breadcrumb"

    items: list[str | BreadcrumbItem] = Field(
        description="The crumbs from root to current, in order: plain labels or "
        "``BreadcrumbItem`` s carrying an ``href``.",
        default_factory=_no_crumbs,
    )
    separator: str = Field(default="/", description="The text drawn between crumbs.")
    on_select: Callable[[int], Any] | None = Field(
        default=None,
        description="Optional handler called with a crumb's index when a crumb "
        "without an ``href`` is tapped; when ``None`` those crumbs are "
        "presentational. The last crumb (current) is never tappable.",
    )
    label: str = Field(
        default="Breadcrumb",
        description="The accessible name of the navigation landmark (aria-label).",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the link crumb paints with.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
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

    def _link_style(self) -> Style:
        """Resolve the LINK style every navigable crumb paints with.

        Returns:
            The resolved LINK variant style in :attr:`color_scheme`.
        """
        return resolve_variant(
            variant=Variant.LINK,
            size=Size.SM,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )

    def _crumb(self, index: int, item: str | BreadcrumbItem) -> Widget:
        """Build one crumb.

        An ``href`` crumb is a ``Text`` tagged ``a`` (a link on every web
        renderer, text elsewhere) that takes only the LINK variant's typography —
        color, size, weight, underline. The variant's padding, background and
        48px ``min_height`` are a button's hit box; on an inline ``<a>`` they
        drew each crumb as a box and pushed it off the separators' baseline. A
        plain crumb is a ``Button`` when
        ``on_select`` is set and it is not the last one, else a ``Text``. The last
        crumb carries ``aria-current="page"`` in every case.

        Args:
            index: The crumb's position.
            item: The crumb label or item.

        Returns:
            The crumb widget.
        """
        key = self.child_key(f"item-{index}")
        is_last = index == len(self.items) - 1
        label = item if isinstance(item, str) else item.label
        href = None if isinstance(item, str) else item.href
        current = {"aria-current": "page"} if is_last else {}
        if href is not None:
            link = self._link_style()
            return Text(
                content=label,
                key=key,
                tag="a",
                attrs={"href": href, **current},
                style=Style(
                    color=link.color,
                    font_size=link.font_size,
                    font_weight=FontWeight.BOLD if is_last else link.font_weight,
                    text_decoration=link.text_decoration,
                ),
            )
        if self.on_select is not None and not is_last:
            return Button(
                label=label,
                on_click=self._handler(index),
                key=key,
                style=self._link_style(),
            )
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        return Text(
            content=label,
            key=key,
            attrs=current,
            style=Style(
                color=on_surface if is_last else on_surface_variant,
                font_size=14.0,
                font_weight=FontWeight.BOLD if is_last else FontWeight.NORMAL,
            ),
        )

    def render(self) -> Widget:
        """Lower the breadcrumb into a ``nav``-tagged row of crumbs and separators.

        Returns:
            A ``Row`` interleaving crumbs with ``aria-hidden`` separator labels.
        """
        on_surface_variant = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        children: list[Widget] = []
        for index, item in enumerate(self.items):
            if index:
                children.append(
                    Text(
                        content=self.separator,
                        style=Style(color=on_surface_variant, font_size=14.0),
                        key=self.child_key(f"sep-{index}"),
                        attrs={"aria-hidden": "true"},
                    )
                )
            children.append(self._crumb(index, item))
        default = Style(gap=6.0, align=AlignItems.CENTER)
        return Row(
            key=self.base_key,
            style=merge_style(default, self.style),
            tag=self.tag or "nav",
            attrs={"aria-label": self.label, **self.attrs},
            children=children,
        )
