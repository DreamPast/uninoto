use crate::font_data::LoadedFont;
use crate::glyph_data::GlyphInfo;

pub(crate) fn render_glyph_cell(
    ui: &mut egui::Ui,
    ch: char,
    info: &GlyphInfo,
    font_data: &[LoadedFont],
    width: f32,
    height: f32,
    font_size: f32,
) -> egui::Response {
    render_glyph_cell_with_color(
        ui,
        ch,
        info,
        font_data,
        width,
        height,
        font_size,
        ui.visuals().text_color(),
    )
}

pub(crate) fn render_glyph_cell_with_color(
    ui: &mut egui::Ui,
    ch: char,
    info: &GlyphInfo,
    font_data: &[LoadedFont],
    width: f32,
    height: f32,
    font_size: f32,
    color: egui::Color32,
) -> egui::Response {
    let (rect, response) = ui.allocate_exact_size(egui::vec2(width, height), egui::Sense::click());
    if ch.is_control() {
        if !paint_outline_glyph(ui, rect, ch, info, font_data, font_size, color) {
            ui.painter().text(
                rect.center(),
                egui::Align2::CENTER_CENTER,
                "",
                egui::FontId::new(font_size, info.font_family.clone()),
                color,
            );
        }
        response
    } else {
        ui.painter().text(
            rect.center(),
            egui::Align2::CENTER_CENTER,
            ch.to_string(),
            egui::FontId::new(font_size, info.font_family.clone()),
            color,
        );
        response
    }
}

fn paint_outline_glyph(
    ui: &mut egui::Ui,
    rect: egui::Rect,
    ch: char,
    info: &GlyphInfo,
    font_data: &[LoadedFont],
    font_size: f32,
    color: egui::Color32,
) -> bool {
    let Some((_, data)) = font_data.get(info.font_index) else {
        return false;
    };
    let Ok(face) = ttf_parser::Face::parse(data, 0) else {
        return false;
    };
    let Some(glyph_id) = face.glyph_index(ch) else {
        return false;
    };

    let mut builder = OutlinePathBuilder::default();
    let Some(bbox) = face.outline_glyph(glyph_id, &mut builder) else {
        return false;
    };
    let units_per_em = face.units_per_em() as f32;
    if units_per_em <= 0.0 {
        return false;
    }
    let scale = font_size / units_per_em;
    let glyph_width = (bbox.x_max - bbox.x_min) as f32 * scale;
    let glyph_height = (bbox.y_max - bbox.y_min) as f32 * scale;
    if glyph_width <= 0.0 || glyph_height <= 0.0 {
        return false;
    }

    let left = rect.center().x - glyph_width / 2.0;
    let bottom = rect.center().y + glyph_height / 2.0;
    let transform = |x: f32, y: f32| {
        egui::pos2(
            left + (x - bbox.x_min as f32) * scale,
            bottom - (y - bbox.y_min as f32) * scale,
        )
    };

    let stroke = egui::Stroke::new(1.0, color);
    for contour in builder.contours {
        if contour.len() >= 2 {
            let points = contour
                .into_iter()
                .map(|(x, y)| transform(x, y))
                .collect::<Vec<_>>();
            ui.painter().add(egui::Shape::closed_line(points, stroke));
        }
    }
    true
}

#[derive(Default)]
struct OutlinePathBuilder {
    contours: Vec<Vec<(f32, f32)>>,
    current: Vec<(f32, f32)>,
    last: Option<(f32, f32)>,
}

impl OutlinePathBuilder {
    fn push(&mut self, x: f32, y: f32) {
        self.current.push((x, y));
        self.last = Some((x, y));
    }

    fn finish_contour(&mut self) {
        if !self.current.is_empty() {
            self.contours.push(std::mem::take(&mut self.current));
        }
        self.last = None;
    }
}

impl ttf_parser::OutlineBuilder for OutlinePathBuilder {
    fn move_to(&mut self, x: f32, y: f32) {
        self.finish_contour();
        self.push(x, y);
    }

    fn line_to(&mut self, x: f32, y: f32) {
        self.push(x, y);
    }

    fn quad_to(&mut self, x1: f32, y1: f32, x: f32, y: f32) {
        let Some((x0, y0)) = self.last else {
            self.push(x, y);
            return;
        };
        for step in 1..=8 {
            let t = step as f32 / 8.0;
            let mt = 1.0 - t;
            self.push(
                mt * mt * x0 + 2.0 * mt * t * x1 + t * t * x,
                mt * mt * y0 + 2.0 * mt * t * y1 + t * t * y,
            );
        }
    }

    fn curve_to(&mut self, x1: f32, y1: f32, x2: f32, y2: f32, x: f32, y: f32) {
        let Some((x0, y0)) = self.last else {
            self.push(x, y);
            return;
        };
        for step in 1..=12 {
            let t = step as f32 / 12.0;
            let mt = 1.0 - t;
            self.push(
                mt * mt * mt * x0 + 3.0 * mt * mt * t * x1 + 3.0 * mt * t * t * x2 + t * t * t * x,
                mt * mt * mt * y0 + 3.0 * mt * mt * t * y1 + 3.0 * mt * t * t * y2 + t * t * t * y,
            );
        }
    }

    fn close(&mut self) {
        self.finish_contour();
    }
}
