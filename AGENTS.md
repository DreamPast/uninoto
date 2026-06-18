# AGENTS.md

## Project Notes

- Use the Python scripts in `src/` as the implementation.
- Run scripts with `pypy3 src/<script>.py`.
- Prefer `fontTools` APIs for cmap inspection, subsetting, merging, and font writing.
- Project outputs prioritize broad visible-character fallback coverage over
  shaping, ligatures, layout, hinting, or typographic quality. Users who need
  those features should use the official source fonts listed in the README.

## Commit Message Guidelines

- When creating a commit, use the first line as a concise summary.
- Starting from the second line, explain the purpose and impact of the change.
  Keep this description at a higher level, such as improved coverage,
  performance, reliability, or maintainability, instead of listing exactly
  which code paths were edited.

## Font Source Policy

- Source discovery intentionally accepts static TTF and OTF fonts by requested style:
  - `regular`: explicitly Regular style names only;
  - `bold`: Bold/Black/ExtraBold/SemiBold/DemiBold only;
  - `italic`: Italic/Oblique only;
  - `bolditalic`: Bold Italic only;
  - `full`: explicitly Regular plus uncertain style names for maximum regular-style coverage;
  - reject variable fonts: `-VF`, bracket axes such as `[wght]`, and `/Variable/` paths.
- `regular`, `bold`, `italic`, and `bolditalic` outputs are merged independently. Each standard style only uses explicitly matching sources and must not fall back to or mix in other style variants.
- Unassigned codepoints and Private Use codepoints must not enter merged fonts and must not be counted in coverage or missing checks.
- Added fallback sources must provide correct script-specific glyphs for their mapped codepoints. Do not use block-level fallback, codepoint-box, last-resort, placeholder, or other generic missing-glyph indicator fonts as coverage sources.
- `NOTES.md` records previously explored font sources and the conclusions from those checks. Review it before re-exploring candidates, and append future font-source investigations there, including rejected sources and the reason for each decision.
- Generated fonts strip layout and hinting tables before writing. Remove unencoded orphan glyphs and stale cmap references; keep placeholder glyphs such as `.notdef` and glyphs required as composite components. Write `.notdef` as a visible Noto-style fallback box without mapping it from any Unicode codepoint.
- Mono outputs must use mono-classified source fonts only. Source glyphs are eligible for mono only when their original advance width already matches the current Noto mono metrics: half-width characters use 600 units and CJK/fullwidth/emoji characters use 1000 units. Do not modify source glyph widths to make them fit.
- `pypy3 src/download-noto.py` uses the latest `notofonts/notofonts.github.io` monthly build as the main Noto source set by downloading that repository tag zip and extracting ordinary Noto family TTF files, preferring `googlefonts/ttf` and falling back to `hinted/ttf` or `full/ttf` when needed; large CJK fonts come from `notofonts/noto-cjk` Sans/Serif static regional archives, and Noto Emoji comes from `googlefonts/noto-emoji`. Source discovery filters to requested static styles and treats uncertain style names as `full`-only sources. Use `--monthly-tag <tag>` only when reproducing a specific month.
- Extra fallback downloads currently include Jigmo (CC0 1.0), Padauk, Scheherazade New, Harmattan, BabelStone/TangutYinchuan/HanaMin/Scriptwide/Plangothic/Cascadia/Charis/Doulos/Junicode/Kanchenjunga/Kedebideri/Khitan/DivesAkuru/Abydos and other entries listed in `src/uninoto/download_noto.py`; update `LICENSE`, `README.md`, and `README_zh_CN.md` whenever adding or removing a source.
- The default merge writes regular outputs under `fonts\merged\regular\`; additional styles use `fonts\merged\bold\`, `fonts\merged\italic\`, `fonts\merged\bolditalic\`, and `fonts\merged\full\`. Each style writes separate sans, serif, mono, and extra output families. A family is written to the no-suffix file only when all selected codepoints fit within the TTF glyph limit; otherwise it is split directly into numbered files such as `uninoto_sans1.ttf`, `uninoto_sans2.ttf`, and so on. Extra fallback outputs are split by target family: `uninoto_sans_extra*.ttf` contains neutral-source codepoints missing from sans plus serif-selected codepoints missing from sans, and `uninoto_serif_extra*.ttf` contains neutral-source codepoints missing from serif plus sans-selected codepoints missing from serif. Source paths that clearly contain sans go to sans; paths that clearly contain serif/serief go to serif; paths that clearly contain mono go to mono only. Sources that are not clearly sans, serif, or mono are neutral and go to the directional extra outputs only when the target family does not already cover the codepoint.

## Build And Audit Commands

- Install dependencies: `pypy3 -m pip install -r requirements.txt`
- Format Python after edits: `pypy3 -m black src/`
- Syntax check: `pypy3 -m pyright`
- Download Noto fonts: `pypy3 src/download-noto.py`
- `pypy3 src/download-noto.py` supports resume, configurable concurrency, and environment proxy settings.
- Extract already downloaded Noto CJK, Noto Emoji, and fallback archives: `pypy3 src/download-noto.py --extract-existing`
- Merge planes: `pypy3 src/merge.py` (`--family sans`, `--family serif`, `--family mono`, or `--family extra` limits output to one family)
- Merge all configured styles and families with worker processes: `pypy3 src/merge-all.py` (default worker cap is 8; pass `--jobs <n>` to override). `merge-all.py` runs style/family tasks independently and strips layout/hinting metadata before direct numbered output splitting.
- Build full-style sans/extra per-plane outputs: `pypy3 src/full-per-plane.py`. This reads `fonts\merged\full\uninoto_sans*.ttf` and `fonts\merged\full\uninoto_sans_extra*.ttf`, gives sans coverage priority over sans_extra, removes stale `fonts\merged\full_per_plane\plane*.ttf` and `fonts\merged\full_per_plane\uninoto_plane*.ttf`, and writes only non-empty planes as `uninoto_plane0.ttf`, `uninoto_plane1.ttf`, and so on.
- Merge commands clean the target style/family's existing merged fonts and reports before regenerating them so stale split outputs do not remain.
- Merges can take several minutes because they subset and write many large fonts; use a long command timeout, or limit by `--family`/style when only a targeted check is needed.
- `pypy3 src/merge.py` writes style-scoped reports such as `fonts\reports\regular\sans-missing-visible.csv`, `fonts\reports\regular\serif-missing-visible.csv`, and `fonts\reports\regular\mono-missing-visible.csv`. The sans and serif missing reports include their directional extra output coverage (`uninoto_sans_extra*` for sans and `uninoto_serif_extra*` for serif); `sans-missing-visible-without_extra.csv` and `serif-missing-visible-without_extra.csv` use only the sans/serif outputs without directional extra files. Mono reports only use mono outputs. Extra outputs do not get separate missing-visible reports.

## CJK Extension B+ And Recent Script Sources

Standard merge outputs are capacity-packed rather than split by Unicode plane. Use `pypy3 src/full-per-plane.py` when a temporary full-style sans/extra fallback set split by Unicode plane is needed.

- **Jigmo** (`https://kamichikoichi.github.io/jigmo/Jigmo-20250912.zip`, CC0 1.0) is already wired as a fallback source and covers many Unicode 17 CJK extension characters through Extension J.
- **Padauk** (OFL 1.1) is already wired for Myanmar and Myanmar Extended-C coverage.
- **Scheherazade New** and **Harmattan** (OFL 1.1) are already wired for Arabic supplement/Ajami coverage.
- `notofonts/gurung-khema` and `notofonts/ol-onal` currently have no Regular/static TTF release assets, but their SFD sources contain correct encoded glyphs and are built into minimal static TTFs by `src/uninoto/sfd_to_ttf.py`. For other Noto source repositories, do not add them to the downloader unless a direct font artifact appears or the project gains a source-build path for that source format.

After adding or changing any fallback font source, run `pypy3 src/download-noto.py --extract-existing` if archives are already present, then `pypy3 src/merge.py` to regenerate outputs and reports.

## Known Behaviors

- TTF glyph count is limited to 65535. `src/uninoto/merge.py` preflights each category and checks the final glyph count after writing.
- As of the 2026-06-17 merge with explicit styles, de-duplicated directional extra, and mono width eligibility, Unicode 17 non-control, non-whitespace visible codepoint coverage is: `regular` sans with extra 96290/159612 (60.328%), `regular` serif with extra 96292/159612 (60.329%), `regular` mono 35114/159612 (22.000%), `bold` sans/serif with extra 55727/159612 (34.914%), `bold` mono 35118/159612 (22.002%), `italic` sans/serif with extra 3164/159612 (1.982%), `italic` mono 26/159612 (0.016%), `bolditalic` sans/serif with extra 3125/159612 (1.958%), `bolditalic` mono 26/159612 (0.016%), `full` sans with directional extra 159522/159612 (99.944%), `full` serif with directional extra 159524/159612 (99.945%), and `full` mono 35119/159612 (22.003%). Remaining `full` sans/serif visible gaps are recorded in `fonts\reports\full\*-missing-visible.csv`. Check `fonts/reports/*-missing-visible.csv` before claiming full coverage.
- Do not use GNU uninoto; the user explicitly rejected pixel/bitmap fonts.
