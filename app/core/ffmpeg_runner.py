"""FFmpeg batch compression runner with per-file progress reporting."""

from __future__ import annotations

import re
import subprocess
import threading
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from PySide6.QtCore import QObject, QThread, Signal

from app.core.compression_profiles import CompressionSettings
from app.core.ffmpeg_path import resolve_ffmpeg_executable


class TaskStatus(str, Enum):
    PENDING = "等待中"
    RUNNING = "压缩中"
    COMPLETED = "完成"
    FAILED = "失败"
    SKIPPED = "已跳过"
    CANCELLED = "已取消"


@dataclass
class FileTask:
    source_path: Path
    output_path: Path
    original_size: int = 0
    compressed_size: int = -1
    progress: int = 0
    status: TaskStatus = TaskStatus.PENDING
    message: str = ""
    duration_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.original_size == 0 and self.source_path.is_file():
            self.original_size = self.source_path.stat().st_size


TIME_RE = re.compile(r"time=(\d{2}):(\d{2}):(\d{2}\.\d+)")
DURATION_RE = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2}\.\d+)")


def _parse_hms(value: str) -> float:
    parts = value.split(":")
    if len(parts) != 3:
        return 0.0
    hours, minutes, seconds = parts
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


class CompressionWorker(QObject):
    task_updated = Signal(int)
    task_finished = Signal(int, bool, str)
    batch_progress = Signal(int, int)
    batch_finished = Signal()
    log_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._tasks: list[FileTask] = []
        self._settings: CompressionSettings | None = None
        self._stop_requested = False
        self._pause_event = threading.Event()
        self._pause_event.set()

    def configure(
        self,
        tasks: list[FileTask],
        settings: CompressionSettings,
    ) -> None:
        self._tasks = tasks
        self._settings = settings
        self._stop_requested = False
        self._pause_event.set()

    def request_stop(self) -> None:
        self._stop_requested = True
        self._pause_event.set()

    def pause(self) -> None:
        self._pause_event.clear()

    def resume(self) -> None:
        self._pause_event.set()

    def run(self) -> None:
        ffmpeg_path, error = resolve_ffmpeg_executable()
        if ffmpeg_path is None:
            for index, task in enumerate(self._tasks):
                if task.status in (TaskStatus.PENDING, TaskStatus.FAILED):
                    task.status = TaskStatus.FAILED
                    task.message = error
                    self.task_updated.emit(index)
            self.batch_finished.emit()
            return

        assert self._settings is not None
        completed = 0
        total = len(self._tasks)

        for index, task in enumerate(self._tasks):
            if self._stop_requested:
                if task.status == TaskStatus.PENDING:
                    task.status = TaskStatus.CANCELLED
                    task.message = "用户已停止"
                    self.task_updated.emit(index)
                continue

            if task.status not in (TaskStatus.PENDING, TaskStatus.FAILED):
                if task.status == TaskStatus.COMPLETED:
                    completed += 1
                continue

            self._pause_event.wait()
            if self._stop_requested:
                continue

            task.status = TaskStatus.RUNNING
            task.progress = 0
            task.message = "正在压缩..."
            self.task_updated.emit(index)
            self.batch_progress.emit(completed, total)

            success, message = self._compress_one(ffmpeg_path, task, index)
            if success:
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                if task.output_path.is_file():
                    task.compressed_size = task.output_path.stat().st_size
                task.message = "压缩完成"
                completed += 1
            else:
                task.status = TaskStatus.FAILED
                task.message = message

            self.task_updated.emit(index)
            self.task_finished.emit(index, success, message)
            self.batch_progress.emit(completed, total)

        self.batch_finished.emit()

    def _compress_one(
        self,
        ffmpeg_path: Path,
        task: FileTask,
        task_index: int,
    ) -> tuple[bool, str]:
        assert self._settings is not None
        task.output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            str(ffmpeg_path),
            "-y",
            "-hide_banner",
            "-i",
            str(task.source_path),
            *self._settings.build_ffmpeg_args(),
            str(task.output_path),
        ]

        duration = 0.0
        process: subprocess.Popen[str] | None = None

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except OSError as exc:
            return False, f"无法启动 FFmpeg：{exc}"

        assert process.stderr is not None
        stderr_lines: list[str] = []

        for line in process.stderr:
            if self._stop_requested:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                return False, "用户已停止"

            self._pause_event.wait()
            stderr_lines.append(line.rstrip())

            if duration <= 0:
                match = DURATION_RE.search(line)
                if match:
                    duration = _parse_hms(
                        f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
                    )
                    task.duration_seconds = duration

            match = TIME_RE.search(line)
            if match and duration > 0:
                current = _parse_hms(
                    f"{match.group(1)}:{match.group(2)}:{match.group(3)}"
                )
                progress = min(99, int(current / duration * 100))
                if progress > task.progress:
                    task.progress = progress
                    self.task_updated.emit(task_index)

        return_code = process.wait()
        if return_code != 0:
            tail = "\n".join(stderr_lines[-8:]).strip()
            return False, tail or f"FFmpeg 退出码 {return_code}"

        return True, "压缩完成"


class CompressionController(QObject):
    """High-level API used by the UI layer."""

    task_updated = Signal(int)
    task_finished = Signal(int, bool, str)
    batch_progress = Signal(int, int)
    batch_finished = Signal()
    log_message = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[FileTask] = []
        self._thread: QThread | None = None
        self._worker: CompressionWorker | None = None
        self._running = False

    @property
    def is_running(self) -> bool:
        return self._running

    def set_tasks(self, tasks: list[FileTask]) -> None:
        self.tasks = tasks

    def start(self, settings: CompressionSettings, retry_failed_only: bool = False) -> None:
        if self._running:
            return

        if retry_failed_only:
            for task in self.tasks:
                if task.status == TaskStatus.FAILED:
                    task.status = TaskStatus.PENDING
                    task.progress = 0
                    task.message = ""
                    task.compressed_size = -1
        else:
            for task in self.tasks:
                if task.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.PENDING
                    task.progress = 0
                    task.message = ""
                    task.compressed_size = -1

        self._thread = QThread()
        self._worker = CompressionWorker()
        self._worker.moveToThread(self._thread)

        self._worker.configure(self.tasks, settings)
        self._thread.started.connect(self._worker.run)
        self._worker.task_updated.connect(self.task_updated)
        self._worker.task_finished.connect(self.task_finished)
        self._worker.batch_progress.connect(self.batch_progress)
        self._worker.batch_finished.connect(self._on_batch_finished)
        self._worker.log_message.connect(self.log_message)

        self._running = True
        self._thread.start()

    def stop(self) -> None:
        if self._worker:
            self._worker.request_stop()

    def pause(self) -> None:
        if self._worker:
            self._worker.pause()

    def resume(self) -> None:
        if self._worker:
            self._worker.resume()

    def _on_batch_finished(self) -> None:
        self._running = False
        if self._thread:
            self._thread.quit()
            self._thread.wait(5000)
        self._thread = None
        self._worker = None
        self.batch_finished.emit()
