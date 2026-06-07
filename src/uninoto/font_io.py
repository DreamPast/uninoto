from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fontTools.ttLib import TTFont

from .unicode_utils import is_mergeable_codepoint

LEGACY_NOTO_SOURCE_SEGMENTS = ("/noto-fonts/", "/noto-cjkext/", "/noto-extra/")


@dataclass(frozen=True)
class FontInfo:
    path: Path
    codepoints: frozenset[int]


def font_type_from_path(path: Path) -> str | None:
    suffix = path.suffix.lower()
    if suffix == ".ttf":
        return "ttf"
    if suffix == ".otf":
        return "otf"
    return None


def list_font_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(
        (p for p in root.rglob("*") if p.is_file() and font_type_from_path(p)),
        key=lambda p: str(p).lower(),
    )


def _norm(path: Path) -> str:
    return path.as_posix().lower()


def _is_babelstone_static_ttf(basename: str) -> bool:
    if not basename.endswith(".ttf") or not basename.startswith("babelstone"):
        return False
    blocked = ("pua", "colour", "color", "vertical", "rotated", "inverse")
    return not any(token in basename for token in blocked)


def is_regular_static_source_font(path: Path) -> bool:
    normalized = _norm(path)
    basename = path.name.lower()
    if any(segment in normalized for segment in LEGACY_NOTO_SOURCE_SEGMENTS):
        return False
    if "/extracted/" in normalized:
        return False
    if "/noto-emoji/" in normalized:
        return basename in {
            "notoemoji-regular.ttf",
            "noto-colrv1.ttf",
            "noto-colrv1-noflags.ttf",
        }
    if "/fallback/" in normalized:
        if basename == "abydos.ttf":
            return normalized.endswith("/fallback/abydos.ttf")
        if basename == "notofangsongkssvertical-regular.ttf":
            return "/googlefonts/ttf/" in normalized or normalized.endswith(
                "/fallback/notofangsongkssvertical-v1.000/notofangsongkssvertical-regular.ttf"
            )
        if basename in {"hanaminb.otf", "hanaminc.otf"}:
            return True
        return _is_babelstone_static_ttf(basename) or basename in {
            "cascadiacode-regular.ttf",
            "hanaminb.ttf",
            "hanaminc.ttf",
            "scriptwidesanscjk-a.ttf",
            "scriptwidesanscjk-b.ttf",
            "scriptwidesanscjk-c.ttf",
            "kanchenjunga-regular.ttf",
            "junicode-regular.ttf",
            "kedebideri-regular.ttf",
            "charis-regular.ttf",
            "doulossil-regular.ttf",
            "fairfaxhd-nocjk-newname.ttf",
        }
    if not (basename.endswith(".ttf") or basename.endswith(".otf")):
        return False
    if "regular" not in basename:
        return False
    if "-italic" in basename or "-oblique" in basename:
        return False
    if any(
        token in basename
        for token in ("bold", "black", "medium", "light", "thin", "[", "]", "-vf")
    ):
        return False
    if "/variable/" in normalized or "ttf-vf" in normalized or "otf-vf" in normalized:
        return False
    return True


CodepointFilter = Callable[[int], bool]


def read_font_codepoint_map(
    path: Path, codepoint_filter: CodepointFilter = is_mergeable_codepoint
) -> dict[int, str]:
    font = TTFont(path, lazy=True, fontNumber=0)
    try:
        cmap = font.getBestCmap() or {}
        return {cp: glyph for cp, glyph in cmap.items() if codepoint_filter(cp)}
    finally:
        font.close()


def read_font_codepoints(
    path: Path, codepoint_filter: CodepointFilter = is_mergeable_codepoint
) -> set[int]:
    return set(read_font_codepoint_map(path, codepoint_filter))


def discover_fonts(
    root: Path, codepoint_filter: CodepointFilter = is_mergeable_codepoint
) -> list[FontInfo]:
    fonts: list[FontInfo] = []
    for file in (p for p in list_font_files(root) if is_regular_static_source_font(p)):
        try:
            cmap = read_font_codepoint_map(file, codepoint_filter)
        except Exception as exc:
            print(f"skip invalid font: {file} ({exc})")
            continue
        if cmap:
            fonts.append(FontInfo(path=file, codepoints=frozenset(cmap)))
    return fonts
