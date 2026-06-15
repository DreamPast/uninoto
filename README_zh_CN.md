# uninoto — 通用 Unicode 覆盖字体

[English](./README.md) | **简体中文**

uninoto 旨在创建一套能够显示绝大部分 Unicode 可见字符的通用字体。本项目主要以Noto作为主字体，结合了其余免费可商用后备字体，实现对绝大部分可见字符的覆盖。

## 字体结果

当前项目有三个族，`sans`（无衬线）、`serif`（衬线）和`mono`（等宽），由Google Noto Fonts合并而来，CJK汉字优先使用**简体中文**字形。

输出按样式放在 `fonts/merged/<style>/` 下。默认构建 `regular`，也可以构建
`bold`、`italic`、`bolditalic` 和 `full`。样式命名不确定的静态字体会归入
`full`，不会归入 `regular`。

由于单个TTF最多包含65535个glyph，因此每个族可能拆成多个ttf：

- 如果能放进单个 TTF，无后缀文件会包含该族的全部码点
- 非 full 的保留排版输出按来源、区域和码点组拆分。可简单概括的 CJK 区域使用 `_sc`、`_tc`、`_jp`、`_kr` 等后缀；其它拆分组使用 `_1`、`_2`、`_3` 等数字后缀
- `full` 输出使用紧凑的 BMP/upper 拆分：upper 码点能放进一个文件时写成 `_upper`，否则写成 `_upper1`、`_upper2` 等
- 空的拆分分桶会跳过，不写空字体

`uninoto_last.ttf`包含了若干其余免费可商用后备字体，用于补充`sans`和`serif`。

`mono`族字体经过等宽处理，advance width 为半宽 600 或全宽 1000。

stripped 输出写出前会清理没有 cmap 对应的孤儿 glyph。非 full 的保留排版输出会保留源字体的排版/提示/度量元数据，并可能保留 OpenType 排版表、hinting 或复合字形引用的 no-cmap glyph。

输出文件结构：

| 路径 | 变体 | 说明 |
|------|------|------|
| `fonts/merged/<style>/uninoto_sans.ttf` | Sans base | 能放下时包含 Sans 全部码点 |
| `fonts/merged/<style>/uninoto_sans_<region>.ttf` | Sans 区域拆分 | 非 full 输出中，区域可概括为 `sc`、`tc`、`jp`、`kr` 等时写入 |
| `fonts/merged/<style>/uninoto_sans_<N>.ttf` | Sans 数字拆分 | 非 full 输出中，拆分组没有简洁区域名时写入 |
| `fonts/merged/<style>/uninoto_serif_<region>.ttf` | Serif 区域拆分 | 规则同 Sans |
| `fonts/merged/<style>/uninoto_mono_<N>.ttf` | Mono 数字拆分 | 规则同 Sans |
| `fonts/merged/<style>/uninoto_last_<N>.ttf` | Sans/Serif 共享补充拆分 | 非 full last 输出，没有简洁区域名时使用数字 |
| `fonts/merged/full/uninoto_<family>_upper<N>.ttf` | Full upper 拆分 | `full` 保留紧凑的 BMP/upper 命名 |

截至 2026-06-15 的 Unicode 17 合并审计，可见非 Mark 字符共 157088 个，覆盖率如下：

| 样式 | Sans + last | Sans | Serif + last | Serif | Mono |
|------|-------------|------|--------------|-------|------|
| `regular` | 79004 (50.293%) | 71214 (45.334%) | 79004 (50.293%) | 61390 (39.080%) | 71630 (45.599%) |
| `bold` | 54574 (34.741%) | 53934 (34.334%) | 54574 (34.741%) | 51155 (32.565%) | 54196 (34.500%) |
| `italic` | 2853 (1.816%) | 2794 (1.779%) | 2853 (1.816%) | 2722 (1.733%) | 2794 (1.779%) |
| `bolditalic` | 2814 (1.791%) | 2755 (1.754%) | 2814 (1.791%) | 2722 (1.733%) | 2755 (1.754%) |
| `full` | 156539 (99.651%) | 152703 (97.209%) | 156539 (99.651%) | 143723 (91.492%) | 152703 (97.209%) |

## 字体来源

uninoto 按请求样式合并以下来源的静态 TTF/OTF 字体，并排除变量字体。标准样式只接受明确匹配的样式来源：

- `regular`：明确标记为 Regular 的静态来源
- `bold`：Bold / Black / ExtraBold / SemiBold 来源
- `italic`：Italic / Oblique 来源
- `bolditalic`：Bold Italic 来源
- `full`：明确 Regular 加上样式不确定的静态来源，用来尽可能提高 regular 风格覆盖率

`regular`、`bold`、`italic` 和 `bolditalic` 各自独立合并。标准样式只使用明确匹配的来源，不回退或混入其他样式变体。

### 主要来源 —— Noto 字体

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

当前剩余可见缺口主要集中在较新的 Unicode 16/17 文字和 Tangut 相关区块。Noto 已有若干 OFL 源码仓库，例如 [Gurung Khema](https://github.com/notofonts/gurung-khema) 与 [Ol Onal](https://github.com/notofonts/ol-onal)，但目前没有发布 Regular/static TTF 文件或 release asset。因此在出现直接字体产物，或项目加入源码构建流程之前，下载脚本暂不默认接入这些仓库。

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
# 默认 4 个 worker，以便在保留排版数据时减少内存/IO 争抢
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
