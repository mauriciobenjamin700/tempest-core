# 4. Keys and identity

Every interaction reaches the core as **key + event**: the renderer says “the node
`quality-segments-item-1` was clicked” and the runtime looks that node up in the
tree to find the handler. The key *is* the node's identity — for the diff and for
event routing.

Hence the rule: **one key, one node.** Two equal keys on one screen and the
handler that answers belongs to the first node the lookup finds — not necessarily
the one the user touched.

## The problem, measured

Two `SegmentedControl`s on one screen: one for the theme, one for the quality.

```python
from tempest_core import Column, Node, SegmentedControl, build

theme: list[int] = []
quality: list[int] = []

screen = Column(
    key="root",
    children=[
        SegmentedControl(
            key="theme-segments",
            options=["System", "Light", "Dark"],
            on_select=theme.append,
        ),
        SegmentedControl(
            key="quality-segments",
            options=["Low", "Medium", "High"],
            on_select=quality.append,
        ),
    ],
)


def keys(node: Node) -> list[str]:  # (1)!
    """Return the keys of the node and of every descendant."""
    found = [node.key] if node.key is not None else []
    for child in node.children:
        found.extend(keys(child))
    return found


print(keys(build(screen)))
```

1. A plain walk of the built tree, just to look at the emitted keys.

```text
['root',
 'theme-segments', 'theme-segments-item-0', 'theme-segments-item-1', 'theme-segments-item-2',
 'quality-segments', 'quality-segments-item-0', 'quality-segments-item-1', 'quality-segments-item-2']
```

Not one repeated. Before 0.15.0 both controls emitted `seg-0`, `seg-1`, `seg-2`
**each** — clicking “Light” on the theme control changed the quality, and the
theme control sat inert.

## The three pieces

Every component now carries an explicit identity:

| Piece | What it is |
|---|---|
| `default_key` | The component's name, used when the caller passes no `key` (`"segmented"`, `"navbar"`, `"card"`…). |
| `base_key` | `self.key or self.default_key` — the key of the root the component emits. |
| `child_key(suffix)` | `f"{base_key}-{suffix}"` — the key of each inner node. |

```python
from tempest_core import SegmentedControl

control = SegmentedControl(key="quality", options=[], on_select=lambda i: None)

control.base_key            # "quality"
control.child_key("item-0") # "quality-item-0"

unkeyed = SegmentedControl(options=[], on_select=lambda i: None)

unkeyed.base_key            # "segmented"
unkeyed.child_key("item-0") # "segmented-item-0"
```

!!! warning "Two unkeyed instances still collide"
    `default_key` covers the common case of **one** control per screen and keeps
    a tree dump readable. It cannot invent identity: two unkeyed instances of the
    same component land on the same base. On a screen with two of them, **pass a
    `key`** — that is exactly what `key` means.

## Writing your own component

The same contract holds for your components: declare `default_key` and route
every inner node through `child_key`.

```python
from typing import ClassVar

from tempest_core import Button, Column, Component, Text, Widget, build


class Counter(Component):
    """A label with an increment button."""

    default_key: ClassVar[str] = "counter"  # (1)!

    value: int = 0

    def render(self) -> Widget:
        """Lower the counter into primitives."""
        return Column(
            key=self.base_key,  # (2)!
            children=[
                Text(content=str(self.value), key=self.child_key("value")),  # (3)!
                Button(label="+1", on_click=lambda: None, key=self.child_key("plus")),
            ],
        )


print([n.key for n in build(Counter(key="cart", value=2)).children])
# -> ['cart-value', 'cart-plus']
```

1. The component's name. Without it, an unkeyed instance would inherit
   `"component"` — and collide with any other equally distracted component.
2. The root uses `base_key`, never a hand-written `self.key or "..."`.
3. The suffix names the node's **role** inside the component (`value`, `plus`,
   `item-0`), without repeating the component's name — the base already carries
   it.

!!! tip "The test that holds this"
    `tests/test_child_keys.py` builds two instances of each interactive
    component, asserts the tree has no repeated key and fires the handler by key —
    the way the runtime would. A new component without its own `default_key`
    fails the parametrized guard.

## Migrating from 0.14.x

The inner keys changed shape along with the fix: on top of the prefix, the suffix
dropped the repetition of the component's name. If your code (or your test, or
your renderer fixture) looks a node up by a literal key, update it:

| Component | Before | Now |
|---|---|---|
| `SegmentedControl` | `seg-1` | `<key>-item-1` |
| `RadioGroup` | `radio-1` | `<key>-item-1` |
| `NavBar` | `nav-1` | `<key>-item-1` |
| `Tabs` | `tab-1` | `<key>-item-1` |
| `Breadcrumb` | `crumb-1` / `sep-1` | `<key>-item-1` / `<key>-sep-1` |
| `Rating` | `star-1` | `<key>-star-1` |
| `Card` | `card-body` / `card-col` | `<key>-body` / `<key>-col` |
| `DataTable` | `dt-next` / `dt-row-0` | `<key>-next` / `<key>-row-0` |
| `Stepper` | `step-up` / `step-value` | `<key>-up` / `<key>-value` |
| `SearchBar` | `search-input` | `<key>-input` |
| `EmailInput` (and BR siblings) | `email-field` / `field-label` | `<key>-field` / `<key>-field-label` |

Where `<key>` is the `key` you passed — or the component's `default_key`
(`segmented`, `navbar`, `card`, `data-table`, `stepper`, `searchbar`,
`email-input`…) when you passed none. For an unkeyed component, `AppBar`,
`Header`, `Card` and friends land on exactly the old key (`appbar-title`,
`header-subtitle`, `card-body`), because the suffix already repeated the
component's name.

## Recap

- Events route by key; a repeated key delivers the event to the wrong node.
- `base_key` is the component's root, `child_key(suffix)` is each inner node.
- `default_key` names the component for an unkeyed instance — two on one screen
  still need an explicit `key`.
- Your own components follow the same contract, and the parametrized guard
  enforces it.
