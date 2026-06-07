from __future__ import annotations

import argparse
import csv as csv_lib
import shutil
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast

from fontTools import subset
from fontTools.merge import Merger
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.ttLib.tables._g_l_y_f import Glyph

from .font_io import FontInfo, discover_fonts, list_font_files, read_font_codepoints
from .planes import (
    DEFAULT_CATEGORIES,
    FONT_FAMILIES,
    LAST_OUTPUT_NAMES,
    LEGACY_LAST_OUTPUT_NAMES,
    Category,
    FontFamily,
    all_output_names,
    codepoint_in_category,
    output_name_for,
    parse_font_family,
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
    unicode_plane_name,
)

UPPER_BUCKET_CODEPOINT_LIMIT = 60000
LAST_BUCKET_CODEPOINT_LIMIT = TTF_GLYPH_LIMIT - 1
PLANE_1_END = 0x1FFFF
REPORT_FAMILIES: tuple[FontFamily, ...] = ("sans", "serif", "mono")
MONO_HALF_WIDTH = 600
MONO_FULL_WIDTH = 1000
MERGE_UNITS_PER_EM = 1000
NOTO_ASCENT = 1069
NOTO_DESCENT = -293
NOTO_LINE_GAP = 0
WIN_METRICS_BY_FAMILY: dict[FontFamily | None, tuple[int, int]] = {
    "sans": (1124, 395),
    "serif": (1069, 389),
    "mono": (1229, 389),
    "last": (1124, 395),
    None: (1124, 395),
}
USE_TYPO_METRICS = 1 << 7
CodepointFilter = Callable[[int], bool]


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
    coverage_output: Path
    missing_output: Path
    missing_summary_output: Path | None
    include_marks: bool
    derived_age: Path
    unicode_data: Path


@dataclass(frozen=True)
class ProvenanceRecord:
    codepoint: int
    font_file: str
    source_font: str
    note: str = ""


@dataclass
class Segment:
    start: int
    end: int
    plane: str
    font_file: str
    source_font: str
    note: str


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


def relative_source(file_path: Path) -> str:
    return (
        file_path.relative_to(Path.cwd()).as_posix()
        if file_path.is_relative_to(Path.cwd())
        else file_path.as_posix()
    )


def output_font_name(file_path: Path) -> str | None:
    names = set(all_output_names())
    return file_path.name if file_path.name in names else None


def report_path_for_family(output: Path, family: FontFamily) -> Path:
    suffix = output.suffix or ".csv"
    return output.with_name(f"{family}-{output.stem}{suffix}")


def selected_codepoints_for_category(
    category: Category, fonts: list[FontInfo], family: FontFamily
) -> list[SelectedCodepoint]:
    selected: dict[int, FontInfo] = {}
    for info in ordered_fonts(category, fonts, family):
        for cp in info.codepoints:
            if codepoint_in_category(category, cp) and cp not in selected:
                selected[cp] = info
    return [SelectedCodepoint(cp, selected[cp]) for cp in sorted(selected)]


def selected_upper_codepoints(
    fonts: list[FontInfo], family: FontFamily
) -> list[SelectedCodepoint]:
    selected: dict[int, FontInfo] = {}
    for info in ordered_fonts("upper1", fonts, family):
        for cp in info.codepoints:
            if 0x10000 <= cp <= PLANE_1_END and cp not in selected:
                selected[cp] = info
    for info in ordered_fonts("upper2", fonts, family):
        for cp in info.codepoints:
            if cp > PLANE_1_END and cp not in selected:
                selected[cp] = info
    return [SelectedCodepoint(cp, selected[cp]) for cp in sorted(selected)]


def upper_buckets(
    fonts: list[FontInfo], family: FontFamily
) -> dict[Category, list[SelectedCodepoint]]:
    selected = selected_upper_codepoints(fonts, family)
    upper1 = selected[:UPPER_BUCKET_CODEPOINT_LIMIT]
    upper2 = selected[UPPER_BUCKET_CODEPOINT_LIMIT : UPPER_BUCKET_CODEPOINT_LIMIT * 2]
    overflow = len(selected) - len(upper1) - len(upper2)
    if overflow > 0:
        raise ValueError(
            f"upper codepoints require more than two buckets: {len(selected)} codepoints, "
            f"{UPPER_BUCKET_CODEPOINT_LIMIT * 2} capacity"
        )
    return {"upper1": upper1, "upper2": upper2}


def selected_output_codepoints(
    fonts: list[FontInfo], family: FontFamily
) -> list[SelectedCodepoint]:
    buckets = upper_buckets(fonts, family)
    return sorted(
        [
            *selected_codepoints_for_category("bmp", fonts, family),
            *buckets["upper1"],
            *buckets["upper2"],
        ],
        key=lambda item: item.codepoint,
    )


def target_mono_width(codepoint: int | None) -> int:
    if codepoint is None:
        return MONO_HALF_WIDTH
    category = general_category(codepoint)
    if category.startswith("M"):
        return 0
    if in_ranges(codepoint, CJK_RELATED_RANGES) or in_ranges(codepoint, EMOJI_RANGES):
        return MONO_FULL_WIDTH
    return MONO_HALF_WIDTH


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


def _subset_font_to_temp(source: Path, codepoints: list[int], target: Path) -> None:
    options = subset.Options()
    dynamic_options = cast(SubsetOptionsOverrides, options)
    options.hinting = False
    options.layout_features = []
    options.drop_tables += ["BASE", "GPOS", "GSUB", "MATH", "vhea", "vmtx", "VORG"]
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


def _normalize_font_names(font: TTFont, output: Path) -> None:
    stem = output.stem.removeprefix("uninoto_")
    family_name = "Uninoto " + " ".join(
        part.capitalize() for part in stem.split("_") if part
    )
    ps_base = "".join(ch for ch in family_name if ch.isalnum())
    names = {
        0: "Copyright (c) The Uninoto Project Authors.",
        1: family_name,
        2: "Regular",
        3: f"1.000;UNIN;{ps_base}-Regular",
        4: f"{family_name} Regular",
        5: "Version 1.000",
        6: f"{ps_base}-Regular",
        7: "Uninoto is a generated font family name.",
        8: "DreamPast",
        9: "DreamPast",
        10: "Generated from Noto and compatible fallback font sources.",
        11: "https://github.com/notofonts",
        13: "Source fonts retain their original licenses. Noto fonts are licensed under the SIL Open Font License, Version 1.1.",
        14: "https://scripts.sil.org/OFL",
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
        if stem == f"uninoto_{family}" or stem.startswith(f"uninoto_{family}_"):
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


def _write_merged_font(
    temp_subsets: list[Path], output: Path, normalize_mono_width: bool
) -> int:
    output.parent.mkdir(parents=True, exist_ok=True)
    font = (
        TTFont(str(temp_subsets[0]))
        if len(temp_subsets) == 1
        else Merger().merge([str(path) for path in temp_subsets])
    )
    try:
        if normalize_mono_width:
            _normalize_mono_widths(font)
        _normalize_font_names(font, output)
        _normalize_vertical_metrics(font, output)
        if "OS/2" in font:
            cast(Os2Table, font["OS/2"]).usMaxContext = 0
        glyphs = len(font.getGlyphOrder())
        if glyphs > TTF_GLYPH_LIMIT:
            raise ValueError(
                f"{output.name} wrote {glyphs} glyphs, limit {TTF_GLYPH_LIMIT}"
            )
        font.save(output)
        return glyphs
    finally:
        font.close()


def merge_selected_codepoints(
    label: str,
    output_name: str,
    selected: list[SelectedCodepoint],
    output_root: Path,
    normalize_mono_width: bool,
    codepoint_filter: CodepointFilter,
) -> list[ProvenanceRecord]:
    estimated = len(selected) + 1
    if estimated > TTF_GLYPH_LIMIT:
        raise ValueError(
            f"{label} cannot fit into one TTF: estimated {estimated} glyph slots, limit {TTF_GLYPH_LIMIT}"
        )
    output = output_root / output_name
    source_by_codepoint: dict[int, str] = {}
    codepoints_by_font: dict[Path, list[int]] = {}
    for item in selected:
        source_by_codepoint[item.codepoint] = relative_source(item.font.path)
        codepoints_by_font.setdefault(item.font.path, []).append(item.codepoint)
    if not codepoints_by_font:
        print(f"skip {label}: no cmap entries")
        return []
    with tempfile.TemporaryDirectory(prefix="uninoto-") as temp:
        temp_root = Path(temp)
        temp_subsets: list[Path] = []
        for index, (font_path, codepoints) in enumerate(codepoints_by_font.items()):
            unique = sorted(set(codepoints))
            target = temp_root / f"subset-{index}.ttf"
            _subset_font_to_temp(font_path, unique, target)
            temp_subsets.append(target)
        glyphs = _write_merged_font(temp_subsets, output, normalize_mono_width)
    actual = read_font_codepoints(output, codepoint_filter)
    print(
        f"wrote {output} ({glyphs} glyphs, {len(actual)}/{len(selected)} codepoints, {len(codepoints_by_font)} subsets)"
    )
    return [
        ProvenanceRecord(
            cp,
            output_name,
            source_by_codepoint.get(cp, ""),
            "" if cp in source_by_codepoint else "source-not-found",
        )
        for cp in sorted(actual)
    ]


def merge_category(
    category: Category,
    family: FontFamily,
    fonts: list[FontInfo],
    output_root: Path,
    codepoint_filter: CodepointFilter,
) -> list[ProvenanceRecord]:
    selected = selected_codepoints_for_category(category, fonts, family)
    return merge_selected_codepoints(
        f"{family}-{category}",
        output_name_for(family, category),
        selected,
        output_root,
        family == "mono",
        codepoint_filter,
    )


def merge_last(
    fonts: list[FontInfo], output_root: Path, codepoint_filter: CodepointFilter
) -> list[ProvenanceRecord]:
    sans = {item.codepoint: item for item in selected_output_codepoints(fonts, "sans")}
    serif = {
        item.codepoint: item for item in selected_output_codepoints(fonts, "serif")
    }
    selected = [item for cp, item in sans.items() if cp not in serif]
    selected.extend(item for cp, item in serif.items() if cp not in sans)
    selected.sort(key=lambda item: item.codepoint)
    only_sans = len([cp for cp in sans if cp not in serif])
    only_serif = len([cp for cp in serif if cp not in sans])
    print(
        f"sans/serif coverage check: sans={len(sans)}, serif={len(serif)}, only-sans={only_sans}, only-serif={only_serif}"
    )
    remove_last_output_fonts(output_root)
    if len(selected) <= LAST_BUCKET_CODEPOINT_LIMIT:
        return merge_selected_codepoints(
            "last",
            LAST_OUTPUT_NAMES[0],
            selected,
            output_root,
            False,
            codepoint_filter,
        )
    provenance: list[ProvenanceRecord] = []
    provenance.extend(
        merge_selected_codepoints(
            "last1",
            LAST_OUTPUT_NAMES[1],
            selected[:LAST_BUCKET_CODEPOINT_LIMIT],
            output_root,
            False,
            codepoint_filter,
        )
    )
    last2 = selected[LAST_BUCKET_CODEPOINT_LIMIT : LAST_BUCKET_CODEPOINT_LIMIT * 2]
    provenance.extend(
        merge_selected_codepoints(
            "last2",
            LAST_OUTPUT_NAMES[2],
            last2,
            output_root,
            False,
            codepoint_filter,
        )
    )
    overflow = max(0, len(selected) - LAST_BUCKET_CODEPOINT_LIMIT * 2)
    if overflow:
        print(
            f"warning: last has {len(selected)} codepoints; left {overflow} overflow codepoints"
        )
    return provenance


def write_coverage_csv(records: list[ProvenanceRecord], output: Path) -> None:
    sorted_records = sorted(
        records, key=lambda r: (r.codepoint, r.font_file, r.source_font)
    )
    segments: list[Segment] = []
    for record in sorted_records:
        plane = unicode_plane_name(record.codepoint)
        last = segments[-1] if segments else None
        if (
            last
            and last.end + 1 == record.codepoint
            and last.plane == plane
            and last.font_file == record.font_file
            and last.source_font == record.source_font
            and last.note == record.note
        ):
            last.end = record.codepoint
        else:
            segments.append(
                Segment(
                    record.codepoint,
                    record.codepoint,
                    plane,
                    record.font_file,
                    record.source_font,
                    record.note,
                )
            )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv_lib.writer(fh)
        writer.writerow(["code_range", "plane", "font_file", "source_font", "note"])
        for segment in segments:
            code_range = (
                cp_hex(segment.start)
                if segment.start == segment.end
                else f"{cp_hex(segment.start)}..{cp_hex(segment.end)}"
            )
            writer.writerow(
                [
                    code_range,
                    segment.plane,
                    segment.font_file,
                    segment.source_font,
                    segment.note,
                ]
            )
    print(f"wrote {output} ({len(segments)} provenance segments)")


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


def merged_coverage_fonts(output_root: Path, family: FontFamily) -> list[Path]:
    family_names = [output_name_for(family, c) for c in DEFAULT_CATEGORIES]
    names = set(
        [*family_names, *LAST_OUTPUT_NAMES]
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


def font_files_by_output_names(output_root: Path, names: set[str]) -> list[Path]:
    return [file for file in list_font_files(output_root) if file.name in names]


def check_sans_serif_fallback_coverage(
    output_root: Path, codepoint_filter: CodepointFilter
) -> None:
    sans_names = {
        *[output_name_for("sans", c) for c in DEFAULT_CATEGORIES],
        *LAST_OUTPUT_NAMES,
    }
    serif_names = {
        *[output_name_for("serif", c) for c in DEFAULT_CATEGORIES],
        *LAST_OUTPUT_NAMES,
    }
    sans = collect_merged_coverage(
        font_files_by_output_names(output_root, sans_names), codepoint_filter
    )
    serif = collect_merged_coverage(
        font_files_by_output_names(output_root, serif_names), codepoint_filter
    )
    only_sans = [cp for cp in sans if cp not in serif]
    only_serif = [cp for cp in serif if cp not in sans]
    print(
        f"sans/serif fallback coverage check: sans={len(sans)}, serif={len(serif)}, only-sans={len(only_sans)}, only-serif={len(only_serif)}"
    )
    if only_sans or only_serif:
        raise ValueError("sans and serif fallback coverage are not identical")


def write_missing_visible_report_for_fonts(
    options: Options,
    label: str,
    font_paths: list[Path],
    missing_output: Path,
    missing_summary_output: Path | None,
) -> None:
    codepoint_filter = project_mergeable_codepoint_filter(options.unicode_data)
    covered = collect_merged_coverage(font_paths, codepoint_filter)
    age_ranges = read_age_ranges(options.derived_age)
    category_ranges = read_unicode_data_ranges(options.unicode_data)
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
    print(f"{label} coverage fonts: {names}")
    print(f"{label} covered codepoints: {len(covered)}")
    print(f"wrote {missing_output} ({len(missing)} missing visible)")


def write_missing_visible_report(options: Options, family: FontFamily) -> None:
    if family not in REPORT_FAMILIES:
        return
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
    )
    if family in {"sans", "serif"}:
        write_missing_visible_report_for_fonts(
            options,
            f"{family} without last",
            family_output_fonts(options.output, family),
            report_path_with_suffix(options.missing_output, family, "without_last"),
            (
                report_path_with_suffix(
                    options.missing_summary_output, family, "without_last"
                )
                if options.missing_summary_output
                else None
            ),
        )


def family_output_fonts(output_root: Path, family: FontFamily) -> list[Path]:
    names = {output_name_for(family, category) for category in DEFAULT_CATEGORIES}
    return [file for file in list_font_files(output_root) if file.name in names]


def report_path_with_suffix(output: Path, family: FontFamily, suffix: str) -> Path:
    report_path = report_path_for_family(output, family)
    return report_path.with_name(f"{report_path.stem}-{suffix}{report_path.suffix}")


def remove_last_output_fonts(output_root: Path) -> None:
    for name in (*LAST_OUTPUT_NAMES, *LEGACY_LAST_OUTPUT_NAMES):
        (output_root / name).unlink(missing_ok=True)


def remove_stale_last_reports(options: Options) -> None:
    outputs = [
        report_path_for_family(options.coverage_output, "last"),
        report_path_for_family(options.missing_output, "last"),
    ]
    if options.missing_summary_output:
        outputs.append(report_path_for_family(options.missing_summary_output, "last"))
    for output in outputs:
        output.unlink(missing_ok=True)


def parse_args() -> Options:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="fonts/noto")
    parser.add_argument("--output", default="fonts/merged")
    parser.add_argument("--family")
    parser.add_argument(
        "--coverage-output", default="fonts/reports/plane-font-coverage.csv"
    )
    parser.add_argument("--missing-output", default="fonts/reports/missing-visible.csv")
    parser.add_argument("--missing-summary-output")
    parser.add_argument("--include-marks", action="store_true")
    parser.add_argument("--derived-age", default="fonts/unicode/DerivedAge.txt")
    parser.add_argument("--unicode-data", default="fonts/unicode/UnicodeData.txt")
    args = parser.parse_args()
    return Options(
        input=Path(args.input),
        output=Path(args.output),
        family=parse_font_family(args.family, "--family") if args.family else None,
        coverage_output=Path(args.coverage_output),
        missing_output=Path(args.missing_output),
        missing_summary_output=(
            Path(args.missing_summary_output) if args.missing_summary_output else None
        ),
        include_marks=bool(args.include_marks),
        derived_age=Path(args.derived_age),
        unicode_data=Path(args.unicode_data),
    )


def main() -> None:
    options = parse_args()
    codepoint_filter = project_mergeable_codepoint_filter(options.unicode_data)
    fonts = discover_fonts(options.input, codepoint_filter)
    if not fonts:
        raise ValueError(f"no fonts found below {options.input}")
    print(f"discovered {len(fonts)} fonts")
    families: list[FontFamily] = (
        [options.family] if options.family is not None else list(FONT_FAMILIES)
    )
    remove_stale_last_reports(options)
    for family in families:
        if family == "last":
            merge_last(fonts, options.output, codepoint_filter)
            continue
        provenance: list[ProvenanceRecord] = []
        provenance.extend(
            merge_category("bmp", family, fonts, options.output, codepoint_filter)
        )
        buckets = upper_buckets(fonts, family)
        provenance.extend(
            merge_selected_codepoints(
                f"{family}-upper1",
                output_name_for(family, "upper1"),
                buckets["upper1"],
                options.output,
                family == "mono",
                codepoint_filter,
            )
        )
        provenance.extend(
            merge_selected_codepoints(
                f"{family}-upper2",
                output_name_for(family, "upper2"),
                buckets["upper2"],
                options.output,
                family == "mono",
                codepoint_filter,
            )
        )
        write_coverage_csv(
            provenance, report_path_for_family(options.coverage_output, family)
        )
    for family in families:
        if family in REPORT_FAMILIES:
            write_missing_visible_report(options, family)
    if not options.family or options.family == "last":
        check_sans_serif_fallback_coverage(options.output, codepoint_filter)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
