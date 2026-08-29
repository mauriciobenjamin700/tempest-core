# 1. State and rebuilds

A live UI = state + a function from state to tree. The **`App`** holds the state,
runs your `view(app)`, and on a state change rebuilds and diffs — emitting patches
through an `apply_patches` callback.

```python
from dataclasses import dataclass

from tempest_core import App, Column, Text, Widget


@dataclass
class State:
    value: int = 0


emitted = []


def view(app: App[State]) -> Widget:
    return Column(children=[Text(content=f"Count: {app.state.value}", key="lbl")])


app = App(state=State(), view=view, apply_patches=emitted.append)  # (1)!
app.start()  # (2)!
app.set_state(lambda s: setattr(s, "value", 1))  # (3)!
```

1. `apply_patches` receives each tick's patch list. A renderer applies it; here we
   just collect.
2. `start()` builds the initial scene.
3. `set_state` mutates state and **schedules a coalesced rebuild** — several
   changes in one tick become a single diff.

!!! note "The view is pure"
    `view()` only **reads** `app.state` and describes the UI. Changing state is the
    handlers' job, via `set_state`. The view never mutates anything.

!!! note "A failed delivery does not desynchronize the tree"
    `apply_patches` is your renderer, and renderers fail: the socket drops, the
    client cannot decode, the encoder refuses the payload. When the call raises,
    the `App` does **not** adopt the new scene — the baseline keeps describing
    what the renderer actually has.

    That is what makes the loss self-healing. The next rebuild diffs from the real
    tree, so the work the lost batch carried is regenerated — including an
    `insert`, which is precisely what a later diff could not recover if the
    baseline had moved on.

## Navigation is state too

Navigation lives on the `App` itself: `app.push(route)` / `app.pop()` /
`app.replace(route)` / `app.reset(stack)` change the top route and schedule a
rebuild. `app.nav` is the read-only `NavStack` — the `view` reads `app.nav.top`
(and `app.nav.can_pop`) and draws the screen. No new IR node: changing routes is
just the view producing a different tree.

## Recap

- `App(state, view, apply_patches)` + `start()` starts the UI.
- `set_state(mutator)` schedules a coalesced rebuild → diff → patches.
- `app.push` / `app.pop` / `app.reset` is navigation as state (route read at `app.nav.top`).
- The baseline only advances once the patches were delivered; a failed
  delivery is repaired by the next rebuild.
- Next: [styling](style.md).
