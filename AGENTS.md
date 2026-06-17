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
- Mono output advance widths must remain consistent with the current Noto mono sources: half-width characters use 600 units and CJK/fullwidth/emoji characters use 1000 units.
- `pypy3 src/download-noto.py` uses the latest `notofonts/notofonts.github.io` monthly build as the main Noto source set by downloading that repository tag zip and extracting ordinary Noto family TTF files, preferring `googlefonts/ttf` and falling back to `hinted/ttf` or `full/ttf` when needed; large CJK fonts come from `notofonts/noto-cjk` Sans/Serif static regional archives, and Noto Emoji comes from `googlefonts/noto-emoji`. Source discovery filters to requested static styles and treats uncertain style names as `full`-only sources. Use `--monthly-tag <tag>` only when reproducing a specific month.
- Extra fallback downloads currently include Jigmo (CC0 1.0), Padauk, Scheherazade New, Harmattan, BabelStone/TangutYinchuan/HanaMin/Scriptwide/Plangothic/Cascadia/Charis/Doulos/Junicode/Kanchenjunga/Kedebideri/Khitan/DivesAkuru/Abydos and other entries listed in `src/uninoto/download_noto.py`; update `LICENSE`, `README.md`, and `README_zh_CN.md` whenever adding or removing a source.
- The default merge writes regular outputs under `fonts\merged\regular\`; additional styles use `fonts\merged\bold\`, `fonts\merged\italic\`, `fonts\merged\bolditalic\`, and `fonts\merged\full\`. Each style writes separate sans, serif, mono, extra, and last_resort output families. A family is written to the no-suffix file only when all selected codepoints fit within the TTF glyph limit; otherwise it is split directly into numbered files such as `uninoto_sans1.ttf`, `uninoto_sans2.ttf`, and so on. Extra outputs are written as `uninoto_extra.ttf`, or split into `uninoto_extra1.ttf`, `uninoto_extra2.ttf`, and so on when needed. Last Resort diagnostic prompts are written only for `full` as `uninoto_last_resort.ttf`. Source paths that clearly contain sans go to sans; paths that clearly contain serif/serief go to serif; paths that clearly contain mono go to mono first, then mono uses non-serif sources as fallback with controlled advance widths. Sources that are not clearly sans or serif are neutral and go to extra instead of the sans/serif families. Extra contains neutral coverage needed by either sans or serif plus the sans/serif coverage difference from clearly classified sources.

## Build And Audit Commands

- Install dependencies: `pypy3 -m pip install -r requirements.txt`
- Format Python after edits: `pypy3 -m black src/`
- Syntax check: `pypy3 -m pyright`
- Download Noto fonts: `pypy3 src/download-noto.py`
- `pypy3 src/download-noto.py` supports resume, configurable concurrency, and environment proxy settings.
- Extract already downloaded Noto CJK, Noto Emoji, and fallback archives: `pypy3 src/download-noto.py --extract-existing`
- Merge planes: `pypy3 src/merge.py` (`--family sans`, `--family serif`, `--family mono`, `--family extra`, or `--family last_resort` limits output to one family)
- Merge all configured styles and families with worker processes: `pypy3 src/merge-all.py` (default worker cap is 8; pass `--jobs <n>` to override). `merge-all.py` runs style/family tasks independently and strips layout/hinting metadata before direct numbered output splitting.
- Merge commands clean the target style/family's existing merged fonts and reports before regenerating them so stale split outputs do not remain.
- Merges can take several minutes because they subset and write many large fonts; use a long command timeout, or limit by `--family`/style when only a targeted check is needed.
- `pypy3 src/merge.py` writes style-scoped reports such as `fonts\reports\regular\sans-missing-visible.csv`, `fonts\reports\regular\serif-missing-visible.csv`, and `fonts\reports\regular\mono-missing-visible.csv`. The sans and serif missing reports use the full fallback output set and include shared extra output coverage; `sans-missing-visible-without_extra.csv` and `serif-missing-visible-without_extra.csv` use only the sans/serif outputs without `uninoto_extra*`; mono reports only use mono outputs. Extra and last_resort outputs do not get separate missing-visible reports.

## CJK Extension B+ And Recent Script Sources

Split outputs are capacity-packed rather than split by Unicode plane.

- **Jigmo** (`https://kamichikoichi.github.io/jigmo/Jigmo-20250912.zip`, CC0 1.0) is already wired as a fallback source and covers many Unicode 17 CJK extension characters through Extension J.
- **Padauk** (OFL 1.1) is already wired for Myanmar and Myanmar Extended-C coverage.
- **Scheherazade New** and **Harmattan** (OFL 1.1) are already wired for Arabic supplement/Ajami coverage.
- `notofonts/gurung-khema` and `notofonts/ol-onal` currently have no Regular/static TTF release assets, but their SFD sources contain correct encoded glyphs and are built into minimal static TTFs by `src/uninoto/sfd_to_ttf.py`. For other Noto source repositories, do not add them to the downloader unless a direct font artifact appears or the project gains a source-build path for that source format.

After adding or changing any fallback font source, run `pypy3 src/download-noto.py --extract-existing` if archives are already present, then `pypy3 src/merge.py` to regenerate outputs and reports.

## Known Behaviors

- TTF glyph count is limited to 65535. `src/uninoto/merge.py` preflights each category and checks the final glyph count after writing.
- As of the 2026-06-17 merge with explicit styles and `full`, Unicode 17 visible codepoint coverage is: `regular` sans/serif with extra 96293/159631 (60.323%), `bold` sans/serif with extra 55727/159631 (34.910%), `italic` sans/serif with extra 3164/159631 (1.982%), `bolditalic` sans/serif with extra 3125/159631 (1.958%), and `full` sans/serif with extra 159525/159631 (99.934%) plus mono 159430/159631 (99.874%). Remaining `full` sans/serif visible gaps are Tulu-Tigalari, Duployan, and three Egyptian Hieroglyphs Extended-A codepoints. Check `fonts/reports/*-missing-visible.csv` before claiming full coverage.
- Do not use GNU uninoto; the user explicitly rejected pixel/bitmap fonts.
