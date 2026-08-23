"""Feedback components: ``Banner``, ``Alert``, ``EmptyState``, ``Badge`` and ``Stat``.

Inline (non-overlay) status surfaces built from primitives. With Trilho H4 these
are **themed via the design-system tokens**: ``Badge`` resolves its pill treatment
from the Chakra-style ``variant`` / ``size`` / ``color_scheme`` (a Material 3
solid/subtle/outline badge) through
:func:`~tempest_core.variants.resolve_badge_variant`; ``Banner`` / ``Alert`` resolve
their block treatment through :func:`~tempest_core.variants.resolve_alert_variant`;
``EmptyState`` reads its muted tones and spacing from the theme; ``Stat`` tints its
delta with the H4 ``success`` / ``error`` status roles. Every existing call site
(``Banner(message=…, tone=…)``, ``Badge(label=…, tone=…)``) still works: the H4
props are additive, and the legacy ``tone`` prop is mapped onto a ``color_scheme``.

Transient/overlay feedback (snackbars, toasts, dialogs) needs a stacking layer and
is out of scope here.
"""

from __future__ import annotations

from typing import ClassVar

from pydantic import Field

from tempest_core.components.base import merge_style
from tempest_core.style import (
    AlertVariant,
    AlignItems,
    BadgeVariant,
    Border,
    Edge,
    FontWeight,
    Size,
    Style,
    TextAlign,
)
from tempest_core.theme import MediaQueryData, Theme, current_theme
from tempest_core.tokens import ColorRole
from tempest_core.variants import (
    ResponsiveSize,
    merge_styles,
    resolve_alert_variant,
    resolve_badge_variant,
)
from tempest_core.widgets import Column, Component, Row, Text, Widget

__all__ = ["Banner", "Alert", "EmptyState", "Badge", "Stat", "ProgressStepper"]

#: Maps the legacy ``tone`` prop onto an H4 ``color_scheme`` so existing call sites
#: (``Banner(tone="success")``) keep working against the new status families. An
#: unknown tone falls back to ``"info"``.
_TONE_SCHEME: dict[str, str] = {
    "info": "info",
    "success": "success",
    "warning": "warning",
    "error": "error",
}


def _tone_scheme(tone: str) -> str:
    """Map a legacy ``tone`` name to an H4 ``color_scheme``.

    Args:
        tone: One of ``"info"`` / ``"success"`` / ``"warning"`` / ``"error"``.

    Returns:
        The matching ``color_scheme`` name, falling back to ``"info"``.
    """
    return _TONE_SCHEME.get(tone, "info")


class Banner(Component):
    """An inline status bar with a message and an optional trailing action.

    Themed (Trilho H4): the background/content come from the
    :func:`~tempest_core.variants.resolve_alert_variant` resolver against the theme
    (a Material 3 subtle alert by default) rather than a hard-coded hex. The legacy
    ``tone`` prop is mapped onto a ``color_scheme``, so ``Banner(tone="success")``
    keeps working; pass ``color_scheme`` / ``variant`` directly for the full H4 API.

    Attributes:
        message: The banner text.
        tone: The legacy status tone (``"info"`` / ``"success"`` / ``"warning"`` /
            ``"error"``); mapped onto ``color_scheme`` when the latter is unset.
        color_scheme: The Material 3 status family to tint with; ``None`` derives
            it from ``tone``.
        variant: The alert treatment (subtle / solid / left_accent / top_accent).
        action: An optional trailing widget (e.g. a dismiss ``Button``).
        theme: The design-system theme whose tokens resolve the treatment.
    """

    default_key: ClassVar[str] = "banner"

    message: str = Field(default="", description="The banner text.")
    tone: str = Field(
        default="info",
        description="The legacy status tone, mapped onto ``color_scheme``.",
    )
    color_scheme: str | None = Field(
        default=None,
        description="The Material 3 status family to tint with; derived from "
        "``tone`` when ``None``.",
    )
    variant: AlertVariant = Field(
        default=AlertVariant.SUBTLE,
        description="The alert treatment (subtle / solid / left_accent / top_accent).",
    )
    action: Widget | None = Field(
        default=None,
        description="An optional trailing widget (e.g. a dismiss ``Button``).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the treatment.",
    )

    def render(self) -> Widget:
        """Lower the banner into a primitive row.

        Returns:
            A themed ``Row`` with the growing message and the optional action.
        """
        scheme = self.color_scheme or _tone_scheme(self.tone)
        resolved = resolve_alert_variant(
            variant=self.variant,
            color_scheme=scheme,
            theme=self.theme,
        )
        content = resolved.color
        children: list[Widget] = [
            Text(
                content=self.message,
                style=Style(grow=1.0, color=content, font_size=14.0),
                key=self.child_key("text"),
            )
        ]
        if self.action is not None:
            children.append(self.action)
        layout = merge_styles(
            resolved,
            Style(gap=12.0, align=AlignItems.CENTER),
        )
        return Row(
            key=self.base_key,
            style=merge_style(layout, self.style),
            children=children,
        )


class Alert(Component):
    """A block-level status callout: optional icon glyph, title, body and dismiss.

    The richer sibling of :class:`Banner`, lowered through the same
    :func:`~tempest_core.variants.resolve_alert_variant` resolver: a row with an
    optional leading glyph and an optional trailing dismiss widget around a column
    that stacks the title (bold) over the body text. Use ``variant=LEFT_ACCENT``
    for the classic accented-edge callout.

    Attributes:
        title: The alert's headline (bold).
        body: An optional secondary line of detail.
        glyph: An optional leading text glyph (no icon font needed).
        color_scheme: The Material 3 status family to tint with (default
            ``"info"``).
        variant: The alert treatment (subtle / solid / left_accent / top_accent).
        dismiss: An optional trailing dismiss widget (e.g. a close ``Button``).
        theme: The design-system theme whose tokens resolve the treatment.
    """

    default_key: ClassVar[str] = "alert"

    title: str = Field(default="", description="The alert's headline (bold).")
    body: str | None = Field(
        default=None, description="An optional secondary line of detail."
    )
    glyph: str | None = Field(
        default=None, description="An optional leading text glyph."
    )
    color_scheme: str = Field(
        default="info", description="The Material 3 status family to tint with."
    )
    variant: AlertVariant = Field(
        default=AlertVariant.SUBTLE,
        description="The alert treatment (subtle / solid / left_accent / top_accent).",
    )
    dismiss: Widget | None = Field(
        default=None,
        description="An optional trailing dismiss widget (e.g. a close ``Button``).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the treatment.",
    )

    def render(self) -> Widget:
        """Lower the alert into a themed primitive row.

        Returns:
            A themed ``Row`` of an optional glyph, the title/body column and an
            optional dismiss widget.
        """
        resolved = resolve_alert_variant(
            variant=self.variant,
            color_scheme=self.color_scheme,
            theme=self.theme,
        )
        content = resolved.color
        column_children: list[Widget] = [
            Text(
                content=self.title,
                style=Style(
                    color=content,
                    font_size=15.0,
                    font_weight=FontWeight.BOLD,
                ),
                key=self.child_key("title"),
            )
        ]
        if self.body is not None:
            column_children.append(
                Text(
                    content=self.body,
                    style=Style(color=content, font_size=13.0),
                    key=self.child_key("body"),
                )
            )
        row_children: list[Widget] = []
        if self.glyph is not None:
            row_children.append(
                Text(
                    content=self.glyph,
                    style=Style(color=content, font_size=20.0),
                    key=self.child_key("glyph"),
                )
            )
        row_children.append(
            Column(
                style=Style(grow=1.0, gap=self.theme.space("xs")),
                children=column_children,
                key=self.child_key("col"),
            )
        )
        if self.dismiss is not None:
            row_children.append(self.dismiss)
        layout = merge_styles(
            resolved,
            Style(gap=self.theme.space("sm"), align=AlignItems.CENTER),
        )
        return Row(
            key=self.base_key,
            style=merge_style(layout, self.style),
            children=row_children,
            semantics=self.semantics,
        )


class EmptyState(Component):
    """A centered placeholder for empty screens: glyph, title, subtitle, action.

    Themed (Trilho H4): the glyph/subtitle read the muted ``ON_SURFACE_VARIANT``
    role, the title reads ``ON_SURFACE``, and the gaps/padding come from the theme's
    spacing scale rather than fixed pixels.

    Attributes:
        title: The primary message.
        subtitle: An optional secondary line.
        glyph: A large text glyph shown above the title (no icon font needed).
        action: An optional call-to-action widget (e.g. a ``Button``).
        theme: The design-system theme whose tokens supply colors and spacing.
    """

    default_key: ClassVar[str] = "emptystate"

    title: str = Field(default="", description="The primary message.")
    subtitle: str | None = Field(
        default=None, description="An optional secondary line."
    )
    glyph: str = Field(
        default="○",
        description="A large text glyph shown above the title (no icon font needed).",
    )
    action: Widget | None = Field(
        default=None,
        description="An optional call-to-action widget (e.g. a ``Button``).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply colors and spacing.",
    )

    def render(self) -> Widget:
        """Lower the empty state into a centered primitive column.

        Returns:
            A ``Column`` stacking the glyph, title, optional subtitle and action.
        """
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        children: list[Widget] = [
            Text(
                content=self.glyph,
                style=Style(font_size=48.0, color=muted, text_align=TextAlign.CENTER),
                key=self.child_key("glyph"),
            ),
            Text(
                content=self.title,
                style=Style(
                    font_size=18.0,
                    font_weight=FontWeight.BOLD,
                    color=on_surface,
                    text_align=TextAlign.CENTER,
                ),
                key=self.child_key("title"),
            ),
        ]
        if self.subtitle is not None:
            children.append(
                Text(
                    content=self.subtitle,
                    style=Style(
                        font_size=14.0,
                        color=muted,
                        text_align=TextAlign.CENTER,
                    ),
                    key=self.child_key("subtitle"),
                )
            )
        if self.action is not None:
            children.append(self.action)
        default = Style(
            gap=self.theme.space("sm"),
            align=AlignItems.CENTER,
            padding=Edge.all(self.theme.space("lg")),
        )
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=children,
        )


class Badge(Component):
    """A small inline status pill (count or short label).

    Themed (Trilho H4): the pill treatment comes from
    :func:`~tempest_core.variants.resolve_badge_variant` against the theme (a
    Material 3 solid/subtle/outline badge) rather than a hard-coded hex. The legacy
    ``tone`` prop is mapped onto a ``color_scheme``, so ``Badge(tone="error")``
    keeps working; pass ``color_scheme`` / ``variant`` / ``size`` for the full API.

    Attributes:
        label: The badge text (e.g. a count like ``"3"`` or ``"NEW"``).
        tone: The legacy status tone, mapped onto ``color_scheme`` when unset.
        color_scheme: The Material 3 status family to tint with; derived from
            ``tone`` when ``None``.
        variant: The badge treatment (solid / subtle / outline).
        size: The density size of the pill.
        theme: The design-system theme whose tokens resolve the treatment.
        media: Optional viewport snapshot for a responsive ``size``.
    """

    default_key: ClassVar[str] = "badge"

    label: str = Field(
        default="",
        description='The badge text (e.g. a count like ``"3"`` or ``"NEW"``).',
    )
    tone: str = Field(
        default="error",
        description="The legacy status tone, mapped onto ``color_scheme``.",
    )
    color_scheme: str | None = Field(
        default=None,
        description="The Material 3 status family; derived from ``tone`` when "
        "``None``.",
    )
    variant: BadgeVariant = Field(
        default=BadgeVariant.SOLID,
        description="The badge treatment (solid / subtle / outline).",
    )
    size: ResponsiveSize = Field(
        default=Size.SM, description="The density size of the pill."
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens resolve the treatment.",
    )
    media: MediaQueryData | None = Field(
        default=None,
        description="Optional viewport snapshot for a responsive ``size``.",
    )

    def render(self) -> Widget:
        """Lower the badge into a primitive pill.

        Returns:
            A small rounded ``Text`` pill in the resolved badge style.
        """
        scheme = self.color_scheme or _tone_scheme(self.tone)
        resolved = resolve_badge_variant(
            variant=self.variant,
            size=self.size,
            color_scheme=scheme,
            theme=self.theme,
            media=self.media,
        )
        default = merge_styles(resolved, Style(text_align=TextAlign.CENTER))
        return Text(
            content=self.label,
            key=self.base_key,
            style=merge_style(default, self.style),
        )


class Stat(Component):
    """A labelled metric with a value and an optional trend delta.

    A compact dashboard stat: a muted label over a large value, with an optional
    ``delta`` line tinted by the H4 ``success`` (up) or ``error`` (down) status
    role depending on ``delta_up`` — the canonical "▲ +12%" / "▼ -3%" trend cue.

    Attributes:
        label: The metric's caption (muted).
        value: The metric's value (large, prominent).
        delta: An optional trend line (e.g. ``"+12%"``); ``None`` hides it.
        delta_up: Whether the delta is positive (success-tinted) or negative
            (error-tinted).
        theme: The design-system theme whose tokens supply colors and spacing.
    """

    default_key: ClassVar[str] = "stat"

    label: str = Field(default="", description="The metric's caption (muted).")
    value: str = Field(default="", description="The metric's value (prominent).")
    delta: str | None = Field(
        default=None, description='An optional trend line (e.g. ``"+12%"``).'
    )
    delta_up: bool = Field(
        default=True,
        description="Whether the delta is positive (success) or negative (error).",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme whose tokens supply colors and spacing.",
    )

    def render(self) -> Widget:
        """Lower the stat into a primitive column.

        Returns:
            A ``Column`` of the muted label, the prominent value and an optional
            status-tinted delta.
        """
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        on_surface = self.theme.color(ColorRole.ON_SURFACE)
        children: list[Widget] = [
            Text(
                content=self.label,
                style=Style(color=muted, font_size=13.0),
                key=self.child_key("label"),
            ),
            Text(
                content=self.value,
                style=Style(
                    color=on_surface,
                    font_size=28.0,
                    font_weight=FontWeight.BOLD,
                ),
                key=self.child_key("value"),
            ),
        ]
        if self.delta is not None:
            delta_color = self.theme.color(
                ColorRole.SUCCESS if self.delta_up else ColorRole.ERROR
            )
            arrow = "▲" if self.delta_up else "▼"
            children.append(
                Text(
                    content=f"{arrow} {self.delta}",
                    style=Style(
                        color=delta_color,
                        font_size=13.0,
                        font_weight=FontWeight.MEDIUM,
                    ),
                    key=self.child_key("delta"),
                )
            )
        default = Style(gap=self.theme.space("xs"))
        return Column(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=children,
            semantics=self.semantics,
        )


def _no_steps() -> list[str]:
    """Provide a fresh, typed empty step-label list for default factories.

    Returns:
        A new empty list of strings.
    """
    return []


class ProgressStepper(Component):
    """A horizontal wizard / progress stepper showing labelled, numbered steps.

    Lays out the steps in a row: each step is a small numbered circle (a filled
    accent disc for done/active steps, a muted outline for pending ones) above its
    label, joined by connector rules. The colors are theme-driven: done/active
    steps read the ``color_scheme`` role; pending steps read the muted
    ``ON_SURFACE_VARIANT`` role. Named ``ProgressStepper`` to avoid colliding with
    the numeric :class:`~tempest_core.components.Stepper` (a +/- number spinner).

    Attributes:
        steps: The step labels, in order.
        current: The index of the active step (steps before it read as done).
        color_scheme: The Material 3 role family the done/active steps paint with.
        theme: The design-system theme resolving the step colors and spacing.
    """

    default_key: ClassVar[str] = "progress-stepper"

    steps: list[str] = Field(
        description="The step labels, in order.", default_factory=_no_steps
    )
    current: int = Field(
        default=0, description="The index of the active step (earlier steps = done)."
    )
    color_scheme: str = Field(
        default="primary",
        description="The Material 3 role family the done/active steps paint with.",
    )
    theme: Theme = Field(
        default_factory=current_theme,
        description="The design-system theme resolving the step colors and spacing.",
    )

    def _step_cell(self, index: int, label: str) -> Widget:
        """Build one step cell: a numbered circle above its label.

        Args:
            index: The zero-based step position.
            label: The step's caption.

        Returns:
            A ``Column`` of the numbered disc and the label.
        """
        done_or_active = index <= self.current
        accent = self.theme.color(self.color_scheme)
        on_accent = self.theme.color(f"on_{self.color_scheme}")
        muted = self.theme.color(ColorRole.ON_SURFACE_VARIANT)
        outline = self.theme.color(ColorRole.OUTLINE)
        if done_or_active:
            disc_style = Style(
                width=28.0,
                height=28.0,
                radius=14.0,
                background=accent,
                color=on_accent,
                align=AlignItems.CENTER,
                text_align=TextAlign.CENTER,
                font_weight=FontWeight.BOLD,
                font_size=13.0,
            )
            label_color = self.theme.color(ColorRole.ON_SURFACE)
        else:
            disc_style = Style(
                width=28.0,
                height=28.0,
                radius=14.0,
                border=Border(width=1.0, color=outline),
                color=muted,
                align=AlignItems.CENTER,
                text_align=TextAlign.CENTER,
                font_size=13.0,
            )
            label_color = muted
        return Column(
            key=self.child_key(f"step-{index}"),
            style=Style(gap=self.theme.space("xs"), align=AlignItems.CENTER),
            children=[
                Text(
                    content=str(index + 1),
                    style=disc_style,
                    key=self.child_key(f"step-disc-{index}"),
                ),
                Text(
                    content=label,
                    style=Style(color=label_color, font_size=12.0),
                    key=self.child_key(f"step-label-{index}"),
                ),
            ],
        )

    def render(self) -> Widget:
        """Lower the stepper into a primitive row of step cells.

        Returns:
            A ``Row`` of step cells joined by flexible connector spaces.

        Note:
            Each gap between two cells carries a growing connector rule, tinted
            by whether the step it leads into is already done.
        """
        children: list[Widget] = []
        for index, label in enumerate(self.steps):
            if index > 0:
                done = index <= self.current
                color = (
                    self.theme.color(self.color_scheme)
                    if done
                    else self.theme.color(ColorRole.OUTLINE_VARIANT)
                )
                children.append(
                    Text(
                        content="",
                        style=Style(grow=1.0, height=2.0, background=color),
                        key=self.child_key(f"step-conn-{index}"),
                    )
                )
            children.append(self._step_cell(index, label))
        default = Style(
            gap=self.theme.space("xs"),
            align=AlignItems.CENTER,
        )
        return Row(
            key=self.base_key,
            style=merge_style(default, self.style),
            children=children,
            semantics=self.semantics,
        )
