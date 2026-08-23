"""Page-structure components: ``Sidebar``, ``Scaffold``, ``Grid``, stacks.

``Sidebar`` is a fixed-width lateral column; ``Scaffold`` is the page frame that
stacks an app bar, a growing body and an optional bottom bar; ``Grid`` lays
children out in a fixed number of equal-width columns; ``HStack``/``VStack`` are
thin SwiftUI-style stacks over ``Row``/``Column`` with a token-step ``gap`` and
alignment ergonomics. All lower to primitive ``Column``/``Row``/``Container``
trees.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import AlignItems, CardVariant, Edge, JustifyContent, Style
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import merge_styles, resolve_surface_variant
from tempest_core.widgets import Column, Component, Container, Row, ScrollView, Widget

__all__ = ["Sidebar", "Scaffold", "Grid", "HStack", "VStack"]


def _no_widgets() -> list[Widget]:
    """Provide a fresh, typed empty widget list for default factories.

    Returns:
        A new empty list of widgets.
    """
    return []


class Sidebar(Component):
    """A fixed-width lateral column of navigation/content widgets.

    Themed (Trilho H5): the panel surface is resolved from ``variant`` /
    ``color_scheme`` / ``elevation`` via
    :func:`~tempest_core.variants.resolve_surface_variant`, mirroring a card; the
    fixed width and padding are unchanged. Backward-compatible:
    ``Sidebar(children=…)`` is an elevated neutral panel.

    Attributes:
        children: The widgets stacked top-to-bottom in the sidebar.
        width: The sidebar's fixed width in logical pixels.
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with.
        elevation: An explicit M3 elevation level (0-5) overriding the default.
        theme: The design-system theme whose tokens resolve the panel surface.
        media: Optional viewport snapshot (accepted for parity; forwarded).
    """

    default_key: ClassVar[str] = "sidebar"

    children: list[Widget] = Field(
        description="The widgets stacked top-to-bottom in the sidebar.",
        default_factory=_no_widgets,
    )
    width: float = Field(
        default=240.0, description="The sidebar's fixed width in logical pixels."
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
        """Lower the sidebar into a fixed-width primitive column.

        Returns:
            A ``Column`` carrying the sidebar's children, with the resolved
            surface style.
        """
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


class Scaffold(Component):
    """A page frame: app bar on top, growing body, optional bottom bar.

    Attributes:
        app_bar: The top bar widget (commonly an :class:`AppBar`); omitted when
            ``None``.
        body: The main content; defaults to an empty column when ``None``.
        bottom_bar: A bottom bar widget (e.g. a :class:`NavBar` or ``Footer``);
            omitted when ``None``.
        scroll: When ``True``, the body is wrapped in a ``ScrollView`` (a Qt
            convenience; the Compose renderer scrolls natively post-Trilho-B).
        theme: The design-system theme whose ``BACKGROUND`` role fills the frame.
    """

    default_key: ClassVar[str] = "scaffold"

    app_bar: Widget | None = Field(
        default=None,
        description="The top bar widget (commonly an :class:`AppBar`); omitted when "
        "``None``.",
    )
    body: Widget | None = Field(
        default=None,
        description="The main content; defaults to an empty column when ``None``.",
    )
    bottom_bar: Widget | None = Field(
        default=None,
        description="A bottom bar widget (e.g. a :class:`NavBar` or ``Footer``); "
        "omitted when ``None``.",
    )
    scroll: bool = Field(
        default=False,
        description="When ``True``, the body is wrapped in a ``ScrollView`` (a Qt "
        "convenience; the Compose renderer scrolls natively post-Trilho-B).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose ``BACKGROUND`` role fills the "
        "frame.",
    )

    def render(self) -> Widget:
        """Lower the scaffold into a stacked primitive column.

        Returns:
            A ``Column`` stacking the app bar, the (growing) body and the bottom
            bar in order.
        """
        children: list[Widget] = []
        if self.app_bar is not None:
            children.append(self.app_bar)
        body: Widget = self.body if self.body is not None else Column()
        if self.scroll:
            body = ScrollView(
                children=[body],
                style=Style(grow=1.0),
                key=self.child_key("body"),
            )
        else:
            body = Container(
                child=body, style=Style(grow=1.0), key=self.child_key("body")
            )
        children.append(body)
        if self.bottom_bar is not None:
            children.append(self.bottom_bar)
        default = Style(gap=0.0, background=self.theme.color(ColorRole.BACKGROUND))
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=children,
        )


class Grid(Component):
    """A fixed-column grid laying children out in equal-width cells.

    Attributes:
        children: The cell widgets, filled left-to-right then top-to-bottom.
        columns: The number of columns per row (clamped to at least 1).
        gap: The spacing between cells, both horizontally and vertically.
    """

    default_key: ClassVar[str] = "grid"

    children: list[Widget] = Field(
        description="The cell widgets, filled left-to-right then top-to-bottom.",
        default_factory=_no_widgets,
    )
    columns: int = Field(
        default=2, description="The number of columns per row (clamped to at least 1)."
    )
    gap: float | str = Field(
        default=8.0,
        description='The spacing between cells — a token-step name (``"md"``) or a '
        "float in logical pixels.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose spacing scale resolves a step name.",
    )

    def render(self) -> Widget:
        """Lower the grid into a primitive column of rows.

        Returns:
            A ``Column`` of ``Row``s; each child is wrapped in a growing
            ``Container`` so columns share width, and short final rows are padded
            with empty cells to keep alignment.
        """
        columns = max(1, self.columns)
        gap = self.theme.space(self.gap) if isinstance(self.gap, str) else self.gap
        rows: list[Widget] = []
        for start in range(0, len(self.children), columns):
            chunk = self.children[start : start + columns]
            cells: list[Widget] = [
                Container(
                    style=Style(grow=1.0),
                    child=child,
                    key=self.child_key(f"cell-{start + offset}"),
                )
                for offset, child in enumerate(chunk)
            ]
            for pad in range(len(chunk), columns):
                cells.append(
                    Container(
                        style=Style(grow=1.0),
                        key=self.child_key(f"cell-pad-{start}-{pad}"),
                    )
                )
            rows.append(
                Row(
                    style=Style(gap=gap),
                    children=cells,
                    key=self.child_key(f"row-{start}"),
                )
            )
        default = Style(gap=gap)
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=rows,
        )


class HStack(Component):
    """A horizontal stack: children laid left-to-right with a token-step gap.

    A thin, SwiftUI-style ergonomic wrapper over the primitive
    :class:`~tempest_core.widgets.Row`. The ``gap`` is a **token-step** name
    (``"md"`` / ``"lg"``) resolved against the theme's spacing scale, or a raw
    float for backward-compatibility; ``align`` (cross-axis) and ``justify``
    (main-axis) are surfaced directly so the common layout is one call. An
    explicit ``style`` is merged on top of the resolved defaults.

    Attributes:
        children: The ordered child widgets, laid left-to-right.
        gap: The spacing between children — a token-step name (``"md"``) or a
            float in logical pixels.
        align: The cross-axis (vertical) alignment of the children.
        justify: The main-axis (horizontal) distribution of the children.
        theme: The design-system theme whose spacing scale resolves the gap.
    """

    default_key: ClassVar[str] = "hstack"

    children: list[Widget] = Field(
        description="The ordered child widgets, laid left-to-right.",
        default_factory=_no_widgets,
    )
    gap: float | str = Field(
        default="md",
        description="Spacing between children — a token-step name or a float.",
    )
    align: AlignItems | None = Field(
        default=AlignItems.CENTER,
        description="The cross-axis (vertical) alignment of the children.",
    )
    justify: JustifyContent | None = Field(
        default=None,
        description="The main-axis (horizontal) distribution of the children.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose spacing scale resolves the gap.",
    )

    def render(self) -> Widget:
        """Lower the horizontal stack into a primitive ``Row``.

        Returns:
            A ``Row`` carrying the resolved gap/align/justify, with any explicit
            ``style`` merged on top.
        """
        gap = self.theme.space(self.gap) if isinstance(self.gap, str) else self.gap
        default = Style(gap=gap, align=self.align, justify=self.justify)
        return Row(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=self.children,
        )


class VStack(Component):
    """A vertical stack: children laid top-to-bottom with a token-step gap.

    The vertical sibling of :class:`HStack` over the primitive
    :class:`~tempest_core.widgets.Column`. The ``gap`` is a **token-step** name
    resolved against the theme's spacing scale (or a raw float); ``align``
    (cross-axis, horizontal) and ``justify`` (main-axis, vertical) are surfaced
    directly. An explicit ``style`` is merged on top.

    Attributes:
        children: The ordered child widgets, laid top-to-bottom.
        gap: The spacing between children — a token-step name (``"md"``) or a
            float in logical pixels.
        align: The cross-axis (horizontal) alignment of the children.
        justify: The main-axis (vertical) distribution of the children.
        theme: The design-system theme whose spacing scale resolves the gap.
    """

    default_key: ClassVar[str] = "vstack"

    children: list[Widget] = Field(
        description="The ordered child widgets, laid top-to-bottom.",
        default_factory=_no_widgets,
    )
    gap: float | str = Field(
        default="md",
        description="Spacing between children — a token-step name or a float.",
    )
    align: AlignItems | None = Field(
        default=None,
        description="The cross-axis (horizontal) alignment of the children.",
    )
    justify: JustifyContent | None = Field(
        default=None,
        description="The main-axis (vertical) distribution of the children.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose spacing scale resolves the gap.",
    )

    def render(self) -> Widget:
        """Lower the vertical stack into a primitive ``Column``.

        Returns:
            A ``Column`` carrying the resolved gap/align/justify, with any
            explicit ``style`` merged on top.
        """
        gap = self.theme.space(self.gap) if isinstance(self.gap, str) else self.gap
        default = Style(gap=gap, align=self.align, justify=self.justify)
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=self.children,
        )
