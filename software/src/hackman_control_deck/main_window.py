from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QFileInfo, QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QCloseEvent, QDesktopServices, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QApplication,
    QCheckBox,
    QDialog,
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

ACTION_TRANSLATION_KEYS = {
    "none": "no_action",
    "shortcut": "keyboard_shortcut",
    "system": "system_command",
    "text": "type_text",
    "open_url": "open_website",
    "launch": "launch_application",
}


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)

        self._store = ProfileStore()
        self._profile = Profile()
        self._selection: str | None = None
        self._control_buttons: dict[str, QToolButton] = {}
        self._social_buttons: dict[str, QToolButton] = {}
        self._background_button: QPushButton | None = None
        self._file_icon_provider = QFileIconProvider()
        self._runner = ActionRunner(self)
        self._device = HcdDeviceManager(self)
        self._firmware_updater = FirmwareUpdater(self)
        self._firmware_dialog: FirmwareDialog | None = None
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
        self._plus_progress_value = self._settings.value(
            "roadmap/plusProgress", 0, type=int
        )
        self._pro_progress_value = self._settings.value(
            "roadmap/proProgress", 0, type=int
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
        self._application_choices: list[tuple[str, str]] | None = None

        self._build_ui()
        self._resize_for_screen()
        self._build_tray()
        self._connect_signals()
        self._reload_profile_list()
        self._device.start()
        self._apply_language()
        QTimer.singleShot(1_500, self._check_release_feed_if_due)

    def _resize_for_screen(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            self.setMinimumSize(1120, 720)
            self.resize(1460, 880)
            return
        available = screen.availableGeometry()
        width = min(1500, max(1080, available.width() - 40))
        height = min(920, max(700, available.height() - 40))
        self.setMinimumSize(min(1120, width), min(720, height))
        self.resize(width, height)

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 12)
        root_layout.setSpacing(14)
        root_layout.addWidget(self._build_top_bar())
        root_layout.addWidget(self._build_support_banner())
        root_layout.addWidget(self._build_roadmap())

        body = QHBoxLayout()
        body.setSpacing(14)
        body.addWidget(self._build_sidebar(), 0)
        body.addWidget(self._build_device_panel(), 1)
        body.addWidget(self._build_editor(), 0)
        root_layout.addLayout(body, 1)
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
        logo.setPixmap(logo_pixmap.scaled(330, 156, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(330, 156)
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
            button.setIconSize(QSize(22, 22))
            button.setFixedSize(36, 36)
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

        self._plus_progress_label = QLabel()
        layout.addWidget(self._plus_progress_label)
        self._plus_progress = QProgressBar()
        self._plus_progress.setRange(0, 100)
        self._plus_progress.setValue(max(0, min(100, self._plus_progress_value)))
        self._plus_progress.setFormat("%p%")
        self._plus_progress.setFixedWidth(180)
        layout.addWidget(self._plus_progress)

        self._pro_progress_label = QLabel()
        layout.addWidget(self._pro_progress_label)
        self._pro_progress = QProgressBar()
        self._pro_progress.setRange(0, 100)
        self._pro_progress.setValue(max(0, min(100, self._pro_progress_value)))
        self._pro_progress.setFormat("%p%")
        self._pro_progress.setFixedWidth(180)
        layout.addWidget(self._pro_progress)
        return frame

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
        frame.setFixedWidth(250)
        layout = QVBoxLayout(frame)
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
        self._feedback_hold_label = QLabel("Minimum LED duration")
        layout.addWidget(self._feedback_hold_label)
        self._feedback_hold_spin = QSpinBox()
        self._feedback_hold_spin.setRange(0, 2000)
        self._feedback_hold_spin.setSingleStep(20)
        self._feedback_hold_spin.setSuffix(" ms")
        self._feedback_hold_spin.setValue(self._feedback_hold_ms)
        self._feedback_hold_spin.valueChanged.connect(self._set_feedback_hold_ms)
        layout.addWidget(self._feedback_hold_spin)
        self._statistics_checkbox = QCheckBox("Enable local statistics")
        self._statistics_checkbox.setChecked(self._statistics_enabled)
        self._statistics_checkbox.toggled.connect(self._set_statistics_enabled)
        layout.addWidget(self._statistics_checkbox)
        self._statistics_button = QPushButton("View statistics…")
        self._statistics_button.clicked.connect(self._open_statistics)
        layout.addWidget(self._statistics_button)
        self._version_label = QLabel(f"Desktop app {APP_VERSION}", objectName="subtitle")
        layout.addWidget(self._version_label)
        return frame

    def _build_device_panel(self) -> QWidget:
        frame = QFrame(objectName="devicePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(28, 22, 28, 24)
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
        frame.setFixedWidth(300)
        outer_layout = QVBoxLayout(frame)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 18, 18, 18)
        self._action_title = QLabel("Action", objectName="sectionTitle")
        layout.addWidget(self._action_title)
        self._selection_label = QLabel("Select a key", objectName="subtitle")
        layout.addWidget(self._selection_label)
        layout.addSpacing(10)

        self._press_tabs = QTabWidget()
        short_tab = QWidget()
        short_layout = QVBoxLayout(short_tab)
        short_layout.setContentsMargins(10, 14, 10, 14)
        self._display_name_label = QLabel("Display name")
        short_layout.addWidget(self._display_name_label)
        self._label_edit = QLineEdit()
        self._label_edit.setEnabled(False)
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
        short_layout.addWidget(self._value_edit)
        self._preset_combo = QComboBox()
        self._preset_combo.setVisible(False)
        self._preset_combo.currentIndexChanged.connect(self._apply_preset)
        short_layout.addWidget(self._preset_combo)
        self._browse_button = QPushButton("Browse…")
        self._browse_button.setVisible(False)
        self._browse_button.clicked.connect(self._browse_application)
        short_layout.addWidget(self._browse_button)
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
        long_layout.addWidget(self._long_value_edit)
        self._long_preset_combo = QComboBox()
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
        self._long_press_delay_label = QLabel("Long press duration")
        long_layout.addWidget(self._long_press_delay_label)
        long_layout.addWidget(self._long_press_delay)
        long_layout.addStretch()

        self._press_tabs.addTab(short_tab, "Short press")
        self._press_tabs.addTab(long_tab, "Long press")
        layout.addWidget(self._press_tabs, 1)
        self._save_action_button = QPushButton("Save actions", objectName="accent")
        self._save_action_button.clicked.connect(self._save_action)
        layout.addWidget(self._save_action_button)
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
        self._release_feed.loaded.connect(self._release_feed_loaded)
        self._release_feed.failed.connect(self._release_feed_failed)

    def _text(self, key: str, **values: object) -> str:
        return translate(self._language, key, **values)

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
        self._long_browse_button.setText(self._text("browse"))
        self._save_action_button.setText(self._text("save_action"))
        self._test_action_button.setText(self._text("test_action"))
        self._test_long_action_button.setText(self._text("test_long_action"))
        self._long_press_delay_label.setText(self._text("long_press_duration"))
        self._press_tabs.setTabText(0, self._text("short_press"))
        self._press_tabs.setTabText(1, self._text("long_press"))
        self._firmware_button.setText(self._text("firmware_button"))
        self._updates_button.setText(self._text("check_updates"))
        self._diagnostics_button.setText(self._text("diagnostics_button"))
        self._reset_keys_button.setText(
            self._text("reset_visible_controls", count=len(self._control_buttons))
        )
        self._feedback_hold_label.setText(self._text("minimum_led_duration"))
        self._statistics_checkbox.setText(self._text("enable_statistics"))
        self._statistics_button.setText(self._text("view_statistics"))
        self._shortcut_hint.setText(self._text("shortcut_hint"))
        self._version_label.setText(self._text("desktop_app", version=APP_VERSION))
        self._credit_label.setText(self._text("credits"))
        self._roadmap_title.setText(self._text("community_roadmap"))
        self._roadmap_message.setText(self._text("roadmap_message"))
        self._plus_progress_label.setText(self._text("hcd_plus"))
        self._pro_progress_label.setText(self._text("hcd_pro"))
        self._plus_progress_label.setToolTip(self._text("hcd_plus_details"))
        self._plus_progress.setToolTip(self._text("hcd_plus_details"))
        self._pro_progress_label.setToolTip(self._text("hcd_pro_details"))
        self._pro_progress.setToolTip(self._text("hcd_pro_details"))

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
            self._selection_label.setText(
                f"Potentiometer {self._selection[1:]} click"
                if self._selection.startswith("P")
                else self._text("key", number=self._selection)
            )
        else:
            self._selection_label.setText(self._text("select_key"))
        self._connection_changed(self._connected, self._connected_port)
        self._update_value_hint()
        self._update_long_value_hint()
        self._refresh_conflicts()

    def _check_release_feed_if_due(self) -> None:
        last_check = self._settings.value("updates/lastCheck", 0, type=int)
        if int(time.time()) - last_check >= RELEASE_CHECK_INTERVAL_SECONDS:
            self._start_release_check(manual=False)

    def _check_release_feed_manually(self) -> None:
        self._start_release_check(manual=True)

    def _start_release_check(self, *, manual: bool) -> None:
        if self._release_feed.is_busy:
            return
        self._manual_release_check = manual
        self._updates_button.setEnabled(False)
        self.statusBar().showMessage(self._text("checking_updates"))
        self._release_feed.check()

    def _release_feed_loaded(self, data: ReleaseFeedData) -> None:
        manual = self._manual_release_check
        self._manual_release_check = False
        self._updates_button.setEnabled(True)
        self._settings.setValue("updates/lastCheck", int(time.time()))

        self._plus_progress.setValue(data.plus_progress)
        self._pro_progress.setValue(data.pro_progress)
        self._settings.setValue("roadmap/plusProgress", data.plus_progress)
        self._settings.setValue("roadmap/proProgress", data.pro_progress)

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
        self.statusBar().showMessage(self._text("update_check_failed"), 5_000)
        if not manual:
            return
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
        if self._selection:
            self._show_action(self._selection)

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
        self._selection_label.setText(
            f"Potentiometer {identifier[1:]} click"
            if identifier.startswith("P")
            else self._text("key", number=identifier)
        )
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
            self._update_value_hint()
            self._update_long_value_hint()
        finally:
            self._loading_action = False

    def _action_type_changed(self, index: int = -1) -> None:
        del index
        if not self._loading_action:
            self._label_edit.clear()
            self._value_edit.clear()
        self._update_value_hint()

    def _long_action_type_changed(self, index: int = -1) -> None:
        del index
        if not self._loading_action:
            self._long_label_edit.clear()
            self._long_value_edit.clear()
        self._update_long_value_hint()

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
        if self._selection:
            self._show_action(self._selection)
        self._has_activity = False
        self._activity_label.setText(self._text("no_activity"))
        self.statusBar().showMessage(
            self._text("visible_controls_reset", count=control_count),
            2500,
        )

    def _save_action(self) -> None:
        if not self._selection:
            return
        long_primary = self._long_editor_action()
        action = Action(
            type=str(self._action_type.currentData()),
            value=self._value_edit.text().strip(),
            label=self._label_edit.text().strip() or "Unassigned",
            long_type=long_primary.type,
            long_value=long_primary.value,
            long_label=long_primary.label,
            long_press_ms=self._long_press_delay.value(),
        )
        self._profile.keys[self._selection] = action
        self._store.save(self._profile)
        self._refresh_control_labels()
        self.statusBar().showMessage(self._text("saved", name=action.label), 2500)

    def _editor_action(self) -> Action:
        if not self._selection:
            return Action()
        return Action(
            type=str(self._action_type.currentData()),
            value=self._value_edit.text().strip(),
            label=self._label_edit.text().strip() or "Unassigned",
            long_press_ms=self._long_press_delay.value(),
        )

    def _long_editor_action(self) -> Action:
        return Action(
            type=str(self._long_action_type.currentData()),
            value=self._long_value_edit.text().strip(),
            label=self._long_label_edit.text().strip() or self._text("long_press"),
        )

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
            button.setIcon(
                self._application_icon(action.value) if action.type == "launch" else QIcon()
            )
            button.setToolTip(
                f"{full_label}\n{action.value}" if action.type == "launch" else full_label
            )
        self._refresh_conflicts()

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
                self._preset_combo.addItem(self._text(label_key), command)
        elif action_type == "launch":
            self._preset_combo.addItem(self._text("choose_installed_app"), "")
            for name, path in self._installed_applications():
                self._preset_combo.addItem(name, path)

        matching_index = self._preset_combo.findData(selected_value)
        self._preset_combo.setCurrentIndex(max(0, matching_index))
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
                self._long_preset_combo.addItem(self._text(label_key), command)
        elif action_type == "launch":
            self._long_preset_combo.addItem(self._text("choose_installed_app"), "")
            for name, path in self._installed_applications():
                self._long_preset_combo.addItem(name, path)
        matching_index = self._long_preset_combo.findData(selected_value)
        self._long_preset_combo.setCurrentIndex(max(0, matching_index))
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
        return (
            ("command_volume_up", "volume_up"),
            ("command_volume_down", "volume_down"),
            ("command_volume_mute", "volume_mute"),
            ("command_play_pause", "media_play_pause"),
            ("command_next_track", "media_next"),
            ("command_previous_track", "media_previous"),
            ("command_brightness_up", "brightness_up"),
            ("command_brightness_down", "brightness_down"),
        )

    def _apply_preset(self, index: int) -> None:
        if index <= 0:
            return
        value = str(self._preset_combo.itemData(index))
        if value:
            if self._action_type.currentData() == "launch":
                self._set_application_value(value)
            else:
                self._value_edit.setText(value)
                self._label_edit.setText(
                    self._preset_combo.itemText(index).split(" — ", maxsplit=1)[0]
                )

    def _apply_long_preset(self, index: int) -> None:
        if index <= 0:
            return
        value = str(self._long_preset_combo.itemData(index))
        if not value:
            return
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
        self.statusBar().showMessage(
            self._text("application_assigned", name=application.stem, key=identifier), 2500
        )

    def _application_icon(self, value: str) -> QIcon:
        path = Path(value)
        if not value or not path.exists():
            return QIcon()
        return self._file_icon_provider.icon(QFileInfo(str(path)))

    def _installed_applications(self) -> list[tuple[str, str]]:
        if self._application_choices is not None:
            return self._application_choices
        if sys.platform != "darwin":
            return []

        applications: dict[str, str] = {}
        roots = (Path("/Applications"), Path("/System/Applications"), Path.home() / "Applications")
        for root in roots:
            if not root.is_dir():
                continue
            for directory, subdirectories, _ in os.walk(root):
                app_directories = [name for name in subdirectories if name.lower().endswith(".app")]
                for app_directory in app_directories:
                    path = Path(directory) / app_directory
                    applications.setdefault(path.stem.casefold(), str(path))
                subdirectories[:] = [
                    name for name in subdirectories if not name.lower().endswith(".app")
                ]
        self._application_choices = sorted(
            ((Path(path).stem, path) for path in applications.values()),
            key=lambda item: item[0].casefold(),
        )
        return self._application_choices

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
            self._firmware_update_prompted_for = None
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

    def _offer_firmware_update(self) -> None:
        info = self._device_info_data
        if info is None or not self._connected_port or self._firmware_updater.is_busy:
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
        message.exec()
        if message.clickedButton() is update_button:
            self._open_firmware_manager()

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
        dialog = FirmwareDialog(
            self._device_info_data,
            self._connected_port,
            self._text,
            self,
        )
        dialog.update_requested.connect(
            lambda port, model: self._confirm_firmware_install(
                port, model, new_device=False
            )
        )
        dialog.install_requested.connect(
            lambda port, model: self._confirm_firmware_install(
                port, model, new_device=True
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
    ) -> None:
        message = QMessageBox(self)
        message.setWindowTitle(self._text("firmware_manager"))
        message.setIcon(QMessageBox.Warning)
        message.setText(
            self._text(
                "new_model_firmware_warning",
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
            self._begin_firmware_install(port, model_identifier, new_device)

    def _begin_firmware_install(
        self,
        port: str,
        model_identifier: str,
        new_device: bool,
    ) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.set_busy(True)
        self._device.stop()
        QTimer.singleShot(
            180,
            lambda: self._firmware_updater.start(
                port,
                model_identifier,
                allow_existing_bootloader=new_device,
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

    def _firmware_finished(self, successful: bool, message: str) -> None:
        if self._firmware_dialog is not None:
            self._firmware_dialog.finish(successful, message)
        QTimer.singleShot(1800, self._device.start)

    def _device_event(self, event: DeviceEvent) -> None:
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
