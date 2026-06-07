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

## CJK Extension B+ Font Sources

The upper-plane outputs are capacity-packed rather than split by Unicode plane. The existing Noto Sans CJK sources only cover up to Extension A, so a key source for CJK Extension B (U+20000..U+2A6DF) would be:

- **Han Nom B** (SIL OFL 1.1) from the Nom Foundation: covers CJK Extension B (U+20000..U+2A6DF) with ~42,000 characters
  - URL: `https://raw.githubusercontent.com/nomfoundation/hannom/master/fonts/HanNomB.ttf`
  - Download to: `fonts/noto/fallback/HanNomB.ttf`
- For Extensions C-I and G-H: no free commercial font currently exists

After adding Han Nom B, run `pypy3 src/merge.py` to regenerate the upper-plane outputs.

## Known Behaviors

- TTF glyph count is limited to 65535. `src/uninoto/merge.py` preflights each category and checks the final glyph count after writing.
- Some visible Unicode characters remain uncovered, especially when restricted to Regular/static Noto sources. Check `fonts/reports/*-missing-visible.csv` before claiming full coverage.
- Do not use GNU uninoto; the user explicitly rejected pixel/bitmap fonts.
