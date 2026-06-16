#!/usr/bin/env python3
"""MP3 Compressor desktop application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MP3 Compressor")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
