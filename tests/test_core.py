"""Foundation tests: the package imports and the engine works headless."""

from __future__ import annotations

from tempest_core import Column, Component, Style, Text, Widget, build, diff
from tempest_core.core.ir import Update


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


def test_escape_hatch_defaults_are_empty() -> None:
    """A plain widget carries no tag and an empty attrs map by default."""
    widget = Text(content="x")
    assert widget.tag is None
    assert widget.attrs == {}


def test_escape_hatch_defaults_surface_on_node() -> None:
    """build copies the default tag/attrs onto the IR node props."""
    node = build(Text(content="x"))
    assert node.props["tag"] is None
    assert node.props["attrs"] == {}


def test_escape_hatch_flows_into_node_props() -> None:
    """tag and attrs set on a widget surface as IR node props via build."""
    node = build(Text(content="x", tag="nav", attrs={"id": "x", "hx-get": "/y"}))
    assert node.props["tag"] == "nav"
    assert node.props["attrs"] == {"id": "x", "hx-get": "/y"}


class _TaggedComponent(Component):
    """A component whose render carries an SSR tag and attrs on a primitive."""

    label: str

    def render(self) -> Widget:
        """Lower to a Text primitive carrying the escape-hatch fields.

        Returns:
            A Text widget with a semantic tag and HTML attributes.
        """
        return Text(
            content=self.label,
            tag="h1",
            attrs={"id": "title", "data-role": "heading"},
        )


def test_escape_hatch_round_trips_through_component_render() -> None:
    """A Component's render expansion surfaces tag/attrs on the built node."""
    node = build(_TaggedComponent(label="Hello"))
    assert node.type == "Text"
    assert node.props["tag"] == "h1"
    assert node.props["attrs"] == {"id": "title", "data-role": "heading"}


def test_attrs_default_is_not_shared_between_instances() -> None:
    """Each widget gets a fresh attrs dict (no mutable-default aliasing)."""
    first = Text(content="a")
    second = Text(content="b")
    first.attrs["id"] = "only-first"
    assert second.attrs == {}
    assert first.attrs == {"id": "only-first"}


def test_diff_reports_changed_attrs_as_update() -> None:
    """Two widgets differing only in attrs diff to an Update with the change."""
    old = build(Text(content="x", attrs={"id": "a"}))
    new = build(Text(content="x", attrs={"id": "b", "hx-get": "/z"}))
    patches = diff(old, new)
    assert len(patches) == 1
    patch = patches[0]
    assert isinstance(patch, Update)
    assert patch.set_props == {"attrs": {"id": "b", "hx-get": "/z"}}
    assert patch.unset_props == []
