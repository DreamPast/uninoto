from __future__ import annotations

import argparse
import concurrent.futures
import os
from dataclasses import dataclass
from pathlib import Path

from .font_io import discover_fonts
from .merge import (
    Options,
    merge_family_outputs,
    project_mergeable_codepoint_filter,
    remove_stale_extra_reports,
    style_options_for,
    write_style_reports,
)
from .planes import (
    FONT_FAMILIES,
    FONT_STYLES,
    FontFamily,
    FontStyle,
    parse_font_family,
    parse_font_style,
)


@dataclass(frozen=True)
class MergeTask:
    input: Path
    output: Path
    family: FontFamily
    style: FontStyle
    unicode_data: Path


def parse_styles(value: str) -> tuple[FontStyle, ...]:
    if value == "all":
        return FONT_STYLES
    return (parse_font_style(value, "--style"),)


def merge_task(task: MergeTask) -> str:
    codepoint_filter = project_mergeable_codepoint_filter(task.unicode_data)
    fonts = discover_fonts(task.input, codepoint_filter, task.style)
    if not fonts:
        raise ValueError(f"no {task.style} fonts found below {task.input}")
    print(
        f"style {task.style}, family {task.family}: discovered {len(fonts)} candidate fonts"
    )
    merge_family_outputs(
        task.family,
        fonts,
        task.output,
        codepoint_filter,
        task.style,
        preserve_source_metadata=False,
    )
    return f"{task.style}/{task.family}"


def parse_args() -> tuple[Options, int]:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="fonts/noto")
    parser.add_argument("--output", default="fonts/merged")
    parser.add_argument("--family")
    parser.add_argument(
        "--style",
        default="all",
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
    parser.add_argument(
        "--jobs",
        type=int,
        default=0,
        help="Worker process count. Defaults to min(8, CPU count, task count).",
    )
    args = parser.parse_args()
    if args.include_marks and args.exclude_marks:
        parser.error("--include-marks and --exclude-marks cannot be used together")
    options = Options(
        input=Path(args.input),
        output=Path(args.output),
        family=parse_font_family(args.family, "--family") if args.family else None,
        styles=parse_styles(args.style),
        missing_output=Path(args.missing_output),
        missing_summary_output=(
            Path(args.missing_summary_output) if args.missing_summary_output else None
        ),
        include_marks=not bool(args.exclude_marks),
        derived_age=Path(args.derived_age),
        unicode_data=Path(args.unicode_data),
    )
    return options, args.jobs


def default_jobs(task_count: int) -> int:
    return max(1, min(8, os.cpu_count() or 1, task_count))


def main() -> None:
    options, requested_jobs = parse_args()
    codepoint_filter = project_mergeable_codepoint_filter(options.unicode_data)
    families: list[FontFamily] = (
        [options.family] if options.family is not None else list(FONT_FAMILIES)
    )
    style_options = {
        style: style_options_for(options, style) for style in options.styles
    }
    for item in style_options.values():
        remove_stale_extra_reports(item)
    tasks = [
        MergeTask(
            input=options.input,
            output=style_options[style].output,
            family=family,
            style=style,
            unicode_data=options.unicode_data,
        )
        for style in options.styles
        for family in families
    ]
    jobs = requested_jobs if requested_jobs > 0 else default_jobs(len(tasks))
    print(f"merge tasks: {len(tasks)}, worker processes: {jobs}")
    with concurrent.futures.ProcessPoolExecutor(max_workers=jobs) as executor:
        futures = [executor.submit(merge_task, task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            print(f"completed {future.result()}")
    for style in options.styles:
        write_style_reports(style_options[style], families)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
