"""Resolve bundled or system FFmpeg executable path."""

from __future__ import annotations

import os
import platform
import shutil
import stat
import sys
from pathlib import Path


def _project_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[2]


def bundled_ffmpeg_path() -> Path:
    system = platform.system().lower()
    root = _project_root()
    if system == "darwin":
        return root / "resources" / "ffmpeg" / "macos" / "ffmpeg"
    if system == "windows":
        return root / "resources" / "ffmpeg" / "windows" / "ffmpeg.exe"
    return root / "resources" / "ffmpeg" / "linux" / "ffmpeg"


def resolve_ffmpeg_executable() -> tuple[Path | None, str]:
    """Return (path, error_message). path is None when unavailable."""
    bundled = bundled_ffmpeg_path()
    if bundled.is_file():
        if os.name != "nt":
            mode = bundled.stat().st_mode
            if not mode & stat.S_IXUSR:
                try:
                    bundled.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
                except OSError:
                    pass
        return bundled, ""

    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg), ""

    platform_name = platform.system()
    return None, (
        f"未找到 FFmpeg 可执行文件（平台：{platform_name}）。\n"
        f"请将对应平台的 ffmpeg 放到：{bundled}"
    )
