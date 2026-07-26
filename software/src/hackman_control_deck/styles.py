APP_STYLE = """
QWidget {
    background: #090909;
    color: #f4f4f4;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow { background: #050505; }
QLabel, QCheckBox { background: transparent; }
QFrame#topBar, QFrame#sidebar, QFrame#editor, QFrame#devicePanel, QFrame#supportBanner, QFrame#roadmapBanner {
    background: #101010;
    border: 1px solid #2b2b2b;
    border-radius: 12px;
}
QFrame#firmwareCard {
    background: #151515;
    border: 1px solid #343434;
    border-radius: 9px;
}
QFrame#supportBanner { background: #141414; }
QFrame#roadmapBanner { background: #0d0d0d; }
QFrame#topBar { background: #050505; }
QLabel#supportText { color: #c8c8c8; }
QLabel#roadmapText { color: #a8a8a8; }
QLabel#title { font-size: 17pt; font-weight: 700; }
QLabel#subtitle { color: #a0a0a0; }
QLabel#sectionTitle { font-size: 12pt; font-weight: 650; }
QLabel#connectionDot { color: #484848; font-size: 17pt; }
QLabel#connectionDot[connected="true"] { color: #ff3b30; }
QLabel#diagnosticKey, QLabel#diagnosticLed {
    background: #151515;
    color: #9a9a9a;
    border: 1px solid #383838;
    border-radius: 9px;
    padding: 10px;
    font-weight: 650;
}
QLabel#diagnosticKey[active="true"] {
    background: #f4f4f4;
    color: #080808;
    border-color: #ffffff;
}
QLabel#diagnosticLed[active="true"] { color: #ff4a4a; border-color: #ff4a4a; }
QPushButton {
    background: #1a1a1a;
    border: 1px solid #363636;
    border-radius: 8px;
    padding: 8px 12px;
}
QPushButton:hover { border-color: #ffffff; background: #242424; }
QPushButton:pressed { background: #353535; }
QPushButton#resetKeysButton {
    color: #c8c8c8;
    background: #121212;
    border-color: #3d3d3d;
}
QPushButton#resetKeysButton:hover {
    color: #ffffff;
    background: #242424;
    border-color: #ffffff;
}
QPushButton#conflictButton {
    color: #ffcc66;
    background: #211a0c;
    border-color: #7a5b1d;
}
QPushButton#conflictButton:hover { border-color: #ffcc66; }
QPushButton#accent {
    background: #f4f4f4;
    color: #080808;
    border-color: #ffffff;
    font-weight: 700;
}
QPushButton#supportAccent {
    background: #f4f4f4;
    color: #080808;
    border-color: #ffffff;
    font-weight: 700;
}
QPushButton#supportAccent:hover { background: #ffffff; }
QToolButton#deviceKey {
    font-size: 8pt;
    font-weight: 600;
    background: rgba(8, 8, 8, 155);
    border: 2px solid rgba(210, 210, 210, 115);
    border-radius: 10px;
    padding: 3px;
}
QToolButton#deviceKey:hover { border-color: #ffffff; background: rgba(42, 42, 42, 190); }
QToolButton#deviceKey[selected="true"] { border-color: #ffffff; background: rgba(15, 15, 15, 210); }
QToolButton#deviceKey[active="true"] { background: #ffffff; color: #070707; border-color: white; }
QWidget#socialLinks { background: transparent; }
QToolButton#socialButton {
    background: #181818;
    border: 1px solid #363636;
    border-radius: 18px;
    padding: 6px;
}
QToolButton#socialButton:hover {
    background: #3a3a3a;
    border-color: #ffffff;
}
QToolButton#socialButton:pressed { background: #454545; }
QToolTip {
    color: #080808;
    background-color: #f4f4f4;
    border: 1px solid #ffffff;
    border-radius: 7px;
    padding: 7px 10px;
    font-weight: 600;
}
QListWidget, QLineEdit, QComboBox, QSpinBox, QPlainTextEdit {
    background: #080808;
    border: 1px solid #363636;
    border-radius: 7px;
    padding: 7px;
    selection-background-color: #dedede;
    selection-color: #080808;
}
QListWidget::item { padding: 8px; border-radius: 6px; }
QListWidget::item:selected { background: #ededed; color: #080808; }
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #555555;
    border-radius: 4px;
    background: #090909;
}
QCheckBox::indicator:checked {
    background: #ffffff;
    border-color: #ffffff;
}
QProgressBar {
    color: #ffffff;
    background: #080808;
    border: 1px solid #3b3b3b;
    border-radius: 7px;
    text-align: center;
    min-height: 18px;
}
QProgressBar::chunk {
    background: #f4f4f4;
    border-radius: 6px;
}
QStatusBar { color: #a0a0a0; }
QTabWidget::pane {
    background: #0d0d0d;
    border: 1px solid #363636;
    border-radius: 8px;
}
QTabBar::tab {
    background: #151515;
    color: #a8a8a8;
    border: 1px solid #363636;
    padding: 9px 12px;
    min-width: 92px;
}
QTabBar::tab:selected {
    background: #f4f4f4;
    color: #080808;
    font-weight: 700;
}
"""
