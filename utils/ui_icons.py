"""Local SVG icons for plot navigation buttons."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QPushButton

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ICON_DIR = _PROJECT_ROOT / "icon" / "ui"

NAV_BUTTON_SIZE = 26
NAV_ICON_SIZE = 14
NAV_BUTTON_GAP = 3
NAV_BUTTON_MARGIN = 8

NAV_BUTTON_STYLE = """
QPushButton {
    color: rgb(210, 210, 210);
    font-size: 13px;
    background-color: rgba(28, 28, 28, 200);
    border: 1px solid rgb(70, 70, 70);
    border-radius: 3px;
    padding: 0px;
}
QPushButton:hover {
    color: white;
    background-color: rgba(48, 68, 68, 230);
    border-color: rgb(60, 162, 161);
}
QPushButton:pressed {
    background-color: rgba(60, 162, 161, 55);
    border-color: rgb(60, 162, 161);
}
QPushButton:checked {
    color: white;
    background-color: rgba(60, 162, 161, 80);
    border-color: rgb(60, 162, 161);
}
"""


def ui_icon_path(filename: str) -> str:
    """Absolute path to a bundled SVG in icon/ui/, independent of cwd."""
    return str(_ICON_DIR / filename)


def load_ui_icon(filename: str, size: int = NAV_ICON_SIZE) -> QIcon:
    path = ui_icon_path(filename)
    if QGuiApplication.instance() is None:
        return QIcon(path)
    try:
        from PySide6.QtSvg import QSvgRenderer

        renderer = QSvgRenderer(path)
        pixel = max(size * 2, 32)
        pixmap = QPixmap(pixel, pixel)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        renderer.render(painter)
        painter.end()
        icon = QIcon()
        icon.addPixmap(pixmap)
        return icon
    except Exception:
        return QIcon(path)


def apply_nav_icon(btn: QPushButton, filename: str, tooltip: str, *, checkable: bool = False) -> None:
    btn.setText("")
    btn.setIcon(load_ui_icon(filename))
    btn.setIconSize(QSize(NAV_ICON_SIZE, NAV_ICON_SIZE))
    apply_nav_button_chrome(btn, tooltip, checkable=checkable)


def apply_nav_button_chrome(btn: QPushButton, tooltip: str, *, checkable: bool = False) -> None:
    """Shared compact chrome for overlay pan / zoom / reset buttons."""
    btn.setFixedSize(NAV_BUTTON_SIZE, NAV_BUTTON_SIZE)
    btn.setStyleSheet(NAV_BUTTON_STYLE)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setFocusPolicy(Qt.NoFocus)
    if checkable:
        btn.setCheckable(True)
