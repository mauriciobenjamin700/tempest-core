# Overlays

**Overlays** are the surfaces that float *above* the screen tree: dialogs,
sheets, toasts, menus, tooltips, and popovers. In `tempest-core` they aren't
nested in the layout — they are **pushed onto the `Scene`'s overlay layer**, and
a renderer realizes each as the platform-native surface (Qt `QDialog`/`QMenu`;
Compose `AlertDialog`/`ModalBottomSheet`/`DropdownMenu`). 🚀

The detail that runs through this whole page: **an overlay widget has no "open"
flag**. It describes *what* appears; *when* it appears is the app's decision, via
the imperative API (`show_dialog` / `show_sheet` / `toast` / `show_menu`), which
manages the overlay's lifetime. The widget declares only the content and the
handlers.

!!! info "What you'll learn here"
    - Why **visibility is controlled by the app**, not by a widget prop.
    - The two handler contracts: **`on_dismiss`** (closed) and **`on_select`** (chose).
    - How `Menu` and `ActionSheet` use **`MenuItem`**, a serializable value model.
    - How **`anchor`** positions menus and popovers from another widget's `key`.
    - Why `Toast` **dismisses itself** and has no `on_dismiss`.

## `Dialog`

A **modal** dialog floated above the screen, optionally with a title. The body is
a list of child widgets; `on_dismiss` reacts to closing via a barrier tap (the
scrim behind it) or the system *back* button:

```python
from tempest_core import Dialog, Text, Button, Column

confirm = Dialog(
    title="Delete project?",
    children=[
        Text(text="This action cannot be undone."),
        Button(label="Delete", color_scheme="error"),
    ],
    on_dismiss=lambda e: app.set_state(dialog_open=False),  # (1)!
)
```

1. The handler may be **sync or `async`**. It receives a `DismissEvent` carrying
   the closed overlay's `overlay_id` (or `None` — see [API reference](../reference.md)).

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str \| None` | `None` | Optional dialog title. |
| `children` | `list[Widget]` | `[]` | The dialog body widgets. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler on dismiss (barrier tap or *back*); receives `DismissEvent`. |

!!! note "Visibility belongs to the app, not the widget"
    Notice there is **no `open` or `visible` prop**. A `Dialog` only exists on
    screen while the app keeps it on the `Scene`'s overlay layer. You open it with
    the imperative API (`show_dialog`) and close it by reacting to `on_dismiss` — the
    widget never holds its own open/closed state.

## `BottomSheet`

A sheet that **slides up** from the bottom edge of the screen. Same shape as
`Dialog` — body in `children`, closing in `on_dismiss` — but its dismiss gesture
adds **swipe-down** on top of the barrier tap:

```python
from tempest_core import BottomSheet, Column, Text, Button

filters = BottomSheet(
    children=[
        Text(text="Sort by"),
        Button(label="Newest", variant="ghost"),
        Button(label="Most popular", variant="ghost"),
    ],
    on_dismiss=lambda e: app.set_state(sheet_open=False),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The sheet body widgets. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler on dismiss (barrier tap or swipe-down); receives `DismissEvent`. |

!!! tip "Dialog vs. BottomSheet"
    Both are dismissible modals sharing the `on_dismiss` contract. Reach for
    `Dialog` for centered confirmations and decisions; for `BottomSheet` for options
    and forms that suit the thumb on mobile, anchored at the bottom edge.

## `Toast`

A **transient** message that appears briefly then **dismisses itself**. Unlike
the other overlays, `Toast` has no `on_dismiss`: `App.toast` schedules the
auto-dismiss on the event loop, and `duration_s` also travels to the renderer so
the device can mirror the same timing:

```python
from tempest_core import Toast

saved = Toast(message="Changes saved")
long = Toast(message="Syncing…", duration_s=5.0)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `message` | `str` | *(required)* | The text to display. |
| `duration_s` | `float` | `2.5` | How long the toast stays visible, in seconds. |

!!! note "No `on_dismiss` — closing is automatic"
    `Toast` is the only overlay on this page without a dismiss handler. It doesn't
    wait for interaction: it appears, counts `duration_s`, and disappears. `App.toast`
    owns the timer on the loop; `duration_s` is only mirrored to the renderer so the
    visual feedback stays in sync.

## `Tooltip`

A small hint label shown next to an **anchored child**. It annotates a widget
without consuming its tap; `color_scheme` tells the renderer which Material 3
role family to paint the hint surface with:

```python
from tempest_core import Tooltip, IconButton

hint = Tooltip(
    message="Archive conversation",
    child=IconButton(icon="archive", label="Archive"),
    color_scheme="neutral",
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `message` | `str` | *(required)* | The hint text. |
| `child` | `Widget \| None` | `None` | Optional widget the tooltip annotates. |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the renderer paints the hint surface with. |

!!! info "The engine carries the prop; the renderer resolves the accent (H4)"
    `Tooltip` resolves no color in the core: it only **carries** the `color_scheme`.
    The renderer is the one that matches the accent against the active theme —
    keeping the core from ever touching pixels, like the rest of the library.

## `Menu` and `MenuItem`

A `Menu` is a list of selectable items **anchored to a widget**. The items aren't
widgets: each is a **`MenuItem`**, a *frozen*, JSON-serializable value model, so
the list crosses the device bridge as plain data. Selection fires `on_select`
with the chosen item's `value` and `label`:

```python
from tempest_core import Menu, MenuItem

actions = Menu(
    items=[
        MenuItem(label="Rename", value="rename", icon="edit"),
        MenuItem(label="Duplicate", value="duplicate", icon="copy"),
        MenuItem(label="Delete", value="delete", icon="trash"),
    ],
    anchor="options-button",  # (1)!
    on_select=lambda e: app.run(e.value),  # (2)!
)
```

1. `anchor` is the **`key`** of the widget the menu positions itself from.
2. The handler receives a `MenuSelectEvent` with `value` (stable) and `label` (visible).

### `Menu` props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `items` | `list[MenuItem]` | `[]` | The selectable entries. |
| `anchor` | `str \| None` | `None` | The `key` of the widget the menu anchors to. |
| `on_select` | `MenuSelectHandler \| None` | `None` | Handler on item selection; receives `MenuSelectEvent`. |

### `MenuItem` props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `label` | `str` | *(required)* | The display label. |
| `value` | `str` | *(required)* | The stable value reported by `MenuSelectEvent` on select. |
| `icon` | `str \| None` | `None` | Optional icon name to render alongside the label. |

!!! note "`MenuItem` is data, not a widget"
    `MenuItem` is `frozen` and carries only serializable fields (`label`, `value`,
    `icon`). That's why it doesn't live in the widget tree: it crosses the bridge as
    a plain `dict`. Always separate the **stable `value`** (what your code compares)
    from the **visible `label`** (what the user reads) — it's the `value` that
    reaches the handler.

!!! tip "Positioning via `anchor`"
    `anchor` doesn't move the menu in the layout: it names the `key` of the trigger
    widget so the renderer anchors the native surface near it (a `DropdownMenu` below
    the button, say). Without `anchor`, the renderer positions with its platform
    default.

## `Popover`

A floating panel **anchored near a widget**, dismissible by tapping away. Like
`Menu`, it takes an `anchor` (the trigger's `key`); like `Dialog`, it has
`on_dismiss`. The difference is free content: instead of items, an arbitrary
`child`:

```python
from tempest_core import Popover, Column, Text, Switch

preferences = Popover(
    child=Column(
        children=[
            Text(text="Notifications"),
            Switch(value=True),
        ]
    ),
    anchor="bell-icon",
    on_dismiss=lambda e: app.set_state(popover_open=False),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | Optional widget shown inside the popover. |
| `anchor` | `str \| None` | `None` | The `key` of the widget the popover anchors to. |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler on dismiss; receives `DismissEvent`. |

!!! tip "Popover vs. Menu"
    Use `Menu` when the content is a **list of choices** (it carries `items` +
    `on_select`). Use `Popover` when it's a **free-content panel** anchored to the
    trigger — a mini-form, a summary, loose controls.

## `ActionSheet`

A list of actions **anchored at the bottom** of the screen, optionally titled.
It's `Menu`'s cousin for the mobile bottom-sheet pattern: same `MenuItem`, same
`on_select`, but anchored at the bottom instead of next to a widget:

```python
from tempest_core import ActionSheet, MenuItem

share = ActionSheet(
    title="Share via",
    items=[
        MenuItem(label="Copy link", value="copy", icon="link"),
        MenuItem(label="Email", value="email", icon="mail"),
        MenuItem(label="Message", value="sms", icon="chat"),
    ],
    on_select=lambda e: app.share(e.value),
)
```

### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `title` | `str \| None` | `None` | Optional sheet title. |
| `items` | `list[MenuItem]` | `[]` | The selectable actions. |
| `on_select` | `MenuSelectHandler \| None` | `None` | Handler on action selection; receives `MenuSelectEvent`. |

!!! note "`ActionSheet` selects; `BottomSheet` composes"
    Both rise from the bottom edge, but they solve different contracts.
    `ActionSheet` is **selection** (`items` + `on_select`, via `MenuSelectEvent`),
    like a menu laid down in the footer. `BottomSheet` is **free content**
    (`children` + `on_dismiss`) — a whole layout that slides up. Choose by the
    contract, not the look.

## Recap

- **Overlays float above the screen** and live on the `Scene`'s overlay layer, not
  in the layout — the app pushes them via the imperative API and manages the
  lifetime.
- **No visibility flag**: no overlay has an `open`/`visible` prop; opening and
  closing is the app's decision, and the widget only declares content and handlers.
- **Two handler contracts**: `on_dismiss` → `DismissEvent` (`Dialog`,
  `BottomSheet`, `Popover`); `on_select` → `MenuSelectEvent` (`Menu`,
  `ActionSheet`).
- **`Toast`** is the exception: it **dismisses itself** by `duration_s`, with no
  `on_dismiss`.
- **`MenuItem`** is a *frozen*, serializable value model (`label` / `value` /
  `icon`) — data, not a widget; always separate the stable `value` from the visible
  `label`.
- **`anchor`** is the trigger widget's `key` — it positions `Menu` and `Popover`
  near it; without it, the platform default applies.
- **`Tooltip`** carries `color_scheme`, but the renderer is what resolves the
  accent against the theme (H4).
