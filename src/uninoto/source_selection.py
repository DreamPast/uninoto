from __future__ import annotations

from pathlib import Path

from .font_io import FontInfo
from .planes import Category, FontFamily

CjkRegion = str


def _norm(path: Path) -> str:
    return path.as_posix().lower()


def cjk_source_rank(path: Path, region: CjkRegion) -> tuple[int, str]:
    text = _norm(path)
    region_tokens = {
        "sc": ("cjksc", "notosanssc", "notoserifsc", "/sc/", "hans"),
        "tc": ("cjktc", "notosanstc", "notoseriftc", "/tc/", "hant"),
        "hk": ("cjkhk", "notosanshk", "notoserifhk", "/hk/"),
        "jp": ("cjkjp", "notosansjp", "notoserifjp", "/jp/"),
        "kr": ("cjkkr", "notosanskr", "notoserifkr", "/kr/"),
    }
    tokens = region_tokens.get(region, region_tokens["sc"])
    if any(token in text for token in tokens):
        return (0, text)
    if region != "sc" and any(token in text for token in region_tokens["sc"]):
        return (1, text)
    if is_babelstone_fallback_source(path):
        return (3, text)
    if is_fairfax_fallback_source(path):
        return (99, text)
    if "/fallback/" in text:
        return (4, text)
    if "cjk" in text:
        return (2, text)
    return (5, text)


def style_rank(path: Path) -> tuple[int, str]:
    name = path.name.lower()
    normalized = _norm(path)
    is_cjk_regional_vf = (
        "/noto-cjk/" in normalized and name.endswith("-vf.ttf") and "mono" not in name
    )
    is_variable = "[" in name or "-vf" in name
    is_regular = "regular" in name and "italic" not in name
    is_ui = "ui" in name
    is_bold = "bold" in name or "black" in name
    is_italic = "italic" in name
    score = 0 if is_regular else 5 if is_cjk_regional_vf else 10
    score += 1 if is_ui else 0
    score += 4 if is_variable else 0
    score += 20 if is_bold else 0
    score += 30 if is_italic else 0
    return (score, normalized)


def is_fallback_source(path: Path) -> bool:
    return "/fallback/" in _norm(path)


def is_babelstone_fallback_source(path: Path) -> bool:
    normalized = _norm(path)
    return "/fallback/" in normalized and path.name.lower().startswith("babelstone")


def is_fairfax_fallback_source(path: Path) -> bool:
    normalized = _norm(path)
    return (
        "/fallback/fairfaxhd/" in normalized
        and path.name.lower() == "fairfaxhd-nocjk-newname.ttf"
    )


def fallback_family_rank(path: Path) -> int:
    if not is_fallback_source(path):
        return 0
    if is_fairfax_fallback_source(path):
        return 100
    return 0 if is_babelstone_fallback_source(path) else 10


def source_freshness_rank(path: Path) -> int:
    normalized = _norm(path)
    if "/noto-monthly/" in normalized:
        return 0
    return 1


def source_family(path: Path) -> str:
    normalized = _norm(path)
    basename = path.name.lower()
    if (
        "notosansmono" in normalized
        or "mono" in basename
        or basename == "cascadiacode-regular.ttf"
    ):
        return "mono"
    if "notosans" in normalized or "sanscjk" in normalized or "sans" in basename:
        return "sans"
    if (
        "notoserif" in normalized
        or "serifcjk" in normalized
        or "serif" in basename
        or "serief" in basename
    ):
        return "serif"
    return "neutral"


def requested_family_rank(path: Path, family: FontFamily) -> int:
    source = source_family(path)
    if family == "last":
        return 0 if source == "neutral" else 2
    if family == "mono":
        if source == "mono":
            return 0
        if source == "sans":
            return 1
        if source == "neutral":
            return 2
        return 99
    if source == family:
        return 0
    if source == "neutral":
        return 1
    return 2


def source_family_eligible(path: Path, family: FontFamily) -> bool:
    source = source_family(path)
    if family == "mono":
        return source != "serif"
    return source == "neutral" if family == "last" else source in {family, "neutral"}


def source_family_rank(path: Path, category: Category, family: FontFamily) -> int:
    normalized = _norm(path)
    name = path.name.lower()
    if is_fairfax_fallback_source(path):
        return 99
    if category in {"bmp", "upper1"}:
        if family == "mono" and "notosansmono" in normalized:
            return 0
        if family == "mono" and name == "cascadiacode-regular.ttf":
            return 1
        if (
            family == "sans"
            and "/notosans/" in normalized
            and name == "notosans-regular.ttf"
        ):
            return 0
        if (
            family == "serif"
            and "/notoserif/" in normalized
            and name == "notoserif-regular.ttf"
        ):
            return 0
        priority = (
            ("notosanssymbols2", 2),
            ("notosanssymbols", 3),
            ("notomusic", 4),
            ("notosansmath", 5),
            ("notonaskharabic", 6),
            ("notosansarabicui", 8),
            ("notosansarabic", 7),
        )
        for token, rank in priority:
            if token in normalized:
                return rank
        if "/notosans/" in normalized:
            return 9
        if is_fallback_source(path):
            return 19
        return 20
    if is_fallback_source(path):
        return 19
    if family == "mono" and "notosansmono" in normalized:
        return 0
    if family == "sans" and "/notosans" in normalized:
        return 0
    if family == "serif" and "/notoserif" in normalized:
        return 0
    if "/notosans" in normalized or "/notoserif" in normalized:
        return 5
    return 20


def ordered_fonts(
    category: Category, fonts: list[FontInfo], family: FontFamily = "sans"
) -> list[FontInfo]:
    eligible = [font for font in fonts if source_family_eligible(font.path, family)]
    if category == "upper2":
        return sorted(
            eligible,
            key=lambda f: (
                requested_family_rank(f.path, family),
                cjk_source_rank(f.path, "sc")[0],
                style_rank(f.path)[0],
                cjk_source_rank(f.path, "sc")[1],
            ),
        )
    return sorted(
        eligible,
        key=lambda f: (
            requested_family_rank(f.path, family),
            source_family_rank(f.path, category, family),
            source_freshness_rank(f.path),
            fallback_family_rank(f.path),
            style_rank(f.path)[0],
            style_rank(f.path)[1],
        ),
    )
