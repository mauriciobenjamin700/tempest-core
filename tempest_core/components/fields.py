"""Field components: ``Stepper`` (numeric +/-) and ``SearchBar`` (text + clear).

Higher-level value inputs assembled from primitives. ``SearchBar`` wraps the
controlled ``Input``; ``Stepper`` clamps to optional bounds before reporting.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import Field

from tempest_core.components.base import (
    MUTED,
    ON_SURFACE,
    merge_style,
)
from tempest_core.icons import Icons
from tempest_core.style import (
    AlignItems,
    CardVariant,
    Edge,
    FieldVariant,
    FontWeight,
    Size,
    Style,
    Variant,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_field_variant,
    resolve_surface_variant,
)
from tempest_core.widgets import (
    Button,
    Component,
    IconButton,
    Input,
    Row,
    Text,
    TextChangeEvent,
    Widget,
)

__all__ = ["Stepper", "SearchBar"]


class Stepper(Component):
    """A numeric stepper: ``-`` decrement, current value, ``+`` increment.

    Attributes:
        value: The current value.
        step: The amount added/removed per tap.
        min_value: The lower bound, or ``None`` for unbounded.
        max_value: The upper bound, or ``None`` for unbounded.
        on_change: Called with the new (clamped) value when a button is tapped.
    """

    value: int = Field(default=0, description="The current value.")
    step: int = Field(default=1, description="The amount added/removed per tap.")
    min_value: int | None = Field(
        default=None, description="The lower bound, or ``None`` for unbounded."
    )
    max_value: int | None = Field(
        default=None, description="The upper bound, or ``None`` for unbounded."
    )
    on_change: Callable[[int], Any] = Field(
        description="Called with the new (clamped) value when a button is tapped."
    )

    def _clamped(self, candidate: int) -> int:
        """Clamp ``candidate`` to the configured bounds.

        Args:
            candidate: The proposed new value.

        Returns:
            The value clamped to ``[min_value, max_value]`` where set.
        """
        if self.min_value is not None and candidate < self.min_value:
            return self.min_value
        if self.max_value is not None and candidate > self.max_value:
            return self.max_value
        return candidate

    def _handler(self, delta: int) -> Callable[[], None]:
        """Build a zero-argument handler stepping the value by ``delta``.

        Args:
            delta: The signed amount to add to the current value.

        Returns:
            A click handler invoking ``on_change`` with the clamped result.
        """

        def handler() -> None:
            self.on_change(self._clamped(self.value + delta))

        return handler

    def _button(self, label: str, delta: int, key: str) -> Widget:
        """Build one stepper button.

        Args:
            label: The button glyph (``"-"`` or ``"+"``).
            delta: The signed step the button applies.
            key: The reconciler key.

        Returns:
            A styled increment/decrement button.
        """
        return Button(
            label=label,
            on_click=self._handler(delta),
            key=key,
            style=Style(
                padding=Edge.symmetric(vertical=8.0, horizontal=16.0),
                radius=8.0,
                background=MUTED,
                color=ON_SURFACE,
                font_size=18.0,
            ),
        )

    def render(self) -> Widget:
        """Lower the stepper into a primitive row.

        Returns:
            A ``Row`` of the decrement button, the value and the increment button.
        """
        default = Style(gap=10.0, align=AlignItems.CENTER)
        return Row(
            key=self.key or "stepper",
            style=merge_style(default, self.style),
            children=[
                self._button("-", -self.step, "step-down"),
                Text(
                    content=str(self.value),
                    style=Style(
                        font_size=18.0, font_weight=FontWeight.BOLD, color=ON_SURFACE
                    ),
                    key="step-value",
                ),
                self._button("+", self.step, "step-up"),
            ],
        )


class SearchBar(Component):
    """A search field: a controlled text ``Input`` with an optional clear button.

    Themed (Trilho H5): the inner ``Input`` style is resolved from the Chakra-style
    ``field_variant`` / ``color_scheme`` / ``size`` props via
    :func:`~tempest_core.variants.resolve_field_variant`; the outer pill carries a
    surface treatment from :func:`~tempest_core.variants.resolve_surface_variant`;
    and the clear button lowers to an :class:`~tempest_core.widgets.IconButton`
    (the curated :data:`~tempest_core.icons.Icons.X` glyph, ``GHOST`` variant).
    Backward-compatible: ``SearchBar(value=…, on_change=…)`` is a filled neutral
    search pill.

    Attributes:
        value: The current query text (controlled).
        placeholder: The empty-field hint.
        on_change: Called with the validated ``TextChangeEvent`` on each edit.
        on_clear: Optional handler for the clear button; the button shows only
            when set and the field is non-empty.
        field_variant: The inner input's field treatment (outline / filled /
            flushed).
        color_scheme: The Material 3 role family the focus tint paints with.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        theme: The design-system theme whose tokens resolve the field and pill.
        media: Optional viewport snapshot used to resolve a responsive ``size``.
    """

    value: str = Field(default="", description="The current query text (controlled).")
    placeholder: str = Field(default="Search", description="The empty-field hint.")
    on_change: Callable[[TextChangeEvent], Any] = Field(
        description="Called with the validated ``TextChangeEvent`` on each edit."
    )
    on_clear: Callable[[], Any] | None = Field(
        default=None,
        description="Optional handler for the clear button; the button shows only when "
        "set and the field is non-empty.",
    )
    field_variant: FieldVariant = Field(
        default=FieldVariant.FILLED,
        description="The inner input's field treatment (outline / filled / flushed).",
    )
    color_scheme: str = Field(
        default="neutral",
        description="The Material 3 role family the focus tint paints with.",
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the field and pill.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def render(self) -> Widget:
        """Lower the search bar into a primitive row.

        Returns:
            A ``Row`` of the input and, when applicable, a clear icon button,
            carrying the resolved surface pill style.
        """
        field_style = merge_styles(
            resolve_field_variant(
                variant=self.field_variant,
                size=self.size,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            ),
            Style(grow=1.0),
        )
        children: list[Widget] = [
            Input(
                value=self.value,
                placeholder=self.placeholder,
                on_change=self.on_change,
                key="search-input",
                style=field_style,
            )
        ]
        if self.on_clear is not None and self.value:
            children.append(
                IconButton(
                    icon=Icons.X,
                    on_click=self.on_clear,
                    variant=Variant.GHOST,
                    color_scheme=self.color_scheme,
                    size=self.size,
                    label="clear",
                    theme=self.theme,
                    media=self.media,
                    key="search-clear",
                )
            )
        surface = resolve_surface_variant(
            variant=CardVariant.FILLED,
            color_scheme=self.color_scheme,
            theme=self.theme,
            padding_step="none",
            radius_step="lg",
            media=self.media,
        )
        default = merge_styles(
            surface,
            Style(
                gap=8.0,
                align=AlignItems.CENTER,
                padding=Edge.all(8.0),
            ),
        )
        return Row(
            key=self.key or "searchbar",
            style=merge_style(default, self.style),
            children=children,
        )
