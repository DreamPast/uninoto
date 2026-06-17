from __future__ import annotations

import argparse
import copy
import csv as csv_lib
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from fontTools import subset
from fontTools.merge import Merger
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable as FontToolsCmapSubtable
from fontTools.ttLib.tables._g_l_y_f import Glyph

from .font_io import FontInfo, discover_fonts, list_font_files, read_font_codepoints
from .planes import (
    EXTRA_OUTPUT_NAMES,
    FONT_FAMILIES,
    FONT_STYLES,
    LAST_RESORT_OUTPUT_NAMES,
    LEGACY_EXTRA_OUTPUT_NAMES,
    MAX_RECOGNIZED_SPLIT_OUTPUTS,
    MAX_RECOGNIZED_UPPER_OUTPUTS,
    Category,
    FontFamily,
    FontStyle,
    all_output_names,
    codepoint_in_category,
    output_name_for,
    parse_font_family,
    parse_font_style,
)
from .source_selection import ordered_fonts
from .unicode_utils import (
    CJK_RELATED_RANGES,
    EMOJI_RANGES,
    INVISIBLE_GENERAL_CATEGORIES,
    TTF_GLYPH_LIMIT,
    cp_hex,
    general_category,
    in_ranges,
    is_visible_codepoint,
)

UPPER_BUCKET_CODEPOINT_LIMIT = 50000
SPLIT_BUCKET_CODEPOINT_LIMIT = TTF_GLYPH_LIMIT - 2048
EXTRA_BUCKET_CODEPOINT_LIMIT = TTF_GLYPH_LIMIT - 1
PRESERVE_METADATA_CODEPOINT_LIMIT = 8000
PLACEHOLDER_GLYPHS = {".notdef", ".null", "nonmarkingreturn"}
LAST_RESORT_SOURCE = Path("fallback/LastResort/LastResort-Regular.ttf")
LAST_RESORT_FALLBACK_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}
LAYOUT_GLYPH_REFERENCE_TABLES = ("BASE", "GDEF", "GPOS", "GSUB", "JSTF")
PLANE_1_END = 0x1FFFF
REPORT_FAMILIES: tuple[FontFamily, ...] = ("sans", "serif", "mono")
# Verified against the current Noto mono sources: NotoSansMono Regular uses
# 600-unit Latin advances, and NotoSansMonoCJK Regular uses 1000-unit CJK/fullwidth advances.
DEFAULT_MONO_HALF_WIDTH = 600
DEFAULT_MONO_FULL_WIDTH = 1000
MERGE_UNITS_PER_EM = 1000
NOTDEF_DEFAULT_WIDTH = 600
NOTDEF_Y_MIN = -200
NOTDEF_Y_MAX = 800
NOTO_ASCENT = 1069
NOTO_DESCENT = -293
NOTO_LINE_GAP = 0
WIN_METRICS_BY_FAMILY: dict[FontFamily | None, tuple[int, int]] = {
    "sans": (1124, 395),
    "serif": (1069, 389),
    "mono": (1229, 389),
    "extra": (1124, 395),
    "last_resort": (1124, 395),
    None: (1124, 395),
}
USE_TYPO_METRICS = 1 << 7
CodepointFilter = Callable[[int], bool]
OutputNameBuilder = Callable[[int, list["SelectedCodepoint"]], str]
REGION_SPLIT_LABELS = ("sc", "tc", "hk", "jp", "kr")
STALE_SPLIT_OUTPUT_LIMIT = 512
STALE_BMP_SPLIT_OUTPUT_LIMIT = 512


def _is_capacity_error(exc: Exception) -> bool:
    text = str(exc)
    return "cannot fit into one TTF" in text or (
        " wrote " in text and f"limit {TTF_GLYPH_LIMIT}" in text
    )


def _split_selected_by_source(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    by_layout_group = _split_selected_by_layout_group(selected)
    if by_layout_group is not None:
        return by_layout_group
    source_order: list[Path] = []
    source_seen: set[Path] = set()
    for item in selected:
        path = item.font.path
        if path not in source_seen:
            source_seen.add(path)
            source_order.append(path)
    if len(source_order) <= 1:
        return None
    left_sources = set(source_order[: len(source_order) // 2])
    left = [item for item in selected if item.font.path in left_sources]
    right = [item for item in selected if item.font.path not in left_sources]
    if not left or not right:
        return None
    return left, right


def _source_layout_group(path: Path) -> tuple[str, str]:
    normalized = path.as_posix().lower()
    name = path.name.lower()
    cjk_regions = {
        "sc": ("cjksc", "notosanssc", "notoserifsc", "/sc/", "hans"),
        "tc": ("cjktc", "notosanstc", "notoseriftc", "/tc/", "hant"),
        "hk": ("cjkhk", "notosanshk", "notoserifhk", "/hk/"),
        "jp": ("cjkjp", "notosansjp", "notoserifjp", "/jp/"),
        "kr": ("cjkkr", "notosanskr", "notoserifkr", "/kr/"),
    }
    for region, tokens in cjk_regions.items():
        if any(token in normalized for token in tokens):
            return ("cjk", region)
    if "/fallback/" in normalized:
        return ("fallback", path.parent.name.lower())
    parent = path.parent.name.lower()
    if parent and parent != "ttf":
        return ("family", parent)
    return ("font", name)


def _simple_region_label(selected: list[SelectedCodepoint]) -> str | None:
    labels = {
        group[1]
        for item in selected
        for group in [_source_layout_group(item.font.path)]
        if group[0] == "cjk" and group[1] in REGION_SPLIT_LABELS
    }
    groups = {_source_layout_group(item.font.path) for item in selected}
    return next(iter(labels)) if len(labels) == 1 and len(groups) == 1 else None


class SplitOutputNameBuilder:
    def __init__(self, family: FontFamily) -> None:
        self.prefix = f"uninoto_{family}"
        self.region_counts: dict[str, int] = {}
        self.numeric_index = 0

    def snapshot(self) -> tuple[dict[str, int], int]:
        return dict(self.region_counts), self.numeric_index

    def restore(self, snapshot: tuple[dict[str, int], int]) -> None:
        self.region_counts, self.numeric_index = snapshot

    def __call__(self, _index: int, selected: list[SelectedCodepoint]) -> str:
        region = _simple_region_label(selected)
        if region:
            self.region_counts[region] = self.region_counts.get(region, 0) + 1
            count = self.region_counts[region]
            suffix = region if count == 1 else f"{region}{count}"
        else:
            self.numeric_index += 1
            suffix = str(self.numeric_index)
        return f"{self.prefix}_{suffix}.ttf"


def make_split_output_name_builder(family: FontFamily) -> SplitOutputNameBuilder:
    return SplitOutputNameBuilder(family)


def _split_selected_by_plane(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    bmp = [item for item in selected if item.codepoint <= 0xFFFF]
    upper = [item for item in selected if item.codepoint > 0xFFFF]
    if not bmp or not upper:
        return None
    return bmp, upper


def _split_selected_by_layout_group(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    group_order: list[tuple[str, str]] = []
    group_seen: set[tuple[str, str]] = set()
    for item in selected:
        group = _source_layout_group(item.font.path)
        if group not in group_seen:
            group_seen.add(group)
            group_order.append(group)
    if len(group_order) <= 1:
        return None
    left_groups = set(group_order[: len(group_order) // 2])
    left = [
        item for item in selected if _source_layout_group(item.font.path) in left_groups
    ]
    right = [
        item
        for item in selected
        if _source_layout_group(item.font.path) not in left_groups
    ]
    if not left or not right:
        return None
    return left, right


def _split_selected_for_retry(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    by_plane = _split_selected_by_plane(selected)
    if by_plane is not None:
        return by_plane
    by_source = _split_selected_by_source(selected)
    if by_source is not None:
        return by_source
    if len(selected) <= 1:
        return None
    midpoint = len(selected) // 2
    if midpoint <= 0 or midpoint >= len(selected):
        return None
    return selected[:midpoint], selected[midpoint:]


def _split_selected_by_capacity(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    if len(selected) <= SPLIT_BUCKET_CODEPOINT_LIMIT:
        return None
    left = selected[:SPLIT_BUCKET_CODEPOINT_LIMIT]
    right = selected[SPLIT_BUCKET_CODEPOINT_LIMIT:]
    if not left or not right:
        return None
    return left, right


def _split_selected_by_midpoint(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    if len(selected) <= 1:
        return None
    midpoint = len(selected) // 2
    if midpoint <= 0 or midpoint >= len(selected):
        return None
    return selected[:midpoint], selected[midpoint:]


def _split_selected_for_capacity_retry(
    selected: list[SelectedCodepoint],
) -> tuple[list[SelectedCodepoint], list[SelectedCodepoint]] | None:
    by_capacity = _split_selected_by_capacity(selected)
    if by_capacity is not None:
        return by_capacity
    return _split_selected_by_midpoint(selected)


class SubsetOptionsOverrides(Protocol):
    name_IDs: list[str]
    name_languages: list[str]
    canonical_order: bool


class HeadTable(Protocol):
    unitsPerEm: int
    glyphDataFormat: int


class HheaTable(Protocol):
    ascent: int
    descent: int
    lineGap: int


class Os2Table(Protocol):
    sTypoAscender: int
    sTypoDescender: int
    sTypoLineGap: int
    usWinAscent: int
    usWinDescent: int
    fsSelection: int
    usMaxContext: int


class NameTable(Protocol):
    def removeNames(self, **kwargs: int) -> None: ...

    def setName(
        self,
        string: str,
        nameID: int,
        platformID: int,
        platEncID: int,
        langID: int,
    ) -> None: ...


class HmtxTable(Protocol):
    metrics: dict[str, tuple[int, int]]


class CmapSubtable(Protocol):
    format: int
    cmap: dict[int, str]


class CmapTable(Protocol):
    tables: list[CmapSubtable]


class GlyfTable(Protocol):
    glyphs: dict[str, Glyph]
    glyphOrder: list[str]

    def __getitem__(self, glyph_name: str) -> Glyph: ...


class MaxpTable(Protocol):
    tableVersion: int
    maxZones: int
    maxTwilightPoints: int
    maxStorage: int
    maxFunctionDefs: int
    maxInstructionDefs: int
    maxStackElements: int
    maxSizeOfInstructions: int
    maxComponentElements: int
    maxComponentDepth: int

    def recalc(self, ttFont: TTFont) -> None: ...


@dataclass(frozen=True)
class Options:
    input: Path
    output: Path
    family: FontFamily | None
    styles: tuple[FontStyle, ...]
    missing_output: Path
    missing_summary_output: Path | None
    include_marks: bool
    derived_age: Path
    unicode_data: Path


@dataclass(frozen=True)
class AgeRange:
    start: int
    end: int
    version: str


@dataclass(frozen=True)
class GeneralCategoryRange:
    start: int
    end: int
    category: str


@dataclass(frozen=True)
class SelectedCodepoint:
    codepoint: int
    font: FontInfo


@dataclass(frozen=True)
class WriteResult:
    glyphs: int
    pruned: int
    preserved_metadata: bool


def output_font_name(file_path: Path) -> str | None:
    names = set(all_output_names())
    return file_path.name if file_path.name in names else None


def report_path_for_family(output: Path, family: FontFamily) -> Path:
    suffix = output.suffix or ".csv"
    return output.with_name(f"{family}-{output.stem}{suffix}")


def output_root_for_style(output: Path, style: FontStyle) -> Path:
    if output.name in FONT_STYLES:
        return output if output.name == style else output.parent / style
    return output / style


def report_file_for_style(output: Path, style: FontStyle) -> Path:
    if output.parent.name in FONT_STYLES:
        return (
            output
            if output.parent.name == style
            else output.parent.parent / style / output.name
        )
    return output.parent / style / output.name


def selected_codepoints_for_category(
    category: Category,
    fonts: list[FontInfo],
    family: FontFamily,
    style: FontStyle,
) -> list[SelectedCodepoint]:
    selected: dict[int, FontInfo] = {}
    for info in ordered_fonts(category, fonts, family, style):
        for cp in info.codepoints:
            if codepoint_in_category(category, cp) and cp not in selected:
                selected[cp] = info
    return [SelectedCodepoint(cp, selected[cp]) for cp in sorted(selected)]


def selected_upper_codepoints(
    fonts: list[FontInfo],
    family: FontFamily,
    style: FontStyle,
) -> list[SelectedCodepoint]:
    selected: dict[int, FontInfo] = {}
    for info in ordered_fonts("upper1", fonts, family, style):
        for cp in info.codepoints:
            if 0x10000 <= cp <= PLANE_1_END and cp not in selected:
                selected[cp] = info
    for info in ordered_fonts("upper2", fonts, family, style):
        for cp in info.codepoints:
            if cp > PLANE_1_END and cp not in selected:
                selected[cp] = info
    return [SelectedCodepoint(cp, selected[cp]) for cp in sorted(selected)]


def selected_output_codepoints(
    fonts: list[FontInfo],
    family: FontFamily,
    style: FontStyle,
) -> list[SelectedCodepoint]:
    return sorted(
        [
            *selected_codepoints_for_category("bmp", fonts, family, style),
            *selected_upper_codepoints(fonts, family, style),
        ],
        key=lambda item: item.codepoint,
    )


def target_mono_width(codepoint: int | None) -> int:
    if codepoint is None:
        return DEFAULT_MONO_HALF_WIDTH
    category = general_category(codepoint)
    if category.startswith("M"):
        return 0
    if in_ranges(codepoint, CJK_RELATED_RANGES) or in_ranges(codepoint, EMOJI_RANGES):
        return DEFAULT_MONO_FULL_WIDTH
    return DEFAULT_MONO_HALF_WIDTH


def _glyph_bounds(glyph: Glyph) -> tuple[int, int] | None:
    coords = getattr(glyph, "coordinates", None)
    if not coords:
        return None
    xs = [int(point[0]) for point in coords]
    return (min(xs), max(xs)) if xs else None


def _normalize_mono_widths(font: TTFont) -> None:
    cmap = cast(dict[int, str], font.getBestCmap() or {})
    glyph_to_codepoint = {glyph: cp for cp, glyph in cmap.items()}
    glyf = cast(GlyfTable, font["glyf"])
    hmtx = cast(HmtxTable, font["hmtx"])
    glyph_order = cast(list[str], font.getGlyphOrder())
    for glyph_name in glyph_order:
        if glyph_name == ".notdef":
            continue
        glyph = glyf[glyph_name]
        codepoint = glyph_to_codepoint.get(glyph_name)
        target = target_mono_width(codepoint)
        _advance, _lsb = hmtx.metrics.get(glyph_name, (target, 0))
        if target == 0:
            hmtx.metrics[glyph_name] = (0, 0)
            continue
        if not hasattr(glyph, "coordinates"):
            hmtx.metrics[glyph_name] = (target, 0)
            continue
        bounds = _glyph_bounds(glyph)
        if bounds is None:
            hmtx.metrics[glyph_name] = (target, 0)
            continue
        x_min, x_max = bounds
        ink_width = x_max - x_min
        scale = target / ink_width if ink_width > target and ink_width > 0 else 1.0
        source_center = (x_min + x_max) / 2
        target_center = target / 2
        # Mono fallback sources can be proportional; keep ink centered while clamping advance width.
        coords = glyph.coordinates
        for index in range(len(coords)):
            x, y = coords[index]
            coords[index] = (round((x - source_center) * scale + target_center), y)
        new_bounds = _glyph_bounds(glyph)
        hmtx.metrics[glyph_name] = (target, new_bounds[0] if new_bounds else 0)


def _subset_font_to_temp(
    source: Path,
    codepoints: list[int],
    target: Path,
    preserve_source_metadata: bool,
) -> None:
    options = subset.Options()
    dynamic_options = cast(SubsetOptionsOverrides, options)
    if preserve_source_metadata:
        options.hinting = True
        options.drop_tables += ["MATH", "vhea", "vmtx", "VORG"]
    else:
        options.hinting = False
        options.layout_features = []
        options.drop_tables += [
            "BASE",
            "cvt ",
            "GDEF",
            "GPOS",
            "GSUB",
            "fpgm",
            "gasp",
            "hdmx",
            "JSTF",
            "MATH",
            "prep",
            "VDMX",
            "vhea",
            "vmtx",
            "VORG",
        ]
    dynamic_options.name_IDs = ["*"]
    options.name_legacy = True
    dynamic_options.name_languages = ["*"]
    options.notdef_outline = True
    options.recalc_bounds = True
    options.recalc_timestamp = False
    options.glyph_names = True
    dynamic_options.canonical_order = True
    font = subset.load_font(str(source), options)
    try:
        sub = subset.Subsetter(options)
        sub.populate(unicodes=codepoints)
        sub.subset(font)
        _convert_cff_to_truetype(font)
        _normalize_units_per_em(font)
        _drop_unmergeable_tables(font)
        subset.save_font(font, str(target), options)
    finally:
        font.close()


def _normalize_units_per_em(font: TTFont) -> None:
    if cast(HeadTable, font["head"]).unitsPerEm != MERGE_UNITS_PER_EM:
        scale_upem(font, MERGE_UNITS_PER_EM)


def _drop_unmergeable_tables(font: TTFont) -> None:
    for tag in ("MATH", "vhea", "vmtx", "VORG"):
        if tag in font:
            del font[tag]


def _new_maxp_table() -> MaxpTable:
    maxp = cast(MaxpTable, newTable("maxp"))
    maxp.tableVersion = 0x00010000
    maxp.maxZones = 2
    maxp.maxTwilightPoints = 0
    maxp.maxStorage = 0
    maxp.maxFunctionDefs = 0
    maxp.maxInstructionDefs = 0
    maxp.maxStackElements = 0
    maxp.maxSizeOfInstructions = 0
    maxp.maxComponentElements = 0
    maxp.maxComponentDepth = 0
    return maxp


def _convert_cff_to_truetype(font: TTFont) -> None:
    if "CFF " not in font and "CFF2" not in font:
        return
    # fontTools.merge cannot combine CFF outlines into the TrueType output we write.
    glyph_set = font.getGlyphSet()
    glyph_order = cast(list[str], font.getGlyphOrder())
    glyf = cast(GlyfTable, newTable("glyf"))
    glyf.glyphs = {}
    glyf.glyphOrder = list(glyph_order)
    max_err = max(1.0, cast(HeadTable, font["head"]).unitsPerEm / 1000)
    for glyph_name in glyph_order:
        pen = TTGlyphPen(cast(dict[str, object], glyph_set))
        glyph_set[glyph_name].draw(Cu2QuPen(pen, max_err, reverse_direction=True))
        glyph = pen.glyph()
        glyf.glyphs[glyph_name] = glyph
    font["glyf"] = glyf
    merged_glyf = cast(GlyfTable, font["glyf"])
    for glyph_name in glyph_order:
        glyph = merged_glyf[glyph_name]
        glyph.recalcBounds(merged_glyf)
        if not hasattr(glyph, "xMin"):
            glyph.xMin = glyph.yMin = glyph.xMax = glyph.yMax = 0
    font["loca"] = newTable("loca")
    for tag in ("CFF ", "CFF2", "VORG"):
        if tag in font:
            del font[tag]
    font.sfntVersion = "\x00\x01\x00\x00"
    cast(HeadTable, font["head"]).glyphDataFormat = 0
    font["maxp"] = _new_maxp_table()
    cast(MaxpTable, font["maxp"]).recalc(font)


STYLE_NAME: dict[FontStyle, str] = {
    "regular": "Regular",
    "bold": "Bold",
    "italic": "Italic",
    "bolditalic": "Bold Italic",
    "full": "Regular",
}


STYLE_POSTSCRIPT_SUFFIX: dict[FontStyle, str] = {
    "regular": "Regular",
    "bold": "Bold",
    "italic": "Italic",
    "bolditalic": "BoldItalic",
    "full": "Regular",
}


def _normalize_font_names(font: TTFont, output: Path, style: FontStyle) -> None:
    stem = output.stem.removeprefix("uninoto_")
    family_name = "Uninoto " + " ".join(
        part.capitalize() for part in stem.split("_") if part
    )
    ps_base = "".join(ch for ch in family_name if ch.isalnum())
    subfamily_name = STYLE_NAME[style]
    ps_suffix = STYLE_POSTSCRIPT_SUFFIX[style]
    names = {
        0: "Copyright (c) The Uninoto Project Authors.",
        1: family_name,
        2: subfamily_name,
        3: f"1.000;UNIN;{ps_base}-{ps_suffix}",
        4: f"{family_name} {subfamily_name}",
        5: "Version 1.000",
        6: f"{ps_base}-{ps_suffix}",
        7: "Uninoto is a generated font family name.",
        8: "DreamPast",
        9: "DreamPast",
        10: "Generated from Noto and compatible fallback font sources.",
        11: "https://github.com/notofonts",
        13: "Source fonts retain their original licenses. See the uninoto repository LICENSE file for the source font license inventory.",
        14: "https://github.com/DreamPast/uninoto/blob/main/LICENSE",
    }
    name_table = cast(NameTable, font["name"])
    for name_id in list(names):
        name_table.removeNames(nameID=name_id)
    for name_id, value in names.items():
        name_table.setName(value, name_id, 3, 1, 0x409)
        name_table.setName(value, name_id, 1, 0, 0)


def _family_for_output(output: Path) -> FontFamily | None:
    stem = output.stem
    for family in FONT_FAMILIES:
        prefix = f"uninoto_{family}"
        if stem == prefix or stem.startswith(f"{prefix}_"):
            return family
        if stem.startswith(prefix) and stem[len(prefix) :].isdecimal():
            return family
    return None


def _normalize_vertical_metrics(font: TTFont, output: Path) -> None:
    if "hhea" in font:
        hhea = cast(HheaTable, font["hhea"])
        hhea.ascent = NOTO_ASCENT
        hhea.descent = NOTO_DESCENT
        hhea.lineGap = NOTO_LINE_GAP
    if "OS/2" not in font:
        return
    os2 = cast(Os2Table, font["OS/2"])
    win_ascent, win_descent = WIN_METRICS_BY_FAMILY[_family_for_output(output)]
    os2.sTypoAscender = NOTO_ASCENT
    os2.sTypoDescender = NOTO_DESCENT
    os2.sTypoLineGap = NOTO_LINE_GAP
    os2.usWinAscent = win_ascent
    os2.usWinDescent = win_descent
    os2.fsSelection |= USE_TYPO_METRICS


def _notdef_outline_glyph(advance_width: int) -> Glyph:
    width = max(advance_width, NOTDEF_DEFAULT_WIDTH)
    margin = max(50, round(width * 0.1))
    stroke = max(45, round(width * 0.08))
    x_min = margin
    x_max = width - margin
    y_min = NOTDEF_Y_MIN
    y_max = NOTDEF_Y_MAX
    inner_x_min = min(x_min + stroke, x_max)
    inner_x_max = max(x_max - stroke, x_min)
    inner_y_min = min(y_min + stroke, y_max)
    inner_y_max = max(y_max - stroke, y_min)
    pen = TTGlyphPen(None)
    pen.moveTo((x_min, y_min))
    pen.lineTo((x_min, y_max))
    pen.lineTo((x_max, y_max))
    pen.lineTo((x_max, y_min))
    pen.closePath()
    pen.moveTo((inner_x_min, inner_y_min))
    pen.lineTo((inner_x_max, inner_y_min))
    pen.lineTo((inner_x_max, inner_y_max))
    pen.lineTo((inner_x_min, inner_y_max))
    pen.closePath()
    return pen.glyph()


def _ensure_notdef_outline(font: TTFont) -> None:
    if "glyf" not in font or "hmtx" not in font:
        return
    glyph_order = cast(list[str], font.getGlyphOrder())
    if ".notdef" not in glyph_order:
        glyph_order.insert(0, ".notdef")
        font.setGlyphOrder(glyph_order)
    elif glyph_order[0] != ".notdef":
        glyph_order = [".notdef", *(name for name in glyph_order if name != ".notdef")]
        font.setGlyphOrder(glyph_order)
    glyf = cast(GlyfTable, font["glyf"])
    hmtx = cast(HmtxTable, font["hmtx"])
    advance_width, _lsb = hmtx.metrics.get(".notdef", (NOTDEF_DEFAULT_WIDTH, 0))
    glyph = _notdef_outline_glyph(advance_width)
    glyf.glyphs[".notdef"] = glyph
    glyf.glyphOrder = list(cast(list[str], font.getGlyphOrder()))
    glyph.recalcBounds(glyf)
    hmtx.metrics[".notdef"] = (max(advance_width, NOTDEF_DEFAULT_WIDTH), glyph.xMin)


def _ensure_cmap_subtable(font: TTFont, format_: int) -> CmapSubtable:
    cmap_table = cast(CmapTable, font["cmap"])
    for table in cmap_table.tables:
        if getattr(table, "format", None) == format_:
            return table
    table = FontToolsCmapSubtable.newSubtable(format_)
    if format_ == 12:
        table.platformID = 3
        table.platEncID = 10
    else:
        table.platformID = 3
        table.platEncID = 1
    table.language = 0
    table.cmap = {}
    cmap_table.tables.append(table)
    return table


def _last_resort_component_closure(source_font: TTFont, roots: set[str]) -> set[str]:
    if "glyf" not in source_font:
        return set(roots)
    glyf = cast(GlyfTable, source_font["glyf"])
    needed = set(roots)
    stack = list(roots)
    while stack:
        glyph_name = stack.pop()
        if glyph_name not in glyf.glyphs:
            continue
        glyph = glyf[glyph_name]
        if not glyph.isComposite():
            continue
        for component in glyph.components:
            component_name = component.glyphName
            if component_name not in needed:
                needed.add(component_name)
                stack.append(component_name)
    return needed


def _copy_last_resort_glyphs(
    source_font: TTFont, target_font: TTFont, glyph_names: set[str]
) -> int:
    if "glyf" not in source_font or "hmtx" not in source_font:
        return 0
    if "glyf" not in target_font or "hmtx" not in target_font:
        return 0
    source_glyf = cast(GlyfTable, source_font["glyf"])
    source_hmtx = cast(HmtxTable, source_font["hmtx"])
    target_glyf = cast(GlyfTable, target_font["glyf"])
    target_hmtx = cast(HmtxTable, target_font["hmtx"])
    target_order = cast(list[str], target_font.getGlyphOrder())
    target_names = set(target_order)
    copied = 0
    for glyph_name in sorted(_last_resort_component_closure(source_font, glyph_names)):
        if glyph_name not in source_glyf.glyphs:
            continue
        if glyph_name not in target_names:
            target_order.append(glyph_name)
            target_names.add(glyph_name)
        target_glyf.glyphs[glyph_name] = copy.deepcopy(source_glyf.glyphs[glyph_name])
        if glyph_name in source_hmtx.metrics:
            target_hmtx.metrics[glyph_name] = source_hmtx.metrics[glyph_name]
        else:
            target_hmtx.metrics[glyph_name] = (NOTDEF_DEFAULT_WIDTH, 0)
        copied += 1
    target_font.setGlyphOrder(target_order)
    target_glyf.glyphOrder = list(target_order)
    return copied


def is_last_resort_fallback_codepoint(codepoint: int, category: str) -> bool:
    try:
        if chr(codepoint).isspace():
            return True
    except ValueError:
        return False
    return category in LAST_RESORT_FALLBACK_CATEGORIES


def last_resort_fallback_codepoints(unicode_data: Path) -> set[int]:
    codepoints: set[int] = set()
    ranges = read_unicode_data_ranges(unicode_data)
    for codepoint in range(0x110000):
        category = category_from_ranges(codepoint, ranges) or "Cn"
        if not is_last_resort_fallback_codepoint(codepoint, category):
            continue
        codepoints.add(codepoint)
    return codepoints


def add_last_resort_fallbacks_to_font(
    path: Path, source: Path, codepoints: set[int], replace_cmap: bool = False
) -> int:
    if not source.exists():
        raise FileNotFoundError(f"missing Unicode Last Resort source: {source}")
    source_font = TTFont(source)
    font = TTFont(path)
    try:
        if replace_cmap and "cmap" in font:
            cast(CmapTable, font["cmap"]).tables = []
        source_cmap = source_font.getBestCmap() or {}
        mapping = {
            codepoint: glyph_name
            for codepoint, glyph_name in source_cmap.items()
            if codepoint in codepoints
        }
        copied = _copy_last_resort_glyphs(source_font, font, set(mapping.values()))
        if mapping:
            cmap12 = _ensure_cmap_subtable(font, 12)
            cmap12.cmap.update(mapping)
            cmap4 = _ensure_cmap_subtable(font, 4)
            cmap4.cmap.update(
                {
                    codepoint: glyph_name
                    for codepoint, glyph_name in mapping.items()
                    if codepoint <= 0xFFFF
                }
            )
        if "maxp" in font:
            cast(MaxpTable, font["maxp"]).recalc(font)
        if mapping or copied:
            font.save(path)
        return len(mapping)
    finally:
        font.close()
        source_font.close()


def add_last_resort_fallbacks_to_output(
    output: Path, source: Path, codepoints: set[int], replace_cmap: bool = False
) -> None:
    total = add_last_resort_fallbacks_to_font(
        output, source, codepoints, replace_cmap=replace_cmap
    )
    if codepoints:
        print(f"last resort fallback glyphs: added {total} mappings to {output.name}")


def _composite_component_closure(font: TTFont, roots: set[str]) -> set[str]:
    if "glyf" not in font:
        return set(roots)
    glyf = cast(GlyfTable, font["glyf"])
    needed = set(roots)
    stack = list(roots)
    while stack:
        glyph_name = stack.pop()
        if glyph_name not in glyf.glyphs:
            continue
        glyph = glyf[glyph_name]
        if not glyph.isComposite():
            continue
        for component in glyph.components:
            component_name = component.glyphName
            if component_name not in needed:
                needed.add(component_name)
                stack.append(component_name)
    return needed


def _all_cmap_glyphs(font: TTFont) -> set[str]:
    if "cmap" not in font:
        return set()
    glyphs: set[str] = set()
    for table in cast(CmapTable, font["cmap"]).tables:
        glyphs.update(table.cmap.values())
    return glyphs


def _layout_glyphs(font: TTFont) -> set[str]:
    glyphs: set[str] = set()
    for tag in LAYOUT_GLYPH_REFERENCE_TABLES:
        if tag not in font:
            continue
        table = cast(Any, font[tag])
        get_all_glyphs = getattr(table.table, "getAllGlyphs", None)
        if get_all_glyphs:
            glyphs.update(get_all_glyphs())
    return glyphs


def _drop_cmap_entries_for_missing_glyphs(font: TTFont, glyph_names: set[str]) -> None:
    if "cmap" not in font:
        return
    cmap_table = cast(CmapTable, font["cmap"])
    cmap_table.tables = [
        table for table in cmap_table.tables if getattr(table, "format", None) != 14
    ]
    for table in cmap_table.tables:
        table.cmap = {
            codepoint: glyph_name
            for codepoint, glyph_name in table.cmap.items()
            if glyph_name in glyph_names
        }


def _prune_unencoded_glyphs(font: TTFont, keep_layout_tables: bool) -> int:
    glyph_order = cast(list[str], font.getGlyphOrder())
    encoded_glyphs = _all_cmap_glyphs(font)
    placeholders = set(glyph_order) & PLACEHOLDER_GLYPHS
    layout_glyphs = _layout_glyphs(font) if keep_layout_tables else set()
    needed = _composite_component_closure(
        font, encoded_glyphs | layout_glyphs | placeholders
    )
    removable = [glyph_name for glyph_name in glyph_order if glyph_name not in needed]
    if not removable:
        return 0
    if not keep_layout_tables:
        for tag in LAYOUT_GLYPH_REFERENCE_TABLES:
            if tag in font:
                del font[tag]
    keep = set(glyph_order) - set(removable)
    new_order = [glyph_name for glyph_name in glyph_order if glyph_name in keep]
    font.setGlyphOrder(new_order)
    _drop_cmap_entries_for_missing_glyphs(font, set(new_order))
    if "glyf" in font:
        glyf = cast(GlyfTable, font["glyf"])
        glyf.glyphs = {
            glyph_name: glyf.glyphs[glyph_name]
            for glyph_name in new_order
            if glyph_name in glyf.glyphs
        }
        glyf.glyphOrder = list(new_order)
    for tag in ("hmtx", "vmtx"):
        if tag in font:
            metrics_table = cast(HmtxTable, font[tag])
            metrics = metrics_table.metrics
            metrics_table.metrics = {
                glyph_name: metrics[glyph_name]
                for glyph_name in new_order
                if glyph_name in metrics
            }
    if "maxp" in font:
        cast(MaxpTable, font["maxp"]).recalc(font)
    return len(removable)


def _write_merged_font(
    temp_subsets: list[Path],
    output: Path,
    normalize_mono_width: bool,
    style: FontStyle,
    preserve_source_metadata: bool,
) -> tuple[int, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    font = (
        TTFont(str(temp_subsets[0]))
        if len(temp_subsets) == 1
        else Merger().merge([str(path) for path in temp_subsets])
    )
    try:
        if normalize_mono_width:
            _normalize_mono_widths(font)
        _normalize_font_names(font, output, style)
        if not preserve_source_metadata:
            _normalize_vertical_metrics(font, output)
        _ensure_notdef_outline(font)
        if "OS/2" in font and not preserve_source_metadata:
            cast(Os2Table, font["OS/2"]).usMaxContext = 0
        pruned = 0
        if not preserve_source_metadata:
            pruned = _prune_unencoded_glyphs(font, keep_layout_tables=False)
        if preserve_source_metadata:
            _drop_cmap_entries_for_missing_glyphs(
                font, set(cast(list[str], font.getGlyphOrder()))
            )
        glyphs = len(font.getGlyphOrder())
        if glyphs > TTF_GLYPH_LIMIT:
            raise ValueError(
                f"{output.name} wrote {glyphs} glyphs, limit {TTF_GLYPH_LIMIT}"
            )
        font.save(output)
        return glyphs, pruned
    finally:
        font.close()


def _merge_selected_codepoints_once(
    label: str,
    output_name: str,
    selected: list[SelectedCodepoint],
    output_root: Path,
    normalize_mono_width: bool,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool,
    allow_stripped_fallback: bool,
) -> WriteResult | None:
    estimated = len(selected) + 1
    if estimated > TTF_GLYPH_LIMIT:
        raise ValueError(
            f"{label} cannot fit into one TTF: estimated {estimated} glyph slots, limit {TTF_GLYPH_LIMIT}"
        )
    output = output_root / output_name
    codepoints_by_font: dict[Path, list[int]] = {}
    for item in selected:
        codepoints_by_font.setdefault(item.font.path, []).append(item.codepoint)
    if not codepoints_by_font:
        print(f"skip {label}: no cmap entries")
        return None
    with tempfile.TemporaryDirectory(prefix="uninoto-") as temp:
        temp_root = Path(temp)

        def build_subsets(preserve_metadata: bool) -> list[Path]:
            suffix = "preserve" if preserve_metadata else "stripped"
            temp_subsets: list[Path] = []
            for index, (font_path, codepoints) in enumerate(codepoints_by_font.items()):
                unique = sorted(set(codepoints))
                target = temp_root / f"subset-{suffix}-{index}.ttf"
                _subset_font_to_temp(font_path, unique, target, preserve_metadata)
                temp_subsets.append(target)
            return temp_subsets

        try:
            glyphs, pruned = _write_merged_font(
                build_subsets(preserve_source_metadata),
                output,
                normalize_mono_width,
                style,
                preserve_source_metadata,
            )
        except Exception as exc:
            if not preserve_source_metadata or not allow_stripped_fallback:
                raise
            print(
                f"{label} could not preserve source metadata; retrying stripped output ({exc})"
            )
            glyphs, pruned = _write_merged_font(
                build_subsets(False),
                output,
                normalize_mono_width,
                style,
                False,
            )
    actual = read_font_codepoints(output, codepoint_filter)
    print(
        f"wrote {output} ({glyphs} glyphs, {len(actual)}/{len(selected)} codepoints, {len(codepoints_by_font)} subsets, pruned={pruned})"
    )
    return WriteResult(
        glyphs=glyphs,
        pruned=pruned,
        preserved_metadata=preserve_source_metadata and pruned == 0,
    )


def merge_selected_codepoints(
    label: str,
    output_name: str,
    selected: list[SelectedCodepoint],
    output_root: Path,
    normalize_mono_width: bool,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool | None = None,
) -> None:
    preserve_metadata = (
        False
        if preserve_source_metadata is None
        else preserve_source_metadata and style != "full"
    )
    _merge_selected_codepoints_once(
        label,
        output_name,
        selected,
        output_root,
        normalize_mono_width,
        codepoint_filter,
        style,
        preserve_metadata,
        True,
    )


def merge_selected_codepoints_with_split(
    label: str,
    output_names: list[str],
    selected: list[SelectedCodepoint],
    output_root: Path,
    normalize_mono_width: bool,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
    output_name_builder: OutputNameBuilder | None = None,
    cleanup_stale: bool = True,
) -> int:
    if not selected:
        print(f"skip {label}: no cmap entries")
        return 0

    preserve_metadata = preserve_source_metadata and style != "full"
    retry_splitter = (
        _split_selected_for_retry
        if preserve_metadata
        else _split_selected_for_capacity_retry
    )
    written = 0
    written_names: list[str] = []

    def write_chunk(
        chunk: list[SelectedCodepoint], failure_reason: str | None = None
    ) -> None:
        nonlocal written
        if written >= len(output_names):
            raise ValueError(
                f"{label} requires more than {len(output_names)} split outputs"
            )
        chunk_label = label if written == 0 else f"{label}-{written + 1}"
        must_split = len(chunk) + 1 > TTF_GLYPH_LIMIT
        if (
            preserve_metadata
            and not must_split
            and len(chunk) > PRESERVE_METADATA_CODEPOINT_LIMIT
        ):
            split = _split_selected_for_retry(chunk)
            if split is not None:
                write_chunk(split[0], "preserve metadata chunk limit")
                write_chunk(split[1], "preserve metadata chunk limit")
                return
        name_builder_snapshot = (
            output_name_builder.snapshot()
            if isinstance(output_name_builder, SplitOutputNameBuilder)
            else None
        )
        output_name = (
            output_name_builder(written, chunk)
            if output_name_builder
            else output_names[written]
        )
        if not must_split and preserve_metadata:
            try:
                _merge_selected_codepoints_once(
                    chunk_label,
                    output_name,
                    chunk,
                    output_root,
                    normalize_mono_width,
                    codepoint_filter,
                    style,
                    True,
                    False,
                )
                written += 1
                written_names.append(output_name)
                return
            except Exception as exc:
                failure_reason = str(exc)
                must_split = _is_capacity_error(exc)
                if not must_split:
                    split = _split_selected_by_source(chunk)
                    if split is not None:
                        if (
                            isinstance(output_name_builder, SplitOutputNameBuilder)
                            and name_builder_snapshot is not None
                        ):
                            output_name_builder.restore(name_builder_snapshot)
                        print(
                            f"{chunk_label} layout metadata merge failed; splitting source groups ({failure_reason})"
                        )
                        write_chunk(split[0], failure_reason)
                        write_chunk(split[1], failure_reason)
                        return
        if must_split:
            split = retry_splitter(chunk)
            if split is not None:
                if (
                    isinstance(output_name_builder, SplitOutputNameBuilder)
                    and name_builder_snapshot is not None
                ):
                    output_name_builder.restore(name_builder_snapshot)
                write_chunk(split[0], failure_reason)
                write_chunk(split[1], failure_reason)
                return
        if len(chunk) <= 1 or not must_split:
            if preserve_metadata:
                print(
                    f"{chunk_label} could not preserve source metadata; retrying stripped output ({failure_reason})"
                )
            try:
                _merge_selected_codepoints_once(
                    chunk_label,
                    output_name,
                    chunk,
                    output_root,
                    normalize_mono_width,
                    codepoint_filter,
                    style,
                    False,
                    False,
                )
                written += 1
                written_names.append(output_name)
            except Exception as exc:
                if len(chunk) <= 1 or not _is_capacity_error(exc):
                    raise
                split = retry_splitter(chunk)
                if split is None:
                    raise
                if (
                    isinstance(output_name_builder, SplitOutputNameBuilder)
                    and name_builder_snapshot is not None
                ):
                    output_name_builder.restore(name_builder_snapshot)
                write_chunk(split[0], str(exc))
                write_chunk(split[1], str(exc))
            return
        raise ValueError(f"{chunk_label} cannot be split further ({failure_reason})")

    write_chunk(selected)
    if cleanup_stale:
        keep = set(written_names)
        for stale_name in output_names:
            if stale_name not in keep:
                (output_root / stale_name).unlink(missing_ok=True)
    return written


def merge_category(
    category: Category,
    family: FontFamily,
    fonts: list[FontInfo],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
) -> None:
    selected = selected_codepoints_for_category(category, fonts, family, style)
    return merge_selected_codepoints(
        f"{family}-{category}",
        output_name_for(family, category),
        selected,
        output_root,
        family == "mono",
        codepoint_filter,
        style,
        preserve_source_metadata,
    )


def merge_extra(
    fonts: list[FontInfo],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
) -> None:
    sans = {
        item.codepoint: item
        for item in selected_output_codepoints(fonts, "sans", style)
    }
    serif = {
        item.codepoint: item
        for item in selected_output_codepoints(fonts, "serif", style)
    }
    neutral = {
        item.codepoint: item
        for item in selected_output_codepoints(fonts, "extra", style)
    }
    selected_by_codepoint = {
        cp: item for cp, item in neutral.items() if cp not in sans or cp not in serif
    }
    selected_by_codepoint.update(
        {cp: item for cp, item in sans.items() if cp not in serif and cp not in neutral}
    )
    selected_by_codepoint.update(
        {cp: item for cp, item in serif.items() if cp not in sans and cp not in neutral}
    )
    selected = [selected_by_codepoint[cp] for cp in sorted(selected_by_codepoint)]
    only_sans = len([cp for cp in sans if cp not in serif])
    only_serif = len([cp for cp in serif if cp not in sans])
    neutral_only = len([cp for cp in neutral if cp not in sans or cp not in serif])
    print(
        f"sans/serif coverage check: sans={len(sans)}, serif={len(serif)}, "
        f"neutral-extra={neutral_only}, only-sans={only_sans}, only-serif={only_serif}"
    )
    remove_extra_output_fonts(output_root)
    preserve_metadata = preserve_source_metadata and style != "full"
    should_try_single = len(selected) <= EXTRA_BUCKET_CODEPOINT_LIMIT and not (
        preserve_metadata
        and (
            len(selected) > PRESERVE_METADATA_CODEPOINT_LIMIT
            or (
                len(selected) > 1000 and _split_selected_by_source(selected) is not None
            )
        )
    )
    if should_try_single:
        try:
            _merge_selected_codepoints_once(
                "extra",
                EXTRA_OUTPUT_NAMES[0],
                selected,
                output_root,
                False,
                codepoint_filter,
                style,
                preserve_metadata,
                False,
            )
            for stale_name in EXTRA_OUTPUT_NAMES[1:]:
                (output_root / stale_name).unlink(missing_ok=True)
            return
        except Exception as exc:
            if style == "full":
                raise
            if _is_capacity_error(exc):
                print(
                    f"extra does not fit with source metadata; splitting outputs ({exc})"
                )
            elif preserve_metadata:
                print(
                    f"extra could not preserve source metadata in one output; splitting source groups ({exc})"
                )
            else:
                raise
    merge_selected_codepoints_with_split(
        "extra",
        split_output_names("extra"),
        selected,
        output_root,
        False,
        codepoint_filter,
        style,
        preserve_source_metadata,
    )


def merge_last_resort(
    output_root: Path,
    style: FontStyle,
    last_resort_source: Path | None,
    last_resort_codepoints: set[int] | None,
) -> None:
    remove_last_resort_output_fonts(output_root)
    if style != "full":
        print(f"skip last_resort: only full style writes Last Resort prompts")
        return
    if last_resort_source is None:
        raise ValueError("last_resort source path was not provided")
    output = output_root / LAST_RESORT_OUTPUT_NAMES[0]
    output_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(last_resort_source, output)
    add_last_resort_fallbacks_to_output(
        output, last_resort_source, last_resort_codepoints or set(), replace_cmap=True
    )


def parse_age_ranges(text: str) -> list[AgeRange]:
    ranges: list[AgeRange] = []
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = [part.strip() for part in line.split(";")]
        if len(parts) < 2:
            continue
        start_text, _, end_text = parts[0].partition("..")
        start = int(start_text, 16)
        end = int(end_text, 16) if end_text else start
        ranges.append(AgeRange(start, end, parts[1]))
    return ranges


def parse_unicode_data_ranges(text: str) -> list[GeneralCategoryRange]:
    ranges: list[GeneralCategoryRange] = []
    pending: tuple[int, str] | None = None
    for raw_line in text.splitlines():
        if not raw_line:
            continue
        fields = raw_line.split(";")
        if len(fields) < 3:
            continue
        codepoint = int(fields[0], 16)
        name = fields[1]
        category = fields[2]
        # UnicodeData compresses large contiguous blocks as First/Last sentinels.
        if name.endswith(", First>"):
            pending = (codepoint, category)
        elif name.endswith(", Last>") and pending:
            ranges.append(GeneralCategoryRange(pending[0], codepoint, pending[1]))
            pending = None
        else:
            ranges.append(GeneralCategoryRange(codepoint, codepoint, category))
    return sorted(ranges, key=lambda item: item.start)


def read_age_ranges(path: Path) -> list[AgeRange]:
    return parse_age_ranges(path.read_text(encoding="utf-8")) if path.exists() else []


def read_unicode_data_ranges(path: Path) -> list[GeneralCategoryRange]:
    return (
        parse_unicode_data_ranges(path.read_text(encoding="utf-8"))
        if path.exists()
        else []
    )


def project_mergeable_codepoint_filter(unicode_data: Path) -> CodepointFilter:
    ranges = read_unicode_data_ranges(unicode_data)
    if not ranges:

        def fallback_filter(codepoint: int) -> bool:
            return is_visible_codepoint(codepoint, True)

        return fallback_filter

    def codepoint_filter(codepoint: int) -> bool:
        category = category_from_ranges(codepoint, ranges)
        if category is None or category in INVISIBLE_GENERAL_CATEGORIES:
            return False
        return True

    return codepoint_filter


def unicode_version(codepoint: int, ranges: list[AgeRange]) -> str:
    for range_ in ranges:
        if range_.start <= codepoint <= range_.end:
            return range_.version
    return "unknown"


def category_from_ranges(
    codepoint: int, ranges: list[GeneralCategoryRange]
) -> str | None:
    low = 0
    high = len(ranges) - 1
    while low <= high:
        mid = (low + high) // 2
        range_ = ranges[mid]
        if codepoint < range_.start:
            high = mid - 1
        elif range_.end < codepoint:
            low = mid + 1
        else:
            return range_.category
    return None


def category_for_report(codepoint: int, ranges: list[GeneralCategoryRange]) -> str:
    return category_from_ranges(codepoint, ranges) or general_category(codepoint)


def is_visible_report_codepoint(
    codepoint: int, category: str, include_marks: bool
) -> bool:
    if category in {"Cc", "Cf", "Cs", "Co", "Cn"}:
        return False
    if not include_marks and category.startswith("M"):
        return False
    return True


def report_codepoint_filter(
    category_ranges: list[GeneralCategoryRange], include_marks: bool
) -> CodepointFilter:
    def codepoint_filter(codepoint: int) -> bool:
        category = category_for_report(codepoint, category_ranges)
        return is_visible_report_codepoint(codepoint, category, include_marks)

    return codepoint_filter


def merged_coverage_fonts(output_root: Path, family: FontFamily) -> list[Path]:
    family_names = family_output_names(family)
    names = set(
        [*family_names, *extra_output_names()]
        if family in {"sans", "serif"}
        else family_names
    )
    return [file for file in list_font_files(output_root) if file.name in names]


def collect_merged_coverage(
    font_paths: list[Path], codepoint_filter: CodepointFilter
) -> set[int]:
    covered: set[int] = set()
    for path in font_paths:
        covered.update(read_font_codepoints(path, codepoint_filter))
    return covered


def collect_report_coverage(
    font_paths: list[Path],
    codepoint_filter: CodepointFilter,
    extra_codepoints: set[int] | None = None,
) -> set[int]:
    if extra_codepoints is None:
        return collect_merged_coverage(font_paths, codepoint_filter)

    extra_names = set(extra_output_names())
    base_paths = [path for path in font_paths if path.name not in extra_names]
    extra_paths = [path for path in font_paths if path.name in extra_names]
    covered = collect_merged_coverage(base_paths, codepoint_filter)

    def extra_filter(codepoint: int) -> bool:
        return codepoint in extra_codepoints and codepoint_filter(codepoint)

    covered.update(collect_merged_coverage(extra_paths, extra_filter))
    return covered


def font_files_by_output_names(output_root: Path, names: set[str]) -> list[Path]:
    return [file for file in list_font_files(output_root) if file.name in names]


def check_sans_serif_fallback_coverage(
    output_root: Path,
    codepoint_filter: CodepointFilter,
    extra_codepoints: set[int],
) -> None:
    sans_names = {
        *family_output_names("sans"),
        *extra_output_names(),
    }
    serif_names = {
        *family_output_names("serif"),
        *extra_output_names(),
    }
    sans = collect_report_coverage(
        font_files_by_output_names(output_root, sans_names),
        codepoint_filter,
        extra_codepoints,
    )
    serif = collect_report_coverage(
        font_files_by_output_names(output_root, serif_names),
        codepoint_filter,
        extra_codepoints,
    )
    only_sans = [cp for cp in sans if cp not in serif]
    only_serif = [cp for cp in serif if cp not in sans]
    print(
        f"sans/serif fallback coverage check: sans={len(sans)}, serif={len(serif)}, only-sans={len(only_sans)}, only-serif={len(only_serif)}"
    )


def write_missing_visible_report_for_fonts(
    options: Options,
    label: str,
    font_paths: list[Path],
    missing_output: Path,
    missing_summary_output: Path | None,
    extra_codepoints: set[int] | None = None,
) -> None:
    age_ranges = read_age_ranges(options.derived_age)
    category_ranges = read_unicode_data_ranges(options.unicode_data)
    codepoint_filter = report_codepoint_filter(category_ranges, options.include_marks)
    covered = collect_report_coverage(font_paths, codepoint_filter, extra_codepoints)
    missing: list[int] = []
    ranges = (
        [(range_.start, range_.end) for range_ in age_ranges]
        if age_ranges
        else [(0, 0x10FFFF)]
    )
    for start, end in ranges:
        for cp in range(start, end + 1):
            category = category_for_report(cp, category_ranges)
            if (
                is_visible_report_codepoint(cp, category, options.include_marks)
                and cp not in covered
            ):
                missing.append(cp)
    missing_output.parent.mkdir(parents=True, exist_ok=True)
    with missing_output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv_lib.writer(fh)
        writer.writerow(["codepoint", "char", "general_category", "unicode_version"])
        for cp in missing:
            writer.writerow(
                [
                    cp_hex(cp),
                    chr(cp),
                    category_for_report(cp, category_ranges),
                    unicode_version(cp, age_ranges),
                ]
            )
    if missing_summary_output:
        summary: dict[str, int] = {}
        for cp in missing:
            start = cp & ~0xFF
            page = f"{cp_hex(start)}..{cp_hex(start + 0xFF)}"
            summary[page] = summary.get(page, 0) + 1
        missing_summary_output.parent.mkdir(parents=True, exist_ok=True)
        with missing_summary_output.open("w", encoding="utf-8", newline="") as fh:
            writer = csv_lib.writer(fh)
            writer.writerow(["range", "missing_count"])
            writer.writerows(summary.items())
    names = ", ".join(
        name for name in (output_font_name(path) for path in font_paths) if name
    )
    report_scope = "visible codepoints" if options.include_marks else "visible non-mark"
    print(f"{label} coverage fonts: {names}")
    print(f"{label} covered {report_scope}: {len(covered)}")
    print(f"wrote {missing_output} ({len(missing)} missing {report_scope})")


def selected_extra_report_codepoints(
    options: Options, codepoint_filter: CodepointFilter
) -> set[int]:
    style = options.styles[0]
    fonts = discover_fonts(options.input, codepoint_filter, style)
    sans = {item.codepoint for item in selected_output_codepoints(fonts, "sans", style)}
    serif = {
        item.codepoint for item in selected_output_codepoints(fonts, "serif", style)
    }
    neutral = {
        item.codepoint for item in selected_output_codepoints(fonts, "extra", style)
    }
    return {
        *{cp for cp in neutral if cp not in sans or cp not in serif},
        *{cp for cp in sans if cp not in serif and cp not in neutral},
        *{cp for cp in serif if cp not in sans and cp not in neutral},
    }


def write_missing_visible_report(options: Options, family: FontFamily) -> None:
    if family not in REPORT_FAMILIES:
        return
    category_ranges = read_unicode_data_ranges(options.unicode_data)
    codepoint_filter = report_codepoint_filter(category_ranges, options.include_marks)
    extra_codepoints = (
        selected_extra_report_codepoints(options, codepoint_filter)
        if family in {"sans", "serif"}
        else None
    )
    write_missing_visible_report_for_fonts(
        options,
        family,
        merged_coverage_fonts(options.output, family),
        report_path_for_family(options.missing_output, family),
        (
            report_path_for_family(options.missing_summary_output, family)
            if options.missing_summary_output
            else None
        ),
        extra_codepoints,
    )
    if family in {"sans", "serif"}:
        write_missing_visible_report_for_fonts(
            options,
            f"{family} without extra",
            family_output_fonts(options.output, family),
            report_path_with_suffix(options.missing_output, family, "without_extra"),
            (
                report_path_with_suffix(
                    options.missing_summary_output, family, "without_extra"
                )
                if options.missing_summary_output
                else None
            ),
        )


def family_output_fonts(output_root: Path, family: FontFamily) -> list[Path]:
    names = set(family_output_names(family))
    return [file for file in list_font_files(output_root) if file.name in names]


def report_path_with_suffix(output: Path, family: FontFamily, suffix: str) -> Path:
    report_path = report_path_for_family(output, family)
    return report_path.with_name(f"{report_path.stem}-{suffix}{report_path.suffix}")


def remove_extra_output_fonts(output_root: Path) -> None:
    for name in (
        *EXTRA_OUTPUT_NAMES,
        *LEGACY_EXTRA_OUTPUT_NAMES,
        *split_output_names("extra"),
    ):
        (output_root / name).unlink(missing_ok=True)


def extra_output_names() -> list[str]:
    return [EXTRA_OUTPUT_NAMES[0], *split_output_names("extra")]


def remove_last_resort_output_fonts(output_root: Path) -> None:
    for name in (*LAST_RESORT_OUTPUT_NAMES, *split_output_names("last_resort")):
        (output_root / name).unlink(missing_ok=True)


def last_resort_output_names() -> list[str]:
    return [LAST_RESORT_OUTPUT_NAMES[0], *split_output_names("last_resort")]


def remove_stale_extra_reports(options: Options) -> None:
    outputs = [report_path_for_family(options.missing_output, "extra")]
    for family in ("sans", "serif"):
        outputs.append(
            report_path_with_suffix(options.missing_output, family, "without_last")
        )
    if options.missing_summary_output:
        outputs.append(report_path_for_family(options.missing_summary_output, "extra"))
        for family in ("sans", "serif"):
            outputs.append(
                report_path_with_suffix(
                    options.missing_summary_output, family, "without_last"
                )
            )
    for output in outputs:
        output.unlink(missing_ok=True)


def remove_upper_output_fonts(output_root: Path, family: FontFamily) -> None:
    for name in upper_output_names(family):
        (output_root / name).unlink(missing_ok=True)


def remove_bmp_split_output_fonts(output_root: Path, family: FontFamily) -> None:
    for name in stale_bmp_split_output_names(family):
        (output_root / name).unlink(missing_ok=True)


def remove_split_output_fonts(output_root: Path, family: FontFamily) -> None:
    for name in split_output_names(family):
        (output_root / name).unlink(missing_ok=True)


def remove_legacy_split_output_fonts(output_root: Path, family: FontFamily) -> None:
    for name in legacy_split_output_names(family):
        (output_root / name).unlink(missing_ok=True)


def remove_family_output_fonts(output_root: Path, family: FontFamily) -> None:
    for name in family_output_names(family):
        (output_root / name).unlink(missing_ok=True)


def remove_family_merge_outputs(output_root: Path, family: FontFamily) -> None:
    if family == "extra":
        remove_extra_output_fonts(output_root)
        return
    if family == "last_resort":
        remove_last_resort_output_fonts(output_root)
        return
    remove_family_output_fonts(output_root, family)
    remove_upper_output_fonts(output_root, family)
    remove_bmp_split_output_fonts(output_root, family)
    remove_legacy_split_output_fonts(output_root, family)


def remove_family_reports(options: Options, family: FontFamily) -> None:
    if family == "extra":
        remove_stale_extra_reports(options)
        return
    if family == "last_resort":
        return
    if family not in REPORT_FAMILIES:
        return
    outputs = [report_path_for_family(options.missing_output, family)]
    if options.missing_summary_output:
        outputs.append(report_path_for_family(options.missing_summary_output, family))
    if family in {"sans", "serif"}:
        outputs.append(
            report_path_with_suffix(options.missing_output, family, "without_extra")
        )
        if options.missing_summary_output:
            outputs.append(
                report_path_with_suffix(
                    options.missing_summary_output, family, "without_extra"
                )
            )
    for output in outputs:
        output.unlink(missing_ok=True)


def bmp_output_names(family: FontFamily) -> list[str]:
    return [output_name_for(family, "bmp")]


def stale_bmp_split_output_names(family: FontFamily) -> list[str]:
    return [
        output_name_for(family, f"bmp{index}")
        for index in range(2, STALE_BMP_SPLIT_OUTPUT_LIMIT + 1)
    ]


def upper_output_names(family: FontFamily) -> list[str]:
    numbered = [
        output_name_for(family, f"upper{index}")
        for index in range(1, upper_output_count_limit() + 1)
    ]
    return [output_name_for(family, "upper"), *numbered]


def split_output_names(family: FontFamily) -> list[str]:
    return [
        output_name_for(family, str(index))
        for index in range(1, split_output_count_limit() + 1)
    ]


def legacy_split_output_names(family: FontFamily) -> list[str]:
    region = [
        output_name_for(family, region_name) for region_name in REGION_SPLIT_LABELS
    ]
    numbered_regions = [
        output_name_for(family, f"{region_name}{index}")
        for region_name in REGION_SPLIT_LABELS
        for index in range(2, split_output_count_limit() + 1)
    ]
    underscored_numeric = [
        f"uninoto_{family}_{index}.ttf"
        for index in range(1, split_output_count_limit() + 1)
    ]
    return [*underscored_numeric, *region, *numbered_regions]


def family_output_names(family: FontFamily) -> list[str]:
    return [*bmp_output_names(family), *split_output_names(family)]


def upper_output_count_limit() -> int:
    return MAX_RECOGNIZED_UPPER_OUTPUTS


def split_output_count_limit() -> int:
    return MAX_RECOGNIZED_SPLIT_OUTPUTS


def try_merge_combined_family_output(
    family: FontFamily,
    selected: list[SelectedCodepoint],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
) -> bool:
    preserve_metadata = preserve_source_metadata and style != "full"
    if preserve_metadata and len(selected) > PRESERVE_METADATA_CODEPOINT_LIMIT:
        print(
            f"{family}-combined exceeds preserve metadata chunk target; splitting outputs"
        )
        return False
    try:
        _merge_selected_codepoints_once(
            f"{family}-combined",
            output_name_for(family, "bmp"),
            selected,
            output_root,
            family == "mono",
            codepoint_filter,
            style,
            preserve_metadata,
            False,
        )
    except Exception as exc:
        if not _is_capacity_error(exc):
            if style == "full":
                raise
            if not preserve_metadata:
                raise
            print(
                f"{family}-combined could not preserve source metadata in one output; splitting outputs ({exc})"
            )
            return False
        print(f"{family}-combined does not fit in one TTF; splitting outputs ({exc})")
        return False
    remove_bmp_split_output_fonts(output_root, family)
    remove_upper_output_fonts(output_root, family)
    remove_legacy_split_output_fonts(output_root, family)
    remove_split_output_fonts(output_root, family)
    return True


def merge_family_outputs(
    family: FontFamily,
    fonts: list[FontInfo],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    last_resort_codepoints: set[int] | None = None,
    last_resort_source: Path | None = None,
    preserve_source_metadata: bool = False,
) -> None:
    remove_family_merge_outputs(output_root, family)
    if family == "extra":
        merge_extra(
            fonts,
            output_root,
            codepoint_filter,
            style,
            preserve_source_metadata,
        )
        return
    if family == "last_resort":
        merge_last_resort(
            output_root,
            style,
            last_resort_source,
            last_resort_codepoints,
        )
        return
    bmp = selected_codepoints_for_category("bmp", fonts, family, style)
    upper = selected_upper_codepoints(fonts, family, style)
    combined = sorted(
        [*bmp, *upper],
        key=lambda item: item.codepoint,
    )
    if try_merge_combined_family_output(
        family,
        combined,
        output_root,
        codepoint_filter,
        style,
        preserve_source_metadata,
    ):
        return
    merge_selected_codepoints_with_split(
        family,
        split_output_names(family),
        combined,
        output_root,
        family == "mono",
        codepoint_filter,
        style,
        preserve_source_metadata,
    )


def try_merge_upper_output(
    family: FontFamily,
    selected: list[SelectedCodepoint],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
) -> bool:
    preserve_metadata = preserve_source_metadata and style != "full"
    if preserve_metadata and len(selected) > PRESERVE_METADATA_CODEPOINT_LIMIT:
        print(
            f"{family}-upper exceeds preserve metadata chunk target; splitting outputs"
        )
        return False
    try:
        _merge_selected_codepoints_once(
            f"{family}-upper",
            output_name_for(family, "upper"),
            selected,
            output_root,
            family == "mono",
            codepoint_filter,
            style,
            preserve_metadata,
            False,
        )
    except Exception as exc:
        if not _is_capacity_error(exc):
            if style == "full":
                raise
            if not preserve_metadata:
                raise
            print(
                f"{family}-upper could not preserve source metadata in one output; splitting outputs ({exc})"
            )
            return False
        print(f"{family}-upper does not fit in one TTF; splitting outputs ({exc})")
        return False
    for name in upper_output_names(family)[1:]:
        (output_root / name).unlink(missing_ok=True)
    return True


def merge_upper_bucket_outputs(
    family: FontFamily,
    selected: list[SelectedCodepoint],
    output_root: Path,
    codepoint_filter: CodepointFilter,
    style: FontStyle,
    preserve_source_metadata: bool = False,
) -> None:
    (output_root / output_name_for(family, "upper")).unlink(missing_ok=True)
    numbered_names = upper_output_names(family)[1:]
    if style != "full":
        merge_selected_codepoints_with_split(
            f"{family}-upper",
            numbered_names,
            selected,
            output_root,
            family == "mono",
            codepoint_filter,
            style,
            preserve_source_metadata,
        )
        return
    buckets = [
        selected[index : index + UPPER_BUCKET_CODEPOINT_LIMIT]
        for index in range(0, len(selected), UPPER_BUCKET_CODEPOINT_LIMIT)
    ]
    limit = len(numbered_names)
    if len(buckets) > limit:
        raise ValueError(
            f"{family} upper codepoints require {len(buckets)} buckets, "
            f"but only {limit} output names are recognized"
        )
    for index, bucket in enumerate(buckets, start=1):
        merge_selected_codepoints(
            f"{family}-upper{index}",
            numbered_names[index - 1],
            bucket,
            output_root,
            family == "mono",
            codepoint_filter,
            style,
        )
    for stale_index in range(len(buckets) + 1, limit + 1):
        (output_root / numbered_names[stale_index - 1]).unlink(missing_ok=True)


def style_options_for(options: Options, style: FontStyle) -> Options:
    return Options(
        input=options.input,
        output=output_root_for_style(options.output, style),
        family=options.family,
        styles=(style,),
        missing_output=report_file_for_style(options.missing_output, style),
        missing_summary_output=(
            report_file_for_style(options.missing_summary_output, style)
            if options.missing_summary_output
            else None
        ),
        include_marks=options.include_marks,
        derived_age=options.derived_age,
        unicode_data=options.unicode_data,
    )


def write_style_reports(
    options: Options,
    families: list[FontFamily],
) -> None:
    report_families: list[FontFamily] = (
        ["sans", "serif"] if options.family == "extra" else families
    )
    for family in report_families:
        remove_family_reports(options, family)
        if family in REPORT_FAMILIES:
            write_missing_visible_report(options, family)
    if not options.family or options.family == "extra":
        category_ranges = read_unicode_data_ranges(options.unicode_data)
        codepoint_filter = report_codepoint_filter(
            category_ranges, options.include_marks
        )
        extra_codepoints = selected_extra_report_codepoints(options, codepoint_filter)
        check_sans_serif_fallback_coverage(
            options.output, codepoint_filter, extra_codepoints
        )


def parse_args() -> Options:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="fonts/noto")
    parser.add_argument("--output", default="fonts/merged")
    parser.add_argument("--family")
    parser.add_argument(
        "--style",
        default="regular",
        help="Font style to merge: regular, bold, italic, bolditalic, full, or all.",
    )
    parser.add_argument("--missing-output", default="fonts/reports/missing-visible.csv")
    parser.add_argument("--missing-summary-output")
    parser.add_argument("--include-marks", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--exclude-marks",
        action="store_true",
        help="Report visible non-mark codepoints instead of all visible codepoints.",
    )
    parser.add_argument("--derived-age", default="fonts/unicode/DerivedAge.txt")
    parser.add_argument("--unicode-data", default="fonts/unicode/UnicodeData.txt")
    args = parser.parse_args()
    if args.include_marks and args.exclude_marks:
        parser.error("--include-marks and --exclude-marks cannot be used together")
    styles = (
        FONT_STYLES
        if args.style == "all"
        else (parse_font_style(args.style, "--style"),)
    )
    return Options(
        input=Path(args.input),
        output=Path(args.output),
        family=parse_font_family(args.family, "--family") if args.family else None,
        styles=styles,
        missing_output=Path(args.missing_output),
        missing_summary_output=(
            Path(args.missing_summary_output) if args.missing_summary_output else None
        ),
        include_marks=not bool(args.exclude_marks),
        derived_age=Path(args.derived_age),
        unicode_data=Path(args.unicode_data),
    )


def main() -> None:
    options = parse_args()
    codepoint_filter = project_mergeable_codepoint_filter(options.unicode_data)
    last_resort_codepoints = last_resort_fallback_codepoints(options.unicode_data)
    last_resort_source = options.input / LAST_RESORT_SOURCE
    families: list[FontFamily] = (
        [options.family] if options.family is not None else list(FONT_FAMILIES)
    )
    for style in options.styles:
        style_options = style_options_for(options, style)
        fonts = discover_fonts(options.input, codepoint_filter, style)
        if not fonts:
            raise ValueError(f"no {style} fonts found below {options.input}")
        print(f"style {style}: discovered {len(fonts)} candidate fonts")
        remove_stale_extra_reports(style_options)
        for family in families:
            merge_family_outputs(
                family,
                fonts,
                style_options.output,
                codepoint_filter,
                style,
                last_resort_codepoints=last_resort_codepoints,
                last_resort_source=last_resort_source,
            )
        write_style_reports(style_options, families)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
