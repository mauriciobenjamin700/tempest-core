"""Foundation tests: the package imports and the engine works headless."""

from __future__ import annotations

from tempest_core import Column, Style, Text, build, diff


def test_build_and_diff() -> None:
    """build + diff over a small tree produces the expected Update patch."""
    a = build(Column(children=[Text(content="x", key="t")]))
    b = build(Column(children=[Text(content="y", key="t")]))
    patches = diff(a, b)
    assert len(patches) == 1
    dumped = patches[0].model_dump(mode="json")
    assert dumped["set_props"] == {"content": "y"}


def test_style_dump_shape() -> None:
    """Style serializes Color as an rgba dict — the cross-renderer contract."""
    from tempest_core.style import Color

    style = Style(gap=8.0, color=Color.from_hex("#111111"))
    dumped = style.model_dump(mode="json")
    assert dumped["gap"] == 8.0
    assert dumped["color"] == {"r": 17, "g": 17, "b": 17, "a": 1.0}


def test_public_api_is_importable() -> None:
    """The advertised top-level symbols all resolve."""
    import tempest_core

    for name in ("App", "Column", "Row", "Text", "Button", "build", "diff", "Style"):
        assert hasattr(tempest_core, name), name
