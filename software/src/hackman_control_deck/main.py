import sys

from PySide6.QtCore import QCoreApplication, QSettings, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from hackman_control_deck.constants import APP_NAME, APP_VERSION, ASSET_DIR, ORGANIZATION_NAME
from hackman_control_deck.main_window import MainWindow
from hackman_control_deck.styles import APP_STYLE


def main() -> int:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    icon_name = "hcd_app_icon_rounded.png" if sys.platform == "darwin" else "hcd_logo.png"
    app.setWindowIcon(QIcon(str(ASSET_DIR / icon_name)))
    window = MainWindow()
    app.applicationStateChanged.connect(window.application_state_changed)
    start_minimized = QSettings().value("macos/startMinimized", False, type=bool)
    if "--background" in sys.argv or (sys.platform == "darwin" and start_minimized):
        window.start_in_background()
    else:
        window.show()
        QTimer.singleShot(350, window.show_usage_reminder)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
