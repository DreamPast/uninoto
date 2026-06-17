from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from fontTools.ttLib import TTFont

from .merge import _subset_font_to_temp, _write_merged_font
from .unicode_utils import TTF_GLYPH_LIMIT

SANS_EXTRA_PREFIX = "uninoto_sans_extra"


def _source_fonts(input_root: Path) -> list[Path]:
    sans_fonts = [
        path
        for path in sorted(input_root.glob("uninoto_sans*.ttf"))
        if not path.name.startswith(SANS_EXTRA_PREFIX)
    ]
    sans_extra_fonts = sorted(input_root.glob(f"{SANS_EXTRA_PREFIX}*.ttf"))
    return [*sans_fonts, *sans_extra_fonts]


def _source_codepoints_by_plane(
    fonts: list[Path],
) -> dict[int, dict[Path, list[int]]]:
    seen: set[int] = set()
    planes: dict[int, dict[Path, list[int]]] = {}
    for path in fonts:
        font = TTFont(path, lazy=True)
        try:
            cmap = font.getBestCmap() or {}
        finally:
            font.close()
        for codepoint in sorted(cmap):
            if codepoint in seen:
                continue
            seen.add(codepoint)
            plane = codepoint // 0x10000
            planes.setdefault(plane, {}).setdefault(path, []).append(codepoint)
    return planes


def _remove_stale_plane_outputs(output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for pattern in ("plane*.ttf", "uninoto_plane*.ttf"):
        for path in output_root.glob(pattern):
            path.unlink()


def _write_plane_font(
    plane: int,
    codepoints_by_font: dict[Path, list[int]],
    output_root: Path,
) -> None:
    codepoint_count = sum(len(codepoints) for codepoints in codepoints_by_font.values())
    if codepoint_count + 1 > TTF_GLYPH_LIMIT:
        raise ValueError(
            f"uninoto_plane{plane}.ttf has {codepoint_count} codepoints and may exceed "
            f"the TTF glyph limit of {TTF_GLYPH_LIMIT}"
        )
    output = output_root / f"uninoto_plane{plane}.ttf"
    with tempfile.TemporaryDirectory(prefix=f"uninoto-plane{plane}-") as temp:
        temp_root = Path(temp)
        subsets: list[Path] = []
        for index, (font_path, codepoints) in enumerate(codepoints_by_font.items()):
            subset_path = temp_root / f"subset-{index}.ttf"
            _subset_font_to_temp(
                font_path,
                codepoints,
                subset_path,
                preserve_source_metadata=False,
            )
            subsets.append(subset_path)
        glyphs, pruned = _write_merged_font(
            subsets,
            output,
            normalize_mono_width=False,
            style="full",
            preserve_source_metadata=False,
        )
    print(
        f"wrote {output} ({glyphs} glyphs, {codepoint_count} codepoints, "
        f"{len(subsets)} subsets, pruned={pruned})"
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=("Build one full-style sans/extra fallback font per Unicode plane.")
    )
    parser.add_argument(
        "--input",
        default="fonts/merged/full",
        help="directory containing full uninoto_sans*.ttf and uninoto_sans_extra*.ttf",
    )
    parser.add_argument(
        "--output",
        default="fonts/merged/full_per_plane",
        help="directory for uninoto_plane*.ttf outputs",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_root = Path(args.input)
    output_root = Path(args.output)
    fonts = _source_fonts(input_root)
    if not fonts:
        raise ValueError(f"no sans/sans_extra fonts found below {input_root}")
    planes = _source_codepoints_by_plane(fonts)
    _remove_stale_plane_outputs(output_root)
    for plane in sorted(planes):
        _write_plane_font(plane, planes[plane], output_root)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
