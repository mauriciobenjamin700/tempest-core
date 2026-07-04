# tempest-core

**The renderer-agnostic UI core** — the engine behind
[tempestroid](https://github.com/mauriciobenjamin700/tempestroid) (native
renderers: Qt / Compose / Android) and tempestweb (DOM, WASM + server modes). 🌩️

One tree, many renderers. You describe the UI as **typed Python** and the core
produces an immutable tree (the IR) and computes the **diff** between two trees —
renderers just apply the patches.

```python
from tempest_core import Column, Text, build, diff

old = build(Column(children=[Text(content="Count: 0", key="label")]))
new = build(Column(children=[Text(content="Count: 1", key="label")]))

diff(old, new)
# -> [Update(set_props={"content": "Count: 1"})]
```

## What's inside

| Layer | What it does |
|---|---|
| **IR + reconciler** | `build` / `diff` (and `build_scene` / `diff_scene` for overlays), the `Node` / `Patch` model, and `App` with a coalesced rebuild loop |
| **Typed style** | `Style`, `Color`, `Edge`, gradients, shadows, borders, transitions — no CSS cascade, inline and typed |
| **Widgets & components** | layout (Column/Row/Container/Stack), text, button, inputs, checkbox, lists (LazyColumn/Row/Grid), overlays, gestures, media, + composed components (cards, forms, fields, tables, BR inputs…) |
| **Design system** | Chakra ergonomics (`variant`/`size`/`color_scheme`) → Material 3 `Style` via pure resolvers (`variants.py`): buttons/fields/selection, surfaces, feedback (`success`/`warning`/`info`), navigation and a research / data-science kit |
| **Cross-cutting** | animation, i18n, navigation (`Route`/`NavStack`), theme, validators (CPF/CNPJ/email/phone), icons |

!!! tip "No platform-coupled code"
    No Qt, JNI, Android or DOM here — the core imports cleanly under CPython,
    Pyodide and a headless server. Only hard dependency: `pydantic>=2`.

## Next steps

- [Installation](installation.md) — `pip install tempest-core`.
- [Tutorial](tutorial/index.md) — build and diff your first tree.
- [API reference](reference.md) — the public symbols.
