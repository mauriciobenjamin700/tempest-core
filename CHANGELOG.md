# Changelog

All notable changes to **tempest-core** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to semantic
versioning.

## [Unreleased]

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
