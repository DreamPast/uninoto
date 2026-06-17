from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .font_io import list_font_files, read_font_codepoints
from .merge import (
    category_from_ranges,
    is_last_resort_fallback_codepoint,
    last_resort_output_names,
    project_mergeable_codepoint_filter,
    read_unicode_data_ranges,
)
from .planes import all_output_names
from .unicode_utils import cp_hex, general_category


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fonts-dir", default="fonts/merged/regular")
    parser.add_argument("--output", default="fonts/validation/invalid-codepoints.csv")
    parser.add_argument("--unicode-data", default="fonts/unicode/UnicodeData.txt")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    codepoint_filter = project_mergeable_codepoint_filter(Path(args.unicode_data))
    category_ranges = read_unicode_data_ranges(Path(args.unicode_data))
    last_resort_names = set(last_resort_output_names())
    font_files = list_font_files(Path(args.fonts_dir))
    names = set(all_output_names())
    fonts = (
        font_files if args.all else [file for file in font_files if file.name in names]
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    invalid = 0
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["font", "codepoint", "general_category"])
        for font in fonts:
            for cp in read_font_codepoints(font, lambda _cp: True):
                category = category_from_ranges(cp, category_ranges) or "Cn"
                if (
                    font.name in last_resort_names
                    and is_last_resort_fallback_codepoint(cp, category)
                    and font.parent.name == "full"
                ):
                    continue
                if not codepoint_filter(cp):
                    invalid += 1
                    writer.writerow(
                        [
                            str(font),
                            cp_hex(cp),
                            general_category(cp) if category == "Cn" else category,
                        ]
                    )
    print(f"fonts: {len(fonts)}")
    print(f"invalid codepoints: {invalid}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
