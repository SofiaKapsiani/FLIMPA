"""Pan and scroll navigation for zoomed intensity / lifetime image plots."""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QWidget

from utils.ui_icons import apply_nav_icon


def _image_ax(canvas):
    for ax in canvas.figure.axes:
        if ax.images:
            return ax
    return canvas.figure.axes[0] if canvas.figure.axes else None


def _image_bounds(ax):
    arr = ax.images[0].get_array()
    ny, nx = arr.shape[:2]
    return -0.5, nx - 0.5, ny - 0.5, -0.5


def _clamp_view(ax, xlim, ylim):
    """Keep the current view inside the image extent."""
    xmin, xmax, ymax, ymin = _image_bounds(ax)
    x0, x1 = xlim
    y0, y1 = ylim
    span_x = x1 - x0
    span_y = abs(y1 - y0)
    full_span_x = xmax - xmin
    full_span_y = abs(ymin - ymax)

    if span_x >= full_span_x:
        x0, x1 = xmin, xmax
    else:
        if x0 < xmin:
            x1 += xmin - x0
            x0 = xmin
        if x1 > xmax:
            x0 -= x1 - xmax
            x1 = xmax

    if span_y >= full_span_y:
        y0, y1 = ymax, ymin
    else:
        if y0 > y1:
            if y1 < ymin:
                y0 += ymin - y1
                y1 = ymin
            if y0 > ymax:
                y1 -= y0 - ymax
                y0 = ymax
        else:
            if y0 < ymin:
                y1 += ymin - y0
                y0 = ymin
            if y1 > ymax:
                y0 -= y1 - ymax
                y1 = ymax

    return (x0, x1), (y0, y1)


def capture_image_limits(canvas):
    """Save current zoom/pan view before figure.clear()."""
    ax = _image_ax(canvas)
    if ax is None:
        return None
    return ax.get_xlim(), ax.get_ylim()


def apply_image_limits(ax, limits):
    """Restore a saved view after replotting the image."""
    if limits is None or ax is None or not ax.images:
        return
    xlim, ylim = limits
    xlim, ylim = _clamp_view(ax, xlim, ylim)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)


class PlotPanController:
    """
    Drag-to-pan on zoomed image plots.

    - Pan button (hand): left-drag to move the view
    - Right-click drag or middle-click drag: pan any time
    - Two-finger scroll / mouse wheel: pan when zoomed in
    """

    def __init__(self, host: QWidget, canvas, editor):
        self.host = host
        self.canvas = canvas
        self.editor = editor
        self.pan_mode = False
        self._panning = False
        self._pan_anchor: tuple[float, float, tuple[float, float], tuple[float, float]] | None = None

        self.pan_btn = QPushButton(host)
        apply_nav_icon(self.pan_btn, "pan.svg", "Pan", checkable=True)
        self.pan_btn.toggled.connect(self._on_pan_mode_toggled)

        self._cids = [
            canvas.mpl_connect("button_press_event", self._on_press),
            canvas.mpl_connect("motion_notify_event", self._on_motion),
            canvas.mpl_connect("button_release_event", self._on_release),
            canvas.mpl_connect("scroll_event", self._on_scroll),
        ]

        if not hasattr(editor.main_window, "plot_pan_controllers"):
            editor.main_window.plot_pan_controllers = []
        editor.main_window.plot_pan_controllers.append(self)

    @property
    def blocks_inspect_click(self) -> bool:
        # Only block inspect while actively dragging to pan, not merely because pan mode exists.
        return self._panning

    def disable_pan_mode(self):
        self._panning = False
        self._pan_anchor = None
        self.pan_mode = False
        self.pan_btn.blockSignals(True)
        self.pan_btn.setChecked(False)
        self.pan_btn.blockSignals(False)

    def _on_pan_mode_toggled(self, enabled: bool):
        self.pan_mode = enabled

    def _pan_button(self, button: int) -> bool:
        if button in (2, 3):
            return True
        if self.editor._tool == "inspect":
            return False
        return self.pan_mode and button == 1

    def _on_press(self, event):
        ax = _image_ax(self.canvas)
        if ax is None or event.inaxes != ax or not self._pan_button(event.button):
            return
        self._panning = True
        self._pan_anchor = (event.xdata, event.ydata, ax.get_xlim(), ax.get_ylim())

    def _on_motion(self, event):
        if not self._panning or self._pan_anchor is None:
            return
        ax = _image_ax(self.canvas)
        if ax is None or event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
        xpress, ypress, (x0, x1), (y0, y1) = self._pan_anchor
        dx = xpress - event.xdata
        dy = ypress - event.ydata
        new_xlim, new_ylim = _clamp_view(ax, (x0 + dx, x1 + dx), (y0 + dy, y1 + dy))
        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        if self.editor._inspect_xy is not None:
            self.editor._draw_inspect_marker()
        self.canvas.draw_idle()

    def _on_release(self, event):
        self._panning = False
        self._pan_anchor = None

    def _on_scroll(self, event):
        ax = _image_ax(self.canvas)
        if ax is None or event.inaxes != ax:
            return
        xmin, xmax, ymax, ymin = _image_bounds(ax)
        x0, x1 = ax.get_xlim()
        y0, y1 = ax.get_ylim()
        span_x = x1 - x0
        span_y = abs(y1 - y0)
        if span_x >= (xmax - xmin) and span_y >= abs(ymin - ymax):
            return

        step = float(getattr(event, "step", 0) or 0)
        if step == 0:
            return
        frac = 0.12
        dx = -step * span_x * frac
        dy = -step * span_y * frac
        new_xlim, new_ylim = _clamp_view(ax, (x0 + dx, x1 + dx), (y0 + dy, y1 + dy))
        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        if self.editor._inspect_xy is not None:
            self.editor._draw_inspect_marker()
        self.canvas.draw_idle()

    def reposition(self):
        """Return button width for layout in PlotZoomOverlay."""
        return self.pan_btn.width()
