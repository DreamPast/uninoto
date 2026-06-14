# uninoto — 通用 Unicode 覆盖字体

[English](./README.md) | **简体中文**

uninoto 旨在创建一套能够显示绝大部分 Unicode 可见字符的通用字体。本项目主要以Noto作为主字体，结合了其余免费可商用后备字体，实现对绝大部分可见字符的覆盖。

## 字体结果

当前项目有三个族，`sans`（无衬线）、`serif`（衬线）和`mono`（等宽），由Google Noto Fonts合并而来，CJK汉字优先使用**简体中文**字形。

由于单个TTF最多包含65535个glyph，因此每个族包含三个ttf：

- 无后缀的覆盖U+0~U+FFFF
- `upper1`和`upper2`包含U+FFFF之后的码点

`uninoto_last.ttf`包含了若干其余免费可商用后备字体，用于补充`sans`和`serif`。

`mono`族字体经过等宽处理，advance width 为半宽 600 或全宽 1000。

当前项目输出如下文件：

- uninoto_sans.ttf
- uninoto_sans_upper1.ttf
- uninoto_sans_upper2.ttf
- uninoto_serif.ttf
- uninoto_serif_upper1.ttf
- uninoto_serif_upper2.ttf
- uninoto_mono.ttf
- uninoto_mono_upper1.ttf
- uninoto_mono_upper2.ttf
- uninoto_last.ttf

截至 2026-06-14 的 Unicode 17 合并审计，一共有 159563 个可见字符，覆盖率如下：

- `sans`（包含`last`）：159018 / 159563，99.656%
- `serif`（包含`last`）：159018 / 159563，99.656%
- `mono`：155120 / 159563，97.252%

## 字体来源

uninoto 合并以下来源的字体（均为 Regular/static 字重，排除 Bold、Oblique、Variable 等变体）：

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

# 3. 合并字体并生成审计报告
pypy3 src/merge.py
```

### 审计报告

合并完成后，以下报告写入 `fonts/reports/`：

- `sans-plane-font-coverage.csv` / `serif-plane-font-coverage.csv` / `mono-plane-font-coverage.csv`：每个码位来自哪个源字体
- `sans-missing-visible.csv` / `serif-missing-visible.csv` / `mono-missing-visible.csv`：合并后仍缺失的可见码点
- `sans-missing-visible-without_last.csv` / `serif-missing-visible-without_last.csv`：不含 `uninoto_last*` 补充的缺失码点

## 许可证

### 构建脚本

`src/` 目录下的构建脚本以 **MIT License** 发布。

### 生成字体

合并输出的字体（`fonts/merged/uninoto_*.ttf`）是由 [LICENSE](./LICENSE) 中列出的源字体构成的复合/衍生作品。源字体的许可证与声明继续保留；生成字体的元数据会指向本仓库的许可证清单。

### 源字体许可证

所有源字体的许可证文本、许可证引用与来源声明收录在仓库根目录的 [LICENSE](./LICENSE) 文件中，包括：

- **SIL Open Font License 1.1**（Noto 系列、多数 BabelStone script fonts、Padauk、Scheherazade New、Harmattan、Charis SIL、Doulos SIL、Junicode、Kanchenjunga、Kedebideri、Fairfax HD、Scriptwide Sans CJK、Cascadia Code 等）
- **CC0 1.0 Universal**（Jigmo 字云）
- **Arphic Public License**（BabelStone Han）
- **Hanazono Font License**（HanaMinB、HanaMinC，亦可用 OFL 1.1）
- **George Douros 自由使用声明**（Abydos）

详细的源字体文件列表及对应许可证条款请参阅 [LICENSE](./LICENSE)。
