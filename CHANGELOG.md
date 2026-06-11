# Changelog

All notable changes to **tempest-core** are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to semantic
versioning.

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
