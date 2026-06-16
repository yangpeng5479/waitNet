#!/usr/bin/env python3
"""Download static FFmpeg binaries for bundling into the application."""

from __future__ import annotations

import argparse
import platform
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOURCES = ROOT / "resources" / "ffmpeg"

# Official static builds maintained by the community.
MAC_URL = "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip"
WIN_URL = (
    "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
)


def _download(url: str, destination: Path) -> None:
    print(f"Downloading: {url}")
    with urllib.request.urlopen(url, timeout=120) as response:
        destination.write_bytes(response.read())


def _chmod_executable(path: Path) -> None:
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def install_macos() -> Path:
    target = RESOURCES / "macos" / "ffmpeg"
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "ffmpeg.zip"
        _download(MAC_URL, archive)
        with zipfile.ZipFile(archive) as zf:
            zf.extract("ffmpeg", tmp)
        shutil.copy2(Path(tmp) / "ffmpeg", target)
    _chmod_executable(target)
    return target


def install_windows() -> Path:
    target = RESOURCES / "windows" / "ffmpeg.exe"
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "ffmpeg.zip"
        _download(WIN_URL, archive)
        with zipfile.ZipFile(archive) as zf:
            names = [n for n in zf.namelist() if n.endswith("/bin/ffmpeg.exe")]
            if not names:
                raise RuntimeError("ffmpeg.exe not found in Windows archive")
            zf.extract(names[0], tmp)
            extracted = Path(tmp) / names[0]
        shutil.copy2(extracted, target)
    return target


def install_linux() -> Path:
    target = RESOURCES / "linux" / "ffmpeg"
    target.parent.mkdir(parents=True, exist_ok=True)

    url = "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz"
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "ffmpeg.tar.xz"
        _download(url, archive)
        with tarfile.open(archive, "r:xz") as tf:
            members = [m for m in tf.getmembers() if m.name.endswith("/ffmpeg")]
            if not members:
                raise RuntimeError("ffmpeg binary not found in Linux archive")
            tf.extract(members[0], tmp)
            extracted = Path(tmp) / members[0].name
        shutil.copy2(extracted, target)
    _chmod_executable(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Download FFmpeg for bundling")
    parser.add_argument(
        "--platform",
        choices=["macos", "windows", "linux", "auto"],
        default="auto",
    )
    args = parser.parse_args()

    system = platform.system().lower()
    if args.platform == "auto":
        if system == "darwin":
            platform_name = "macos"
        elif system == "windows":
            platform_name = "windows"
        else:
            platform_name = "linux"
    else:
        platform_name = args.platform

    installers = {
        "macos": install_macos,
        "windows": install_windows,
        "linux": install_linux,
    }
    target = installers[platform_name]()
    print(f"Installed FFmpeg to: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
