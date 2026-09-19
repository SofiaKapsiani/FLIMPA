"""Plot navigation SVG icons resolve from the project tree, not cwd."""

from pathlib import Path

from utils.ui_icons import (
    NAV_BUTTON_GAP,
    NAV_BUTTON_MARGIN,
    NAV_BUTTON_SIZE,
    load_ui_icon,
    ui_icon_path,
)


def test_ui_icon_files_exist():
    pan = Path(ui_icon_path("pan.svg"))
    home = Path(ui_icon_path("home.svg"))
    assert pan.is_file()
    assert home.is_file()
    assert pan.is_absolute()
    assert "icon" in pan.parts and "ui" in pan.parts


def test_load_ui_icon_not_null(qapp):
    icon = load_ui_icon("pan.svg")
    assert not icon.isNull()
    icon = load_ui_icon("home.svg")
    assert not icon.isNull()


def test_nav_overlay_metrics():
    assert 26 <= NAV_BUTTON_SIZE <= 28
    assert 3 <= NAV_BUTTON_GAP <= 4
    assert NAV_BUTTON_MARGIN == 8
