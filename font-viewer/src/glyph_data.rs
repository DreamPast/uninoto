use std::collections::{BTreeMap, BTreeSet};
use std::sync::Arc;

use egui::FontFamily;
use unicode_names2::name;

use crate::font_data::LoadedFont;

#[derive(Clone)]
#[allow(dead_code)]
pub struct GlyphInfo {
    pub font_index: usize,
    pub font_family: FontFamily,
    pub name: Option<String>,
    pub plane: &'static str,
    pub category: &'static str,
}

pub fn load_glyph_map(font_data: &[LoadedFont]) -> BTreeMap<u32, GlyphInfo> {
    let mut map = BTreeMap::new();
    for (idx, (font_name, data)) in font_data.iter().enumerate() {
        let font_family = FontFamily::Name(Arc::from(font_name.as_str()));
        let face = ttf_parser::Face::parse(data, 0).expect("Failed to parse font");
        if let Some(cmap) = face.tables().cmap {
            for subtable in cmap.subtables {
                let is_unicode_cmap = subtable.platform_id == ttf_parser::PlatformId::Unicode
                    || (subtable.platform_id == ttf_parser::PlatformId::Windows
                        && (subtable.encoding_id == 1 || subtable.encoding_id == 10));
                if !is_unicode_cmap {
                    continue;
                }
                subtable.codepoints(|cp| {
                    if !map.contains_key(&cp) {
                        if let Some(ch) = char::from_u32(cp) {
                            map.insert(
                                cp,
                                GlyphInfo {
                                    font_index: idx,
                                    font_family: font_family.clone(),
                                    name: name(ch).map(|n| n.to_string()),
                                    plane: plane_name(cp),
                                    category: category_abbr(ch),
                                },
                            );
                        }
                    }
                });
            }
        }
    }
    map
}

pub fn build_grid_rows(filtered: &[u32], search_active: bool) -> Vec<u32> {
    if search_active {
        let mut rows = Vec::new();
        let mut last_start = None;
        for cp in filtered {
            let start = cp & !0xF;
            if last_start != Some(start) {
                rows.push(start);
                last_start = Some(start);
            }
        }
        return rows;
    }

    let mut rows: BTreeSet<u32> = filtered.iter().map(|cp| cp & !0xF).collect();
    rows.extend(
        (0..=0x10FFF0)
            .step_by(16)
            .filter(|row_start| row_has_meaningful_codepoint(*row_start)),
    );
    rows.into_iter().collect()
}

fn plane_name(cp: u32) -> &'static str {
    match cp >> 16 {
        0 => "BMP",
        1 => "SMP",
        2 => "SIP",
        3 => "TIP",
        14 => "SSP",
        15 | 16 => "SPUA",
        _ => "?",
    }
}

fn category_abbr(ch: char) -> &'static str {
    if ch.is_ascii_uppercase() {
        "Lu"
    } else if ch.is_ascii_lowercase() {
        "Ll"
    } else if ch.is_uppercase() {
        "Lu"
    } else if ch.is_lowercase() {
        "Ll"
    } else if ch.is_ascii_digit() {
        "Nd"
    } else if ch.is_numeric() {
        "No"
    } else if ch.is_whitespace() || ch.is_ascii_whitespace() {
        "Zs"
    } else if ch.is_control() {
        "Cc"
    } else if ch.is_ascii_punctuation() {
        "Po"
    } else if ch.is_alphabetic() {
        "Lo"
    } else if ch.is_ascii() {
        "Po"
    } else {
        "So"
    }
}

fn row_has_meaningful_codepoint(row_start: u32) -> bool {
    (0..16).any(|offset| is_meaningful_codepoint(row_start + offset))
}

fn is_meaningful_codepoint(cp: u32) -> bool {
    let Some(ch) = char::from_u32(cp) else {
        return false;
    };
    if ch.is_control() {
        return true;
    }
    if is_private_use_codepoint(cp) {
        return true;
    }
    name(ch).is_some()
}

fn is_private_use_codepoint(cp: u32) -> bool {
    (0xE000..=0xF8FF).contains(&cp)
        || (0xF0000..=0xFFFFD).contains(&cp)
        || (0x100000..=0x10FFFD).contains(&cp)
}
