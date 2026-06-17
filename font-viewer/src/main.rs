#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod app;
mod controls;
mod font_data;
mod glyph_data;
mod glyph_paint;
mod util;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        renderer: eframe::Renderer::Glow,
        viewport: egui::ViewportBuilder::default().with_inner_size([1000.0, 750.0]),
        ..Default::default()
    };
    eframe::run_native(
        "Font Viewer",
        options,
        Box::new(|cc| Ok(Box::new(app::ViewerApp::new(cc)))),
    )
}
