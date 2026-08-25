# Events & handlers

Every interactive `tempest-core` widget has two sides. The **handler prop** you
pass in (`on_click`, `on_change`, `on_submit`…) is the outside; on the inside,
each widget declares **which typed `Event`** that handler will receive. This page
documents that other side: the **events**, the **enums** they carry, the
**handler aliases** that type them, and the **`Semantics`** that describes the
node to screen readers. 🚀

!!! info "What you'll learn here"
    - How a **raw** event becomes a typed `Event` in `parse_event`, and how
      `handler_accepts_event` decides the calling convention.
    - The **full table** of event types with each one's real fields.
    - The **enums** events carry (`SwipeDirection`, `SensorType`,
      `ConnectivityState`, `AppState`).
    - The **handler aliases** (`EventHandler`, `TapHandler`, …) and where they show up.
    - The **`Semantics`** class and how widgets expose it for accessibility.

## How events flow

Without a WebView there is no JS↔Python frontier: the typed contract lives at the
**Python↔Kotlin** boundary. When the native side reports a tap or a text change,
it sends a **raw payload** (a `Mapping[str, Any]`) — and that payload must be
validated *before* it enters a Python handler, exactly like FastAPI validates a
request body. Three pieces assemble this flow:

- **`event_schemas`** — a `ClassVar` on every `Widget` that **maps a handler prop
  name to the `Event` type** its payload becomes. It's how introspection publishes
  each widget's event contract. A `Button` declares `{"on_click": TapEvent}`.
- **`parse_event`** — the validation gate: it takes the expected `event_type` and
  the `raw` payload, and returns a typed `Event` (or raises `EventValidationError`
  with the structured field errors).
- **`handler_accepts_event`** — it inspects the handler's signature: a handler that
  accepts **one positional argument** receives the typed event; a **zero-argument**
  handler is called bare. Both the bridge registry and the Qt renderer use it to
  agree on the calling convention.

The handler itself may be **sync or `async`** — the runtime schedules awaitables
on the event loop. Here's the full path of a `Button` with `on_click`:

```python
from tempest_core import Button, TapEvent, parse_event, handler_accepts_event


def on_tap(event: TapEvent) -> None:
    """Handle a tap by reading the tap position off the typed event."""
    print("tapped at", event.x, event.y)


button = Button(label="Save", on_click=on_tap)

# 1. The widget publishes its contract: which prop becomes which Event.
assert button.event_schemas == {"on_click": TapEvent}

# 2. The native side sends a raw payload; parse_event validates at the boundary.
raw: dict[str, float] = {"x": 12.0, "y": 34.0}
event: TapEvent = parse_event(TapEvent, raw)

# 3. handler_accepts_event decides the convention: with-arg vs. bare.
if handler_accepts_event(on_tap):
    on_tap(event)  # receives the validated TapEvent
else:
    on_tap()  # a zero-argument handler is called bare
```

!!! note "`parse_event` is the single trust gate"
    Native code sends an untyped map; **only a valid payload** becomes an `Event`
    the handler can trust. If the payload doesn't match the `event_type`,
    `parse_event` raises `EventValidationError` carrying the `event_type` and the
    Pydantic `errors` list (JSON-serializable) — no half-validated data ever slips
    into the handler.

!!! tip "Zero arguments when the value doesn't matter"
    Not every handler needs the event. `Button(on_click=lambda: counter.incr())`
    is perfectly valid: because the lambda declares no positional argument,
    `handler_accepts_event` returns `False` and the runtime calls it bare. You only
    declare the parameter when you're going to **read** a field (`event.value`,
    `event.x`…).

## Event types

Every event inherits from **`Event`** (a *frozen* `BaseModel`, so the reconciler
diffs it by value). The table lists each type with its real fields and defaults.
Fields with no default are **required** in the payload.

| `Event` | Emitted by / when | Real fields |
| --- | --- | --- |
| `TapEvent` | a tap/click on a widget | `x: float \| None = None`, `y: float \| None = None` |
| `TextChangeEvent` | a text input's value changed | `value: str`, `valid: bool \| None = None` |
| `ToggleEvent` | a checkbox/switch toggled | `checked: bool` |
| `SlideEvent` | a slider's value changed | `value: float` (within the widget's `[min, max]`) |
| `DateChangeEvent` | a date picker's value changed | `value: str` (ISO `yyyy-mm-dd`, empty when cleared) |
| `FileSelectEvent` | a file was selected from a file picker | `uri: str`, `name: str \| None = None` |
| `LongPressEvent` | a press held past the long-press threshold | `x: float \| None = None`, `y: float \| None = None` |
| `SwipeEvent` | a directional swipe past the distance threshold | `direction: SwipeDirection`, `dx: float = 0.0`, `dy: float = 0.0` |
| `RouteChangeEvent` | the active route changed (push/pop/replace) | `name: str`, `params: dict[str, Any] = {}` |
| `ScrollEvent` | a scrollable container scrolled | `offset: float`, `direction: str` (`"vertical"`/`"horizontal"`) |
| `RefreshEvent` | a pull-to-refresh completed | *(no payload — the gesture is the signal)* |
| `EndReachedEvent` | the list scrolled past its end threshold | *(no payload — triggers pagination)* |
| `DismissEvent` | an overlay was dismissed (scrim/swipe/back) | `overlay_id: str \| None = None` |
| `MenuSelectEvent` | an item selected from a menu/action sheet | `value: str`, `label: str` |
| `PanEvent` | a pan/drag reported per-frame and on release | `dx: float = 0.0`, `dy: float = 0.0`, `vx: float = 0.0`, `vy: float = 0.0` |
| `ScaleEvent` | a pinch (scale + rotation) with a focal point | `scale: float = 1.0`, `focus_x: float = 0.0`, `focus_y: float = 0.0`, `rotation: float = 0.0` |
| `DragEvent` | a drag-and-drop (picked up and, maybe, dropped) | `data: str = ""`, `x: float \| None = None`, `y: float \| None = None` |
| `ReorderEvent` | a list item dragged to another position | `from_index: int`, `to_index: int` |
| `SelectEvent` | an option selected from a dropdown/select | `value: str`, `index: int` |
| `TimeChangeEvent` | a time picker's value changed | `value: str` (24h `"HH:MM"`, `""` when cleared) |
| `RangeChangeEvent` | a range slider's bounds changed | `low: float`, `high: float` |
| `SubmitEvent` | a form (or completable input) was submitted | `values: dict[str, str] = {}` |
| `ValidationEvent` | a form field was validated | `field: str`, `value: str`, `error: str \| None = None` |
| `PageChangeEvent` | a `PageView`'s active page changed | `page: int`, `previous: int = 0` |
| `QrScanEvent` | a QR/barcode was decoded | `data: str`, `format: str = "QR_CODE"` |
| `CameraFrameEvent` | one RGB frame from a live camera preview | `width: int`, `height: int`, `data: str` (base64 of the `H×W×3` buffer), `rotation: int = 0` |
| `LifecycleEvent` | the app moved between lifecycle states | `state: AppState` |
| `SensorEvent` | one sample from a device sensor stream | `sensor: SensorType`, `values: list[float] = []`, `timestamp_ms: int = 0` |
| `ConnectivityEvent` | the device's network connectivity changed | `state: ConnectivityState` |
| `DeepLinkEvent` | the app was opened/resumed via a deep link | `url: str`, `params: dict[str, str] = {}` |
| `ThemeChangeEvent` | the active theme mode changed (dark/light) | `mode: ThemeMode` |
| `LocaleChangeEvent` | the locale / layout direction changed | `language: str`, `region: str \| None = None`, `rtl: bool = False` |

!!! info "Payloads are always JSON-serializable by construction"
    Notice that no event carries tuples or nested models. A `ScaleEvent` reports
    the focal point as **two top-level floats** (`focus_x`/`focus_y`), not a tuple;
    `RangeChangeEvent` sends `low`/`high` separately; `SensorEvent` sends a **flat
    list** of floats. This keeps every payload crossable over the bridge with no
    custom serialization.

!!! note "Events that don't come from a widget handler"
    `LifecycleEvent`, `SensorEvent`, `ConnectivityEvent`, `ThemeChangeEvent`, and
    `LocaleChangeEvent` are **not** emitted by a widget `on_*`. The host fires them
    and the bridge routes them over **reserved tokens** — `"__sensor__:<type>"`,
    `"__connectivity__:<state>"`, `"__theme__"`, `"__locale__"` — to `App` methods
    (`set_theme`, `set_locale`, …). They're platform events, not touch events.

## Event enums

Some events carry an enum instead of a free-form string, so the field has a closed
domain. All are `StrEnum`, so they serialize as the string value itself.

### `SwipeDirection`

The cardinal direction of a swipe gesture (carried by `SwipeEvent.direction`).

| Member | Value | Meaning |
| --- | --- | --- |
| `LEFT` | `"left"` | The pointer travelled predominantly toward the left edge (decreasing x). |
| `RIGHT` | `"right"` | The pointer travelled toward the right edge (increasing x). |
| `UP` | `"up"` | The pointer travelled toward the top of the screen (decreasing y). |
| `DOWN` | `"down"` | The pointer travelled toward the bottom of the screen (increasing y). |

### `SensorType`

The hardware sensor a continuous stream can be opened on (carried by
`SensorEvent.sensor`).

| Member | Value | Meaning |
| --- | --- | --- |
| `ACCELEROMETER` | `"accelerometer"` | Linear acceleration along x/y/z (incl. gravity), in m/s². |
| `GYROSCOPE` | `"gyroscope"` | Angular velocity (rate of rotation) about x/y/z, in rad/s. |
| `MAGNETOMETER` | `"magnetometer"` | Geomagnetic field along x/y/z, in microtesla — the compass basis. |
| `PRESSURE` | `"pressure"` | Ambient atmospheric (barometric) pressure, in hectopascals. |
| `LIGHT` | `"light"` | Ambient illuminance at the screen, in lux. |
| `PROXIMITY` | `"proximity"` | Nearness of an object to the front of the device (e.g. an ear), in cm. |
| `STEP_COUNTER` | `"step_counter"` | Cumulative steps since last boot, from the hardware pedometer. |

### `ConnectivityState`

The device's network connectivity state (carried by `ConnectivityEvent.state`).

| Member | Value | Meaning |
| --- | --- | --- |
| `CONNECTED` | `"connected"` | An active link of a generic/undistinguished transport. |
| `DISCONNECTED` | `"disconnected"` | No active link — requests fail until connectivity returns. |
| `WIFI` | `"wifi"` | Connected over Wi-Fi — typically unmetered, larger transfers OK. |
| `MOBILE` | `"mobile"` | Connected over cellular (mobile data) — typically metered. |

### `AppState`

The lifecycle state of the app process (carried by `LifecycleEvent.state`).

| Member | Value | Meaning |
| --- | --- | --- |
| `FOREGROUND` | `"foreground"` | Visible and receiving input — the active task in front of the user. |
| `BACKGROUND` | `"background"` | No longer visible; should pause UI work and release scarce resources. |
| `INACTIVE` | `"inactive"` | Transitional/partially-obscured — visible but not receiving input. |

## Handler aliases

Each `on_*` prop is typed by a **handler `TypeAlias`**. They aren't classes —
they're just **typed callables** that document which `Event` the handler receives
and let introspection emit a schema (a raw `Callable` has no JSON-schema
representation, so each alias carries a `WithJsonSchema` annotation).

Every event-bearing alias accepts **three shapes** for the same prop:

- `Callable[[YourEvent], Any]` — a sync handler that reads the event;
- `Callable[[YourEvent], Awaitable[Any]]` — its `async` version;
- a **zero-argument** handler (sync or `async`) for when the value doesn't matter.

The runtime only passes the event when the handler accepts a positional argument
(exactly what `handler_accepts_event` decides).

```python
from tempest_core import Slider, SlideHandler, SlideEvent


# All three shapes below are valid SlideHandlers.
def sync_handler(event: SlideEvent) -> None:
    """Read the new value synchronously."""
    print(event.value)


async def async_handler(event: SlideEvent) -> None:
    """Persist the new value asynchronously."""
    await store.save(event.value)


def bare_handler() -> None:
    """React without needing the value."""
    mark_dirty()


slider = Slider(on_change=sync_handler)  # (1)!
```

1. `Slider.on_change` is typed as `SlideHandler`, so any of the three shapes is
   accepted. The widget declares `{"on_change": SlideEvent}` in `event_schemas` —
   that's how the bridge knows to validate the payload into a `SlideEvent`.

| Alias | Event it delivers | Shows up on (examples) |
| --- | --- | --- |
| `EventHandler` | *(zero arguments)* | `Button.on_click`, `IconButton.on_click` |
| `TapHandler` | `TapEvent` | tap detectors, `on_double_tap` |
| `TextChangeHandler` | `TextChangeEvent` | `Input.on_change`, `TextArea.on_change` |
| `ToggleHandler` | `ToggleEvent` | `Checkbox.on_change`, `Switch.on_change` |
| `SlideHandler` | `SlideEvent` | `Slider.on_change` |
| `DateChangeHandler` | `DateChangeEvent` | `DatePicker.on_change` |
| `FileSelectHandler` | `FileSelectEvent` | `FilePicker.on_select` |
| `LongPressHandler` | `LongPressEvent` | long-press gestures |
| `SwipeHandler` | `SwipeEvent` | swipe gestures |
| `RouteChangeHandler` | `RouteChangeEvent` | `Navigator.on_change`, `TabBar.on_change` |
| `ScrollHandler` | `ScrollEvent` | virtualized lists |
| `RefreshHandler` | `RefreshEvent` | `RefreshControl` |
| `EndReachedHandler` | `EndReachedEvent` | paginated lists |
| `DismissHandler` | `DismissEvent` | `Dialog`, `BottomSheet`, `Dismissible` |
| `MenuSelectHandler` | `MenuSelectEvent` | `Menu.on_select`, `ActionSheet.on_select` |
| `PanHandler` | `PanEvent` | pan gesture (the same-named *widget* — see note) |
| `ScaleHandler` | `ScaleEvent` | pinch gesture (the same-named *widget* — see note) |
| `DragHandler` | `DragEvent` | `Draggable.on_drag`, `DragTarget.on_drop` |
| `ReorderHandler` | `ReorderEvent` | `ReorderableList.on_reorder` |
| `SelectHandler` | `SelectEvent` | `Dropdown.on_change` |
| `TimeChangeHandler` | `TimeChangeEvent` | `TimePicker.on_change` |
| `RangeChangeHandler` | `RangeChangeEvent` | `RangeSlider.on_change` |
| `SubmitHandler` | `SubmitEvent` | `Form.on_submit` |
| `ValidationHandler` | `ValidationEvent` | `FormField.on_validate` |
| `PageChangeHandler` | `PageChangeEvent` | `PageView.on_change` |

!!! warning "`PanHandler` and `ScaleHandler` are *widgets* at the package level"
    The `PanHandler`/`ScaleHandler` aliases live in `widgets.base`, but at the
    package level (`from tempest_core import PanHandler`) those names are the
    same-named **advanced-gesture widgets**, which **shadow** the aliases. The
    aliases stay private to `base`. If you want the *callback type*, it's `PanEvent`
    / `ScaleEvent` it receives; if you import `PanHandler`, you get the widget.

## Semantics & accessibility

Any node in the tree carries accessibility metadata via `Widget.semantics`, a
**`Semantics`** instance (a *frozen* `BaseModel`, so the reconciler diffs it by
value). The leaf renderers map these fields to the platform's accessibility
surface — `QAccessible` name/description on Qt, and
`Modifier.semantics { contentDescription; role }` on Compose — so TalkBack and Qt
AT can describe the node.

| Field | Type | What it carries |
| --- | --- | --- |
| `label` | `str \| None` | The accessible label (`contentDescription` / accessible name). |
| `role` | `str \| None` | Accessible role hint (e.g. `"button"`, `"image"`, `"heading"`); the renderer maps it to its native role enum. |
| `hint` | `str \| None` | An accessibility hint / tooltip describing what the node does. |

```python
from tempest_core import Container, Semantics

card = Container(
    semantics=Semantics(
        label="Product card",
        role="button",
        hint="Double-tap to open details",
    ),
)
```

!!! danger "Icon-only widgets depend on `Semantics` to not go mute"
    A button with no visible text has no derivable accessible label. That's why
    `IconButton` routes its `label` into the accessibility surface — without it,
    the node is mute to screen readers. Whenever a widget has no visible text, fill
    `semantics` (or the `label` the widget dedicates to a11y).

!!! note "`focusable` and `focus_order` travel with `Semantics`"
    Beyond `semantics`, every `Widget` exposes `focusable: bool | None` (accepts
    focus; `None` keeps the widget's natural focusability) and `focus_order: int |
    None` (explicit tab order; `None` uses the natural traversal order). Together
    with `Semantics`, they form the accessibility surface both renderers consume.

### A component carries the name you gave it

A component **is not a node**: `build` replaces it with the tree its `render`
returns, before any renderer sees the tree. So a prop that describes the node —
`semantics`, `focusable`, `focus_order`, `tag`, `attrs` — has to cross that
boundary, or it dies there.

```python
from tempest_core import Card, Semantics, Text, build

tree = build(
    Card(
        key="totals",
        semantics=Semantics(label="Budget totals"),  # (1)!
        children=[Text(content="$1,234.56")],
    )
)
print(tree.type)  # "Container"
print(tree.props["semantics"].label)  # "Budget totals"
```

1. The prop lives on every `Widget`'s base, so naming any component is just this —
   one line, with no `Container` wrapped around it to hang the name on.

```text
Container
Budget totals
```

!!! warning "Until 0.17.0 this did nothing"
    The prop was **declared and dropped**: naming a `Card` compiled, type-checked
    and reached no node at all. Measured over the 54 public components:
    `semantics` was dropped by **50** of them, and `focusable`, `focus_order`,
    `tag` and `attrs` by all **54**. If you wrapped a component in a `Container`
    just to be able to name it, that wrapper can go.

!!! info "Who wins, and why `style` stays out"
    **The render owns what it touched.** If the tree the component returns already
    sets the prop on any node, yours stays out — which is what keeps a field
    correct: it puts the accessible name on the `<input>` a screen reader stops at,
    and a second copy on the wrapper would announce the same control twice.
    `style` is **never** carried: a component is documented as reading
    `self.style` and folding it into the tree it returns, and several merge it into
    an inner node, so carrying it too would apply it twice. The canonical list is
    `CARRIED_PROPS`, exported from the package root.

## Recap

- **Two sides**: the `on_*` prop is the outside; `event_schemas` maps each prop to
  the typed `Event` it delivers.
- **`parse_event`** is the boundary gate: it validates a raw payload into a typed
  `Event` or raises `EventValidationError` with the structured errors.
- **`handler_accepts_event`** decides the convention: a one-argument handler
  receives the event; a zero-argument handler is called bare. Handlers may be sync
  or `async`.
- **~32 event types**, all inheriting from `Event` (*frozen*), with payloads always
  JSON-serializable (top-level floats, flat lists — never tuples).
- **Closed-domain enums**: `SwipeDirection`, `SensorType`, `ConnectivityState`,
  `AppState`.
- **Handler aliases** type each prop and accept sync/`async`/zero-arg; watch out
  that package-level `PanHandler`/`ScaleHandler` are the *widgets*.
- **A component carries them**: `semantics`, `focusable`, `focus_order`, `tag`
  and `attrs` (`CARRIED_PROPS`) cross the component boundary onto the root it
  renders — unless its own `render` already touched the prop; `style` never does,
  because the component folds it in.
- **`Semantics`** (`label` / `role` / `hint`) plus `focusable` / `focus_order` form
  the accessibility surface Qt and Compose consume.

For the full signatures, see the [API reference](../reference.md).
