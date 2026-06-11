"""tempest-core — the renderer-agnostic core shared across the tempest stack.

The engine behind both tempestroid (native renderers) and tempestweb (DOM): the
IR, reconciler, state model, style model, widgets, components and the
cross-cutting helpers (animation, i18n, navigation, theme, validators). It carries
no platform-coupled code (no Qt, no JNI, no Android, no DOM) so it imports cleanly
under CPython, Pyodide and a headless server.

This is the single source of truth — consumers depend on the published package and
import from here (``from tempest_core import App, Column, build, diff``) rather than
vendoring a copy.
"""

from tempest_core.animation import AnimationController
from tempest_core.core import (
    App,
    Insert,
    Node,
    OverlayEntry,
    Patch,
    Path,
    Remove,
    Reorder,
    Replace,
    Scene,
    Update,
    build,
    build_scene,
    diff,
    diff_scene,
    event_catalog,
    introspect,
    widget_catalog,
)
from tempest_core.i18n import Locale, t, translate
from tempest_core.navigation import NavStack, Route, routes_from_path
from tempest_core.style import Style
from tempest_core.theme import MediaQueryData, Theme, ThemeMode
from tempest_core.widgets import (
    Button,
    Column,
    Component,
    Container,
    Row,
    Text,
    Widget,
)

__all__ = [
    "AnimationController",
    "App",
    "Button",
    "Column",
    "Component",
    "Container",
    "Insert",
    "Locale",
    "MediaQueryData",
    "NavStack",
    "Node",
    "OverlayEntry",
    "Patch",
    "Path",
    "Remove",
    "Reorder",
    "Replace",
    "Route",
    "Row",
    "Scene",
    "Style",
    "Text",
    "Theme",
    "ThemeMode",
    "Update",
    "Widget",
    "build",
    "build_scene",
    "diff",
    "diff_scene",
    "event_catalog",
    "introspect",
    "routes_from_path",
    "t",
    "translate",
    "widget_catalog",
]
