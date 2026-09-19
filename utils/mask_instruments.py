"""Floating Masking tools control over intensity / lifetime plots.

One Masking tools button + vertical popup over the image.
See README.md (Masking).
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QLabel,
    QSizePolicy,
)

from utils.auto_segmentation import AUTO_SEGMENT_UI_ENABLED
from utils.ui_icons import (
    NAV_BUTTON_GAP,
    NAV_BUTTON_MARGIN,
    apply_nav_button_chrome,
    apply_nav_icon,
)

_ZOOM_FACTOR = 1.35


def _image_ax(canvas):
    """Main image axes (skip colorbar axes)."""
    for ax in canvas.figure.axes:
        if ax.images:
            return ax
    return canvas.figure.axes[0] if canvas.figure.axes else None


def _reset_image_limits(ax) -> None:
    if ax is None or not ax.images:
        return
    arr = ax.images[0].get_array()
    ny, nx = arr.shape[:2]
    ax.set_xlim(-0.5, nx - 0.5)
    ax.set_ylim(ny - 0.5, -0.5)


def _zoom_image_ax(ax, factor: float) -> None:
    """Zoom around centre; factor > 1 zooms in."""
    if ax is None or not ax.images:
        return
    arr = ax.images[0].get_array()
    ny, nx = arr.shape[:2]

    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    xc = (x0 + x1) / 2
    yc = (y0 + y1) / 2
    half_w = (x1 - x0) / 2 / factor
    half_h = abs(y1 - y0) / 2 / factor

    half_w = float(np.clip(half_w, max(2.0, nx / 80.0), nx / 2))
    half_h = float(np.clip(half_h, max(2.0, ny / 80.0), ny / 2))

    ax.set_xlim(xc - half_w, xc + half_w)
    if y0 > y1:
        ax.set_ylim(yc + half_h, yc - half_h)
    else:
        ax.set_ylim(yc - half_h, yc + half_h)


_PANEL_STYLE = """
QFrame#maskInstrumentsPanel {
    background-color: rgb(45, 45, 45);
    border: 1px solid rgb(60, 162, 161);
    border-radius: 4px;
}
QPushButton {
    color: white;
    font-size: 11px;
    text-align: left;
    padding: 6px 10px;
    border: none;
    background: transparent;
}
QPushButton:hover {
    background-color: rgb(60, 80, 80);
}
QPushButton:checked {
    background-color: rgb(60, 162, 161);
    color: white;
}
QLabel {
    color: rgb(180, 180, 180);
    font-size: 10px;
}
"""

_BTN_STYLE = """
QPushButton {
    color: white;
    font-size: 11px;
    background-color: rgba(45, 45, 45, 210);
    border: 1px solid rgb(60, 162, 161);
    border-radius: 4px;
    padding: 4px 10px;
}
QPushButton:hover {
    background-color: rgb(60, 80, 80);
}
"""


class PlotZoomOverlay:
    """Zoom in / out / reset buttons anchored top-right on the plot host."""

    def __init__(self, host: QWidget, canvas, editor):
        self.host = host
        self.canvas = canvas
        self.editor = editor

        self.zoom_out_btn = QPushButton("−", host)
        self.zoom_in_btn = QPushButton("+", host)
        self.zoom_reset_btn = QPushButton(host)
        apply_nav_button_chrome(self.zoom_out_btn, "Zoom out")
        apply_nav_button_chrome(self.zoom_in_btn, "Zoom in")
        apply_nav_icon(self.zoom_reset_btn, "home.svg", "Reset view")
        self.zoom_out_btn.clicked.connect(lambda: self._apply_zoom(1 / _ZOOM_FACTOR))
        self.zoom_in_btn.clicked.connect(lambda: self._apply_zoom(_ZOOM_FACTOR))
        self.zoom_reset_btn.clicked.connect(self._reset_zoom)

        self._pan = None

    def attach_pan(self, pan):
        self._pan = pan

    def _apply_zoom(self, factor: float):
        ax = _image_ax(self.canvas)
        if ax is None:
            return
        _zoom_image_ax(ax, factor)
        if self.editor._inspect_xy is not None:
            self.editor._draw_inspect_marker()
        self.canvas.draw_idle()

    def _reset_zoom(self):
        ax = _image_ax(self.canvas)
        if ax is None:
            return
        _reset_image_limits(ax)
        if self.editor._inspect_xy is not None:
            self.editor._draw_inspect_marker()
        self.canvas.draw_idle()

    def reposition(self):
        margin = NAV_BUTTON_MARGIN
        gap = NAV_BUTTON_GAP
        all_buttons = []
        if self._pan is not None:
            all_buttons.append(self._pan.pan_btn)
        all_buttons.extend([self.zoom_reset_btn, self.zoom_in_btn, self.zoom_out_btn])
        total_w = sum(b.width() for b in all_buttons) + gap * max(0, len(all_buttons) - 1)
        x = max(margin, self.host.width() - total_w - margin)
        y = margin
        x_cursor = x
        for btn in all_buttons:
            btn.move(x_cursor, y)
            btn.raise_()
            x_cursor += btn.width() + gap


class MaskInstrumentsOverlay:
    """
    Single Masking button + vertical popup anchored top-left on the plot host.
    Does not block the rest of the canvas — only the button/panel receive clicks.
    """

    def __init__(self, host: QWidget, main_window, ui_layout):
        self.host = host
        self.main_window = main_window
        self.ui_layout = ui_layout
        self.editor = main_window.mask_editor

        self.btn = QPushButton("Masking tools", host)
        self.btn.setStyleSheet(_BTN_STYLE)
        self.btn.setCursor(Qt.PointingHandCursor)
        self.btn.clicked.connect(self._toggle_popup)

        self.popup = QFrame(host)
        self.popup.setObjectName("maskInstrumentsPanel")
        self.popup.setStyleSheet(_PANEL_STYLE)
        self.popup.hide()

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(4, 4, 4, 4)
        popup_layout.setSpacing(2)

        # Back exits the active masking tool and closes the menu
        back_btn = QPushButton("Back")
        back_btn.setToolTip("Stop the current masking tool and close this menu.")
        back_btn.clicked.connect(self._back_pressed)
        popup_layout.addWidget(back_btn)

        tooltips = {
            "Polygon": "Click points on the image; close on first point or Enter.",
            "Lasso": "Draw a freehand outline.",
            "Brush": "Paint regions; start on existing region to extend it.",
            "Delete region": "Click a labelled region to remove that whole region.",
            "Auto segment": "Intensity auto-segmentation, then refine manually.",
            "Clear mask": "Remove all regions for this file and stop the masking tool.",
        }
        for label, tool in [
            ("Polygon", "poly"),
            ("Lasso", "lasso"),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tooltips[label])
            btn.clicked.connect(lambda checked=False, t=tool: self._pick_tool(t))
            popup_layout.addWidget(btn)

        brush_btn = QPushButton("Brush")
        brush_btn.setToolTip(tooltips["Brush"])
        brush_btn.clicked.connect(lambda: self._pick_tool("brush"))
        popup_layout.addWidget(brush_btn)

        if AUTO_SEGMENT_UI_ENABLED:
            auto_btn = QPushButton("Auto segment")
            auto_btn.setToolTip(tooltips["Auto segment"])
            auto_btn.clicked.connect(self._run_auto_segment)
            popup_layout.addWidget(auto_btn)

        delete_region_btn = QPushButton("Delete region")
        delete_region_btn.setToolTip(tooltips["Delete region"])
        delete_region_btn.clicked.connect(lambda: self._pick_tool("delete_region"))
        popup_layout.addWidget(delete_region_btn)

        self.antimask_btn = QPushButton("Eraser")
        self.antimask_btn.setCheckable(True)
        self.antimask_btn.setToolTip(
            "Pixel eraser with adjustable size (same control as Brush). "
            "Selecting another tool (Polygon, Lasso, Brush, …) switches away from Eraser."
        )
        self.antimask_btn.clicked.connect(self._on_eraser_clicked)
        popup_layout.addWidget(self.antimask_btn)

        # Size control sits below Brush/Eraser so showing it does not shift those buttons mid-click
        self.size_row = QWidget()
        size_layout = QVBoxLayout(self.size_row)
        size_layout.setContentsMargins(6, 0, 6, 4)
        size_layout.setSpacing(2)
        self.size_label = QLabel("Brush size (px)")
        size_layout.addWidget(self.size_label)
        self.brush_spin = QSpinBox()
        self.brush_spin.setRange(1, 30)
        self.brush_spin.setValue(self.editor.brush_width)
        self.brush_spin.valueChanged.connect(self.editor.set_brush_width)
        size_layout.addWidget(self.brush_spin)
        self.size_row.hide()
        popup_layout.addWidget(self.size_row)

        clear_btn = QPushButton("Clear mask")
        clear_btn.setToolTip(tooltips["Clear mask"])
        clear_btn.clicked.connect(self._clear_mask)
        popup_layout.addWidget(clear_btn)

        self.popup.setFixedWidth(168)
        self.reposition()

    def reposition(self):
        margin = 8
        self.btn.adjustSize()
        self.btn.move(margin, margin)
        self.btn.raise_()
        if self.popup.isVisible():
            self.popup.move(margin, margin + self.btn.height() + 4)
            self.popup.raise_()

    def _update_btn_label(self):
        if self.editor.antimask_mode:
            self.btn.setText("Masking tools · Eraser")
        else:
            self.btn.setText("Masking tools")

    def _set_eraser_checked(self, enabled: bool):
        self.antimask_btn.blockSignals(True)
        self.antimask_btn.setChecked(enabled)
        self.antimask_btn.blockSignals(False)

    def _sync_size_controls(self):
        """Show width spinner only while Brush is active (including Eraser + brush)."""
        show = self.editor._tool == "brush"
        self.size_row.setVisible(show)
        if show:
            if self.editor.antimask_mode:
                self.size_label.setText("Eraser size (px)")
            else:
                self.size_label.setText("Brush size (px)")
            self.brush_spin.blockSignals(True)
            self.brush_spin.setValue(self.editor.brush_width)
            self.brush_spin.blockSignals(False)
        self.popup.adjustSize()
        self.reposition()

    def _clear_eraser_mode(self):
        """Turn Eraser off in both editor state and UI."""
        self.editor.set_antimask_mode(False)
        self._set_eraser_checked(False)
        self._update_btn_label()
        self._sync_size_controls()

    def _back_pressed(self):
        if self.editor._tool is not None and self.editor._tool != "inspect":
            self.editor.deactivate()
        self._clear_eraser_mode()
        self._close_popup()

    def _toggle_popup(self):
        if self.popup.isVisible():
            self._close_popup()
        else:
            self._set_eraser_checked(self.editor.antimask_mode)
            self._sync_size_controls()
            self.popup.show()
            self.popup.raise_()

    def _close_popup(self):
        self.popup.hide()

    def _pick_tool(self, tool: str):
        # Switching to any draw/edit tool leaves Eraser mode
        self.editor.set_antimask_mode(False)
        self._set_eraser_checked(False)
        self.editor.activate_tool(tool)
        self._update_btn_label()
        if tool == "brush":
            # Keep menu open so brush width can be adjusted
            self._sync_size_controls()
            if not self.popup.isVisible():
                self.popup.show()
                self.popup.raise_()
            return
        self.size_row.hide()
        self._close_popup()

    def _run_auto_segment(self):
        if not AUTO_SEGMENT_UI_ENABLED:
            return
        self._clear_eraser_mode()
        self._close_popup()
        self.ui_layout.run_auto_segmentation()

    def _on_eraser_clicked(self):
        # checkable button already flipped; drive editor from the new checked state
        enabled = self.antimask_btn.isChecked()
        self.editor.set_antimask_mode(enabled)
        self._update_btn_label()
        if enabled:
            # Defer so layout / plot refresh cannot eat the click that turned Eraser on
            QTimer.singleShot(0, self._after_eraser_enabled)
        else:
            # Turning Eraser off leaves brush active so size control still applies
            if self.editor._tool != "brush":
                self.editor.activate_tool("brush")
            self.editor.set_antimask_mode(False)
            self._sync_size_controls()

    def _after_eraser_enabled(self):
        if not self.editor.antimask_mode:
            return
        self.editor.activate_tool("brush")
        self._set_eraser_checked(True)
        self._sync_size_controls()
        if not self.popup.isVisible():
            self.popup.show()
            self.popup.raise_()

    def _clear_mask(self):
        self.editor.clear_mask()
        self._clear_eraser_mode()
        self.size_row.hide()
        self._close_popup()

class PlotWithMaskInstruments(QWidget):
    """Wraps a FigureCanvas; repositions the overlay on resize."""

    def __init__(self, canvas, main_window, ui_layout, parent=None):
        super().__init__(parent)
        self._canvas = canvas
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(canvas)
        self._overlay = MaskInstrumentsOverlay(self, main_window, ui_layout)
        self._zoom = PlotZoomOverlay(self, canvas, main_window.mask_editor)
        from utils.plot_pan import PlotPanController

        self._pan = PlotPanController(self, canvas, main_window.mask_editor)
        self._zoom.attach_pan(self._pan)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._overlay.reposition()
        self._zoom.reposition()

    @property
    def canvas(self):
        return self._canvas


def wrap_plot_with_instruments(canvas, main_window, ui_layout) -> PlotWithMaskInstruments:
    return PlotWithMaskInstruments(canvas, main_window, ui_layout)
