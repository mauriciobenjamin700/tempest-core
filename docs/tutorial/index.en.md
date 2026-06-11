# Tutorial — build & diff

The heart of tempest-core is two functions: **`build`** turns a widget into an
immutable tree (the IR), and **`diff`** compares two trees and returns the minimal
list of **patches**. A renderer applies those patches; the core never touches
pixels.

## Build a tree

```python
from tempest_core import Column, Text, build

tree = build(
    Column(
        children=[
            Text(content="Hello", key="greeting"),  # (1)!
        ],
    )
)
print(tree.type)        # "Column"
print(tree.children[0].props["content"])  # "Hello"
```

1. `key` is the node's stable identity — it's how the diff matches nodes across
   rebuilds. Give a `key` to anything that can change position or content.

`build` returns an immutable `Node`: `{type, key, props, children}`.

## Diff two trees

```python
from tempest_core import Column, Text, build, diff

a = build(Column(children=[Text(content="Hello", key="g")]))
b = build(Column(children=[Text(content="Bye", key="g")]))

patches = diff(a, b)
print(patches[0].model_dump(mode="json"))
# {"path": [0], "set_props": {"content": "Bye"}, "unset_props": []}
```

The diff is **keyed and minimal**: only what changed becomes a patch. The five
kinds are `Update`, `Insert`, `Remove`, `Reorder` and `Replace`.

!!! info "Why this matters"
    The renderer gets only the delta — it never rebuilds the whole screen. Same
    model as React, but the tree is typed Python, no JSX.

## Recap

- `build(widget) -> Node` — the immutable tree.
- `diff(old, new) -> list[Patch]` — the minimal, keyed delta.
- Give nodes a `key` so the diff matches correctly.
- Next: [state and rebuilds](state.md).
