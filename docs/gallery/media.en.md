# Media & Canvas

After the simple text and button leaves, this is the **rich** surface of
`tempest-core`: bitmaps and icons, a **retained-mode `Canvas`** (a serializable
list of draw commands), video/web/SVG embeds, live camera and QR scanning, an
embedded map, and the visual-effect wrappers
(`Blur` / `BackdropFilter` / `ClipPath`). 🎨

Everything here follows the same rule as the rest of the IR: **JSON-serializable
values only**. Colors in `Canvas` commands are `[r, g, b, a]` lists of floats in
`[0, 1]` — never tuples, never `Color` objects — so the same list reaches both
leaf renderers (Qt via `QPainter`; Compose via `drawIntoCanvas`) untranslated.

!!! info "What you'll learn here"
    - The **image and icon** leaves (`Image`, `Icon`, `Svg`) and the `ImageFit`
      enum that decides how content scales inside its box.
    - How the **`Canvas` is a declarative drawing model**: a *command list*
      (`MoveTo`, `LineTo`, `FillCmd`, …) the renderers replay each paint.
    - The **advanced and device-media surfaces**: video, web view, camera, QR
      scanner, map — and the effect wrappers (`Blur`, `BackdropFilter`,
      `ClipPath`).

## Image & icons

The visual baseline: get a pixel or a vector onto the screen and say **how it
scales** inside its box. Three leaves (`Image`, `Icon`, `Svg`) and one shared enum
(`ImageFit`).

### `ImageFit`

The scaling vocabulary, borrowed from CSS `object-fit`. It shows up on `Image.fit`
and `Svg.fit`, and decides what happens when the content's aspect ratio doesn't
match the box's.

| Member | Value | What it does |
| --- | --- | --- |
| `CONTAIN` | `"contain"` | Scale preserving the aspect ratio until the image fits **entirely** in the box. The whole image is visible; empty space (letterboxing) may remain on the unfilled axis. |
| `COVER` | `"cover"` | Scale preserving the aspect ratio until it **covers** the whole box. No empty space; whatever overflows the longer axis is cropped. |
| `FILL` | `"fill"` | Stretch to the box's exact width and height, **ignoring** the aspect ratio. Nothing is cropped, but the image may look distorted. |
| `NONE` | `"none"` | Do not scale; render at the intrinsic pixel size. Larger than the box → clipped; smaller → centered with surrounding space. |

```python
from tempest_core import ImageFit

ImageFit.CONTAIN  # fits entirely, may leave space
ImageFit.COVER    # covers everything, may crop
```

!!! tip "`CONTAIN` vs. `COVER`"
    The choice is almost always between these two: `CONTAIN` when **no pixel may
    disappear** (a logo, a diagram) and `COVER` when the box **must not have a
    hole** (a banner, a background avatar). `FILL` distorts and `NONE` ignores the
    box — reach for them only when that's exactly what you want.

### `Image`

A bitmap loaded from a URL or a bundled asset. In the minimal case, only `src`:

```python
from tempest_core import Image, ImageFit

cover = Image(
    src="https://picsum.photos/800/600",
    fit=ImageFit.COVER,
    alt="Article cover photo",
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `src` | `str` | *(required)* | The image source — an `http(s)` URL or a bundled asset path. |
| `fit` | `ImageFit` | `CONTAIN` | How the image scales within its box. |
| `alt` | `str` | `""` | Alternative text shown if the image cannot be loaded. |

!!! note "`alt` is accessibility, not decoration"
    `alt` becomes the alternative text (the HTML `alt` equivalent): it shows if the
    image fails and is what screen readers announce. Fill it in whenever the image
    carries information.

### `Icon`

A vector icon. `name` may be one of the framework's **curated** names (e.g.
`"search"`, `"home"`) — in which case the renderer strokes the built-in
single-path geometry — or an arbitrary platform icon identifier; when neither
resolves, the renderer falls back to showing the name itself.

```python
from tempest_core import Icon

magnifier = Icon(name="search", size=20.0)
house = Icon(name="home")  # renderer default size
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `name` | `str` | *(required)* | The icon identifier — a curated value (or its string) or a platform name. |
| `size` | `float \| None` | `None` | The icon's edge length in logical pixels, or `None` for the renderer default. |

### `Svg`

A scalable vector graphic loaded from a URL or asset. Unlike `Icon` (a single path
geometry), `Svg` renders a whole SVG document, and reuses the same `ImageFit` as
`Image` to scale:

```python
from tempest_core import Svg, ImageFit

logo = Svg(src="assets/logo.svg", fit=ImageFit.CONTAIN)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `src` | `str` | *(required)* | The SVG source — an `http(s)` URL or an asset path. |
| `fit` | `ImageFit` | `CONTAIN` | How the vector scales within its box. |

## Canvas & drawing vocabulary

`Canvas` doesn't draw through imperative calls — it **interprets a command list**.
That list *is* the drawing IR: a serializable, value-diffable sequence of
`DrawCommand` that both leaf renderers replay each paint. You build the scene as
data; the reconciler diffs the list by value and emits a single `Update` with the
new list when something changes.

A `DrawCommand` is a **discriminated union** (on the `kind` field) of nine frozen
value models. Think of them as a small drawing vocabulary, with two groups:

- **Path construction** — accumulate geometry into the active path: `MoveTo`,
  `LineTo`, `ArcTo`, `Close`, `DrawRect`, `DrawOval`.
- **Painting** — consume the active path (and reset it): `FillCmd`, `StrokeCmd`.
  Plus `DrawText`, which paints text directly at a point.

The core idea: **one shape = geometry + paint**. A line is
`MoveTo` + `LineTo` + `StrokeCmd`. A filled bar is `DrawRect` + `FillCmd`. You
first describe *where*, then say *how to paint*.

### `Canvas`

The retained-mode surface that interprets the list.

```python
from tempest_core import (
    Canvas,
    MoveTo,
    LineTo,
    StrokeCmd,
    DrawRect,
    FillCmd,
)

chart = Canvas(
    width=200.0,
    height=120.0,
    commands=[
        # A line: move the point, trace to the next, then stroke.
        MoveTo(x=0.0, y=100.0),
        LineTo(x=200.0, y=20.0),
        StrokeCmd(color=[0.1, 0.5, 0.9, 1.0], width=2.0),
        # A bar: describe the rectangle, then fill.
        DrawRect(x=20.0, y=60.0, width=40.0, height=60.0),
        FillCmd(color=[0.9, 0.3, 0.2, 1.0]),
    ],
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `commands` | `list[DrawCommand]` | `[]` | The ordered draw commands replayed each paint. |
| `width` | `float \| None` | `None` | Optional fixed canvas width, in logical pixels. |
| `height` | `float \| None` | `None` | Optional fixed canvas height, in logical pixels. |

!!! info "Order is the semantics"
    Commands run **in order**, like layers of paint: a paint command
    (`FillCmd` / `StrokeCmd`) consumes everything accumulated into the path *so
    far* and **resets** it. So each painted shape is a `geometry… → paint` block,
    and the next shape starts fresh.

### Path-construction commands

| Command | `kind` | Fields (default) | What it does |
| --- | --- | --- | --- |
| `MoveTo` | `"move_to"` | `x`, `y` | Move the current point of the path **without drawing**. |
| `LineTo` | `"line_to"` | `x`, `y` | Add a straight line from the current point to `(x, y)`. |
| `ArcTo` | `"arc_to"` | `x`, `y`, `width`, `height`, `start_angle`, `sweep_angle` | Add an elliptical arc within box `(x, y, width, height)`; angles in **degrees**. |
| `Close` | `"close"` | — | Close the active subpath back to its start point. |
| `DrawRect` | `"draw_rect"` | `x`, `y`, `width`, `height` | Add a rectangle to the active path. |
| `DrawOval` | `"draw_oval"` | `x`, `y`, `width`, `height` | Add an ellipse (oval) within box `(x, y, width, height)`. |

```python
from tempest_core import MoveTo, LineTo, ArcTo, Close, DrawRect, DrawOval

MoveTo(x=10.0, y=10.0)
LineTo(x=90.0, y=10.0)
ArcTo(x=0.0, y=0.0, width=100.0, height=100.0, start_angle=0.0, sweep_angle=90.0)
Close()
DrawRect(x=0.0, y=0.0, width=50.0, height=30.0)
DrawOval(x=0.0, y=0.0, width=50.0, height=50.0)
```

!!! note "`DrawRect` / `DrawOval` accumulate geometry, they don't paint"
    Despite the `Draw` prefix, these two only **add the shape to the active
    path** — nothing appears until a later `FillCmd` or `StrokeCmd`. `DrawText` is
    the exception: it paints immediately.

### Paint commands

| Command | `kind` | Fields (default) | What it does |
| --- | --- | --- | --- |
| `FillCmd` | `"fill"` | `color` | Fill the active path with a solid color and reset the path. |
| `StrokeCmd` | `"stroke"` | `color`, `width` (`1.0`) | Stroke the active path's outline and reset the path. |
| `DrawText` | `"draw_text"` | `text`, `x`, `y`, `size` (`14.0`), `color` (`[0,0,0,1]`) | Draw a run of text at the baseline anchor `(x, y)`. |

```python
from tempest_core import FillCmd, StrokeCmd, DrawText

FillCmd(color=[0.2, 0.7, 0.4, 1.0])
StrokeCmd(color=[0.0, 0.0, 0.0, 1.0], width=3.0)
DrawText(text="42", x=12.0, y=24.0, size=16.0, color=[0.1, 0.1, 0.1, 1.0])
```

!!! warning "Color is always an `[r, g, b, a]` list of floats in `[0, 1]`"
    Every color-bearing command (`FillCmd`, `StrokeCmd`, `DrawText`) uses a
    **list** of four normalized floats — never a tuple, never `0–255`, never a
    `Color` object. That's what keeps the command directly JSON-serializable via
    `model_dump()`. Pure opaque red is `[1.0, 0.0, 0.0, 1.0]`.

## Advanced & device-media surfaces

Here the leaf delegates to a real platform capability: a video decoder, a web
engine, the camera, the map. The core still never touches pixels — it only
describes *what* to embed and *how* to react to the events the platform emits.

### `VideoPlayer`

An embedded video player.

```python
from tempest_core import VideoPlayer

clip = VideoPlayer(
    src="https://cdn.example.com/intro.mp4",
    autoplay=True,
    loop=True,
    muted=True,      # silent autoplay — the common mobile/web policy
    controls=False,
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `src` | `str` | *(required)* | The video source — an `http(s)` URL or an asset path. |
| `autoplay` | `bool` | `False` | Whether playback starts automatically when mounted. |
| `loop` | `bool` | `False` | Whether playback restarts when it reaches the end. |
| `controls` | `bool` | `True` | Whether the platform transport controls are shown. |
| `muted` | `bool` | `False` | Whether the audio track starts muted. |

### `WebView`

An embedded web view rendering a remote page.

```python
from tempest_core import WebView

docs = WebView(url="https://example.com/help", javascript_enabled=True)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `url` | `str` | *(required)* | The page URL to load. |
| `javascript_enabled` | `bool` | `True` | Whether JavaScript execution is allowed. |

### `CameraPreview`

A live camera preview surface that **optionally streams frames** to the app.
Without `on_frame` it's just a preview. With `on_frame`, the device attaches an
`ImageAnalysis` stage (keeping only the latest frame) and invokes the handler with
a `CameraFrameEvent` at most every `frame_interval_ms`.

```python
from tempest_core import CameraPreview

async def on_frame(event):
    # rebuild the array with tempestroid.vision.frame_array and run inference
    ...

camera = CameraPreview(
    facing="back",
    on_frame=on_frame,
    frame_interval_ms=300,
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `facing` | `str` | `"back"` | Which camera to use (`"front"` or `"back"`). |
| `on_frame` | `EventHandler \| None` | `None` | Handler invoked with a `CameraFrameEvent` per (throttled) frame; sync or `async`. |
| `frame_interval_ms` | `int` | `300` | Minimum gap between emitted frames, in ms (ignored when `on_frame` is unset). |

!!! tip "The throttle exists because inference is slower than the camera"
    The camera delivers dozens of frames per second; an on-device model takes far
    longer than that per frame. `frame_interval_ms` decouples the two — keeping
    only the latest frame — so you don't pile up work that never catches the feed.

### `QrScanner`

A live camera surface that scans QR/barcodes and reports each result.

```python
from tempest_core import QrScanner

def on_scan(event):
    print("scanned code:", event)

scanner = QrScanner(on_scan=on_scan)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `on_scan` | `EventHandler \| None` | `None` | Handler invoked with a `QrScanEvent` for each decoded code; sync or `async`. |

### `MapView`

An embedded map centered on a coordinate, with optional markers.

```python
from tempest_core import MapView

map_view = MapView(
    latitude=-23.5505,
    longitude=-46.6333,
    zoom=14.0,
    markers=[
        {"lat": -23.5505, "lng": -46.6333, "title": "São Paulo"},
    ],
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `latitude` | `float` | `0.0` | The map center latitude, in degrees. |
| `longitude` | `float` | `0.0` | The map center longitude, in degrees. |
| `zoom` | `float` | `12.0` | The map zoom level. |
| `markers` | `list[dict[str, Any]]` | `[]` | JSON-serializable marker descriptors (each a dict, e.g. `{"lat": …, "lng": …, "title": …}`); the list crosses the boundary as-is. |

!!! note "Markers are plain dicts, not widgets"
    Each marker is a JSON-serializable `dict` the native renderer interprets — the
    exact shape (`lat` / `lng` / `title` …) is a data contract, not a widget
    subtree.

### Effects: `Blur`, `BackdropFilter`

Two wrappers that blur — the difference is **what**. `Blur` blurs its own child;
`BackdropFilter` blurs the **layers behind** the child (a semantic alias, for
frosted glass over content). Both share the same fields.

```python
from tempest_core import Blur, BackdropFilter, Image, Text

frosted = Blur(radius=12.0, child=Image(src="assets/photo.jpg"))
glass = BackdropFilter(radius=16.0, child=Text(value="Overlaid"))
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `radius` | `float` | `8.0` | The blur radius, in logical pixels. |
| `child` | `Widget \| None` | `None` | The optional wrapped widget. |

!!! info "`Blur` vs. `BackdropFilter`"
    Same mechanics, different targets: use `Blur` to blur **the child's content** (a
    censored photo, a placeholder) and `BackdropFilter` to blur **what's behind**
    the child (a translucent bar over the page).

### Clipping: `ClipShape`, `ClipPath`

`ClipPath` clips its child to a predefined shape, picked by the `ClipShape` enum.

| `ClipShape` | Value | What it does |
| --- | --- | --- |
| `CIRCLE` | `"circle"` | Clip to a **circle** inscribed in the box (uses the shorter side as diameter on a non-square box). Great for avatars. |
| `ROUNDED_RECT` | `"rounded_rect"` | Clip to a rounded-corner rectangle, using `radius` as the corner radius. Radius `0` ≈ a plain rectangle. |
| `OVAL` | `"oval"` | Clip to an **ellipse** filling the box's full width and height (it stretches; a non-square box yields an oval, not a circle). |

```python
from tempest_core import ClipPath, ClipShape, Image

avatar = ClipPath(
    shape=ClipShape.CIRCLE,
    child=Image(src="assets/profile.jpg"),
)

card = ClipPath(
    shape=ClipShape.ROUNDED_RECT,
    radius=16.0,
    child=Image(src="assets/banner.jpg"),
)
```

| Prop | Type | Default | What it does |
| --- | --- | --- | --- |
| `shape` | `ClipShape` | `ROUNDED_RECT` | The clipping shape. |
| `radius` | `float` | `8.0` | The corner radius for `ROUNDED_RECT`, in logical pixels. |
| `child` | `Widget \| None` | `None` | The optional wrapped widget. |

!!! warning "`CIRCLE` vs. `OVAL` on a non-square box"
    Both become a circle when the box is square. On a rectangular box, `CIRCLE`
    uses the **shorter side** (stays round, centered) and `OVAL` **stretches** to
    fill both axes (becomes oval). `radius` only has an effect on `ROUNDED_RECT`.

## Recap

- **Image & icons**: `Image` (bitmap), `Icon` (vector path) and `Svg` (vector
  document) get content onto the screen; `ImageFit`
  (`CONTAIN` / `COVER` / `FILL` / `NONE`) decides how it scales in the box.
- **`Canvas` is a declarative drawing model**: a `list[DrawCommand]` the renderers
  replay. Order is the semantics and each shape is `geometry → paint`.
- **Command vocabulary**: path construction (`MoveTo`, `LineTo`, `ArcTo`, `Close`,
  `DrawRect`, `DrawOval`) + painting (`FillCmd`, `StrokeCmd`, `DrawText`). A line =
  `MoveTo` + `LineTo` + `StrokeCmd`; a bar = `DrawRect` + `FillCmd`. Colors are
  `[r, g, b, a]` lists in `[0, 1]`.
- **Device surfaces**: `VideoPlayer`, `WebView`, `CameraPreview` (with `on_frame`
  throttled by `frame_interval_ms`), `QrScanner`, `MapView`.
- **Effects and clipping**: `Blur` (the child) vs. `BackdropFilter` (behind the
  child); `ClipPath` clips to `ClipShape.CIRCLE` / `ROUNDED_RECT` / `OVAL`.

All fields and shapes are just JSON-serializable data — see the full types in the
[API reference](../reference.md).
