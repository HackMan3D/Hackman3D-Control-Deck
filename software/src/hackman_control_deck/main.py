import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLockFile, QSettings, Qt, QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from hackman_control_deck.constants import APP_NAME, APP_VERSION, ASSET_DIR, ORGANIZATION_NAME
from hackman_control_deck.macos_local_network import MacLocalNetworkPermission
from hackman_control_deck.main_window import MainWindow
from hackman_control_deck.styles import APP_STYLE


def main() -> int:
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    QCoreApplication.setApplicationVersion(APP_VERSION)

    # Some Windows GPU/driver combinations leave stale QWidget backing-store
    # fragments behind while complex panels are resized or scrolled.  This app
    # does not need hardware OpenGL, so prefer Qt's stable software renderer on
    # Windows.  The attribute must be set before QApplication is constructed.
    if sys.platform == "win32":
        QCoreApplication.setAttribute(Qt.AA_UseSoftwareOpenGL)

    # Starting the app again while it is already running in the tray used to
    # create another full window.  The overlapping windows looked like stale
    # or cropped UI fragments, especially after resizing.  Keep one desktop
    # instance per Windows session and let QLockFile clean up after crashes.
    instance_lock: QLockFile | None = None
    if sys.platform == "win32":
        lock_path = Path(tempfile.gettempdir()) / "hackman3d-control-deck.lock"
        instance_lock = QLockFile(str(lock_path))
        instance_lock.setStaleLockTime(30_000)
        if not instance_lock.tryLock(0):
            return 0

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLE)
    icon_name = "hcd_app_icon_rounded.png" if sys.platform == "darwin" else "hcd_logo.png"
    app.setWindowIcon(QIcon(str(ASSET_DIR / icon_name)))
    local_network_permission = MacLocalNetworkPermission(app)
    window = MainWindow()
    app.applicationStateChanged.connect(window.application_state_changed)
    start_minimized = QSettings().value("macos/startMinimized", False, type=bool)
    if "--background" in sys.argv or (sys.platform == "darwin" and start_minimized):
        window.start_in_background()
    else:
        window.show()
        QTimer.singleShot(350, window.show_usage_reminder)
    QTimer.singleShot(800, local_network_permission.request)
    app.aboutToQuit.connect(local_network_permission.stop)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
