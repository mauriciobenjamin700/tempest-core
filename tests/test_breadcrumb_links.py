"""Tests for ``Breadcrumb`` crumbs with a destination (issue #30).

A server-rendered trail has no event loop to resolve ``on_select``, so a step
that should lead back to its folder needs an ``href``. These tests pin the IR the
web renderers turn into markup: the ``nav`` landmark and its ``aria-label``, an
``a``-tagged crumb with ``href`` for each :class:`BreadcrumbItem` that has one,
``aria-current="page"`` on the last crumb, ``aria-hidden`` separators, the
unchanged ``list[str]`` + ``on_select`` path, and the ``href`` scheme guard.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from tempest_core import (
    BREADCRUMB_HREF_SCHEMES,
    Breadcrumb,
    BreadcrumbItem,
    Node,
    Theme,
    build,
)

THEME = Theme()


def _crumb(node: Node, index: int) -> Node:
    return next(c for c in node.children if c.key == f"breadcrumb-item-{index}")


def _separators(node: Node) -> list[Node]:
    return [c for c in node.children if (c.key or "").startswith("breadcrumb-sep-")]


def _folders() -> Breadcrumb:
    return Breadcrumb(
        items=[
            BreadcrumbItem(label="bucket", href="/b"),
            BreadcrumbItem(label="fotos", href="/b/fotos"),
            BreadcrumbItem(label="2026", href="/b/fotos/2026"),
        ],
        theme=THEME,
    )


def test_root_is_a_labelled_nav_landmark() -> None:
    node = build(_folders())
    assert node.type == "Row"
    assert node.props["tag"] == "nav"
    assert node.props["attrs"] == {"aria-label": "Breadcrumb"}


def test_label_names_the_landmark() -> None:
    node = build(Breadcrumb(items=["a"], label="Pastas"))
    assert node.props["attrs"]["aria-label"] == "Pastas"


def test_href_crumbs_are_links() -> None:
    node = build(_folders())
    for index, href in enumerate(["/b", "/b/fotos"]):
        crumb = _crumb(node, index)
        assert crumb.type == "Text"
        assert crumb.props["tag"] == "a"
        assert crumb.props["attrs"] == {"href": href}


def test_last_crumb_is_current_page_link() -> None:
    crumb = _crumb(build(_folders()), 2)
    assert crumb.props["tag"] == "a"
    assert crumb.props["attrs"] == {"href": "/b/fotos/2026", "aria-current": "page"}


def test_link_crumb_paints_link_variant() -> None:
    node = build(
        Breadcrumb(
            items=[BreadcrumbItem(label="a", href="/a"), "b"], color_scheme="info"
        )
    )
    assert _crumb(node, 0).props["style"].color == THEME.color("info")


def test_link_crumb_is_inline_not_a_button_box() -> None:
    """The LINK variant's hit box (padding, background, min height) stays off.

    Measured in Chrome: with the full variant each ``<a>`` drew as a 48px box and
    sat off the separators' baseline.
    """
    style = _crumb(build(_folders()), 0).props["style"]
    assert style.padding is None
    assert style.background is None
    assert style.min_height is None
    assert style.text_decoration is not None


def test_crumb_without_href_is_plain_text() -> None:
    node = build(
        Breadcrumb(items=[BreadcrumbItem(label="raiz"), BreadcrumbItem(label="x")])
    )
    crumb = _crumb(node, 0)
    assert crumb.type == "Text"
    assert crumb.props.get("tag") is None
    assert crumb.props.get("attrs") in (None, {})


def test_plain_labels_mark_last_as_current() -> None:
    node = build(Breadcrumb(items=["Home", "Page"]))
    assert _crumb(node, 1).props["attrs"] == {"aria-current": "page"}
    assert _crumb(node, 0).props.get("attrs") in (None, {})


def test_separators_are_hidden_from_assistive_tech() -> None:
    seps = _separators(build(_folders()))
    assert len(seps) == 2
    assert all(s.props["attrs"] == {"aria-hidden": "true"} for s in seps)


def test_mixed_items_keep_on_select_for_plain_crumbs() -> None:
    seen: list[int] = []
    node = build(
        Breadcrumb(
            items=[BreadcrumbItem(label="bucket", href="/b"), "fotos", "2026"],
            on_select=seen.append,
        )
    )
    assert _crumb(node, 0).props["tag"] == "a"
    button = _crumb(node, 1)
    assert button.type == "Button"
    button.props["on_click"]()
    assert seen == [1]
    assert _crumb(node, 2).type == "Text"


def test_str_items_with_on_select_are_unchanged() -> None:
    seen: list[int] = []
    node = build(Breadcrumb(items=["Home", "Sub", "Page"], on_select=seen.append))
    assert [c.type for c in node.children] == [
        "Button",
        "Text",
        "Button",
        "Text",
        "Text",
    ]
    _crumb(node, 0).props["on_click"]()
    assert seen == [0]


def test_component_tag_and_attrs_merge_over_defaults() -> None:
    node = build(
        Breadcrumb(items=["a"], tag="div", attrs={"id": "trail", "aria-label": "X"})
    )
    assert node.props["tag"] == "div"
    assert node.props["attrs"] == {"aria-label": "X", "id": "trail"}


def test_allowed_schemes_are_pinned() -> None:
    assert frozenset({"http", "https"}) == BREADCRUMB_HREF_SCHEMES


@pytest.mark.parametrize(
    "href",
    [
        "/b/fotos",
        "../",
        "fotos/2026",
        "?page=2",
        "#top",
        "https://example.com/b",
        "HTTP://example.com",
        "/b/minhas fotos",
        "/b/a:b",
    ],
)
def test_relative_and_web_hrefs_are_accepted(href: str) -> None:
    assert BreadcrumbItem(label="x", href=href).href == href


@pytest.mark.parametrize(
    "href",
    [
        "javascript:alert(1)",
        "JavaScript:alert(1)",
        " javascript:alert(1)",
        "java\tscript:alert(1)",
        "java\nscript:alert(1)",
        "\x00javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "vbscript:msgbox(1)",
        "file:///etc/passwd",
    ],
)
def test_executable_or_local_schemes_are_refused(href: str) -> None:
    with pytest.raises(ValidationError):
        BreadcrumbItem(label="x", href=href)


def test_item_is_frozen() -> None:
    item = BreadcrumbItem(label="x", href="/x")
    with pytest.raises(ValidationError):
        item.label = "y"  # type: ignore[misc]
