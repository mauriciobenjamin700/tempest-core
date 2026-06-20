"""Button leaf widget (styled with the H1 Chakra-style variant API)."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, PrivateAttr, model_validator

from tempest_core.style import ComponentState, Size, Style, Variant
from tempest_core.theme import MediaQueryData, Theme
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_variant,
    resolve_variant_states,
)
from tempest_core.widgets.base import EventHandler, Widget
from tempest_core.widgets.events import Event, TapEvent

__all__ = ["Button"]


class Button(Widget):
    """A tappable button, styled via the Chakra-ergonomics variant API.

    The button resolves its base :class:`~tempest_core.style.Style` from its
    ``variant`` / ``size`` / ``color_scheme`` against the design-system
    ``theme`` (Material 3 tokens), via
    :func:`~tempest_core.variants.resolve_variant`. An explicit ``style`` is
    **merged on top** of the resolved base (its set fields win), so hand-styling
    still works and stays backward-compatible: ``Button(label=...)`` with no
    variant produces a solid/primary/md button, and ``Button(label=..., style=…)``
    layers the override over it. The resolved style is baked into
    :attr:`~tempest_core.widgets.base.Widget.style` so the renderers consume a
    plain ``Style`` unchanged.

    The per-state styles (default/hover/pressed/disabled/focus) are exposed via
    :meth:`state_styles` so a renderer can apply the matching Material 3 state
    layer on real pointer/focus events — the resolution stays pure and in the
    engine; only the event→state mapping lives in the renderers.

    The accessibility surface (``semantics`` / ``focusable`` / ``focus_order``)
    is preserved unchanged from :class:`~tempest_core.widgets.base.Widget`.

    Attributes:
        label: The text shown on the button.
        on_click: Optional handler invoked on tap. May be sync or ``async``;
            the runtime schedules awaitables on the event loop.
        variant: The visual treatment (solid/outline/ghost/link).
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map (``{"base": Size.SM, "md": Size.LG}``).
        color_scheme: The Material 3 role family to paint with (``"primary"``,
            ``"secondary"``, ``"tertiary"``, ``"error"`` or ``"neutral"``).
        theme: The design-system theme whose tokens resolve the variant; defaults
            to the baseline Material 3 theme.
        media: Optional viewport snapshot used to resolve a responsive ``size``.

    Methods:
        state_styles: Resolve the per-interaction-state style table for the
            renderers (default/hover/pressed/disabled/focus).
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_click": TapEvent}

    label: str = Field(description="The text shown on the button.")
    on_click: EventHandler | None = Field(
        default=None,
        description="Optional handler invoked on tap. May be sync or ``async``; the "
        "runtime schedules awaitables on the event loop.",
    )
    variant: Variant = Field(
        default=Variant.SOLID,
        description="The visual treatment (solid/outline/ghost/link).",
    )
    size: ResponsiveSize = Field(
        default=Size.MD,
        description="The density size — a single ``Size`` or a per-breakpoint map.",
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family to paint with.",
    )
    theme: Theme = Field(
        default_factory=Theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    #: The caller's explicit ``style`` override, captured before the resolved
    #: variant style is baked into ``style``. Re-applied on top of every per-state
    #: style by :meth:`state_styles` so the override layers over each state, not
    #: over the already-merged default.
    _style_override: Style | None = PrivateAttr(default=None)

    @model_validator(mode="after")
    def _resolve_style(self) -> Button:
        """Bake the resolved variant style into ``style`` (override layered on top).

        Resolves the base style from ``variant``/``size``/``color_scheme`` against
        the theme, captures the caller's explicit ``style`` as the override, then
        merges that override over the resolved base so hand-set fields win. Runs
        after construction so the renderers see a concrete ``Style``.

        Returns:
            The button with its ``style`` field resolved.
        """
        override = self.style
        self._style_override = override
        resolved = resolve_variant(
            variant=self.variant,
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )
        merged = merge_styles(resolved, override) if override is not None else resolved
        # ``model_validator(mode="after")`` may assign on the validated instance.
        object.__setattr__(self, "style", merged)
        return self

    def state_styles(self) -> dict[ComponentState, Style]:
        """Resolve the per-interaction-state style table for the renderers.

        Returns the resolved :class:`~tempest_core.style.Style` for every
        :class:`~tempest_core.style.ComponentState` (default/hover/pressed/
        disabled/focus), each with any explicit ``style`` override merged on top —
        the same merge applied to the baked default style. A renderer applies the
        matching style on the corresponding pointer/focus event.

        Returns:
            A mapping of each ``ComponentState`` to its resolved, override-merged
            ``Style``.
        """
        states = resolve_variant_states(
            variant=self.variant,
            size=self.size,
            color_scheme=self.color_scheme,
            theme=self.theme,
            media=self.media,
        )
        override = self._style_override
        if override is None:
            return states
        return {state: merge_styles(style, override) for state, style in states.items()}
