"""Theme and media-query context for the app (phase E9).

A :class:`Theme` (dark/light mode + a small Material-like color palette) and the
:class:`MediaQueryData` (viewport size, density, text-scale, platform dark mode,
orientation) are **input context** the ``view(app)`` reads when it builds the
tree — not nodes in the tree. They never break the "widget tree is the IR"
invariant: the reconciler still diffs a plain widget tree; the theme/media just
change *which* tree the view produces.

Both models are frozen so the runtime can hold them as immutable snapshots and
swap them wholesale (``App.set_theme`` / ``App._update_media``) rather than
mutating in place.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum

from pydantic import ConfigDict, Field

from tempest_core._model import _CoreModel
from tempest_core.style import Color, Curve, Style
from tempest_core.tokens import (
    ColorRole,
    ColorScheme,
    MotionScale,
    TokenRef,
    TokenSet,
    TypographyToken,
    default_tokens,
)

__all__ = [
    "ThemeMode",
    "Theme",
    "MediaQueryData",
    "current_theme",
    "use_theme",
]


_current: ContextVar[Theme | None] = ContextVar("tempest_core_theme", default=None)
"""The theme the view being built runs under, or ``None`` outside a build."""


def current_theme() -> Theme:
    """Return the theme of the view currently building.

    Every themed component declares ``theme`` with this as its default
    factory, which is what makes an app's palette reach the tree without a
    single call site passing it down. The factory runs while the widget is
    constructed — that is, while the view runs — so :meth:`use_theme` only
    has to be installed around the view call.

    Outside a build there is no app to ask, so this answers the Material
    baseline. That keeps a widget constructed in a test, a script or a REPL
    working exactly as before.

    Returns:
        Theme: The active theme, or a baseline one outside a build.
    """
    active = _current.get()
    return Theme() if active is None else active


@contextmanager
def use_theme(theme: Theme) -> Iterator[None]:
    """Run a block with ``theme`` as the one components default to.

    Installed by :meth:`~tempest_core.App._build` around the view call. The
    variable is a :class:`~contextvars.ContextVar`, so concurrent apps —
    two server sessions building at the same time — never see each other's
    palette, and the token is reset on the way out even if the view raises.

    Args:
        theme (Theme): The palette for the tree about to be built.

    Yields:
        None: Control, with the theme installed.
    """
    token = _current.set(theme)
    try:
        yield
    finally:
        _current.reset(token)


class ThemeMode(StrEnum):
    """The active color-scheme mode of the application.

    ``SYSTEM`` defers to the platform's current setting (read from
    :attr:`MediaQueryData.platform_dark_mode`); ``LIGHT`` / ``DARK`` force the
    respective scheme regardless of the OS.

    Attributes:
        LIGHT: Force the light color scheme always, ignoring the OS setting.
        DARK: Force the dark color scheme always, ignoring the OS setting.
        SYSTEM: Follow the platform's current scheme, resolving against
            :attr:`MediaQueryData.platform_dark_mode` at build time.
    """

    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


class Theme(_CoreModel):
    """An immutable theme: the active mode plus a small color palette.

    The palette mirrors a subset of Material's color roles. Every legacy color
    is optional: ``None`` lets the renderer fall back to its own default scheme.
    The ``view`` reads :attr:`mode` (resolving ``SYSTEM`` against the media
    query) to decide which colors to apply to the tree it builds.

    Beyond the legacy flat colors, a theme carries a full Material 3
    :class:`~tempest_core.tokens.TokenSet` (color schemes + spacing/shape/
    typography/elevation/motion scales). A researcher seeds a brand color with
    :meth:`from_seed` to get a complete M3 palette, then components (or the
    ``view``) read tokens via :meth:`color`/:meth:`space`/:meth:`radius`/… or
    resolve a :class:`~tempest_core.tokens.TokenRef` carried in a ``Style`` via
    :meth:`resolve_ref`. The legacy flat colors remain so existing apps keep
    working unchanged — tokens are additive.

    Attributes:
        mode: The active color-scheme mode.
        tokens: The Material 3 token set (color schemes + scales). Defaults to
            the baseline M3 token set.
        primary: The legacy primary brand color (optional override).
        secondary: The legacy secondary brand color (optional override).
        background: The legacy screen background color (optional override).
        surface: The legacy raised-surface color (optional override).
        on_primary: The legacy color of content drawn on ``primary``.
        on_background: The legacy color of content drawn on ``background``.
        error: The legacy error color (optional override).

    Methods:
        from_seed: Build a theme from a brand seed color (classmethod).
        is_dark: Resolve whether the theme renders dark, given the platform
            setting (resolves ``SYSTEM`` against the media query).
        scheme: Resolve the active :class:`~tempest_core.tokens.ColorScheme`.
        color: Resolve a color role to a concrete color.
        space: Resolve a spacing step to its pixel value.
        radius: Resolve a radius step to its pixel value.
        typography: Resolve a typography role to its token.
        elevation: Resolve an elevation level to its dp value.
        resolve_ref: Resolve a :class:`~tempest_core.tokens.TokenRef` to a
            concrete value.
    """

    model_config = ConfigDict(frozen=True)

    mode: ThemeMode = ThemeMode.SYSTEM
    tokens: TokenSet = Field(default_factory=default_tokens)
    primary: Color | None = None
    secondary: Color | None = None
    background: Color | None = None
    surface: Color | None = None
    on_primary: Color | None = None
    on_background: Color | None = None
    error: Color | None = None

    @classmethod
    def from_seed(
        cls,
        seed: Color,
        *,
        mode: ThemeMode = ThemeMode.SYSTEM,
        secondary_seed: Color | None = None,
        tertiary_seed: Color | None = None,
        error_seed: Color | None = None,
        success_seed: Color | None = None,
        warning_seed: Color | None = None,
        info_seed: Color | None = None,
    ) -> Theme:
        """Build a theme whose tokens are derived from a brand seed color.

        This is the researcher-facing entry point: seed a single brand color and
        get a complete Material 3 token set (light + dark schemes + the default
        scales). Override the secondary/tertiary/error key colors to hand-pick
        brand accents, or the H4 success/warning/info status seeds to retune the
        semantic status colors.

        Args:
            seed: The primary brand/key color.
            mode: The initial color-scheme mode.
            secondary_seed: Override key color for the secondary palette.
            tertiary_seed: Override key color for the tertiary palette.
            error_seed: Override key color for the error palette.
            success_seed: Override key color for the success status palette (H4).
            warning_seed: Override key color for the warning status palette (H4).
            info_seed: Override key color for the info status palette (H4).

        Returns:
            A theme carrying the seeded token set.
        """
        return cls(
            mode=mode,
            tokens=TokenSet.from_seed(
                seed,
                secondary_seed=secondary_seed,
                tertiary_seed=tertiary_seed,
                error_seed=error_seed,
                success_seed=success_seed,
                warning_seed=warning_seed,
                info_seed=info_seed,
            ),
        )

    def is_dark(self, *, platform_dark_mode: bool = False) -> bool:
        """Resolve whether the theme renders dark, given the platform setting.

        ``LIGHT`` / ``DARK`` are absolute; ``SYSTEM`` defers to the platform.

        Args:
            platform_dark_mode: The OS dark-mode flag (typically
                :attr:`MediaQueryData.platform_dark_mode`).

        Returns:
            ``True`` when the resolved scheme is dark.
        """
        if self.mode is ThemeMode.DARK:
            return True
        if self.mode is ThemeMode.LIGHT:
            return False
        return platform_dark_mode

    def scheme(self, *, platform_dark_mode: bool = False) -> ColorScheme:
        """Resolve the active color scheme for the current mode.

        Args:
            platform_dark_mode: The OS dark-mode flag, used to resolve
                ``SYSTEM`` mode.

        Returns:
            The light or dark color scheme matching the resolved mode.
        """
        return self.tokens.scheme(
            is_dark=self.is_dark(platform_dark_mode=platform_dark_mode)
        )

    def color(
        self, role: ColorRole | str, *, platform_dark_mode: bool = False
    ) -> Color:
        """Resolve a Material 3 color role to a concrete color.

        Args:
            role: The color role (a :class:`~tempest_core.tokens.ColorRole` or
                its string value).
            platform_dark_mode: The OS dark-mode flag, used to resolve
                ``SYSTEM`` mode.

        Returns:
            The concrete color for that role in the active scheme.
        """
        resolved = role if isinstance(role, ColorRole) else ColorRole(role)
        return self.scheme(platform_dark_mode=platform_dark_mode).role(resolved)

    def space(self, name: str) -> float:
        """Resolve a named spacing step to its pixel value.

        Args:
            name: The spacing step name (``"md"``, …).

        Returns:
            The spacing in logical pixels.
        """
        return self.tokens.spacing.get(name)

    def radius(self, name: str) -> float:
        """Resolve a named radius step to its pixel value.

        Args:
            name: The radius step name (``"lg"``, …).

        Returns:
            The radius in logical pixels.
        """
        return self.tokens.shape.get(name)

    def typography(self, name: str) -> TypographyToken:
        """Resolve a typography role to its token.

        Args:
            name: The type role name (``"body_medium"``, …).

        Returns:
            The typography token for that role.
        """
        return self.tokens.typography.get(name)

    def elevation(self, level: int) -> float:
        """Resolve an elevation level to its dp value.

        Args:
            level: The elevation level, 0-5.

        Returns:
            The elevation in dp.
        """
        return self.tokens.elevation.get(level)

    def resolve_ref(
        self, ref: TokenRef, *, platform_dark_mode: bool = False
    ) -> Color | float | TypographyToken | Curve | int:
        """Resolve a token reference to its concrete value.

        This is the seam that lets a ``Style`` field carry a
        :class:`~tempest_core.tokens.TokenRef` instead of a raw value: the
        renderer (or the variant resolver in H1) calls this to turn the
        reference into the concrete color/spacing/radius/type/elevation/motion
        value before the diff.

        Args:
            ref: The token reference to resolve.
            platform_dark_mode: The OS dark-mode flag, used to resolve a color
                reference against the active scheme.

        Returns:
            The concrete value: a :class:`~tempest_core.style.Color` for
            ``"color"``; a ``float`` for ``"space"``/``"radius"``/
            ``"elevation"``; a :class:`~tempest_core.tokens.TypographyToken` for
            ``"type"``; a :class:`~tempest_core.style.Curve` or ``int`` for
            ``"motion"`` (easing curve vs. duration in ms).

        Raises:
            ValueError: If ``ref.category`` is not a known token category.
            KeyError: If ``ref.name`` is not a defined token in its category.
        """
        if ref.category == "color":
            return self.color(ref.name, platform_dark_mode=platform_dark_mode)
        if ref.category == "space":
            return self.space(ref.name)
        if ref.category == "radius":
            return self.radius(ref.name)
        if ref.category == "type":
            return self.typography(ref.name)
        if ref.category == "elevation":
            level = int(ref.name.removeprefix("level"))
            return self.elevation(level)
        if ref.category == "motion":
            if ref.name not in MotionScale.model_fields:
                raise KeyError(f"unknown motion token: {ref.name!r}")
            value: Curve | int = getattr(self.tokens.motion, ref.name)
            return value
        raise ValueError(f"unknown token category: {ref.category!r}")

    def resolve_style(
        self,
        refs: dict[str, TokenRef],
        *,
        base: Style | None = None,
        platform_dark_mode: bool = False,
    ) -> Style:
        """Build a concrete ``Style`` by resolving token references per field.

        This is the **Style ⟷ token seam**: a component (or the H1 variant
        resolver) maps style fields to token references — e.g.
        ``{"background": TokenRef.color("primary"), "radius":
        TokenRef.radius("lg")}`` — and the theme resolves them against its
        tokens, producing a plain frozen ``Style`` the renderers consume
        unchanged. A ``"type"`` reference expands into the matching
        ``font_size``/``line_height``/``font_weight``/``letter_spacing`` fields.
        Raw ``Style`` values keep working — this is purely an additive way to
        source values from the theme.

        Args:
            refs: Mapping of ``Style`` field name to the token reference that
                supplies its value.
            base: An optional base style the resolved fields are layered on top
                of (via :meth:`Style.merge`); ``None`` starts from an empty
                style.
            platform_dark_mode: The OS dark-mode flag, used to resolve color
                references against the active scheme.

        Returns:
            A concrete, frozen ``Style`` with every referenced field resolved.

        Raises:
            ValueError: If a reference category is unknown.
            KeyError: If a referenced token name is not defined.
        """
        fields: dict[str, object] = {}
        for field, ref in refs.items():
            value = self.resolve_ref(ref, platform_dark_mode=platform_dark_mode)
            if isinstance(value, TypographyToken):
                fields["font_size"] = value.font_size
                fields["line_height"] = value.line_height
                fields["font_weight"] = value.font_weight
                fields["letter_spacing"] = value.letter_spacing
            else:
                fields[field] = value
        if base is None:
            return Style.model_validate(fields)
        # Layer the resolved fields over the base's already-set fields and
        # validate once, so nested value objects (Color, …) stay properly typed
        # (a plain ``Style.merge`` updates via ``model_copy`` without
        # re-validation, which would leave the resolved color as a raw dict).
        merged = base.model_dump(exclude_none=True)
        merged.update(fields)
        return Style.model_validate(merged)


class MediaQueryData(_CoreModel):
    """An immutable snapshot of the viewport / environment context.

    Read by the ``view`` to build responsively (e.g. switch a column to a row
    above a width breakpoint, scale text by the user's accessibility setting).
    The renderer keeps it current via ``App._update_media`` on resize / config
    change; it is never serialized as tree data — it is context, not a node.

    Attributes:
        width: The viewport width in logical pixels.
        height: The viewport height in logical pixels.
        device_pixel_ratio: The display density (physical / logical pixels).
        text_scale_factor: The user's font-scale accessibility multiplier.
        platform_dark_mode: Whether the OS is currently in dark mode.
        orientation: ``"portrait"`` or ``"landscape"``.
    """

    model_config = ConfigDict(frozen=True)

    width: float = 0.0
    height: float = 0.0
    device_pixel_ratio: float = 1.0
    text_scale_factor: float = 1.0
    platform_dark_mode: bool = False
    orientation: str = "portrait"
