# NOTES.md

## Investigated Sources With No `full` Non-Mono Coverage Gain

- **Noto Syriac release zips**
  - Source: `notofonts/syriac` releases `NotoSansSyriacWestern-v3.001`, `NotoSansSyriacEastern-v3.001`, and `NotoSansSyriac-v3.000`.
  - Decision: not added as extra fallback sources.
  - Reason: direct cmap checks against `fonts/reports/full/sans-missing-visible.csv` found no overlap with the current missing visible codepoints.

- **Noto Arabic release zips**
  - Source: `notofonts/arabic` releases `NotoSansArabic-v2.013` and `NotoNaskhArabic-v2.021`.
  - Decision: not added as extra fallback sources.
  - Reason: direct cmap checks against `fonts/reports/full/sans-missing-visible.csv` found no overlap with the current missing visible codepoints, including Arabic Extended-C and Arabic Presentation Forms-A gaps.

- **Noto Sharada release zip**
  - Source: `notofonts/sharada` release `NotoSansSharada-v2.006`.
  - Decision: not added as an extra fallback source.
  - Reason: direct cmap checks against `fonts/reports/full/sans-missing-visible.csv` found no overlap with the current missing Sharada Supplement codepoints.

- **Locally downloaded but filtered static fonts**
  - Source: non-source-filtered TTF/OTF files already under `fonts/noto`.
  - Decision: no additional local font was enabled for `full` non-mono coverage.
  - Reason: after excluding known PUA/color/vertical/rotated/inverse and non-regular style variants, no remaining local font had any cmap overlap with `fonts/reports/full/sans-missing-visible.csv`.

- **Current BabelStone Tangut fonts**
  - Source: `BabelStoneTangutComponents.ttf`, `BabelStoneTangutRadicals.ttf`, `BabelStoneTangutWenhai.ttf`, and `TangutYinchuan.ttf` from the current BabelStone downloads.
  - Decision: no additional `full` non-mono coverage change beyond the already-enabled source set.
  - Reason: direct cmap checks against `fonts/reports/full/sans-missing-visible.csv` found no overlap. The current BabelStone Tangut Components font covers the older Tangut Components range but not the Unicode 17 Tangut Components Supplement gaps.

- **Jai Tulunad Tulu fonts**
  - Source: `Pingara_Tulu_Font_V5.otf`, `Brvu-1.otf`, `mandara.ttf`, and `XAAlAlieg(allige)Academy1.4.ttf` linked from `https://jaitulunad.in/others/tulu-fonts`.
  - Decision: not added.
  - Reason: the page did not provide a reusable font license, and direct cmap checks found no Unicode Tulu-Tigalari mappings (`U+11380..U+113FF`) and no overlap with `fonts/reports/full/sans-missing-visible.csv`.

- **GNU FreeFont 20120503**
  - Source: `https://ftp.gnu.org/gnu/freefont/freefont-ttf-20120503.zip`.
  - Decision: not added.
  - Reason: direct cmap checks for all TTFs in the release found no overlap with `fonts/reports/full/sans-missing-visible.csv`.

- **Noto repository sweep for newest `full` non-mono gaps**
  - Source: GitHub API enumeration of the `notofonts` organization and repository searches for Garay, Tulu-Tigalari, Tai Yo, Tolong Siki, and Sidetic.
  - Decision: no new Noto source was added for these scripts.
  - Reason: no matching `notofonts` repository or release asset was found for those script names. Existing `notofonts` releases for Syriac, Arabic, and Sharada were checked separately and had no current missing-codepoint overlap.

- **Alphabetum**
  - Source: Alphabetum multilingual Unicode font.
  - Decision: rejected for this project.
  - Reason: it is a commercial font, not a free reusable/commercial-redistributable fallback source. It may include Sidetic, but it does not satisfy the project's source policy.

- **Kurinto Font Folio**
  - Source: `https://kurinto.com/` and its download page.
  - Decision: not downloaded or added during this pass.
  - Reason: the project is OFL and commercially usable, but the current public package is v2.197 from 2021 and even the Lite package is about 500 MiB. The remaining priority `full` non-mono gaps are concentrated in Unicode 16/17 scripts and recent Tangut additions, so there is no strong evidence that downloading this old large package would improve the current missing report.

- **Noto Serif Dives Akuru source package**
  - Source: `notofonts/dives-akuru` `main` branch `sources/NotoSerifDivesAkuru.glyphspackage`.
  - Decision: no source-build fallback was added for the remaining Dives Akuru gaps.
  - Reason: the upstream release TTF covers 49 Dives Akuru codepoints but misses the current 23 `full` non-mono Dives Akuru gaps. Parsing the current glyph package source found no Unicode mappings in `U+11900..U+1195F`, so it does not provide an obvious source path for the missing encoded characters.

- **Noto Egyptian Hieroglyphs release and legacy repository**
  - Source: `notofonts/egyptian-hieroglyphs` release `NotoSansEgyptianHieroglyphs-v2.001` and legacy `notofonts/NotoSansEgyptianHieroglyphs`.
  - Decision: not added as extra fallback sources for the remaining Egyptian Hieroglyphs Extended-A gaps.
  - Reason: direct cmap checks found no overlap with the remaining `full` non-mono missing codepoints `U+1407B`, `U+141DA`, and `U+143BF`.

- **Tulu-Tigalari public search**
  - Source: web searches for Unicode Tulu-Tigalari fonts and GitHub repository searches for Tulu-Tigalari names and codepoint strings such as `11380`.
  - Decision: no new Tulu-Tigalari fallback source was added.
  - Reason: searches found standards/encyclopedia references and legacy/non-Unicode Tulu font pages, but no free commercially reusable font with Unicode `U+11380..U+113FF` cmap coverage. GitHub repository search did not find a candidate project, and unauthenticated GitHub code search was unavailable.

- **Noto monthly freshness check**
  - Source: current local `notofonts.github.io-noto-monthly-release-2026.06.01` archive and upstream `latest_monthly_tag()`.
  - Decision: no additional monthly Noto download was needed.
  - Reason: the local monthly source is already the latest upstream tag as of this check, and the regenerated `full` report still has Tulu-Tigalari and three Egyptian Hieroglyphs Extended-A gaps.
