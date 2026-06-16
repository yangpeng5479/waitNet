"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
from app.core.i18n import app_display_name, detect_app_language
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
    I18N = {
        "zh": {
            "title": "音频压缩",
            "group_paths": "文件来源",
            "group_settings": "压缩配置",
            "group_controls": "批处理控制",
            "group_tasks": "文件任务列表",
            "group_summary": "汇总统计",
            "group_log": "日志",
            "btn_source_folder": "选择源文件夹",
            "btn_source_file": "选择单个 MP3 文件",
            "btn_target_folder": "选择目标文件夹",
            "btn_scan": "扫描 MP3",
            "btn_start": "开始压缩",
            "btn_pause": "暂停",
            "btn_resume": "继续",
            "btn_stop": "停止",
            "btn_retry": "重试失败项",
            "btn_clear": "清空任务",
            "label_source": "源文件夹",
            "label_target": "目标文件夹",
            "label_profile": "预设",
            "label_channels": "声道",
            "label_mode": "压缩方式",
            "label_qscale": "VBR 质量",
            "label_bitrate": "比特率",
            "label_sample_rate": "采样率",
            "overall_progress": "总体进度：{completed} / {total}",
            "overall_init": "总体进度：0 / 0",
            "summary_init": "尚未开始压缩",
            "table_headers": ["文件名", "原始大小", "压缩后", "节省", "进度", "状态", "备注"],
            "dialog_source_folder": "选择源文件夹",
            "dialog_target_folder": "选择目标文件夹",
            "dialog_source_file": "选择单个 MP3 文件",
            "filter_mp3": "MP3 文件 (*.mp3)",
            "dialog_accept": "打开",
            "dialog_cancel": "取消",
            "warn_title": "提示",
            "warn_path_invalid": "路径无效",
            "warn_ffmpeg": "FFmpeg 未就绪",
            "warn_need_paths": "请先选择源文件夹和目标文件夹。",
            "info_no_mp3": "源文件夹中没有找到 MP3 文件。",
            "info_no_failed": "没有失败的任务需要重试。",
            "log_selected_file": "已选择单文件：{name}",
            "log_scanned": "已扫描 {count} 个 MP3 文件。",
            "log_same_dir": "检测到源目录和目标目录一致，已自动改为源目录下 outFile。",
            "log_start": "开始压缩，共 {count} 个文件。",
            "log_paused": "已暂停。",
            "log_resumed": "已继续。",
            "log_stopping": "正在停止...",
            "log_cleared": "任务已清空（未删除任何文件夹或文件）。",
            "log_finished": "批处理结束。",
            "msg_compressing": "正在压缩...",
            "msg_completed": "压缩完成",
            "msg_stopped": "用户已停止",
            "summary_done": "已完成 {done}/{total} | 原始总计 {original} | 压缩后总计 {compressed} | 总体节省 {pct:.1f}%",
            "summary_pending": "共 {count} 个文件，原始总计 {original}",
            "status_pending": "等待中",
            "status_running": "压缩中",
            "status_completed": "完成",
            "status_failed": "失败",
            "status_skipped": "已跳过",
            "status_cancelled": "已取消",
            "profile_recommended_name": "推荐配置",
            "profile_recommended_desc": "单声道 + libmp3lame + VBR qscale 8",
            "profile_high_compression_name": "高压缩",
            "profile_high_compression_desc": "单声道 + 64kbps CBR，体积更小",
            "profile_high_quality_name": "高质量",
            "profile_high_quality_desc": "立体声 + VBR qscale 4，音质更好",
            "profile_custom_name": "自定义",
            "profile_custom_desc": "手动调整声道、比特率、VBR 质量等参数",
            "channels_mono": "单声道 (1)",
            "channels_stereo": "立体声 (2)",
            "mode_vbr": "VBR 质量 (qscale)",
            "mode_cbr": "固定比特率 (CBR)",
            "sample_rate_keep": "保持原始",
            "qscale_tip": "数值越小音质越好，文件越大",
            "label_language": "语言",
        },
        "en": {
            "title": "Audio Compressor",
            "group_paths": "Input and Output",
            "group_settings": "Compression Settings",
            "group_controls": "Batch Controls",
            "group_tasks": "Task List",
            "group_summary": "Summary",
            "group_log": "Logs",
            "btn_source_folder": "Select Source Folder",
            "btn_source_file": "Select Single MP3 File",
            "btn_target_folder": "Select Target Folder",
            "btn_scan": "Scan MP3",
            "btn_start": "Start",
            "btn_pause": "Pause",
            "btn_resume": "Resume",
            "btn_stop": "Stop",
            "btn_retry": "Retry Failed",
            "btn_clear": "Clear Tasks",
            "label_source": "Source Folder",
            "label_target": "Target Folder",
            "label_profile": "Profile",
            "label_channels": "Channels",
            "label_mode": "Mode",
            "label_qscale": "VBR Quality",
            "label_bitrate": "Bitrate",
            "label_sample_rate": "Sample Rate",
            "overall_progress": "Progress: {completed} / {total}",
            "overall_init": "Progress: 0 / 0",
            "summary_init": "No tasks yet",
            "table_headers": ["File", "Original", "Compressed", "Saved", "Progress", "Status", "Message"],
            "dialog_source_folder": "Select Source Folder",
            "dialog_target_folder": "Select Target Folder",
            "dialog_source_file": "Select Single MP3 File",
            "filter_mp3": "MP3 Files (*.mp3)",
            "dialog_accept": "Open",
            "dialog_cancel": "Cancel",
            "warn_title": "Notice",
            "warn_path_invalid": "Invalid Path",
            "warn_ffmpeg": "FFmpeg Not Ready",
            "warn_need_paths": "Please select source and target folders first.",
            "info_no_mp3": "No MP3 files were found in source folder.",
            "info_no_failed": "No failed tasks to retry.",
            "log_selected_file": "Single file selected: {name}",
            "log_scanned": "Scanned {count} MP3 file(s).",
            "log_same_dir": "Source and target are the same, output changed to source/outFile.",
            "log_start": "Compression started: {count} file(s).",
            "log_paused": "Paused.",
            "log_resumed": "Resumed.",
            "log_stopping": "Stopping...",
            "log_cleared": "Tasks cleared (files/folders were not deleted).",
            "log_finished": "Batch completed.",
            "msg_compressing": "Compressing...",
            "msg_completed": "Completed",
            "msg_stopped": "Stopped by user",
            "summary_done": "Done {done}/{total} | Original {original} | Compressed {compressed} | Saved {pct:.1f}%",
            "summary_pending": "{count} file(s), original total {original}",
            "status_pending": "Pending",
            "status_running": "Running",
            "status_completed": "Completed",
            "status_failed": "Failed",
            "status_skipped": "Skipped",
            "status_cancelled": "Cancelled",
            "profile_recommended_name": "Recommended",
            "profile_recommended_desc": "Mono + libmp3lame + VBR qscale 8",
            "profile_high_compression_name": "High Compression",
            "profile_high_compression_desc": "Mono + 64kbps CBR for smaller output",
            "profile_high_quality_name": "High Quality",
            "profile_high_quality_desc": "Stereo + VBR qscale 4 for better quality",
            "profile_custom_name": "Custom",
            "profile_custom_desc": "Adjust channels, bitrate, VBR quality and more",
            "channels_mono": "Mono (1)",
            "channels_stereo": "Stereo (2)",
            "mode_vbr": "VBR Quality (qscale)",
            "mode_cbr": "Constant Bitrate (CBR)",
            "sample_rate_keep": "Keep original",
            "qscale_tip": "Lower value means better quality and larger size",
            "label_language": "Language",
        },
        "ar": {
            "title": "ضاغط الصوت",
            "group_paths": "الإدخال والإخراج",
            "group_settings": "إعدادات الضغط",
            "group_controls": "التحكم الدفعي",
            "group_tasks": "قائمة المهام",
            "group_summary": "الملخص",
            "group_log": "السجل",
            "btn_source_folder": "اختر مجلد المصدر",
            "btn_source_file": "اختر ملف MP3 واحد",
            "btn_target_folder": "اختر مجلد الهدف",
            "btn_scan": "فحص MP3",
            "btn_start": "بدء",
            "btn_pause": "إيقاف مؤقت",
            "btn_resume": "متابعة",
            "btn_stop": "إيقاف",
            "btn_retry": "إعادة محاولة الفاشلة",
            "btn_clear": "مسح المهام",
            "label_source": "مجلد المصدر",
            "label_target": "مجلد الهدف",
            "label_profile": "النمط",
            "label_channels": "القنوات",
            "label_mode": "وضع الضغط",
            "label_qscale": "جودة VBR",
            "label_bitrate": "معدل البت",
            "label_sample_rate": "معدل العينة",
            "overall_progress": "التقدم: {completed} / {total}",
            "overall_init": "التقدم: 0 / 0",
            "summary_init": "لا توجد مهام بعد",
            "table_headers": ["الملف", "الأصلي", "بعد الضغط", "التوفير", "التقدم", "الحالة", "ملاحظات"],
            "dialog_source_folder": "اختر مجلد المصدر",
            "dialog_target_folder": "اختر مجلد الهدف",
            "dialog_source_file": "اختر ملف MP3 واحد",
            "filter_mp3": "ملفات MP3 (*.mp3)",
            "dialog_accept": "فتح",
            "dialog_cancel": "إلغاء",
            "warn_title": "تنبيه",
            "warn_path_invalid": "مسار غير صالح",
            "warn_ffmpeg": "‏FFmpeg غير جاهز",
            "warn_need_paths": "يرجى اختيار مجلد المصدر ومجلد الهدف أولاً.",
            "info_no_mp3": "لم يتم العثور على ملفات MP3 في مجلد المصدر.",
            "info_no_failed": "لا توجد مهام فاشلة لإعادة المحاولة.",
            "log_selected_file": "تم اختيار ملف واحد: {name}",
            "log_scanned": "تم فحص {count} ملف MP3.",
            "log_same_dir": "المصدر والهدف متطابقان، تم تغيير الإخراج إلى source/outFile.",
            "log_start": "بدأ الضغط: {count} ملف.",
            "log_paused": "تم الإيقاف المؤقت.",
            "log_resumed": "تمت المتابعة.",
            "log_stopping": "جارٍ الإيقاف...",
            "log_cleared": "تم مسح المهام (لم يتم حذف الملفات أو المجلدات).",
            "log_finished": "اكتملت الدفعة.",
            "msg_compressing": "جارٍ الضغط...",
            "msg_completed": "اكتمل",
            "msg_stopped": "تم الإيقاف بواسطة المستخدم",
            "summary_done": "اكتمل {done}/{total} | الأصلي {original} | بعد الضغط {compressed} | التوفير {pct:.1f}%",
            "summary_pending": "{count} ملف، الحجم الأصلي الإجمالي {original}",
            "status_pending": "قيد الانتظار",
            "status_running": "جارٍ الضغط",
            "status_completed": "مكتمل",
            "status_failed": "فشل",
            "status_skipped": "تم التخطي",
            "status_cancelled": "أُلغي",
            "profile_recommended_name": "الإعداد الموصى به",
            "profile_recommended_desc": "قناة واحدة + libmp3lame + ‏VBR qscale 8",
            "profile_high_compression_name": "ضغط عالٍ",
            "profile_high_compression_desc": "قناة واحدة + ‏CBR 64kbps لحجم أصغر",
            "profile_high_quality_name": "جودة عالية",
            "profile_high_quality_desc": "ستيريو + ‏VBR qscale 4 لجودة أفضل",
            "profile_custom_name": "مخصص",
            "profile_custom_desc": "تعديل القنوات ومعدل البت وجودة VBR وغيرها",
            "channels_mono": "أحادي (1)",
            "channels_stereo": "ستيريو (2)",
            "mode_vbr": "جودة VBR (qscale)",
            "mode_cbr": "معدل بت ثابت (CBR)",
            "sample_rate_keep": "الحفاظ على الأصلي",
            "qscale_tip": "القيمة الأقل تعني جودة أعلى وحجم أكبر",
            "label_language": "اللغة",
        },
    }

    def __init__(self) -> None:
        super().__init__()
        self._lang = detect_app_language()
        self._is_rtl = self._lang == "ar"
        self.setWindowTitle(app_display_name(self._lang))
        self.resize(1080, 720)
        if self._is_rtl:
            self.setLayoutDirection(Qt.RightToLeft)
        self._selected_source_file: Path | None = None

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

        root.addLayout(self._build_top_bar())
        root.addWidget(self._build_path_group())
        root.addWidget(self._build_settings_group())
        root.addWidget(self._build_control_group())
        root.addWidget(self._build_task_table_group(), stretch=1)
        root.addWidget(self._build_summary_group())
        root.addWidget(self._build_log_group())

    def _build_top_bar(self) -> QHBoxLayout:
        bar = QHBoxLayout()
        bar.addStretch()
        self.language_label = QLabel(self._t("label_language"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("中文", "zh")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("العربية", "ar")
        idx = self.language_combo.findData(self._lang)
        if idx >= 0:
            self.language_combo.setCurrentIndex(idx)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        bar.addWidget(self.language_label)
        bar.addWidget(self.language_combo)
        return bar

    def _build_path_group(self) -> QGroupBox:
        self.paths_group = QGroupBox(self._t("group_paths"))
        layout = QFormLayout(self.paths_group)

        self.source_edit = QLineEdit()
        self.source_btn = QPushButton(self._t("btn_source_folder"))
        self.source_btn.clicked.connect(self._choose_source)
        self.source_file_btn = QPushButton(self._t("btn_source_file"))
        self.source_file_btn.clicked.connect(self._choose_source_file)

        source_row = QHBoxLayout()
        source_row.addWidget(self.source_edit)
        source_row.addWidget(self.source_btn)
        source_row.addWidget(self.source_file_btn)

        self.output_edit = QLineEdit()
        self.output_btn = QPushButton(self._t("btn_target_folder"))
        self.output_btn.clicked.connect(self._choose_output)

        output_row = QHBoxLayout()
        output_row.addWidget(self.output_edit)
        output_row.addWidget(self.output_btn)

        self.source_row_label = QLabel(self._t("label_source"))
        self.target_row_label = QLabel(self._t("label_target"))
        layout.addRow(self.source_row_label, source_row)
        layout.addRow(self.target_row_label, output_row)
        return self.paths_group

    def _build_settings_group(self) -> QGroupBox:
        self.settings_group = QGroupBox(self._t("group_settings"))
        layout = QHBoxLayout(self.settings_group)

        form = QFormLayout()
        self.profile_combo = QComboBox()
        for profile in PROFILES:
            self.profile_combo.addItem(self._profile_name(profile.id), profile.id)
        self.profile_combo.currentIndexChanged.connect(self._on_profile_changed)

        self.profile_desc = QLabel()
        self.profile_desc.setWordWrap(True)
        self.profile_desc.setStyleSheet("color: #666;")

        self.channels_combo = QComboBox()
        self.channels_combo.addItem(self._t("channels_mono"), 1)
        self.channels_combo.addItem(self._t("channels_stereo"), 2)

        self.rate_mode_combo = QComboBox()
        self.rate_mode_combo.addItem(self._t("mode_vbr"), RateMode.VBR.value)
        self.rate_mode_combo.addItem(self._t("mode_cbr"), RateMode.CBR.value)
        self.rate_mode_combo.currentIndexChanged.connect(self._on_rate_mode_changed)

        self.qscale_spin = QSpinBox()
        self.qscale_spin.setRange(0, 9)
        self.qscale_spin.setValue(8)
        self.qscale_spin.setToolTip(self._t("qscale_tip"))

        self.bitrate_combo = QComboBox()
        for rate in (32, 48, 64, 96, 128, 192, 256, 320):
            self.bitrate_combo.addItem(f"{rate} kbps", rate)
        self.bitrate_combo.setCurrentIndex(3)

        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItem(self._t("sample_rate_keep"), None)
        for rate in (22050, 32000, 44100, 48000):
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)

        self.profile_row_label = QLabel(self._t("label_profile"))
        self.channels_row_label = QLabel(self._t("label_channels"))
        self.mode_row_label = QLabel(self._t("label_mode"))
        self.qscale_row_label = QLabel(self._t("label_qscale"))
        self.bitrate_row_label = QLabel(self._t("label_bitrate"))
        self.sample_rate_row_label = QLabel(self._t("label_sample_rate"))
        form.addRow(self.profile_row_label, self.profile_combo)
        form.addRow(self.channels_row_label, self.channels_combo)
        form.addRow(self.mode_row_label, self.rate_mode_combo)
        form.addRow(self.qscale_row_label, self.qscale_spin)
        form.addRow(self.bitrate_row_label, self.bitrate_combo)
        form.addRow(self.sample_rate_row_label, self.sample_rate_combo)

        layout.addLayout(form, stretch=2)
        layout.addWidget(self.profile_desc, stretch=3)
        return self.settings_group

    def _build_control_group(self) -> QGroupBox:
        self.controls_group = QGroupBox(self._t("group_controls"))
        layout = QHBoxLayout(self.controls_group)

        self.scan_btn = QPushButton(self._t("btn_scan"))
        self.scan_btn.clicked.connect(self._scan_files)

        self.start_btn = QPushButton(self._t("btn_start"))
        self.start_btn.clicked.connect(self._start_compression)

        self.pause_btn = QPushButton(self._t("btn_pause"))
        self.pause_btn.clicked.connect(self._pause_compression)
        self.pause_btn.setEnabled(False)

        self.resume_btn = QPushButton(self._t("btn_resume"))
        self.resume_btn.clicked.connect(self._resume_compression)
        self.resume_btn.setEnabled(False)

        self.stop_btn = QPushButton(self._t("btn_stop"))
        self.stop_btn.clicked.connect(self._stop_compression)
        self.stop_btn.setEnabled(False)

        self.retry_btn = QPushButton(self._t("btn_retry"))
        self.retry_btn.clicked.connect(self._retry_failed)
        self.clear_btn = QPushButton(self._t("btn_clear"))
        self.clear_btn.clicked.connect(self._clear_tasks)
        self.clear_btn.setEnabled(False)

        self.overall_label = QLabel(self._t("overall_init"))
        self.overall_bar = QProgressBar()
        self.overall_bar.setRange(0, 100)
        self.overall_bar.setValue(0)

        layout.addWidget(self.scan_btn)
        layout.addWidget(self.start_btn)
        layout.addWidget(self.pause_btn)
        layout.addWidget(self.resume_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.retry_btn)
        layout.addWidget(self.clear_btn)
        layout.addStretch()
        layout.addWidget(self.overall_label)
        layout.addWidget(self.overall_bar, stretch=1)
        return self.controls_group

    def _build_task_table_group(self) -> QGroupBox:
        self.tasks_group = QGroupBox(self._t("group_tasks"))
        layout = QVBoxLayout(self.tasks_group)

        self.task_table = QTableWidget(0, 7)
        self.task_table.setHorizontalHeaderLabels(self._t("table_headers"))
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
        return self.tasks_group

    def _build_summary_group(self) -> QGroupBox:
        self.summary_group = QGroupBox(self._t("group_summary"))
        layout = QHBoxLayout(self.summary_group)
        self.summary_label = QLabel(self._t("summary_init"))
        layout.addWidget(self.summary_label)
        return self.summary_group

    def _build_log_group(self) -> QGroupBox:
        self.log_group = QGroupBox(self._t("group_log"))
        layout = QVBoxLayout(self.log_group)
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(120)
        layout.addWidget(self.log_view)
        return self.log_group

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
            QMessageBox.warning(self, self._t("warn_ffmpeg"), error)

    def _append_log(self, message: str) -> None:
        self.log_view.append(message)

    def _choose_source(self) -> None:
        dialog = self._build_file_dialog(self._t("dialog_source_folder"))
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec():
            selected_paths = dialog.selectedFiles()
            if not selected_paths:
                return
            path = selected_paths[0]
            self._selected_source_file = None
            self.source_edit.setText(path)

    def _choose_source_file(self) -> None:
        dialog = self._build_file_dialog(self._t("dialog_source_file"))
        dialog.setFileMode(QFileDialog.ExistingFile)
        dialog.setNameFilter(self._t("filter_mp3"))
        if dialog.exec():
            selected_paths = dialog.selectedFiles()
            if not selected_paths:
                return
            selected = Path(selected_paths[0])
            self._selected_source_file = selected
            self.source_edit.setText(str(selected.parent))
            self._append_log(self._t("log_selected_file", name=selected.name))

    def _choose_output(self) -> None:
        dialog = self._build_file_dialog(self._t("dialog_target_folder"))
        dialog.setFileMode(QFileDialog.Directory)
        if dialog.exec():
            selected_paths = dialog.selectedFiles()
            if not selected_paths:
                return
            path = selected_paths[0]
            self.output_edit.setText(path)

    def _build_file_dialog(self, title: str) -> QFileDialog:
        dialog = QFileDialog(self, title)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setLabelText(QFileDialog.Accept, self._t("dialog_accept"))
        dialog.setLabelText(QFileDialog.Reject, self._t("dialog_cancel"))
        dialog.setLayoutDirection(Qt.RightToLeft if self._is_rtl else Qt.LeftToRight)
        return dialog

    def _on_profile_changed(self) -> None:
        profile = get_profile_by_id(self.profile_combo.currentData())
        self.profile_desc.setText(self._profile_description(profile.id))
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

    def _on_language_changed(self) -> None:
        selected = self.language_combo.currentData()
        if not selected or selected == self._lang:
            return
        self._lang = selected
        self._is_rtl = self._lang == "ar"
        self._retranslate_ui()

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(app_display_name(self._lang))
        app = QApplication.instance()
        if app:
            app.setApplicationName(app_display_name(self._lang))
            app.setApplicationDisplayName(app_display_name(self._lang))
            app.setLayoutDirection(Qt.RightToLeft if self._is_rtl else Qt.LeftToRight)
        self.setLayoutDirection(Qt.RightToLeft if self._is_rtl else Qt.LeftToRight)

        self.language_label.setText(self._t("label_language"))
        self.paths_group.setTitle(self._t("group_paths"))
        self.settings_group.setTitle(self._t("group_settings"))
        self.controls_group.setTitle(self._t("group_controls"))
        self.tasks_group.setTitle(self._t("group_tasks"))
        self.summary_group.setTitle(self._t("group_summary"))
        self.log_group.setTitle(self._t("group_log"))
        self.source_row_label.setText(self._t("label_source"))
        self.target_row_label.setText(self._t("label_target"))
        self.profile_row_label.setText(self._t("label_profile"))
        self.channels_row_label.setText(self._t("label_channels"))
        self.mode_row_label.setText(self._t("label_mode"))
        self.qscale_row_label.setText(self._t("label_qscale"))
        self.bitrate_row_label.setText(self._t("label_bitrate"))
        self.sample_rate_row_label.setText(self._t("label_sample_rate"))
        self.source_btn.setText(self._t("btn_source_folder"))
        self.source_file_btn.setText(self._t("btn_source_file"))
        self.output_btn.setText(self._t("btn_target_folder"))
        self.scan_btn.setText(self._t("btn_scan"))
        self.start_btn.setText(self._t("btn_start"))
        self.pause_btn.setText(self._t("btn_pause"))
        self.resume_btn.setText(self._t("btn_resume"))
        self.stop_btn.setText(self._t("btn_stop"))
        self.retry_btn.setText(self._t("btn_retry"))
        self.clear_btn.setText(self._t("btn_clear"))
        self.qscale_spin.setToolTip(self._t("qscale_tip"))

        self.task_table.setHorizontalHeaderLabels(self._t("table_headers"))

        self._refresh_profile_options()
        for row, task in enumerate(self._controller.tasks):
            self._set_row(row, task)
        self._update_summary()
        if not self._controller.tasks:
            self.overall_label.setText(self._t("overall_init"))

    def _refresh_profile_options(self) -> None:
        current_id = self.profile_combo.currentData()
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for profile in PROFILES:
            self.profile_combo.addItem(self._profile_name(profile.id), profile.id)
        idx = self.profile_combo.findData(current_id)
        if idx < 0:
            idx = self.profile_combo.findData(get_default_profile().id)
        if idx >= 0:
            self.profile_combo.setCurrentIndex(idx)
        self.profile_combo.blockSignals(False)

        self.channels_combo.blockSignals(True)
        self.channels_combo.clear()
        self.channels_combo.addItem(self._t("channels_mono"), 1)
        self.channels_combo.addItem(self._t("channels_stereo"), 2)
        self.channels_combo.blockSignals(False)

        self.rate_mode_combo.blockSignals(True)
        current_mode = self.rate_mode_combo.currentData()
        self.rate_mode_combo.clear()
        self.rate_mode_combo.addItem(self._t("mode_vbr"), RateMode.VBR.value)
        self.rate_mode_combo.addItem(self._t("mode_cbr"), RateMode.CBR.value)
        mode_index = self.rate_mode_combo.findData(current_mode)
        self.rate_mode_combo.setCurrentIndex(mode_index if mode_index >= 0 else 0)
        self.rate_mode_combo.blockSignals(False)

        self.sample_rate_combo.blockSignals(True)
        current_sample = self.sample_rate_combo.currentData()
        self.sample_rate_combo.clear()
        self.sample_rate_combo.addItem(self._t("sample_rate_keep"), None)
        for rate in (22050, 32000, 44100, 48000):
            self.sample_rate_combo.addItem(f"{rate} Hz", rate)
        sr_index = self.sample_rate_combo.findData(current_sample)
        self.sample_rate_combo.setCurrentIndex(sr_index if sr_index >= 0 else 0)
        self.sample_rate_combo.blockSignals(False)

        self._on_profile_changed()

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
            QMessageBox.warning(self, self._t("warn_title"), self._t("warn_need_paths"))
            return

        output = self._resolve_output_dir(source, output)

        ok, message = validate_paths(source, output)
        if not ok:
            QMessageBox.warning(self, self._t("warn_path_invalid"), message)
            return

        if self._selected_source_file and self._selected_source_file.is_file():
            files = [self._selected_source_file]
        else:
            files = scan_mp3_files(source)
        if not files:
            QMessageBox.information(self, self._t("warn_title"), self._t("info_no_mp3"))
            return

        output_dir = Path(output)
        tasks = [
            FileTask(source_path=f, output_path=output_dir / f.name) for f in files
        ]
        self._controller.set_tasks(tasks)
        self._populate_task_table()
        self._update_summary()
        self._append_log(self._t("log_scanned", count=len(tasks)))
        self.clear_btn.setEnabled(True)

    def _resolve_output_dir(self, source: str, output: str) -> str:
        source_path = Path(source).resolve()
        output_path = Path(output).resolve()
        if source_path == output_path:
            adjusted = source_path / "outFile"
            self.output_edit.setText(str(adjusted))
            self._append_log(self._t("log_same_dir"))
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

        self.task_table.setItem(row, self.COL_STATUS, QTableWidgetItem(self._status_text(task.status)))
        self.task_table.setItem(row, self.COL_MESSAGE, QTableWidgetItem(self._message_text(task.message)))

    def _set_controls_running(self, running: bool) -> None:
        self.start_btn.setEnabled(not running)
        self.scan_btn.setEnabled(not running)
        self.pause_btn.setEnabled(running)
        self.resume_btn.setEnabled(False)
        self.stop_btn.setEnabled(running)
        self.retry_btn.setEnabled(not running)
        self.clear_btn.setEnabled((not running) and bool(self._controller.tasks))
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
            QMessageBox.warning(self, self._t("warn_path_invalid"), message)
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
            QMessageBox.warning(self, self._t("warn_ffmpeg"), ffmpeg_error)
            return

        self._set_controls_running(True)
        settings = self._current_settings()
        self._append_log(self._t("log_start", count=len(self._controller.tasks)))
        self._controller.start(settings)

    def _pause_compression(self) -> None:
        self._controller.pause()
        self.pause_btn.setEnabled(False)
        self.resume_btn.setEnabled(True)
        self._append_log(self._t("log_paused"))

    def _resume_compression(self) -> None:
        self._controller.resume()
        self.pause_btn.setEnabled(True)
        self.resume_btn.setEnabled(False)
        self._append_log(self._t("log_resumed"))

    def _stop_compression(self) -> None:
        self._controller.stop()
        self._append_log(self._t("log_stopping"))

    def _retry_failed(self) -> None:
        failed = [t for t in self._controller.tasks if t.status == TaskStatus.FAILED]
        if not failed:
            QMessageBox.information(self, self._t("warn_title"), self._t("info_no_failed"))
            return
        self._set_controls_running(True)
        self._controller.start(self._current_settings(), retry_failed_only=True)

    def _clear_tasks(self) -> None:
        if self._controller.is_running:
            return
        self._controller.set_tasks([])
        self.task_table.setRowCount(0)
        self.overall_label.setText(self._t("overall_init"))
        self.overall_bar.setValue(0)
        self.summary_label.setText(self._t("summary_init"))
        self.clear_btn.setEnabled(False)
        self._append_log(self._t("log_cleared"))

    def _on_task_updated(self, index: int) -> None:
        if 0 <= index < len(self._controller.tasks):
            self._set_row(index, self._controller.tasks[index])

    def _on_batch_progress(self, completed: int, total: int) -> None:
        self.overall_label.setText(self._t("overall_progress", completed=completed, total=total))
        percent = int(completed / total * 100) if total else 0
        self.overall_bar.setValue(percent)
        self._update_summary()

    def _on_batch_finished(self) -> None:
        all_completed = bool(self._controller.tasks) and all(
            task.status == TaskStatus.COMPLETED for task in self._controller.tasks
        )
        self._set_controls_running(False)
        self._update_summary()
        self._append_log(self._t("log_finished"))
        if all_completed:
            QApplication.beep()

    def _t(self, key: str, **kwargs):
        text = self.I18N.get(self._lang, self.I18N["en"]).get(key, key)
        if isinstance(text, list):
            return text[:]  # defensive copy for mutable UI lists
        return text.format(**kwargs) if kwargs else text

    def _profile_name(self, profile_id: str) -> str:
        return self._t(f"profile_{profile_id}_name")

    def _profile_description(self, profile_id: str) -> str:
        return self._t(f"profile_{profile_id}_desc")

    def _status_text(self, status: TaskStatus) -> str:
        return self._t(f"status_{status.value}")

    def _message_text(self, message: str) -> str:
        mapping = {
            "Compressing...": self._t("msg_compressing"),
            "Completed": self._t("msg_completed"),
            "Stopped by user": self._t("msg_stopped"),
        }
        return mapping.get(message, message)

    def _update_summary(self) -> None:
        tasks = self._controller.tasks
        if not tasks:
            self.summary_label.setText(self._t("summary_init"))
            return

        completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        total_original = sum(t.original_size for t in completed)
        total_compressed = sum(t.compressed_size for t in completed if t.compressed_size >= 0)

        if completed:
            pct = savings_percent(total_original, total_compressed)
            self.summary_label.setText(
                self._t(
                    "summary_done",
                    done=len(completed),
                    total=len(tasks),
                    original=format_size(total_original),
                    compressed=format_size(total_compressed),
                    pct=pct,
                )
            )
        else:
            pending_original = sum(t.original_size for t in tasks)
            self.summary_label.setText(
                self._t(
                    "summary_pending",
                    count=len(tasks),
                    original=format_size(pending_original),
                )
            )
