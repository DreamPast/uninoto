use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use egui::{FontData, FontDefinitions, FontFamily};

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
    show_extra: bool,
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
    if show_extra && family != FontFamilyMode::Mono {
        paths.extend(matching_font_paths(&font_dir, family.extra_prefix())?);
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

impl FontFamilyMode {
    fn extra_prefix(self) -> &'static str {
        match self {
            Self::Sans => "uninoto_sans_extra",
            Self::Serif => "uninoto_serif_extra",
            Self::Mono => "uninoto_mono_extra",
        }
    }
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
            (ext == "ttf" || ext == "otf") && font_name_matches_prefix(&file_name, prefix)
        })
        .collect();
    paths.sort_by(|a, b| font_sort_key(a, prefix).cmp(&font_sort_key(b, prefix)));
    Ok(paths)
}

fn font_name_matches_prefix(file_name: &str, prefix: &str) -> bool {
    let stem = file_name
        .strip_suffix(".ttf")
        .or_else(|| file_name.strip_suffix(".otf"))
        .unwrap_or(file_name);
    let Some(suffix) = stem.strip_prefix(prefix) else {
        return false;
    };
    suffix.is_empty()
        || suffix.chars().all(|ch| ch.is_ascii_digit())
        || suffix.starts_with("_upper")
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
