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

The build writes `sans`, `serif`, `mono`, shared `extra` fallback outputs, and
a separate `last_resort` diagnostic output.
CJK ideographs use Simplified Chinese forms where those forms are available.

Font sources are routed by explicit family signals in their path or file name:

- `sans` uses sources that clearly identify themselves as sans, such as Noto Sans or Sans CJK sources.
- `serif` uses sources that clearly identify themselves as serif (including the legacy `serief` spelling).
- `mono` uses mono sources first, then non-serif sources with normalized advance widths.
- `extra` uses neutral sources that are not clearly sans or serif, and also stores the coverage difference between clearly classified sans and serif sources so the two fallback chains align.
- `last_resort` stores Unicode Last Resort diagnostic prompts for whitespace and invisible codepoints in the `full` style only.

Outputs are grouped by style under `fonts/merged/<style>/`. The default build
creates `regular`; additional supported style builds are `bold`, `italic`,
`bolditalic`, and `full`. Static fonts with uncertain style naming are used by
`full`, not by `regular`.

Each family may be split across several TTF files because one TTF can contain at
most 65,535 glyphs:

- Files without a suffix contain all covered codepoints when they fit in one TTF
- When a family does not fit in one TTF, it is split directly into numbered files such as `uninoto_sans1.ttf`, `uninoto_sans2.ttf`, and so on
- Empty split buckets are skipped

`uninoto_extra.ttf` contains shared fallback coverage for `sans` and `serif`:
neutral sources plus the coverage difference between clearly classified sans and
serif sources.

The `full` style's `last_resort` output contains Unicode Last Resort prompts
for whitespace codepoints plus invisible codepoints (`Cc`, `Cf`, `Cs`, `Co`, and
`Cn`). These prompts are diagnostic glyphs: they help reveal spaces, control
characters, private-use characters, surrogate codepoints, unassigned codepoints,
and noncharacters on systems that would otherwise render them as blank. They are
not used for visible character coverage and are kept separate from `extra`.

The `mono` family uses normalized advance widths that match the current Noto
mono sources: half-width 600 and full-width 1000.

Generated fonts are stripped of layout and hinting tables before writing.
Unencoded orphan glyphs are pruned, while placeholders such as `.notdef` and
glyphs required as composite components are kept. The `.notdef` glyph is written
as a visible Noto-style fallback box and is not mapped from any Unicode
codepoint.

Output structure:

| Path | Variant | Notes |
|------|---------|-------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans | Contains all Sans codepoints when they fit |
| `fonts/merged/<style>/uninoto_sans<N>.ttf` | Sans bucket N | Written as needed when Sans exceeds the glyph limit |
| `fonts/merged/<style>/uninoto_serif.ttf` | Serif | Contains all Serif codepoints when they fit |
| `fonts/merged/<style>/uninoto_serif<N>.ttf` | Serif bucket N | Written as needed when Serif exceeds the glyph limit |
| `fonts/merged/<style>/uninoto_mono.ttf` | Mono | Contains all Mono codepoints when they fit |
| `fonts/merged/<style>/uninoto_mono<N>.ttf` | Mono bucket N | Written as needed when Mono exceeds the glyph limit |
| `fonts/merged/<style>/uninoto_extra.ttf` | Neutral shared fallback | Contains all extra codepoints when they fit |
| `fonts/merged/<style>/uninoto_extra<N>.ttf` | Extra bucket N | Written as needed when extra output exceeds the glyph limit |
| `fonts/merged/full/uninoto_last_resort.ttf` | Last Resort diagnostics | Contains whitespace and invisible-codepoint prompts |

Coverage as of the 2026-06-16 merge against Unicode 17 visible codepoints
(159,631 total):

The `Sans + extra` and `Serif + extra` columns are the effective fallback-chain
coverage. The bare `Sans base` and `Serif base` columns show only clearly
classified base family sources, excluding shared `extra` coverage.

| Style | Sans + extra | Sans base | Serif + extra | Serif base | Mono |
|-------|-------------|------|--------------|-------|------|
| `full` | 159,525 (99.934%) | 143,885 (90.138%) | 159,525 (99.934%) | 58,469 (36.627%) | 159,430 (99.874%) |
| `regular` | 96,293 (60.323%) | 70,855 (44.388%) | 96,293 (60.323%) | 58,469 (36.627%) | 96,029 (60.157%) |
| `bold` | 55,727 (34.910%) | 54,588 (34.197%) | 55,727 (34.910%) | 50,494 (31.630%) | 55,308 (34.647%) |
| `italic` | 3,164 (1.982%) | 3,086 (1.933%) | 3,164 (1.982%) | 3,000 (1.879%) | 3,103 (1.944%) |
| `bolditalic` | 3,125 (1.958%) | 3,047 (1.909%) | 3,125 (1.958%) | 3,000 (1.879%) | 3,064 (1.919%) |

## Font sources

uninoto merges static TTF/OTF fonts by style. Variable fonts are excluded. Each
style is built on its own:

For the source list in downloader order, see [FONT_SOURCES.md](./FONT_SOURCES.md).

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
| [BabelStone](https://www.babelstone.co.uk/Fonts/) | Various ancient scripts and rare characters, including Tangut Yinchuan | OFL 1.1 / Arphic Public License for BabelStone Han |
| [Jigmo](https://kamichikoichi.github.io/jigmo/) | Unicode 17 CJK extensions through Extension J | CC0 1.0 |
| [Padauk](https://software.sil.org/padauk/) | Myanmar script, including Myanmar Extended-C | OFL 1.1 |
| [Scheherazade New](https://software.sil.org/scheherazade/) | Arabic script supplement | OFL 1.1 |
| [Harmattan](https://software.sil.org/harmattan/) | Ajami / West African Arabic script supplement | OFL 1.1 |
| [HanaMin (Hanazono)](https://github.com/cjkvi/HanaMinAFDKO) | CJK Extension B/C ideographs | GlyphWiki / OFL 1.1 |
| [Scriptwide Sans CJK](https://github.com/scriptwide-fonts/scriptwide-sans-cjk) | Supplementary CJK coverage | OFL 1.1 |
| [Plangothic](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project) | Unicode 16/17 script and Tangut supplement coverage | OFL 1.1 |
| [Cascadia Code](https://github.com/microsoft/cascadia-code) | Monospace font supplement | OFL 1.1 |
| [Charis SIL](https://software.sil.org/charis/) | Serif IPA and extended Latin | OFL 1.1 |
| [Doulos SIL](https://software.sil.org/doulos/) | Serif IPA and phonetic notation | OFL 1.1 |
| [Junicode](https://github.com/psb1558/Junicode-font) | Medieval Latin and scholarly characters | OFL 1.1 |
| [Kanchenjunga](https://github.com/silnrsi/font-kanchenjunga) | Kirat Rai script | OFL 1.1 |
| [Kedebideri](https://software.sil.org/kedebideri/) | Zaghawa Beria script | OFL 1.1 |
| [Fairfax HD](https://www.kreativekorp.com/software/fonts/fairfaxhd/) | UCSUR and scholarly characters | OFL 1.1 |
| [Unicode Last Resort](https://github.com/unicode-org/last-resort-font) | `full`/`last_resort` diagnostic prompts for whitespace and invisible codepoints | OFL 1.1 |
| [Khitan Small Script](https://github.com/notofonts/khitan-small-script) | Khitan small script | OFL 1.1 |
| [Noto Serif Dives Akuru](https://github.com/notofonts/dives-akuru) | Dives Akuru script | OFL 1.1 |
| [Noto Gurung Khema](https://github.com/notofonts/gurung-khema) | Gurung Khema script, built from upstream SFD source | OFL 1.1 |
| [Noto Ol Onal](https://github.com/notofonts/ol-onal) | Ol Onal script, built from upstream SFD source | OFL 1.1 |
| [Abydos](https://greekfonts.teilar.gr/) | Egyptian Hieroglyphs supplement | Free use |

### Investigated sources not included

The remaining visible gaps are concentrated in recently encoded scripts and
Tangut-related blocks. Some newer Noto script repositories do not publish
regular/static TTF release files. When an upstream SFD source is available and
contains correct encoded glyphs, `src/uninoto/sfd_to_ttf.py` can build a minimal
static TTF for merging.

After filtering empty-outline glyphs, the remaining `full` sans/serif + extra
gaps are Tulu-Tigalari, Duployan, and three Egyptian Hieroglyphs Extended-A
codepoints.

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
- `sans-missing-visible-without_extra.csv` / `serif-missing-visible-without_extra.csv`: missing codepoints excluding `uninoto_extra*` coverage

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

- **SIL Open Font License 1.1** (Noto families, most BabelStone script fonts, Padauk, Scheherazade New, Harmattan, Charis SIL, Doulos SIL, Junicode, Kanchenjunga, Kedebideri, Fairfax HD, Scriptwide Sans CJK, Cascadia Code, Unicode Last Resort, etc.)
- **CC0 1.0 Universal** (Jigmo)
- **Arphic Public License** (BabelStone Han)
- **GlyphWiki License** (HanaMinB, HanaMinC)
- **George Douros free-use notice** (Abydos)

See [LICENSE](./LICENSE) for the full source font inventory and corresponding license terms.
