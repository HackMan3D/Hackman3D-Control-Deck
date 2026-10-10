from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .models import ACTION_TYPES, Action, Profile


ACTION_TRANSLATION_KEYS = {
    "none": "no_action",
    "shortcut": "keyboard_shortcut",
    "system": "system_command",
    "text": "type_text",
    "open_url": "open_website",
    "launch": "launch_application",
}


class KeyCombinationsEditor(QWidget):
    def __init__(
        self,
        text: Callable[..., str],
        profile: Profile,
        key_count: int,
        catalogue: Callable[[str], list[tuple[str, str, str]]],
        save_profile: Callable[[], None],
        run_action: Callable[[Action], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._text = text
        self._profile = profile
        self._catalogue = catalogue
        self._save_profile = save_profile
        self._run_action = run_action

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        help_label = QLabel(text("key_combinations_help"))
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self._list = QListWidget()
        self._list.setMaximumHeight(90)
        self._list.currentTextChanged.connect(self._load_combination)
        layout.addWidget(self._list)

        layout.addWidget(QLabel(text("choose_two_or_three_keys"), objectName="sectionTitle"))
        self._key_grid = QGridLayout()
        self._keys: dict[str, QCheckBox] = {}
        layout.addLayout(self._key_grid)
        self._rebuild_keys(key_count)

        layout.addWidget(QLabel(text("display_name")))
        self._label = QLineEdit()
        layout.addWidget(self._label)

        layout.addWidget(QLabel(text("action_type")))
        self._action_type = QComboBox()
        for action_type in ACTION_TYPES:
            self._action_type.addItem(text(ACTION_TRANSLATION_KEYS[action_type]), action_type)
        self._action_type.currentIndexChanged.connect(self._action_type_changed)
        layout.addWidget(self._action_type)

        self._search = QLineEdit()
        self._search.setPlaceholderText(text("search_actions"))
        self._search.textChanged.connect(self._search_actions)
        layout.addWidget(self._search)
        self._search_results = QListWidget()
        self._search_results.setVisible(False)
        self._search_results.itemClicked.connect(self._apply_search_result)
        layout.addWidget(self._search_results)

        self._value_label = QLabel(text("value"))
        layout.addWidget(self._value_label)
        self._value = QLineEdit()
        layout.addWidget(self._value)

        self._preset = QComboBox()
        self._preset.currentIndexChanged.connect(self._preset_selected)
        layout.addWidget(self._preset)

        self._browse = QPushButton(text("browse"))
        self._browse.clicked.connect(self._browse_application)
        layout.addWidget(self._browse)
        # Keep application/system/shortcut choices immediately below the
        # action type, matching the short- and long-press editors.
        layout.removeWidget(self._preset)
        layout.removeWidget(self._browse)
        preset_position = layout.indexOf(self._action_type) + 1
        layout.insertWidget(preset_position, self._preset)
        layout.insertWidget(preset_position + 1, self._browse)

        buttons = QHBoxLayout()
        delete_button = QPushButton(text("delete_combination"))
        delete_button.clicked.connect(self._delete)
        buttons.addWidget(delete_button)
        test_button = QPushButton(text("test_action"))
        test_button.clicked.connect(self._test)
        buttons.addWidget(test_button)
        buttons.addStretch()
        save_button = QPushButton(text("save_combination"), objectName="accent")
        save_button.clicked.connect(self._save)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)
        layout.addStretch()

        self._action_type_changed()
        self._refresh()

    def set_context(self, profile: Profile, key_count: int) -> None:
        self._profile = profile
        self._rebuild_keys(key_count)
        self._refresh()

    def _rebuild_keys(self, key_count: int) -> None:
        for checkbox in self._keys.values():
            self._key_grid.removeWidget(checkbox)
            checkbox.deleteLater()
        self._keys.clear()
        for index in range(1, key_count + 1):
            checkbox = QCheckBox(self._text("key", number=index))
            self._keys[str(index)] = checkbox
            self._key_grid.addWidget(checkbox, (index - 1) // 4, (index - 1) % 4)

    def _refresh(self, select: str = "") -> None:
        self._list.blockSignals(True)
        self._list.clear()
        self._list.addItems(
            sorted(self._profile.chords, key=lambda key: tuple(map(int, key.split("+"))))
        )
        self._list.blockSignals(False)
        if select:
            matches = self._list.findItems(select, Qt.MatchExactly)
            if matches:
                self._list.setCurrentItem(matches[0])

    def _load_combination(self, key: str) -> None:
        identifiers = set(key.split("+"))
        for identifier, checkbox in self._keys.items():
            checkbox.setChecked(identifier in identifiers)
        action = self._profile.chords.get(key)
        if action is None:
            return
        self._label.setText(action.label)
        self._action_type.setCurrentIndex(self._action_type.findData(action.type))
        self._value.setText(action.value)
        self._select_matching_preset(action.value)

    def _action_type_changed(self, unused: int = -1) -> None:
        del unused
        action_type = str(self._action_type.currentData())
        free_value = action_type in {"shortcut", "text", "open_url"}
        self._value.setVisible(free_value)
        self._value_label.setVisible(free_value)
        self._browse.setVisible(action_type == "launch")
        choices = self._catalogue(action_type)
        self._preset.blockSignals(True)
        self._preset.clear()
        placeholder = {
            "shortcut": "choose_shortcut",
            "system": "choose_system_command",
            "launch": "choose_installed_app",
        }.get(action_type, "choose_action")
        self._preset.addItem(self._text(placeholder), None)
        for label, item_type, value in choices:
            self._preset.addItem(label, (item_type, value, label))
        self._preset.blockSignals(False)
        self._preset.setVisible(bool(choices))

    def _search_actions(self, query: str) -> None:
        self._search_results.clear()
        normalized = query.strip().casefold()
        if not normalized:
            self._search_results.setVisible(False)
            return
        for label, action_type, value in self._catalogue(""):
            if normalized not in f"{label} {value}".casefold():
                continue
            item = QListWidgetItem(label if not value else f"{label} — {value}")
            item.setData(Qt.UserRole, (action_type, value, label))
            self._search_results.addItem(item)
        self._search_results.setVisible(self._search_results.count() > 0)
        self._search_results.setMaximumHeight(
            min(150, 32 * max(1, self._search_results.count()))
        )

    def _apply_search_result(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.UserRole)
        if not isinstance(data, tuple):
            return
        action_type, value, label = data
        self._action_type.setCurrentIndex(self._action_type.findData(action_type))
        self._value.setText(str(value))
        self._label.setText(str(label))
        self._select_matching_preset(str(value))
        self._search.clear()

    def _preset_selected(self, index: int) -> None:
        data = self._preset.itemData(index)
        if not isinstance(data, tuple):
            return
        _action_type, value, label = data
        self._value.setText(str(value))
        self._label.setText(str(label))

    def _select_matching_preset(self, value: str) -> None:
        for index in range(1, self._preset.count()):
            data = self._preset.itemData(index)
            if isinstance(data, tuple) and data[1] == value:
                self._preset.setCurrentIndex(index)
                return
        self._preset.setCurrentIndex(0)

    def _browse_application(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            self._text("choose_application"),
            str(Path.home()),
        )
        if path:
            self._value.setText(path)
            self._label.setText(Path(path).stem)

    def _selected_key(self) -> str:
        selected = [identifier for identifier, box in self._keys.items() if box.isChecked()]
        return "+".join(sorted(selected, key=int))

    def _current_action(self) -> Action:
        return Action(
            str(self._action_type.currentData()),
            self._value.text().strip(),
            self._label.text().strip() or self._selected_key(),
        )

    def _save(self) -> None:
        key = self._selected_key()
        if len(key.split("+")) not in {2, 3}:
            QMessageBox.warning(
                self,
                self._text("key_combinations"),
                self._text("choose_two_or_three_keys"),
            )
            return
        self._profile.chords[key] = self._current_action()
        self._save_profile()
        self._refresh(key)

    def _test(self) -> None:
        self._run_action(self._current_action())

    def _delete(self) -> None:
        key = self._list.currentItem().text() if self._list.currentItem() else ""
        if key and key in self._profile.chords:
            del self._profile.chords[key]
            self._save_profile()
            self._refresh()
