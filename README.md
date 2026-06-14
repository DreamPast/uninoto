# uninoto — Universal Unicode Coverage Font

**English** | [简体中文](./README_zh_CN.md)

uninoto aims to create a universal font family capable of displaying the vast majority of visible Unicode characters. Using Google Noto as the primary font family combined with additional free-to-use fallback fonts, it achieves near-complete coverage of visible characters.

## Font Outputs

The project produces three font families: `sans` (sans-serif), `serif`, and `mono` (monospace), derived from Google Noto Fonts. CJK ideographs default to **Simplified Chinese** glyph forms where available.

Each family is split across three TTF files due to the 65535 glyph limit per TTF:

- Files without a suffix cover U+0000 through U+FFFF (BMP)
- `upper1` and `upper2` cover codepoints above U+FFFF (higher planes)

`uninoto_last.ttf` contains additional codepoints from fallback fonts that complement both `sans` and `serif`.

The `mono` family uses normalized advance widths: half-width (600) or full-width (1000).

Output files:

- `uninoto_sans.ttf` / `uninoto_sans_upper1.ttf` / `uninoto_sans_upper2.ttf`
- `uninoto_serif.ttf` / `uninoto_serif_upper1.ttf` / `uninoto_serif_upper2.ttf`
- `uninoto_mono.ttf` / `uninoto_mono_upper1.ttf` / `uninoto_mono_upper2.ttf`
- `uninoto_last.ttf`

Coverage as of the 2026-06-14 merge against Unicode 17 (159,563 visible
characters total):

- `sans` (with `last`): 159,018 / 159,563, 99.656%
- `serif` (with `last`): 159,018 / 159,563, 99.656%
- `mono`: 155,120 / 159,563, 97.252%

## Font Sources

uninoto merges regular/static-weight fonts only (Bold, Oblique, Variable, and other variants are excluded):

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

# 3. Merge fonts and write audit reports
pypy3 src/merge.py
```

### Audit Reports

After merging, the following reports are written to `fonts/reports/`:

- `sans-plane-font-coverage.csv` / `serif-plane-font-coverage.csv` / `mono-plane-font-coverage.csv` — which source font provided each codepoint
- `sans-missing-visible.csv` / `serif-missing-visible.csv` / `mono-missing-visible.csv` — visible codepoints still uncovered after merging
- `sans-missing-visible-without_last.csv` / `serif-missing-visible-without_last.csv` — missing codepoints excluding `uninoto_last*` coverage

## License

### Build Scripts

The build scripts under `src/` are released under the **MIT License**.

### Generated Fonts

The merged output fonts (`fonts/merged/uninoto_*.ttf`) are composite/derivative
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
