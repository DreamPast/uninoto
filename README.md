# uninoto: Unicode coverage font

**English** | [简体中文](./README_zh_CN.md)

uninoto builds fallback fonts for visible Unicode characters. It starts with
Google Noto, then adds other redistributable fonts where Noto does not yet have
coverage.

The goal is basic display coverage: make missing characters show up as glyphs
instead of blanks. The generated fonts do not promise correct shaping,
ligatures, script-specific layout, kerning, hinting, or professional typography.
For that, use the official source fonts listed below.

Use uninoto as a fallback font. It is meant to fill gaps after an application or
document has already tried its preferred fonts.

## Font outputs

The build writes three families: `sans`, `serif`, and `mono`. CJK ideographs use
Simplified Chinese forms where those forms are available.

Outputs are grouped by style under `fonts/merged/<style>/`. The default build
creates `regular`; additional supported style builds are `bold`, `italic`,
`bolditalic`, and `full`. Static fonts with uncertain style naming are used by
`full`, not by `regular`.

Each family may be split across several TTF files because one TTF can contain at
most 65,535 glyphs:

- Files without a suffix contain all covered codepoints when they fit in one TTF
- When needed, files without a suffix cover U+0000 through U+FFFF (BMP)
- If all codepoints above U+FFFF fit in one additional TTF, they are written as `_upper`
- If `_upper` would exceed the TTF glyph limit, upper-plane codepoints are split as `_upper1`, `_upper2`, and so on
- Empty split buckets are skipped

`uninoto_last.ttf` contains codepoints from fallback fonts that fill gaps shared
by `sans` and `serif`.

The `mono` family uses normalized advance widths: half-width (600) or full-width (1000).

Generated fonts are stripped of layout and hinting tables before writing.
Unencoded orphan glyphs are pruned, while placeholders such as `.notdef` and
glyphs required as composite components are kept. The `.notdef` glyph is written
as a visible Noto-style fallback box and is not mapped from any Unicode
codepoint.

Output structure:

| Path | Variant | Notes |
|------|---------|-------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans base | Contains all Sans codepoints when they fit; otherwise BMP |
| `fonts/merged/<style>/uninoto_sans_upper.ttf` | Sans upper | Written when all Sans upper-plane codepoints fit in one extra file |
| `fonts/merged/<style>/uninoto_sans_upper<N>.ttf` | Sans upper bucket N | Written as needed when `_upper` would exceed the glyph limit |
| `fonts/merged/<style>/uninoto_serif.ttf` | Serif base | Contains all Serif codepoints when they fit; otherwise BMP |
| `fonts/merged/<style>/uninoto_serif_upper.ttf` | Serif upper | Written when all Serif upper-plane codepoints fit in one extra file |
| `fonts/merged/<style>/uninoto_serif_upper<N>.ttf` | Serif upper bucket N | Written as needed when `_upper` would exceed the glyph limit |
| `fonts/merged/<style>/uninoto_mono.ttf` | Mono base | Contains all Mono codepoints when they fit; otherwise BMP |
| `fonts/merged/<style>/uninoto_mono_upper.ttf` | Mono upper | Written when all Mono upper-plane codepoints fit in one extra file |
| `fonts/merged/<style>/uninoto_mono_upper<N>.ttf` | Mono upper bucket N | Written as needed when `_upper` would exceed the glyph limit |
| `fonts/merged/<style>/uninoto_last.ttf` | Sans/Serif shared fallback | Contains all last codepoints when they fit; otherwise the first last bucket |
| `fonts/merged/<style>/uninoto_last<N>.ttf` | Last bucket N | Written as needed when last output exceeds the glyph limit |

Coverage as of the 2026-06-15 merge against Unicode 17 visible non-mark
characters (157,088 total):

| Style | Sans + last | Sans | Serif + last | Serif | Mono |
|-------|-------------|------|--------------|-------|------|
| `full` | 156,539 (99.651%) | 152,703 (97.209%) | 156,539 (99.651%) | 143,723 (91.492%) | 152,703 (97.209%) |
| `regular` | 79,004 (50.293%) | 71,214 (45.334%) | 79,004 (50.293%) | 61,390 (39.080%) | 71,630 (45.599%) |
| `bold` | 54,574 (34.741%) | 53,934 (34.334%) | 54,574 (34.741%) | 51,155 (32.565%) | 54,196 (34.500%) |
| `italic` | 2,853 (1.816%) | 2,794 (1.779%) | 2,853 (1.816%) | 2,722 (1.733%) | 2,794 (1.779%) |
| `bolditalic` | 2,814 (1.791%) | 2,755 (1.754%) | 2,814 (1.791%) | 2,722 (1.733%) | 2,755 (1.754%) |

## Font sources

uninoto merges static TTF/OTF fonts by style. Variable fonts are excluded. Each
style is built on its own:

| Style | Intended use | Style consistency |
|-------|--------------|-------------------|
| `full` | Maximum coverage for visible characters | May mix visual styles. It includes uncertain sources when they add coverage |
| `regular` | Default regular fallback | Keeps a regular look where possible. It does not use uncertain, bold, italic, or bold italic sources |
| `bold` | Bold fallback text | Keeps a bold look where possible. It does not fall back to regular or italic sources |
| `italic` | Italic fallback text | Keeps an italic or slanted look where possible. Coverage is much lower because broad italic sources are rare |
| `bolditalic` | Bold italic fallback text | Keeps a bold italic look where possible. Coverage is much lower because broad bold italic sources are rare |

Use `full` when coverage is more important than visual consistency. Use the
other styles when matching the requested text style matters more than covering
every possible character.

### Primary source: Noto fonts

- [Noto Monthly Build](https://github.com/notofonts/notofonts.github.io): ordinary Noto family TTFs from the monthly release tag
- [Noto CJK](https://github.com/notofonts/noto-cjk): static regional CJK packages (SC/TC/JP/KR/HK)
- [Noto Emoji](https://github.com/googlefonts/noto-emoji)

### Fallback sources

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

### Investigated sources not included

The remaining visible gaps are concentrated in recently encoded scripts and
Tangut-related blocks. Public OFL source repositories exist for some newer Noto
scripts such as [Gurung Khema](https://github.com/notofonts/gurung-khema) and
[Ol Onal](https://github.com/notofonts/ol-onal), but they currently do not
publish regular/static TTF release files. They are not downloaded by default
until a direct font artifact is available or a source build pipeline is added.

In the 2026-06-14 audit, the largest remaining `sans`/`serif` gaps were
Tangut Components Supplement, Garay, Tulu-Tigalari, Tolong Siki, Tai Yo,
Ol Onal, Gurung Khema, Sidetic, Tangut Supplement, Dives Akuru, Arabic
Presentation Forms-A, and Syriac Supplement.

## Building from source

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
pypy3 src/merge-all.py
```

### Audit reports

After merging, reports are written to `fonts/reports/<style>/`:

- `sans-missing-visible.csv` / `serif-missing-visible.csv` / `mono-missing-visible.csv`: visible codepoints still uncovered after merging
- `sans-missing-visible-without_last.csv` / `serif-missing-visible-without_last.csv`: missing codepoints excluding `uninoto_last*` coverage

## License

### Build scripts

The build scripts under `src/` are released under the **MIT License**.

### Generated fonts

The merged output fonts (`fonts/merged/<style>/uninoto_*.ttf`) are composite/derivative
works built from the source fonts listed in [LICENSE](./LICENSE). Source font
licenses and notices are retained; generated font metadata points back to this
repository's license inventory.

### Source font licenses

License texts, license references, and source notices for the source fonts are included in [LICENSE](./LICENSE):

- **SIL Open Font License 1.1** (Noto families, most BabelStone script fonts, Padauk, Scheherazade New, Harmattan, Charis SIL, Doulos SIL, Junicode, Kanchenjunga, Kedebideri, Fairfax HD, Scriptwide Sans CJK, Cascadia Code, etc.)
- **CC0 1.0 Universal** (Jigmo)
- **Arphic Public License** (BabelStone Han)
- **GlyphWiki License** (HanaMinB, HanaMinC)
- **George Douros free-use notice** (Abydos)

See [LICENSE](./LICENSE) for the full source font inventory and corresponding license terms.
