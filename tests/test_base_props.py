"""A component carries the base props the caller set on it.

Every :class:`~tempest_core.widgets.Widget` declares ``semantics``, ``focusable``,
``focus_order``, ``tag`` and ``attrs`` — props that describe the *node*. A
component is not a node: :func:`~tempest_core.build` replaces it with the tree its
``render`` returns, so until this existed a prop set on a component reached
nothing at all. Naming a ``Card`` compiled, type-checked, and did nothing.

Measured over the 54 public components before the fix:

| Prop | Dropped by |
| --- | --- |
| ``semantics`` | 50 of 54 (four forwarded it by hand: see below) |
| ``focusable`` | 54 of 54 |
| ``focus_order`` | 54 of 54 |
| ``tag`` | 54 of 54 |
| ``attrs`` | 54 of 54 |
| ``key`` | 0 of 54 — already handled by ``base_key`` |

The four that forwarded ``semantics`` were ``ListTile``, ``Alert``, ``Stat`` and
``ProgressStepper``, each with the same line inside its own ``render``.

The consequence was measured downstream, in tempestweb: a grid of twenty items
with one header row needs caption-less cells, and a caption-less cell whose
``semantics`` is dropped is a control with no accessible name — axe reported
``label`` (critical) on every field of a login form, in every app using it.

The four hand-written forwards are gone with this: one mechanism, so a component
added tomorrow gets the behaviour without its author knowing the rule exists.
"""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from tempest_core import (
    CARRIED_PROPS,
    Card,
    Column,
    Component,
    Container,
    Node,
    Semantics,
    Text,
    Widget,
    build,
    components,
)

NAME: str = "Total proposto"
"""The name a caller asks for, distinctive enough to find in a built tree."""

OWN_NAME: str = "the name the render chose"
"""A name a ``render`` hardcodes, used to pin which side wins."""

REQUIRED_VALUES: dict[str, Any] = {"confidence": 0.9, "image_src": "/img.png"}
"""Values for the required fields that are not handlers.

Every other required field across the component surface is an event handler, so it
gets a no-op. A new required field of another type makes the instances here fail
loudly, which is the point — a component this sweep cannot build is a component
the sweep is not covering.
"""


def _noop(*_args: Any, **_kwargs: Any) -> None:
    """Swallow whatever a component's handler is called with."""


def _instance(component: type[Component], **props: Any) -> Component:
    """Build one instance of a component, filling its required fields.

    Args:
        component: The component class.
        **props: The props under test.

    Returns:
        The instance.
    """
    filled: dict[str, Any] = dict(props)
    for name, field in component.model_fields.items():
        if field.is_required():
            filled[name] = REQUIRED_VALUES.get(name, _noop)
    return component(**filled)


def _component_classes() -> list[type[Component]]:
    """Collect the public component classes the package exports.

    Returns:
        Every public :class:`~tempest_core.widgets.Component` subclass declared in
        :mod:`tempest_core.components` that implements ``render``.
    """
    found: list[type[Component]] = []
    for name in components.__all__:
        obj = getattr(components, name)
        if not (inspect.isclass(obj) and issubclass(obj, Component)):
            continue
        if obj.render is Component.render:
            continue
        found.append(obj)
    return found


def _announcing(node: Node, label: str) -> list[Node]:
    """Collect every node in a built tree announcing one accessible name.

    Args:
        node: The root of the built tree.
        label: The name to look for.

    Returns:
        The matching nodes, in tree order.
    """
    semantics = node.props.get("semantics")
    found = [node] if getattr(semantics, "label", None) == label else []
    for child in node.children:
        found.extend(_announcing(child, label))
    return found


class _Named(Component):
    """A component whose ``render`` names its own root.

    Attributes:
        default_key: The component's own base key.
    """

    default_key = "named"

    def render(self) -> Widget:
        """Lower into a container that already announces a name of its own.

        Returns:
            A named container.
        """
        return Container(
            key=self.base_key,
            semantics=Semantics(label=OWN_NAME),
            attrs={"data-render": "kept", "data-both": "render"},
        )


class _Routing(Component):
    """A component that routes the name it is given to its own control.

    This is what every field is: the accessible name belongs on the ``Input`` a
    screen reader stops at, not on the wrapper around it.

    Attributes:
        default_key: The component's own base key.
    """

    default_key = "routing"

    def render(self) -> Widget:
        """Lower into a wrapper whose inner control carries the name.

        Returns:
            A column wrapping a named container.
        """
        return Column(
            key=self.base_key,
            children=[
                Container(key=self.child_key("control"), semantics=self.semantics),
            ],
        )


class _Nesting(Component):
    """A component whose ``render`` returns another component.

    Attributes:
        default_key: The component's own base key.
    """

    default_key = "nesting"

    def render(self) -> Widget:
        """Lower into a component, not a primitive.

        Returns:
            A card, which is itself a component.
        """
        return Card(key=self.base_key, children=[Text(content="x")])


@pytest.mark.parametrize("component", _component_classes(), ids=lambda c: c.__name__)
def test_every_component_carries_the_name_it_is_given(
    component: type[Component],
) -> None:
    """A named component announces that name on exactly one node: its root.

    Args:
        component: The component under test.
    """
    tree = build(_instance(component, semantics=Semantics(label=NAME)))
    assert _announcing(tree, NAME) == [tree], (
        f"{component.__name__} dropped the name it was given — a component is "
        "expanded before any renderer sees the tree, so a prop nobody carries "
        "reaches no node at all"
    )


@pytest.mark.parametrize("component", _component_classes(), ids=lambda c: c.__name__)
def test_every_component_carries_focus_and_tag(component: type[Component]) -> None:
    """``focusable``, ``focus_order`` and ``tag`` reach the rendered root too.

    Args:
        component: The component under test.
    """
    tree = build(
        _instance(
            component,
            focusable=True,
            focus_order=7,
            tag="section",
            attrs={"data-probe": "1"},
        )
    )
    assert tree.props["focusable"] is True
    assert tree.props["focus_order"] == 7
    assert tree.props["tag"] == "section"
    assert tree.props["attrs"]["data-probe"] == "1"


@pytest.mark.parametrize("component", _component_classes(), ids=lambda c: c.__name__)
def test_a_component_given_nothing_invents_nothing(
    component: type[Component],
) -> None:
    """No prop set means no prop on the root — the carry adds only what it is told.

    Args:
        component: The component under test.
    """
    tree = build(_instance(component))
    assert tree.props["semantics"] is None
    assert tree.props["focusable"] is None
    assert tree.props["focus_order"] is None
    assert tree.props["tag"] is None


def test_the_render_keeps_the_prop_it_touched() -> None:
    """A prop the render already set is left alone, name and ``attrs`` alike.

    The component decided; the base does not second-guess it. Overwriting would
    also be the more dangerous direction — see
    :func:`test_a_routed_name_is_not_copied_onto_the_wrapper`.
    """
    tree = build(
        _Named(semantics=Semantics(label=NAME), attrs={"data-app": "1"}),
    )
    assert _announcing(tree, OWN_NAME) == [tree]
    assert _announcing(tree, NAME) == []
    assert tree.props["attrs"] == {"data-render": "kept", "data-both": "render"}


def test_a_routed_name_is_not_copied_onto_the_wrapper() -> None:
    """A component that names its own control gets no second name on the root.

    This is the case that decides the rule. Copying the name onto the wrapper too
    announces one control twice, and puts ``aria-label`` on an element with no
    role — measured downstream as ``aria-prohibited-attr`` (serious) on a screen
    that was clean before.
    """
    tree = build(_Routing(semantics=Semantics(label=NAME)))
    announced = _announcing(tree, NAME)
    assert [node.key for node in announced] == ["routing-control"]
    assert tree.props["semantics"] is None


@pytest.mark.parametrize(
    ("prop", "value"),
    [("focusable", False), ("focus_order", 0), ("tag", "section")],
)
def test_a_falsy_prop_is_still_a_value(prop: str, value: object) -> None:
    """``focusable=False`` and ``focus_order=0`` are choices, not absence.

    The first implementation tested truthiness, so a node the caller marked as
    *not* focusable, and one asked to come first in the traversal, both arrived
    with the prop unset — the same silent drop this whole file exists to stop,
    one layer in.

    Args:
        prop: The base prop under test.
        value: The falsy-but-meaningful value.
    """
    tree = build(Card(key="card", children=[], **{prop: value}))
    assert tree.props[prop] == value


def test_an_empty_attrs_dict_is_absence() -> None:
    """``attrs`` defaults to ``{}``, so an empty dict carries nothing.

    It is the one carried prop whose "unset" is not ``None``: carrying an empty
    dict onto a root that already had attributes would erase them.
    """
    tree = build(_Named(attrs={}))
    assert tree.props["attrs"] == {"data-render": "kept", "data-both": "render"}


def test_attrs_are_carried_when_the_render_sets_none() -> None:
    """``attrs`` follows the same rule as the rest: carried only if untouched."""
    tree = build(Card(key="card", attrs={"data-app": "1"}, children=[]))
    assert tree.props["attrs"] == {"data-app": "1"}


def test_the_name_crosses_two_component_boundaries() -> None:
    """A component that renders another component still lands the name once."""
    tree = build(_Nesting(semantics=Semantics(label=NAME)))
    assert _announcing(tree, NAME) == [tree]


def test_carried_props_is_the_whole_base_surface() -> None:
    """:data:`CARRIED_PROPS` plus the three exceptions is every base field.

    A base prop added later would otherwise be dropped at every component
    boundary in silence — which is exactly how the five in this file got there.
    ``key`` is namespaced by ``base_key``, and ``style`` is the component's own
    to fold in (several merge it into an inner node, so carrying it would apply
    it twice).
    """
    assert set(CARRIED_PROPS) | {"key", "style"} == set(Widget.model_fields)


def test_a_named_component_inside_a_tree_keeps_the_name_on_its_own_root() -> None:
    """The carry is per component, not per tree: a child component keeps its name."""
    tree = build(
        Column(
            key="root",
            children=[Card(key="card", semantics=Semantics(label=NAME), children=[])],
        )
    )
    announced = _announcing(tree, NAME)
    assert [node.key for node in announced] == ["card"]
