from __future__ import annotations

from typing import Literal

Category = Literal["bmp", "upper", "upper1", "upper2"]
FontFamily = Literal["sans", "serif", "mono", "extra", "last_resort"]
FontStyle = Literal["regular", "bold", "italic", "bolditalic", "full"]

MAX_RECOGNIZED_UPPER_OUTPUTS = 512
MAX_RECOGNIZED_EXTRA_OUTPUTS = 512
MAX_RECOGNIZED_LAST_RESORT_OUTPUTS = 512
MAX_RECOGNIZED_SPLIT_OUTPUTS = 512
FONT_FAMILIES: tuple[FontFamily, ...] = (
    "sans",
    "serif",
    "mono",
    "extra",
    "last_resort",
)
FONT_STYLES: tuple[FontStyle, ...] = (
    "regular",
    "bold",
    "italic",
    "bolditalic",
    "full",
)
EXTRA_OUTPUT_NAMES = (
    "uninoto_extra.ttf",
    *(
        f"uninoto_extra{index}.ttf"
        for index in range(1, MAX_RECOGNIZED_EXTRA_OUTPUTS + 1)
    ),
)
LAST_RESORT_OUTPUT_NAMES = (
    "uninoto_last_resort.ttf",
    *(
        f"uninoto_last_resort{index}.ttf"
        for index in range(1, MAX_RECOGNIZED_LAST_RESORT_OUTPUTS + 1)
    ),
)
LEGACY_EXTRA_OUTPUT_NAMES = (
    "uninoto_last.ttf",
    *(
        f"uninoto_last{index}.ttf"
        for index in range(1, MAX_RECOGNIZED_EXTRA_OUTPUTS + 1)
    ),
    "uninoto_other.ttf",
    "uninoto_other1.ttf",
    "uninoto_other2.ttf",
)
FAMILY_PREFIX: dict[FontFamily, str] = {
    "sans": "uninoto_sans",
    "serif": "uninoto_serif",
    "mono": "uninoto_mono",
    "extra": "uninoto_extra",
    "last_resort": "uninoto_last_resort",
}


def codepoint_in_category(category: Category, codepoint: int) -> bool:
    if category == "bmp":
        return codepoint <= 0xFFFF
    return codepoint > 0xFFFF


def output_name_for(family: FontFamily, category: str) -> str:
    if family == "extra":
        if category == "bmp":
            return EXTRA_OUTPUT_NAMES[0]
        if category.isdecimal():
            return f"uninoto_extra{category}.ttf"
        if category == "upper1":
            return EXTRA_OUTPUT_NAMES[1]
        if category == "upper2":
            return EXTRA_OUTPUT_NAMES[2]
        return f"uninoto_extra_{category}.ttf"
    if family == "last_resort":
        if category == "bmp":
            return LAST_RESORT_OUTPUT_NAMES[0]
        if category.isdecimal():
            return f"uninoto_last_resort{category}.ttf"
        return f"uninoto_last_resort_{category}.ttf"
    prefix = FAMILY_PREFIX[family]
    if category == "bmp":
        return f"{prefix}.ttf"
    if category.isdecimal():
        return f"{prefix}{category}.ttf"
    if category == "upper":
        return f"{prefix}_upper.ttf"
    return f"{prefix}_{category}.ttf"


def all_output_names() -> list[str]:
    upper_categories = [
        "upper",
        *(f"upper{index}" for index in range(1, MAX_RECOGNIZED_UPPER_OUTPUTS + 1)),
    ]
    split_categories = [
        str(index) for index in range(1, MAX_RECOGNIZED_SPLIT_OUTPUTS + 1)
    ]
    return [
        output_name_for("sans", "bmp"),
        *(output_name_for("sans", c) for c in split_categories),
        *(output_name_for("sans", c) for c in upper_categories),
        output_name_for("serif", "bmp"),
        *(output_name_for("serif", c) for c in split_categories),
        *(output_name_for("serif", c) for c in upper_categories),
        output_name_for("mono", "bmp"),
        *(output_name_for("mono", c) for c in split_categories),
        *(output_name_for("mono", c) for c in upper_categories),
        *EXTRA_OUTPUT_NAMES,
        *LAST_RESORT_OUTPUT_NAMES,
    ]


def parse_font_family(value: str | None, option_name: str = "family") -> FontFamily:
    if value in FONT_FAMILIES:
        return value
    if value == "serief":
        return "serif"
    raise ValueError(
        f"invalid {option_name}: {value or '<missing>'} (expected sans, serif, mono, extra, or last_resort)"
    )


def parse_font_style(value: str | None, option_name: str = "style") -> FontStyle:
    if value in FONT_STYLES:
        return value
    raise ValueError(
        f"invalid {option_name}: {value or '<missing>'} "
        "(expected regular, bold, italic, bolditalic, full, or all)"
    )
