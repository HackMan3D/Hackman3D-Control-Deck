from __future__ import annotations

import os
import sys
import time
import base64
import json
import subprocess
from pathlib import Path

from PySide6.QtCore import (
    QByteArray,
    QBuffer,
    QFileInfo,
    QIODevice,
    QObject,
    QRunnable,
    QSettings,
    QSize,
    Qt,
    QThreadPool,
    QTimer,
    QUrl,
    Signal,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QCloseEvent,
    QDesktopServices,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPixmap,
)
from PySide6.QtWidgets import (
    QComboBox,
    QApplication,
    QCheckBox,
    QColorDialog,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileIconProvider,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QSpinBox,
    QSizePolicy,
    QSpacerItem,
    QSystemTrayIcon,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .action_runner import ActionRunner
from .constants import (
    APP_NAME,
    APP_VERSION,
    ASSET_DIR,
    COMPATIBLE_PRODUCT_NAMES,
    CONTACT_URL,
    PAYPAL_URL,
    RELEASE_CHECK_INTERVAL_SECONDS,
    RELEASE_MANIFEST_URL,
    RELEASES_URL,
    SOCIAL_LINKS,
)
from .conflicts import find_action_conflicts
from .device import HcdDeviceManager
from .device_preview import DevicePreview
from .diagnostics_dialog import DiagnosticsDialog
from .firmware_dialog import FirmwareDialog
from .firmware_updater import (
    FirmwareUpdater,
    firmware_target,
    firmware_update_available,
)
from .favicon import download_favicon
from .models import ACTION_TYPES, Action, Profile
from .macos_integration import (
    MacMenuBarIcon,
    MacWindowMinimizeHandler,
    is_start_at_login_enabled,
    set_dock_icon_visible,
    set_start_at_login,
)
from .profile_store import ProfileStore
from .permissions_dialog import MacPermissionsDialog
from .protocol import DeviceEvent, DeviceInfo, EventKind
from .release_feed import ReleaseFeedClient, ReleaseFeedData
from .statistics import StatisticsStore
from .statistics_dialog import StatisticsDialog
from .translations import LANGUAGES, translate


PRO_COLOR_PRESETS = {
    "classic": {
        "screen": "#080808",
        "key": "#171717",
        "border": "#404040",
        "header": "#FFFFFF",
        "led": "#F02020",
    },
    "graphite": {
        "screen": "#161616",
        "key": "#282828",
        "border": "#8A8A8A",
        "header": "#F4F4F4",
        "led": "#FF453A",
    },
    "electric_blue": {
        "screen": "#06101D",
        "key": "#10263D",
        "border": "#3A9DFF",
        "header": "#DCEEFF",
        "led": "#2F9BFF",
    },
    "arctic": {
        "screen": "#DDE7EF",
        "key": "#F7FAFC",
        "border": "#7393AA",
        "header": "#15232E",
        "led": "#00A7E1",
    },
    "ruby": {
        "screen": "#160507",
        "key": "#2A0B10",
        "border": "#E4314B",
        "header": "#FFE3E7",
        "led": "#FF173D",
    },
    "emerald": {
        "screen": "#04130E",
        "key": "#0B261B",
        "border": "#22C77A",
        "header": "#D9FFEC",
        "led": "#20E887",
    },
    "violet": {
        "screen": "#10071B",
        "key": "#241039",
        "border": "#A45CFF",
        "header": "#F0E3FF",
        "led": "#C13CFF",
    },
    "amber": {
        "screen": "#171006",
        "key": "#2D1F0B",
        "border": "#F0A52B",
        "header": "#FFF0D1",
        "led": "#FF8A00",
    },
    "cyberpunk": {
        "screen": "#050615",
        "key": "#10122B",
        "border": "#00E5FF",
        "header": "#FF4FD8",
        "led": "#FFE600",
    },
    "snow": {
        "screen": "#E9E9E9",
        "key": "#FFFFFF",
        "border": "#565656",
        "header": "#111111",
        "led": "#FF3B30",
    },
}

ACTION_TRANSLATION_KEYS = {
    "none": "no_action",
    "shortcut": "keyboard_shortcut",
    "system": "system_command",
    "text": "type_text",
    "open_url": "open_website",
    "launch": "launch_application",
}

SYSTEM_ICON_FILES = {
    "volume_up": "system_volume_up.svg",
    "volume_down": "system_volume_down.svg",
    "volume_mute": "system_volume_mute.svg",
    "microphone_mute": "system_microphone_mute.svg",
    "microphone_up": "system_volume_up.svg",
    "microphone_down": "system_volume_down.svg",
    "media_play_pause": "system_play_pause.svg",
    "media_next": "system_next.svg",
    "media_previous": "system_previous.svg",
    "brightness_up": "system_brightness_up.svg",
    "brightness_down": "system_brightness_down.svg",
    "shutdown": "system_shutdown.svg",
    "restart": "system_restart.svg",
    "lock": "system_lock.svg",
    "sleep": "system_sleep.svg",
}

SYSTEM_COMMANDS = (
    ("command_volume_up", "volume_up", {"darwin", "win32"}),
    ("command_volume_down", "volume_down", {"darwin", "win32"}),
    ("command_volume_mute", "volume_mute", {"darwin", "win32"}),
    ("command_microphone_mute", "microphone_mute", {"darwin", "win32"}),
    ("command_microphone_up", "microphone_up", {"darwin", "win32"}),
    ("command_microphone_down", "microphone_down", {"darwin", "win32"}),
    ("command_play_pause", "media_play_pause", {"darwin", "win32"}),
    ("command_next_track", "media_next", {"darwin", "win32"}),
    ("command_previous_track", "media_previous", {"darwin", "win32"}),
    ("command_brightness_up", "brightness_up", {"darwin", "win32"}),
    ("command_brightness_down", "brightness_down", {"darwin", "win32"}),
    ("command_lock", "lock", {"darwin", "win32"}),
    ("command_sleep", "sleep", {"darwin", "win32"}),
    ("command_restart", "restart", {"darwin", "win32"}),
    ("command_shutdown", "shutdown", {"darwin", "win32"}),
)


class _FaviconSignals(QObject):
    finished = Signal(str, str, str, bytes)


class _FaviconTask(QRunnable):
    def __init__(self, profile: str, identifier: str, url: str) -> None:
        super().__init__()
        self.profile = profile
        self.identifier = identifier
        self.url = url
        self.signals = _FaviconSignals()

    def run(self) -> None:
        self.signals.finished.emit(
            self.profile,
            self.identifier,
            self.url,
            download_favicon(self.url),
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        self._store = ProfileStore(model_identifier="HCD-BASE")
        self._profile = Profile()
        self._selection: str | None = None
        self._control_buttons: dict[str, QToolButton] = {}
        self._social_buttons: dict[str, QToolButton] = {}
        self._background_button: QPushButton | None = None
        self._file_icon_provider = QFileIconProvider()
        self._application_icon_sources: dict[str, str] = {}
        self._runner = ActionRunner(self)
        self._device = HcdDeviceManager(self)
        self._firmware_updater = FirmwareUpdater(self)
        self._firmware_dialog: FirmwareDialog | None = None
        self._firmware_update_message: QMessageBox | None = None
        self._firmware_update_prompted_for: tuple[str, str] | None = None
        self._diagnostics_dialog: DiagnosticsDialog | None = None
        self._statistics_dialog: StatisticsDialog | None = None
        self._statistics = StatisticsStore()
        self._background_mode_active = False
        self._ignore_dock_activation_until = 0.0
        self._allow_exit = False
        self._settings = QSettings()
        self._release_feed = ReleaseFeedClient(self)
        self._manual_release_check = False
        self._release_prompted_for = self._settings.value(
            "updates/promptedVersion", "", type=str
        )
        self._roadmap_progress_value = self._settings.value(
            "roadmap/progress", 0.0, type=float
        )
        self._language = self._settings.value("ui/language", "en", type=str)
        if self._language not in LANGUAGES:
            self._language = "en"
        self._start_minimized = self._settings.value("macos/startMinimized", False, type=bool)
        self._statistics_enabled = self._settings.value("statistics/enabled", False, type=bool)
        self._feedback_hold_ms = max(
            0,
            min(2000, self._settings.value("device/feedbackHoldMs", 120, type=int)),
        )
        self._pro_icon_size = max(
            0, min(3, self._settings.value("pro/iconSize", 1, type=int))
        )
        self._pro_icon_shape = self._settings.value(
            "pro/iconShape", "original", type=str
        )
        if self._pro_icon_shape not in {"original", "macos", "windows"}:
            self._pro_icon_shape = "original"
        # HCD Pro uses icons only. Text labels caused unnecessary full-screen
        # redraws on the RGB panel and made the 7x4 layout less readable.
        self._settings.remove("pro/showLabels")
        self._pro_theme = 0
        self._settings.remove("pro/theme")
        self._pro_colors = {
            name: self._normalized_color(
                self._settings.value(f"pro/color/{name}", default, type=str),
                default,
            )
            for name, default in PRO_COLOR_PRESETS["classic"].items()
        }
        self._pro_slider_mode = self._settings.value("pro/sliderMode", "volume", type=str)
        if self._pro_slider_mode not in {"off", "volume", "brightness"}:
            self._pro_slider_mode = "volume"
        self._pro_second_fader = self._settings.value(
            "pro/secondFader", False, type=bool
        )
        self._pending_slider_value = 50
        self._pending_microphone_value = 50
        self._slider_action_timer = QTimer(self)
        self._slider_action_timer.setSingleShot(True)
        self._slider_action_timer.setInterval(80)
        self._slider_action_timer.timeout.connect(self._apply_pro_slider_value)
        self._last_slider_input_at = 0.0
        self._last_microphone_input_at = 0.0
        self._microphone_action_timer = QTimer(self)
        self._microphone_action_timer.setSingleShot(True)
        self._microphone_action_timer.setInterval(80)
        self._microphone_action_timer.timeout.connect(self._apply_pro_microphone_value)
        self._pending_encoder_steps = {1: 0, 2: 0}
        self._encoder_action_timer = QTimer(self)
        self._encoder_action_timer.setSingleShot(True)
        self._encoder_action_timer.setInterval(90)
        self._encoder_action_timer.timeout.connect(self._apply_encoder_adjustments)
        self._system_level_timer = QTimer(self)
        self._system_level_timer.setInterval(1_000)
        self._system_level_timer.timeout.connect(self._sync_pro_slider_from_system)
        self._system_level_timer.start()
        self._connected = False
        self._heartbeat_active = False
        self._connected_port = ""
        self._device_product = ""
        self._device_model_identifier = ""
        self._device_info_data: DeviceInfo | None = None
        self._pressed_keys: set[str] = set()
        self._key_pressed_at: dict[str, float] = {}
        self._has_activity = False
        self._loading_action = False
        self._last_pro_layout_fingerprint = ""
        self._action_save_timer = QTimer(self)
        self._action_save_timer.setSingleShot(True)
        self._action_save_timer.setInterval(450)
        self._action_save_timer.timeout.connect(lambda: self._save_action(False))
        self._pro_sync_timer = QTimer(self)
        self._pro_sync_timer.setSingleShot(True)
        self._pro_sync_timer.setInterval(700)
        self._pro_sync_timer.timeout.connect(self._sync_pro_labels)
        self._custom_icon_data = ""
        self._icon_source = ""
        self._favicon_pool = QThreadPool(self)
        self._favicon_pool.setMaxThreadCount(3)
        self._favicon_pending: set[tuple[str, str, str]] = set()
        self._favicon_refresh_timer = QTimer(self)
        self._favicon_refresh_timer.setInterval(6 * 60 * 60 * 1000)
        self._favicon_refresh_timer.timeout.connect(self._refresh_website_icons)
        self._favicon_refresh_timer.start()
        self._application_choices: list[tuple[str, str]] | None = None
        self._application_icon_cache: dict[str, QIcon] = {}
        self._primary_preset_value = ""
        self._long_preset_value = ""
        self._release_feed_timer = QTimer(self)
        self._release_feed_timer.setInterval(RELEASE_CHECK_INTERVAL_SECONDS * 1000)
        self._release_feed_timer.timeout.connect(self._check_release_feed_if_due)

        self._build_ui()
        self._device_preview.set_pro_second_fader(self._pro_second_fader)
        self._device_preview.set_pro_colors(self._pro_colors)
        self._resize_for_screen()
        self._build_tray()
        self._connect_signals()
        self._reload_profile_list()
        self._device.start()
        self._apply_language()
        QTimer.singleShot(1_500, self._check_release_feed_if_due)
        self._release_feed_timer.start()

    def _resize_for_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.setMinimumSize(1120, 720)
            self.resize(1460, 880)
            return
        available = screen.availableGeometry()
        # Use the available desktop width instead of capping the window at
        # 1500 px.  The previous cap needlessly compressed the editor on common
        # 1080p and high-DPI Windows desktops, making its right edge look cut.
        width = max(1080, available.width() - 40)
        height = min(920, max(700, available.height() - 40))
        self.setMinimumSize(min(1120, width), min(720, height))
        self.resize(width, height)
        QTimer.singleShot(0, self._set_initial_body_sizes)

    def _set_initial_body_sizes(self) -> None:
        if not hasattr(self, "_body_splitter"):
            return
        saved = self._settings.value("ui/bodySplitter", QByteArray())
        if isinstance(saved, QByteArray) and not saved.isEmpty():
            return
        available = max(0, self._body_splitter.width())
        sidebar_width = min(240, max(210, round(available * 0.16)))
        editor_width = min(410, max(340, round(available * 0.23)))
        device_width = max(360, available - sidebar_width - editor_width)
        self._body_splitter.setSizes([sidebar_width, device_width, editor_width])

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 10)
        root_layout.setSpacing(10)
        root_layout.addWidget(self._build_top_bar())
        root_layout.addWidget(self._build_support_banner())
        root_layout.addWidget(self._build_roadmap())

        self._body_splitter = QSplitter(Qt.Horizontal)
        self._body_splitter.setObjectName("bodySplitter")
        self._body_splitter.setChildrenCollapsible(False)
        self._body_splitter.setHandleWidth(8)
        self._body_splitter.addWidget(self._build_sidebar())
        self._body_splitter.addWidget(self._build_device_panel())
        self._body_splitter.addWidget(self._build_editor())
        self._body_splitter.setStretchFactor(0, 0)
        self._body_splitter.setStretchFactor(1, 1)
        self._body_splitter.setStretchFactor(2, 0)
        saved_splitter = self._settings.value("ui/bodySplitter", QByteArray())
        if isinstance(saved_splitter, QByteArray) and not saved_splitter.isEmpty():
            self._body_splitter.restoreState(saved_splitter)
        self._body_splitter.splitterMoved.connect(
            lambda position, index: self._settings.setValue(
                "ui/bodySplitter", self._body_splitter.saveState()
            )
        )
        root_layout.addWidget(self._body_splitter, 1)
        self._credit_label = QLabel(
            "Created, designed and developed by HackMan3D", objectName="subtitle"
        )
        self._credit_label.setAlignment(Qt.AlignCenter)
        root_layout.addWidget(self._credit_label)
        self.setCentralWidget(root)
        self.statusBar().showMessage(self._text("starting_discovery"))

    def _build_top_bar(self) -> QWidget:
        frame = QFrame(objectName="topBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(18, 12, 18, 12)
        logo = QLabel()
        logo_pixmap = QPixmap(str(ASSET_DIR / "hcd_logo.png"))
        logo.setPixmap(logo_pixmap.scaled(250, 118, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(250, 118)
        logo.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo)
        layout.addWidget(self._build_social_links())
        layout.addStretch()
        self._firmware_label = QLabel("Firmware —", objectName="subtitle")
        layout.addWidget(self._firmware_label)
        self._firmware_button = QPushButton("Firmware…")
        self._firmware_button.clicked.connect(self._open_firmware_manager)
        layout.addWidget(self._firmware_button)
        self._updates_button = QPushButton("Updates…")
        self._updates_button.clicked.connect(self._check_release_feed_manually)
        layout.addWidget(self._updates_button)
        self._diagnostics_button = QPushButton("Diagnostics…")
        self._diagnostics_button.clicked.connect(self._open_diagnostics)
        layout.addWidget(self._diagnostics_button)
        self._connection_dot = QLabel("●", objectName="connectionDot")
        self._connection_dot.setProperty("connected", False)
        layout.addWidget(self._connection_dot)
        self._connection_label = QLabel("Disconnected")
        layout.addWidget(self._connection_label)
        if sys.platform != "darwin":
            self._background_button = QPushButton("Run in background")
            self._background_button.clicked.connect(self._send_to_background)
            layout.addWidget(self._background_button)
        return frame

    def _build_social_links(self) -> QWidget:
        widget = QWidget(objectName="socialLinks")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(6)
        for key, tooltip, url in SOCIAL_LINKS:
            button = QToolButton(objectName="socialButton")
            button.setIcon(QIcon(str(ASSET_DIR / f"social_{key}.svg")))
            button.setIconSize(QSize(20, 20))
            button.setFixedSize(32, 32)
            button.setToolTip(tooltip)
            button.setToolTipDuration(5000)
            button.setCursor(Qt.PointingHandCursor)
            button.setAccessibleName(tooltip)
            button.clicked.connect(
                lambda checked=False, target=url: self._open_external_link(target)
            )
            self._social_buttons[key] = button
            layout.addWidget(button)
        return widget

    @staticmethod
    def _open_external_link(url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _build_support_banner(self) -> QWidget:
        frame = QFrame(objectName="supportBanner")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 12, 10)
        layout.setSpacing(10)
        self._support_message = QLabel(objectName="supportText")
        self._support_message.setWordWrap(True)
        layout.addWidget(self._support_message, 1)
        self._feedback_button = QPushButton(objectName="supportButton")
        self._feedback_button.clicked.connect(lambda: self._open_external_link(CONTACT_URL))
        layout.addWidget(self._feedback_button)
        self._support_button = QPushButton(objectName="supportAccent")
        self._support_button.clicked.connect(lambda: self._open_external_link(PAYPAL_URL))
        layout.addWidget(self._support_button)
        return frame

    def _build_roadmap(self) -> QWidget:
        frame = QFrame(objectName="roadmapBanner")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(14)

        labels = QVBoxLayout()
        self._roadmap_title = QLabel(objectName="sectionTitle")
        self._roadmap_message = QLabel(objectName="roadmapText")
        self._roadmap_message.setWordWrap(True)
        labels.addWidget(self._roadmap_title)
        labels.addWidget(self._roadmap_message)
        layout.addLayout(labels, 1)

        progress_layout = QVBoxLayout()
        self._roadmap_progress = QProgressBar()
        self._roadmap_progress.setRange(0, 1000)
        self._set_roadmap_progress(self._roadmap_progress_value)
        self._roadmap_progress.setFixedWidth(320)
        progress_layout.addWidget(self._roadmap_progress)
        self._roadmap_milestones = QLabel(objectName="subtitle")
        self._roadmap_milestones.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self._roadmap_milestones)
        layout.addLayout(progress_layout)
        return frame

    def _set_roadmap_progress(self, progress: float) -> None:
        value = max(0.0, min(100.0, float(progress)))
        self._roadmap_progress.setValue(round(value * 10))
        label = f"{value:.1f}".rstrip("0").rstrip(".")
        self._roadmap_progress.setFormat(f"{label}%")

    def _build_tray(self) -> None:
        if sys.platform == "darwin":
            self._tray = None
            self._menu_bar_icon = MacMenuBarIcon(
                ASSET_DIR / "hcd_status.png",
                lambda: QTimer.singleShot(0, self._restore_window),
            )
            self._macos_minimize_handler = MacWindowMinimizeHandler(
                APP_NAME,
                lambda: QTimer.singleShot(0, self._send_to_background),
            )
            self._menu_bar_icon.hide()
            QTimer.singleShot(0, self._install_macos_minimize_handler)
            return

        self._menu_bar_icon = None
        self._macos_minimize_handler = None
        self._tray = QSystemTrayIcon(QIcon(str(ASSET_DIR / "hcd_tray.svg")), self)
        self._tray.setToolTip(APP_NAME)

        menu = QMenu(self)
        self._tray_open_action = QAction("Open HackMan3D Control Deck", self)
        self._tray_open_action.triggered.connect(self._restore_window)
        menu.addAction(self._tray_open_action)
        menu.addSeparator()
        self._tray_quit_action = QAction("Quit", self)
        self._tray_quit_action.triggered.connect(self._quit_application)
        menu.addAction(self._tray_quit_action)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._tray_activated)

        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()
        else:
            if self._background_button is not None:
                self._background_button.setToolTip(
                    "The system tray is unavailable; the window will be minimized instead."
                )

    def _build_sidebar(self) -> QWidget:
        frame = QFrame(objectName="sidebar")
        frame.setMinimumWidth(205)
        outer_layout = QVBoxLayout(frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFrameShape(QFrame.NoFrame)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 16, 14, 14)
        self._profiles_title = QLabel("Profiles", objectName="sectionTitle")
        layout.addWidget(self._profiles_title)
        self._profile_list = QListWidget()
        layout.addWidget(self._profile_list, 1)
        self._new_profile_button = QPushButton("New profile")
        self._new_profile_button.clicked.connect(self._new_profile)
        layout.addWidget(self._new_profile_button)
        profile_actions = QHBoxLayout()
        self._rename_profile_button = QPushButton("Rename")
        self._rename_profile_button.clicked.connect(self._rename_profile)
        profile_actions.addWidget(self._rename_profile_button)
        self._delete_profile_button = QPushButton("Delete")
        self._delete_profile_button.clicked.connect(self._delete_profile)
        profile_actions.addWidget(self._delete_profile_button)
        layout.addLayout(profile_actions)
        self._profile_tools_button = QPushButton("Profile tools…")
        profile_menu = QMenu(self._profile_tools_button)
        self._duplicate_profile_action = profile_menu.addAction("Duplicate")
        self._duplicate_profile_action.triggered.connect(self._duplicate_profile)
        profile_menu.addSeparator()
        self._import_profile_action = profile_menu.addAction("Import profile…")
        self._import_profile_action.triggered.connect(self._import_profile)
        self._export_profile_action = profile_menu.addAction("Export profile…")
        self._export_profile_action.triggered.connect(self._export_profile)
        profile_menu.addSeparator()
        self._backup_profiles_action = profile_menu.addAction("Back up all profiles…")
        self._backup_profiles_action.triggered.connect(self._backup_profiles)
        self._restore_profiles_action = profile_menu.addAction("Restore backup…")
        self._restore_profiles_action.triggered.connect(self._restore_profiles)
        self._profile_tools_button.setMenu(profile_menu)
        layout.addWidget(self._profile_tools_button)
        self._deck_settings_button = QPushButton("Deck settings…")
        self._deck_settings_button.clicked.connect(self._open_deck_settings)
        layout.addWidget(self._deck_settings_button)
        self._language_label = QLabel("Language")
        layout.addWidget(self._language_label)
        self._language_combo = QComboBox()
        for code, name in LANGUAGES.items():
            self._language_combo.addItem(name, code)
        self._language_combo.setCurrentIndex(self._language_combo.findData(self._language))
        self._language_combo.currentIndexChanged.connect(self._change_language)
        layout.addWidget(self._language_combo)
        if sys.platform == "darwin":
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            layout.addWidget(separator)
            self._macos_title = QLabel("macOS", objectName="sectionTitle")
            layout.addWidget(self._macos_title)
            self._start_at_login_checkbox = QCheckBox("Start with Mac")
            start_at_login = is_start_at_login_enabled()
            self._start_at_login_checkbox.setChecked(start_at_login)
            self._start_at_login_checkbox.toggled.connect(self._set_start_at_login)
            layout.addWidget(self._start_at_login_checkbox)
            if start_at_login:
                try:
                    set_start_at_login(True)
                except OSError:
                    pass
            self._start_minimized_checkbox = QCheckBox("Start minimized in menu bar")
            self._start_minimized_checkbox.setChecked(self._start_minimized)
            self._start_minimized_checkbox.toggled.connect(self._set_start_minimized)
            layout.addWidget(self._start_minimized_checkbox)
            self._permissions_button = QPushButton("macOS permissions…")
            self._permissions_button.clicked.connect(self._open_permissions_assistant)
            layout.addWidget(self._permissions_button)
        self._statistics_checkbox = QCheckBox("Enable local statistics")
        self._statistics_checkbox.setChecked(self._statistics_enabled)
        self._statistics_checkbox.toggled.connect(self._set_statistics_enabled)
        layout.addWidget(self._statistics_checkbox)
        self._statistics_button = QPushButton("View statistics…")
        self._statistics_button.clicked.connect(self._open_statistics)
        layout.addWidget(self._statistics_button)
        self._version_label = QLabel(f"Desktop app {APP_VERSION}", objectName="subtitle")
        layout.addWidget(self._version_label)
        layout.addStretch()
        sidebar_scroll.setWidget(content)
        outer_layout.addWidget(sidebar_scroll)
        return frame

    def _build_device_panel(self) -> QWidget:
        frame = QFrame(objectName="devicePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 16, 12, 16)
        title_row = QHBoxLayout()
        self._device_title = QLabel("Control Deck", objectName="title")
        title_row.addWidget(self._device_title)
        title_row.addStretch()
        self._profile_name = QLabel("Default", objectName="subtitle")
        title_row.addWidget(self._profile_name)
        layout.addLayout(title_row)
        self._device_help = QLabel(
            "Select a control to configure its action.", objectName="subtitle"
        )
        layout.addWidget(self._device_help)
        layout.addSpacing(14)

        self._device_preview = DevicePreview(ASSET_DIR / "hcd_device_render_off.png")
        self._device_preview.setMaximumSize(1100, 660)
        self._device_preview.control_selected.connect(self._select)
        self._device_preview.application_dropped.connect(self._application_dropped)
        self._control_buttons = self._device_preview.buttons
        layout.addWidget(self._device_preview, 1)
        reset_row = QHBoxLayout()
        reset_row.addStretch()
        self._reset_keys_button = QPushButton(objectName="resetKeysButton")
        self._reset_keys_button.setFixedWidth(220)
        self._reset_keys_button.clicked.connect(self._reset_all_keys)
        reset_row.addWidget(self._reset_keys_button)
        reset_row.addStretch()
        layout.addLayout(reset_row)
        self._conflicts_button = QPushButton(objectName="conflictButton")
        self._conflicts_button.clicked.connect(self._show_conflicts)
        self._conflicts_button.setVisible(False)
        layout.addWidget(self._conflicts_button)
        self._activity_label = QLabel("No device activity", objectName="subtitle")
        self._activity_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._activity_label)
        return frame

    def _build_editor(self) -> QWidget:
        frame = QFrame(objectName="editor")
        frame.setMinimumWidth(300)
        outer_layout = QVBoxLayout(frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(14, 16, 14, 16)
        self._action_title = QLabel("Action", objectName="sectionTitle")
        layout.addWidget(self._action_title)
        self._selection_label = QLabel("Select a key", objectName="subtitle")
        layout.addWidget(self._selection_label)
        layout.addSpacing(10)

        self._press_tabs = QTabWidget()
        self._encoder_editor = QFrame(objectName="encoderEditor")
        encoder_layout = QVBoxLayout(self._encoder_editor)
        encoder_layout.setContentsMargins(10, 14, 10, 14)
        self._encoder_mode_label = QLabel("Encoder function")
        encoder_layout.addWidget(self._encoder_mode_label)
        self._encoder_mode_combo = QComboBox()
        self._encoder_mode_combo.addItem("Output volume", "volume")
        self._encoder_mode_combo.addItem("Microphone volume", "microphone")
        self._encoder_mode_combo.addItem("Screen brightness", "brightness")
        self._encoder_mode_combo.currentIndexChanged.connect(
            self._encoder_mode_changed
        )
        encoder_layout.addWidget(self._encoder_mode_combo)
        self._encoder_mode_help = QLabel(
            "Rotation decreases or increases this setting. Clicking toggles mute for sound or microphone.",
            objectName="subtitle",
        )
        self._encoder_mode_help.setWordWrap(True)
        encoder_layout.addWidget(self._encoder_mode_help)
        encoder_layout.addStretch()
        self._encoder_editor.setVisible(False)
        layout.addWidget(self._encoder_editor, 1)
        short_tab = QWidget()
        short_layout = QVBoxLayout(short_tab)
        short_layout.setContentsMargins(10, 14, 10, 14)
        self._display_name_label = QLabel("Display name")
        short_layout.addWidget(self._display_name_label)
        self._label_edit = QLineEdit()
        self._label_edit.setEnabled(False)
        self._label_edit.textChanged.connect(self._schedule_action_save)
        short_layout.addWidget(self._label_edit)
        self._action_type_label = QLabel("Action type")
        short_layout.addWidget(self._action_type_label)
        self._action_type = QComboBox()
        for action_type in ACTION_TYPES:
            self._action_type.addItem(action_type, action_type)
        self._action_type.setEnabled(False)
        self._action_type.currentIndexChanged.connect(self._action_type_changed)
        short_layout.addWidget(self._action_type)
        self._value_caption = QLabel("Value")
        short_layout.addWidget(self._value_caption)
        self._value_edit = QLineEdit()
        self._value_edit.setEnabled(False)
        self._value_edit.textChanged.connect(self._schedule_action_save)
        short_layout.addWidget(self._value_edit)
        self._preset_combo = QComboBox()
        self._preset_combo.setIconSize(QSize(30, 30))
        self._preset_combo.setVisible(False)
        self._preset_combo.currentIndexChanged.connect(self._apply_preset)
        short_layout.addWidget(self._preset_combo)
        self._browse_button = QPushButton("Browse…")
        self._browse_button.setVisible(False)
        self._browse_button.clicked.connect(self._browse_application)
        short_layout.addWidget(self._browse_button)
        self._choose_icon_button = QPushButton("Choose icon…")
        self._choose_icon_button.clicked.connect(self._choose_custom_icon)
        short_layout.addWidget(self._choose_icon_button)
        self._clear_icon_button = QPushButton("Remove icon")
        self._clear_icon_button.clicked.connect(self._clear_custom_icon)
        short_layout.addWidget(self._clear_icon_button)
        self._test_action_button = QPushButton("Test action")
        self._test_action_button.clicked.connect(self._test_action)
        short_layout.addWidget(self._test_action_button)
        short_layout.addStretch()

        long_tab = QWidget()
        long_layout = QVBoxLayout(long_tab)
        long_layout.setContentsMargins(10, 14, 10, 14)
        self._long_display_name_label = QLabel("Display name")
        long_layout.addWidget(self._long_display_name_label)
        self._long_label_edit = QLineEdit()
        self._long_label_edit.setEnabled(False)
        self._long_label_edit.textChanged.connect(self._schedule_action_save)
        long_layout.addWidget(self._long_label_edit)
        self._long_action_type_label = QLabel("Action type")
        long_layout.addWidget(self._long_action_type_label)
        self._long_action_type = QComboBox()
        for action_type in ACTION_TYPES:
            self._long_action_type.addItem(action_type, action_type)
        self._long_action_type.setEnabled(False)
        self._long_action_type.currentIndexChanged.connect(self._long_action_type_changed)
        long_layout.addWidget(self._long_action_type)
        self._long_value_caption = QLabel("Value")
        long_layout.addWidget(self._long_value_caption)
        self._long_value_edit = QLineEdit()
        self._long_value_edit.setEnabled(False)
        self._long_value_edit.textChanged.connect(self._schedule_action_save)
        long_layout.addWidget(self._long_value_edit)
        self._long_preset_combo = QComboBox()
        self._long_preset_combo.setIconSize(QSize(30, 30))
        self._long_preset_combo.setVisible(False)
        self._long_preset_combo.currentIndexChanged.connect(self._apply_long_preset)
        long_layout.addWidget(self._long_preset_combo)
        self._long_browse_button = QPushButton("Browse…")
        self._long_browse_button.setVisible(False)
        self._long_browse_button.clicked.connect(self._browse_long_application)
        long_layout.addWidget(self._long_browse_button)
        self._test_long_action_button = QPushButton("Test long action")
        self._test_long_action_button.clicked.connect(self._test_long_action)
        long_layout.addWidget(self._test_long_action_button)
        self._long_press_delay = QSpinBox()
        self._long_press_delay.setRange(200, 5000)
        self._long_press_delay.setSingleStep(50)
        self._long_press_delay.setSuffix(" ms")
        self._long_press_delay.setValue(650)
        self._long_press_delay.setEnabled(False)
        self._long_press_delay.valueChanged.connect(self._schedule_action_save)
        self._long_press_delay_label = QLabel("Long press duration")
        long_layout.addWidget(self._long_press_delay_label)
        long_layout.addWidget(self._long_press_delay)
        long_layout.addStretch()

        self._press_tabs.addTab(short_tab, "Short press")
        self._press_tabs.addTab(long_tab, "Long press")
        layout.addWidget(self._press_tabs, 1)
        self._save_action_button = QPushButton("Save actions", objectName="accent")
        self._save_action_button.clicked.connect(lambda: self._save_action(True))
        self._save_action_button.setVisible(False)
        layout.addSpacerItem(QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding))
        self._shortcut_hint = QLabel(
            "Shortcuts use + separators, for example CTRL+SHIFT+S. "
            "Actions run on the PC when the matching device event is received.",
            objectName="subtitle",
        )
        self._shortcut_hint.setWordWrap(True)
        layout.addWidget(self._shortcut_hint)
        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return frame

    def _connect_signals(self) -> None:
        self._profile_list.currentTextChanged.connect(self._load_profile)
        self._device.connection_changed.connect(self._connection_changed)
        self._device.status_changed.connect(self.statusBar().showMessage)
        self._device.event_received.connect(self._device_event)
        self._device.info_received.connect(self._device_info)
        self._device.heartbeat_changed.connect(self._heartbeat_changed)
        self._runner.action_failed.connect(self._action_error)
        self._firmware_updater.status_changed.connect(self._firmware_status_changed)
        self._firmware_updater.progress_changed.connect(self._firmware_progress_changed)
        self._firmware_updater.log_changed.connect(self._firmware_log_changed)
        self._firmware_updater.finished.connect(self._firmware_finished)
        self._firmware_updater.esp32_bootloader_required.connect(
            self._show_esp32_bootloader_assistant
        )
        self._firmware_updater.ota_arm_requested.connect(self._device.arm_pro_ota)
        self._release_feed.loaded.connect(self._release_feed_loaded)
        self._release_feed.failed.connect(self._release_feed_failed)

    def _text(self, key: str, **values: object) -> str:
        return translate(self._language, key, **values)

    @staticmethod
    def _normalized_color(value: str, fallback: str = "#000000") -> str:
        color = QColor(str(value))
        return color.name(QColor.NameFormat.HexRgb).upper() if color.isValid() else fallback

    def _change_language(self, index: int = -1) -> None:
        del index
        language = str(self._language_combo.currentData())
        if language not in LANGUAGES:
            return
        self._language = language
        self._settings.setValue("ui/language", language)
        self._apply_language()

    def _apply_language(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setLayoutDirection(Qt.RightToLeft if self._language == "ar" else Qt.LeftToRight)
        self._profiles_title.setText(self._text("profiles"))
        self._new_profile_button.setText(self._text("new_profile"))
        self._rename_profile_button.setText(self._text("rename_profile"))
        self._delete_profile_button.setText(self._text("delete_profile"))
        self._profile_tools_button.setText(self._text("profile_tools"))
        self._duplicate_profile_action.setText(self._text("duplicate_profile"))
        self._import_profile_action.setText(self._text("import_profile"))
        self._export_profile_action.setText(self._text("export_profile"))
        self._backup_profiles_action.setText(self._text("backup_profiles"))
        self._restore_profiles_action.setText(self._text("restore_profiles"))
        self._language_label.setText(self._text("language"))
        if self._background_button is not None:
            self._background_button.setText(self._text("run_background"))
        self._support_message.setText(self._text("support_message"))
        self._feedback_button.setText(self._text("send_feedback"))
        self._support_button.setText(self._text("support_project"))
        self._device_title.setText(self._text("control_deck"))
        self._device_help.setText(self._text("select_control"))
        self._action_title.setText(self._text("action"))
        self._display_name_label.setText(self._text("display_name"))
        self._action_type_label.setText(self._text("action_type"))
        self._long_display_name_label.setText(self._text("display_name"))
        self._long_action_type_label.setText(self._text("action_type"))
        self._browse_button.setText(self._text("browse"))
        self._choose_icon_button.setText(self._text("choose_custom_icon"))
        self._clear_icon_button.setText(self._text("remove_custom_icon"))
        self._long_browse_button.setText(self._text("browse"))
        self._save_action_button.setText(self._text("save_action"))
        self._test_action_button.setText(self._text("test_action"))
        self._test_long_action_button.setText(self._text("test_long_action"))
        self._long_press_delay_label.setText(self._text("long_press_duration"))
        self._encoder_mode_label.setText(self._text("encoder_function"))
        self._encoder_mode_combo.setItemText(0, self._text("output_volume"))
        self._encoder_mode_combo.setItemText(1, self._text("microphone_volume"))
        self._encoder_mode_combo.setItemText(2, self._text("screen_brightness"))
        self._encoder_mode_help.setText(self._text("encoder_help"))
        self._press_tabs.setTabText(0, self._text("short_press"))
        self._press_tabs.setTabText(1, self._text("long_press"))
        self._firmware_button.setText(self._text("firmware_button"))
        self._updates_button.setText(self._text("check_updates"))
        self._diagnostics_button.setText(self._text("diagnostics_button"))
        self._reset_keys_button.setText(
            self._text("reset_visible_controls", count=len(self._control_buttons))
        )
        self._deck_settings_button.setText(self._text("deck_settings"))
        self._statistics_checkbox.setText(self._text("enable_statistics"))
        self._statistics_button.setText(self._text("view_statistics"))
        self._shortcut_hint.setText(self._text("shortcut_hint"))
        self._version_label.setText(self._text("desktop_app", version=APP_VERSION))
        self._credit_label.setText(self._text("credits"))
        self._roadmap_title.setText(self._text("community_roadmap"))
        self._roadmap_message.setText(self._text("roadmap_message"))
        self._roadmap_milestones.setText(self._text("roadmap_milestones"))
        self._roadmap_progress.setToolTip(
            self._text("hcd_plus_details") + "\n\n" + self._text("hcd_pro_details")
        )

        if sys.platform == "darwin":
            self._start_at_login_checkbox.setText(self._text("start_with_mac"))
            self._start_minimized_checkbox.setText(self._text("start_minimized"))
            self._permissions_button.setText(self._text("macos_permissions"))
        elif self._tray is not None:
            self._tray_open_action.setText(f"Open {APP_NAME}")
            self._tray_quit_action.setText("Quit")

        self._action_type.blockSignals(True)
        for index, action_type in enumerate(ACTION_TYPES):
            key = ACTION_TRANSLATION_KEYS[action_type]
            self._action_type.setItemText(index, self._text(key))
            self._long_action_type.setItemText(index, self._text(key))
        self._action_type.blockSignals(False)

        if not self._has_activity:
            self._activity_label.setText(self._text("no_activity"))
        if self._selection:
            if self._selection.startswith("P"):
                label = f"Encoder {self._selection[1:]} · click"
            elif self._selection.startswith("E"):
                direction = "left" if self._selection.endswith("L") else "right"
                label = f"Encoder {self._selection[1:-1]} · {direction}"
            else:
                label = self._text("key", number=self._selection)
            self._selection_label.setText(label)
        else:
            self._selection_label.setText(self._text("select_key"))
        self._connection_changed(self._connected, self._connected_port)
        self._update_value_hint()
        self._update_long_value_hint()
        self._refresh_conflicts()

    def _check_release_feed_if_due(self) -> None:
        if not RELEASE_MANIFEST_URL:
            return
        self._start_release_check(manual=False)

    def _check_release_feed_manually(self) -> None:
        if not RELEASE_MANIFEST_URL:
            self._open_external_link(RELEASES_URL)
            self.statusBar().showMessage(self._text("opening_downloads"), 5_000)
            return
        self._start_release_check(manual=True)

    def _start_release_check(self, *, manual: bool) -> None:
        if self._release_feed.is_busy or not RELEASE_MANIFEST_URL:
            return
        self._manual_release_check = manual
        self._updates_button.setEnabled(False)
        if manual:
            self.statusBar().showMessage(self._text("checking_updates"))
        self._release_feed.check()

    def _release_feed_loaded(self, data: ReleaseFeedData) -> None:
        manual = self._manual_release_check
        self._manual_release_check = False
        self._updates_button.setEnabled(True)

        self._set_roadmap_progress(data.roadmap_progress)
        self._settings.setValue("roadmap/progress", data.roadmap_progress)

        if not data.update_available:
            self.statusBar().showMessage(self._text("app_up_to_date"), 5_000)
            if manual:
                message = QMessageBox(self)
                message.setWindowTitle(self._text("app_updates"))
                message.setIcon(QMessageBox.Information)
                message.setText(self._text("app_up_to_date"))
                message.setInformativeText(
                    self._text("installed_app_version", version=APP_VERSION)
                )
                message.setStandardButtons(QMessageBox.Ok)
                message.button(QMessageBox.Ok).setText(self._text("ok"))
                message.exec()
            return

        self.statusBar().showMessage(
            self._text("app_update_available_short", version=data.latest_version)
        )
        if not manual and self._release_prompted_for == data.latest_version:
            return
        self._release_prompted_for = data.latest_version
        self._settings.setValue("updates/promptedVersion", data.latest_version)

        message = QMessageBox(self)
        message.setWindowTitle(self._text("app_update_available_title"))
        message.setIcon(QMessageBox.Information)
        message.setText(
            self._text(
                "app_update_available",
                installed=APP_VERSION,
                available=data.latest_version,
            )
        )
        if data.release_notes:
            message.setInformativeText(data.release_notes)
        download_button = message.addButton(
            self._text("download_update"), QMessageBox.AcceptRole
        )
        later_button = message.addButton(self._text("later"), QMessageBox.RejectRole)
        download_button.setEnabled(bool(data.download_url))
        message.setDefaultButton(download_button if data.download_url else later_button)
        message.exec()
        if message.clickedButton() is download_button and data.download_url:
            self._open_external_link(data.download_url)

    def _release_feed_failed(self, error: str) -> None:
        manual = self._manual_release_check
        self._manual_release_check = False
        self._updates_button.setEnabled(True)
        if not manual:
            return
        self.statusBar().showMessage(self._text("update_check_failed"), 5_000)
        message = QMessageBox(self)
        message.setWindowTitle(self._text("app_updates"))
        message.setIcon(QMessageBox.Warning)
        message.setText(self._text("update_check_failed"))
        message.setInformativeText(error)
        message.setStandardButtons(QMessageBox.Ok)
        message.button(QMessageBox.Ok).setText(self._text("ok"))
        message.exec()

    def show_usage_reminder(self) -> None:
        if self._settings.value("ui/hideBackgroundReminder", False, type=bool):
            return

        message = QMessageBox(self)
        message.setWindowTitle(APP_NAME)
        message.setIcon(QMessageBox.Information)
        message.setText(self._text("reminder_title"))
        message.setInformativeText(self._text("reminder_text"))
        message.setStandardButtons(QMessageBox.Ok)
        message.button(QMessageBox.Ok).setText(self._text("ok"))
        hide_reminder = QCheckBox(self._text("dont_show_again"))
        message.setCheckBox(hide_reminder)
        message.exec()
        if hide_reminder.isChecked():
            self._settings.setValue("ui/hideBackgroundReminder", True)

    def _reload_profile_list(self, select: str | None = None) -> None:
        names = self._store.list_profiles()
        self._profile_list.blockSignals(True)
        self._profile_list.clear()
        self._profile_list.addItems(names)
        requested = select or (names[0] if names else "Default")
        matches = self._profile_list.findItems(requested, Qt.MatchExactly)
        if matches:
            self._profile_list.setCurrentItem(matches[0])
        self._profile_list.blockSignals(False)
        self._load_profile(requested)

    def _load_profile(self, name: str) -> None:
        if not name:
            return
        self._profile = self._store.load(name)
        self._profile_name.setText(self._profile.name)
        self._refresh_control_labels()
        self._schedule_pro_sync(force=True)
        if self._selection:
            self._show_action(self._selection)
        self._refresh_website_icons()

    def _new_profile(self) -> None:
        dialog = QInputDialog(self)
        dialog.setWindowTitle(self._text("new_profile_title"))
        dialog.setLabelText(self._text("profile_name"))
        dialog.setOkButtonText(self._text("ok"))
        dialog.setCancelButtonText(self._text("cancel"))
        accepted = dialog.exec() == QDialog.Accepted
        name = dialog.textValue()
        if accepted and name.strip():
            try:
                profile = self._store.create(name)
            except FileExistsError:
                self._show_profile_exists(name.strip())
            else:
                self._reload_profile_list(profile.name)

    def _rename_profile(self) -> None:
        current_item = self._profile_list.currentItem()
        if current_item is None:
            return
        current_name = current_item.text()

        dialog = QInputDialog(self)
        dialog.setWindowTitle(self._text("rename_profile_title"))
        dialog.setLabelText(self._text("profile_name"))
        dialog.setTextValue(current_name)
        dialog.setOkButtonText(self._text("ok"))
        dialog.setCancelButtonText(self._text("cancel"))
        dialog.lineEdit().selectAll()
        accepted = dialog.exec() == QDialog.Accepted
        requested_name = dialog.textValue().strip()
        if not accepted or not requested_name or requested_name == current_name:
            return
        try:
            profile = self._store.rename(current_name, requested_name)
        except FileExistsError:
            self._show_profile_exists(requested_name)
        else:
            self._reload_profile_list(profile.name)

    def _delete_profile(self) -> None:
        current_item = self._profile_list.currentItem()
        if current_item is None:
            return
        profile_name = current_item.text()

        message = QMessageBox(self)
        message.setWindowTitle(self._text("delete_profile_title"))
        message.setIcon(QMessageBox.Warning)
        message.setText(self._text("delete_profile_confirm", name=profile_name))
        delete_button = message.addButton(self._text("delete_profile"), QMessageBox.DestructiveRole)
        message.addButton(self._text("cancel"), QMessageBox.RejectRole)
        message.exec()
        if message.clickedButton() is not delete_button:
            return

        self._store.delete(profile_name)
        self._selection = None
        self._reload_profile_list()

    def _duplicate_profile(self) -> None:
        current_item = self._profile_list.currentItem()
        if current_item is None:
            return
        profile = self._store.duplicate(current_item.text())
        self._reload_profile_list(profile.name)
        self.statusBar().showMessage(self._text("profile_duplicated", name=profile.name), 2500)

    def _import_profile(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self._text("import_profile"), str(Path.home()), "HCD Profile (*.hcdprofile)"
        )
        if not path:
            return
        try:
            profile = self._store.import_profile(Path(path))
        except ValueError as error:
            QMessageBox.warning(self, APP_NAME, str(error))
            return
        self._reload_profile_list(profile.name)
        self.statusBar().showMessage(self._text("profile_imported", name=profile.name), 2500)

    def _export_profile(self) -> None:
        current_item = self._profile_list.currentItem()
        if current_item is None:
            return
        name = current_item.text()
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._text("export_profile"),
            str(Path.home() / f"{name}.hcdprofile"),
            "HCD Profile (*.hcdprofile)",
        )
        if path:
            destination = Path(path)
            if destination.suffix != ".hcdprofile":
                destination = destination.with_suffix(".hcdprofile")
            self._store.export_profile(name, destination)
            self.statusBar().showMessage(self._text("profile_exported"), 2500)

    def _backup_profiles(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self,
            self._text("backup_profiles"),
            str(Path.home() / "HackMan3D-Control-Deck.hcdbackup"),
            "HCD Backup (*.hcdbackup)",
        )
        if path:
            destination = Path(path)
            if destination.suffix != ".hcdbackup":
                destination = destination.with_suffix(".hcdbackup")
            self._store.export_backup(destination)
            self.statusBar().showMessage(self._text("backup_created"), 2500)

    def _restore_profiles(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, self._text("restore_profiles"), str(Path.home()), "HCD Backup (*.hcdbackup)"
        )
        if not path:
            return
        try:
            profiles = self._store.import_backup(Path(path))
        except ValueError as error:
            QMessageBox.warning(self, APP_NAME, str(error))
            return
        selected = profiles[0].name if profiles else None
        self._reload_profile_list(selected)
        self.statusBar().showMessage(self._text("backup_restored", count=len(profiles)), 2500)

    def _show_profile_exists(self, name: str) -> None:
        message = QMessageBox(self)
        message.setWindowTitle(APP_NAME)
        message.setIcon(QMessageBox.Information)
        message.setText(self._text("profile_exists", name=name))
        message.addButton(self._text("ok"), QMessageBox.AcceptRole)
        message.exec()

    def _select(self, identifier: str) -> None:
        self._refresh_control_labels()
        self._selection = identifier
        for item, button in self._control_buttons.items():
            button.setProperty("selected", item == identifier)
            button.style().unpolish(button)
            button.style().polish(button)
        self._show_action(identifier)

    def _action_for(self, identifier: str) -> Action:
        self._profile.ensure_controls(
            self._device_info_data.key_count if self._device_info_data else 9,
            self._device_info_data.potentiometer_count if self._device_info_data else 0,
        )
        return self._profile.keys[identifier]

    def _show_action(self, identifier: str) -> None:
        action = self._action_for(identifier)
        self._primary_preset_value = action.value
        self._long_preset_value = action.long_value
        if identifier.startswith("P"):
            selection_label = f"Encoder {identifier[1:]}"
        elif identifier.startswith("E"):
            direction = "left" if identifier.endswith("L") else "right"
            selection_label = f"Encoder {identifier[1:-1]} · {direction}"
        else:
            selection_label = self._text("key", number=identifier)
        self._selection_label.setText(selection_label)
        if identifier.startswith("P"):
            self._press_tabs.setVisible(False)
            self._shortcut_hint.setVisible(False)
            self._encoder_editor.setVisible(True)
            encoder_id = identifier[1:]
            mode = self._profile.encoder_modes.get(
                encoder_id, "volume" if encoder_id == "1" else "microphone"
            )
            self._encoder_mode_combo.blockSignals(True)
            index = self._encoder_mode_combo.findData(mode)
            self._encoder_mode_combo.setCurrentIndex(max(0, index))
            self._encoder_mode_combo.blockSignals(False)
            return
        self._encoder_editor.setVisible(False)
        self._press_tabs.setVisible(True)
        self._shortcut_hint.setVisible(True)
        self._label_edit.setEnabled(True)
        self._action_type.setEnabled(True)
        self._value_edit.setEnabled(True)
        self._long_label_edit.setEnabled(True)
        self._long_action_type.setEnabled(True)
        self._long_value_edit.setEnabled(True)
        self._long_press_delay.setEnabled(True)
        self._loading_action = True
        try:
            self._label_edit.setText(action.label)
            self._action_type.setCurrentIndex(self._action_type.findData(action.type))
            self._value_edit.setText(action.value)
            self._long_label_edit.setText(
                action.long_label if action.long_type != "none" else self._text("no_long_action")
            )
            self._long_action_type.setCurrentIndex(
                self._long_action_type.findData(action.long_type)
            )
            self._long_value_edit.setText(action.long_value)
            self._long_press_delay.setValue(action.long_press_ms)
            self._custom_icon_data = action.icon_data
            self._icon_source = action.icon_source
            self._update_value_hint()
            self._update_long_value_hint()
        finally:
            self._loading_action = False

    def _action_type_changed(self, index: int = -1) -> None:
        del index
        if not self._loading_action:
            self._label_edit.clear()
            self._value_edit.clear()
            self._primary_preset_value = ""
            self._custom_icon_data = ""
            self._icon_source = ""
        self._update_value_hint()
        self._schedule_action_save()

    def _long_action_type_changed(self, index: int = -1) -> None:
        del index
        if not self._loading_action:
            self._long_label_edit.clear()
            self._long_value_edit.clear()
            self._long_preset_value = ""
        self._update_long_value_hint()
        self._schedule_action_save()

    def _schedule_action_save(self, *unused: object) -> None:
        del unused
        if self._loading_action or not self._selection:
            return
        self._action_save_timer.start()

    def _encoder_mode_changed(self, index: int = -1) -> None:
        del index
        if not self._selection or not self._selection.startswith("P"):
            return
        mode = str(self._encoder_mode_combo.currentData())
        if mode not in {"volume", "microphone", "brightness"}:
            return
        self._profile.encoder_modes[self._selection[1:]] = mode
        self._store.save(self._profile)
        self.statusBar().showMessage(
            f"Encoder {self._selection[1:]}: {self._encoder_mode_combo.currentText()}",
            2_000,
        )

    def _reset_all_keys(self) -> None:
        control_count = len(self._control_buttons)
        message = QMessageBox(self)
        message.setWindowTitle(self._text("reset_all_keys_title"))
        message.setIcon(QMessageBox.Warning)
        message.setText(
            self._text(
                "reset_visible_controls_confirm",
                name=self._profile.name,
                count=control_count,
            )
        )
        reset_button = message.addButton(
            self._text("reset_visible_controls", count=control_count),
            QMessageBox.DestructiveRole,
        )
        message.addButton(self._text("cancel"), QMessageBox.RejectRole)
        message.exec()
        if message.clickedButton() is not reset_button:
            return

        self._profile.reset_controls(tuple(self._control_buttons))
        self._store.save(self._profile)
        self._refresh_control_labels()
        self._schedule_pro_sync(force=True)
        if self._selection:
            self._show_action(self._selection)
        self._has_activity = False
        self._activity_label.setText(self._text("no_activity"))
        self.statusBar().showMessage(
            self._text("visible_controls_reset", count=control_count),
            2500,
        )

    def _save_action(self, show_status: bool = True) -> None:
        if not self._selection:
            return
        primary = self._editor_action()
        long_primary = self._long_editor_action()
        icon_data = self._custom_icon_data
        icon_source = self._icon_source
        if primary.type == "open_url" and icon_source != "custom":
            icon_data = self._favicon_data(primary.value)
            icon_source = "auto" if icon_data else ""
        action = Action(
            type=primary.type,
            value=primary.value,
            label=primary.label,
            long_type=long_primary.type,
            long_value=long_primary.value,
            long_label=long_primary.label,
            long_press_ms=self._long_press_delay.value(),
            icon_data=icon_data,
            icon_source=icon_source,
        )
        self._profile.keys[self._selection] = action
        self._store.save(self._profile)
        self._refresh_control_labels()
        if hasattr(self, "_schedule_pro_sync"):
            self._schedule_pro_sync()
        if show_status:
            self.statusBar().showMessage(self._text("saved", name=action.label), 2500)

    def _editor_action(self) -> Action:
        if not self._selection:
            return Action()
        action_type = str(self._action_type.currentData())
        return Action(
            type=action_type,
            value=self._editor_value(
                action_type,
                self._value_edit,
                self._preset_combo,
                self._primary_preset_value,
            ),
            label=self._editor_label(
                self._label_edit,
                self._preset_combo,
                "Unassigned",
            ),
            long_press_ms=self._long_press_delay.value(),
            icon_data=self._custom_icon_data,
            icon_source=self._icon_source,
        )

    def _long_editor_action(self) -> Action:
        action_type = str(self._long_action_type.currentData())
        return Action(
            type=action_type,
            value=self._editor_value(
                action_type,
                self._long_value_edit,
                self._long_preset_combo,
                self._long_preset_value,
            ),
            label=self._editor_label(
                self._long_label_edit,
                self._long_preset_combo,
                self._text("long_press"),
            ),
        )

    @staticmethod
    def _editor_value(
        action_type: str,
        edit: QLineEdit,
        presets: QComboBox,
        remembered: str = "",
    ) -> str:
        if action_type in {"system", "launch"}:
            if remembered:
                return remembered.strip()
            selected = presets.currentData()
            if selected:
                return str(selected).strip()
        return edit.text().strip()

    @staticmethod
    def _editor_label(edit: QLineEdit, presets: QComboBox, fallback: str) -> str:
        label = edit.text().strip()
        if label:
            return label
        if presets.currentIndex() > 0:
            preset_label = presets.currentText().split(" — ", maxsplit=1)[0].strip()
            if preset_label:
                return preset_label
        return fallback

    def _test_action(self) -> None:
        if self._selection:
            self._runner.run(self._editor_action())

    def _test_long_action(self) -> None:
        if not self._selection:
            return
        action = self._long_editor_action()
        if action.type == "none":
            return
        self._runner.run(action)

    def _refresh_control_labels(self) -> None:
        for identifier, button in self._control_buttons.items():
            action = self._action_for(identifier)
            full_label = action.label or f"Key {identifier}"
            button.setText(self._preview_label(full_label))
            button.setIcon(self._action_icon(action))
            button.setToolTip(
                f"{full_label}\n{action.value}" if action.type == "launch" else full_label
            )
        self._refresh_conflicts()

    def _schedule_pro_sync(self, force: bool = False) -> None:
        if force:
            self._last_pro_layout_fingerprint = ""
        self._pro_sync_timer.start()

    def _sync_pro_labels(self) -> None:
        info = self._device_info_data
        if info is None or info.model_identifier != "HCD-PRO":
            return
        if self._device.pro_sync_busy:
            self._pro_sync_timer.start()
            return
        fingerprint = repr(
            (
                self._profile.name,
                self._pro_icon_size,
                self._pro_icon_shape,
                tuple(sorted(self._pro_colors.items())),
                self._pro_second_fader,
                self._pro_slider_mode,
                tuple(
                    (
                        index,
                        action.type,
                        action.value,
                        action.label,
                        action.icon_data,
                        action.icon_source,
                    )
                    for index in range(1, info.key_count + 1)
                    for action in (self._action_for(str(index)),)
                ),
            )
        )
        if fingerprint == self._last_pro_layout_fingerprint:
            return
        labels = {
            str(index): self._action_for(str(index)).label or f"Key {index}"
            for index in range(1, info.key_count + 1)
        }
        icons: dict[str, bytes] = {}
        for index in range(1, info.key_count + 1):
            identifier = str(index)
            action = self._action_for(identifier)
            icon = self._action_icon(action)
            if not icon.isNull():
                icons[identifier] = self._pro_icon_data(icon)
        accepted = self._device.set_pro_layout(
            labels,
            icons,
            self._pro_icon_size,
            False,
            self._pro_theme,
            self._pro_second_fader,
            self._pro_slider_mode,
            self._pro_colors,
        )
        if accepted:
            self._last_pro_layout_fingerprint = fingerprint
        elif self._device.is_connected:
            self._pro_sync_timer.start()

    def _pro_icon_data(self, icon: QIcon) -> bytes:
        image = QImage(64, 64, QImage.Format.Format_RGB32)
        image.fill(QColor(self._pro_colors["key"]))
        source = icon.pixmap(QSize(128, 128)).toImage()
        source.setDevicePixelRatio(1.0)
        source = source.scaled(
            QSize(58, 58),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        painter = QPainter(image)
        painter.drawImage((64 - source.width()) // 2, (64 - source.height()) // 2, source)
        painter.end()

        # Qt performs the RGB565 conversion in native code. The previous
        # per-pixel Python loop was especially expensive on packaged Windows
        # builds and briefly froze the whole editor for a complete Pro layout.
        rgb565 = image.convertToFormat(QImage.Format.Format_RGB16)
        return bytes(rgb565.constBits()[: rgb565.sizeInBytes()])

    def _refresh_conflicts(self) -> None:
        conflicts = find_action_conflicts(self._profile)
        self._conflicts_button.setVisible(bool(conflicts))
        self._conflicts_button.setText(
            self._text("conflicts_found", count=len(conflicts))
            if conflicts
            else self._text("no_conflicts")
        )

    def _show_conflicts(self) -> None:
        conflicts = find_action_conflicts(self._profile)
        if not conflicts:
            return
        lines = []
        for conflict in conflicts:
            locations = ", ".join(
                self._text(
                    "conflict_location",
                    key_id=key_id,
                    press=self._text("short_press" if press == "short" else "long_press"),
                )
                for key_id, press in conflict.assignments
            )
            lines.append(f"• {conflict.value}: {locations}")
        QMessageBox.information(
            self,
            self._text("shortcut_conflicts"),
            self._text("conflict_help") + "\n\n" + "\n".join(lines),
        )

    @staticmethod
    def _preview_label(label: str) -> str:
        return label if len(label) <= 11 else f"{label[:10]}…"

    def _update_value_hint(self) -> None:
        action_type = str(self._action_type.currentData())
        captions = {
            "none": self._text("value"),
            "shortcut": self._text("shortcut"),
            "system": self._text("system_command"),
            "text": self._text("text"),
            "open_url": self._text("website_address"),
            "launch": self._text("application_path"),
        }
        placeholders = {
            "none": self._text("no_value"),
            "shortcut": "CTRL+SHIFT+S",
            "system": self._text("choose_system_command"),
            "text": self._text("text_to_type"),
            "open_url": "https://example.com",
            "launch": r"C:\Program Files\Application\app.exe",
        }
        self._value_caption.setText(captions[action_type])
        self._value_edit.setPlaceholderText(placeholders[action_type])
        self._value_caption.setVisible(action_type != "system")
        self._value_edit.setVisible(action_type != "system")
        self._value_edit.setEnabled(
            self._selection is not None and action_type not in {"none", "system"}
        )
        self._browse_button.setVisible(action_type == "launch")
        self._update_presets(action_type)

    def _update_long_value_hint(self) -> None:
        action_type = str(self._long_action_type.currentData())
        captions = {
            "none": self._text("value"),
            "shortcut": self._text("shortcut"),
            "system": self._text("system_command"),
            "text": self._text("text"),
            "open_url": self._text("website_address"),
            "launch": self._text("application_path"),
        }
        placeholders = {
            "none": self._text("no_value"),
            "shortcut": "CTRL+SHIFT+S",
            "system": self._text("choose_system_command"),
            "text": self._text("text_to_type"),
            "open_url": "https://example.com",
            "launch": r"C:\Program Files\Application\app.exe",
        }
        self._long_value_caption.setText(captions[action_type])
        self._long_value_edit.setPlaceholderText(placeholders[action_type])
        self._long_value_caption.setVisible(action_type != "system")
        self._long_value_edit.setVisible(action_type != "system")
        self._long_value_edit.setEnabled(
            self._selection is not None and action_type not in {"none", "system"}
        )
        self._long_browse_button.setVisible(action_type == "launch")
        self._update_long_presets(action_type)

    def _update_presets(self, action_type: str) -> None:
        selected_value = self._value_edit.text()
        self._preset_combo.blockSignals(True)
        self._preset_combo.clear()

        if action_type == "shortcut":
            self._preset_combo.addItem(self._text("choose_shortcut"), "")
            for label, shortcut in self._shortcut_presets():
                self._preset_combo.addItem(f"{label} — {shortcut}", shortcut)
        elif action_type == "system":
            self._preset_combo.addItem(self._text("choose_system_command"), "")
            for label_key, command in self._system_command_presets():
                self._preset_combo.addItem(
                    self._system_icon(command), self._text(label_key), command
                )
        elif action_type == "launch":
            self._preset_combo.addItem(self._text("choose_installed_app"), "")
            for name, path in self._installed_applications():
                self._preset_combo.addItem(self._application_icon(path), name, path)

        matching_index = self._preset_combo.findData(selected_value)
        self._preset_combo.setCurrentIndex(max(0, matching_index))
        self._primary_preset_value = selected_value if matching_index > 0 else ""
        self._preset_combo.setVisible(action_type in {"shortcut", "system", "launch"})
        self._preset_combo.blockSignals(False)

    def _update_long_presets(self, action_type: str) -> None:
        selected_value = self._long_value_edit.text()
        self._long_preset_combo.blockSignals(True)
        self._long_preset_combo.clear()
        if action_type == "shortcut":
            self._long_preset_combo.addItem(self._text("choose_shortcut"), "")
            for label, shortcut in self._shortcut_presets():
                self._long_preset_combo.addItem(f"{label} — {shortcut}", shortcut)
        elif action_type == "system":
            self._long_preset_combo.addItem(self._text("choose_system_command"), "")
            for label_key, command in self._system_command_presets():
                self._long_preset_combo.addItem(
                    self._system_icon(command), self._text(label_key), command
                )
        elif action_type == "launch":
            self._long_preset_combo.addItem(self._text("choose_installed_app"), "")
            for name, path in self._installed_applications():
                self._long_preset_combo.addItem(
                    self._application_icon(path), name, path
                )
        matching_index = self._long_preset_combo.findData(selected_value)
        self._long_preset_combo.setCurrentIndex(max(0, matching_index))
        self._long_preset_value = selected_value if matching_index > 0 else ""
        self._long_preset_combo.setVisible(action_type in {"shortcut", "system", "launch"})
        self._long_preset_combo.blockSignals(False)

    def _shortcut_presets(self) -> tuple[tuple[str, str], ...]:
        common = (
            (self._text("command_copy"), "CMD+C" if sys.platform == "darwin" else "CTRL+C"),
            (self._text("command_paste"), "CMD+V" if sys.platform == "darwin" else "CTRL+V"),
            (self._text("command_cut"), "CMD+X" if sys.platform == "darwin" else "CTRL+X"),
            (self._text("command_undo"), "CMD+Z" if sys.platform == "darwin" else "CTRL+Z"),
            (self._text("command_redo"), "CMD+SHIFT+Z" if sys.platform == "darwin" else "CTRL+Y"),
            (self._text("command_save"), "CMD+S" if sys.platform == "darwin" else "CTRL+S"),
            (self._text("command_select_all"), "CMD+A" if sys.platform == "darwin" else "CTRL+A"),
            (self._text("command_find"), "CMD+F" if sys.platform == "darwin" else "CTRL+F"),
            (self._text("command_print"), "CMD+P" if sys.platform == "darwin" else "CTRL+P"),
        )
        if sys.platform == "darwin":
            return common + (
                (self._text("command_spotlight"), "CMD+SPACE"),
                (self._text("command_switch_app"), "CMD+TAB"),
                (self._text("command_close_window"), "CMD+W"),
                (self._text("command_screenshot"), "CMD+SHIFT+4"),
            )
        return common + (
            (self._text("command_search"), "WIN+S"),
            (self._text("command_switch_app"), "ALT+TAB"),
            (self._text("command_close_window"), "ALT+F4"),
            (self._text("command_screenshot"), "WIN+SHIFT+S"),
            (self._text("command_lock"), "WIN+L"),
        )

    @staticmethod
    def _system_command_presets() -> tuple[tuple[str, str], ...]:
        return tuple(
            (label, command)
            for label, command, platforms in SYSTEM_COMMANDS
            if sys.platform in platforms
        )

    def _apply_preset(self, index: int) -> None:
        if index <= 0:
            self._primary_preset_value = ""
            if not self._loading_action:
                self._value_edit.clear()
            return
        value = str(self._preset_combo.itemData(index))
        if value:
            self._primary_preset_value = value
            if self._action_type.currentData() == "launch":
                self._set_application_value(value)
            else:
                self._value_edit.setText(value)
                self._label_edit.setText(
                    self._preset_combo.itemText(index).split(" — ", maxsplit=1)[0]
                )

    def _apply_long_preset(self, index: int) -> None:
        if index <= 0:
            self._long_preset_value = ""
            if not self._loading_action:
                self._long_value_edit.clear()
            return
        value = str(self._long_preset_combo.itemData(index))
        if not value:
            return
        self._long_preset_value = value
        if self._long_action_type.currentData() == "launch":
            self._set_long_application_value(value)
        else:
            self._long_value_edit.setText(value)
            self._long_label_edit.setText(
                self._long_preset_combo.itemText(index).split(" — ", maxsplit=1)[0]
            )

    def _set_application_value(self, value: str) -> None:
        self._value_edit.setText(value)
        application_name = Path(value).stem
        self._label_edit.setText(application_name)
        if self._selection:
            button = self._control_buttons[self._selection]
            button.setText(self._preview_label(application_name))
            button.setIcon(self._application_icon(value))
            button.setToolTip(value)

    def _set_long_application_value(self, value: str) -> None:
        self._long_value_edit.setText(value)
        self._long_label_edit.setText(Path(value).stem)

    def _application_dropped(self, identifier: str, path: str) -> None:
        application = Path(path)
        is_application = application.suffix.lower() in {
            ".app",
            ".exe",
            ".bat",
            ".cmd",
            ".lnk",
        }
        if not is_application:
            self.statusBar().showMessage(self._text("drop_application_only"), 3000)
            return
        action = Action(type="launch", value=str(application), label=application.stem)
        self._profile.keys[identifier] = action
        self._store.save(self._profile)
        self._select(identifier)
        self._refresh_control_labels()
        self._schedule_pro_sync(force=True)
        self.statusBar().showMessage(
            self._text("application_assigned", name=application.stem, key=identifier), 2500
        )

    def _application_icon(self, value: str) -> QIcon:
        cached = self._application_icon_cache.get(value)
        if cached is not None:
            return cached
        path = Path(value)
        if not value or not path.exists():
            return QIcon()
        icon_path = path
        if sys.platform == "win32" and path.suffix.casefold() == ".lnk":
            source = self._application_icon_sources.get(str(path))
            if source is None:
                resolved = self._windows_shortcut_icon_sources([path])
                self._application_icon_sources.update(resolved)
                source = resolved.get(str(path))
            if source and Path(source).is_file():
                icon_path = Path(source)
        icon = self._file_icon_provider.icon(QFileInfo(str(icon_path)))
        if icon.isNull() and icon_path != path:
            icon = self._file_icon_provider.icon(QFileInfo(str(path)))
        if sys.platform == "win32":
            icon = self._trimmed_icon(icon)
        self._application_icon_cache[value] = icon
        return icon

    @staticmethod
    def _trimmed_icon(icon: QIcon) -> QIcon:
        if icon.isNull():
            return icon
        canvas_size = 256
        image = icon.pixmap(QSize(canvas_size, canvas_size)).toImage()
        image.setDevicePixelRatio(1.0)
        left = image.width()
        top = image.height()
        right = -1
        bottom = -1
        for y in range(image.height()):
            for x in range(image.width()):
                if image.pixelColor(x, y).alpha() > 8:
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)
        if right < left or bottom < top:
            return icon
        visible = image.copy(left, top, right - left + 1, bottom - top + 1)
        content_size = round(canvas_size * 0.9)
        visible = visible.scaled(
            QSize(content_size, content_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        canvas = QPixmap(canvas_size, canvas_size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawImage(
            (canvas_size - visible.width()) // 2,
            (canvas_size - visible.height()) // 2,
            visible,
        )
        painter.end()
        return QIcon(canvas)

    @staticmethod
    def _system_icon(value: str) -> QIcon:
        filename = SYSTEM_ICON_FILES.get(value)
        return QIcon(str(ASSET_DIR / filename)) if filename else QIcon()

    @staticmethod
    def _padded_icon(icon: QIcon, scale: float = 0.78) -> QIcon:
        if icon.isNull():
            return icon
        canvas_size = 256
        content_size = max(1, round(canvas_size * scale))
        source = icon.pixmap(QSize(canvas_size, canvas_size))
        source.setDevicePixelRatio(1.0)
        source = source.scaled(
            QSize(content_size, content_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        canvas = QPixmap(canvas_size, canvas_size)
        canvas.fill(Qt.GlobalColor.transparent)
        painter = QPainter(canvas)
        painter.drawPixmap(
            (canvas_size - source.width()) // 2,
            (canvas_size - source.height()) // 2,
            source,
        )
        painter.end()
        return QIcon(canvas)

    def _masked_icon(self, icon: QIcon) -> QIcon:
        if icon.isNull() or self._pro_icon_shape == "original":
            return icon
        canvas_size = 256
        canvas = QPixmap(canvas_size, canvas_size)
        canvas.fill(Qt.GlobalColor.transparent)
        # A Retina pixmap can contain 512 physical pixels for a requested
        # logical size of 256. Normalize it before measuring or clipping;
        # otherwise the 256 px scan only sees the upper-left quarter.
        source_image = icon.pixmap(QSize(canvas_size, canvas_size)).toImage()
        source_image.setDevicePixelRatio(1.0)
        source_image = source_image.scaled(
            QSize(canvas_size, canvas_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        normalized = QPixmap(canvas_size, canvas_size)
        normalized.fill(Qt.GlobalColor.transparent)
        normalizer = QPainter(normalized)
        normalizer.drawImage(
            (canvas_size - source_image.width()) // 2,
            (canvas_size - source_image.height()) // 2,
            source_image,
        )
        normalizer.end()
        image = normalized.toImage()
        left = canvas_size
        top = canvas_size
        right = -1
        bottom = -1
        for y in range(canvas_size):
            for x in range(canvas_size):
                if image.pixelColor(x, y).alpha() > 8:
                    left = min(left, x)
                    top = min(top, y)
                    right = max(right, x)
                    bottom = max(bottom, y)
        if right < left or bottom < top:
            return icon
        visible_width = right - left + 1
        visible_height = bottom - top + 1
        path = QPainterPath()
        radius_ratio = 0.22 if self._pro_icon_shape == "macos" else 0.06
        radius = min(visible_width, visible_height) * radius_ratio
        path.addRoundedRect(
            float(left),
            float(top),
            float(visible_width),
            float(visible_height),
            radius,
            radius,
        )
        painter = QPainter(canvas)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipPath(path)
        painter.drawPixmap(0, 0, normalized)
        painter.end()
        return QIcon(canvas)

    def _action_icon(self, action: Action) -> QIcon:
        icon = QIcon()
        if action.icon_data:
            try:
                pixmap = QPixmap()
                if pixmap.loadFromData(base64.b64decode(action.icon_data)):
                    icon = QIcon(pixmap)
                    if action.type == "open_url" and action.icon_source == "auto":
                        icon = self._padded_icon(icon)
            except (ValueError, TypeError):
                pass
        if icon.isNull() and action.type == "launch":
            icon = self._application_icon(action.value)
        if icon.isNull() and action.type == "system":
            icon = self._padded_icon(self._system_icon(action.value))
        return self._masked_icon(icon)

    def _choose_custom_icon(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("choose_custom_icon"),
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.svg)",
        )
        if not path:
            return
        icon = QIcon(path)
        if icon.isNull():
            return
        self._custom_icon_data = self._encode_icon(icon)
        self._icon_source = "custom"
        self._schedule_action_save()

    def _clear_custom_icon(self) -> None:
        self._custom_icon_data = ""
        self._icon_source = ""
        self._schedule_action_save()

    @staticmethod
    def _encode_icon(icon: QIcon) -> str:
        pixmap = icon.pixmap(QSize(256, 256))
        data = QByteArray()
        buffer = QBuffer(data)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "PNG")
        buffer.close()
        return base64.b64encode(bytes(data)).decode("ascii")

    def _favicon_data(self, value: str) -> str:
        payload = download_favicon(value)
        pixmap = QPixmap()
        if payload and pixmap.loadFromData(payload):
            return self._encode_icon(QIcon(pixmap))
        return ""

    def _refresh_website_icons(self) -> None:
        profile_name = self._profile.name
        for identifier, action in self._profile.keys.items():
            if action.type != "open_url" or not action.value or action.icon_source == "custom":
                continue
            pending_key = (profile_name, identifier, action.value)
            if pending_key in self._favicon_pending:
                continue
            self._favicon_pending.add(pending_key)
            task = _FaviconTask(profile_name, identifier, action.value)
            task.signals.finished.connect(self._website_icon_refreshed)
            self._favicon_pool.start(task)

    def _website_icon_refreshed(
        self,
        profile_name: str,
        identifier: str,
        url: str,
        payload: bytes,
    ) -> None:
        self._favicon_pending.discard((profile_name, identifier, url))
        if profile_name != self._profile.name or not payload:
            return
        action = self._profile.keys.get(identifier)
        if (
            action is None
            or action.type != "open_url"
            or action.value != url
            or action.icon_source == "custom"
        ):
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(payload):
            return
        refreshed = self._encode_icon(QIcon(pixmap))
        if refreshed == action.icon_data:
            return
        action.icon_data = refreshed
        action.icon_source = "auto"
        self._store.save(self._profile)
        self._refresh_control_labels()
        self._schedule_pro_sync(force=True)
        if self._selection == identifier:
            self._custom_icon_data = refreshed
            self._icon_source = "auto"

    def _installed_applications(self) -> list[tuple[str, str]]:
        if self._application_choices is not None:
            return self._application_choices

        applications: dict[str, str] = {}
        if sys.platform == "darwin":
            roots = (
                Path("/Applications"),
                Path("/System/Applications"),
                Path.home() / "Applications",
            )
            for root in roots:
                if not root.is_dir():
                    continue
                for directory, subdirectories, _ in os.walk(root):
                    app_directories = [
                        name
                        for name in subdirectories
                        if name.lower().endswith(".app")
                    ]
                    for app_directory in app_directories:
                        path = Path(directory) / app_directory
                        applications.setdefault(path.stem.casefold(), str(path))
                    subdirectories[:] = [
                        name
                        for name in subdirectories
                        if not name.lower().endswith(".app")
                    ]
        elif sys.platform == "win32":
            roots: list[Path] = []
            for variable in ("PROGRAMDATA", "APPDATA"):
                value = os.environ.get(variable)
                if value:
                    roots.append(
                        Path(value)
                        / "Microsoft"
                        / "Windows"
                        / "Start Menu"
                        / "Programs"
                    )
            applications.update(self._windows_start_menu_applications(roots))
            shortcuts = [
                Path(path)
                for path in applications.values()
                if Path(path).suffix.casefold() == ".lnk"
            ]
            self._application_icon_sources.update(
                self._windows_shortcut_icon_sources(shortcuts)
            )
        self._application_choices = sorted(
            ((Path(path).stem, path) for path in applications.values()),
            key=lambda item: item[0].casefold(),
        )
        return self._application_choices

    @staticmethod
    def _windows_start_menu_applications(roots: list[Path]) -> dict[str, str]:
        applications: dict[str, str] = {}
        for root in roots:
            if not root.is_dir():
                continue
            for suffix in ("*.lnk", "*.url", "*.appref-ms"):
                for path in root.rglob(suffix):
                    if path.is_file() and not path.stem.casefold().startswith(
                        ("uninstall", "désinstaller")
                    ):
                        applications.setdefault(path.stem.casefold(), str(path))
        return applications

    @staticmethod
    def _windows_shortcut_icon_sources(shortcuts: list[Path]) -> dict[str, str]:
        if not shortcuts:
            return {}
        script = r"""
$shell = New-Object -ComObject WScript.Shell
$paths = ConvertFrom-Json $env:HCD_SHORTCUT_PATHS
$result = @()
foreach ($path in @($paths)) {
    try {
        $shortcut = $shell.CreateShortcut([string]$path)
        $icon = [Environment]::ExpandEnvironmentVariables([string]$shortcut.IconLocation)
        $icon = $icon -replace ',-?\d+$', ''
        $target = [Environment]::ExpandEnvironmentVariables([string]$shortcut.TargetPath)
        $source = if ($icon -and (Test-Path -LiteralPath $icon -PathType Leaf)) {
            $icon
        } elseif ($target -and (Test-Path -LiteralPath $target -PathType Leaf)) {
            $target
        } else {
            ''
        }
        if ($source) {
            $result += [PSCustomObject]@{ shortcut = [string]$path; source = $source }
        }
    } catch {}
}
$result | ConvertTo-Json -Compress
"""
        environment = os.environ.copy()
        environment["HCD_SHORTCUT_PATHS"] = json.dumps(
            [str(path) for path in shortcuts], ensure_ascii=False
        )
        try:
            result = subprocess.run(  # noqa: S603
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                check=False,
                close_fds=True,
                capture_output=True,
                text=True,
                timeout=12,
                env=environment,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode or not result.stdout.strip():
                return {}
            payload = json.loads(result.stdout)
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
            return {}
        entries = payload if isinstance(payload, list) else [payload]
        return {
            str(entry["shortcut"]): str(entry["source"])
            for entry in entries
            if isinstance(entry, dict) and entry.get("shortcut") and entry.get("source")
        }

    def _browse_application(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("choose_application"),
            str(Path.home()),
        )
        if path:
            self._set_application_value(path)

    def _browse_long_application(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("choose_application"),
            str(Path.home()),
        )
        if path:
            self._set_long_application_value(path)

    def _connection_changed(self, connected: bool, port: str) -> None:
        self._connected = connected
        self._connected_port = port
        self._device_preview.set_connection_active(connected)
        if not connected:
            self._pressed_keys.clear()
            self._device_preview.set_feedback_active(False)
        self._connection_dot.setProperty("connected", connected)
        self._connection_dot.style().unpolish(self._connection_dot)
        self._connection_dot.style().polish(self._connection_dot)
        self._connection_label.setText(
            (self._device_product or self._text("connected_generic"))
            if connected
            else self._text("disconnected")
        )
        if connected:
            self._device.set_feedback_hold_ms(self._feedback_hold_ms)
        if not connected:
            self._device_product = ""
            self._device_model_identifier = ""
            self._device_info_data = None
            self._connection_label.setToolTip("")
            self._firmware_label.setText(self._text("firmware_unknown"))
        self._update_diagnostics()

    def _heartbeat_changed(self, active: bool) -> None:
        self._heartbeat_active = active
        self._update_diagnostics()

    def _send_to_background(self) -> None:
        self.start_in_background(notify=True)

    def start_in_background(self, notify: bool = False) -> None:
        self._background_mode_active = True
        if sys.platform == "darwin":
            self._ignore_dock_activation_until = time.monotonic() + 1.0
        if sys.platform != "darwin" and not QSystemTrayIcon.isSystemTrayAvailable():
            self.showMinimized()
            return
        self.hide()
        if sys.platform == "darwin":
            self._menu_bar_icon.show()
            QTimer.singleShot(100, self._finish_background_transition)
        if notify and self._tray is not None and QSystemTrayIcon.supportsMessages():
            self._tray.showMessage(
                APP_NAME,
                "The controller remains connected in the background.",
                QSystemTrayIcon.Information,
                2500,
            )

    def _finish_background_transition(self) -> None:
        if self._background_mode_active and not self.isVisible():
            set_dock_icon_visible(False)

    def _restore_window(self) -> None:
        self._background_mode_active = False
        if sys.platform == "darwin":
            self._menu_bar_icon.hide()
            set_dock_icon_visible(True)
            QTimer.singleShot(50, self._finish_restore_window)
            return
        self._finish_restore_window()

    def _finish_restore_window(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._install_macos_minimize_handler()
        central_widget = self.centralWidget()
        if central_widget is not None:
            central_widget.update()
        self.update()

    def _set_start_at_login(self, checked: bool) -> None:
        try:
            set_start_at_login(checked)
        except OSError as error:
            self._start_at_login_checkbox.blockSignals(True)
            self._start_at_login_checkbox.setChecked(not checked)
            self._start_at_login_checkbox.blockSignals(False)
            QMessageBox.warning(
                self,
                APP_NAME,
                self._text("login_error", error=error),
            )

    def _set_start_minimized(self, checked: bool) -> None:
        self._start_minimized = checked
        self._settings.setValue("macos/startMinimized", checked)

    def _open_permissions_assistant(self) -> None:
        dialog = MacPermissionsDialog(self._text, self)
        dialog.exec()

    def _set_feedback_hold_ms(self, duration_ms: int) -> None:
        self._feedback_hold_ms = max(0, min(2000, duration_ms))
        self._settings.setValue("device/feedbackHoldMs", self._feedback_hold_ms)
        if self._connected:
            self._device.set_feedback_hold_ms(self._feedback_hold_ms)

    def _open_deck_settings(self) -> None:
        is_pro = self._device_model_identifier == "HCD-PRO"
        dialog = QDialog(self)
        dialog.setWindowTitle(self._text("deck_settings_title"))
        dialog.setMinimumWidth(430)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)

        title = QLabel(self._text("deck_settings_title"), objectName="title")
        layout.addWidget(title)
        help_label = QLabel(self._text("deck_settings_help"), objectName="subtitle")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        form = QFrame(objectName="firmwareCard")
        form_layout = QVBoxLayout(form)
        form_layout.setContentsMargins(16, 16, 16, 16)
        form_layout.setSpacing(8)

        form_layout.addWidget(QLabel(self._text("icon_size")))
        icon_size = QComboBox()
        for key in ("small", "normal", "large", "extra_large"):
            icon_size.addItem(self._text(key))
        icon_size.setCurrentIndex(self._pro_icon_size)
        form_layout.addWidget(icon_size)

        form_layout.addWidget(QLabel(self._text("icon_shape")))
        icon_shape = QComboBox()
        icon_shape.addItem(self._text("icon_shape_original"), "original")
        icon_shape.addItem(self._text("icon_shape_macos"), "macos")
        icon_shape.addItem(self._text("icon_shape_windows"), "windows")
        icon_shape.setCurrentIndex(max(0, icon_shape.findData(self._pro_icon_shape)))
        form_layout.addWidget(icon_shape)

        form_layout.addWidget(QLabel(self._text("color_preset")))
        color_preset = QComboBox()
        color_preset.setIconSize(QSize(80, 22))
        color_preset.setMaxVisibleItems(len(PRO_COLOR_PRESETS) + 1)
        for preset_name, preset_colors in PRO_COLOR_PRESETS.items():
            swatch = QPixmap(80, 22)
            swatch.fill(QColor(preset_colors["screen"]))
            swatch_painter = QPainter(swatch)
            segment_width = swatch.width() // 4
            for segment, color_name in enumerate(("key", "border", "header", "led")):
                swatch_painter.fillRect(
                    segment * segment_width,
                    0,
                    segment_width,
                    swatch.height(),
                    QColor(preset_colors[color_name]),
                )
            swatch_painter.end()
            color_preset.addItem(
                QIcon(swatch),
                self._text(f"color_{preset_name}"),
                preset_name,
            )
        color_preset.addItem(self._text("color_custom"), "custom")
        selected_colors = dict(self._pro_colors)
        selected_preset = next(
            (
                name
                for name, colors in PRO_COLOR_PRESETS.items()
                if colors == selected_colors
            ),
            "custom",
        )
        color_preset.setCurrentIndex(color_preset.findData(selected_preset))
        form_layout.addWidget(color_preset)

        color_buttons: dict[str, QPushButton] = {}

        def refresh_color_buttons() -> None:
            for name, button in color_buttons.items():
                color = selected_colors[name]
                foreground = "#080808" if QColor(color).lightness() > 145 else "#FFFFFF"
                button.setText(color)
                button.setStyleSheet(
                    f"background:{color};color:{foreground};border:1px solid #777777;"
                )

        def choose_color(name: str) -> None:
            chosen = QColorDialog.getColor(
                QColor(selected_colors[name]),
                dialog,
                self._text(f"color_{name}"),
                QColorDialog.ColorDialogOption.ShowAlphaChannel,
            )
            if not chosen.isValid():
                return
            selected_colors[name] = chosen.name(QColor.NameFormat.HexRgb).upper()
            color_preset.setCurrentIndex(color_preset.findData("custom"))
            refresh_color_buttons()

        for name in ("screen", "key", "border", "header", "led"):
            row = QHBoxLayout()
            row.addWidget(QLabel(self._text(f"color_{name}")), 1)
            button = QPushButton()
            button.setMinimumWidth(120)
            button.clicked.connect(lambda checked=False, item=name: choose_color(item))
            color_buttons[name] = button
            row.addWidget(button)
            form_layout.addLayout(row)

        def apply_color_preset(index: int) -> None:
            preset = str(color_preset.itemData(index))
            if preset in PRO_COLOR_PRESETS:
                selected_colors.update(PRO_COLOR_PRESETS[preset])
                refresh_color_buttons()

        color_preset.currentIndexChanged.connect(apply_color_preset)
        refresh_color_buttons()

        form_layout.addWidget(QLabel(self._text("vertical_fader")))
        slider_mode = QComboBox()
        slider_mode.addItem(self._text("master_volume"), "volume")
        slider_mode.addItem(self._text("screen_brightness"), "brightness")
        slider_mode.addItem(self._text("disabled"), "off")
        slider_mode.setCurrentIndex(max(0, slider_mode.findData(self._pro_slider_mode)))
        form_layout.addWidget(slider_mode)

        second_fader = QCheckBox(self._text("second_microphone_fader"))
        second_fader.setChecked(self._pro_second_fader)
        second_fader.setToolTip(self._text("second_microphone_fader_help"))
        form_layout.addWidget(second_fader)

        pro_widgets = form.findChildren(QWidget)
        form_layout.addWidget(QLabel(self._text("minimum_led_duration")))
        feedback_hold = QSpinBox()
        feedback_hold.setRange(0, 2000)
        feedback_hold.setSingleStep(20)
        feedback_hold.setSuffix(" ms")
        feedback_hold.setValue(self._feedback_hold_ms)
        form_layout.addWidget(feedback_hold)
        if not is_pro:
            for widget in pro_widgets:
                widget.setVisible(False)
        layout.addWidget(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setText(self._text("ok"))
        buttons.button(QDialogButtonBox.Cancel).setText(self._text("cancel"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return
        if is_pro:
            self._set_pro_icon_size(icon_size.currentIndex())
            self._set_pro_icon_shape(str(icon_shape.currentData() or "original"))
            self._set_pro_colors(selected_colors)
            self._set_pro_slider_mode_value(str(slider_mode.currentData() or "off"))
            self._set_pro_second_fader(second_fader.isChecked())
        self._set_feedback_hold_ms(feedback_hold.value())

    def _set_pro_icon_size(self, index: int) -> None:
        self._pro_icon_size = max(0, min(3, index))
        self._settings.setValue("pro/iconSize", self._pro_icon_size)
        self._schedule_pro_sync(force=True)

    def _set_pro_icon_shape(self, shape: str) -> None:
        self._pro_icon_shape = (
            shape if shape in {"original", "macos", "windows"} else "original"
        )
        self._settings.setValue("pro/iconShape", self._pro_icon_shape)
        self._refresh_control_labels()
        self._schedule_pro_sync(force=True)

    def _set_pro_colors(self, colors: dict[str, str]) -> None:
        defaults = PRO_COLOR_PRESETS["classic"]
        self._pro_colors = {
            name: self._normalized_color(colors.get(name, default), default)
            for name, default in defaults.items()
        }
        for name, color in self._pro_colors.items():
            self._settings.setValue(f"pro/color/{name}", color)
        self._device_preview.set_pro_colors(self._pro_colors)
        self._schedule_pro_sync(force=True)

    def _set_pro_slider_mode_value(self, mode: str) -> None:
        self._pro_slider_mode = mode if mode in {"off", "volume", "brightness"} else "off"
        self._settings.setValue("pro/sliderMode", self._pro_slider_mode)
        self._schedule_pro_sync(force=True)
        QTimer.singleShot(0, self._sync_pro_slider_from_system)

    def _set_pro_second_fader(self, enabled: bool) -> None:
        self._pro_second_fader = bool(enabled)
        self._settings.setValue("pro/secondFader", self._pro_second_fader)
        self._device_preview.set_pro_second_fader(self._pro_second_fader)
        self._schedule_pro_sync(force=True)
        QTimer.singleShot(0, self._sync_pro_slider_from_system)

    def _apply_pro_slider_value(self) -> None:
        if self._pro_slider_mode != "off":
            self._runner.set_continuous_value(
                self._pro_slider_mode,
                self._pending_slider_value,
            )

    def _apply_pro_microphone_value(self) -> None:
        if self._pro_second_fader:
            self._runner.set_continuous_value("microphone", self._pending_microphone_value)

    def _apply_encoder_adjustments(self) -> None:
        pending = dict(self._pending_encoder_steps)
        self._pending_encoder_steps = {1: 0, 2: 0}
        for encoder_id, delta in pending.items():
            if delta == 0:
                continue
            mode = self._profile.encoder_modes.get(
                str(encoder_id),
                "volume" if encoder_id == 1 else "microphone",
            )
            self._runner.adjust_continuous_value(mode, delta)

    def _sync_pro_slider_from_system(self) -> None:
        info = self._device_info_data
        if info is None or info.model_identifier != "HCD-PRO":
            return
        now = time.monotonic()
        if self._pro_slider_mode != "off" and now - self._last_slider_input_at >= 0.7:
            value = self._runner.continuous_value(self._pro_slider_mode)
            if value is not None:
                self._pending_slider_value = value
                self._device_preview.set_pro_slider_value(value)
                self._device.set_pro_slider_value(value, 1)
        if self._pro_second_fader and now - self._last_microphone_input_at >= 0.7:
            microphone_value = self._runner.continuous_value("microphone")
            if microphone_value is not None:
                self._pending_microphone_value = microphone_value
                self._device_preview.set_pro_microphone_value(microphone_value)
                self._device.set_pro_slider_value(microphone_value, 2)

    def _set_statistics_enabled(self, enabled: bool) -> None:
        self._statistics_enabled = enabled
        self._settings.setValue("statistics/enabled", enabled)

    def _open_statistics(self) -> None:
        if self._statistics_dialog is not None:
            self._statistics_dialog.raise_()
            self._statistics_dialog.activateWindow()
            return
        dialog = StatisticsDialog(
            self._statistics,
            self._profile.name,
            self._text,
            self,
        )
        dialog.finished.connect(lambda result: self._statistics_closed(result))
        self._statistics_dialog = dialog
        dialog.open()

    def _statistics_closed(self, result: int) -> None:
        del result
        self._statistics_dialog = None

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self._restore_window()

    def application_state_changed(self, state: Qt.ApplicationState) -> None:
        if (
            sys.platform == "darwin"
            and state == Qt.ApplicationActive
            and self._background_mode_active
            and not self.isVisible()
            and time.monotonic() >= self._ignore_dock_activation_until
        ):
            QTimer.singleShot(0, self._restore_window)

    def _quit_application(self) -> None:
        if self._firmware_updater.is_busy:
            QMessageBox.warning(self, APP_NAME, self._text("firmware_busy_close"))
            return
        self._allow_exit = True
        self._device.stop()
        if self._tray is not None:
            self._tray.hide()
        if self._menu_bar_icon is not None:
            self._menu_bar_icon.dispose()
        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _install_macos_minimize_handler(self) -> None:
        if self._macos_minimize_handler is not None:
            self._macos_minimize_handler.install()

    def _device_info(self, info: DeviceInfo) -> None:
        profile_model = (
            info.model_identifier
            if info.model_identifier in ProfileStore.MODELS
            else "HCD-BASE"
        )
        previous_model = self._store.model_identifier
        if previous_model != profile_model:
            self._store.save(self._profile)
            self._store.set_model(profile_model)
            self._reload_profile_list()
        self._device_info_data = info
        self._device_product = info.product
        self._device_model_identifier = info.model_identifier
        self._profile.ensure_controls(info.key_count, info.potentiometer_count)
        self._store.save(self._profile)
        self._device_preview.set_model(
            info.model_identifier,
            info.key_count,
            info.potentiometer_count,
        )
        self._device_title.setText(info.product)
        self._selection = None
        self._refresh_control_labels()
        # Update an outdated Pro before sending its display snapshot. Besides
        # reducing unnecessary traffic, this leaves a safe recovery path for
        # a firmware build whose display synchronization is defective.
        if firmware_update_available(info.firmware_version, info.model_identifier):
            self._pro_sync_timer.stop()
            self._last_pro_layout_fingerprint = ""
        else:
            self._schedule_pro_sync(force=True)
        self._reset_keys_button.setText(
            self._text("reset_visible_controls", count=len(self._control_buttons))
        )
        self._connection_label.setText(info.product)
        self._connection_label.setToolTip(f"{info.model_identifier} · {self._connected_port}")
        self._firmware_label.setText(f"Firmware {info.firmware_version}")
        self.statusBar().showMessage(
            f"{info.product} · {info.model_identifier} · {self._connected_port}"
        )
        self._update_diagnostics()
        if self._diagnostics_dialog is not None:
            self._diagnostics_dialog.set_controls(
                info.key_count,
                info.potentiometer_count,
            )
        QTimer.singleShot(250, self._offer_firmware_update)
        QTimer.singleShot(350, self._sync_pro_slider_from_system)

    def _offer_firmware_update(self) -> None:
        info = self._device_info_data
        if (
            info is None
            or not self._connected_port
            or self._firmware_updater.is_busy
            or self._firmware_dialog is not None
            or self._firmware_update_message is not None
        ):
            return
        target = firmware_target(info.model_identifier)
        if target is None or not info.product.startswith(COMPATIBLE_PRODUCT_NAMES):
            return
        prompt_key = (self._connected_port, info.firmware_version)
        if self._firmware_update_prompted_for == prompt_key:
            return
        if not firmware_update_available(info.firmware_version, info.model_identifier):
            return
        self._firmware_update_prompted_for = prompt_key

        message = QMessageBox(self)
        self._firmware_update_message = message
        message.setWindowTitle(self._text("firmware_update_available_title"))
        message.setIcon(QMessageBox.Information)
        message.setText(
            self._text(
                "firmware_update_available",
                installed=info.firmware_version,
                included=target.version,
            )
        )
        update_button = message.addButton(self._text("update_now"), QMessageBox.AcceptRole)
        message.addButton(self._text("later"), QMessageBox.RejectRole)
        try:
            message.exec()
            if message.clickedButton() is update_button:
                self._open_firmware_manager()
        finally:
            self._firmware_update_message = None

    def _open_diagnostics(self) -> None:
        if self._diagnostics_dialog is not None:
            self._diagnostics_dialog.raise_()
            self._diagnostics_dialog.activateWindow()
            return
        dialog = DiagnosticsDialog(self._text, self)
        dialog.finished.connect(lambda result: self._diagnostics_closed(result))
        self._diagnostics_dialog = dialog
        self._update_diagnostics()
        if self._device_info_data is not None:
            dialog.set_controls(
                self._device_info_data.key_count,
                self._device_info_data.potentiometer_count,
            )
        for identifier in self._pressed_keys:
            dialog.set_key_state(identifier, True)
        dialog.open()

    def _diagnostics_closed(self, result: int) -> None:
        del result
        self._diagnostics_dialog = None

    def _update_diagnostics(self) -> None:
        if self._diagnostics_dialog is None:
            return
        self._diagnostics_dialog.update_device(
            self._connected,
            self._connected_port,
            self._device_info_data,
            self._heartbeat_active,
        )
        self._diagnostics_dialog.set_feedback_led(self._connected and bool(self._pressed_keys))

    def _open_firmware_manager(self) -> None:
        if self._firmware_updater.is_busy:
            return
        if self._firmware_dialog is not None:
            self._firmware_dialog.show()
            self._firmware_dialog.raise_()
            self._firmware_dialog.activateWindow()
            return
        dialog = FirmwareDialog(
            self._device_info_data,
            self._connected_port,
            self._text,
            self,
        )
        dialog.update_requested.connect(
            lambda port, model, ssid, password: self._confirm_firmware_install(
                port,
                model,
                new_device=False,
                wifi_ssid=ssid,
                wifi_password=password,
            )
        )
        dialog.install_requested.connect(
            lambda port, model, ssid, password: self._confirm_firmware_install(
                port,
                model,
                new_device=True,
                wifi_ssid=ssid,
                wifi_password=password,
            )
        )
        dialog.finished.connect(lambda result: self._firmware_dialog_closed(result))
        self._firmware_dialog = dialog
        dialog.open()

    def _firmware_dialog_closed(self, result: int) -> None:
        del result
        if not self._firmware_updater.is_busy:
            self._firmware_dialog = None

    def _confirm_firmware_install(
        self,
        port: str,
        model_identifier: str,
        new_device: bool,
        wifi_ssid: str,
        wifi_password: str,
    ) -> None:
        message = QMessageBox(self)
        message.setWindowTitle(self._text("firmware_manager"))
        message.setIcon(QMessageBox.Warning)
        message.setText(
            self._text(
                "new_esp32_firmware_warning"
                if model_identifier == "HCD-PRO"
                else "new_model_firmware_warning",
                port=port,
                model=model_identifier,
            )
            if new_device
            else self._text("firmware_update_warning")
        )
        install_button = message.addButton(self._text("install_firmware"), QMessageBox.AcceptRole)
        message.addButton(self._text("cancel"), QMessageBox.RejectRole)
        message.exec()
        if message.clickedButton() is install_button:
            self._begin_firmware_install(
                port,
                model_identifier,
                new_device,
                wifi_ssid,
                wifi_password,
            )

    def _begin_firmware_install(
        self,
        port: str,
        model_identifier: str,
        new_device: bool,
        wifi_ssid: str,
        wifi_password: str,
    ) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.set_busy(True)
        wifi_ota = model_identifier == "HCD-PRO" and port.startswith("Wi-Fi")
        if not wifi_ota:
            self._device.stop()
        QTimer.singleShot(
            180,
            lambda: self._firmware_updater.start(
                port,
                model_identifier,
                allow_existing_bootloader=new_device,
                wifi_ssid=wifi_ssid,
                wifi_password=wifi_password,
            ),
        )

    def _firmware_status_changed(self, message: str) -> None:
        self.statusBar().showMessage(message)
        if self._firmware_dialog is not None:
            self._firmware_dialog.set_status(message)

    def _firmware_progress_changed(self, value: int) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.set_progress(value)

    def _firmware_log_changed(self, log: str) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.set_log(log)

    def _show_esp32_bootloader_assistant(self) -> None:
        message = QMessageBox(self)
        message.setWindowTitle(self._text("esp32_bootloader_title"))
        message.setIcon(QMessageBox.Information)
        message.setText(self._text("esp32_bootloader_instructions"))
        continue_button = message.addButton(
            self._text("esp32_bootloader_continue"), QMessageBox.AcceptRole
        )
        message.addButton(self._text("cancel"), QMessageBox.RejectRole)
        message.exec()
        if message.clickedButton() is continue_button:
            self._firmware_updater.resume_esp32_install()
        else:
            self._firmware_updater.cancel()

    def _firmware_finished(self, successful: bool, message: str) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.finish(successful, message)
        QTimer.singleShot(1800, self._device.start)

    def _device_event(self, event: DeviceEvent) -> None:
        if event.kind == EventKind.SLIDER:
            self._has_activity = True
            value = round(int(event.state) * 100 / 1023)
            if event.control_id == 2:
                self._last_microphone_input_at = time.monotonic()
                self._pending_microphone_value = value
                self._device_preview.set_pro_microphone_value(value)
                self._activity_label.setText(
                    f"{self._text('microphone_volume')}: {value}%"
                )
                self._microphone_action_timer.start()
            else:
                self._last_slider_input_at = time.monotonic()
                self._pending_slider_value = value
                self._device_preview.set_pro_slider_value(value)
                self._activity_label.setText(
                    f"{self._text('vertical_fader')}: {value}%"
                )
                self._slider_action_timer.start()
            return
        if event.kind == EventKind.POTENTIOMETER:
            self._has_activity = True
            self._activity_label.setText(
                f"Potentiometer {event.control_id}: {event.state}"
            )
            if self._diagnostics_dialog is not None:
                self._diagnostics_dialog.set_potentiometer_value(
                    event.control_id,
                    int(event.state),
                )
            return
        if event.kind == EventKind.ENCODER:
            identifier = f"P{event.control_id}"
            if identifier not in self._control_buttons:
                return
            mode = self._profile.encoder_modes.get(
                str(event.control_id),
                "volume" if event.control_id == 1 else "microphone",
            )
            button = self._control_buttons[identifier]
            button.setProperty("active", True)
            button.style().unpolish(button)
            button.style().polish(button)
            QTimer.singleShot(90, lambda item=button: self._clear_active(item))
            self._has_activity = True
            direction = -5 if event.state == "LEFT" else 5
            self._activity_label.setText(
                f"Encoder {event.control_id} · {mode} · {event.state.lower()}"
            )
            self._pending_encoder_steps[event.control_id] = max(
                -100,
                min(
                    100,
                    self._pending_encoder_steps.get(event.control_id, 0) + direction,
                ),
            )
            self._encoder_action_timer.start()
            return
        if event.kind not in {EventKind.KEY, EventKind.POTENTIOMETER_BUTTON}:
            return
        identifier = (
            str(event.control_id)
            if event.kind == EventKind.KEY
            else f"P{event.control_id}"
        )
        should_run = event.state == "DOWN"

        if identifier not in self._control_buttons:
            return
        button = self._control_buttons[identifier]
        if should_run:
            self._pressed_keys.add(identifier)
            self._key_pressed_at[identifier] = time.monotonic()
            button.setProperty("active", True)
            button.style().unpolish(button)
            button.style().polish(button)
        else:
            self._pressed_keys.discard(identifier)
            self._clear_active(button)
        self._device_preview.set_feedback_active(self._connected and bool(self._pressed_keys))
        if event.kind == EventKind.POTENTIOMETER_BUTTON:
            mode = self._profile.encoder_modes.get(
                str(event.control_id),
                "volume" if event.control_id == 1 else "microphone",
            )
            mute_command = {
                "volume": "volume_mute",
                "microphone": "microphone_mute",
            }.get(mode, "")
            action = Action(
                "system" if mute_command else "none",
                mute_command,
                f"Encoder {event.control_id} · {mode}",
            )
        else:
            action = self._action_for(identifier)
        self._has_activity = True
        self._activity_label.setText(action.label)
        if self._diagnostics_dialog is not None:
            self._diagnostics_dialog.set_key_state(identifier, should_run)
            self._diagnostics_dialog.set_feedback_led(self._connected and bool(self._pressed_keys))
        has_long_action = action.long_type != "none"
        if should_run and not has_long_action:
            self._run_device_action(identifier, "short", action)
        elif not should_run:
            pressed_at = self._key_pressed_at.pop(identifier, time.monotonic())
            held_ms = round((time.monotonic() - pressed_at) * 1000)
            if has_long_action:
                if held_ms >= action.long_press_ms:
                    self._run_device_action(identifier, "long", action.long_action())
                else:
                    self._run_device_action(identifier, "short", action)

    def _run_device_action(self, identifier: str, press_kind: str, action: Action) -> None:
        if self._statistics_enabled:
            self._statistics.record(self._profile.name, identifier, press_kind)
        self._runner.run(action)

    @staticmethod
    def _clear_active(button: QToolButton) -> None:
        button.setProperty("active", False)
        button.style().unpolish(button)
        button.style().polish(button)

    def _action_error(self, message: str) -> None:
        QMessageBox.warning(self, APP_NAME, self._text("action_error", error=message))

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._firmware_updater.is_busy:
            QMessageBox.warning(self, APP_NAME, self._text("firmware_busy_close"))
            event.ignore()
            return
        if (
            self._background_mode_active
            and not self._allow_exit
            and (sys.platform == "darwin" or QSystemTrayIcon.isSystemTrayAvailable())
        ):
            self.hide()
            event.ignore()
            return
        self._device.stop()
        if self._tray is not None:
            self._tray.hide()
        if self._menu_bar_icon is not None:
            self._menu_bar_icon.dispose()
        super().closeEvent(event)
