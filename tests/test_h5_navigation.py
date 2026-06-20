"""Tests for the H5 styled navigation kit (Trilho H, phase H5).

H5 is a **skin pass**: it migrates the navigation components' hard-coded
``components/base.py`` hexes (``SURFACE`` / ``ACCENT`` / ``MUTED`` / ``ON_SURFACE``
/ …) to Material 3 theme tokens, reusing the **existing** variant resolvers
(``resolve_surface_variant`` H3, ``resolve_badge_variant`` H4, ``resolve_variant``
H1, ``resolve_field_variant`` H2) — adding NO new resolver, enum or ``Style``
field. These tests pin: each skinned component resolves theme colors (not the old
hexes); the new ``Tabs`` strip + underline indicator; ``NavBar``/``Tabs`` active
vs inactive item styles; ``Burger`` lowering to an icon button; ``SearchBar``
field resolution; full backward-compatibility of the old call sites and explicit
``style=``; and the hard constraint ``len(Style.model_fields) == 41``.
"""

from __future__ import annotations

from tempest_core import (
    Style,
    Tabs,
    Theme,
    build,
)
from tempest_core.components import (
    AppBar,
    Breadcrumb,
    Burger,
    CollapsingAppBar,
    Drawer,
    Footer,
    Header,
    NavBar,
    Scaffold,
    SearchBar,
    Sidebar,
)
from tempest_core.components.base import (
    ACCENT,
    BACKGROUND,
    MUTED,
    ON_MUTED,
    ON_SURFACE,
    SURFACE,
)
from tempest_core.core import Node
from tempest_core.style import Border, Color, SideBorder
from tempest_core.tokens import ColorRole

THEME = Theme()

#: The legacy hard-coded palette H5 migrated away from. A skinned component must
#: not paint any of these literal hexes anymore (its colors come from the theme).
_LEGACY_HEXES: frozenset[Color] = frozenset(
    {BACKGROUND, SURFACE, ACCENT, MUTED, ON_SURFACE, ON_MUTED}
)


def _node_style(node: Node) -> Style:
    """Return a node's resolved ``Style`` prop.

    Args:
        node: The built IR node.

    Returns:
        The node's ``style`` prop (must be present for a skinned container).
    """
    style = node.props.get("style")
    assert isinstance(style, Style)
    return style


def _colors(style: Style) -> list[Color]:
    """Collect every concrete ``Color`` value carried by a style.

    Args:
        style: The style to scan.

    Returns:
        The list of ``Color`` values found across the color-bearing fields.
    """
    found: list[Color] = []
    for name in ("background", "color"):
        value = getattr(style, name)
        if isinstance(value, Color):
            found.append(value)
    border = style.border
    if isinstance(border, Border) and isinstance(border.color, Color):
        found.append(border.color)
    if isinstance(border, SideBorder):
        for side in (border.top, border.right, border.bottom, border.left):
            if isinstance(side, Border) and isinstance(side.color, Color):
                found.append(side.color)
    return found


# --------------------------------------------------------------------------- #
# Exports
# --------------------------------------------------------------------------- #


def test_tabs_importable_from_root_and_components() -> None:
    """The new ``Tabs`` component is importable from both surfaces."""
    from tempest_core import Tabs as RootTabs
    from tempest_core.components import Tabs as ComponentsTabs

    assert RootTabs is Tabs
    assert ComponentsTabs is Tabs


# --------------------------------------------------------------------------- #
# Hard constraint — no new Style field
# --------------------------------------------------------------------------- #


def test_no_style_field_added() -> None:
    """H5 adds NO new ``Style`` field — the count stays pinned at 41."""
    assert len(Style.model_fields) == 41


# --------------------------------------------------------------------------- #
# AppBar / Footer / CollapsingAppBar — surface resolver
# --------------------------------------------------------------------------- #


def test_appbar_resolves_theme_surface_not_legacy_hex() -> None:
    """An ``AppBar`` fills with the theme surface, never the legacy hex."""
    node = build(AppBar(title="Home"))
    style = _node_style(node)
    assert style.background == THEME.color(ColorRole.SURFACE)
    # The title inherits the resolved surface content color.
    titles = [c for c in node.children if c.key == "appbar-title"]
    assert titles
    assert titles[0].props["style"].color == THEME.color(ColorRole.ON_SURFACE)


def test_appbar_carries_elevation_shadow_when_elevated() -> None:
    """An elevated ``AppBar`` carries an elevation shadow (existing field)."""
    node = build(AppBar(title="X"))
    assert _node_style(node).shadow is not None


def test_appbar_color_scheme_tints_surface() -> None:
    """A tinted ``color_scheme`` paints the container role, not the plain surface."""
    node = build(AppBar(title="X", color_scheme="primary"))
    style = _node_style(node)
    assert style.background == THEME.color(ColorRole.PRIMARY_CONTAINER)


def test_footer_resolves_theme_surface() -> None:
    """A ``Footer`` fills with the resolved theme surface."""
    node = build(Footer(children=[]))
    style = _node_style(node)
    assert style.background == THEME.color(ColorRole.SURFACE)


def test_collapsing_app_bar_resolves_surface_and_keeps_collapse() -> None:
    """The collapsing bar recolors via the surface resolver but keeps the math."""
    expanded = build(CollapsingAppBar(title="T", scroll_offset=0.0))
    collapsed = build(CollapsingAppBar(title="T", scroll_offset=10_000.0))
    es = _node_style(expanded)
    cs = _node_style(collapsed)
    assert es.background == THEME.color(ColorRole.SURFACE)
    # Height collapse derivation is unchanged: expanded 200 -> collapsed 56.
    assert es.height == 200.0
    assert cs.height == 56.0


def test_collapsing_app_bar_legacy_background_still_wins() -> None:
    """The legacy ``background`` escape hatch overrides the resolved surface."""
    custom = Color.from_hex("#123456")
    node = build(CollapsingAppBar(title="T", background=custom))
    assert _node_style(node).background == custom


# --------------------------------------------------------------------------- #
# Header — tokens only
# --------------------------------------------------------------------------- #


def test_header_uses_theme_tokens_not_legacy_hexes() -> None:
    """The header band + title + subtitle read theme roles, not legacy hexes."""
    node = build(Header(title="Title", subtitle="Sub"))
    band = _node_style(node)
    assert band.background == THEME.color(ColorRole.SURFACE_VARIANT)
    title = next(c for c in node.children if c.key == "header-title")
    subtitle = next(c for c in node.children if c.key == "header-subtitle")
    assert title.props["style"].color == THEME.color(ColorRole.ON_SURFACE)
    assert subtitle.props["style"].color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


def test_header_color_scheme_tints_title() -> None:
    """A ``color_scheme`` tints the header title with the role color."""
    node = build(Header(title="Title", color_scheme="primary"))
    title = next(c for c in node.children if c.key == "header-title")
    assert title.props["style"].color == THEME.color("primary")


# --------------------------------------------------------------------------- #
# Sidebar / Drawer — surface resolver
# --------------------------------------------------------------------------- #


def test_sidebar_resolves_surface_keeps_width() -> None:
    """A ``Sidebar`` resolves the surface and keeps its fixed width."""
    node = build(Sidebar(children=[], width=300.0))
    style = _node_style(node)
    assert style.background == THEME.color(ColorRole.SURFACE)
    assert style.width == 300.0


def test_drawer_open_resolves_surface() -> None:
    """An open ``Drawer`` resolves the panel surface and keeps its width."""
    node = build(Drawer(open=True, children=[], width=320.0))
    style = _node_style(node)
    assert style.background == THEME.color(ColorRole.SURFACE)
    assert style.width == 320.0


def test_drawer_closed_is_empty_box() -> None:
    """A closed ``Drawer`` collapses to an empty container (unchanged)."""
    node = build(Drawer(open=False, children=[]))
    assert node.type == "Container"
    assert not node.children


# --------------------------------------------------------------------------- #
# Scaffold — background token
# --------------------------------------------------------------------------- #


def test_scaffold_background_is_theme_background() -> None:
    """The ``Scaffold`` frame fills with the theme ``BACKGROUND`` role."""
    node = build(Scaffold())
    assert _node_style(node).background == THEME.color(ColorRole.BACKGROUND)


# --------------------------------------------------------------------------- #
# NavBar — active accent pill vs inactive ghost
# --------------------------------------------------------------------------- #


def test_navbar_surface_is_theme_surface() -> None:
    """The ``NavBar`` strip fills with the resolved theme surface."""
    node = build(NavBar(items=["A"], active=0, on_select=lambda i: None))
    assert _node_style(node).background == THEME.color(ColorRole.SURFACE_VARIANT)


def test_navbar_active_item_is_accent_pill() -> None:
    """The active ``NavBar`` item is a SOLID accent pill in the role color."""
    node = build(NavBar(items=["A", "B"], active=0, on_select=lambda i: None))
    active = next(c for c in node.children if c.key == "nav-0")
    assert active.props["style"].background == THEME.color(ColorRole.PRIMARY)
    assert active.props["style"].color == THEME.color(ColorRole.ON_PRIMARY)


def test_navbar_inactive_item_is_ghost() -> None:
    """An inactive ``NavBar`` item is a GHOST (transparent-ish surface) treatment."""
    node = build(NavBar(items=["A", "B"], active=0, on_select=lambda i: None))
    inactive = next(c for c in node.children if c.key == "nav-1")
    # GHOST sits on the surface; it is NOT the accent fill.
    assert inactive.props["style"].background == THEME.color(ColorRole.SURFACE)
    assert inactive.props["style"].background != THEME.color(ColorRole.PRIMARY)


def test_navbar_color_scheme_is_honored() -> None:
    """A ``NavBar`` color_scheme paints the active pill with that role family."""
    node = build(
        NavBar(items=["A"], active=0, on_select=lambda i: None, color_scheme="error")
    )
    active = next(c for c in node.children if c.key == "nav-0")
    assert active.props["style"].background == THEME.color(ColorRole.ERROR)


def test_navbar_does_not_use_legacy_hexes() -> None:
    """No skinned ``NavBar`` node paints a legacy hard-coded hex."""
    node = build(NavBar(items=["A", "B"], active=0, on_select=lambda i: None))
    for n in (node, *node.children):
        style = n.props.get("style")
        if isinstance(style, Style):
            for c in _colors(style):
                assert c not in _LEGACY_HEXES


def test_navbar_select_handler_fires() -> None:
    """Tapping a ``NavBar`` item invokes ``on_select`` with its index."""
    seen: list[int] = []
    node = build(NavBar(items=["A", "B"], active=0, on_select=seen.append))
    handler = node.children[1].props["on_click"]
    handler()
    assert seen == [1]


# --------------------------------------------------------------------------- #
# Tabs — strip + underline indicator
# --------------------------------------------------------------------------- #


def test_tabs_lowers_to_row_of_buttons() -> None:
    """A ``Tabs`` strip lowers to a ``Row`` of one button per tab."""
    node = build(Tabs(tabs=["One", "Two", "Three"], active=0, on_select=lambda i: None))
    assert node.type == "Row"
    assert [c.type for c in node.children] == ["Button", "Button", "Button"]
    assert [c.key for c in node.children] == ["tab-0", "tab-1", "tab-2"]


def test_tabs_active_has_accent_underline() -> None:
    """The active tab carries a bottom ``SideBorder`` underline in the accent role."""
    node = build(Tabs(tabs=["One", "Two"], active=1, on_select=lambda i: None))
    active = next(c for c in node.children if c.key == "tab-1")
    border = active.props["style"].border
    assert isinstance(border, SideBorder)
    assert border.bottom is not None
    assert border.bottom.color == THEME.color("primary")
    assert border.top is None and border.left is None and border.right is None
    # The active tab text takes the accent role color.
    assert active.props["style"].color == THEME.color(ColorRole.PRIMARY)


def test_tabs_inactive_has_no_underline() -> None:
    """An inactive tab has no underline border and a neutral (non-accent) color."""
    node = build(Tabs(tabs=["One", "Two"], active=1, on_select=lambda i: None))
    inactive = next(c for c in node.children if c.key == "tab-0")
    assert inactive.props["style"].border is None
    assert inactive.props["style"].color != THEME.color(ColorRole.PRIMARY)


def test_tabs_color_scheme_drives_underline() -> None:
    """The ``Tabs`` color_scheme drives the underline + active color."""
    node = build(
        Tabs(tabs=["One"], active=0, on_select=lambda i: None, color_scheme="secondary")
    )
    active = next(c for c in node.children if c.key == "tab-0")
    border = active.props["style"].border
    assert isinstance(border, SideBorder)
    assert border.bottom is not None
    assert border.bottom.color == THEME.color("secondary")


def test_tabs_select_handler_fires() -> None:
    """Tapping a tab invokes ``on_select`` with its index."""
    seen: list[int] = []
    node = build(Tabs(tabs=["One", "Two"], active=0, on_select=seen.append))
    node.children[1].props["on_click"]()
    assert seen == [1]


def test_tabs_is_a_component_not_a_leaf() -> None:
    """``Tabs`` is a Component (lowers to primitives), not an IR leaf widget."""
    from tempest_core.core.introspection import WIDGET_TYPES

    assert Tabs not in WIDGET_TYPES
    assert "Tabs" not in {w.__name__ for w in WIDGET_TYPES}


# --------------------------------------------------------------------------- #
# SearchBar — field resolution + icon clear button
# --------------------------------------------------------------------------- #


def test_searchbar_inner_input_resolves_field_style() -> None:
    """The ``SearchBar`` inner input resolves a focus-led field style + grows."""
    node = build(SearchBar(value="", on_change=lambda e: None))
    inp = next(c for c in node.children if c.key == "search-input")
    style = inp.props["style"]
    assert style.grow == 1.0
    # The typed text content is on_surface (the field resolver's content color).
    assert style.color == THEME.color(ColorRole.ON_SURFACE)


def test_searchbar_pill_resolves_surface() -> None:
    """The outer ``SearchBar`` pill carries a resolved surface fill."""
    node = build(SearchBar(value="", on_change=lambda e: None))
    assert _node_style(node).background == THEME.color(ColorRole.SURFACE_VARIANT)


def test_searchbar_clear_button_is_icon_button() -> None:
    """The clear button lowers to an ``IconButton`` when set and value non-empty."""
    node = build(SearchBar(value="q", on_change=lambda e: None, on_clear=lambda: None))
    clear = next(c for c in node.children if c.key == "search-clear")
    assert clear.type == "IconButton"


def test_searchbar_clear_hidden_when_empty() -> None:
    """The clear button is absent when the field is empty."""
    node = build(SearchBar(value="", on_change=lambda e: None, on_clear=lambda: None))
    assert all(c.key != "search-clear" for c in node.children)


def test_searchbar_does_not_use_legacy_hexes() -> None:
    """No skinned ``SearchBar`` node paints a legacy hard-coded hex."""
    node = build(SearchBar(value="q", on_change=lambda e: None, on_clear=lambda: None))
    for n in (node, *node.children):
        style = n.props.get("style")
        if isinstance(style, Style):
            for c in _colors(style):
                assert c not in _LEGACY_HEXES


# --------------------------------------------------------------------------- #
# Burger — icon button
# --------------------------------------------------------------------------- #


def test_burger_lowers_to_icon_button() -> None:
    """A ``Burger`` lowers to an ``IconButton`` showing the menu icon."""
    node = build(Burger(on_click=lambda: None))
    assert node.type == "IconButton"
    assert node.props["icon"] == "menu"


def test_burger_click_handler_fires() -> None:
    """Tapping a ``Burger`` invokes its ``on_click``."""
    seen: list[bool] = []
    node = build(Burger(on_click=lambda: seen.append(True)))
    node.props["on_click"]()
    assert seen == [True]


def test_burger_glyph_fallback_still_accepted() -> None:
    """The deprecated ``glyph`` kwarg is still accepted (backward-compat)."""
    node = build(Burger(on_click=lambda: None, glyph="X"))
    assert node.type == "IconButton"


# --------------------------------------------------------------------------- #
# Breadcrumb — theme roles + link variant
# --------------------------------------------------------------------------- #


def test_breadcrumb_current_and_separator_use_theme_roles() -> None:
    """The current crumb + separators read theme roles, not legacy hexes."""
    node = build(Breadcrumb(items=["Home", "Sub", "Page"]))
    last = next(c for c in node.children if c.key == "crumb-2")
    assert last.props["style"].color == THEME.color(ColorRole.ON_SURFACE)
    sep = next(c for c in node.children if (c.key or "").startswith("sep-"))
    assert sep.props["style"].color == THEME.color(ColorRole.ON_SURFACE_VARIANT)


def test_breadcrumb_link_crumb_uses_variant_resolver() -> None:
    """A tappable crumb resolves a LINK style in the color_scheme role."""
    node = build(
        Breadcrumb(
            items=["Home", "Page"], on_select=lambda i: None, color_scheme="info"
        )
    )
    link = next(c for c in node.children if c.key == "crumb-0")
    assert link.type == "Button"
    assert link.props["style"].color == THEME.color("info")


def test_breadcrumb_select_fires_for_non_last() -> None:
    """Tapping a non-current crumb invokes ``on_select`` with its index."""
    seen: list[int] = []
    node = build(Breadcrumb(items=["Home", "Page"], on_select=seen.append))
    link = next(c for c in node.children if c.key == "crumb-0")
    link.props["on_click"]()
    assert seen == [0]


# --------------------------------------------------------------------------- #
# Backward compatibility — old call sites + explicit style
# --------------------------------------------------------------------------- #


def test_old_call_sites_still_build() -> None:
    """Every navigation component still accepts its pre-H5 call shape."""
    assert build(AppBar(title="A")).type == "Row"
    assert build(Footer(children=[])).type == "Row"
    assert build(Header(title="H")).type == "Column"
    assert build(Sidebar(children=[])).type == "Column"
    assert build(Scaffold()).type == "Column"
    assert build(NavBar(items=["A"], active=0, on_select=lambda i: None)).type == "Row"
    assert build(Breadcrumb(items=["A"])).type == "Row"
    assert build(Burger(on_click=lambda: None)).type == "IconButton"
    assert build(Drawer(open=True, children=[])).type == "Column"


def test_explicit_style_overrides_resolved() -> None:
    """An explicit ``style=`` wins over the resolved surface (its set fields)."""
    custom = Color.from_hex("#abcdef")
    node = build(AppBar(title="A", style=Style(background=custom)))
    assert _node_style(node).background == custom


def test_explicit_style_overrides_navbar_surface() -> None:
    """An explicit ``style=`` on ``NavBar`` overrides the resolved strip fill."""
    custom = Color.from_hex("#fedcba")
    node = build(
        NavBar(
            items=["A"],
            active=0,
            on_select=lambda i: None,
            style=Style(background=custom),
        )
    )
    assert _node_style(node).background == custom
