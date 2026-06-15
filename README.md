# uninoto — Universal Unicode Coverage Font

**English** | [简体中文](./README_zh_CN.md)

uninoto aims to create a universal font family capable of displaying the vast majority of visible Unicode characters. Using Google Noto as the primary font family combined with additional free-to-use fallback fonts, it achieves near-complete coverage of visible characters.

## Font Outputs

The project produces three font families: `sans` (sans-serif), `serif`, and `mono` (monospace), derived from Google Noto Fonts. CJK ideographs default to **Simplified Chinese** glyph forms where available.

Outputs are grouped by style under `fonts/merged/<style>/`. The default build
creates `regular`; additional supported style builds are `bold`, `italic`,
`bolditalic`, and `full`. Static fonts with uncertain style naming are used by
`full`, not by `regular`.

Each family may be split across multiple TTF files due to the 65535 glyph limit per TTF:

- Files without a suffix contain all covered codepoints when they fit in one TTF
- Non-full layout-preserving outputs split by source/region/codepoint groups.
  Simple CJK regional groups use suffixes such as `_sc`, `_tc`, `_jp`, `_kr`;
  other split groups use numeric suffixes such as `_1`, `_2`, `_3`
- `full` outputs use compact BMP/upper splitting: `_upper` when upper-plane
  codepoints fit in one file, or `_upper1`, `_upper2`, and so on when needed
- Empty split buckets are skipped

`uninoto_last.ttf` contains additional codepoints from fallback fonts that complement both `sans` and `serif`.

The `mono` family uses normalized advance widths: half-width (600) or full-width (1000).

Stripped outputs prune unencoded orphan glyphs before writing. Non-full
layout-preserving outputs keep source layout/hint/metric metadata and may retain
no-cmap glyphs referenced by OpenType layout tables, hinting, or composites.

Output file structure:

| Path | Variant | Notes |
|------|---------|-------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans base | Contains all Sans codepoints when they fit |
| `fonts/merged/<style>/uninoto_sans_<region>.ttf` | Sans regional split | Non-full output for a simple region such as `sc`, `tc`, `jp`, or `kr` |
| `fonts/merged/<style>/uninoto_sans_<N>.ttf` | Sans numbered split | Non-full output when a split group has no concise region name |
| `fonts/merged/<style>/uninoto_serif_<region>.ttf` | Serif regional split | Same naming rule as Sans |
| `fonts/merged/<style>/uninoto_mono_<N>.ttf` | Mono numbered split | Same naming rule as Sans |
| `fonts/merged/<style>/uninoto_last_<N>.ttf` | Sans/Serif shared fallback split | Non-full last output, numbered when no concise region applies |
| `fonts/merged/full/uninoto_<family>_upper<N>.ttf` | Full upper split | `full` keeps compact BMP/upper split naming |

Coverage as of the 2026-06-15 merge against Unicode 17 visible non-mark
characters (157,088 total):

| Style | Sans + last | Sans | Serif + last | Serif | Mono |
|-------|-------------|------|--------------|-------|------|
| `regular` | 79,004 (50.293%) | 71,214 (45.334%) | 79,004 (50.293%) | 61,390 (39.080%) | 71,630 (45.599%) |
| `bold` | 54,574 (34.741%) | 53,934 (34.334%) | 54,574 (34.741%) | 51,155 (32.565%) | 54,196 (34.500%) |
| `italic` | 2,853 (1.816%) | 2,794 (1.779%) | 2,853 (1.816%) | 2,722 (1.733%) | 2,794 (1.779%) |
| `bolditalic` | 2,814 (1.791%) | 2,755 (1.754%) | 2,814 (1.791%) | 2,722 (1.733%) | 2,755 (1.754%) |
| `full` | 156,539 (99.651%) | 152,703 (97.209%) | 156,539 (99.651%) | 143,723 (91.492%) | 152,703 (97.209%) |

## Font Sources

uninoto merges static TTF/OTF fonts by requested style. Variable fonts are
excluded. The standard style selectors only accept explicitly matching style
sources:

- `regular`: explicitly regular static sources
- `bold`: bold/black/extra-bold/semi-bold sources
- `italic`: italic/oblique sources
- `bolditalic`: bold italic sources
- `full`: explicitly regular plus uncertain static sources, for maximum regular-style coverage

The `regular`, `bold`, `italic`, and `bolditalic` outputs are merged
independently. Each standard style only uses explicitly matching sources and
does not fall back to other style variants.

### Primary Source — Noto Fonts

- [Noto Monthly Build](https://github.com/notofonts/notofonts.github.io) — ordinary Noto family TTFs from the monthly release tag
- [Noto CJK](https://github.com/notofonts/noto-cjk) — static regional CJK packages (SC/TC/JP/KR/HK)
- [Noto Emoji](https://github.com/googlefonts/noto-emoji)

### Fallback Sources

| Font | Purpose | License |
|------|---------|---------|
| [BabelStone](https://www.babelstone.co.uk/Fonts/) | Various ancient scripts and rare characters | OFL 1.1 / Arphic Public License for BabelStone Han |
| [Jigmo](https://kamichikoichi.github.io/jigmo/) | Unicode 17 CJK extensions through Extension J | CC0 1.0 |
| [Padauk](https://software.sil.org/padauk/) | Myanmar script, including Myanmar Extended-C | OFL 1.1 |
| [Scheherazade New](https://software.sil.org/scheherazade/) | Arabic script supplement | OFL 1.1 |
| [Harmattan](https://software.sil.org/harmattan/) | Ajami / West African Arabic script supplement | OFL 1.1 |
| [HanaMin (Hanazono)](https://github.com/cjkvi/HanaMinAFDKO) | CJK Extension B/C ideographs | GlyphWiki / OFL 1.1 |
| [Scriptwide Sans CJK](https://github.com/scriptwide-fonts/scriptwide-sans-cjk) | Supplementary CJK coverage | OFL 1.1 |
| [Cascadia Code](https://github.com/microsoft/cascadia-code) | Monospace font supplement | OFL 1.1 |
| [Charis SIL](https://software.sil.org/charis/) | Serif IPA and extended Latin | OFL 1.1 |
| [Doulos SIL](https://software.sil.org/doulos/) | Serif IPA and phonetic notation | OFL 1.1 |
| [Junicode](https://github.com/psb1558/Junicode-font) | Medieval Latin and scholarly characters | OFL 1.1 |
| [Kanchenjunga](https://github.com/silnrsi/font-kanchenjunga) | Kirat Rai script | OFL 1.1 |
| [Kedebideri](https://software.sil.org/kedebideri/) | Zaghawa Beria script | OFL 1.1 |
| [Fairfax HD](https://www.kreativekorp.com/software/fonts/fairfaxhd/) | UCSUR and scholarly characters | OFL 1.1 |
| [Khitan Small Script](https://github.com/notofonts/khitan-small-script) | Khitan small script | OFL 1.1 |
| [Abydos](https://greekfonts.teilar.gr/) | Egyptian Hieroglyphs supplement | Free use |

### Investigated Sources Not Yet Included

The remaining visible gaps are concentrated in recently encoded scripts and
Tangut-related blocks. Public OFL source repositories exist for some newer Noto
scripts such as [Gurung Khema](https://github.com/notofonts/gurung-khema) and
[Ol Onal](https://github.com/notofonts/ol-onal), but they currently do not
publish regular/static TTF release files. They are not downloaded by default
until a direct font artifact is available or a source build pipeline is added.

As of the 2026-06-14 audit, the largest remaining `sans`/`serif` gaps are
Tangut Components Supplement, Garay, Tulu-Tigalari, Tolong Siki, Tai Yo,
Ol Onal, Gurung Khema, Sidetic, Tangut Supplement, Dives Akuru, Arabic
Presentation Forms-A, and Syriac Supplement.

## Building from Source

### Prerequisites

- Python 3.11+ (PyPy 3.11 recommended)
- Windows: [7-Zip](https://www.7-zip.org/) required for RPM extraction

### Steps

```powershell
# 1. Install dependencies
pypy3 -m pip install -r requirements.txt

# 2. Download font sources (concurrent download with resume support, 8 threads default)
pypy3 src/download-noto.py

# Optional: extract already downloaded archives without re-downloading
pypy3 src/download-noto.py --extract-existing

# 3. Merge regular fonts and write audit reports
pypy3 src/merge.py

# Optional: merge another style or all configured styles
pypy3 src/merge.py --style bold
pypy3 src/merge.py --style all

# Optional: merge all configured styles/families with worker processes
# Defaults to 4 workers to reduce memory/IO contention while preserving layout data
pypy3 src/merge-all.py
```

### Audit Reports

After merging, the following reports are written to `fonts/reports/<style>/`:

- `sans-missing-visible.csv` / `serif-missing-visible.csv` / `mono-missing-visible.csv` — visible codepoints still uncovered after merging
- `sans-missing-visible-without_last.csv` / `serif-missing-visible-without_last.csv` — missing codepoints excluding `uninoto_last*` coverage

## License

### Build Scripts

The build scripts under `src/` are released under the **MIT License**.

### Generated Fonts

The merged output fonts (`fonts/merged/<style>/uninoto_*.ttf`) are composite/derivative
works built from the source fonts listed in [LICENSE](./LICENSE). Source font
licenses and notices are retained; generated font metadata points back to this
repository's license inventory.

### Source Font Licenses

License texts, license references, and source notices for the source fonts are included in [LICENSE](./LICENSE):

- **SIL Open Font License 1.1** (Noto families, most BabelStone script fonts, Padauk, Scheherazade New, Harmattan, Charis SIL, Doulos SIL, Junicode, Kanchenjunga, Kedebideri, Fairfax HD, Scriptwide Sans CJK, Cascadia Code, etc.)
- **CC0 1.0 Universal** (Jigmo)
- **Arphic Public License** (BabelStone Han)
- **GlyphWiki License** (HanaMinB, HanaMinC)
- **George Douros free-use notice** (Abydos)

See [LICENSE](./LICENSE) for the full source font inventory and corresponding license terms.
