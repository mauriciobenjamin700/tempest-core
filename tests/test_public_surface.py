"""The package root re-exports every public name its submodules declare.

This is the guard for a defect that cost a consumer 50 files. ``tempest_core``
re-exported about a third of its own surface, so ``from tempest_core import
Input`` raised ImportError and tempestweb had no choice but to import from
``tempest_core.widgets.inputs`` — against its own house rule of importing from the
package root. A partial root is a root that teaches people to bypass it, and
nothing failed when a new widget was added without a re-export.

Two things are checked, and both matter:

#. every ``__all__`` entry of every submodule appears in ``tempest_core.__all__``
   (the surface cannot shrink silently), and
#. every name in ``tempest_core.__all__`` is actually importable from the root and
   is the same object the submodule holds (the list cannot lie).

The third check is about type checkers rather than runtime: a re-export needs the
``from x import Y as Y`` form, or basedpyright and Pylance in strict mode report
"private import usage" at every consumer call site. ``__all__`` alone does not
silence that, so the source is inspected for the redundant form.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import tempest_core

PACKAGE_ROOT: Path = Path(tempest_core.__file__).resolve().parent


def _submodule_surface() -> dict[str, list[str]]:
    """Collect every public name each top-level submodule declares.

    Returns:
        ``{submodule: sorted(__all__)}``, skipping submodules that declare none.
    """
    surface: dict[str, list[str]] = {}
    for module in sorted(
        pkgutil.iter_modules(tempest_core.__path__), key=lambda m: m.name
    ):
        if module.name.startswith("_"):
            continue
        imported = importlib.import_module(f"tempest_core.{module.name}")
        names = getattr(imported, "__all__", None)
        if names:
            surface[module.name] = sorted(names)
    return surface


def test_every_submodule_name_is_re_exported() -> None:
    """A public name a submodule declares must be importable from the root."""
    exported = set(tempest_core.__all__)
    missing: list[str] = [
        f"{submodule}.{name}"
        for submodule, names in _submodule_surface().items()
        for name in names
        if name not in exported
    ]

    assert missing == [], (
        "these public names are not re-exported from tempest_core, so a consumer "
        f"has to import from the submodule: {missing}"
    )


def test_every_exported_name_resolves_to_its_submodule_object() -> None:
    """``__all__`` must not name anything the root cannot hand over."""
    broken: list[str] = []
    for name in tempest_core.__all__:
        if not hasattr(tempest_core, name):
            broken.append(f"{name} (listed, not importable)")
            continue
        root_object = getattr(tempest_core, name)
        owners = [
            submodule
            for submodule, names in _submodule_surface().items()
            if name in names
        ]
        for submodule in owners:
            imported = importlib.import_module(f"tempest_core.{submodule}")
            if getattr(imported, name) is not root_object:
                broken.append(f"{name} (root object differs from {submodule}'s)")

    assert broken == [], f"__all__ does not describe the root: {broken}"


def test_no_two_submodules_export_the_same_name() -> None:
    """A clash would make the root's meaning depend on import order.

    There is none today, and this is what keeps the flat re-export honest: if two
    submodules ever declare the same public name, the root has to make a choice
    explicitly instead of letting the last import win.
    """
    owners: dict[str, list[str]] = {}
    for submodule, names in _submodule_surface().items():
        for name in names:
            owners.setdefault(name, []).append(submodule)

    clashes = {name: mods for name, mods in owners.items() if len(mods) > 1}
    assert clashes == {}, f"the same public name comes from two submodules: {clashes}"


def test_re_exports_use_the_redundant_as_form() -> None:
    """Each re-export is ``Y as Y``, or strict type checkers flag consumers.

    Without it, basedpyright and Pylance report "private import usage" wherever a
    consumer imports the name — ``__all__`` does not silence that, and the two
    together are what make the root usable from a strict-mode codebase.
    """
    source = (PACKAGE_ROOT / "__init__.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    plain: list[str] = [
        f"{node.module}.{alias.name}"
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
        for alias in node.names
        if alias.asname != alias.name
    ]

    assert plain == [], (
        "these re-exports are missing the redundant `as` form, so strict type "
        f"checkers will flag every consumer that imports them: {plain}"
    )


def test_action_sheet_can_be_dismissed() -> None:
    """A modal sheet needs the dismissal contract its siblings have.

    ``ActionSheet`` is presented with a scrim, so a renderer reports the tap
    outside (and Escape) as a dismissal — and had nowhere to send it. A sheet
    whose actions do not close it then traps the reader, which got worse once a
    renderer started trapping focus inside modal overlays.
    """
    from tempest_core import ActionSheet, BottomSheet, Dialog

    for modal in (Dialog, BottomSheet, ActionSheet):
        assert "on_dismiss" in modal.model_fields, (
            f"{modal.__name__} cannot be dismissed"
        )
        assert "on_dismiss" in modal.event_schemas, (
            f"{modal.__name__} declares no event"
        )


def test_a_widget_refuses_a_field_it_does_not_declare() -> None:
    """An unknown keyword must raise, not vanish.

    The default (`extra="ignore"`) drops what it does not recognize, and for a
    widget tree that silence is expensive: ``Container(on_click=handler)`` built
    without complaint and the handler ceased to exist, so the click read as a
    renderer bug and the investigation started in the client's event delegation.
    A typo is the same failure with a worse disguise — ``Text(contnet="hi")``
    rendered an empty label.
    """
    import pytest
    from pydantic import ValidationError

    from tempest_core import Container, Text

    # Container declares no on_click; a clickable card wants Button or
    # GestureDetector, and the error is what says so.
    with pytest.raises(ValidationError, match="on_click"):
        Container(key="card", child=Text(content="x"), on_click=lambda: None)

    with pytest.raises(ValidationError, match="contnet"):
        Text(contnet="hi")

    # What a widget *does* declare still works, unchanged.
    assert Text(content="hi").content == "hi"
