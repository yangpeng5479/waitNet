"""Format file sizes and compute compression statistics."""

from __future__ import annotations


def format_size(num_bytes: int) -> str:
    if num_bytes < 0:
        return "-"
    if num_bytes < 1024:
        return f"{num_bytes} B"
    if num_bytes < 1024 * 1024:
        return f"{num_bytes / 1024:.1f} KB"
    return f"{num_bytes / (1024 * 1024):.2f} MB"


def savings_percent(original: int, compressed: int) -> float:
    if original <= 0:
        return 0.0
    return max(0.0, (original - compressed) / original * 100.0)


def format_savings(original: int, compressed: int) -> str:
    if original <= 0 or compressed < 0:
        return "-"
    pct = savings_percent(original, compressed)
    saved = original - compressed
    sign = "+" if saved < 0 else ""
    return f"{sign}{format_size(abs(saved))} ({pct:.1f}%)"
