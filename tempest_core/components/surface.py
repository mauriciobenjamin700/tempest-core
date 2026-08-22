"""Themed surface primitives: ``Surface`` and ``StyledContainer`` (Trilho H, H3).

The H3 surface kit is anchored on :func:`~tempest_core.variants.resolve_surface_variant`
— the pure resolver that turns the Chakra-ergonomics ``variant`` / ``color_scheme``
/ ``elevation`` props into a Material 3 :class:`~tempest_core.style.Style` (a filled,
elevated or outlined box). Two low-level components consume it:

* :class:`Surface` — the **un-padded** primitive every higher-level surface
  (``Card``, ``Accordion`` header, …) builds on: a single-child box carrying the
  resolved surface style with no inner padding or gap of its own.
* :class:`StyledContainer` — a thin, additive treatment over the IR ``Container``
  primitive that resolves a **token-step** padding (``"md"`` / a float) against the
  theme without mutating the primitive. Keeps the IR ``Container`` pure (D-spec).

Both bake their resolved style at construction (via a ``model_validator``), so the
renderers receive a plain ``Style`` and the diff reacts to a theme change through
the style prop — mirroring the H1/H2 widget baking idiom.
"""

from __future__ import annotations

from pydantic import Field

from tempest_core.style import CardVariant, Edge, Style
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.variants import merge_styles, resolve_surface_variant
from tempest_core.widgets import Component, Container, Widget

__all__ = ["Surface", "StyledContainer"]


class Surface(Component):
    """A themed, un-padded single-child box — the surface primitive cards build on.

    Resolves its :class:`~tempest_core.style.Style` from ``variant`` /
    ``color_scheme`` / ``elevation`` against the design-system ``theme`` via
    :func:`~tempest_core.variants.resolve_surface_variant`, then merges the
    caller's explicit ``style`` on top (its set fields win, so hand-styling still
    works and stays backward-compatible). Unlike :class:`~tempest_core.components.Card`
    it adds **no inner padding or gap** — it is the bare surface, leaving content
    layout to whatever it wraps. ``Card`` is exactly ``Surface`` + padding + a
    ``Column``.

    Attributes:
        child: The optional wrapped widget.
        variant: The surface treatment (elevated / filled / outlined).
        color_scheme: The Material 3 role family to tint with (``"neutral"`` uses
            the plain surface roles; a role family uses the tonal container roles).
        elevation: An explicit Material 3 elevation level (0-5) overriding the
            variant default; ``None`` uses the per-variant default.
        radius_step: The shape-scale step name for the corner radius.
        theme: The design-system theme whose tokens resolve the surface.
        media: Optional viewport snapshot (accepted for parity; unused here).
    """

    #: ``theme``/``media`` are build-time resolution inputs only — they bake into
    #: the resolved ``style`` and are kept OUT of the lowered tree.
    child: Widget | None = Field(
        default=None, description="The optional wrapped widget."
    )
    variant: CardVariant = Field(
        default=CardVariant.ELEVATED,
        description="The surface treatment (elevated / filled / outlined).",
    )
    color_scheme: str = Field(
        default="neutral",
        description="The Material 3 role family to tint with.",
    )
    elevation: int | None = Field(
        default=None,
        description="An explicit M3 elevation level (0-5) overriding the default.",
    )
    radius_step: str = Field(
        default="md", description="The shape-scale step name for the corner radius."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the surface.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot (accepted for parity; unused).",
    )

    def render(self) -> Widget:
        """Lower the surface into a themed single-child container.

        Returns:
            A ``Container`` carrying the resolved surface style (no inner padding
            of its own beyond the resolver's), wrapping the child.
        """
        resolved = resolve_surface_variant(
            variant=self.variant,
            color_scheme=self.color_scheme,
            theme=self.theme,
            elevation=self.elevation,
            radius_step=self.radius_step,
            # A bare surface owns no inner padding; cards add their own.
            padding_step="none",
            media=self.media,
        )
        merged = (
            merge_styles(resolved, self.style) if self.style is not None else resolved
        )
        return Container(key=self.key or "surface", style=merged, child=self.child)


class StyledContainer(Component):
    """A themed single-child box with token-step padding over the IR ``Container``.

    The thin, additive wrapper that gives the primitive
    :class:`~tempest_core.widgets.Container` design-system ergonomics — a
    **token-step** padding (``"md"`` / ``"lg"`` / a raw float) resolved against the
    theme's spacing scale — without mutating the IR primitive, which stays pure.
    A bare ``padding`` float keeps backward-compatibility; a step name resolves via
    :meth:`~tempest_core.theme.Theme.space`. An explicit ``style`` is merged on top.

    Attributes:
        child: The optional wrapped widget.
        padding: The inner padding — a token-step name (``"md"``) or a raw float in
            logical pixels.
        theme: The design-system theme whose spacing scale resolves a step name.
    """

    child: Widget | None = Field(
        default=None, description="The optional wrapped widget."
    )
    padding: float | str = Field(
        default="md",
        description='Inner padding — a token-step name (``"md"``) or a float.',
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose spacing scale resolves a step.",
    )

    def render(self) -> Widget:
        """Lower the styled container into a primitive padded container.

        Returns:
            A ``Container`` whose ``style.padding`` is the resolved token-step (or
            float) padding, with any explicit ``style`` merged on top.
        """
        amount = (
            self.theme.space(self.padding)
            if isinstance(self.padding, str)
            else self.padding
        )
        default = Style(padding=Edge.all(amount))
        merged = (
            merge_styles(default, self.style) if self.style is not None else default
        )
        return Container(
            key=self.key or "styled-container", style=merged, child=self.child
        )
