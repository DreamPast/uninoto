#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::collections::BTreeMap;

use eframe::App;
use egui::{DragValue, RichText, ScrollArea, TextEdit};

use crate::util::{FontFamilyMode, GlyphInfo, build_grid_rows, load_glyph_map, setup_fonts};
pub(crate) mod util;

#[derive(Clone, Copy, PartialEq)]
enum DisplayMode {
    List,
    Grid,
    Text,
}

impl DisplayMode {
    fn label(self) -> &'static str {
        match self {
            Self::List => "List",
            Self::Grid => "Grid",
            Self::Text => "Text",
        }
    }
}

struct ViewerApp {
    font_family: FontFamilyMode,
    display_mode: DisplayMode,
    search: String,
    prev_search: String,
    jump: String,
    glyph_map: BTreeMap<u32, GlyphInfo>,
    filtered: Vec<u32>,
    grid_rows: Vec<String>,
    font_data: Vec<(String, &'static [u8])>,
    font_scale: f32,
    ui_scale: f32,
    default_zoom: f32,
    spin_text: String,
    text_input: String,
    needs_reload: bool,
}

impl ViewerApp {
    fn new(cc: &eframe::CreationContext) -> Self {
        let font_family = FontFamilyMode::Sans;
        let font_data = font_family.font_data();
        if !font_data.is_empty() {
            setup_fonts(&cc.egui_ctx, &font_data);
        }
        let glyph_map = load_glyph_map(&font_data);
        let filtered: Vec<u32> = glyph_map.keys().copied().collect();
        let grid_rows = build_grid_rows(&filtered);
        Self {
            font_family,
            display_mode: DisplayMode::List,
            search: String::new(),
            prev_search: String::new(),
            jump: String::new(),
            glyph_map,
            filtered,
            grid_rows,
            font_data,
            font_scale: 16.0,
            ui_scale: cc.egui_ctx.pixels_per_point(),
            default_zoom: cc.egui_ctx.pixels_per_point(),
            spin_text: format!("{:.2}", cc.egui_ctx.pixels_per_point()),
            text_input: String::new(),
            needs_reload: false,
        }
    }

    fn begin_reload(&mut self, ctx: &egui::Context) {
        self.font_data = self.font_family.font_data();
        if !self.font_data.is_empty() {
            setup_fonts(ctx, &self.font_data);
        }
        self.needs_reload = true;
        ctx.request_repaint();
    }

    fn finish_reload(&mut self) {
        self.glyph_map = load_glyph_map(&self.font_data);
        self.filtered = self.glyph_map.keys().copied().collect();
        self.grid_rows = build_grid_rows(&self.filtered);
        self.prev_search.clear();
        self.needs_reload = false;
    }

    fn try_apply_filter(&mut self) {
        if self.search == self.prev_search {
            return;
        }
        let query = self.search.to_uppercase();
        self.filtered = if query.is_empty() {
            self.glyph_map.keys().copied().collect()
        } else {
            self.glyph_map
                .iter()
                .filter(|(cp, info)| self.matches_search(cp, info, &query))
                .map(|(cp, _)| *cp)
                .collect()
        };
        self.prev_search = self.search.clone();
        self.grid_rows = build_grid_rows(&self.filtered);
    }

    fn matches_search(&self, cp: &u32, info: &GlyphInfo, query: &str) -> bool {
        if format!("{:04X}", cp).contains(query) || format!("{:X}", cp).contains(query) {
            return true;
        }
        if let Some(ch) = char::from_u32(*cp) {
            if self.search.starts_with(ch) {
                return true;
            }
        }
        if let Some(n) = &info.name {
            if n.to_uppercase().contains(query) {
                return true;
            }
        }
        false
    }
}

fn spin_box(
    ui: &mut egui::Ui,
    value: &mut f32,
    text: &mut String,
    min: f32,
    max: f32,
    step: f32,
    default: f32,
) -> bool {
    let mut changed = false;
    ui.spacing_mut().item_spacing.x = 0.0;
    if ui.button("\u{25BC}").clicked() {
        *value = (*value - step).clamp(min, max);
        *text = format!("{:.2}", *value);
        changed = true;
    }
    let resp = ui.add(TextEdit::singleline(text).desired_width(50.0));
    if resp.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
        if let Ok(v) = text.parse::<f32>() {
            let v = if v.is_nan() { default } else { v.clamp(min, max) };
            *value = v;
            *text = format!("{:.2}", v);
            changed = true;
        } else {
            *text = format!("{:.2}", *value);
        }
    }
    if ui.button("\u{25B2}").clicked() {
        *value = (*value + step).clamp(min, max);
        *text = format!("{:.2}", *value);
        changed = true;
    }
    changed
}

fn parse_hex(s: &str) -> Option<u32> {
    let s = s.trim();
    let s = s
        .strip_prefix("U+")
        .or_else(|| s.strip_prefix("u+"))
        .unwrap_or(s);
    u32::from_str_radix(s, 16).ok()
}

impl ViewerApp {
    fn show_top_panel(&mut self, ui: &mut egui::Ui) {
        egui::Panel::top("top_panel").show_inside(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label("Zoom:");
                if spin_box(
                    ui,
                    &mut self.ui_scale,
                    &mut self.spin_text,
                    0.5,
                    3.0,
                    0.25,
                    self.default_zoom,
                ) {
                    ui.ctx().set_zoom_factor(self.ui_scale);
                }
                ui.label("Size:");
                ui.add(DragValue::new(&mut self.font_scale).range(6.0..=48.0).speed(0.25));
                ui.separator();
                ui.label("Family:");
                for mode in &FontFamilyMode::ALL {
                    ui.selectable_value(&mut self.font_family, *mode, mode.label());
                }
                ui.separator();
                ui.label("View:");
                ui.selectable_value(
                    &mut self.display_mode,
                    DisplayMode::List,
                    DisplayMode::List.label(),
                );
                ui.selectable_value(
                    &mut self.display_mode,
                    DisplayMode::Grid,
                    DisplayMode::Grid.label(),
                );
                ui.selectable_value(
                    &mut self.display_mode,
                    DisplayMode::Text,
                    DisplayMode::Text.label(),
                );
            });
            ui.horizontal(|ui: &mut egui::Ui| {
                self.show_jump_bar(ui);
                ui.separator();
                self.show_search_bar(ui);
                ui.separator();
                ui.label(
                    RichText::new(format!(
                        "Glyphs: {}/{}",
                        self.filtered.len(),
                        self.glyph_map.len()
                    ))
                    .strong(),
                );
            });
        });
    }

    fn show_jump_bar(&mut self, ui: &mut egui::Ui) {
        ui.label("Jump to:");
        let jump_resp = ui.add(
            TextEdit::singleline(&mut self.jump)
                .desired_width(80.0)
                .hint_text("U+4E00"),
        );
        let go_clicked = ui.button("Go").clicked();
        let enter_pressed = jump_resp.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
        if go_clicked || enter_pressed {
            if let Some(cp) = parse_hex(&self.jump) {
                if self.glyph_map.contains_key(&cp) {
                    let ch = char::from_u32(cp).unwrap();
                    self.search = ch.to_string();
                    self.jump.clear();
                    ui.ctx().request_repaint();
                }
            }
        }
    }

    fn show_search_bar(&mut self, ui: &mut egui::Ui) {
        ui.label("Search:");
        ui.add(
            TextEdit::singleline(&mut self.search)
                .desired_width(200.0)
                .hint_text("name or U+XXXX"),
        );
        if ui.button("X").clicked() {
            self.search.clear();
        }
    }

    fn show_list_view(&self, ui: &mut egui::Ui) {
        let row_height = self.font_scale + 5.0;
        let num_rows = self.filtered.len();

        let glyph_w = self.font_scale * 3.5;
        let cp_w = self.font_scale * 5.5;
        let plane_w = self.font_scale * 3.0;
        let cat_w = self.font_scale * 4.5;
        let spacer = ui.spacing().item_spacing.x;
        let fixed = glyph_w + cp_w + plane_w + cat_w + spacer * 4.0;
        let max_name_chars = self
            .glyph_map
            .values()
            .filter_map(|i| i.name.as_deref())
            .map(|n| n.len())
            .max()
            .unwrap_or(0)
            .max(8);
        let name_min = (max_name_chars as f32 * self.font_scale * 0.6).max(100.0);
        let name_width = (ui.available_width() - fixed).max(name_min);
        let cols = (glyph_w, cp_w, name_width, plane_w, cat_w);

        ScrollArea::both()
            .auto_shrink([false; 2])
            .scroll_bar_visibility(egui::scroll_area::ScrollBarVisibility::AlwaysVisible)
            .show_rows(ui, row_height, num_rows, |ui, row_range| {
                if row_range.start == 0 {
                    Self::render_list_header(ui, row_height, self.font_scale, cols);
                }
                for row in row_range {
                    let cp = self.filtered[row];
                    let info = &self.glyph_map[&cp];
                    Self::render_list_row(ui, cp, info, row_height, self.font_scale, cols);
                }
            });
    }

    fn render_list_header(
        ui: &mut egui::Ui,
        row_height: f32,
        font_scale: f32,
        cols: (f32, f32, f32, f32, f32),
    ) {
        ui.horizontal(|ui: &mut egui::Ui| {
            ui.add_sized(
                [cols.0, row_height],
                egui::Label::new(RichText::new("Glyph").strong().size(font_scale)),
            );
            ui.add_sized(
                [cols.1, row_height],
                egui::Label::new(RichText::new("Codepoint").strong().size(font_scale)),
            );
            ui.add_sized(
                [cols.2, row_height],
                egui::Label::new(RichText::new("Name").strong().size(font_scale)),
            );
            ui.add_sized(
                [cols.3, row_height],
                egui::Label::new(RichText::new("Plane").strong().size(font_scale)),
            );
            ui.add_sized(
                [cols.4, row_height],
                egui::Label::new(RichText::new("Category").strong().size(font_scale)),
            );
        });
        ui.separator();
    }

    fn render_list_row(
        ui: &mut egui::Ui,
        cp: u32,
        info: &GlyphInfo,
        row_height: f32,
        font_scale: f32,
        cols: (f32, f32, f32, f32, f32),
    ) {
        let ch = char::from_u32(cp).unwrap_or('\u{FFFD}');

        ui.horizontal(|ui: &mut egui::Ui| {
            ui.add_sized(
                [cols.0, row_height],
                egui::Label::new(
                    RichText::new(ch.to_string())
                        .size(font_scale)
                        .family(info.font_family.clone()),
                ),
            );
            ui.add_sized(
                [cols.1, row_height],
                egui::Label::new(
                    RichText::new(format!("U+{:04X}", cp))
                        .monospace()
                        .size(font_scale),
                ),
            );
            if let Some(n) = &info.name {
                ui.add_sized(
                    [cols.2, row_height],
                    egui::Label::new(RichText::new(n.as_str()).size(font_scale)),
                );
            } else {
                ui.add_sized(
                    [cols.2, row_height],
                    egui::Label::new(
                        RichText::new("<unnamed>")
                            .size(font_scale)
                            .color(egui::Color32::GRAY),
                    ),
                );
            }
            ui.add_sized(
                [cols.3, row_height],
                egui::Label::new(RichText::new(info.plane).size(font_scale)),
            );
            ui.add_sized(
                [cols.4, row_height],
                egui::Label::new(RichText::new(info.category).monospace().size(font_scale)),
            );
        });
        ui.separator();
    }

    fn show_grid_view(&self, ui: &mut egui::Ui) {
        let slot_width = self.font_scale + 7.0;
        let row_height = self.font_scale + 7.0;
        let num_rows = self.grid_rows.len();

        ScrollArea::both()
            .auto_shrink([false; 2])
            .scroll_bar_visibility(egui::scroll_area::ScrollBarVisibility::AlwaysVisible)
            .show_rows(ui, row_height, num_rows, |ui, row_range| {
                for row in row_range {
                    let start = row * 32;
                    let end = (start + 32).min(self.filtered.len());
                    let cps = &self.filtered[start..end];
                    Self::render_grid_row(
                        ui,
                        &self.grid_rows[row],
                        cps,
                        &self.glyph_map,
                        slot_width,
                        row_height,
                        self.font_scale,
                    );
                }
            });
    }

    fn render_grid_row(
        ui: &mut egui::Ui,
        text: &str,
        cps: &[u32],
        glyph_map: &BTreeMap<u32, GlyphInfo>,
        slot_width: f32,
        row_height: f32,
        font_size: f32,
    ) {
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing = egui::Vec2::ZERO;
            for (i, ch) in text.chars().enumerate() {
                let resp = ui.add_sized(
                    [slot_width, row_height],
                    egui::Label::new(
                        RichText::new(ch.to_string())
                            .size(font_size)
                            .family(egui::FontFamily::Monospace),
                    ),
                );
                if let Some(cp) = cps.get(i) {
                    if let Some(info) = glyph_map.get(cp) {
                        resp.on_hover_ui(|ui| {
                            ui.label(format!("U+{:04X} ({})", cp, info.plane));
                            ui.label(format!("Category: {}", info.category));
                            if let Some(n) = &info.name {
                                ui.label(n.as_str());
                            }
                        });
                    }
                }
            }
        });
    }
}

impl App for ViewerApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        if self.needs_reload {
            self.finish_reload();
        }

        let old_family = self.font_family;

        self.show_top_panel(ui);

        if self.font_family != old_family {
            self.begin_reload(ui.ctx());
        }

        self.try_apply_filter();

        egui::CentralPanel::default().show_inside(ui, |ui: &mut egui::Ui| {
            match self.display_mode {
                DisplayMode::Text => {
                    ui.add(
                        TextEdit::multiline(&mut self.text_input)
                            .desired_width(ui.available_width())
                            .font(egui::FontId::new(
                                self.font_scale,
                                egui::FontFamily::Proportional,
                            )),
                    );
                }
                _ if self.filtered.is_empty() => {
                    ui.label("No glyphs match the search.");
                }
                DisplayMode::List => self.show_list_view(ui),
                DisplayMode::Grid => self.show_grid_view(ui),
            }
        });

        ui.ctx().request_repaint();
    }
}

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        renderer: eframe::Renderer::Glow,
        viewport: egui::ViewportBuilder::default().with_inner_size([1000.0, 750.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Font Viewer",
        options,
        Box::new(|cc| Ok(Box::new(ViewerApp::new(cc)))),
    )
}
