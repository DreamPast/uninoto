from __future__ import annotations

from typing import Literal

Category = Literal["bmp", "upper1", "upper2"]
FontFamily = Literal["sans", "serif", "mono", "last"]

DEFAULT_CATEGORIES: tuple[Category, ...] = ("bmp", "upper1", "upper2")
FONT_FAMILIES: tuple[FontFamily, ...] = ("sans", "serif", "mono", "last")
LAST_OUTPUT_NAMES = ("uninoto_last.ttf", "uninoto_last1.ttf", "uninoto_last2.ttf")
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


def output_name_for(family: FontFamily, category: Category) -> str:
    if family == "last":
        if category == "bmp":
            return LAST_OUTPUT_NAMES[0]
        if category == "upper1":
            return LAST_OUTPUT_NAMES[1]
        return LAST_OUTPUT_NAMES[2]
    prefix = FAMILY_PREFIX[family]
    if category == "bmp":
        return f"{prefix}.ttf"
    return f"{prefix}_{category}.ttf"


def all_output_names() -> list[str]:
    return [
        *(output_name_for("sans", c) for c in DEFAULT_CATEGORIES),
        *(output_name_for("serif", c) for c in DEFAULT_CATEGORIES),
        *(output_name_for("mono", c) for c in DEFAULT_CATEGORIES),
        *LAST_OUTPUT_NAMES,
    ]


def parse_font_family(value: str | None, option_name: str = "family") -> FontFamily:
    if value in FONT_FAMILIES:
        return value
    if value == "serief":
        return "serif"
    raise ValueError(
        f"invalid {option_name}: {value or '<missing>'} (expected sans, serif, mono, or last)"
    )
