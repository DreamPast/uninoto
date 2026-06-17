use std::collections::BTreeMap;

use eframe::App;
use egui::{DragValue, RichText, ScrollArea, TextEdit};

use crate::controls::{parse_hex, spin_box};
use crate::glyph_paint::{render_glyph_cell, render_glyph_cell_with_color};
use crate::util::{
    FontFamilyMode, FontStyleMode, GlyphInfo, LoadedFont, build_grid_rows, load_font_data,
    load_glyph_map, resolve_font_root, setup_fonts,
};

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

fn copy_grid_char(ui: &egui::Ui, cp: u32) {
    if let Some(ch) = char::from_u32(cp) {
        ui.ctx().copy_text(ch.to_string());
    }
}

pub(crate) struct ViewerApp {
    font_root_text: String,
    font_style: FontStyleMode,
    font_family: FontFamilyMode,
    show_extra: bool,
    display_mode: DisplayMode,
    search: String,
    prev_search: String,
    jump: String,
    glyph_map: BTreeMap<u32, GlyphInfo>,
    filtered: Vec<u32>,
    grid_rows: Vec<u32>,
    font_data: Vec<LoadedFont>,
    load_error: Option<String>,
    font_scale: f32,
    ui_scale: f32,
    default_zoom: f32,
    spin_text: String,
    text_input: String,
    selected_grid_cp: Option<u32>,
    needs_reload: bool,
}

impl ViewerApp {
    pub(crate) fn new(cc: &eframe::CreationContext) -> Self {
        let font_root_text = "../fonts/merged".to_string();
        let font_style = FontStyleMode::Full;
        let font_family = FontFamilyMode::Sans;
        let show_extra = true;
        let font_root = resolve_font_root(&font_root_text);
        let mut load_error = None;
        let font_data = match load_font_data(&font_root, font_style, font_family, show_extra) {
            Ok(font_data) => font_data,
            Err(err) => {
                load_error = Some(err);
                Vec::new()
            }
        };
        if !font_data.is_empty() {
            setup_fonts(&cc.egui_ctx, &font_data);
        }
        let glyph_map = load_glyph_map(&font_data);
        let filtered: Vec<u32> = glyph_map.keys().copied().collect();
        let grid_rows = build_grid_rows(&filtered, false);
        Self {
            font_root_text,
            font_style,
            font_family,
            show_extra,
            display_mode: DisplayMode::List,
            search: String::new(),
            prev_search: String::new(),
            jump: String::new(),
            glyph_map,
            filtered,
            grid_rows,
            font_data,
            load_error,
            font_scale: 16.0,
            ui_scale: cc.egui_ctx.pixels_per_point(),
            default_zoom: cc.egui_ctx.pixels_per_point(),
            spin_text: format!("{:.2}", cc.egui_ctx.pixels_per_point()),
            text_input: String::new(),
            selected_grid_cp: None,
            needs_reload: false,
        }
    }

    fn begin_reload(&mut self, ctx: &egui::Context) {
        let font_root = resolve_font_root(&self.font_root_text);
        match load_font_data(
            &font_root,
            self.font_style,
            self.font_family,
            self.show_extra,
        ) {
            Ok(font_data) => {
                self.font_data = font_data;
                self.load_error = None;
                if !self.font_data.is_empty() {
                    setup_fonts(ctx, &self.font_data);
                }
                self.needs_reload = true;
                ctx.request_repaint();
            }
            Err(err) => {
                self.load_error = Some(err);
            }
        }
    }

    fn finish_reload(&mut self) {
        self.glyph_map = load_glyph_map(&self.font_data);
        self.filtered = self.glyph_map.keys().copied().collect();
        self.grid_rows = build_grid_rows(&self.filtered, false);
        self.prev_search.clear();
        self.selected_grid_cp = None;
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
        self.grid_rows = build_grid_rows(&self.filtered, !self.search.is_empty());
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

    fn handle_grid_copy_shortcut(&self, ui: &mut egui::Ui) {
        if self.display_mode != DisplayMode::Grid {
            return;
        }
        let copy_pressed = ui.input(|i| i.modifiers.command && i.key_pressed(egui::Key::C));
        if copy_pressed {
            if let Some(cp) = self.selected_grid_cp {
                copy_grid_char(ui, cp);
            }
        }
    }
}

impl ViewerApp {
    fn show_top_panel(&mut self, ui: &mut egui::Ui) {
        egui::Panel::top("top_panel").show_inside(ui, |ui| {
            ui.horizontal(|ui| {
                ui.label("Font folder:");
                let folder_resp = ui.add(
                    TextEdit::singleline(&mut self.font_root_text)
                        .desired_width((ui.available_width() - 190.0).max(180.0))
                        .hint_text("../fonts/merged"),
                );
                let enter_pressed =
                    folder_resp.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter));
                let reload_clicked = ui.button("Reload").clicked();
                let browse_clicked = ui.button("Choose...").clicked();
                if browse_clicked {
                    let start_dir = resolve_font_root(&self.font_root_text);
                    let mut dialog = rfd::FileDialog::new();
                    if start_dir.is_dir() {
                        dialog = dialog.set_directory(start_dir);
                    }
                    if let Some(path) = dialog.pick_folder() {
                        self.font_root_text = path.display().to_string();
                        self.begin_reload(ui.ctx());
                    }
                } else if enter_pressed || reload_clicked {
                    self.begin_reload(ui.ctx());
                }
            });
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
                ui.add(
                    DragValue::new(&mut self.font_scale)
                        .range(6.0..=48.0)
                        .speed(0.25),
                );
                ui.separator();
                ui.label("Style:");
                for mode in &FontStyleMode::ALL {
                    ui.selectable_value(&mut self.font_style, *mode, mode.label());
                }
                ui.separator();
                ui.label("Family:");
                for mode in &FontFamilyMode::ALL {
                    ui.selectable_value(&mut self.font_family, *mode, mode.label());
                }
                ui.separator();
                ui.checkbox(&mut self.show_extra, "Extra");
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
                if let Some(err) = &self.load_error {
                    ui.separator();
                    ui.colored_label(egui::Color32::RED, err);
                }
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
                    Self::render_list_row(
                        ui,
                        cp,
                        info,
                        &self.font_data,
                        row_height,
                        self.font_scale,
                        cols,
                    );
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
        font_data: &[LoadedFont],
        row_height: f32,
        font_scale: f32,
        cols: (f32, f32, f32, f32, f32),
    ) {
        let ch = char::from_u32(cp).unwrap_or('\u{FFFD}');

        ui.horizontal(|ui: &mut egui::Ui| {
            render_glyph_cell(ui, ch, info, font_data, cols.0, row_height, font_scale);
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

    fn show_grid_view(&mut self, ui: &mut egui::Ui) {
        let row_header_width = self.font_scale * 5.0;
        let slot_width = (self.font_scale + 12.0).max(26.0);
        let row_height = (self.font_scale + 10.0).max(28.0);
        let num_rows = self.grid_rows.len();

        ScrollArea::both()
            .auto_shrink([false; 2])
            .scroll_bar_visibility(egui::scroll_area::ScrollBarVisibility::AlwaysVisible)
            .show_rows(ui, row_height, num_rows, |ui, row_range| {
                for row in row_range {
                    self.render_grid_row(
                        ui,
                        self.grid_rows[row],
                        row_header_width,
                        slot_width,
                        row_height,
                        self.font_scale,
                    );
                }
            });
    }

    fn render_grid_row(
        &mut self,
        ui: &mut egui::Ui,
        row_start: u32,
        row_header_width: f32,
        slot_width: f32,
        row_height: f32,
        font_size: f32,
    ) {
        ui.horizontal(|ui| {
            ui.spacing_mut().item_spacing = egui::Vec2::ZERO;
            ui.add_sized(
                [row_header_width, row_height],
                egui::Label::new(
                    RichText::new(format!("{row_start:04X}"))
                        .monospace()
                        .strong()
                        .size(font_size * 0.8),
                ),
            );
            for offset in 0..16 {
                let cp = row_start + offset;
                if let Some(info) = self.glyph_map.get(&cp) {
                    let ch = char::from_u32(cp).unwrap_or('\u{FFFD}');
                    let color =
                        if !self.search.is_empty() && self.filtered.binary_search(&cp).is_err() {
                            egui::Color32::from_gray(170)
                        } else {
                            ui.visuals().text_color()
                        };
                    let resp = render_glyph_cell_with_color(
                        ui,
                        ch,
                        info,
                        &self.font_data,
                        slot_width,
                        row_height,
                        font_size,
                        color,
                    )
                    .on_hover_ui(|ui| {
                        ui.label(format!("U+{:04X} ({})", cp, info.plane));
                        ui.label(format!("Category: {}", info.category));
                        if let Some(n) = &info.name {
                            ui.label(n.as_str());
                        }
                    });
                    if self.selected_grid_cp == Some(cp) {
                        ui.painter().rect_stroke(
                            resp.rect.shrink(1.0),
                            0.0,
                            egui::Stroke::new(1.0, ui.visuals().selection.stroke.color),
                            egui::StrokeKind::Inside,
                        );
                    }
                    if resp.clicked() {
                        self.selected_grid_cp = Some(cp);
                    }
                    if resp.double_clicked() {
                        copy_grid_char(ui, cp);
                    }
                    resp.context_menu(|ui| {
                        if ui.button("Copy Character").clicked() {
                            copy_grid_char(ui, cp);
                            ui.close();
                        }
                        if ui.button("Copy Codepoint").clicked() {
                            ui.ctx().copy_text(format!("U+{cp:04X}"));
                            ui.close();
                        }
                    });
                } else {
                    ui.add_sized(
                        [slot_width, row_height],
                        egui::Label::new(RichText::new("").size(font_size)),
                    );
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

        let old_style = self.font_style;
        let old_family = self.font_family;
        let old_show_extra = self.show_extra;

        self.show_top_panel(ui);
        self.handle_grid_copy_shortcut(ui);

        if self.font_style != old_style
            || self.font_family != old_family
            || self.show_extra != old_show_extra
        {
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
                DisplayMode::Grid => self.show_grid_view(ui),
                _ if self.filtered.is_empty() => {
                    ui.label("No glyphs match the search.");
                }
                DisplayMode::List => self.show_list_view(ui),
            }
        });
    }
}
