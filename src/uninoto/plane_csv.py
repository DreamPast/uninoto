from __future__ import annotations

import argparse
import csv
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .font_io import FontInfo, discover_fonts, list_font_files, read_font_codepoints
from .merge import project_mergeable_codepoint_filter
from .planes import (
    DEFAULT_CATEGORIES,
    FONT_FAMILIES,
    Category,
    FontFamily,
    all_output_names,
    codepoint_in_category,
    output_name_for,
)
from .source_selection import ordered_fonts
from .unicode_utils import cp_hex, unicode_plane_name

UPPER_BUCKET_CODEPOINT_LIMIT = 60000
PLANE_1_END = 0x1FFFF
REPORT_FAMILIES: tuple[FontFamily, ...] = ("sans", "serif")
CodepointFilter = Callable[[int], bool]


@dataclass
class Segment:
    start: int
    end: int
    plane: str
    font: str
    source_font: str
    note: str


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


def report_path_for_family(output: Path, family: FontFamily) -> Path:
    return output.with_name(f"{family}-{output.stem}{output.suffix or '.csv'}")


def output_info_for_font(font_file: str) -> tuple[FontFamily, Category] | None:
    for family in FONT_FAMILIES:
        for category in DEFAULT_CATEGORIES:
            if output_name_for(family, category) == font_file:
                return family, category
    return None


def source_map_for_category(
    category: Category, family: FontFamily, fonts: list[FontInfo]
) -> dict[int, str]:
    result: dict[int, str] = {}
    for font in ordered_fonts(category, fonts, family):
        for cp in font.codepoints:
            if codepoint_in_category(category, cp) and cp not in result:
                result[cp] = relative_source(font.path)
    return result


def selected_upper_codepoints(
    fonts: list[FontInfo], family: FontFamily
) -> list[SelectedCodepoint]:
    selected: dict[int, FontInfo] = {}
    for font in ordered_fonts("upper1", fonts, family):
        for cp in font.codepoints:
            if 0x10000 <= cp <= PLANE_1_END and cp not in selected:
                selected[cp] = font
    for font in ordered_fonts("upper2", fonts, family):
        for cp in font.codepoints:
            if cp > PLANE_1_END and cp not in selected:
                selected[cp] = font
    return [SelectedCodepoint(cp, selected[cp]) for cp in sorted(selected)]


def upper_source_maps(
    fonts: list[FontInfo], family: FontFamily
) -> dict[Category, dict[int, str]]:
    selected = selected_upper_codepoints(fonts, family)
    result: dict[Category, dict[int, str]] = {"upper1": {}, "upper2": {}}
    for index, item in enumerate(selected):
        category: Category = (
            "upper1" if index < UPPER_BUCKET_CODEPOINT_LIMIT else "upper2"
        )
        result[category][item.codepoint] = relative_source(item.font.path)
    return result


def write_family_report(
    family: FontFamily,
    merged_fonts: list[Path],
    all_sources: list[FontInfo],
    output: Path,
    codepoint_filter: CodepointFilter,
) -> None:
    sources_by_output: dict[str, dict[int, str]] = {
        output_name_for(family, "bmp"): source_map_for_category(
            "bmp", family, all_sources
        )
    }
    for category, source_map in upper_source_maps(all_sources, family).items():
        sources_by_output[output_name_for(family, category)] = source_map
    family_output_names = {
        output_name_for(family, category) for category in DEFAULT_CATEGORIES
    }
    coverage: dict[int, list[str]] = {}
    for font in merged_fonts:
        if font.name not in family_output_names:
            continue
        info = output_info_for_font(font.name)
        if not info or info[0] != family:
            continue
        for cp in read_font_codepoints(font, codepoint_filter):
            coverage.setdefault(cp, []).append(font.name)
    segments: list[Segment] = []
    for cp in sorted(coverage):
        plane = unicode_plane_name(cp)
        fonts_for_cp = coverage.get(cp, [])
        font_text = ";".join(fonts_for_cp)
        source_font = ";".join(
            dict.fromkeys(
                source
                for source in (
                    sources_by_output.get(font, {}).get(cp, "") for font in fonts_for_cp
                )
                if source
            )
        )
        note_parts = []
        if len(fonts_for_cp) > 1:
            note_parts.append("overlap")
        if not source_font:
            note_parts.append("source-not-found")
        note = ";".join(note_parts)
        last = segments[-1] if segments else None
        if (
            last
            and last.end + 1 == cp
            and last.plane == plane
            and last.font == font_text
            and last.source_font == source_font
            and last.note == note
        ):
            last.end = cp
        else:
            segments.append(Segment(cp, cp, plane, font_text, source_font, note))
    family_output = report_path_for_family(output, family)
    family_output.parent.mkdir(parents=True, exist_ok=True)
    with family_output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
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
                    segment.font,
                    segment.source_font,
                    segment.note,
                ]
            )
    print(f"{family} segments: {len(segments)}")
    print(f"wrote {family_output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts-dir", default="fonts/merged")
    parser.add_argument("--input", default="fonts/noto")
    parser.add_argument("--output", default="fonts/reports/plane-font-coverage.csv")
    parser.add_argument("--unicode-data", default="fonts/unicode/UnicodeData.txt")
    args = parser.parse_args()
    codepoint_filter = project_mergeable_codepoint_filter(Path(args.unicode_data))
    output_names = set(all_output_names())
    merged_fonts = [
        file
        for file in list_font_files(Path(args.fonts_dir))
        if file.name in output_names
    ]
    all_sources = discover_fonts(Path(args.input), codepoint_filter)
    for family in REPORT_FAMILIES:
        write_family_report(
            family, merged_fonts, all_sources, Path(args.output), codepoint_filter
        )
    print(f"fonts: {len(merged_fonts)}")
    print(f"sources: {len(all_sources)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
