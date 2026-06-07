use std::collections::BTreeMap;
use std::sync::Arc;

use egui::{FontData, FontDefinitions, FontFamily};
use unicode_names2::name;

const UNINOTO_LAST: &[u8] = include_bytes!("../../fonts/merged/uninoto_last.ttf");

const FONTS_SANS: [(&str, &[u8]); 4] = [
    (
        "uninoto_sans",
        include_bytes!("../../fonts/merged/uninoto_sans.ttf"),
    ),
    (
        "uninoto_sans_upper1",
        include_bytes!("../../fonts/merged/uninoto_sans_upper1.ttf"),
    ),
    (
        "uninoto_sans_upper2",
        include_bytes!("../../fonts/merged/uninoto_sans_upper2.ttf"),
    ),
    ("uninoto_last", UNINOTO_LAST),
];

const FONTS_SERIF: [(&str, &[u8]); 4] = [
    (
        "uninoto_serif",
        include_bytes!("../../fonts/merged/uninoto_serif.ttf"),
    ),
    (
        "uninoto_serif_upper1",
        include_bytes!("../../fonts/merged/uninoto_serif_upper1.ttf"),
    ),
    (
        "uninoto_serif_upper2",
        include_bytes!("../../fonts/merged/uninoto_serif_upper2.ttf"),
    ),
    ("uninoto_last", UNINOTO_LAST),
];

const FONTS_MONO: [(&str, &[u8]); 3] = [
    (
        "uninoto_mono",
        include_bytes!("../../fonts/merged/uninoto_mono.ttf"),
    ),
    (
        "uninoto_mono_upper1",
        include_bytes!("../../fonts/merged/uninoto_mono_upper1.ttf"),
    ),
    (
        "uninoto_mono_upper2",
        include_bytes!("../../fonts/merged/uninoto_mono_upper2.ttf"),
    ),
];

#[derive(Clone, Copy, PartialEq)]
pub enum FontFamilyMode {
    Sans,
    Serif,
    Mono,
}

impl FontFamilyMode {
    pub const ALL: [FontFamilyMode; 3] = [
        FontFamilyMode::Sans,
        FontFamilyMode::Serif,
        FontFamilyMode::Mono,
    ];

    pub fn label(self) -> &'static str {
        match self {
            Self::Sans => "Sans",
            Self::Serif => "Serif",
            Self::Mono => "Mono",
        }
    }

    pub fn font_data(self) -> Vec<(String, &'static [u8])> {
        let fonts: &[(&str, &[u8])] = match self {
            Self::Sans => &FONTS_SANS,
            Self::Serif => &FONTS_SERIF,
            Self::Mono => &FONTS_MONO,
        };
        fonts
            .iter()
            .map(|(name, data)| (name.to_string(), *data))
            .collect()
    }
}

pub fn setup_fonts(ctx: &egui::Context, font_data: &[(String, &'static [u8])]) {
    let mut fonts = FontDefinitions::default();
    fonts.font_data.clear();
    let mut font_names: Vec<String> = Vec::new();

    for (name, data) in font_data {
        fonts
            .font_data
            .insert(name.clone(), Arc::new(FontData::from_static(data)));
        fonts.families.insert(
            FontFamily::Name(Arc::from(name.as_str())),
            vec![name.clone()],
        );
        font_names.push(name.clone());
    }

    *fonts.families.entry(FontFamily::Monospace).or_default() = font_names.clone();
    *fonts.families.entry(FontFamily::Proportional).or_default() = font_names.clone();
    ctx.set_fonts(fonts);
}

pub fn plane_name(cp: u32) -> &'static str {
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

pub fn category_abbr(ch: char) -> &'static str {
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

#[derive(Clone)]
#[allow(dead_code)]
pub struct GlyphInfo {
    pub font_index: usize,
    pub font_family: FontFamily,
    pub name: Option<String>,
    pub plane: &'static str,
    pub category: &'static str,
}

pub fn load_glyph_map(font_data: &[(String, &'static [u8])]) -> BTreeMap<u32, GlyphInfo> {
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

pub fn build_grid_rows(codepoints: &[u32]) -> Vec<String> {
    let num_rows = codepoints.len().div_ceil(32);
    let mut rows = Vec::with_capacity(num_rows);
    for chunk in codepoints.chunks(32) {
        let row: String = chunk.iter().filter_map(|cp| char::from_u32(*cp)).collect();
        rows.push(row);
    }
    rows
}
