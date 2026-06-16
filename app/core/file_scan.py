"""Scan source directories for MP3 files."""

from __future__ import annotations

from pathlib import Path


def scan_mp3_files(source_dir: str | Path) -> list[Path]:
    directory = Path(source_dir)
    if not directory.is_dir():
        return []
    return sorted(
        p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".mp3"
    )


def validate_paths(source_dir: str | Path, output_dir: str | Path) -> tuple[bool, str]:
    src = Path(source_dir)
    dst = Path(output_dir)

    if not src.is_dir():
        return False, "源文件夹不存在或不可访问。"
    if not dst.exists():
        try:
            dst.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return False, f"无法创建目标文件夹：{exc}"
    if not dst.is_dir():
        return False, "目标路径不是文件夹。"
    return True, ""
