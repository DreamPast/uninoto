from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.pens.ttGlyphPen import TTGlyphPen


@dataclass
class SfdGlyph:
    index: int = -1
    name: str = ""
    codepoint: int = -1
    width: int = 600
    contours: list[list[tuple[str, tuple[float, ...]]]] = field(default_factory=list)
    references: list[tuple[int, tuple[float, float, float, float, float, float]]] = (
        field(default_factory=list)
    )


@dataclass
class SfdFont:
    font_name: str
    family_name: str
    ascent: int
    descent: int
    glyphs: list[SfdGlyph]


NUMBER_PATTERN = r"-?(?:\d+(?:\.\d*)?|\.\d+)"
POINT_COMMAND_RE = re.compile(
    rf"^\s*({NUMBER_PATTERN})\s+({NUMBER_PATTERN})\s+([ml])\s+[-\d]+"
)
CURVE_COMMAND_RE = re.compile(
    rf"^\s*({NUMBER_PATTERN})\s+({NUMBER_PATTERN})\s+"
    rf"({NUMBER_PATTERN})\s+({NUMBER_PATTERN})\s+"
    rf"({NUMBER_PATTERN})\s+({NUMBER_PATTERN})\s+c\s+[-\d]+"
)
GLYPH_NAME_RE = re.compile(r"[^A-Za-z0-9_.]")


def parse_sfd(path: Path) -> SfdFont:
    font_name = path.stem
    family_name = path.stem
    ascent = 800
    descent = 200
    glyphs: list[SfdGlyph] = []
    current: SfdGlyph | None = None
    current_contour: list[tuple[str, tuple[float, ...]]] | None = None
    in_splines = False

    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("FontName: "):
            font_name = line.split(": ", 1)[1].strip()
        elif line.startswith("FamilyName: "):
            family_name = line.split(": ", 1)[1].strip()
        elif line.startswith("Ascent: "):
            ascent = int(float(line.split(": ", 1)[1]))
        elif line.startswith("Descent: "):
            descent = int(float(line.split(": ", 1)[1]))
        elif line.startswith("StartChar: "):
            current = SfdGlyph(name=line.split(": ", 1)[1].strip())
        elif current and line.startswith("Encoding: "):
            parts = line.split()
            current.codepoint = int(parts[1])
            current.index = int(parts[3])
        elif current and line.startswith("Width: "):
            current.width = int(float(line.split(": ", 1)[1]))
        elif current and line.startswith("Refer: "):
            parts = line.split()
            if len(parts) >= 10:
                current.references.append(
                    (
                        int(parts[1]),
                        (
                            float(parts[4]),
                            float(parts[5]),
                            float(parts[6]),
                            float(parts[7]),
                            float(parts[8]),
                            float(parts[9]),
                        ),
                    )
                )
        elif current and line == "SplineSet":
            in_splines = True
            current_contour = None
        elif current and line == "EndSplineSet":
            if current_contour:
                current.contours.append(current_contour)
            in_splines = False
            current_contour = None
        elif current and in_splines:
            current_contour = _parse_spline_line(line, current, current_contour)
        elif current and line == "EndChar":
            glyphs.append(current)
            current = None

    return SfdFont(font_name, family_name, ascent, descent, glyphs)


def _parse_spline_line(
    line: str,
    glyph: SfdGlyph,
    current_contour: list[tuple[str, tuple[float, ...]]] | None,
) -> list[tuple[str, tuple[float, ...]]] | None:
    point_match = POINT_COMMAND_RE.match(line)
    if point_match:
        x = float(point_match.group(1))
        y = float(point_match.group(2))
        command = point_match.group(3)
        if command == "m":
            if current_contour:
                glyph.contours.append(current_contour)
            return [("m", (x, y))]
        if current_contour is not None:
            current_contour.append(("l", (x, y)))
        return current_contour

    curve_match = CURVE_COMMAND_RE.match(line)
    if curve_match and current_contour is not None:
        current_contour.append(
            ("c", tuple(float(curve_match.group(index)) for index in range(1, 7)))
        )
    return current_contour


def build_ttf_from_sfd(source: Path, target: Path) -> None:
    font = parse_sfd(source)
    glyphs_by_index = {glyph.index: glyph for glyph in font.glyphs}
    encoded_glyphs = [glyph for glyph in font.glyphs if glyph.codepoint >= 0]
    glyph_order, glyph_names = _glyph_order(encoded_glyphs)
    units_per_em = font.ascent + font.descent

    builder = FontBuilder(units_per_em, isTTF=True)
    builder.setupGlyphOrder(glyph_order)
    builder.setupCharacterMap(
        {
            glyph.codepoint: glyph_names[glyph.index]
            for glyph in encoded_glyphs
            if glyph.index in glyph_names
        }
    )

    glyf, metrics = _build_glyf_and_metrics(
        encoded_glyphs, glyph_names, glyphs_by_index
    )
    builder.setupGlyf(glyf)
    builder.setupHorizontalMetrics(metrics)
    builder.setupHorizontalHeader(ascent=font.ascent, descent=-font.descent)
    builder.setupOS2(
        sTypoAscender=font.ascent,
        sTypoDescender=-font.descent,
        usWinAscent=font.ascent,
        usWinDescent=font.descent,
    )
    builder.setupNameTable(
        {
            "familyName": font.family_name,
            "styleName": "Regular",
            "uniqueFontIdentifier": f"{font.font_name} 1.000",
            "fullName": f"{font.family_name} Regular",
            "psName": f"{font.font_name}-Regular",
        }
    )
    builder.setupPost()
    builder.setupMaxp()
    target.parent.mkdir(parents=True, exist_ok=True)
    builder.save(target)


def _glyph_order(glyphs: list[SfdGlyph]) -> tuple[list[str], dict[int, str]]:
    order = [".notdef"]
    names = {".notdef"}
    glyph_names: dict[int, str] = {}
    for glyph in glyphs:
        base_name = GLYPH_NAME_RE.sub("_", glyph.name) or f"glyph{glyph.index}"
        name = base_name
        suffix = 1
        while name in names:
            suffix += 1
            name = f"{base_name}.{suffix}"
        names.add(name)
        order.append(name)
        glyph_names[glyph.index] = name
    return order, glyph_names


def _build_glyf_and_metrics(
    glyphs: list[SfdGlyph],
    glyph_names: dict[int, str],
    glyphs_by_index: dict[int, SfdGlyph],
) -> tuple[dict[str, object], dict[str, tuple[int, int]]]:
    glyf = {".notdef": _notdef_glyph()}
    metrics = {".notdef": (600, 0)}
    for glyph in glyphs:
        name = glyph_names[glyph.index]
        glyf[name] = _draw_glyph(glyph, glyphs_by_index)
        metrics[name] = (glyph.width, 0)
    return glyf, metrics


def _notdef_glyph() -> object:
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((550, 0))
    pen.lineTo((550, 700))
    pen.lineTo((50, 700))
    pen.closePath()
    return pen.glyph()


def _draw_glyph(glyph: SfdGlyph, glyphs_by_index: dict[int, SfdGlyph]) -> object:
    pen = TTGlyphPen(None)
    quadratic_pen = Cu2QuPen(pen, max_err=1.0, reverse_direction=False)
    for contour in _expanded_contours(glyph, glyphs_by_index):
        started = False
        for command, values in contour:
            if command == "m":
                quadratic_pen.moveTo((values[0], values[1]))
                started = True
            elif command == "l":
                quadratic_pen.lineTo((values[0], values[1]))
            elif command == "c":
                quadratic_pen.curveTo(
                    (values[0], values[1]),
                    (values[2], values[3]),
                    (values[4], values[5]),
                )
        if started:
            quadratic_pen.closePath()
    return pen.glyph()


def _expanded_contours(
    glyph: SfdGlyph,
    glyphs_by_index: dict[int, SfdGlyph],
    seen: frozenset[int] = frozenset(),
) -> list[list[tuple[str, tuple[float, ...]]]]:
    if glyph.index in seen:
        return []
    contours = list(glyph.contours)
    for reference_index, transform in glyph.references:
        referenced = glyphs_by_index.get(reference_index)
        if referenced is None:
            continue
        for contour in _expanded_contours(
            referenced, glyphs_by_index, seen | {glyph.index}
        ):
            contours.append(_transform_contour(contour, transform))
    return contours


def _transform_contour(
    contour: list[tuple[str, tuple[float, ...]]],
    transform: tuple[float, float, float, float, float, float],
) -> list[tuple[str, tuple[float, ...]]]:
    result = []
    for command, values in contour:
        if command in {"m", "l"}:
            result.append(
                (command, _transform_point((values[0], values[1]), transform))
            )
        else:
            p1 = _transform_point((values[0], values[1]), transform)
            p2 = _transform_point((values[2], values[3]), transform)
            p3 = _transform_point((values[4], values[5]), transform)
            result.append((command, (*p1, *p2, *p3)))
    return result


def _transform_point(
    point: tuple[float, float],
    transform: tuple[float, float, float, float, float, float],
) -> tuple[float, float]:
    x, y = point
    a, b, c, d, e, f = transform
    return (a * x + c * y + e, b * x + d * y + f)
