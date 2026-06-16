#!/usr/bin/env python3
"""MP3 Compressor desktop application entry point."""

import sys

from PySide6.QtCore import QLibraryInfo, Qt, QTranslator
from PySide6.QtWidgets import QApplication

from app.core.i18n import app_display_name, detect_app_language
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    lang = detect_app_language()
    app_name = app_display_name(lang)
    app.setApplicationName(app_name)
    app.setApplicationDisplayName(app_name)
    qt_translator = QTranslator(app)
    qm_lang = {"zh": "zh_CN", "ar": "ar", "en": "en_US"}.get(lang, "en_US")
    translations_dir = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if qt_translator.load(f"qt_{qm_lang}", translations_dir):
        app.installTranslator(qt_translator)
    if lang == "ar":
        app.setLayoutDirection(Qt.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LeftToRight)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
