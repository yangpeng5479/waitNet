"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.compression_profiles import (
    PROFILES,
    CompressionSettings,
    RateMode,
    get_default_profile,
    get_profile_by_id,
)
from app.core.ffmpeg_path import resolve_ffmpeg_executable
from app.core.ffmpeg_runner import CompressionController, FileTask, TaskStatus
from app.core.file_scan import scan_mp3_files, validate_paths
from app.core.size_report import format_savings, format_size, savings_percent


class MainWindow(QMainWindow):
    COL_NAME = 0
    COL_ORIGINAL = 1
    COL_COMPRESSED = 2
    COL_SAVINGS = 3
    COL_PROGRESS = 4
    COL_STATUS = 5
    COL_MESSAGE = 6

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MP3 压缩工具")
        self.resize(1080, 720)

        self._controller = CompressionController()
        self._controller.task_updated.connect(self._on_task_updated)
        self._controller.batch_progress.connect(self._on_batch_progress)
        self._controller.batch_finished.connect(self._on_batch_finished)

        self._build_ui()
        self._apply_default_profile()
        self._check_ffmpeg_on_startup()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        root.addWidget(self._build_path_group())
        root.addWidget(self._build_settings_group())
        root.addWidget(self._build_control_group())
        root.addWidget(self._build_task_table_group(), stretch=1)
        root.addWidget(self._build_summary_group())
        root.addWidget(self._build_log_group())

    def _build_path_group(self) -> QGroupBox:
        group = QGroupBox("文件夹")
        layout = QFormLayout(group)

        self.source_edit = QLineEdit()
        self.source_btn = QPushButton("选择源文件夹")
        self.source_btn.clicked.connect(self._choose_source)

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_edit)
        source_row.addWidget(self.source_btn)

        self.output_edit = QLineEdit()
        self.output_btn = QPushButton("选择目标文件夹")
        self.output_btn.clicked.connect(self._choose_output)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_btn)

        layout.addRow("源文件夹", source_row)
        layout.addRow("目标文件夹", output_row)
        return group

    def _build_settings_group(self) -> QGroupBox:
        group = QGroupBox("压缩配置")
        layout = QHBoxLayout(group)

        form = QFormLayout()
        self.profile_combo = QComboBox()
        for profile in PROFILES:
            self.profile_combo.addItem(profile.name, profile.id)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)

        self.profile_desc = QLabel()
        self.profile_desc.setWordWrap(True)
        self.profile_desc.setStyleSheet("color: #666;")

        self.channels_combo = QComboBox()
        self.channels_combo.addItem("单声道 (1)", 1)
        self.channels_combo.addItem("立体声 (2)", 2)

        self.rate_mode_combo = QComboBox()
        self.rate_mode_combo.addItem("VBR 质量 (qscale)", RateMode.VBR.value)
        self.rate_mode_combo.addItem("固定比特率 (CBR)", RateMode.CBR.value)
        self.rate_mode_combo.currentIndexChanged.connect(self._on_rate_mode_changed)

        self.qscale_spin = QSpinBox()
        self.qscale_spin.setRange(0, 9)
        self.qscale_spin.setValue(8)
        self.qscale_spin.setToolTip("数值越小音质越好，文件越大")

        self.bitrate_combo = QComboBox()
        for rate in (32, 48, 64, 96, 128, 192, 256, 320):
            self.bitrate_combo.addItem(f"{rate} kbps", rate)
        self.bitrate_combo.setCurrentIndex(3)

        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItem("保持原始", None)
        for rate in (22050, 32000, 44100, 48000):
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)

        form.addRow("预设", self.profile_combo)
        form.addRow("声道", self.channels_combo)
        form.addRow("压缩方式", self.rate_mode_combo)
        form.addRow("VBR 质量", self.qscale_spin)
        form.addRow("比特率", self.bitrate_combo)
        form.addRow("采样率", self.sample_rate_combo)

        layout.addLayout(form, stretch=2)
        layout.addWidget(self.profile_desc, stretch=3)
        return group

    def _build_control_group(self) -> QGroupBox:
        group = QGroupBox("批处理控制")
        layout = QHBoxLayout(group)

        self.scan_btn = QPushButton("扫描 MP3")
        self.scan_btn.clicked.connect(self._scan_files)

        self.start_btn = QPushButton("开始压缩")
        self.start_btn.clicked.connect(self._start_compression)

        self.pause_btn = QPushButton("暂停")
        self.pause_btn.clicked.connect(self._pause_compression)
        self.pause_btn.setEnabled(False)

        self.resume_btn = QPushButton("继续")
        self.resume_btn.clicked.connect(self._resume_compression)
        self.resume_btn.setEnabled(False)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.clicked.connect(self._stop_compression)
        self.stop_btn.setEnabled(False)

        self.retry_btn = QPushButton("重试失败项")
        self.retry_btn.clicked.connect(self._retry_failed)

        self.overall_label = QLabel("总体进度：0 / 0")
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)

        layout.addWidget(self.scan_btn)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.resume_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.retry_btn)
        layout.addStretch()
        layout.addWidget(self.overall_label)
        layout.addWidget(self.overall_bar, stretch=1)
        return group

    def _build_task_table_group(self) -> QGroupBox:
        group = QGroupBox("文件任务列表")
        layout = QVBoxLayout(group)

        self.task_table = QTableWidget(0, 7)
        self.task_table.setHorizontalHeaderLabels(
            ["文件名", "原始大小", "压缩后", "节省", "进度", "状态", "备注"]
        )
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.verticalHeader().setVisible(False)
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        self.task_table.setColumnWidth(self.COL_NAME, 260)
        self.task_table.setColumnWidth(self.COL_ORIGINAL, 110)
        self.task_table.setColumnWidth(self.COL_COMPRESSED, 110)
        self.task_table.setColumnWidth(self.COL_SAVINGS, 120)
        self.task_table.setColumnWidth(self.COL_PROGRESS, 180)
        self.task_table.setColumnWidth(self.COL_STATUS, 100)
        self.task_table.setColumnWidth(self.COL_MESSAGE, 260)

        layout.addWidget(self.task_table)
        return group

    def _build_summary_group(self) -> QGroupBox:
        group = QGroupBox("汇总统计")
        layout = QHBoxLayout(group)
        self.summary_label = QLabel("尚未开始压缩")
        layout.addWidget(self.summary_label)
        return group

    def _build_log_group(self) -> QGroupBox:
        group = QGroupBox("日志")
        layout = QVBoxLayout(group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(self.log_view)
        return group

    def _apply_default_profile(self) -> None:
        default = get_default_profile()
        index = self.profile_combo.findData(default.id)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self._on_profile_changed()

    def _check_ffmpeg_on_startup(self) -> None:
        path, error = resolve_ffmpeg_executable()
        if path:
            self._append_log(f"FFmpeg: {path}")
        else:
            self._append_log(error)
            QMessageBox.warning(self, "FFmpeg 未就绪", error)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)

    def _choose_source(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if path:
            self.source_edit.setText(path)

    def _choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if path:
            self.output_edit.setText(path)

    def _on_profile_changed(self) -> None:
        profile = get_profile_by_id(self.profile_combo.currentData())
        self.profile_desc.setText(profile.description)
        settings = profile.settings

        channel_index = self.channels_combo.findData(settings.channels)
        if channel_index >= 0:
            self.channels_combo.setCurrentIndex(channel_index)

        mode_index = self.rate_mode_combo.findData(settings.rate_mode.value)
        if mode_index >= 0:
            self.rate_mode_combo.setCurrentIndex(mode_index)

        self.qscale_spin.setValue(settings.qscale)
        if settings.bitrate_kbps:
            br_index = self.bitrate_combo.findData(settings.bitrate_kbps)
            if br_index >= 0:
                self.bitrate_combo.setCurrentIndex(br_index)

        if settings.sample_rate:
            sr_index = self.sample_rate_combo.findData(settings.sample_rate)
            if sr_index >= 0:
                self.sample_rate_combo.setCurrentIndex(sr_index)
        else:
            self.sample_rate_combo.setCurrentIndex(0)

        is_custom = profile.id == "custom"
        for widget in (
            self.channels_combo,
            self.rate_mode_combo,
            self.qscale_spin,
            self.bitrate_combo,
            self.sample_rate_combo,
        ):
            widget.setEnabled(is_custom)

        self._on_rate_mode_changed()

    def _on_rate_mode_changed(self) -> None:
        is_vbr = self.rate_mode_combo.currentData() == RateMode.VBR.value
        is_custom = self.profile_combo.currentData() == "custom"
        self.qscale_spin.setEnabled(is_custom and is_vbr)
        self.bitrate_combo.setEnabled(is_custom and not is_vbr)

    def _current_settings(self) -> CompressionSettings:
        return CompressionSettings(
            channels=self.channels_combo.currentData(),
            rate_mode=RateMode(self.rate_mode_combo.currentData()),
            qscale=self.qscale_spin.value(),
            bitrate_kbps=self.bitrate_combo.currentData(),
            sample_rate=self.sample_rate_combo.currentData(),
        )

    def _scan_files(self) -> None:
        source = self.source_edit.text().strip()
        output = self.output_edit.text().strip()
        if not source or not output:
            QMessageBox.warning(self, "提示", "请先选择源文件夹和目标文件夹。")
            return

        output = self._resolve_output_dir(source, output)

        ok, message = validate_paths(source, output)
        if not ok:
            QMessageBox.warning(self, "路径无效", message)
            return

        files = scan_mp3_files(source)
        if not files:
            QMessageBox.information(self, "提示", "源文件夹中没有找到 MP3 文件。")
            return

        output_dir = Path(output)
        tasks = [
            FileTask(source_path=f, output_path=output_dir / f.name) for f in files
        ]
        self._controller.set_tasks(tasks)
        self._populate_task_table()
        self._update_summary()
        self._append_log(f"已扫描 {len(tasks)} 个 MP3 文件。")

    def _resolve_output_dir(self, source: str, output: str) -> str:
        source_path = Path(source).resolve()
        output_path = Path(output).resolve()
        if source_path == output_path:
            adjusted = source_path / "outFile"
            self.output_edit.setText(str(adjusted))
            self._append_log("检测到源目录和目标目录一致，已自动改为源目录下 outFile。")
            return str(adjusted)
        return output

    def _populate_task_table(self) -> None:
        self.task_table.setRowCount(len(self._controller.tasks))
        for row, task in enumerate(self._controller.tasks):
            self._set_row(row, task)

    def _set_row(self, row: int, task: FileTask) -> None:
        self.task_table.setItem(row, self.COL_NAME, QTableWidgetItem(task.source_path.name))
        self.task_table.setItem(
            row, self.COL_ORIGINAL, QTableWidgetItem(format_size(task.original_size))
        )
        compressed_text = (
            format_size(task.compressed_size) if task.compressed_size >= 0 else "-"
        )
        self.task_table.setItem(row, self.COL_COMPRESSED, QTableWidgetItem(compressed_text))

        savings_text = (
            format_savings(task.original_size, task.compressed_size)
            if task.compressed_size >= 0
            else "-"
        )
        self.task_table.setItem(row, self.COL_SAVINGS, QTableWidgetItem(savings_text))

        bar = self.task_table.cellWidget(row, self.COL_PROGRESS)
        if not isinstance(bar, QProgressBar):
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setFormat("%p%")
            self.task_table.setCellWidget(row, self.COL_PROGRESS, bar)
        bar.setValue(task.progress)

        self.task_table.setItem(row, self.COL_STATUS, QTableWidgetItem(task.status.value))
        self.task_table.setItem(row, self.COL_MESSAGE, QTableWidgetItem(task.message))

    def _set_controls_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.scan_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(running)
        self.retry_btn.setEnabled(not running)
        self.profile_combo.setEnabled(not running)

    def _start_compression(self) -> None:
        if not self._controller.tasks:
            self._scan_files()
            if not self._controller.tasks:
                return

        source = self.source_edit.text().strip()
        output = self.output_edit.text().strip()
        output = self._resolve_output_dir(source, output)
        ok, message = validate_paths(source, output)
        if not ok:
            QMessageBox.warning(self, "路径无效", message)
            return

        source_path = Path(source).resolve()
        output_path = Path(output).resolve()
        expected_output_parent = output_path
        tasks_need_rescan = (
            not self._controller.tasks
            or any(task.source_path.parent.resolve() != source_path for task in self._controller.tasks)
            or any(task.output_path.parent.resolve() != expected_output_parent for task in self._controller.tasks)
        )
        if tasks_need_rescan:
            self._scan_files()
            if not self._controller.tasks:
                return

        _, ffmpeg_error = resolve_ffmpeg_executable()
        if ffmpeg_error:
            QMessageBox.warning(self, "FFmpeg 未就绪", ffmpeg_error)
            return

        self._set_controls_running(True)
        settings = self._current_settings()
        self._append_log(f"开始压缩，共 {len(self._controller.tasks)} 个文件。")
        self._controller.start(settings)

    def _pause_compression(self) -> None:
        self._controller.pause()
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self._append_log("已暂停。")

    def _resume_compression(self) -> None:
        self._controller.resume()
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self._append_log("已继续。")

    def _stop_compression(self) -> None:
        self._controller.stop()
        self._append_log("正在停止...")

    def _retry_failed(self) -> None:
        failed = [t for t in self._controller.tasks if t.status == TaskStatus.FAILED]
        if not failed:
            QMessageBox.information(self, "提示", "没有失败的任务需要重试。")
            return
        self._set_controls_running(True)
        self._controller.start(self._current_settings(), retry_failed_only=True)

    def _on_task_updated(self, index: int) -> None:
        if 0 <= index < len(self._controller.tasks):
            self._set_row(index, self._controller.tasks[index])

    def _on_batch_progress(self, completed: int, total: int) -> None:
        self.overall_label.setText(f"总体进度：{completed} / {total}")
        percent = int(completed / total * 100) if total else 0
        self.overall_bar.setValue(percent)
        self._update_summary()

    def _on_batch_finished(self) -> None:
        self._set_controls_running(False)
        self._update_summary()
        self._append_log("批处理结束。")

    def _update_summary(self) -> None:
        tasks = self._controller.tasks
        if not tasks:
            self.summary_label.setText("尚未开始压缩")
            return

        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        total_original = sum(t.original_size for t in completed)
        total_compressed = sum(t.compressed_size for t in completed if t.compressed_size >= 0)

        if completed:
            pct = savings_percent(total_original, total_compressed)
            self.summary_label.setText(
                f"已完成 {len(completed)}/{len(tasks)} | "
                f"原始总计 {format_size(total_original)} | "
                f"压缩后总计 {format_size(total_compressed)} | "
                f"总体节省 {pct:.1f}%"
            )
        else:
            pending_original = sum(t.original_size for t in tasks)
            self.summary_label.setText(
                f"共 {len(tasks)} 个文件，原始总计 {format_size(pending_original)}"
            )
