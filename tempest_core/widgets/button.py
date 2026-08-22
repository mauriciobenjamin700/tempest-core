"""Button leaf widget (styled with the H1 Chakra-style variant API)."""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field, PrivateAttr, model_validator

from tempest_core.icons import Icons
from tempest_core.style import ComponentState, Size, Style, Variant
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.variants import (
    MIN_TOUCH_TARGET,
    ResponsiveSize,
    merge_styles,
    resolve_variant,
    resolve_variant_states,
)
from tempest_core.widgets.base import EventHandler, Widget
from tempest_core.widgets.events import Event, TapEvent

__all__ = ["Button", "IconButton"]


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

    #: ``theme``/``media`` are build-time resolution inputs only — they bake into
    #: the resolved ``style`` and are kept OUT of the IR props (a full ``Theme``
    #: per node would bloat the tree and the serialized bridge payload). The
    #: resolved ``style`` already carries their effect.
    prop_exclude_names: ClassVar[frozenset[str]] = frozenset({"theme", "media"})

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
        default_factory=current_theme,
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


class IconButton(Widget):
    """A square/circular icon-only button, styled via the Chakra-style variant API.

    An icon button **is** button-shaped, so it reuses
    :func:`~tempest_core.variants.resolve_variant` exactly like :class:`Button` —
    then pins its ``width`` and ``height`` to the resolved ``min_height`` (a
    square hit area at least the 48dp touch target) and sets a circular ``radius``,
    using only existing :class:`~tempest_core.style.Style` fields (no new field).
    It defaults to the ``GHOST`` variant (the lowest-emphasis, icon-forward
    treatment). An explicit ``style`` is merged on top of the resolved base.

    The ``label`` carries the accessible name (``contentDescription`` / accessible
    label) since the button has no visible text; renderers route it into the
    node's accessibility surface.

    Attributes:
        icon: The icon to show — a curated :class:`~tempest_core.icons.Icons`
            value (or its string) or an arbitrary platform icon name.
        on_click: Optional handler invoked on tap. May be sync or ``async``.
        variant: The visual treatment (solid/outline/ghost/link); defaults to
            ``GHOST``.
        size: The density size — a single :class:`~tempest_core.style.Size` or a
            per-breakpoint map.
        color_scheme: The Material 3 role family to paint with.
        label: The accessible label for the icon-only button (a11y / Semantics).
        theme: The design-system theme whose tokens resolve the variant.
        media: Optional viewport snapshot used to resolve a responsive ``size``.

    Methods:
        state_styles: Resolve the per-interaction-state style table for the
            renderers (default/hover/pressed/disabled/focus), each pinned to the
            square/circular icon-button geometry.
    """

    event_schemas: ClassVar[dict[str, type[Event]]] = {"on_click": TapEvent}

    prop_exclude_names: ClassVar[frozenset[str]] = frozenset({"theme", "media"})

    icon: Icons | str = Field(
        description="The icon to show — a curated Icons value or a platform icon name.",
    )
    on_click: EventHandler | None = Field(
        default=None,
        description="Optional handler invoked on tap. May be sync or ``async``.",
    )
    variant: Variant = Field(
        default=Variant.GHOST,
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
    label: str = Field(
        default="",
        description="The accessible label for the icon-only button (a11y).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the variant.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    _style_override: Style | None = PrivateAttr(default=None)

    @staticmethod
    def _squareify(style: Style) -> Style:
        """Pin a resolved button style to a square/circular icon-button geometry.

        Uses only existing :class:`~tempest_core.style.Style` fields: ``width`` and
        ``height`` are set to the resolved ``min_height`` (a square box at least
        the 48dp touch target) and ``radius`` to half that (a circle).

        Args:
            style: The resolved button style.

        Returns:
            The style pinned to a square, circular geometry.
        """
        dim = style.min_height if style.min_height is not None else MIN_TOUCH_TARGET
        return merge_styles(style, Style(width=dim, height=dim, radius=dim / 2.0))

    @model_validator(mode="after")
    def _resolve_style(self) -> IconButton:
        """Bake the resolved, squared icon-button style into ``style``.

        Resolves the base style like a :class:`Button`, pins it to a square/
        circular geometry, then merges the caller's explicit ``style`` on top.

        Returns:
            The icon button with its ``style`` field resolved.
        """
        override = self.style
        self._style_override = override
        resolved = self._squareify(
            resolve_variant(
                variant=self.variant,
                size=self.size,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            )
        )
        merged = merge_styles(resolved, override) if override is not None else resolved
        object.__setattr__(self, "style", merged)
        return self

    def state_styles(self) -> dict[ComponentState, Style]:
        """Resolve the per-interaction-state style table for the renderers.

        Returns:
            A mapping of each :class:`~tempest_core.style.ComponentState` to its
            resolved, squared, override-merged ``Style``.
        """
        states = {
            state: self._squareify(style)
            for state, style in resolve_variant_states(
                variant=self.variant,
                size=self.size,
                color_scheme=self.color_scheme,
                theme=self.theme,
                media=self.media,
            ).items()
        }
        override = self._style_override
        if override is None:
            return states
        return {state: merge_styles(style, override) for state, style in states.items()}
