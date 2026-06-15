use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use egui::{FontData, FontDefinitions, FontFamily};
use unicode_names2::name;

pub type LoadedFont = (String, Vec<u8>);

#[derive(Clone, Copy, PartialEq)]
pub enum FontStyleMode {
    Regular,
    Bold,
    Italic,
    BoldItalic,
    Full,
}

impl FontStyleMode {
    pub const ALL: [FontStyleMode; 5] = [
        FontStyleMode::Full,
        FontStyleMode::Regular,
        FontStyleMode::Bold,
        FontStyleMode::Italic,
        FontStyleMode::BoldItalic,
    ];

    pub fn label(self) -> &'static str {
        match self {
            Self::Regular => "Regular",
            Self::Bold => "Bold",
            Self::Italic => "Italic",
            Self::BoldItalic => "Bold Italic",
            Self::Full => "Full",
        }
    }

    fn folder(self) -> &'static str {
        match self {
            Self::Regular => "regular",
            Self::Bold => "bold",
            Self::Italic => "italic",
            Self::BoldItalic => "bolditalic",
            Self::Full => "full",
        }
    }
}

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

    fn prefix(self) -> &'static str {
        match self {
            Self::Sans => "uninoto_sans",
            Self::Serif => "uninoto_serif",
            Self::Mono => "uninoto_mono",
        }
    }
}

pub fn resolve_font_root(path_text: &str) -> PathBuf {
    let path = PathBuf::from(path_text.trim());
    if path.is_absolute() {
        path
    } else {
        PathBuf::from(env!("CARGO_MANIFEST_DIR")).join(path)
    }
}

pub fn load_font_data(
    root: &Path,
    style: FontStyleMode,
    family: FontFamilyMode,
) -> Result<Vec<LoadedFont>, String> {
    let style_dir = root.join(style.folder());
    let font_dir = if style_dir.is_dir() {
        style_dir
    } else if root.is_dir() {
        root.to_path_buf()
    } else {
        return Err(format!("Font folder not found: {}", root.display()));
    };

    let mut paths = matching_font_paths(&font_dir, family.prefix())?;
    if family != FontFamilyMode::Mono {
        paths.extend(matching_font_paths(&font_dir, "uninoto_last")?);
    }

    if paths.is_empty() {
        return Err(format!(
            "No {} fonts found in {}",
            family.label(),
            font_dir.display()
        ));
    }

    let mut fonts = Vec::with_capacity(paths.len());
    for path in paths {
        let name = path
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("font")
            .to_string();
        let data = fs::read(&path).map_err(|err| format!("{}: {err}", path.display()))?;
        fonts.push((name, data));
    }
    Ok(fonts)
}

fn matching_font_paths(dir: &Path, prefix: &str) -> Result<Vec<PathBuf>, String> {
    let entries = fs::read_dir(dir).map_err(|err| format!("{}: {err}", dir.display()))?;
    let mut paths: Vec<PathBuf> = entries
        .filter_map(Result::ok)
        .map(|entry| entry.path())
        .filter(|path| {
            let Some(file_name) = path.file_name().and_then(|s| s.to_str()) else {
                return false;
            };
            let Some(ext) = path.extension().and_then(|s| s.to_str()) else {
                return false;
            };
            let file_name = file_name.to_ascii_lowercase();
            let ext = ext.to_ascii_lowercase();
            (ext == "ttf" || ext == "otf") && file_name.starts_with(prefix)
        })
        .collect();
    paths.sort_by(|a, b| font_sort_key(a, prefix).cmp(&font_sort_key(b, prefix)));
    Ok(paths)
}

fn font_sort_key(path: &Path, prefix: &str) -> (u8, u32, String) {
    let stem = path
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    if stem == prefix {
        return (0, 0, stem);
    }
    if let Some(suffix) = stem.strip_prefix(&format!("{prefix}_upper")) {
        let index = suffix.parse::<u32>().unwrap_or(0);
        return (1, index, stem);
    }
    if let Some(suffix) = stem.strip_prefix(prefix) {
        let index = suffix.parse::<u32>().unwrap_or(0);
        return (2, index, stem);
    }
    (3, 0, stem)
}

pub fn setup_fonts(ctx: &egui::Context, font_data: &[LoadedFont]) {
    let mut fonts = FontDefinitions::default();
    fonts.font_data.clear();
    let mut font_names: Vec<String> = Vec::new();

    for (name, data) in font_data {
        fonts
            .font_data
            .insert(name.clone(), Arc::new(FontData::from_owned(data.clone())));
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

pub fn build_grid_rows(codepoints: &[u32]) -> Vec<String> {
    let num_rows = codepoints.len().div_ceil(32);
    let mut rows = Vec::with_capacity(num_rows);
    for chunk in codepoints.chunks(32) {
        let row: String = chunk.iter().filter_map(|cp| char::from_u32(*cp)).collect();
        rows.push(row);
    }
    rows
}
