# Changelog

All notable changes to **tempest-core** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to semantic
versioning.

## [0.13.0] - 2026-08-22

### Added

- **The package root re-exports every public name its submodules declare** —
  343 symbols, up from 101. `from tempest_core import Input` (and `Image`,
  `Checkbox`, `Icon`, `Stack`, `Slider`, `Switch`, `Form`, `Dialog`, `Canvas`,
  `ProgressBar`, `Spinner`, and 231 more) now works.

  The gap was not cosmetic: with two thirds of the surface missing from the root,
  a consumer had no choice but to import from `tempest_core.widgets.inputs` and
  friends. Measured in tempestweb: **50 files** reaching into submodules, against
  that project's own rule of importing from the package root. A partial root is a
  root that teaches people to bypass it.

  Each name is re-exported in **both** forms — `from x import Y as Y` *and* an
  entry in `__all__`. That redundancy is what keeps strict type checkers quiet:
  without the `as` form, basedpyright and Pylance report "private import usage"
  at every consumer call site, and `__all__` alone does not silence it.

- **`tests/test_public_surface.py`** — the guard that keeps the root and the
  submodules from drifting again. It fails when a submodule gains a public name
  the root does not re-export, when `__all__` names something the root cannot
  hand over, when two submodules export the same name (which would make the
  root's meaning depend on import order), and when a re-export loses its `as`
  form.

- **`ActionSheet.on_dismiss`** — the dismissal contract its siblings already had.
  An action sheet is presented modally, so a renderer reports the scrim tap and
  the Escape key; there was nowhere to send that, so a sheet whose actions did
  not close it trapped the reader. That got worse once a renderer started
  trapping focus inside modal overlays, which the web client now does.

### Fixed

- **`mkdocs build --strict` was already failing before this release**, on a
  relative link from the English reference page to a generated directory
  (`../reference/`), which MkDocs reports as unrecognized. The English page now
  points at the generated reference with an absolute URL — there is one generated
  page, not a translated pair, because the docstrings are English either way.

- **`Tween`'s docstring used a `Type Args:` section**, which griffe reads as a
  parameter list and then reports as not appearing in the signature. It only
  surfaced now because `Tween` was one of the symbols the root did not
  re-export, so the reference never rendered it.

### Docs

- Every example in the docs imports from the root (240 import statements
  rewritten), and the three places that told the reader to import from a
  subpackage now say the opposite, because the reason for that advice is gone.

## [0.12.0] - 2026-08-21

### Added

- **`App.theme` finally reaches the components the view builds.** It existed
  and was inert: every themed component declares `theme` with a baseline
  default factory, `build` knew nothing about the app, and nothing connected
  the two. An app that generated a brand palette with `Theme.from_seed` still
  rendered Material-purple buttons, because a component resolves its colors at
  **construction** and writes them into its style. Measured in a real Mode B
  app: `--tw-primary` was the brand slate on `:root` while the button computed
  `rgb(88, 71, 133)`.

  `theme.current_theme()` and `theme.use_theme(theme)` are the connection.
  `App._build` installs the app's theme around the view call — which is when
  components are constructed — and the 46 component fields now default to
  `current_theme` instead of a fresh baseline. No call site changes, no
  signature changes: an app sets `App(theme=...)` and its palette is what the
  tree wears.

  Outside a build `current_theme()` answers the baseline, so a widget built in
  a test, a script or a REPL behaves exactly as before. A theme passed
  explicitly still wins. The variable is a `ContextVar`, so two server
  sessions building concurrently never see each other's palette, and the token
  is reset in a `finally` — a view that raises cannot poison the next build.

## [0.11.0] - 2026-07-09

### Added

- **`CameraPreview` streams frames** — a new `on_frame` handler + `frame_interval_ms`
  throttle. When wired, the device attaches a CameraX `ImageAnalysis` stage and
  invokes the handler with a `CameraFrameEvent` (`width`/`height`/`data` base64 RGB
  /`rotation`) at most every `frame_interval_ms`, so an app can run on-device
  inference on the live feed (rebuild the array with `tempestroid.vision.frame_array`).
  `CameraFrameEvent` is a new exported event.

## [0.10.0] - 2026-07-09

### Added

- **`button_label` on `ImagePicker` / `DocumentPicker`.** The picker button's
  caption was hardcoded (`"Choose image"` / `"Choose document"`), so a
  non-English app could not localise it. A new `button_label` field (defaulting
  to the previous English text, so existing apps are unchanged) feeds the inner
  `FilePicker` label — e.g. `ImagePicker(button_label="Selecionar da galeria")`.

## [0.9.1] - 2026-07-08

### Fixed

- **Image/Document/Result pickers now run an `async` `on_pick`.** The internal
  `_on_uri` adapter that bridges a picker's typed `on_select` to the caller's
  `on_pick(uri)` **discarded the handler's return value**. When `on_pick`
  returned a coroutine (an `async def`, the common case for "load the picked
  file then do work"), the event dispatcher — which awaits a handler's returned
  coroutine (`iscoroutine(result) → await`) — received `None`, so the coroutine
  was never awaited: the picker fired, the callback ran, but the awaited work
  (e.g. loading + analyzing the picked image) silently never happened and no
  error surfaced. The adapter now **returns** `handler(event.uri)`, so a
  coroutine propagates and is awaited. Affects `ImagePicker`, `DocumentPicker`,
  and `ResultView`. (A synchronous `on_pick` is unaffected.)

## [0.9.0] - 2026-07-04

### Added

- **HTML/SSR escape-hatch fields on the `Widget` base — `tag` and `attrs`.** Every
  widget now carries two optional renderer-hint fields for the upcoming HTML/SSR
  leaf renderer (`tempestweb`): `tag: str | None` overrides the semantic HTML
  element emitted (e.g. `"nav"`, `"section"`, `"article"`, `"h1"`), and
  `attrs: dict[str, str]` supplies arbitrary HTML attributes (`hx-*`, `id`,
  `class`, `data-*`, `aria-*`). They follow the existing
  `semantics`/`focusable`/`focus_order` precedent: honored by the web renderer,
  ignored by the native renderers (Qt/Compose). Both flow through `build()` into
  the IR node `props` automatically (no reconciler special-casing), so `diff()`
  reacts to `tag`/`attrs` changes like any other prop. Fully additive and
  backward-compatible: `tag` defaults to `None` and `attrs` to an empty dict, so
  every existing widget and IR node is unchanged in behavior.

## [0.8.2] - 2026-06-25

### Fixed

- **A clickable `Rating` now renders bare stars instead of filled pills.** Each
  tappable star lowered to a `Button` with no explicit variant, inheriting the
  `SOLID` default — so a renderer that paints the variant fill (e.g. the web
  Material 3 base) drew the role color over the ★/☆ glyph, turning the stars into
  solid pills. The clickable star is now an icon-forward `GHOST` button with an
  explicitly transparent fill, so the glyph reads as a bare star on every
  renderer. Display-only `Rating` (no `on_rate`) was already a plain `Text` glyph
  and is unchanged.

## [0.8.1] - 2026-06-20

### Fixed

- **`ConfidenceBadge` now uses the `SUBTLE` badge variant** (tonal container pair)
  instead of `SOLID`, so a high/medium-confidence pill clears WCAG-AA — the
  `SOLID` white-on-saturated-status treatment failed AA (success ~3.02,
  warning ~4.0). Consistency with the H4 A1 status-color decision.

## [0.8.0] - 2026-06-20

### Added

- **H6 research / data-science kit** (Trilho H, phase H6) — the components an
  academic researcher needs to show an ONNX / `ort-vision-sdk` result end to end.
  Every new component lowers to **existing** primitives (composition) or to a
  `Canvas` draw-command list (charts / overlays) — **no new `Style` field**
  (`len(Style.model_fields)` stays 41), **no new variant resolver** and **no new
  `Canvas` draw command**. Fully additive and backward-compatible: every existing
  call site and explicit `style=` keeps working. New module
  `tempest_core/components/research.py`, re-exported from `tempest_core`.
  - **`ChartSeries` / `DetectionBox` (value models).** `ChartSeries`
    (`points` + `label` + optional `color_scheme`) is the chart data unit so a
    chart can plot several named, individually-colored series; `DetectionBox`
    (normalized `[0, 1]` `xyxy` + `name` + `conf`) is resolution-independent and
    multiplied by the canvas size at draw time. The engine takes **no**
    `ort-vision-sdk` dependency — a `Detection` → `DetectionBox` adapter lives on
    the tempestroid side.
  - **`confidence_scheme(conf, *, high=0.8, mid=0.5)`.** The traffic-light helper
    mapping a confidence score to `"success"` / `"warning"` / `"error"`.
  - **`MetricCard` / `StatCard`.** A dashboard metric — the H3 `Card` surface
    wrapping the H4 `Stat` block, with an optional trailing slot. `StatCard` is a
    compact (`filled`) preset of `MetricCard`.
  - **`ConfidenceBadge`.** The H4 `Badge` colored by `confidence_scheme` and
    labelled as a rounded percentage.
  - **`LineChart` / `BarChart`.** Charts drawn over the E7 `Canvas`: a line series
    is `MoveTo` + a run of `LineTo` + one `StrokeCmd` (there is no `DrawLine`); a
    bar is a `DrawRect` + a `FillCmd`; axes/gridlines are strokes and y-tick
    labels are right-aligned `DrawText` (the baseline-anchored command has no
    align field, so the anchor is shifted left by an estimated text width). The
    emitted command list is **deterministic** for fixed input (conformance-pinnable).
    `BarChart` also accepts a plain `values: list[float]` (+ `labels`).
  - **`DetectionOverlay`.** A `Stack` of a base `Image` (`fit=COVER`) and a
    `Canvas` that draws each detection box (`DrawRect` + `StrokeCmd`, colored by
    `confidence_scheme(box.conf)`) plus a filled-background `"{name} {conf:.0%}"`
    caption.
  - **`ResultView`.** The image-picker → result flow: an `ImagePicker` over an
    optional `result` widget slot (the app owns inference + builds the result).

### Changed

- **`DataTable` skin** (H6) — reads its header / zebra / divider colors from the
  theme tokens (no hard-coded hexes) and gains **app-driven** sort + pagination,
  mirroring the E1 list pattern (the component owns no state): new
  `sort_column` / `sort_ascending` / `on_sort`, `page` / `page_size` / `on_page`
  + `theme` props. With `page_size` set the table projects the current page slice
  and renders a prev/next pager; the active sort column shows a directional ▲/▼
  arrow; with `on_sort` wired the header cells become tappable buttons. The legacy
  `DataTable(columns=…, rows=…)` / `sortable=True` call sites still work.
- **`Calendar` / `Clock` skin** (H6) — migrated their hard-coded
  `components/base.py` hexes (`ACCENT` / `MUTED` / `ON_SURFACE` / `ON_MUTED` /
  `SURFACE`) to `theme.color(ColorRole.*)`, adding a `theme` (+ optional
  `color_scheme`) prop. Backward-compatible defaults — but the default look now
  follows the **M3 light** theme rather than the previous restrained dark palette
  (a visual shift for call sites that did not pass a `style`/`theme`).

## [0.7.0] - 2026-06-20

### Added

- **H5 styled navigation kit** (Trilho H, phase H5) — the navigation half of the
  design system. A pure **skin pass**: the navigation components migrate their
  hard-coded `components/base.py` hexes (`SURFACE` / `ACCENT` / `MUTED` /
  `ON_SURFACE` / …) to Material 3 theme tokens, reusing the **existing** variant
  resolvers — **no new resolver, no new enum and no new `Style` field**
  (`len(Style.model_fields)` stays 41; elevation rides the H3 elevation→`Shadow`
  mapping). Fully additive and backward-compatible: every existing call site and
  explicit `style=` keeps working.
  - **`Tabs` (new component).** A tab strip whose active tab carries an
    **underline indicator** — a thin bottom `SideBorder` in the accent role
    (existing `Border` / `SideBorder` fields). The strip is a
    `resolve_surface_variant` surface; each tab is a `resolve_variant` (GHOST)
    text; the active tab takes the `color_scheme` role color. Mirrors `NavBar`'s
    lowering and select-event shape. Re-exported from the package root and
    `tempest_core.components`. It is a `Component` (lowers to primitives), so it
    is **not** an IR leaf and stays out of `WIDGET_TYPES`.
  - **`AppBar` / `Footer` / `CollapsingAppBar`** (`components/bars.py`) — gain
    `variant` (CardVariant, default `ELEVATED`) / `color_scheme` (`"neutral"`) /
    `elevation` / `theme` / `media`; the bar surface (background + elevation
    shadow + tinted container) resolves via `resolve_surface_variant`, the title/
    content color is the resolved surface content. `CollapsingAppBar` keeps its
    height/font collapse derivation verbatim (only recolored) and its legacy
    `background` escape hatch still wins.
  - **`Header`** (`components/bars.py`) — tokens-only: the band fills with
    `SURFACE_VARIANT`, the title/subtitle read `ON_SURFACE` / `ON_SURFACE_VARIANT`,
    spacing/typography from the theme; an optional `color_scheme` tints the title.
  - **`Sidebar` / `Drawer`** (`components/layout.py`, `components/menu.py`) — the
    panel surface resolves via `resolve_surface_variant` (`color_scheme="neutral"`
    default); width / open behavior unchanged.
  - **`Scaffold`** (`components/layout.py`) — `background` ← `theme.color(BACKGROUND)`;
    gains a `theme` input. Tokens-only.
  - **`NavBar`** (`components/navigation.py`) — the bar is a
    `resolve_surface_variant` surface; the active item is an accent pill via
    `resolve_badge_variant` (SOLID, `color_scheme`); inactive items are a
    `resolve_variant` (GHOST, neutral) treatment. Gains `color_scheme`
    (`"primary"`) / `size` / `theme` / `media`; `on_select` / `active` wiring
    unchanged.
  - **`SearchBar`** (`components/fields.py`) — the inner `Input` style resolves
    via `resolve_field_variant`; the outer pill via `resolve_surface_variant`; the
    clear button lowers to an `IconButton` (the curated `Icons.X` glyph, GHOST).
    Gains `field_variant` / `color_scheme` / `size` / `theme` / `media`.
  - **`Breadcrumb`** (`components/navigation.py`) — migrates `ACCENT` / `ON_SURFACE`
    / `ON_MUTED` to theme roles; the link crumb resolves a `resolve_variant` (LINK)
    style. Gains `color_scheme` / `theme` / `media`.
  - **`Burger`** (`components/menu.py`) — re-lowers to an `IconButton`
    (`Icons.MENU`, GHOST, `color_scheme` / `theme`), reusing `resolve_variant` and
    the icon system. The `glyph` prop is kept as a **deprecated** backward-compat
    fallback.

## [0.6.0] - 2026-06-20

### Added

- **H4 styled data-display & feedback kit** (Trilho H, phase H4) — the
  data-display/feedback half of the design system. Fully additive and
  backward-compatible; **no new `Style` field** (`len(Style.model_fields)` stays
  41) — status flows through `color_scheme`, not a `Style` field.
  - **Status color families (H4a).** Three new Material 3 role *families* —
    `success` / `warning` / `info` — added to the token model:
    - 12 new `ColorRole` members (`SUCCESS`/`ON_SUCCESS`/`SUCCESS_CONTAINER`/
      `ON_SUCCESS_CONTAINER`, same for `WARNING` and `INFO`).
    - 16 new `ColorScheme` fields for those roles. They default to `None` and a
      `model_validator` back-fills any left unset from the matching `error` role,
      so every pre-H4 `ColorScheme(...)` constructor and pinned scheme JSON keeps
      validating.
    - Fixed semantic seeds beside `_DEFAULT_ERROR_SEED`: `_DEFAULT_SUCCESS_SEED`
      (`#16a34a` green), `_DEFAULT_WARNING_SEED` (`#d97706` amber),
      `_DEFAULT_INFO_SEED` (`#2563eb` blue), threaded through
      `color_schemes_from_seed` / `_scheme_from_palettes` (light + dark) and
      overridable via `success_seed` / `warning_seed` / `info_seed` on
      `color_schemes_from_seed` / `TokenSet.from_seed` / `Theme.from_seed`.
    - **A1 contrast fix.** A saturated status role on white can fail WCAG-AA
      (verified: success solid = 3.02, warning = 4.0). The subtle status surfaces
      therefore use the **container** treatment (`*_container` / `on_*_container`,
      ~13.7 contrast), not the raw role on white. Tests assert AA on the pairs the
      resolvers actually emit for every status scheme, in light and dark.
  - **Resolvers (H4b).** New pure sibling resolvers in `variants.py`, reusing the
    H1 helpers (`_scheme_roles`, `_CONTAINER_ON_ROLE`, `_apply_state`,
    `resolve_size`):
    - `BadgeVariant` enum (`SOLID`/`SUBTLE`/`OUTLINE`) +
      `resolve_badge_variant(*, variant, size, color_scheme, theme, state,
      platform_dark_mode, media) -> Style` + `resolve_badge_variant_states` +
      `BADGE_DENSITY`. Solid → role + on-role; subtle → container + on-container
      (AA-safe); outline → transparent + role border. Pill radius, compact
      padding, label-scale font.
    - `AlertVariant` enum (`SUBTLE`/`SOLID`/`LEFT_ACCENT`/`TOP_ACCENT`) +
      `resolve_alert_variant(*, variant, color_scheme="info", theme, padding_step,
      radius_step, platform_dark_mode, media) -> Style` (stateless, like a
      surface). Subtle (default) → container pair; solid → role pair; left/top
      accent → subtle fill + a 4px directional `SideBorder` in the saturated role
      (the renderers mirror the physical side under RTL).
    - ProgressBar/Spinner reuse the slider-track look; SegmentedControl reuses
      `resolve_variant` (active = solid, rest = ghost); Rating reads the role
      directly — no new resolvers added for those.
    - `VALID_COLOR_SCHEMES` widened to include `success` / `warning` / `info`.
  - **Components (H4c).**
    - New `Alert` (icon glyph + title + body + optional dismiss; the block
      sibling of `Banner`, via `resolve_alert_variant`), `Stat` (label + value +
      status-tinted up/down delta), `ProgressStepper` (wizard/progress stepper
      with active/done/pending step colors from tokens — named to avoid colliding
      with the numeric `Stepper`), and `Tag` (a closed, non-selectable `Chip`
      preset using the subtle badge).
    - Re-themed (dropped hard-coded hexes, resolve from theme): `Badge`
      (`resolve_badge_variant` + `variant`/`size`/`color_scheme`; legacy `tone`
      mapped onto `color_scheme`), `Banner` (`resolve_alert_variant` + legacy
      `tone`), `Avatar` (`color_scheme` → container pair), `EmptyState` (muted
      tokens + theme spacing), `SegmentedControl` (`resolve_variant`), `Rating`
      (`color_scheme` → star role), `Chip` (`resolve_badge_variant`).
    - `color_scheme` prop added to `ProgressBar` / `Spinner` / `Tooltip` /
      `Skeleton` (the renderers paint the accent; the engine carries the prop).
  - New public surface re-exported from `style.py`, `variants.py`,
    `components/__init__.py` and the package root `tempest_core/__init__.py`
    (+ `__all__`).

## [0.5.0] - 2026-06-20

### Added

- **H3 styled surface & layout kit** (Trilho H, phase H3) — the surface/layout
  half of the design system, anchored on a new pure resolver and a new variant
  enum, fully additive and backward-compatible:
  - `CardVariant` enum (`style.py`): `ELEVATED` (surface bg + elevation shadow,
    no border), `FILLED` (surface-variant bg, no shadow/border), `OUTLINED`
    (surface bg + outline border, no shadow).
  - `resolve_surface_variant(*, variant, color_scheme="neutral", theme,
    elevation=None, padding_step="md", radius_step="md", platform_dark_mode,
    media) -> Style` (`variants.py`) — the H3 sibling of `resolve_variant` for
    the **surface family** (card / surface / panel / accordion header). A surface
    is non-interactive, so there is **no** `state` param and **no** `*_states`
    sibling. `"neutral"` paints with the plain `SURFACE`/`ON_SURFACE` roles; a
    role family (`"primary"`, …) tints with the tonal `*_container` /
    `on_*_container` roles. Padding/radius come from the named token steps.
  - **Elevation → `Shadow`** — Material 3 elevation is realized as a `Shadow`
    mapped from the level (`_ELEVATION_SHADOW`, levels 0–5 → blur/offset, painted
    in `ELEVATION_SHADOW_COLOR`), **not** a new `Style` field. `elevation=`
    overrides the per-variant default level.
  - New components: `Surface` (un-padded themed box the cards build on) and
    `StyledContainer` (token-step padding over the IR `Container`, keeping the
    primitive pure) in `components/surface.py`; `HStack`/`VStack` (SwiftUI-style
    stacks over `Row`/`Column` with a token-step `gap`) in `components/layout.py`.
  - New leaf widget: `Spacer` (a flex spacer baking `grow` into its style;
    registered in `WIDGET_TYPES`/introspection).
- **Themed content components** — `Card` (now `variant`/`color_scheme`/
  `elevation` via `resolve_surface_variant`), `Divider` (M3 `OUTLINE_VARIANT`
  color, token-step thickness), `ListTile` (on-surface theme roles, token
  spacing, Semantics preserved), `Accordion` (themed header surface) and `Grid`
  (token-step `gap`). Every existing call site still works.

### Notes

- **No new `Style` field** — `len(Style.model_fields)` stays `41` (pinned by the
  H1/H2/H3 sentinel + the tempestroid conformance suite).

## [0.4.0] - 2026-06-20

### Added

- **H2 input/action-kit variant API** (Trilho H, phase H2) — three new pure,
  renderer-agnostic resolvers in `variants.py`, each mirroring H1's
  `resolve_variant` and shipping a `*_states` sibling for the per-state table the
  renderers consume:
  - `resolve_field_variant(*, variant, size, color_scheme, theme, state, invalid,
    …) -> Style` (+ `resolve_field_variant_states`) for the **field family** (text
    input, text area, select/dropdown, masked input, autocomplete, pin, date/time
    pickers). Focus-led: the resting treatment is low-emphasis and the
    `color_scheme` role tints only the focus border/caret/label. `invalid=True`
    forces the border/label to the `error` role in every state.
  - `resolve_selection_variant(*, size, color_scheme, theme, state, checked, …) ->
    Style` (+ `resolve_selection_variant_states`) for the **selection family**
    (checkbox, switch). No `variant` (M3 gives one affordance each): emits the
    accent as `color`, an accent fill when `checked`, the outline ring when not,
    and the control-box dimension from `SELECTION_SIZE`.
  - `resolve_slider_variant(*, size, color_scheme, theme, state, …) -> Style` (+
    `resolve_slider_variant_states`) for the **slider family** (slider, range
    slider). No `variant`: the accent active track + thumb, `surface_variant`
    inactive track, and the track thickness from `SLIDER_SIZE`.
- **New `FieldVariant` style enum** (`outline`/`filled`/`flushed`) in `style.py`,
  re-exported from `tempest_core`.
- **New `IconButton` widget** (beside `Button`) — an icon-only button reusing
  `resolve_variant` (defaults to `GHOST`), then pinning `width`/`height` to the
  resolved `min_height` and a circular `radius` (existing `Style` fields only),
  with an accessible `label`. Exposes `state_styles()`.
- **Styled input widgets** — `Input`/`TextArea`/`Dropdown`/`Autocomplete`/
  `MaskedInput`/`PinInput`/`DatePicker`/`TimePicker`/`FilePicker` now accept
  `field_variant`/`size`/`color_scheme`/`theme`/`media` and bake the resolved
  field `Style` (Input passes `invalid=bool(error)`; PinInput forces OUTLINE);
  `Checkbox`/`Switch` accept `size`/`color_scheme`/`theme`/`media` and resolve the
  selection style (passing `checked`); `Slider`/`RangeSlider` resolve the slider
  style. Each exposes `state_styles()`. Backward-compatible: existing calls keep
  working with sensible defaults and an explicit `style=` is merged on top;
  `theme`/`media` stay out of the IR props.
- **Theme-driven Brazilian inputs** — `EmailInput`/`PasswordInput`/`PhoneInput`/
  `CPFInput`/`CNPJInput`/`AddressInput` now accept `color_scheme`/`size`/
  `field_variant`/`theme`/`media` and thread them into the inner field, replacing
  the hard-coded dark hexes with theme-driven resolution (dark mode works); the
  labelled wrapper's label/error colors read from the theme. `EmailInput` keeps
  `mail`, `PasswordInput` stays secure + `lock`.
- **Theme-driven `RadioGroup`** — each row's marker/text color resolves from
  `resolve_selection_variant` against the theme (chosen row = accent, others =
  muted on-surface), keeping the ◉/○ glyphs.
- **Engine-level Material icon aliases** — `MATERIAL_ALIASES` in `icons.py` (common
  Material Symbols name → curated `Icons` glyph, e.g. `photo_camera`→eye,
  `history`→`clock`, `person`→`user`); `icon_path` now consults it so alias
  resolution is renderer-agnostic (both renderers delegate in the H2 PR-2 work).
- Re-exported the new public surface from `tempest_core` (`FieldVariant`,
  `IconButton`, `SELECTION_SIZE`, `SLIDER_SIZE`, `resolve_field_variant`,
  `resolve_field_variant_states`, `resolve_selection_variant`,
  `resolve_selection_variant_states`, `resolve_slider_variant`,
  `resolve_slider_variant_states`); `IconButton` added to the introspection
  `WIDGET_TYPES` catalog.

### Notes

- **No new `Style` field** — every H2 treatment maps onto existing fields
  (`background`/`color`/`border`/`padding`/`radius`/`width`/`height`/`min_height`/
  `font_size`/`font_weight`); track/selection colors land on `color`/`background`.

## [0.3.0] - 2026-06-19

### Added

- **Chakra-style variant API** (Trilho H, phase H1) — a new `variants.py` module
  with `resolve_variant(*, variant, size, color_scheme, theme, state, …) -> Style`,
  the pure, renderer-agnostic resolution that maps the Chakra-ergonomics props
  onto a concrete Material 3 `Style` against the H0 tokens. `resolve_variant_states`
  returns the full per-state style table (default/hover/pressed/disabled/focus) —
  the seam the Qt/Compose renderers consume to apply M3 state layers on real
  pointer/focus events. `resolve_size` resolves a responsive `size` map
  (`{"base": Size.SM, "md": Size.LG}`) against the theme breakpoints + an optional
  `MediaQueryData`. `merge_styles` is a re-validating `Style` merge that keeps
  nested value objects typed.
- **New style enums** in `style.py` — `Variant` (solid/outline/ghost/link),
  `Size` (xs/sm/md/lg) and `ComponentState` (default/hover/pressed/disabled/focus).
- **`Color.blend`/`Color.overlay`/`Color.with_alpha`** — alpha-composite helpers so
  M3 state layers (hover @ 8%, pressed @ 12%, focus, disabled @ 38% content) can be
  computed purely.
- **Styled `Button`** — now accepts `variant` (default `SOLID`), `size` (default
  `MD`, single or responsive map), `color_scheme` (default `"primary"`), plus a
  `theme`/`media`; it resolves its base `Style` via `resolve_variant` (an explicit
  `style` is merged on top) and exposes `state_styles()`. Backward-compatible:
  `Button(label=...)` and a plain `style=` keep working; `Semantics`/`focusable`/
  `focus_order` are preserved. Touch target is held ≥ 48dp for every size; WCAG-AA
  contrast on solid/outline content-vs-fill is preserved by the tokens.
- Re-exported the new public surface from `tempest_core` (`Variant`, `Size`,
  `ComponentState`, `ResponsiveSize`, `resolve_variant`, `resolve_variant_states`,
  `resolve_size`).

## [0.2.0] - 2026-06-19

### Added

- **Material 3 design-token foundation** (Trilho H, phase H0) — a new
  `tokens.py` module with the typed, frozen token model: `TonalPalette` +
  `tonal_palette_from_seed` (deterministic, dependency-free M3 tonal-palette
  generation from a brand seed), `ColorScheme`/`ColorSchemes` +
  `color_schemes_from_seed` (the full M3 color roles for light **and** dark,
  WCAG-AA contrast on every `on_*` role), the systematic scales (`SpacingScale`
  4dp grid, `ShapeScale` radius, `TypographyScale` display/headline/title/body/
  label, `ElevationScale` levels 0-5, `MotionScale` durations + easing),
  `Breakpoints`, and the `TokenSet` bundle (`TokenSet.from_seed` /
  `default_tokens`).
- **`Theme` resolves tokens** — `Theme` now carries a `TokenSet` (default M3
  seeded from the reference purple) and exposes `Theme.from_seed`,
  `scheme`/`color`/`space`/`radius`/`typography`/`elevation`, and `resolve_ref`
  /`resolve_style`. `TokenRef` is the **Style ⟷ token seam**: a style field can
  carry a token reference (`TokenRef.color("primary")`, `TokenRef.radius("lg")`,
  …) that `Theme.resolve_style` resolves into a concrete, frozen `Style` before
  the diff. Additive and backward-compatible — raw `Style`/`Theme` values keep
  working unchanged; the legacy flat color fields remain.
- Re-exported the new public surface from `tempest_core` (`TokenSet`,
  `TokenRef`, `TonalPalette`, `ColorScheme`/`ColorSchemes`, `ColorRole`, the
  scale classes, `default_tokens`, `tonal_palette_from_seed`,
  `color_schemes_from_seed`).

## [0.1.0] — 2026-06-11

First public release. The renderer-agnostic UI core shared across the tempest
stack — extracted so consumers depend on a published package instead of vendoring
a copy.

### Added

- **IR + reconciler**: `build` / `diff` (and `build_scene` / `diff_scene` for the
  overlay layer), the `Node` / `Patch` model, and `App` state with a coalesced
  rebuild loop.
- **Typed style model**: `Style`, `Color`, `Edge`, gradients, shadows, borders,
  and transitions — no CSS cascade, inline-typed.
- **Widgets & components**: layout (Column/Row/Container/Stack), text, button,
  inputs, checkbox, lists (LazyColumn/Row/Grid), overlays, gestures, media, plus
  the composed component set (cards, forms, fields, tables, BR inputs, …).
- **Cross-cutting helpers**: animation, i18n (`translate`), navigation
  (`Route`/`NavStack`/`routes_from_path`), theme, validators (CPF/CNPJ/email/
  phone), icons, devices.
- No platform-coupled code (no Qt, JNI, Android, or DOM) — imports cleanly under
  CPython, Pyodide and a headless server. Only hard dependency: `pydantic>=2`.

### Notes

- Gate mirrors tempestroid: ruff (E/F/I/UP/B/Q/ANN/D + google docstrings),
  pyright strict, pytest — all green.
- Consumed by [`tempestweb`](https://pypi.org/project/tempestweb/); tempestroid's
  own migration onto this package is in progress.
