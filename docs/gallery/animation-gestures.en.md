# Animation & gestures

This page covers the two widget families that give your UI **life and touch** in
`tempest-core`: the **animation** widgets (`Animated`, `AnimatedList`, `Hero`,
`Shimmer`, `Skeleton`) and the **gesture** widgets (`GestureDetector`,
`PanHandler`, `ScaleHandler`, `DoubleTapHandler`, `Draggable`, `DragTarget`,
`Dismissible`, `ReorderableList`, `InteractiveViewer`).

They all follow the core's philosophy: they declaratively describe the **intent**
(a duration, a curve, a typed handler) and the **interpolation or pointer
detection** runs in the engine, not in the renderers. The leaf renderers (Qt /
Compose) only realize the result — the core never touches pixels. 🚀

!!! info "What you'll learn here"
    - How `Animated` mounts a child that is **already interpolated per frame** by
      an `AnimationController` + `Tween`.
    - How `AnimatedList` animates enter/leave with a **duration + curve** per
      direction.
    - How `Hero` matches a geometry across screens in a **shared-element
      transition**.
    - How `Shimmer` and `Skeleton` become a **loading placeholder** with a
      gradient sweep.
    - Which **real gestures** each handler reports — tap, pan/fling,
      pinch/rotation, drag-and-drop, swipe-to-dismiss, reorder, and pan+zoom — and
      the typed event each one delivers.

## Animation

The animation widgets carry **only the metadata** the renderer needs to realize
the motion. The interpolation itself lives in the core: an `AnimationController`
advances a normalized value (0.0..1.0) on the app's frame clock and a `Tween`
interpolates between two endpoints with that value. The leaf renderer always sees
the **final** props for the current frame.

### `Animated`

A wrapper around a single child whose `style` the `view` already interpolated
each frame. You give it a `controller` (which advances the value) and, optionally,
the begin/end styles; the renderer just mounts the child already at this frame's
target.

```python
from tempest_core.widgets import Animated, Container, Text
from tempest_core.animation import AnimationController
from tempest_core.style import Curve, Style

# The controller ramps from 0.0 to 1.0 in 0.3s with a symmetric ease.
controller = AnimationController(duration_s=0.3, curve=Curve.EASE_IN_OUT)

card = Animated(
    child=Container(child=Text(content="Hello")),
    controller=controller,
    style_begin=Style(opacity=0.0),  # (1)!
    style_end=Style(opacity=1.0),
)
```

1. When `style_begin` is `None`, the child's own `style` becomes the start point.
   Just `style_end` is enough for a fade-in.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget` | *(required)* | The wrapped widget, mounted with the frame's interpolated style. |
| `controller` | `Any` | `None` | The `AnimationController` driving the interpolation (typed `Any` to avoid an import cycle through the core animation module). |
| `style_begin` | `Any` | `None` | The `Style` at `value == 0.0`, or `None` to use the child's own style as the start. |
| `style_end` | `Any` | `None` | The `Style` at `value == 1.0`, or `None`. |

!!! note "Interpolation lives in the core, not the renderer"
    The `view` reads the `controller`'s `value`, interpolates the `Tween` and
    folds the result into the child's `Style` — so Qt just mounts the child
    normally. The `controller` / `style_begin` / `style_end` fields stay on the
    node for introspection and device parity, but are **not consumed** by the Qt
    renderer's mount path (a documented Qt-vs-Compose divergence).

!!! tip "Pick the curve by feel, not by name"
    `AnimationController` accepts any `Curve` — `LINEAR` (constant speed),
    `EASE_IN` (accelerate), `EASE_OUT` (decelerate), `EASE_IN_OUT` (symmetric
    ease), `EASE` (the CSS default), `BOUNCE` (bounce at the end) and `ELASTIC`
    (spring-like oscillation). Each leaf maps to its native curve (`QEasingCurve`
    on Qt, `Easing` on Compose); the core itself approximates each so the
    test/simulator clock can interpolate without a renderer.

### `AnimatedList`

A flex container that animates its children **as they enter and leave**. It lays
the children out like a `Column`/`Row`, but on a structural change (an
`Insert`/`Remove` patch) the affected child is animated instead of
appearing/disappearing instantly.

```python
from tempest_core.widgets import AnimatedList, Container, Text
from tempest_core.style import Curve, FlexDirection

lst = AnimatedList(
    direction=FlexDirection.COLUMN,
    children=[
        Container(child=Text(content="Item 1")),
        Container(child=Text(content="Item 2")),
    ],
    enter_duration_ms=300,
    exit_duration_ms=300,
    enter_curve=Curve.EASE_OUT,  # enter decelerating
    exit_curve=Curve.EASE_IN,  # leave accelerating
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `direction` | `FlexDirection` | `COLUMN` | The main-axis direction (column or row). |
| `children` | `list[Widget]` | `[]` | The ordered child widgets. |
| `enter_duration_ms` | `int` | `300` | Enter-animation duration in milliseconds. |
| `exit_duration_ms` | `int` | `300` | Exit-animation duration in milliseconds. |
| `enter_curve` | `Curve` | `EASE_OUT` | The easing curve applied to the enter animation. |
| `exit_curve` | `Curve` | `EASE_IN` | The easing curve applied to the exit animation. |

!!! info "Enter and leave have their own curve and duration"
    The defaults — `EASE_OUT` to enter, `EASE_IN` to leave — follow the Material
    Motion convention: elements that **arrive** decelerate to rest, and elements
    that **depart** accelerate off-screen. Qt realizes this with a
    `QPropertyAnimation` on the child's opacity and maximum height; the device
    renderer wraps each child in `AnimatedVisibility` (a documented divergence).

### `Hero`

Tags a subtree as a **shared element** for a screen transition. When two screens
of a `Navigator` each hold a `Hero` with the same `hero_tag`, the renderer
interpolates the tagged subtree's geometry across the route transition.

```python
from tempest_core.widgets import Hero, Image

# On the list screen: the thumbnail.
thumb = Hero(hero_tag="photo-42", child=Image(src="photo-42-thumb.jpg"))

# On the detail screen: the same tag, larger image — the geometry interpolates between them.
detail = Hero(hero_tag="photo-42", child=Image(src="photo-42-full.jpg"))
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `hero_tag` | `str` | *(required)* | The shared-element identity (must match across screens). |
| `child` | `Widget` | *(required)* | The wrapped widget that participates in the transition. |

!!! warning "The `hero_tag` must be unique within each screen"
    The transition matches **one** source `Hero` with **one** destination `Hero`
    by tag. Two subtrees with the same tag on the same screen make the pairing
    ambiguous. Qt animates the geometry with a `QPropertyAnimation`; Compose uses
    `SharedTransitionLayout` + `Modifier.sharedElement` (a documented divergence).

### `Shimmer`

A **loading placeholder** that sweeps a gradient highlight over a child. It wraps
a child (usually a skeleton layout) and animates a diagonal band from
`base_color` toward `highlight_color` and back, in a loop — the classic "content
is loading" shimmer.

```python
from tempest_core.widgets import Shimmer, Column, Skeleton
from tempest_core.style import Color

loading = Shimmer(
    child=Column(
        children=[
            Skeleton(height=16.0),
            Skeleton(height=16.0, width=180.0),
        ]
    ),
    base_color=Color(r=224, g=224, b=224),  # resting tone
    highlight_color=Color(r=245, g=245, b=245),  # moving highlight tone
    duration_ms=1200,
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget` | *(required)* | The wrapped widget the shimmer paints over. |
| `base_color` | `Color` | `Color(224, 224, 224)` | The resting tone of the gradient. |
| `highlight_color` | `Color` | `Color(245, 245, 245)` | The moving highlight tone. |
| `duration_ms` | `int` | `1200` | The duration of one full sweep, in milliseconds. |

!!! tip "Shimmer is the wrapper; Skeleton is the leaf"
    Use `Shimmer` to paint the sweep over a whole layout of placeholders, and
    `Skeleton` for each individual rectangle (text line, avatar) inside it. Qt
    drives the gradient with a `QTimer` repaint loop; the device renderer uses an
    `InfiniteTransition` + `Brush.linearGradient` (a documented divergence).

### `Skeleton`

The **childless** variant of `Shimmer`: a single rounded rectangle that sweeps the
gradient, used to stand in for a text line or an avatar while the real content
loads.

```python
from tempest_core.widgets import Skeleton

# A fixed-width text line.
line = Skeleton(width=200.0, height=16.0, radius=4.0)

# A square avatar, tinted by the "primary" color family in the active theme.
avatar = Skeleton(width=48.0, height=48.0, radius=24.0, color_scheme="primary")
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `width` | `float \| None` | `None` | The fixed width in logical pixels, or `None` to flex. |
| `height` | `float \| None` | `None` | The fixed height in logical pixels, or `None` to flex. |
| `radius` | `float` | `4.0` | The corner radius in logical pixels. |
| `base_color` | `Color` | `Color(224, 224, 224)` | The resting tone of the gradient. |
| `highlight_color` | `Color` | `Color(245, 245, 245)` | The moving highlight tone. |
| `duration_ms` | `int` | `1200` | The duration of one full sweep, in milliseconds. |
| `color_scheme` | `str` | `"neutral"` | The M3 role family the renderer may tint the shimmer tones with. |

!!! note "`color_scheme` is resolved by the renderer against the active theme"
    The engine only **carries** the `color_scheme` prop; the renderer resolves it
    against the active theme (H4). The default `"neutral"` gives the classic grey
    shimmer. Pass `"primary"` / `"secondary"` / etc. for a tinted placeholder that
    matches the surface it lives on.

## Gestures

`GestureDetector` is the framework's base gesture primitive: a single-child
container that renders its child untouched but watches the pointer over it,
turning press/drag/release sequences into **typed events**. The advanced gesture
widgets specialize that contract for richer interactions.

!!! warning "Wrap non-interactive content"
    Gestures work best around content that does **not** consume the pointer (a
    card, an image, a row of text). A child that already handles the pointer
    itself (e.g. a `Button`) keeps its own handling — a documented v1 limit. Both
    leaf renderers realize the same contract: Qt via pointer event filters /
    `QGraphicsView` / `QDrag`; Compose via `Modifier.pointerInput` /
    `SwipeToDismissBox` / `graphicsLayer`.

### `GestureDetector`

The base detector: reports tap, double-tap, long-press and directional swipe over
its child. Each handler is optional and may be sync or `async`.

```python
from tempest_core.widgets import GestureDetector, Container, Text

card = GestureDetector(
    child=Container(child=Text(content="Tap, hold or swipe")),
    on_tap=lambda e: print("tap"),
    on_double_tap=lambda e: print("double tap"),
    on_long_press=lambda e: print("long press"),
    on_swipe=lambda e: print("swipe", e.direction),  # (1)!
)
```

1. The `SwipeEvent` carries the dominant cardinal direction and the total travel
   (see the [API reference](../reference.md)).

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the gestures are detected over. |
| `on_tap` | `TapHandler \| None` | `None` | Handler for a single tap (receives `TapEvent`). |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler for a double tap (receives `TapEvent`). |
| `on_long_press` | `LongPressHandler \| None` | `None` | Handler for a press held past the threshold (receives `LongPressEvent`). |
| `on_swipe` | `SwipeHandler \| None` | `None` | Handler for a directional swipe (receives `SwipeEvent`). |

### `PanHandler`

Reports a **continuous pan**: as the pointer drags over the child, the renderer
delivers per-frame deltas and, at release, the fling velocity, as a `PanEvent`.

```python
from tempest_core.widgets import PanHandler, Container, Text

draggable = PanHandler(
    child=Container(child=Text(content="Drag me")),
    on_pan=lambda e: app.set_state(x=e.dx, y=e.dy),  # (1)!
)
```

1. The handler is called per frame during the drag; use the deltas to move the
   content and the final velocity for a fling.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the pan is detected over. |
| `on_pan` | `EventHandler \| None` | `None` | Handler for the pan gesture (receives `PanEvent`). |

!!! danger "`PanHandler` and `ScaleHandler` are *widgets*, not the handler aliases"
    The public `PanHandler` and `ScaleHandler` symbols re-exported from
    `tempest_core.widgets` are the **widgets** on this page. They deliberately
    shadow the same-named handler TypeAliases, which stay **private** to the
    `base` module. That's why the *Type* column of `on_pan` above says
    `EventHandler | None`: it's a callable (sync or `async`) that receives the
    `PanEvent`, not the widget.

### `ScaleHandler`

Reports **pinch** (scale + rotation) and a double-tap. `on_scale` receives a
`ScaleEvent` with the cumulative scale, focal point and rotation; the double-tap
is the common pairing to reset the zoom.

```python
from tempest_core.widgets import ScaleHandler, Image

photo = ScaleHandler(
    child=Image(src="map.png"),
    on_scale=lambda e: app.set_state(scale=e.scale),
    on_double_tap=lambda e: app.set_state(scale=1.0),  # reset the zoom
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the gestures are detected over. |
| `on_scale` | `EventHandler \| None` | `None` | Handler for a pinch (receives `ScaleEvent` with cumulative scale, focal point and rotation). |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler for a double tap (receives `TapEvent`; common pairing to reset the zoom). |

### `DoubleTapHandler`

The leanest case: just a **double tap**. Handy for "double-tap to like" or a zoom
shortcut without the cost of the pinch.

```python
from tempest_core.widgets import DoubleTapHandler, Image

likeable = DoubleTapHandler(
    child=Image(src="post.jpg"),
    on_double_tap=lambda e: app.set_state(liked=True),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the double tap is detected over. |
| `on_double_tap` | `TapHandler \| None` | `None` | Handler for a double tap (receives `TapEvent`). |

### `Draggable`

A child that can be **picked up and dragged** onto a `DragTarget`. The `drag_data`
is an opaque label carried to the drop target via `DragEvent.data`, so the target
can identify what landed on it.

```python
from tempest_core.widgets import Draggable, Container, Text

card = Draggable(
    child=Container(child=Text(content="King of Spades")),
    drag_data="king-spades",  # identifies the item at the target
    on_drag=lambda e: print("dropped", e.data),  # (1)!
)
```

1. `on_drag` fires when the drag finishes, with the carried data and the release
   position.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the user drags. |
| `drag_data` | `str` | `""` | An opaque label carried to the drop target via `DragEvent.data`, so the target can identify what landed on it. |
| `on_drag` | `DragHandler \| None` | `None` | Handler fired when the drag finishes (receives `DragEvent` with the carried data and the release position). |

### `DragTarget`

A child that **accepts** a dropped `Draggable`. `on_drop` fires when a draggable
is released over the target, receiving the `DragEvent` with the item's data.

```python
from tempest_core.widgets import DragTarget, Container, Text

pile = DragTarget(
    child=Container(child=Text(content="Drop cards here")),
    on_drop=lambda e: app.play_card(e.data),  # (1)!
)
```

1. `Draggable` + `DragTarget` form the drag-and-drop pair: the former's
   `drag_data` arrives in the latter's `DragEvent.data`.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget that acts as the drop region. |
| `on_drop` | `DragHandler \| None` | `None` | Handler fired when a draggable is released over this target (receives `DragEvent` with the dropped item's data). |

### `Dismissible`

A child that can be **swiped away** to dismiss it (swipe-to-delete). `direction`
sets the swipe direction that triggers the dismiss; `on_dismiss` fires once the
swipe passes the threshold.

```python
from tempest_core.widgets import Dismissible, Container, Text, SwipeDirection

item = Dismissible(
    child=Container(child=Text(content="Swipe to delete")),
    direction=SwipeDirection.LEFT,  # dismiss on a left swipe
    on_dismiss=lambda e: app.remove_item(),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget the dismiss gesture is detected over. |
| `direction` | `SwipeDirection` | `LEFT` | The swipe direction that triggers the dismiss (`LEFT` / `RIGHT` / `UP` / `DOWN`). |
| `on_dismiss` | `DismissHandler \| None` | `None` | Handler fired once the swipe passes the threshold (receives `DismissEvent`; reuses the overlay-dismiss event type). |

!!! note "`on_dismiss` reuses the overlay `DismissEvent`"
    There's no new event for swipe-to-dismiss: it reuses the `DismissEvent` also
    used when an overlay is closed. One less event surface for the core to carry.

### `ReorderableList`

A vertical list whose items can be **dragged into a new order**. The handler
typically mutates its backing list (`items.insert(to_index, items.pop(from_index))`)
and re-renders; a keyed child list then diffs to a `Reorder` patch.

```python
from tempest_core.widgets import ReorderableList, Container, Text


def reorder(e):
    items.insert(e.to_index, items.pop(e.from_index))
    app.rebuild()


lst = ReorderableList(
    children=[
        Container(key="a", child=Text(content="First")),
        Container(key="b", child=Text(content="Second")),
        Container(key="c", child=Text(content="Third")),
    ],
    on_reorder=reorder,  # (1)!
)
```

1. The `ReorderEvent` carries the source and destination index.

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `children` | `list[Widget]` | `[]` | The ordered list items. Prefer stable `key`s so the diff emits a `Reorder`. |
| `on_reorder` | `ReorderHandler \| None` | `None` | Handler fired when an item is dragged to a new slot (receives `ReorderEvent` with source and destination). |

!!! tip "Use stable `key`s to diff as a `Reorder`"
    With stable `key`s, the keyed diff recognizes that items merely swapped places
    and emits a `Reorder` patch (the A2 mechanism) instead of positional updates —
    no new patch kind is needed.

### `InteractiveViewer`

A single-child container the user can **pan and zoom** (pinch + drag), clamped
between `min_scale` and `max_scale`. `on_interaction` fires as the view
transforms, with the current scale, focal point and rotation.

```python
from tempest_core.widgets import InteractiveViewer, Image

viewer = InteractiveViewer(
    child=Image(src="floor-plan.png"),
    min_scale=0.5,
    max_scale=4.0,
    on_interaction=lambda e: app.set_state(scale=e.scale),
)
```

#### Props

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `child` | `Widget \| None` | `None` | The wrapped widget that is panned and zoomed. |
| `min_scale` | `float` | `0.5` | The minimum allowed zoom factor. |
| `max_scale` | `float` | `4.0` | The maximum allowed zoom factor. |
| `on_interaction` | `EventHandler \| None` | `None` | Handler fired as the view transforms (receives `ScaleEvent` with scale, focal point and rotation). |

!!! info "`InteractiveViewer` vs. `ScaleHandler`"
    Both deliver a `ScaleEvent`, but with different roles: `ScaleHandler` only
    **reports** the pinch for you to apply the effect, whereas `InteractiveViewer`
    already **transforms** the child (pan + zoom) within the
    `min_scale`/`max_scale` bounds and notifies you of the transform. Pick the
    viewer when you want ready-made pan+zoom; the handler when you want to control
    the effect yourself.

## Recap

- **Animation declares the intent, the core interpolates.** `Animated` mounts a
  child already at the frame's target (driven by an `AnimationController` +
  `Tween`); `AnimatedList` animates enter/leave with their own **duration +
  `Curve`** per direction.
- **Curves** come from the `Curve` enum: `LINEAR` / `EASE_IN` / `EASE_OUT` /
  `EASE_IN_OUT` / `EASE` / `BOUNCE` / `ELASTIC`, each mapped to the leaf's native
  curve.
- **`Hero`** matches a geometry across screens by `hero_tag` in a shared-element
  transition — the tag must be unique per screen.
- **`Shimmer`** paints a gradient sweep over a layout; **`Skeleton`** is the
  childless leaf, with `color_scheme` resolved by the renderer against the theme.
- **`GestureDetector`** is the base primitive (tap / double-tap / long-press /
  swipe); the advanced ones specialize: `PanHandler` (pan + fling),
  `ScaleHandler` (pinch + rotation + double-tap), `DoubleTapHandler`
  (double-tap only).
- **`Draggable` + `DragTarget`** form drag-and-drop via `drag_data` →
  `DragEvent.data`; **`Dismissible`** does swipe-to-dismiss; **`ReorderableList`**
  drags to reorder (with stable `key`s); **`InteractiveViewer`** gives ready-made
  pan + zoom, clamped by `min_scale`/`max_scale`.
- **`PanHandler` and `ScaleHandler` are widgets** re-exported from
  `tempest_core.widgets` — they deliberately shadow the same-named handler aliases,
  which stay private to `base`.
