# AGENTS.md

## Project Notes

- Use the Python scripts in `src/` as the implementation.
- Run scripts with `pypy3 src/<script>.py`.
- Prefer `fontTools` APIs for cmap inspection, subsetting, merging, and font writing.

## Font Source Policy

- Source discovery intentionally accepts Regular/static TTF and OTF fonts:
  - reject `Bold`, `Black`, `Oblique`, `Medium`, `Light`, `Thin`;
  - fonts with inherent italic glyphs (not differential italic variants) are also accepted;
  - reject variable fonts: `-VF`, bracket axes such as `[wght]`, and `/Variable/` paths.
- Unassigned codepoints and Private Use codepoints must not enter merged fonts and must not be counted in coverage or missing checks.
- `pypy3 src/download-noto.py` uses the latest `notofonts/notofonts.github.io` monthly build as the main Noto source set by downloading that repository tag zip and extracting ordinary Noto family TTF files, preferring `googlefonts/ttf` and falling back to `hinted/ttf` or `full/ttf` when needed; large CJK fonts come from `notofonts/noto-cjk` Sans/Serif static regional archives, and Noto Emoji comes from `googlefonts/noto-emoji`. Source discovery still filters to Regular/static fonts. Use `--monthly-tag <tag>` only when reproducing a specific month.
- Extra fallback downloads currently include Jigmo (CC0 1.0), Padauk, Scheherazade New, Harmattan, BabelStone/HanaMin/Scriptwide/Cascadia/Charis/Doulos/Junicode/Kanchenjunga/Kedebideri/Khitan/Abydos and other entries listed in `src/uninoto/download_noto.py`; update `LICENSE`, `README.md`, and `README_zh_CN.md` whenever adding or removing a source.
- The default merge writes separate sans, serif, mono, and last output families: `uninoto_sans.ttf`, `uninoto_sans_upper1.ttf`, `uninoto_sans_upper2.ttf`, `uninoto_serif.ttf`, `uninoto_serif_upper1.ttf`, `uninoto_serif_upper2.ttf`, `uninoto_mono.ttf`, `uninoto_mono_upper1.ttf`, `uninoto_mono_upper2.ttf`, and either `uninoto_last.ttf` or split `uninoto_last1.ttf` / `uninoto_last2.ttf`. BMP outputs cover `<= U+FFFF`; sans/serif/mono upper outputs are capacity-packed up to 60000 codepoints before overflowing to `upper2`. Source paths that clearly contain sans go to sans; paths that clearly contain serif/serief go to serif; paths that clearly contain mono go to mono first, then mono uses non-serif sources as fallback with controlled advance widths. Neutral sources are included as sans/serif fallback. Last only contains the sans/serif coverage difference, not codepoints already covered by both.

## Build And Audit Commands

- Install dependencies: `pypy3 -m pip install -r requirements.txt`
- Format Python after edits: `pypy3 -m black src/`
- Syntax check: `pypy3 -m pyright`
- Download Noto fonts: `pypy3 src/download-noto.py`
- `pypy3 src/download-noto.py` supports resume, configurable concurrency, and environment proxy settings.
- Extract already downloaded Noto CJK, Noto Emoji, and fallback archives: `pypy3 src/download-noto.py --extract-existing`
- Merge planes: `pypy3 src/merge.py` (`--family sans`, `--family serif`, `--family mono`, or `--family last` limits output to one family)
- `pypy3 src/merge.py` writes `fonts\reports\sans-missing-visible.csv`, `fonts\reports\serif-missing-visible.csv`, and `fonts\reports\mono-missing-visible.csv`. The sans and serif missing reports use the full fallback output set and include shared last output coverage; `fonts\reports\sans-missing-visible-without_last.csv` and `fonts\reports\serif-missing-visible-without_last.csv` use only the sans/serif outputs without `uninoto_last*`; mono reports only use mono outputs. Last outputs do not get separate reports.
- Merge outputs `fonts\reports\sans-plane-font-coverage.csv`, `fonts\reports\serif-plane-font-coverage.csv`, and `fonts\reports\mono-plane-font-coverage.csv` as glyph source provenance for the sans/serif/mono outputs; do not scan any external font directories for this report.

## CJK Extension B+ And Recent Script Sources

The upper-plane outputs are capacity-packed rather than split by Unicode plane.

- **Jigmo** (`https://kamichikoichi.github.io/jigmo/Jigmo-20250912.zip`, CC0 1.0) is already wired as a fallback source and covers many Unicode 17 CJK extension characters through Extension J.
- **Padauk** (OFL 1.1) is already wired for Myanmar and Myanmar Extended-C coverage.
- **Scheherazade New** and **Harmattan** (OFL 1.1) are already wired for Arabic supplement/Ajami coverage.
- Public OFL source repositories exist for newer Noto scripts such as `notofonts/gurung-khema` and `notofonts/ol-onal`, but they currently have no Regular/static TTF release assets. Do not add them to the downloader unless a direct font artifact appears or the project gains a source-build pipeline.

After adding or changing any fallback font source, run `pypy3 src/download-noto.py --extract-existing` if archives are already present, then `pypy3 src/merge.py` to regenerate outputs and reports.

## Known Behaviors

- TTF glyph count is limited to 65535. `src/uninoto/merge.py` preflights each category and checks the final glyph count after writing.
- As of the 2026-06-14 merge with Jigmo/Padauk/Scheherazade New/Harmattan, Unicode 17 visible coverage is: sans with last 159018/159563 (99.656%), serif with last 159018/159563 (99.656%), mono 155120/159563 (97.252%). Remaining sans/serif visible gaps are concentrated in Tangut Components Supplement, Garay, Tulu-Tigalari, Tolong Siki, Tai Yo, Ol Onal, Gurung Khema, Sidetic, Tangut Supplement, Dives Akuru, Arabic Presentation Forms-A, and Syriac Supplement. Check `fonts/reports/*-missing-visible.csv` before claiming full coverage.
- Do not use GNU uninoto; the user explicitly rejected pixel/bitmap fonts.
