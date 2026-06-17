from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from .sfd_to_ttf import build_ttf_from_sfd

GITHUB_API = "https://api.github.com"
NOTO_CJK_RELEASE_TAGS = ("Sans2.004", "Serif2.003")
NOTO_MONTHLY_REF_PREFIX = "noto-monthly-release-"
NOTO_MONTHLY_REFS = f"{GITHUB_API}/repos/notofonts/notofonts.github.io/git/matching-refs/tags/{NOTO_MONTHLY_REF_PREFIX}"
NOTO_EMOJI_BRANCH = "main"
NOTO_EMOJI_MONOCHROME_URL = (
    "https://mirrors.ctan.org/fonts/noto-emoji/NotoEmoji-Regular.ttf"
)
BABELSTONE_FONTS_URL = "https://www.babelstone.co.uk/Fonts/"
USER_AGENT = "uninoto-downloader/3.0"
LEGACY_NOTO_SOURCE_DIRS = ("noto-fonts", "noto-cjkext", "noto-extra")
NOTO_EMOJI_FILES = (
    "fonts/Noto-COLRv1.ttf",
    "fonts/Noto-COLRv1-noflags.ttf",
    "fonts/NotoColorEmoji.ttf",
    "fonts/NotoColorEmoji-noflags.ttf",
)


@dataclass(frozen=True)
class DownloadItem:
    url: str
    relative_path: Path
    extract: bool = False


FALLBACK_ITEMS: tuple[tuple[str, Path], ...] = (
    (
        "https://kamichikoichi.github.io/jigmo/Jigmo-20250912.zip",
        Path("fallback/Jigmo-20250912.zip"),
    ),
    (
        "https://github.com/silnrsi/font-padauk/releases/download/v6.000/Padauk-6.000.zip",
        Path("fallback/Padauk-6.000.zip"),
    ),
    (
        "https://github.com/silnrsi/font-scheherazade/releases/download/v4.500/ScheherazadeNew-4.500.zip",
        Path("fallback/ScheherazadeNew-4.500.zip"),
    ),
    (
        "https://github.com/silnrsi/font-harmattan/releases/download/v4.400/Harmattan-4.400.zip",
        Path("fallback/Harmattan-4.400.zip"),
    ),
    (
        "https://github.com/microsoft/cascadia-code/releases/download/v2407.24/CascadiaCode-2407.24.zip",
        Path("fallback/CascadiaCode-2407.24.zip"),
    ),
    (
        "https://github.com/cjkvi/HanaMinAFDKO/releases/download/8.030/HanaMinB.otf",
        Path("fallback/HanaMin/HanaMinB.otf"),
    ),
    (
        "https://github.com/cjkvi/HanaMinAFDKO/releases/download/8.030/HanaMinC.otf",
        Path("fallback/HanaMin/HanaMinC.otf"),
    ),
    (
        "https://github.com/scriptwide-fonts/scriptwide-sans-cjk/releases/download/v1.004/ScriptwideSansCJK-A.ttf",
        Path("fallback/ScriptwideSansCJK/ScriptwideSansCJK-A.ttf"),
    ),
    (
        "https://github.com/scriptwide-fonts/scriptwide-sans-cjk/releases/download/v1.004/ScriptwideSansCJK-B.ttf",
        Path("fallback/ScriptwideSansCJK/ScriptwideSansCJK-B.ttf"),
    ),
    (
        "https://github.com/scriptwide-fonts/scriptwide-sans-cjk/releases/download/v1.004/ScriptwideSansCJK-C.ttf",
        Path("fallback/ScriptwideSansCJK/ScriptwideSansCJK-C.ttf"),
    ),
    (
        "https://github.com/Fitzgerald-Porthmouth-Koenigsegg/Plangothic_Project/releases/download/V2.9.5792/PlangothicP2-Regular.ttf",
        Path("fallback/Plangothic/PlangothicP2-Regular.ttf"),
    ),
    (
        "https://github.com/notofonts/khitan-small-script/releases/download/NotoFangsongKSSVertical-v1.000/NotoFangsongKSSVertical-v1.000.zip",
        Path("fallback/NotoFangsongKSSVertical-v1.000.zip"),
    ),
    (
        "https://github.com/notofonts/dives-akuru/releases/download/NotoSerifDivesAkuru-v2.000/NotoSerifDivesAkuru-v2.000.zip",
        Path("fallback/NotoSerifDivesAkuru-v2.000.zip"),
    ),
    (
        "https://github.com/silnrsi/font-kanchenjunga/releases/download/v2.001/Kanchenjunga-2.001.zip",
        Path("fallback/Kanchenjunga-2.001.zip"),
    ),
    (
        "https://github.com/psb1558/Junicode-font/releases/download/v2.224/Junicode_2.224.zip",
        Path("fallback/Junicode_2.224.zip"),
    ),
    (
        "https://github.com/silnrsi/font-kedebideri/releases/download/v3.001/Kedebideri-3.001.zip",
        Path("fallback/Kedebideri-3.001.zip"),
    ),
    (
        "https://github.com/silnrsi/font-charis/releases/download/v7.000/Charis-7.000.zip",
        Path("fallback/Charis-7.000.zip"),
    ),
    (
        "https://github.com/silnrsi/font-doulos/releases/download/v7.000/DoulosSIL-7.000.zip",
        Path("fallback/DoulosSIL-7.000.zip"),
    ),
    (
        "https://download.opensuse.org/tumbleweed/repo/oss/noarch/gdouros-abydos-fonts-1.96-2.13.noarch.rpm",
        Path("fallback/gdouros-abydos-fonts-1.96-2.13.noarch.rpm"),
    ),
    (
        "https://www.kreativekorp.com/swdownload/fonts/core/fairfaxhd.zip",
        Path("fallback/fairfaxhd.zip"),
    ),
    (
        "https://github.com/unicode-org/last-resort-font/releases/download/17.000/LastResort-Regular.ttf",
        Path("fallback/LastResort/LastResort-Regular.ttf"),
    ),
    (
        "https://raw.githubusercontent.com/notofonts/ol-onal/main/sources/NotoSerifOlOnal.sfd",
        Path("fallback/NotoSourceBuilds/NotoSerifOlOnal.sfd"),
    ),
    (
        "https://raw.githubusercontent.com/notofonts/gurung-khema/main/sources/NotoSansGurungKhema.sfd",
        Path("fallback/NotoSourceBuilds/NotoSansGurungKhema.sfd"),
    ),
)

SFD_OUTPUT_NAMES: dict[str, str] = {
    "NotoSerifOlOnal.sfd": "NotoSerifOlOnal-Regular.ttf",
    "NotoSansGurungKhema.sfd": "NotoSansGurungKhema-Regular.ttf",
}


def headers() -> dict[str, str]:
    result = {"Accept": "application/vnd.github+json", "User-Agent": USER_AGENT}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        result["Authorization"] = f"Bearer {token}"
    return result


def request(url: str, range_start: int | None = None) -> urllib.request.Request:
    request_headers = headers()
    if range_start is not None and range_start > 0:
        request_headers["Range"] = f"bytes={range_start}-"
    return urllib.request.Request(url, headers=request_headers)


def request_json(url: str) -> object:
    with urllib.request.urlopen(request(url), timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(url: str) -> str:
    with urllib.request.urlopen(request(url), timeout=120) as response:
        return response.read().decode("utf-8", errors="replace")


def object_mapping(value: object, label: str) -> Mapping[str, object]:
    if isinstance(value, dict):
        return cast(Mapping[str, object], value)
    raise ValueError(f"{label} response was not an object")


def object_list(value: object, label: str) -> list[object]:
    if isinstance(value, list):
        return value
    raise ValueError(f"{label} response was not a list")


def exists_non_empty(path: Path) -> bool:
    return path.exists() and path.stat().st_size > 0


def download_file(url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.stat().st_size if target.exists() else 0
    mode = "ab" if existing else "wb"
    try:
        with urllib.request.urlopen(request(url, existing), timeout=120) as response:
            if existing and response.status != 206:
                existing = 0
                mode = "wb"
            total_header = response.headers.get("Content-Length")
            total = (
                int(total_header) + existing
                if total_header and existing
                else int(total_header or 0)
            )
            downloaded = existing
            with target.open(mode) as fh:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
                    downloaded += len(chunk)
        total_text = f"/{total / 1024 / 1024:.1f} MiB" if total else ""
        print(f"downloaded: {target} ({downloaded / 1024 / 1024:.1f}{total_text})")
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and exists_non_empty(target):
            print(f"skip existing: {target}")
            return
        raise


def monthly_tag_sort_key(tag: str) -> int:
    match = re.match(
        rf"^{NOTO_MONTHLY_REF_PREFIX}(\d{{2,4}})\.(\d{{1,2}})\.(\d{{1,2}})$", tag
    )
    if not match:
        return 0
    year = int(match.group(1))
    if year < 100:
        year += 2000
    return year * 10000 + int(match.group(2)) * 100 + int(match.group(3))


def repo_zip_url(owner: str, repo: str, ref: str) -> str:
    ref_path = ref if ref.startswith("refs/") else f"tags/{ref}"
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/{ref_path}"


def branch_zip_url(owner: str, repo: str, branch: str) -> str:
    return f"https://codeload.github.com/{owner}/{repo}/zip/refs/heads/{branch}"


def latest_monthly_tag() -> str:
    refs = object_list(request_json(NOTO_MONTHLY_REFS), "Noto monthly refs")
    tags = sorted(
        (
            str(entry.get("ref", "")).replace("refs/tags/", "")
            for entry in refs
            if isinstance(entry, dict)
        ),
        key=monthly_tag_sort_key,
        reverse=True,
    )
    tags = [tag for tag in tags if monthly_tag_sort_key(tag) > 0]
    if not tags:
        raise ValueError("no Noto monthly release tags found")
    return str(tags[0])


def monthly_source_paths(data: Mapping[str, object]) -> list[str]:
    by_family: dict[str, list[str]] = {}
    tree = data.get("tree", [])
    if not isinstance(tree, list):
        return []
    for entry in tree:
        if not isinstance(entry, dict):
            continue
        if entry.get("type") != "blob":
            continue
        source_path = str(entry.get("path", ""))
        match = re.match(
            r"^fonts/([^/]+)/(googlefonts/ttf|hinted/ttf|full/ttf)/.+\.ttf$",
            source_path,
            re.I,
        )
        if not match:
            continue
        by_family.setdefault(match.group(1), []).append(source_path)
    result: list[str] = []
    for paths in by_family.values():
        # Prefer the release TTFs used by Google Fonts; older families may only have hinted/full TTFs.
        google = [
            p
            for p in paths
            if re.match(r"^fonts/[^/]+/googlefonts/ttf/.+\.ttf$", p, re.I)
        ]
        hinted = [
            p for p in paths if re.match(r"^fonts/[^/]+/hinted/ttf/.+\.ttf$", p, re.I)
        ]
        full = [
            p for p in paths if re.match(r"^fonts/[^/]+/full/ttf/.+\.ttf$", p, re.I)
        ]
        result.extend(google or hinted or full)
    return sorted(result)


def strip_repo_zip_prefix(entry_name: str) -> str:
    normalized = entry_name.replace("\\", "/")
    return normalized[normalized.find("/") + 1 :]


def extract_selected_from_repo_zip(
    archive: Path,
    source_paths: list[str] | tuple[str, ...],
    target_for_source_path: Callable[[str], Path],
) -> int:
    wanted = set(source_paths)
    extracted = 0
    with zipfile.ZipFile(archive) as zf:
        for entry in zf.infolist():
            if entry.is_dir():
                continue
            source_path = strip_repo_zip_prefix(entry.filename)
            if source_path not in wanted:
                continue
            target = target_for_source_path(source_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(entry))
            extracted += 1
    return extracted


def download_noto_monthly_repo(tag: str, output_root: Path) -> int:
    data = object_mapping(
        request_json(
            f"{GITHUB_API}/repos/notofonts/notofonts.github.io/git/trees/{tag}?recursive=1"
        ),
        "Noto monthly tree",
    )
    if data.get("truncated"):
        raise ValueError("Noto monthly tree response was truncated")
    source_paths = monthly_source_paths(data)
    archive = output_root / "archives" / f"notofonts.github.io-{tag}.zip"
    download_file(repo_zip_url("notofonts", "notofonts.github.io", tag), archive)
    shutil.rmtree(output_root / "noto-monthly", ignore_errors=True)
    return extract_selected_from_repo_zip(
        archive,
        source_paths,
        lambda source_path: output_root
        / "noto-monthly"
        / (source_path.split("/")[1] if "/" in source_path else "unknown")
        / Path(source_path).name,
    )


def cjk_release_assets() -> list[DownloadItem]:
    items: list[DownloadItem] = []
    for tag in NOTO_CJK_RELEASE_TAGS:
        data = object_mapping(
            request_json(f"{GITHUB_API}/repos/notofonts/noto-cjk/releases/tags/{tag}"),
            "Noto CJK release",
        )
        assets = data.get("assets", [])
        if not isinstance(assets, list):
            continue
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            name = str(asset.get("name", ""))
            url = asset.get("browser_download_url")
            if isinstance(url, str) and re.match(
                r"^\d+_Noto(Sans|Serif)(Mono)?CJK(jp|kr|sc|tc|hk)\.zip$", name, re.I
            ):
                items.append(
                    DownloadItem(url, Path("noto-cjk") / tag / "archives" / name, True)
                )
    return sorted(items, key=lambda item: item.relative_path.as_posix())


def unique_download_items(items: list[DownloadItem]) -> list[DownloadItem]:
    result: dict[Path, DownloadItem] = {}
    for item in items:
        result[item.relative_path] = item
    return sorted(result.values(), key=lambda item: item.relative_path.as_posix())


def babelstone_font_pages(index_html: str) -> list[str]:
    pages = []
    for href in re.findall(r'href="([^"]+\.html)"', index_html, flags=re.I):
        if href.startswith("../"):
            continue
        pages.append(urllib.parse.urljoin(BABELSTONE_FONTS_URL, href))
    return sorted(set(pages))


def babelstone_downloads(html: str) -> list[DownloadItem]:
    items: list[DownloadItem] = []
    for download_path in re.findall(
        r"Download/[^\"'<> ]+\.(?:ttf|zip|otf)", html, flags=re.I
    ):
        if re.search(r"/BabelStoneHan-\d", download_path):
            continue
        url = urllib.parse.urljoin(BABELSTONE_FONTS_URL, download_path)
        items.append(
            DownloadItem(
                url,
                Path("fallback/BabelStone")
                / Path(
                    urllib.request.url2pathname(urllib.parse.urlparse(url).path)
                ).name,
                True,
            )
        )
    return items


def babelstone_fallback_items() -> list[DownloadItem]:
    index_html = request_text(BABELSTONE_FONTS_URL)
    items = babelstone_downloads(index_html)
    for page_url in babelstone_font_pages(index_html):
        items.extend(babelstone_downloads(request_text(page_url)))
    return unique_download_items(items)


def fallback_items() -> list[DownloadItem]:
    return unique_download_items(
        [
            *babelstone_fallback_items(),
            *(DownloadItem(url, path, True) for url, path in FALLBACK_ITEMS),
        ]
    )


def emoji_items() -> list[DownloadItem]:
    return [
        DownloadItem(
            NOTO_EMOJI_MONOCHROME_URL, Path("noto-emoji/NotoEmoji-Regular.ttf")
        ),
        DownloadItem(
            branch_zip_url("googlefonts", "noto-emoji", NOTO_EMOJI_BRANCH),
            Path(f"archives/noto-emoji-{NOTO_EMOJI_BRANCH}.zip"),
        ),
    ]


def cleanup_legacy_noto_sources(output_root: Path) -> None:
    for name in LEGACY_NOTO_SOURCE_DIRS:
        shutil.rmtree(output_root / name, ignore_errors=True)


def extract_noto_emoji_repo(archive: Path, output_root: Path) -> int:
    for source_path in NOTO_EMOJI_FILES:
        (output_root / "noto-emoji" / Path(source_path).name).unlink(missing_ok=True)
    return extract_selected_from_repo_zip(
        archive,
        NOTO_EMOJI_FILES,
        lambda source_path: output_root / "noto-emoji" / Path(source_path).name,
    )


def extract_font_zip(
    archive: Path, output_root: Path, target_root: Path | None = None
) -> int:
    archive_dir_name = archive.parent.parent.name
    root = target_root or output_root / "noto-cjk" / archive_dir_name / archive.stem
    shutil.rmtree(root, ignore_errors=True)
    extracted = 0
    with zipfile.ZipFile(archive) as zf:
        for entry in zf.infolist():
            if entry.is_dir() or not re.search(r"\.(ttf|otf)$", entry.filename, re.I):
                continue
            target = root / Path(entry.filename).name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(entry))
            extracted += 1
    return extracted


def run_tool(command: str, args: list[str]) -> None:
    completed = subprocess.run(
        [command, *args], check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise RuntimeError(
            completed.stderr.strip() or f"{command} exited with {completed.returncode}"
        )


def extract_abydos_rpm(archive: Path, output_root: Path) -> int:
    if archive.name != "gdouros-abydos-fonts-1.96-2.13.noarch.rpm":
        return 0
    root = archive.with_suffix("")
    root.mkdir(parents=True, exist_ok=True)
    run_tool("7z", ["x", str(archive), f"-o{root}", "-y"])
    cpio = next((path for path in root.iterdir() if path.suffix == ".cpio"), None)
    if not cpio:
        return 0
    payload_root = root / "payload"
    payload_root.mkdir(parents=True, exist_ok=True)
    run_tool("7z", ["x", str(cpio), f"-o{payload_root}", "-y"])
    source = payload_root / "usr/share/fonts/truetype/Abydos.ttf"
    if not exists_non_empty(source):
        return 0
    target = output_root / "fallback/Abydos.ttf"
    if exists_non_empty(target):
        return 0
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return 1


def is_babelstone_archive(archive: Path) -> bool:
    return "/fallback/babelstone/" in archive.as_posix().lower()


def extraction_root_for(archive: Path, output_root: Path) -> Path:
    normalized = archive.as_posix().lower()
    if "/noto-cjk/" in normalized and "/archives/" in normalized:
        archive_dir_name = archive.parent.parent.name
        return output_root / "noto-cjk" / archive_dir_name / archive.stem
    return archive.with_suffix("")


def list_archives(root: Path, suffix: str) -> list[Path]:
    return (
        sorted(
            (p for p in root.rglob(f"*{suffix}") if p.is_file()),
            key=lambda p: str(p).lower(),
        )
        if root.exists()
        else []
    )


def handle_item(item: DownloadItem, output_root: Path) -> None:
    target = output_root / item.relative_path
    download_file(item.url, target)
    if target.name.startswith("noto-emoji-") and target.suffix.lower() == ".zip":
        print(
            f"extracted {extract_noto_emoji_repo(target, output_root)} font files from {target.name}"
        )
    elif target.suffix.lower() == ".sfd":
        output_name = SFD_OUTPUT_NAMES.get(target.name)
        if output_name:
            output = target.with_name(output_name)
            build_ttf_from_sfd(target, output)
            print(f"built {output.name} from {target.name}")
    elif target.suffix.lower() == ".zip" and is_babelstone_archive(target):
        print(f"kept BabelStone archive without extraction: {target.name}")
    elif target.suffix.lower() == ".zip":
        print(
            f"extracted {extract_font_zip(target, output_root, extraction_root_for(target, output_root))} font files from {target.name}"
        )
    elif target.suffix.lower() == ".rpm":
        print(
            f"extracted {extract_abydos_rpm(target, output_root)} font files from {target.name}"
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="fonts/noto")
    parser.add_argument("--skip-fallback", action="store_true")
    parser.add_argument("--fallback-only", action="store_true")
    parser.add_argument("--extract-existing", action="store_true")
    parser.add_argument("--monthly-tag")
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    output_root = Path(args.output)
    output_root.mkdir(parents=True, exist_ok=True)
    if args.concurrency < 1:
        raise ValueError(f"invalid concurrency: {args.concurrency}")
    if args.extract_existing:
        archives = [
            *list_archives(output_root / "noto-cjk", ".zip"),
            *list_archives(output_root / "archives", ".zip"),
            *list_archives(output_root / "fallback", ".zip"),
            *list_archives(output_root / "fallback", ".rpm"),
            *list_archives(output_root / "fallback", ".sfd"),
        ]
        for archive in archives:
            if archive.suffix.lower() == ".rpm":
                print(
                    f"extracted {extract_abydos_rpm(archive, output_root)} font files from {archive.name}"
                )
            elif archive.suffix.lower() == ".sfd":
                output_name = SFD_OUTPUT_NAMES.get(archive.name)
                if output_name:
                    output = archive.with_name(output_name)
                    build_ttf_from_sfd(archive, output)
                    print(f"built {output.name} from {archive.name}")
            elif archive.name.startswith("noto-emoji-"):
                print(
                    f"extracted {extract_noto_emoji_repo(archive, output_root)} font files from {archive.name}"
                )
            elif is_babelstone_archive(archive):
                print(f"kept BabelStone archive without extraction: {archive.name}")
            else:
                print(
                    f"extracted {extract_font_zip(archive, output_root, extraction_root_for(archive, output_root))} font files from {archive.name}"
                )
        return
    cleanup_legacy_noto_sources(output_root)
    if args.fallback_only and args.skip_fallback:
        raise ValueError("--fallback-only cannot be combined with --skip-fallback")
    items = (
        fallback_items()
        if args.fallback_only
        else [
            *cjk_release_assets(),
            *emoji_items(),
            *([] if args.skip_fallback else fallback_items()),
        ]
    )
    if not args.fallback_only:
        monthly_tag = args.monthly_tag or latest_monthly_tag()
        print(f"using Noto monthly build: {monthly_tag}")
        print(
            f"extracted {download_noto_monthly_repo(monthly_tag, output_root)} ordinary Noto TTF files from notofonts.github.io"
        )
    limited_items = items[: args.limit or None]
    with concurrent.futures.ThreadPoolExecutor(
        max_workers=args.concurrency
    ) as executor:
        list(executor.map(lambda item: handle_item(item, output_root), limited_items))
    print(f"done: {output_root}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"error: {exc}")
        raise SystemExit(1) from exc
