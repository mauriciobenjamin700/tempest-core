# tempest-core

📚 **Documentation:** [Português (Brasil)](https://mauriciobenjamin700.github.io/tempest-core/)
· [English (US)](https://mauriciobenjamin700.github.io/tempest-core/en/) — bilingual, on GitHub Pages.

**Renderer-agnostic UI core** shared across the tempest stack — the engine behind
both [tempestroid](https://github.com/mauriciobenjamin700/tempestroid) (native
renderers: Qt / Compose / Android) and tempestweb (DOM, WASM + server modes).

It is the *one tree, many renderers* core: the IR, the reconciler (`build` /
`diff`), the state model (`App`), the typed style model (`Style`, `Color`, `Edge`),
the widget and component trees, plus the cross-cutting helpers (animation, i18n,
navigation, theme, validators). It carries **no platform-coupled code** — no Qt, no
JNI, no Android, no DOM — so it imports cleanly under CPython, Pyodide and a
headless server. Renderers live in the consumers; this package only produces and
diffs the tree.

```python
from tempest_core import App, Column, Text, Button, Style, build, diff

old = build(Column(children=[Text(content="Count: 0", key="label")]))
new = build(Column(children=[Text(content="Count: 1", key="label")]))
patches = diff(old, new)          # -> [Update(set_props={"content": "Count: 1"})]
```

### Design system (Chakra-style variants → Material 3)

Components take Chakra-ergonomics props (`variant`/`size`/`color_scheme`) and a
`theme`, and resolve a concrete Material 3 `Style` via pure resolvers in
`variants.py` — `resolve_variant` (buttons), `resolve_field_variant` (text
inputs / select / masked / autocomplete / pin), `resolve_selection_variant`
(checkbox / switch) and `resolve_slider_variant` (sliders). Each ships a
`*_states` sibling returning the per-state table (default/hover/pressed/disabled/
focus) the renderers apply on real events. The touch target is held ≥ 48dp and
WCAG-AA contrast is preserved. An explicit `style=` is always merged on top.

```python
from tempest_core import IconButton, Theme
from tempest_core.widgets import Input
from tempest_core.style import FieldVariant

field = Input(value="", field_variant=FieldVariant.FILLED, color_scheme="primary")
button = IconButton(icon="settings", color_scheme="primary", label="Open settings")
```

## Install

```bash
pip install tempest-core
```

Requires Python `>=3.11`. Only hard dependency: `pydantic>=2`.

## Status

Extracted from tempestroid's vendored core. **tempestweb** consumes it directly
(no vendored copy). tempestroid's own migration to depend on this package — with
its full Qt↔Compose conformance suite green — is the next phase.

## Develop

```bash
uv sync --extra dev
ruff check . && ruff format --check .
mypy tempest_core
pytest -q
```
