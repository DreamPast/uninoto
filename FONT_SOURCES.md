# Font Sources

This document lists the font source families in the same high-level order used
by `src/uninoto/download_noto.py`. Downloaded files still pass through the source
filters in `src/uninoto/font_io.py` and the family routing logic in
`src/uninoto/source_selection.py` before they are merged.

## Source Routing Summary

1. `sans` uses sources whose path or file name clearly identifies them as sans.
2. `serif` uses sources whose path or file name clearly identifies them as serif
   or the legacy spelling `serief`.
3. `mono` uses mono sources first, then non-serif sources with normalized advance
   widths.
4. Directional `extra` outputs use neutral sources plus the opposite family only
   for codepoints missing from the target family.
5. Color emoji fonts with empty outline glyphs are not accepted as coverage
   sources; `NotoEmoji-Regular.ttf` is the accepted Noto Emoji source.

## Sans Sources

The following sources are routed to `sans` when their discovered file paths or
file names contain explicit sans signals. The order below follows the downloader
order.

1. **Noto monthly ordinary TTF set: Noto Sans families**
   Source: `notofonts/notofonts.github.io`, latest
   `noto-monthly-release-*` tag unless `--monthly-tag` is supplied.
   Routed files: extracted static files whose paths or names contain
   `NotoSans`/`sans`.

2. **Noto CJK Sans release archives**
   Source: `notofonts/noto-cjk` release assets from the `Sans2.004` tag.
   Routed files: regional static Sans CJK archives.

3. **Scriptwide Sans CJK A**
   Source: `ScriptwideSansCJK-A.ttf`.
   Purpose: supplementary CJK coverage.

4. **Scriptwide Sans CJK B**
   Source: `ScriptwideSansCJK-B.ttf`.
   Purpose: supplementary CJK coverage.

5. **Scriptwide Sans CJK C**
   Source: `ScriptwideSansCJK-C.ttf`.
   Purpose: supplementary CJK coverage.

6. **Noto Sans Gurung Khema source build**
   Source: upstream `NotoSansGurungKhema.sfd`, built locally into
   `NotoSansGurungKhema-Regular.ttf`.
   Purpose: Gurung Khema coverage.

## Serif Sources

The following sources are routed to `serif` when their discovered file paths or
file names contain explicit serif signals, including the legacy spelling
`serief`.

1. **Noto monthly ordinary TTF set: Noto Serif families**
   Source: `notofonts/notofonts.github.io`, latest
   `noto-monthly-release-*` tag unless `--monthly-tag` is supplied.
   Routed files: extracted static files whose paths or names contain
   `NotoSerif`/`serif`.

2. **Noto CJK Serif release archives**
   Source: `notofonts/noto-cjk` release assets from the `Serif2.003` tag.
   Routed files: regional static Serif CJK archives.

3. **Noto Serif Dives Akuru**
   Source: `NotoSerifDivesAkuru-v2.000.zip`.
   Purpose: Dives Akuru coverage.

4. **Noto Serif Ol Onal source build**
   Source: upstream `NotoSerifOlOnal.sfd`, built locally into
   `NotoSerifOlOnal-Regular.ttf`.
   Purpose: Ol Onal coverage.

## Extra Sources

The following neutral sources are routed to `extra` when their discovered file
paths or file names do not clearly identify them as sans, serif, or mono.
Directional extra outputs also receive codepoints covered by the opposite
clearly classified family when the target family does not cover them. The order
below follows the downloader order for the neutral source portion. Some fonts listed
here are typographically serif or sans-like, but the program treats them as
neutral because their accepted file paths do not explicitly say `sans` or
`serif`.

1. **Noto monthly ordinary TTF set: neutral Noto families**
   Source: `notofonts/notofonts.github.io`, latest
   `noto-monthly-release-*` tag unless `--monthly-tag` is supplied.
   Routed files: extracted static files that do not clearly match Noto Sans,
   Noto Serif, or mono naming.

2. **Noto Emoji monochrome TTF**
   Source: CTAN mirror for `NotoEmoji-Regular.ttf`.
   Merge use: accepted as the emoji outline coverage source.

3. **BabelStone dynamic fallback fonts**
   Source: `https://www.babelstone.co.uk/Fonts/`.
   Selection: static TTF/OTF/ZIP download links discovered from the BabelStone
   font index and linked font pages, sorted by target path. Versioned
   `BabelStoneHan-*` archives are skipped.

4. **Jigmo**
   Source: `Jigmo-20250912.zip`.
   Purpose: broad CJK extension coverage through recent Unicode versions.

5. **Padauk**
   Source: `Padauk-6.000.zip`.
   Purpose: Myanmar script and Myanmar Extended-C coverage.

6. **Scheherazade New**
   Source: `ScheherazadeNew-4.500.zip`.
   Purpose: Arabic script supplement coverage.

7. **Harmattan**
   Source: `Harmattan-4.400.zip`.
   Purpose: Ajami and West African Arabic-script coverage.

8. **HanaMin B**
   Source: `HanaMinB.otf` from HanaMinAFDKO.
   Purpose: CJK Extension B/C coverage.

9. **HanaMin C**
   Source: `HanaMinC.otf` from HanaMinAFDKO.
   Purpose: additional CJK extension coverage.

10. **Plangothic P2**
    Source: `PlangothicP2-Regular.ttf`.
    Purpose: Unicode 16/17 script coverage and Tangut supplement coverage.

11. **Noto Fangsong KSS Vertical**
    Source: `NotoFangsongKSSVertical-v1.000.zip`.
    Purpose: Khitan Small Script coverage.

12. **Kanchenjunga**
    Source: `Kanchenjunga-2.001.zip`.
    Purpose: Kirat Rai script coverage.

13. **Junicode**
    Source: `Junicode_2.224.zip`.
    Purpose: medieval Latin and scholarly character coverage.

14. **Kedebideri**
    Source: `Kedebideri-3.001.zip`.
    Purpose: Zaghawa Beria coverage.

15. **Charis SIL**
    Source: `Charis-7.000.zip`.
    Purpose: IPA and extended Latin coverage.
    Note: typographically serif, but routed as neutral unless the accepted file
    path explicitly contains `serif`.

16. **Doulos SIL**
    Source: `DoulosSIL-7.000.zip`.
    Purpose: IPA and phonetic notation coverage.
    Note: typographically serif, but routed as neutral unless the accepted file
    path explicitly contains `serif`.

17. **Abydos**
    Source: `gdouros-abydos-fonts-1.96-2.13.noarch.rpm`.
    Purpose: Egyptian Hieroglyphs supplement coverage.

18. **Fairfax HD**
    Source: `fairfaxhd.zip`.
    Purpose: UCSUR and scholarly character coverage.

## Mono And Reference Sources

These sources are downloaded in program order but are not routed to `sans`,
`serif`, or `extra` under the current family rules.

1. **Noto monthly ordinary TTF set: mono families**
   Routed files: extracted static files whose paths or names clearly identify
   mono sources, such as Noto Sans Mono.

2. **Noto CJK Mono release archives**
   Source: `notofonts/noto-cjk` release assets from the `Sans2.004` tag.
   Routed files: regional static Mono CJK archives.

3. **Noto Emoji repository archive**
   Source: `googlefonts/noto-emoji`, `main` branch archive.
   Downloaded files: `Noto-COLRv1.ttf`, `Noto-COLRv1-noflags.ttf`,
   `NotoColorEmoji.ttf`, and `NotoColorEmoji-noflags.ttf`.
   Merge use: retained for reference/extraction compatibility, but not accepted
   as coverage sources when the glyphs rely on color tables instead of outlines.

4. **Cascadia Code**
   Source: `CascadiaCode-2407.24.zip`.
   Purpose: monospace fallback coverage.

See `LICENSE` for the full license text and source notices.
