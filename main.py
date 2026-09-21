"""
main.py — Entrypoint do ASPM
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow
from utils.resources import resource_path


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("ASPM")
    app.setOrganizationName("CiberSeg")
    app_icon = QIcon(resource_path("assets/icon.ico"))
    app.setWindowIcon(app_icon)
    window = MainWindow()
    window.setWindowIcon(app_icon)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
