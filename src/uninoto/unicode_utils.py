from __future__ import annotations

import unicodedata

CodeRange = tuple[int, int]
TTF_GLYPH_LIMIT = 2**16 - 1

HAN_RANGES: tuple[CodeRange, ...] = (
    (0x3400, 0x4DBF),
    (0x4E00, 0x9FFF),
    (0xF900, 0xFAFF),
    (0x20000, 0x2A6DF),
    (0x2A700, 0x2B73F),
    (0x2B740, 0x2B81F),
    (0x2B820, 0x2CEAF),
    (0x2CEB0, 0x2EBEF),
    (0x2EBF0, 0x2EE5F),
    (0x30000, 0x3134F),
    (0x31350, 0x323AF),
    (0x323B0, 0x3347F),
)

CJK_RELATED_RANGES: tuple[CodeRange, ...] = (
    *HAN_RANGES,
    (0x1100, 0x11FF),
    (0x2E80, 0x2EFF),
    (0x2F00, 0x2FDF),
    (0x3000, 0x303F),
    (0x3040, 0x309F),
    (0x30A0, 0x30FF),
    (0x3100, 0x312F),
    (0x3130, 0x318F),
    (0x3190, 0x319F),
    (0x31A0, 0x31BF),
    (0x31C0, 0x31EF),
    (0x31F0, 0x31FF),
    (0x3200, 0x32FF),
    (0x3300, 0x33FF),
    (0xA000, 0xA4CF),
    (0xA960, 0xA97F),
    (0xAC00, 0xD7AF),
    (0xD7B0, 0xD7FF),
    (0xFE30, 0xFE4F),
    (0xFF00, 0xFFEF),
    (0x16FE0, 0x16FFF),
    (0x17000, 0x187FF),
    (0x18800, 0x18AFF),
    (0x1AFF0, 0x1AFFF),
    (0x1B000, 0x1B16F),
    (0x1B170, 0x1B2FF),
    (0x1F200, 0x1F2FF),
)

EMOJI_RANGES: tuple[CodeRange, ...] = ((0x2600, 0x27BF), (0x1F000, 0x1FAFF))
INVISIBLE_GENERAL_CATEGORIES = {"Cc", "Cf", "Cs", "Co", "Cn"}


def in_ranges(codepoint: int, ranges: tuple[CodeRange, ...]) -> bool:
    return any(start <= codepoint <= end for start, end in ranges)


def is_surrogate(codepoint: int) -> bool:
    return 0xD800 <= codepoint <= 0xDFFF


def is_unicode_scalar(codepoint: int) -> bool:
    return 0 <= codepoint <= 0x10FFFF and not is_surrogate(codepoint)


def general_category(codepoint: int) -> str:
    if not is_unicode_scalar(codepoint):
        return "Cs"
    return unicodedata.category(chr(codepoint))


def is_visible_codepoint(codepoint: int, include_marks: bool) -> bool:
    category = general_category(codepoint)
    if category in INVISIBLE_GENERAL_CATEGORIES:
        return False
    if not include_marks and category.startswith("M"):
        return False
    return True


def is_mergeable_codepoint(codepoint: int) -> bool:
    return is_visible_codepoint(codepoint, True)


def cp_hex(codepoint: int) -> str:
    return f"U+{codepoint:04X}"


def unicode_plane_name(codepoint: int) -> str:
    plane = codepoint // 0x10000
    if plane == 0:
        return "Basic Multilingual Plane"
    if plane == 1:
        return "Supplementary Multilingual Plane"
    if plane == 2:
        return "Supplementary Ideographic Plane"
    if plane == 3:
        return "Tertiary Ideographic Plane"
    if plane == 14:
        return "Supplementary Special-purpose Plane"
    if plane == 15:
        return "Supplementary Private Use Area-A"
    if plane == 16:
        return "Supplementary Private Use Area-B"
    return f"Unassigned Plane {plane}"
