from __future__ import annotations

from typing import Literal

Category = Literal["bmp", "upper", "upper1", "upper2"]
FontFamily = Literal["sans", "serif", "mono", "last"]
FontStyle = Literal["regular", "bold", "italic", "bolditalic", "full"]

MAX_RECOGNIZED_BMP_OUTPUTS = 512
MAX_RECOGNIZED_UPPER_OUTPUTS = 512
MAX_RECOGNIZED_LAST_OUTPUTS = 512
MAX_RECOGNIZED_SPLIT_OUTPUTS = 512
REGION_SPLIT_LABELS = ("sc", "tc", "hk", "jp", "kr")
FONT_FAMILIES: tuple[FontFamily, ...] = ("sans", "serif", "mono", "last")
FONT_STYLES: tuple[FontStyle, ...] = (
    "regular",
    "bold",
    "italic",
    "bolditalic",
    "full",
)
LAST_OUTPUT_NAMES = (
    "uninoto_last.ttf",
    *(
        f"uninoto_last{index}.ttf"
        for index in range(1, MAX_RECOGNIZED_LAST_OUTPUTS + 1)
    ),
)
LEGACY_LAST_OUTPUT_NAMES = (
    "uninoto_other.ttf",
    "uninoto_other1.ttf",
    "uninoto_other2.ttf",
)
FAMILY_PREFIX: dict[FontFamily, str] = {
    "sans": "uninoto_sans",
    "serif": "uninoto_serif",
    "mono": "uninoto_mono",
    "last": "uninoto_last",
}


def codepoint_in_category(category: Category, codepoint: int) -> bool:
    if category == "bmp":
        return codepoint <= 0xFFFF
    return codepoint > 0xFFFF


def output_name_for(family: FontFamily, category: str) -> str:
    if family == "last":
        if category == "bmp":
            return LAST_OUTPUT_NAMES[0]
        if category == "upper1":
            return LAST_OUTPUT_NAMES[1]
        if category == "upper2":
            return LAST_OUTPUT_NAMES[2]
        return f"uninoto_last_{category}.ttf"
    prefix = FAMILY_PREFIX[family]
    if category == "bmp":
        return f"{prefix}.ttf"
    if category == "upper":
        return f"{prefix}_upper.ttf"
    return f"{prefix}_{category}.ttf"


def all_output_names() -> list[str]:
    bmp_categories = [
        "bmp",
        *(f"bmp{index}" for index in range(2, MAX_RECOGNIZED_BMP_OUTPUTS + 1)),
    ]
    upper_categories = [
        "upper",
        *(f"upper{index}" for index in range(1, MAX_RECOGNIZED_UPPER_OUTPUTS + 1)),
    ]
    split_categories = [
        *(str(index) for index in range(1, MAX_RECOGNIZED_SPLIT_OUTPUTS + 1)),
        *REGION_SPLIT_LABELS,
        *(
            f"{region}{index}"
            for region in REGION_SPLIT_LABELS
            for index in range(2, MAX_RECOGNIZED_SPLIT_OUTPUTS + 1)
        ),
    ]
    return [
        *(output_name_for("sans", c) for c in bmp_categories),
        *(output_name_for("sans", c) for c in upper_categories),
        *(output_name_for("sans", c) for c in split_categories),
        *(output_name_for("serif", c) for c in bmp_categories),
        *(output_name_for("serif", c) for c in upper_categories),
        *(output_name_for("serif", c) for c in split_categories),
        *(output_name_for("mono", c) for c in bmp_categories),
        *(output_name_for("mono", c) for c in upper_categories),
        *(output_name_for("mono", c) for c in split_categories),
        *LAST_OUTPUT_NAMES,
        *(output_name_for("last", c) for c in split_categories),
    ]


def parse_font_family(value: str | None, option_name: str = "family") -> FontFamily:
    if value in FONT_FAMILIES:
        return value
    if value == "serief":
        return "serif"
    raise ValueError(
        f"invalid {option_name}: {value or '<missing>'} (expected sans, serif, mono, or last)"
    )


def parse_font_style(value: str | None, option_name: str = "style") -> FontStyle:
    if value in FONT_STYLES:
        return value
    raise ValueError(
        f"invalid {option_name}: {value or '<missing>'} "
        "(expected regular, bold, italic, bolditalic, full, or all)"
    )
