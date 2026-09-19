"""Select all / Deselect all — checkbox and analyse flag behaviour."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton, QTableWidget, QTableWidgetItem

from utils.helper_functions import Helpers
from utils.shared_data import SharedData


def _make_table(rows):
    table = QTableWidget(len(rows), 1)
    for i, (name, checked) in enumerate(rows):
        item = QTableWidgetItem(name)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        table.setItem(i, 0, item)
    return table


@pytest.fixture
def helpers(qapp):
    window = SimpleNamespace()
    window.fileTable = _make_table([("a.tif", True), ("b.tif", False)])
    window.select_all_files_button = QPushButton("Select all")
    window.plotImages = MagicMock()
    window.canvas_tau = MagicMock()
    h = Helpers(window)
    sd = SharedData()
    sd.raw_data_dict = {
        "a.tif": {"analyse": "yes"},
        "b.tif": {"analyse": "no"},
    }
    return h, window, sd


def test_all_files_selected_partial(helpers):
    h, window, _ = helpers
    assert h._all_files_selected() is False


def test_all_files_selected_all_checked(helpers):
    h, window, _ = helpers
    window.fileTable = _make_table([("a.tif", True), ("b.tif", True)])
    assert h._all_files_selected() is True


def test_toggle_select_all_checks_every_row(helpers):
    h, window, sd = helpers
    h.toggle_all_file_selection()
    for row in range(window.fileTable.rowCount()):
        assert window.fileTable.item(row, 0).checkState() == Qt.Checked
    assert sd.raw_data_dict["a.tif"]["analyse"] == "yes"
    assert sd.raw_data_dict["b.tif"]["analyse"] == "yes"
    assert window.select_all_files_button.text() == "Deselect all"


def test_toggle_deselect_all(helpers):
    h, window, sd = helpers
    window.fileTable = _make_table([("a.tif", True), ("b.tif", True)])
    sd.raw_data_dict["b.tif"]["analyse"] = "yes"
    h.toggle_all_file_selection()
    for row in range(window.fileTable.rowCount()):
        assert window.fileTable.item(row, 0).checkState() == Qt.Unchecked
    assert sd.raw_data_dict["a.tif"]["analyse"] == "no"
    assert window.select_all_files_button.text() == "Select all"


def test_update_select_all_button_label(helpers):
    h, window, _ = helpers
    h.update_select_all_button_label()
    assert window.select_all_files_button.text() == "Select all"
    window.fileTable.item(1, 0).setCheckState(Qt.Checked)
    h.update_select_all_button_label()
    assert window.select_all_files_button.text() == "Deselect all"
