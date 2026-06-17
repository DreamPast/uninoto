# AGENTS.md

## Font Viewer

GUI application for browsing merged uninoto font glyphs. Built with egui/eframe.

## Font Loading

- Merged fonts are loaded from the selected `fonts/merged/<style>` folder at runtime.
- Directional `extra` fallback outputs are optional UI toggles.
- Font data is stored in `ViewerApp.font_data` as `Vec<(String, Vec<u8>)>`.
- egui built-in fonts are removed — only uninoto fonts are registered.
- Font families are registered fresh when the family selector changes (deferred via `needs_reload` flag to respect `set_fonts`'s deferred activation).

## Font Family Chains

| Family | Font Files |
|--------|-----------|
| Sans   | `uninoto_sans*` plus optional `uninoto_sans_extra*` |
| Serif  | `uninoto_serif*` plus optional `uninoto_serif_extra*` |
| Mono   | `uninoto_mono*` |

## CMap Parsing

- Uses `ttf-parser` 0.25 to read cmap subtables.
- Filters to Unicode-platform subtables and Windows Unicode BMP/platform-10 subtables (covers formats 4, 12, 13, 14).
- First font wins for duplicate codepoints (dedup via `BTreeMap`).
- Codepoint → Unicode name resolved via `unicode_names2` 3.1.0.
- Plane and Unicode general category are computed per-codepoint via `plane_name()` and `category_abbr()`.

## UI Modes

- **List mode**: virtual-scrolled table with columns: Glyph, Codepoint, Name, Plane, Category.
  - Horizontal separators between rows, zero `item_spacing` to avoid `show_rows` gap accumulation.
  - Control-character glyph cells are painted from font outlines so `\t` and similar codepoints do not render as text-layout whitespace.
- **Grid mode**: virtual-scrolled table rows from `0000` to `10FFF0`, with a codepoint row header and 16 fixed-height character cells.
  - Rows made entirely of unassigned or surrogate codepoints are hidden; control codepoint rows remain visible.
  - Hovering a character shows a tooltip with codepoint, plane, category, and Unicode name.
  - Search results keep matched row context: rows without a match are hidden, covered glyphs outside the match are gray, and missing glyph cells are blank.
  - Control-character glyph cells use the same font-outline painting as List mode.
  - Covered glyph cells can be selected; double-click or `Ctrl+C`/`Cmd+C` copies the character, and the context menu can copy the character or codepoint.
- **Text mode**: free-form multiline `TextEdit` for user input, independent of font glyphs.

## Controls

- **Zoom**: `spin_box` widget (▼/▲ buttons + text input), step 0.25, range 0.5–3.0. Reads system DPI as initial value. NaN → reset to system default.
- **Size**: `DragValue`, step 0.25, range 6–48. Controls glyph/table font size.
- **Family**: Sans/Serif/Mono selector.
- **Show**: Extra toggle.
- **View**: List/Grid/Text mode selector.
- **Jump to**: hex codepoint navigation (U+XXXX).
- **Search**: filter by hex codepoint, character, or Unicode name.

## Code Structure

- `src/main.rs`: thin eframe entry point and module declarations.
- `src/app.rs`: `ViewerApp` state, reload/search logic, and List/Grid/Text view composition.
- `src/font_data.rs`: font style/family modes, folder resolution, font loading, and egui font registration.
- `src/glyph_data.rs`: cmap scanning, `GlyphInfo`, Unicode metadata, and Grid row selection.
- `src/glyph_paint.rs`: glyph cell painting, including outline painting for control-character glyphs.
- `src/controls.rs`: small UI helpers such as `spin_box` and hex parsing.
- `src/util.rs`: compatibility re-exports for shared app imports.

## Dependencies

- `egui` 0.34 + `eframe` 0.34 (glow backend)
- `ttf-parser` 0.25
- `unicode_names2` 3.1.0

## Build

```
cargo build
cargo fmt
```

Fonts are embedded — no external file dependencies at runtime.

## Known Limitations

- `font_index` field on `GlyphInfo` is populated but never displayed in the UI (preserved for future use).
- Unicode category detection uses `char` built-in methods (approximate, not exact General Category).
- `ui.ctx().request_repaint()` is called every frame, keeping the UI at max refresh rate.
- Zoom's `set_zoom_factor` multiplies with system DPI — changing zoom on a HiDPI display may produce unexpected total scaling.
