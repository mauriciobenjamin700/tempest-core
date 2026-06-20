# Changelog

All notable changes to **tempest-core** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to semantic
versioning.

## [Unreleased]

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
