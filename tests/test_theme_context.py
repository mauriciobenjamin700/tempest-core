"""The app's theme, reaching the components the view builds.

``App.theme`` existed and was inert. Every themed component declared
``theme`` with a baseline default factory, ``build`` knew nothing about the
app, and nothing connected the two — an app that generated a brand palette
with :meth:`Theme.from_seed` still rendered Material-purple buttons, because
a component resolves its colors at construction and writes them into its
style. Measured in a real Mode B app: ``--tw-primary`` was the brand slate
on ``:root`` while the button computed ``rgb(88, 71, 133)``.

The fix is a context variable installed around the view call, which is when
components are constructed. These pin that it reaches them, that it does not
leak, and that nothing changes for a widget built outside a build.
"""

from __future__ import annotations

from tempest_core import App, Column, Theme, ThemeMode, Widget
from tempest_core.components.cards import Card
from tempest_core.style import Color
from tempest_core.theme import current_theme, use_theme

SEED: Color = Color(r=39, g=58, b=79)
"""A slate blue, so a themed palette is unmistakably not the baseline."""


def _brand() -> Theme:
    """Build the palette an app would generate from its brand colour.

    Returns:
        Theme: A seeded theme, pinned to light so the assertions are stable.
    """
    return Theme.from_seed(SEED, mode=ThemeMode.LIGHT)


class TestWhatAComponentDefaultsTo:
    """Construction time is what decides a component's palette."""

    def test_outside_a_build_the_baseline_answers(self) -> None:
        """A widget in a test, a script or a REPL keeps working."""
        assert current_theme().tokens.schemes.light == Theme().tokens.schemes.light

    def test_inside_use_theme_the_app_palette_answers(self) -> None:
        brand = _brand()

        with use_theme(brand):
            assert Card(children=[]).theme is brand

    def test_the_theme_does_not_leak_out_of_the_block(self) -> None:
        """A palette that outlived its build would tint the next app."""
        with use_theme(_brand()):
            pass

        assert Card(children=[]).theme.tokens.schemes.light.primary != Color(
            r=72,
            g=100,
            b=132,
        )

    def test_a_raising_view_still_resets_it(self) -> None:
        """The token is reset in a finally, so a crash cannot poison the next."""
        try:
            with use_theme(_brand()):
                raise RuntimeError("a view that failed")
        except RuntimeError:
            pass

        assert current_theme().tokens.schemes.light == Theme().tokens.schemes.light


class TestWhatTheAppBuildsWith:
    """The end to end that was broken: App.theme reaching the tree."""

    def test_a_component_built_by_the_view_wears_the_app_theme(self) -> None:
        seen: list[Color] = []

        def view(app: App[dict[str, str]]) -> Widget:
            """Build a card without passing any theme."""
            seen.append(Card(children=[]).theme.tokens.schemes.light.primary)
            return Column(children=[])

        brand = _brand()
        App(state={}, view=view, apply_patches=lambda patches: None).start()
        baseline_primary = seen[-1]
        App(
            state={},
            view=view,
            apply_patches=lambda patches: None,
            theme=brand,
        ).start()

        assert seen[-1] == brand.tokens.schemes.light.primary
        assert baseline_primary != seen[-1]

    def test_an_explicit_theme_still_wins(self) -> None:
        """Passing one by hand must keep overriding the app's."""
        pinned = Theme.from_seed(Color(r=120, g=20, b=20), mode=ThemeMode.LIGHT)
        seen: list[Theme] = []

        def view(app: App[dict[str, str]]) -> Widget:
            """Build a card that names its own theme."""
            seen.append(Card(children=[], theme=pinned).theme)
            return Column(children=[])

        App(
            state={},
            view=view,
            apply_patches=lambda patches: None,
            theme=_brand(),
        ).start()

        assert seen[-1] is pinned
