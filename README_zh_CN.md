# uninoto：通用 Unicode 覆盖字体

[English](./README.md) | **简体中文**

uninoto 用来生成一组覆盖 Unicode 可见字符的后备字体。它以 Noto 为主来源，再加入其他可再分发的字体来补 Noto 尚未覆盖的部分。

本项目关注的是基础显示覆盖：尽量让缺失字符显示为字形，而不是空白。生成字体不保证复杂连笔、脚本排版、字距调整、hinting 或专业排印质量。如果需要这些能力，建议直接使用下方列出的官方源字体。

uninoto 更适合作为后备字体使用。当应用或文档已经尝试了自己的首选字体，但仍有字符无法显示时，它提供一个基本替补。

## 字体结果

当前项目输出 `sans`（无衬线）、`serif`（衬线）、`mono`（等宽）以及按目标族拆分的 `extra` 后备输出。CJK 汉字在可用时优先使用简体中文字形。

字体来源会按路径或文件名中的明确族信息归类：

- `sans` 只使用明确标识为 sans 的来源，例如 Noto Sans 或 Sans CJK 来源。
- `serif` 只使用明确标识为 serif 的来源，也兼容历史拼写 `serief`。
- `mono` 只使用识别为等宽的来源，并且只保留原始 advance width 已符合 mono 指标的 glyph。
- `sans_extra` 使用中性来源以及 serif 选中来源中 sans 缺失的码点。
- `serif_extra` 使用中性来源以及 sans 选中来源中 serif 缺失的码点。

输出按样式放在 `fonts/merged/<style>/` 下。默认构建 `regular`，也可以构建
`bold`、`italic`、`bolditalic` 和 `full`。样式命名不确定的静态字体会归入
`full`，不会归入 `regular`。

单个 TTF 最多包含 65535 个 glyph，因此每个族可能拆成多个 TTF：

- 如果能放进单个 TTF，无后缀文件会包含该族的全部码点
- 如果某个族放不进单个 TTF，会直接拆成编号文件，例如 `uninoto_sans1.ttf`、`uninoto_sans2.ttf`
- 空的拆分分桶会跳过，不写空字体

建议把 uninoto 放在字体 fallback 链的末尾，用作缺失字体或无效字形覆盖的可见提示。生成字体的 `.notdef` 是可见的 Noto 风格缺字方框，因此仍然无法表示的文本不容易静默消失。如果需要能标识 Unicode 区段或特殊码点类别的完整终级提示字体，请查看 [Unicode Last Resort](https://github.com/unicode-org/last-resort-font) 项目。

`mono`族字体只接受原始 advance width 已符合当前 Noto mono 指标的来源 glyph：半宽字符 600，CJK/全宽/emoji 字符 1000。脚本不会把其他宽度强行改成等宽指标。

生成字体写出前会移除 layout 和 hinting 表。没有 cmap 对应的孤儿 glyph 会被清理，`.notdef` 等占位 glyph 以及复合字形需要的组件 glyph 会保留。`.notdef` 会写成可见的 Noto 风格缺字方框，并且不会映射到任何 Unicode 码点。

输出文件结构：

| 路径 | 变体 | 说明 |
|------|------|------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans | 能放下时包含 Sans 全部码点 |
| `fonts/merged/<style>/uninoto_sans<N>.ttf` | Sans N | Sans 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_serif.ttf` | Serif | 能放下时包含 Serif 全部码点 |
| `fonts/merged/<style>/uninoto_serif<N>.ttf` | Serif N | Serif 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_mono.ttf` | Mono | 能放下时包含 Mono 全部码点 |
| `fonts/merged/<style>/uninoto_mono<N>.ttf` | Mono N | Mono 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_sans_extra.ttf` | Sans extra 补充 | 能放下时包含全部 sans extra 码点 |
| `fonts/merged/<style>/uninoto_sans_extra<N>.ttf` | Sans extra N | sans extra 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_serif_extra.ttf` | Serif extra 补充 | 能放下时包含全部 serif extra 码点 |
| `fonts/merged/<style>/uninoto_serif_extra<N>.ttf` | Serif extra N | serif extra 超出 glyph 上限时按需写入 |

截至 2026-06-17 的 Unicode 17 合并审计，非控制、非空白可见码点共 159612 个，覆盖率如下：

`Sans + extra` 和 `Serif + extra` 是实际 fallback 链覆盖率。单独的 `Sans base` 和
`Serif base` 只统计明确归类到对应基础族的来源，不包含按目标族拆分的 `extra` 覆盖。

| 样式 | Sans + extra | Sans base | Serif + extra | Serif base | Mono |
|------|-------------|------|--------------|-------|------|
| `full` | 159522 (99.944%) | 143884 (90.146%) | 159524 (99.945%) | 58469 (36.632%) | 35119 (22.003%) |
| `regular` | 96290 (60.328%) | 70854 (44.391%) | 96292 (60.329%) | 58469 (36.632%) | 35114 (22.000%) |
| `bold` | 55727 (34.914%) | 54588 (34.200%) | 55727 (34.914%) | 50494 (31.635%) | 35118 (22.002%) |
| `italic` | 3164 (1.982%) | 3086 (1.933%) | 3164 (1.982%) | 3000 (1.880%) | 26 (0.016%) |
| `bolditalic` | 3125 (1.958%) | 3047 (1.909%) | 3125 (1.958%) | 3000 (1.880%) | 26 (0.016%) |

## 字体来源

uninoto 按样式合并静态 TTF/OTF 字体，并排除变量字体。每个输出样式都会独立构建：

| 样式 | 适用场景 | 样式一致性 |
|------|----------|------------|
| `full` | 尽可能覆盖更多可见字符 | 可能出现样式不一致。只要不确定来源能增加覆盖，就会纳入 |
| `regular` | 默认 regular 后备字体 | 尽量保持 regular 外观，不使用不确定、粗体、斜体或粗斜体来源 |
| `bold` | 粗体后备文本 | 尽量保持粗体外观，不回退到 regular 或 italic 来源 |
| `italic` | 斜体后备文本 | 尽量保持斜体或倾斜外观。广覆盖斜体来源较少，所以覆盖率明显较低 |
| `bolditalic` | 粗斜体后备文本 | 尽量保持粗斜体外观。广覆盖粗斜体来源较少，所以覆盖率明显较低 |

如果覆盖率优先，使用 `full`。如果更重视请求样式的一致性，使用其它样式。

### 主要来源：Noto 字体

- [notofonts](https://github.com/notofonts/notofonts.github.io) 
- [noto-cjk](https://github.com/notofonts/noto-cjk)
- [noto-emoji](https://github.com/googlefonts/noto-emoji)

### 后备来源

| 字体 | 用途 | 许可证 |
|------|------|--------|
| [BabelStone](https://www.babelstone.co.uk/Fonts/) | 多种古代文字、罕用字符，包括 Tangut Yinchuan | OFL 1.1 / BabelStone Han 使用 Arphic Public License |
| [Jigmo 字云](https://kamichikoichi.github.io/jigmo/) | Unicode 17 CJK 扩展至扩展 J | CC0 1.0 |
| [Padauk](https://software.sil.org/padauk/) | 缅甸文及 Myanmar Extended-C 补充 | OFL 1.1 |
| [Scheherazade New](https://software.sil.org/scheherazade/) | 阿拉伯文字补充 | OFL 1.1 |
| [Harmattan](https://software.sil.org/harmattan/) | Ajami / 西非阿拉伯文字补充 | OFL 1.1 |
| [HanaMin (Hanazono)](https://github.com/cjkvi/HanaMinAFDKO) | CJK 扩展 B/C 区汉字 | Hanazono / OFL 1.1 |
| [Scriptwide Sans CJK](https://github.com/scriptwide-fonts/scriptwide-sans-cjk) | CJK 字符补充 | OFL 1.1 |
| [Plangothic](https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project) | Unicode 16/17 新文字及 Tangut 补充覆盖 | OFL 1.1 |
| [Cascadia Code](https://github.com/microsoft/cascadia-code) | 等宽字体补充 | OFL 1.1 |
| [Charis SIL](https://software.sil.org/charis/) | 衬线 IPA 及扩展拉丁 | OFL 1.1 |
| [Doulos SIL](https://software.sil.org/doulos/) | 衬线 IPA 及音标 | OFL 1.1 |
| [Junicode](https://github.com/psb1558/Junicode-font) | 中世纪拉丁及学术字符 | OFL 1.1 |
| [Kanchenjunga](https://github.com/silnrsi/font-kanchenjunga) | Kirat Rai 文字 | OFL 1.1 |
| [Kedebideri](https://software.sil.org/kedebideri/) | Zaghawa Beria 文字 | OFL 1.1 |
| [Fairfax HD](https://www.kreativekorp.com/software/fonts/fairfaxhd/) | 多种 UCSUR 及学术字符 | OFL 1.1 |
| [Khitan Small Script](https://github.com/notofonts/khitan-small-script) | 契丹小字 | OFL 1.1 |
| [Noto Serif Dives Akuru](https://github.com/notofonts/dives-akuru) | Dives Akuru 文字 | OFL 1.1 |
| [Noto Gurung Khema](https://github.com/notofonts/gurung-khema) | Gurung Khema 文字，从上游 SFD 源码构建 | OFL 1.1 |
| [Noto Ol Onal](https://github.com/notofonts/ol-onal) | Ol Onal 文字，从上游 SFD 源码构建 | OFL 1.1 |
| [Abydos](https://greekfonts.teilar.gr/) | 埃及圣书体补充 | 自由使用 |

### 已调查但暂未接入的来源

当前剩余可见缺口主要集中在较新的 Unicode 16/17 文字和 Tangut 相关区块。部分较新的 Noto 文字仓库没有发布 Regular/static TTF 文件或 release asset。若上游提供 SFD 源码，且其中包含正确编码的真实字形，`src/uninoto/sfd_to_ttf.py` 可以构建最小静态 TTF 供合并使用。

过滤空轮廓字形后，`full` sans/serif + extra 的剩余缺口集中在 Tulu-Tigalari、Duployan 和 3 个 Egyptian Hieroglyphs Extended-A 码点。

## 构建方法

### 环境要求

- Python 3.11+（推荐 PyPy 3.11）
- Windows 环境需安装 [7-Zip](https://www.7-zip.org/)，用于解压 RPM 包

### 步骤

```powershell
# 1. 安装依赖
pypy3 -m pip install -r requirements.txt

# 2. 下载字体来源（并发下载，支持断点续传，默认 8 线程）
pypy3 src/download-noto.py

# 可选：仅解压已下载的归档，不重新下载
pypy3 src/download-noto.py --extract-existing

# 3. 合并 regular 字体并生成审计报告
pypy3 src/merge.py

# 可选：合并某个样式或所有配置样式
pypy3 src/merge.py --style bold
pypy3 src/merge.py --style all

# 可选：使用多进程合并所有配置样式和族
pypy3 src/merge-all.py
```

### 审计报告

合并完成后，以下报告写入 `fonts/reports/<style>/`：

- `sans-missing-visible.csv` / `serif-missing-visible.csv` / `mono-missing-visible.csv`：合并后仍缺失的可见码点
- `sans-missing-visible-without_extra.csv` / `serif-missing-visible-without_extra.csv`：不含按目标族拆分的 extra 补充时的缺失码点

## 许可证

### 构建脚本

`src/` 目录下的构建脚本以 **MIT License** 发布。

### 生成字体

合并输出的字体（`fonts/merged/<style>/uninoto_*.ttf`）是由 [LICENSE](./LICENSE) 中列出的源字体构成的复合/衍生作品。源字体的许可证与声明继续保留；生成字体的元数据会指向本仓库的许可证清单。

### 源字体许可证

所有源字体的许可证文本、许可证引用与来源声明收录在仓库根目录的 [LICENSE](./LICENSE) 文件中，包括：

- **SIL Open Font License 1.1**（Noto 系列、多数 BabelStone script fonts、Padauk、Scheherazade New、Harmattan、Charis SIL、Doulos SIL、Junicode、Kanchenjunga、Kedebideri、Fairfax HD、Scriptwide Sans CJK、Cascadia Code 等）
- **CC0 1.0 Universal**（Jigmo 字云）
- **Arphic Public License**（BabelStone Han）
- **Hanazono Font License**（HanaMinB、HanaMinC，亦可用 OFL 1.1）
- **George Douros 自由使用声明**（Abydos）

详细的源字体文件列表及对应许可证条款请参阅 [LICENSE](./LICENSE)。
