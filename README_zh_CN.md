# uninoto：通用 Unicode 覆盖字体

[English](./README.md) | **简体中文**

uninoto 用来生成一组覆盖 Unicode 可见字符的后备字体。它以 Noto 为主来源，再加入其他可再分发的字体来补 Noto 尚未覆盖的部分。

本项目关注的是基础显示覆盖：尽量让缺失字符显示为字形，而不是空白。生成字体不保证复杂连笔、脚本排版、字距调整、hinting 或专业排印质量。如果需要这些能力，建议直接使用下方列出的官方源字体。

uninoto 更适合作为后备字体使用。当应用或文档已经尝试了自己的首选字体，但仍有字符无法显示时，它提供一个基本替补。

## 字体结果

当前项目输出三个族：`sans`（无衬线）、`serif`（衬线）和`mono`（等宽）。CJK 汉字在可用时优先使用简体中文字形。

输出按样式放在 `fonts/merged/<style>/` 下。默认构建 `regular`，也可以构建
`bold`、`italic`、`bolditalic` 和 `full`。样式命名不确定的静态字体会归入
`full`，不会归入 `regular`。

单个 TTF 最多包含 65535 个 glyph，因此每个族可能拆成多个 TTF：

- 如果能放进单个 TTF，无后缀文件会包含该族的全部码点
- 需要拆分时，无后缀文件覆盖U+0000~U+FFFF
- 如果 U+FFFF 之后的码点能放进单个额外 TTF，则写成 `_upper`
- 如果 `_upper` 仍超过 TTF glyph 上限，则继续拆成 `_upper1`、`_upper2`，以此类推
- 空的拆分分桶会跳过，不写空字体

`uninoto_last.ttf` 包含后备字体中用于补充 `sans` 和 `serif` 的码点。

`mono`族字体经过等宽处理，advance width 为半宽 600 或全宽 1000。

生成字体写出前会移除 layout 和 hinting 表。没有 cmap 对应的孤儿 glyph 会被清理，`.notdef` 等占位 glyph 以及复合字形需要的组件 glyph 会保留。`.notdef` 会写成可见的 Noto 风格缺字方框，并且不会映射到任何 Unicode 码点。

输出文件结构：

| 路径 | 变体 | 说明 |
|------|------|------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans base | 能放下时包含 Sans 全部码点，否则包含 BMP |
| `fonts/merged/<style>/uninoto_sans_upper.ttf` | Sans upper | Sans upper 码点能放进单个额外文件时写入 |
| `fonts/merged/<style>/uninoto_sans_upper<N>.ttf` | Sans upper N | `_upper` 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_serif.ttf` | Serif base | 能放下时包含 Serif 全部码点，否则包含 BMP |
| `fonts/merged/<style>/uninoto_serif_upper.ttf` | Serif upper | Serif upper 码点能放进单个额外文件时写入 |
| `fonts/merged/<style>/uninoto_serif_upper<N>.ttf` | Serif upper N | `_upper` 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_mono.ttf` | Mono base | 能放下时包含 Mono 全部码点，否则包含 BMP |
| `fonts/merged/<style>/uninoto_mono_upper.ttf` | Mono upper | Mono upper 码点能放进单个额外文件时写入 |
| `fonts/merged/<style>/uninoto_mono_upper<N>.ttf` | Mono upper N | `_upper` 超出 glyph 上限时按需写入 |
| `fonts/merged/<style>/uninoto_last.ttf` | Sans/Serif 共享补充 | 能放下时包含全部 last 码点，否则包含第一个 last 分桶 |
| `fonts/merged/<style>/uninoto_last<N>.ttf` | Last N | last 输出超出 glyph 上限时按需写入 |

截至 2026-06-15 的 Unicode 17 合并审计，可见码点共 159631 个，覆盖率如下：

| 样式 | Sans + last | Sans | Serif + last | Serif | Mono |
|------|-------------|------|--------------|-------|------|
| `full` | 159018 (99.616%) | 155120 (97.174%) | 159018 (99.616%) | 145298 (91.021%) | 155120 (97.174%) |
| `regular` | 81194 (50.864%) | 73265 (45.896%) | 81194 (50.864%) | 62590 (39.209%) | 73681 (46.157%) |
| `bold` | 55787 (34.947%) | 55046 (34.483%) | 55787 (34.947%) | 52114 (32.647%) | 55308 (34.647%) |
| `italic` | 3181 (1.993%) | 3103 (1.944%) | 3181 (1.993%) | 3017 (1.890%) | 3103 (1.944%) |
| `bolditalic` | 3142 (1.968%) | 3064 (1.919%) | 3142 (1.968%) | 3017 (1.890%) | 3064 (1.919%) |

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
| [BabelStone](https://www.babelstone.co.uk/Fonts/) | 多种古代文字、罕用字符 | OFL 1.1 / BabelStone Han 使用 Arphic Public License |
| [Jigmo 字云](https://kamichikoichi.github.io/jigmo/) | Unicode 17 CJK 扩展至扩展 J | CC0 1.0 |
| [Padauk](https://software.sil.org/padauk/) | 缅甸文及 Myanmar Extended-C 补充 | OFL 1.1 |
| [Scheherazade New](https://software.sil.org/scheherazade/) | 阿拉伯文字补充 | OFL 1.1 |
| [Harmattan](https://software.sil.org/harmattan/) | Ajami / 西非阿拉伯文字补充 | OFL 1.1 |
| [HanaMin (Hanazono)](https://github.com/cjkvi/HanaMinAFDKO) | CJK 扩展 B/C 区汉字 | Hanazono / OFL 1.1 |
| [Scriptwide Sans CJK](https://github.com/scriptwide-fonts/scriptwide-sans-cjk) | CJK 字符补充 | OFL 1.1 |
| [Cascadia Code](https://github.com/microsoft/cascadia-code) | 等宽字体补充 | OFL 1.1 |
| [Charis SIL](https://software.sil.org/charis/) | 衬线 IPA 及扩展拉丁 | OFL 1.1 |
| [Doulos SIL](https://software.sil.org/doulos/) | 衬线 IPA 及音标 | OFL 1.1 |
| [Junicode](https://github.com/psb1558/Junicode-font) | 中世纪拉丁及学术字符 | OFL 1.1 |
| [Kanchenjunga](https://github.com/silnrsi/font-kanchenjunga) | Kirat Rai 文字 | OFL 1.1 |
| [Kedebideri](https://software.sil.org/kedebideri/) | Zaghawa Beria 文字 | OFL 1.1 |
| [Fairfax HD](https://www.kreativekorp.com/software/fonts/fairfaxhd/) | 多种 UCSUR 及学术字符 | OFL 1.1 |
| [Khitan Small Script](https://github.com/notofonts/khitan-small-script) | 契丹小字 | OFL 1.1 |
| [Abydos](https://greekfonts.teilar.gr/) | 埃及圣书体补充 | 自由使用 |

### 已调查但暂未接入的来源

当前剩余可见缺口主要集中在较新的 Unicode 16/17 文字和 Tangut 相关区块。Noto 已有若干 OFL 源码仓库，例如 [Gurung Khema](https://github.com/notofonts/gurung-khema) 与 [Ol Onal](https://github.com/notofonts/ol-onal)，但目前没有发布 Regular/static TTF 文件或 release asset。在出现直接字体产物，或项目加入源码构建流程之前，下载脚本暂不接入这些仓库。

截至 2026-06-14 审计，`sans` / `serif` 中较大的剩余缺口包括 Tangut Components Supplement、Garay、Tulu-Tigalari、Tolong Siki、Tai Yo、Ol Onal、Gurung Khema、Sidetic、Tangut Supplement、Dives Akuru、Arabic Presentation Forms-A 和 Syriac Supplement。

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
- `sans-missing-visible-without_last.csv` / `serif-missing-visible-without_last.csv`：不含 `uninoto_last*` 补充的缺失码点

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
