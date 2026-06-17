use egui::TextEdit;

pub(crate) fn spin_box(
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
            let v = if v.is_nan() {
                default
            } else {
                v.clamp(min, max)
            };
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

pub(crate) fn parse_hex(s: &str) -> Option<u32> {
    let s = s.trim();
    let s = s
        .strip_prefix("U+")
        .or_else(|| s.strip_prefix("u+"))
        .unwrap_or(s);
    u32::from_str_radix(s, 16).ok()
}
