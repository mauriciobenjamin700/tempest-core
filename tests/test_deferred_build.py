"""Pin the deferred model build, and prove deferring it changes nothing observable.

``_CoreModel`` sets ``defer_build=True`` so importing the core does not build a
validator and serializer for every one of its ~260 models up front. These tests
fix both halves of that contract: the build really is deferred (a regression
would silently put the import cost back), and a deferred model still validates,
serializes, describes itself and enforces its config exactly as before.
"""

from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import subprocess
import sys

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError

import tempest_core
from tempest_core import Column, Style, Text
from tempest_core._model import _CoreModel
from tempest_core.widgets.media import Canvas, Close, MoveTo


def _every_model() -> list[type[BaseModel]]:
    """Collect every Pydantic model the package defines.

    Returns:
        The model classes, deduplicated and sorted by qualified name.
    """
    found: dict[type[BaseModel], None] = {}
    for module in pkgutil.walk_packages(tempest_core.__path__, "tempest_core."):
        imported = importlib.import_module(module.name)
        for obj in vars(imported).values():
            if (
                inspect.isclass(obj)
                and issubclass(obj, BaseModel)
                and obj is not BaseModel
            ):
                found[obj] = None
    return sorted(found, key=lambda cls: f"{cls.__module__}.{cls.__name__}")


def test_the_base_defers_the_build() -> None:
    """The setting itself, so removing it fails loudly instead of slowing boot."""
    assert _CoreModel.model_config.get("defer_build") is True


def test_every_model_inherits_the_deferred_build() -> None:
    """A subclass declaring its own ``model_config`` keeps the base's setting.

    Pydantic merges a subclass's config over its bases', so ``frozen=True`` or
    ``extra="forbid"`` on a subclass must not reset ``defer_build``.
    """
    eager = [
        f"{cls.__module__}.{cls.__name__}"
        for cls in _every_model()
        if cls.model_config.get("defer_build") is not True
    ]
    assert eager == []


def test_importing_the_core_builds_no_widget() -> None:
    """A fresh interpreter imports the whole package without building a widget.

    Runs in a subprocess because the rest of the suite has already built most
    classes in this one. A handful of value models (``Color``, ``Edge``, …) are
    legitimately built at import, because a module-level constant instantiates
    them and construction is a first use; no widget is ever instantiated at
    import, so none may be built.
    """
    script = (
        "import importlib, inspect, pkgutil\n"
        "import tempest_core\n"
        "from tempest_core import Widget\n"
        "built = set()\n"
        "for m in pkgutil.walk_packages(tempest_core.__path__, 'tempest_core.'):\n"
        "    mod = importlib.import_module(m.name)\n"
        "    for obj in vars(mod).values():\n"
        "        if inspect.isclass(obj) and issubclass(obj, Widget) "
        "and obj.__pydantic_complete__:\n"
        "            built.add(obj.__qualname__)\n"
        "print(sorted(built))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "[]"


def test_a_fresh_widget_builds_on_first_validation() -> None:
    """A new subclass stays unbuilt until constructed, then is built and works."""

    class Badge(Text):
        """A throwaway widget subclass for this test."""

        level: int = Field(default=0, ge=0)

    assert Badge.__pydantic_complete__ is False
    assert list(Badge.model_fields)[-1] == "level"
    badge = Badge(content="new", level=2)
    assert Badge.__pydantic_complete__ is True
    assert badge.model_dump()["level"] == 2


def test_every_model_builds() -> None:
    """Every model's deferred build succeeds, so no forward ref fails at first use.

    With the build deferred, an unresolvable annotation would surface in an app
    the first time it touches the class; forcing the build here moves that
    failure into the suite.
    """
    failed: list[str] = []
    for cls in _every_model():
        try:
            cls.model_rebuild(force=True)
        except Exception as exc:
            failed.append(f"{cls.__module__}.{cls.__name__}: {exc}")
        else:
            if not cls.__pydantic_complete__:
                failed.append(f"{cls.__module__}.{cls.__name__}: incomplete")
    assert failed == []


def test_recursive_tree_validates_and_round_trips() -> None:
    """A recursive ``children: list[Widget]`` tree validates, dumps and re-validates."""
    tree = Column(children=[Text(content="a"), Column(children=[Text(content="b")])])
    inner = tree.children[1]
    assert isinstance(inner, Column)
    leaf = inner.children[0]
    assert isinstance(leaf, Text)
    assert json.loads(leaf.model_dump_json())["content"] == "b"
    dumped = tree.model_dump()
    assert len(dumped["children"]) == 2
    assert Column.model_validate(dumped).model_dump() == dumped


def test_discriminated_union_picks_the_member() -> None:
    """``DrawCommand`` still dispatches on ``kind`` when a dict crosses back."""
    canvas = Canvas.model_validate(
        {"commands": [{"kind": "move_to", "x": 1, "y": 2}, {"kind": "close"}]}
    )
    assert isinstance(canvas.commands[0], MoveTo)
    assert isinstance(canvas.commands[1], Close)
    with pytest.raises(ValidationError):
        Canvas.model_validate({"commands": [{"kind": "teleport"}]})


def test_json_schema_is_produced() -> None:
    """``model_json_schema`` builds a deferred model and describes its fields."""
    schema = Canvas.model_json_schema()
    assert "commands" in schema["properties"]
    assert "discriminator" in json.dumps(schema)


def test_config_still_applies() -> None:
    """``frozen``, ``extra="forbid"`` and ``allow_inf_nan=False`` are unchanged."""
    style = Style(width=10)
    with pytest.raises(ValidationError):
        style.width = 20  # type: ignore[misc]
    with pytest.raises(ValidationError):
        Text(content="hi", contnet="typo")  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Style(width=float("nan"))


def test_a_subclass_config_merges_with_the_deferred_build() -> None:
    """A model overriding ``model_config`` keeps both its own and the base's keys."""

    class Frozen(_CoreModel):
        """A throwaway frozen model for this test."""

        model_config = ConfigDict(frozen=True)

        value: float = 0.0

    assert Frozen.model_config.get("defer_build") is True
    assert Frozen.model_config.get("allow_inf_nan") is False
    with pytest.raises(ValidationError):
        Frozen(value=float("inf"))
