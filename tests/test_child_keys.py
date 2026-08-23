"""Tests for component key namespacing: every emitted key hangs off the base key.

A component that names its inner nodes with a fixed key (``key="seg-0"``) collides
the moment a screen holds two instances of it — and since events route by key, the
handler that answers belongs to the wrong instance. These tests pin the fix: a
component's own root key is :attr:`~tempest_core.widgets.Component.base_key` and
every inner node goes through
:meth:`~tempest_core.widgets.Component.child_key`, so two instances on one screen
share no key at all.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

import pytest

from tempest_core import (
    Breadcrumb,
    Card,
    Column,
    DataTable,
    EmailInput,
    NavBar,
    RadioGroup,
    Rating,
    SegmentedControl,
    Stepper,
    Tabs,
    Text,
    build,
    components,
)
from tempest_core.core import Node
from tempest_core.widgets import Component


def _keys(node: Node) -> list[str]:
    """Collect every key in a built tree, in depth-first order.

    Args:
        node: The root of the built tree.

    Returns:
        The keys of ``node`` and its descendants, skipping unkeyed nodes.
    """
    found = [node.key] if node.key is not None else []
    for child in node.children:
        found.extend(_keys(child))
    return found


def _handler_for(node: Node, key: str) -> Callable[[], Any]:
    """Resolve the click handler of the first node carrying ``key``.

    This mirrors how a runtime routes an event: a depth-first search that stops at
    the first key match.

    Args:
        node: The root of the built tree.
        key: The key the event was raised on.

    Returns:
        The matching node's ``on_click`` handler.

    Raises:
        KeyError: If no node carries ``key`` with an ``on_click`` handler.
    """
    if node.key == key and "on_click" in node.props:
        handler: Callable[[], Any] = node.props["on_click"]
        return handler
    for child in node.children:
        try:
            return _handler_for(child, key)
        except KeyError:
            continue
    raise KeyError(key)


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


def test_base_key_falls_back_to_the_component_name() -> None:
    """An unkeyed component roots at its ``default_key``, a keyed one at its key."""
    assert (
        SegmentedControl(options=[], on_select=lambda i: None).base_key == "segmented"
    )
    assert (
        SegmentedControl(
            key="theme-segments", options=[], on_select=lambda i: None
        ).base_key
        == "theme-segments"
    )


def test_child_key_namespaces_under_the_base_key() -> None:
    """``child_key`` prefixes the component's key, so inner keys stay local to it."""
    control = SegmentedControl(key="quality", options=[], on_select=lambda i: None)
    assert control.child_key("item-0") == "quality-item-0"
    assert SegmentedControl(options=[], on_select=lambda i: None).child_key(
        "item-0"
    ) == ("segmented-item-0")


def test_two_segmented_controls_route_to_their_own_handler() -> None:
    """Clicking the second control's segment must not fire the first's handler.

    The measured regression: both controls emitted ``seg-1``, the depth-first
    lookup stopped at the first one, and every interaction with the second control
    drove the first.
    """
    theme_hits: list[int] = []
    quality_hits: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                SegmentedControl(
                    key="theme-segments",
                    options=["System", "Light", "Dark"],
                    on_select=theme_hits.append,
                ),
                SegmentedControl(
                    key="quality-segments",
                    options=["Low", "Medium", "High"],
                    on_select=quality_hits.append,
                ),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    _handler_for(node, "quality-segments-item-1")()
    assert quality_hits == [1]
    assert theme_hits == []
    _handler_for(node, "theme-segments-item-2")()
    assert theme_hits == [2]
    assert quality_hits == [1]


def test_two_radio_groups_route_to_their_own_handler() -> None:
    """Two ``RadioGroup``s on one screen keep their option keys apart."""
    size_hits: list[int] = []
    color_hits: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                RadioGroup(
                    key="size", options=["S", "M", "L"], on_select=size_hits.append
                ),
                RadioGroup(
                    key="color", options=["Red", "Blue"], on_select=color_hits.append
                ),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    _handler_for(node, "color-item-1")()
    assert color_hits == [1]
    assert size_hits == []


def test_two_navbars_route_to_their_own_handler() -> None:
    """Two ``NavBar``s keep their item keys apart."""
    top_hits: list[int] = []
    bottom_hits: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                NavBar(key="top", items=["A", "B"], on_select=top_hits.append),
                NavBar(key="bottom", items=["C", "D"], on_select=bottom_hits.append),
            ],
        )
    )
    _handler_for(node, "bottom-item-0")()
    assert bottom_hits == [0]
    assert top_hits == []


def test_two_tab_strips_route_to_their_own_handler() -> None:
    """Two ``Tabs`` strips keep their item keys apart."""
    outer_hits: list[int] = []
    inner_hits: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                Tabs(key="outer", tabs=["A", "B"], on_select=outer_hits.append),
                Tabs(key="inner", tabs=["C", "D"], on_select=inner_hits.append),
            ],
        )
    )
    _handler_for(node, "inner-item-1")()
    assert inner_hits == [1]
    assert outer_hits == []


def test_two_cards_emit_distinct_inner_keys() -> None:
    """``Card`` namespaces its body/column, so two cards keep the keyed diff sane."""
    node = build(
        Column(
            key="root",
            children=[
                Card(key="left", children=[Text(content="a")]),
                Card(key="right", children=[Text(content="b")]),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    assert "left-body" in keys
    assert "right-body" in keys


def test_two_data_tables_route_their_pagers_apart() -> None:
    """Two paginated ``DataTable``s keep their pager buttons apart."""
    left_pages: list[int] = []
    right_pages: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                DataTable(
                    key="left",
                    columns=["A"],
                    rows=[["1"], ["2"], ["3"]],
                    page_size=1,
                    page=0,
                    on_page=left_pages.append,
                ),
                DataTable(
                    key="right",
                    columns=["B"],
                    rows=[["1"], ["2"], ["3"]],
                    page_size=1,
                    page=0,
                    on_page=right_pages.append,
                ),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    _handler_for(node, "right-next")()
    assert right_pages == [1]
    assert left_pages == []


def test_two_labelled_br_fields_keep_their_label_keys_apart() -> None:
    """A labelled BR field namespaces its label/error lines under its own key."""
    node = build(
        Column(
            key="root",
            children=[
                EmailInput(key="login-email", error="obrigatório", on_change=print),
                EmailInput(key="billing-email", error="obrigatório", on_change=print),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    assert "login-email-field-label" in keys
    assert "billing-email-field-error" in keys


def test_two_steppers_and_ratings_keep_their_keys_apart() -> None:
    """``Stepper`` and ``Rating`` namespace their buttons and stars."""
    quantity: list[int] = []
    score: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                Stepper(key="quantity", value=1, on_change=quantity.append),
                Stepper(key="guests", value=2, on_change=lambda v: None),
                Rating(key="score", value=2, on_rate=score.append),
                Rating(key="quality", value=1, on_rate=lambda v: None),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    _handler_for(node, "quantity-up")()
    assert quantity == [2]
    _handler_for(node, "score-star-4")()
    assert score == [5]


def test_breadcrumb_separators_and_crumbs_are_namespaced() -> None:
    """Two ``Breadcrumb`` trails keep their crumbs and separators apart."""
    hits: list[int] = []
    node = build(
        Column(
            key="root",
            children=[
                Breadcrumb(key="main", items=["Home", "Docs", "API"], on_select=print),
                Breadcrumb(key="aside", items=["A", "B", "C"], on_select=hits.append),
            ],
        )
    )
    keys = _keys(node)
    assert len(keys) == len(set(keys))
    _handler_for(node, "aside-item-0")()
    assert hits == [0]


@pytest.mark.parametrize("component", _component_classes(), ids=lambda c: c.__name__)
def test_every_component_names_itself(component: type[Component]) -> None:
    """Each renderable component overrides ``default_key`` with its own name.

    An inherited ``"component"`` would make two *different* unkeyed components
    collide, which is the same defect one step removed.
    """
    assert component.default_key != Component.default_key
