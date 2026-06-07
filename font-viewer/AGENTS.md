# AGENTS.md

## Font Viewer

GUI application for browsing merged uninoto font glyphs. Built with egui/eframe.

## Font Loading

- Fonts are embedded at compile time via `include_bytes!()`.
- All 10 merged fonts (Sans x4, Serif x4, Mono x3 with `uninoto_last` shared) are baked into the binary (~172 MB).
- Font data is stored in `ViewerApp.font_data` as `Vec<(String, &'static [u8])>`.
- egui built-in fonts are removed — only uninoto fonts are registered.
- Font families are registered fresh when the family selector changes (deferred via `needs_reload` flag to respect `set_fonts`'s deferred activation).

## Font Family Chains

| Family | Font Files |
|--------|-----------|
| Sans   | `uninoto_sans.ttf` → `uninoto_sans_upper1.ttf` → `uninoto_sans_upper2.ttf` → `uninoto_last.ttf` |
| Serif  | `uninoto_serif.ttf` → `uninoto_serif_upper1.ttf` → `uninoto_serif_upper2.ttf` → `uninoto_last.ttf` |
| Mono   | `uninoto_mono.ttf` → `uninoto_mono_upper1.ttf` → `uninoto_mono_upper2.ttf` (no last) |

## CMap Parsing

- Uses `ttf-parser` 0.25 to read cmap subtables.
- Filters to Unicode-platform subtables and Windows Unicode BMP/platform-10 subtables (covers formats 4, 12, 13, 14).
- First font wins for duplicate codepoints (dedup via `BTreeMap`).
- Codepoint → Unicode name resolved via `unicode_names2` 3.1.0.
- Plane and Unicode general category are computed per-codepoint via `plane_name()` and `category_abbr()`.

## UI Modes

- **List mode**: virtual-scrolled table with columns: Glyph, Codepoint, Name, Plane, Category.
  - Horizontal separators between rows, zero `item_spacing` to avoid `show_rows` gap accumulation.
- **Grid mode**: virtual-scrolled fixed-width character slots (32 per row) using `FontFamily::Monospace`.
  - Hovering a character shows a tooltip with codepoint, plane, category, and Unicode name.
- **Text mode**: free-form multiline `TextEdit` for user input, independent of font glyphs.

## Controls

- **Zoom**: `spin_box` widget (▼/▲ buttons + text input), step 0.25, range 0.5–3.0. Reads system DPI as initial value. NaN → reset to system default.
- **Size**: `DragValue`, step 0.25, range 6–48. Controls glyph/table font size.
- **Family**: Sans/Serif/Mono selector.
- **View**: List/Grid/Text mode selector.
- **Jump to**: hex codepoint navigation (U+XXXX).
- **Search**: filter by hex codepoint, character, or Unicode name.

## Code Structure

- `src/util.rs`: `FontFamilyMode`, font data arrays, `setup_fonts`, `load_glyph_map`, `build_grid_rows`, `plane_name`, `category_abbr`.
- `src/main.rs`: `ViewerApp` struct, `App` impl, all UI rendering split into focused methods (`show_top_panel`, `show_jump_bar`, `show_search_bar`, `show_list_view`, `show_grid_view`, `render_list_row`, `render_grid_row`, `try_apply_filter`, `matches_search`, `spin_box`).

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
